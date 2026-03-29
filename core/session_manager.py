"""
core/session_manager.py — Gestione sessione utente per Foliarium.

Fornisce un oggetto SessionManager che centralizza lo stato dell'utente
autenticato, sostituendo le variabili sparse in gui_main.py.

Il SessionManager è thread-safe per accessi in lettura; le scritture
(login/logout) avvengono solo dal thread UI.

Utilizzo:
    from core.session_manager import SessionManager

    session = SessionManager()

    # Dopo il login:
    session.login(user_id=5, user_info={"nome": "Admin", ...}, session_id="abc")

    # In qualsiasi punto:
    if session.is_authenticated:
        print(session.user_id, session.role)

    # Logout:
    session.logout()
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from threading import Lock
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Ruoli utente (specchio dei ruoli nel DB)
# ---------------------------------------------------------------------------

class Role:
    ADMIN = "admin"
    ARCHIVISTA = "archivista"
    VISUALIZZATORE = "visualizzatore"

    _ALL = {ADMIN, ARCHIVISTA, VISUALIZZATORE}

    # Permessi per ruolo: set di stringhe azione
    _PERMISSIONS: Dict[str, set] = {
        ADMIN: {
            "view", "search", "insert", "edit", "delete",
            "export", "import", "manage_users", "view_audit",
            "backup", "configure",
        },
        ARCHIVISTA: {
            "view", "search", "insert", "edit",
            "export", "import",
        },
        VISUALIZZATORE: {
            "view", "search", "export",
        },
    }

    @classmethod
    def permissions_for(cls, role: str) -> set:
        return cls._PERMISSIONS.get(role, set())

    @classmethod
    def is_valid(cls, role: str) -> bool:
        return role in cls._ALL


# ---------------------------------------------------------------------------
# SessionManager
# ---------------------------------------------------------------------------

class SessionManager:
    """
    Gestisce lo stato della sessione utente corrente.

    Un'istanza di questo oggetto viene creata in CatastoMainWindow e
    passata ai widget che ne hanno bisogno, evitando variabili globali.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._user_id: Optional[int] = None
        self._user_info: Dict[str, Any] = {}
        self._session_id: Optional[str] = None
        self._login_time: Optional[datetime] = None
        self._last_activity: Optional[datetime] = None
        self._client_ip: str = "127.0.0.1"

    # ------------------------------------------------------------------
    # Autenticazione
    # ------------------------------------------------------------------

    def login(
        self,
        user_id: int,
        user_info: Dict[str, Any],
        session_id: Optional[str] = None,
        client_ip: str = "127.0.0.1",
    ) -> None:
        """
        Avvia una nuova sessione utente.

        Args:
            user_id:    ID univoco dell'utente nel DB.
            user_info:  Dizionario con almeno 'nome' e 'ruolo'.
            session_id: UUID sessione (generato automaticamente se None).
            client_ip:  IP del client (per audit log).
        """
        with self._lock:
            now = datetime.now()
            self._user_id = user_id
            self._user_info = dict(user_info)
            self._session_id = session_id or str(uuid.uuid4())
            self._login_time = now
            self._last_activity = now
            self._client_ip = client_ip

        logger.info(
            "Login: user_id=%s nome='%s' ruolo='%s' session=%s",
            user_id,
            user_info.get("nome", "?"),
            user_info.get("ruolo", "?"),
            self._session_id[:8] + "..." if self._session_id else "?",
        )

    def logout(self) -> None:
        """Termina la sessione corrente."""
        with self._lock:
            user_name = self._user_info.get("nome", "?")
            self._user_id = None
            self._user_info = {}
            self._session_id = None
            self._login_time = None
            self._last_activity = None

        logger.info("Logout: utente '%s'", user_name)

    def refresh_activity(self) -> None:
        """Aggiorna il timestamp di ultima attività (per il timeout sessione)."""
        with self._lock:
            if self._user_id is not None:
                self._last_activity = datetime.now()

    # ------------------------------------------------------------------
    # Stato sessione (proprietà thread-safe in lettura)
    # ------------------------------------------------------------------

    @property
    def is_authenticated(self) -> bool:
        return self._user_id is not None

    @property
    def user_id(self) -> Optional[int]:
        return self._user_id

    @property
    def session_id(self) -> Optional[str]:
        return self._session_id

    @property
    def login_time(self) -> Optional[datetime]:
        return self._login_time

    @property
    def last_activity(self) -> Optional[datetime]:
        return self._last_activity

    @property
    def client_ip(self) -> str:
        return self._client_ip

    # ------------------------------------------------------------------
    # Informazioni utente
    # ------------------------------------------------------------------

    @property
    def user_info(self) -> Dict[str, Any]:
        """Copia del dizionario user_info (immutabile dall'esterno)."""
        return dict(self._user_info)

    @property
    def role(self) -> Optional[str]:
        return self._user_info.get("ruolo")

    @property
    def display_name(self) -> str:
        return self._user_info.get("nome", "")

    @property
    def email(self) -> Optional[str]:
        return self._user_info.get("email")

    # ------------------------------------------------------------------
    # Permessi
    # ------------------------------------------------------------------

    def has_permission(self, permission: str) -> bool:
        """
        Verifica se l'utente ha il permesso specificato.

        Args:
            permission: Una delle stringhe definite in Role._PERMISSIONS.
        """
        if not self.is_authenticated:
            return False
        return permission in Role.permissions_for(self.role or "")

    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    def can(self, *permissions: str) -> bool:
        """Ritorna True se l'utente ha TUTTI i permessi elencati."""
        return all(self.has_permission(p) for p in permissions)

    def can_any(self, *permissions: str) -> bool:
        """Ritorna True se l'utente ha ALMENO UNO dei permessi elencati."""
        return any(self.has_permission(p) for p in permissions)

    # ------------------------------------------------------------------
    # Contesto per audit log
    # ------------------------------------------------------------------

    def get_audit_context(self) -> Dict[str, Any]:
        """
        Restituisce un dict con i dati necessari per scrivere in audit_log.

        Compatibile con CatastoDBManager.log_app_event().
        """
        return {
            "user_id": self._user_id,
            "session_id": self._session_id,
            "client_ip": self._client_ip,
        }

    # ------------------------------------------------------------------
    # Timeout
    # ------------------------------------------------------------------

    def seconds_since_activity(self) -> float:
        """Secondi trascorsi dall'ultima attività (-1 se non autenticato)."""
        if self._last_activity is None:
            return -1.0
        return (datetime.now() - self._last_activity).total_seconds()

    def is_timed_out(self, timeout_minutes: int) -> bool:
        """
        Verifica se la sessione è scaduta per inattività.

        Args:
            timeout_minutes: 0 significa nessun timeout.
        """
        if not self.is_authenticated or timeout_minutes <= 0:
            return False
        return self.seconds_since_activity() > timeout_minutes * 60

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        if not self.is_authenticated:
            return "SessionManager(non autenticato)"
        return (
            f"SessionManager(user_id={self._user_id}, "
            f"nome='{self.display_name}', ruolo='{self.role}')"
        )
