"""
api/deps.py — Dependency injection FastAPI: DB manager + autenticazione.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from api.auth import get_session

_bearer = HTTPBearer(auto_error=False)

# DB manager è un singleton impostato da api/main.py all'avvio
_db_manager = None


def set_db_manager(mgr) -> None:
    global _db_manager
    _db_manager = mgr


def get_db():
    if _db_manager is None:
        raise HTTPException(status_code=503, detail="Database non disponibile")
    return _db_manager


def get_current_session(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    if creds is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token mancante")
    session = get_session(creds.credentials)
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessione scaduta o non valida")
    return session


def require_admin(session: dict = Depends(get_current_session)) -> dict:
    if session.get("ruolo") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accesso riservato agli amministratori")
    return session
