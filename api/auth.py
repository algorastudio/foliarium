"""
api/auth.py — Gestione sessioni in-memory per il server API locale.
Token UUID, nessun JWT: il server gira solo su localhost.
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict

SESSION_TTL_MINUTES = 120

_sessions: Dict[str, dict] = {}


def create_session(user_id: int, username: str, ruolo: str) -> str:
    token = str(uuid.uuid4())
    _sessions[token] = {
        "user_id": user_id,
        "username": username,
        "ruolo": ruolo,
        "expires": datetime.utcnow() + timedelta(minutes=SESSION_TTL_MINUTES),
    }
    return token


def get_session(token: str) -> Optional[dict]:
    s = _sessions.get(token)
    if s is None:
        return None
    if datetime.utcnow() > s["expires"]:
        _sessions.pop(token, None)
        return None
    s["expires"] = datetime.utcnow() + timedelta(minutes=SESSION_TTL_MINUTES)
    return s


def delete_session(token: str) -> None:
    _sessions.pop(token, None)
