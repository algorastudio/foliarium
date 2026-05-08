"""
core/auth_manager.py — Autenticazione e controllo accessi per Foliarium.

Fornisce AuthManager che si appoggia a CatastoDBManager e SessionManager
per autenticare gli utenti e verificare i permessi.

Utilizzo:
    from core.auth_manager import AuthManager
    from core.session_manager import SessionManager

    session = SessionManager()
    auth = AuthManager(db_manager, session)

    if auth.authenticate("mario", "password123"):
        print("Accesso consentito:", session.display_name)
    else:
        print("Credenziali errate")

    # Verifica permessi (lancia AuthorizationError se non autorizzato):
    auth.require_permission("manage_users")
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import bcrypt

from core.session_manager import SessionManager, Role
from utils.error_handlers import AuthenticationError, AuthorizationError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate limiting in-memory (per-processo).
# Protegge da brute-force sul login GUI/API della singola istanza.
# ---------------------------------------------------------------------------
_LOCKOUT_THRESHOLD = 5        # tentativi falliti prima del blocco
_LOCKOUT_DURATION = 900       # secondi di lockout (15 minuti)

_login_failures: dict[str, dict] = {}  # {username: {"count": int, "locked_until": float}}
_rate_lock = threading.Lock()

# Hash precomputato (bcrypt cost 12) usato come dummy per normalizzare i tempi
# di risposta del login e impedire user enumeration tramite timing.
_DUMMY_HASH = "$2b$12$GKuBBTnSGLRF1LRjMZWoLuiQF5kVXq7Jl9VFhJxcN8tAe2gOQUhy"


class AuthManager:
    """
    Gestisce autenticazione utenti e verifica permessi.

    Si integra con il DB layer (CatastoDBManager) per recuperare
    le credenziali e con SessionManager per mantenere lo stato.
    """

    def __init__(self, db_manager, session: SessionManager) -> None:
        """
        Args:
            db_manager: Istanza di CatastoDBManager già connessa.
            session:    Istanza di SessionManager condivisa con l'app.
        """
        self._db = db_manager
        self._session = session

    # ------------------------------------------------------------------
    # Autenticazione
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Rate limiting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_locked_out(username: str) -> bool:
        with _rate_lock:
            entry = _login_failures.get(username)
            if not entry:
                return False
            if entry["count"] >= _LOCKOUT_THRESHOLD:
                if time.monotonic() < entry["locked_until"]:
                    return True
                # Lockout scaduto: azzera
                _login_failures.pop(username, None)
            return False

    @staticmethod
    def _record_failure(username: str) -> int:
        with _rate_lock:
            entry = _login_failures.setdefault(username, {"count": 0, "locked_until": 0.0})
            entry["count"] += 1
            if entry["count"] >= _LOCKOUT_THRESHOLD:
                entry["locked_until"] = time.monotonic() + _LOCKOUT_DURATION
                logger.warning(
                    "Account '%s' bloccato per %d minuti dopo %d tentativi falliti.",
                    username, _LOCKOUT_DURATION // 60, entry["count"],
                )
            return entry["count"]

    @staticmethod
    def _reset_failures(username: str) -> None:
        with _rate_lock:
            _login_failures.pop(username, None)

    # ------------------------------------------------------------------
    # Autenticazione
    # ------------------------------------------------------------------

    def authenticate(self, username: str, password: str) -> bool:
        """
        Autentica l'utente e apre la sessione in caso di successo.

        Args:
            username: Nome utente.
            password: Password in chiaro.

        Returns:
            True se autenticato, False se credenziali errate.

        Raises:
            AuthenticationError: Se l'account è bloccato, disabilitato o si
                                  verifica un errore durante il recupero.
        """
        if not username or not password:
            return False

        username = username.strip()

        if self._is_locked_out(username):
            logger.warning("Login bloccato per rate limiting: '%s'", username)
            raise AuthenticationError(
                "Account temporaneamente bloccato per troppi tentativi falliti.\n"
                f"Riprovare tra {_LOCKOUT_DURATION // 60} minuti o contattare l'amministratore."
            )

        try:
            user = self._db.get_utente_by_username(username)
        except Exception as e:
            logger.error("Errore recupero utente '%s': %s", username, e)
            raise AuthenticationError(
                f"Impossibile verificare le credenziali: {e}"
            ) from e

        if user is None:
            logger.warning("Tentativo login utente inesistente: '%s'", username)
            # Esegue un check bcrypt dummy per normalizzare i tempi di risposta
            # e impedire user enumeration tramite timing.
            self._verify_password(_DUMMY_HASH, password)
            self._record_failure(username)
            return False

        # Verifica account attivo
        if not user.get("attivo", True):
            logger.warning("Tentativo login account disabilitato: '%s'", username)
            raise AuthenticationError(
                "L'account è stato disabilitato. Contattare l'amministratore."
            )

        # Verifica password
        stored_hash = user.get("password_hash", "")
        if not self._verify_password(stored_hash, password):
            logger.warning("Password errata per utente '%s'", username)
            self._record_failure(username)
            return False

        # Successo — azzera contatore e apri sessione
        self._reset_failures(username)
        self._session.login(
            user_id=user["id"],
            user_info={
                "nome": user.get("nome", username),
                "ruolo": user.get("ruolo", Role.VISUALIZZATORE),
                "email": user.get("email"),
                "username": username,
            },
        )

        logger.info(
            "Autenticazione riuscita: '%s' (id=%s, ruolo=%s)",
            username,
            user["id"],
            user.get("ruolo"),
        )
        return True

    def logout(self) -> None:
        """Chiude la sessione corrente."""
        self._session.logout()

    # ------------------------------------------------------------------
    # Verifica permessi
    # ------------------------------------------------------------------

    def check_permission(self, permission: str) -> bool:
        """Ritorna True se l'utente ha il permesso, False altrimenti."""
        return self._session.has_permission(permission)

    def require_permission(self, permission: str) -> None:
        """
        Verifica che l'utente abbia il permesso specificato.

        Raises:
            AuthenticationError: Se non autenticato.
            AuthorizationError:  Se autenticato ma senza il permesso.
        """
        if not self._session.is_authenticated:
            raise AuthenticationError("Sessione non attiva. Effettuare il login.")
        if not self._session.has_permission(permission):
            raise AuthorizationError(
                f"Permesso '{permission}' non disponibile per il ruolo "
                f"'{self._session.role}'."
            )

    def require_admin(self) -> None:
        """Verifica che l'utente sia admin."""
        self.require_permission("manage_users")

    # ------------------------------------------------------------------
    # Change password
    # ------------------------------------------------------------------

    def change_password(
        self,
        user_id: int,
        new_password: str,
        current_password: Optional[str] = None,
    ) -> bool:
        """
        Cambia la password di un utente.

        Se current_password è fornita, verifica prima la password corrente
        (usato quando l'utente cambia la propria password).
        Se non fornita, richiede che il chiamante sia admin.

        Returns:
            True se la password è stata cambiata.

        Raises:
            AuthenticationError: Se la password corrente è errata.
            AuthorizationError:  Se l'utente non ha i permessi.
            ValueError:          Se la nuova password non rispetta la policy.
        """
        from validators import FieldValidator

        # Validazione nuova password
        result = FieldValidator.password_strength(new_password)
        if not result.is_valid:
            raise ValueError(result.error_message)

        # Se viene fornita la password corrente, verifichiamo
        if current_password is not None:
            try:
                user = self._db.get_utente_by_id(user_id)
            except Exception as e:
                raise AuthenticationError(f"Impossibile recuperare l'utente: {e}") from e

            if user is None or not self._verify_password(
                user.get("password_hash", ""), current_password
            ):
                raise AuthenticationError("La password corrente non è corretta.")
        else:
            # Senza password corrente, solo l'admin può farlo
            self.require_permission("manage_users")

        new_hash = self._hash_password(new_password)
        try:
            self._db.update_user_password(user_id, new_hash)
        except Exception as e:
            raise AuthenticationError(
                f"Impossibile aggiornare la password: {e}"
            ) from e

        logger.info("Password cambiata per user_id=%s", user_id)
        return True

    # ------------------------------------------------------------------
    # Helper crittografia
    # ------------------------------------------------------------------

    @staticmethod
    def _hash_password(password: str) -> str:
        return bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

    @staticmethod
    def _verify_password(stored_hash: str, password: str) -> bool:
        try:
            if not stored_hash:
                return False
            return bcrypt.checkpw(
                password.encode("utf-8"),
                stored_hash.encode("utf-8"),
            )
        except Exception as e:
            logger.error("Errore verifica password: %s", e)
            return False
