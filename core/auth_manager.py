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
from typing import Optional

import bcrypt

from core.session_manager import SessionManager, Role
from utils.error_handlers import AuthenticationError, AuthorizationError

logger = logging.getLogger(__name__)


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

    def authenticate(self, username: str, password: str) -> bool:
        """
        Autentica l'utente e apre la sessione in caso di successo.

        Args:
            username: Nome utente.
            password: Password in chiaro.

        Returns:
            True se autenticato, False se credenziali errate.

        Raises:
            AuthenticationError: Se l'account è disabilitato o si verifica
                                  un errore durante il recupero dei dati.
        """
        if not username or not password:
            return False

        try:
            user = self._db.get_utente_by_username(username.strip())
        except Exception as e:
            logger.error("Errore recupero utente '%s': %s", username, e)
            raise AuthenticationError(
                f"Impossibile verificare le credenziali: {e}"
            ) from e

        if user is None:
            logger.warning("Tentativo login utente inesistente: '%s'", username)
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
            return False

        # Successo — apri sessione
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
