"""api/deps.py — Dependency injection FastAPI: DB manager + autenticazione.

Supporta due metodi di autenticazione equivalenti dal punto di vista delle
route:

1. **Sessione utente** (`Authorization: Bearer <token>`): usata dal frontend
   React, sessione in-memory TTL 120 min (vedi `api/auth.py`). Implicitamente
   ha tutti gli scope.

2. **Chiave API** (`X-Foliarium-Api-Key: flr_xxxxxxxx...`): usata da
   integrazioni esterne (MCP server, Zapier, script). Scopes granulari
   memorizzati in `catasto.api_keys`.

Le route esistenti continuano a usare ``get_current_session`` senza modifiche:
restituisce un dict con la stessa shape di prima, con in più i campi
``auth_method`` (``"session"`` | ``"api_key"``) e ``scopes`` (lista). Per le
route che vogliono fare scope-check usare ``require_scope("read:partite")``.
"""

from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from api.auth import get_session
from api.rate_limit import check_and_increment

_bearer = HTTPBearer(auto_error=False)

API_KEY_HEADER = "X-Foliarium-Api-Key"

# DB manager è un singleton impostato da api/main.py all'avvio
_db_manager = None


def set_db_manager(mgr) -> None:
    global _db_manager
    _db_manager = mgr


def get_db():
    if _db_manager is None:
        raise HTTPException(status_code=503, detail="Database non disponibile")
    return _db_manager


def _principal_from_api_key(plaintext: str) -> Optional[dict]:
    """Valida una API key contro il DB. Restituisce dict-session-like o None."""
    if _db_manager is None:
        return None
    info = _db_manager.validate_api_key(plaintext)
    if info is None:
        return None
    return {
        # Lo schema dict è retrocompatibile con la session: user_id, username,
        # ruolo come prima, ma con auth_method e scopes in più.
        "user_id": info.get("created_by"),
        "username": info.get("created_by_username") or f"api-key:{info['prefix']}",
        "ruolo": info.get("created_by_ruolo") or "api",
        "auth_method": "api_key",
        "scopes": info.get("scopes") or [],
        "api_key_id": info["id"],
        "api_key_name": info["name"],
        "rate_limit_per_min": info.get("rate_limit_per_min"),
    }


def get_current_session(
    request: Request,
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    """Autenticazione: prova API key, poi bearer session.

    Mantiene il nome storico per backward compat con le 8 routes esistenti.
    """
    # 1. API key header
    api_key = request.headers.get(API_KEY_HEADER)
    if api_key:
        principal = _principal_from_api_key(api_key)
        if principal is not None:
            allowed, retry_after = check_and_increment(
                principal.get("api_key_id"), principal.get("rate_limit_per_min")
            )
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        "Limite di richieste superato per la chiave API "
                        f"(max {principal.get('rate_limit_per_min')}/min). "
                        f"Riprovare tra {retry_after}s."
                    ),
                    headers={"Retry-After": str(retry_after)},
                )
            return principal
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chiave API non valida, scaduta o revocata",
        )

    # 2. Bearer session token (flusso frontend)
    if creds is not None:
        session = get_session(creds.credentials)
        if session is not None:
            # Arricchisco la session con i campi nuovi mantenendo backward compat
            return {
                **session,
                "auth_method": "session",
                "scopes": ["*:*"],  # le sessioni umane hanno tutti gli scope
            }
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessione scaduta o non valida",
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenziali mancanti (Authorization: Bearer ... o X-Foliarium-Api-Key)",
    )


def require_admin(session: dict = Depends(get_current_session)) -> dict:
    if session.get("ruolo") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accesso riservato agli amministratori",
        )
    return session


def _scope_matches(granted: str, required: str) -> bool:
    """Match con wildcard: `read:*` copre `read:partite`, `*:*` copre tutto."""
    if granted == required or granted == "*:*":
        return True
    if ":" in granted and ":" in required:
        g_act, g_res = granted.split(":", 1)
        r_act, r_res = required.split(":", 1)
        if (g_act == r_act or g_act == "*") and (g_res == r_res or g_res == "*"):
            return True
    return False


def require_scope(scope: str):
    """Factory di dependency che richiede uno scope specifico.

    Le sessioni utente (auth_method="session") passano sempre grazie allo
    scope wildcard ``*:*``. Le chiavi API devono avere lo scope esatto o uno
    wildcard che lo copre.

    Uso::

        @router.get("/partite")
        def list_partite(session=Depends(require_scope("read:partite"))):
            ...
    """
    def _checker(session: dict = Depends(get_current_session)) -> dict:
        granted = session.get("scopes") or []
        if any(_scope_matches(g, scope) for g in granted):
            return session
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Scope richiesto: {scope!r}. Scope concessi: {granted}.",
        )
    return _checker
