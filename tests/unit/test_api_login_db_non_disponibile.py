"""
tests/unit/test_api_login_db_non_disponibile.py
===============================================
Il login web deve distinguere "credenziali sbagliate" da "database giu'".

Prima della correzione ``get_user_credentials`` restituiva ``None`` anche
quando la query falliva, e ``POST /auth/login`` lo trattava come utente
inesistente: con il database irraggiungibile (per esempio ``DB_SSLMODE=require``
contro un PostgreSQL senza TLS) ogni login rispondeva 401 «Credenziali non
valide». L'archivista credeva di aver sbagliato la password e chi gestisce
il server non vedeva nulla che puntasse al database.

Contratto fissato qui:

- errore del database durante il login       -> 503 «Database non disponibile»
- utente inesistente                         -> 401 «Credenziali non valide»
- password errata                            -> 401 «Credenziali non valide»
- manager presente ma pool mai inizializzato -> 503 da ``get_db``, con un
  nuovo tentativo di inizializzazione al piu' ogni ``_POOL_RETRY_INTERVAL_S``
  secondi, cosi' l'API torna a rispondere quando il database risale.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import bcrypt
import psycopg2
import pytest

from catasto_exceptions import DBMError


pytestmark = pytest.mark.unit

LOGIN_URL = "/api/v1/auth/login"


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode()


def _errore_db() -> DBMError:
    """DBMError incatenato a un errore di connessione, come lo solleva il layer DB."""
    causa = psycopg2.OperationalError(
        "connection to server failed: server does not support SSL, "
        "but SSL was required"
    )
    try:
        raise DBMError("Database non raggiungibile") from causa
    except DBMError as e:
        return e


@pytest.fixture
def client_con_db():
    """TestClient con il solo router di auth e un db_manager mockato."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import api.deps as deps
    from api.routes import auth

    def _factory(mock_db):
        deps.set_db_manager(mock_db)
        app = FastAPI()
        app.include_router(auth.router, prefix="/api/v1")
        return TestClient(app)

    yield _factory

    deps.set_db_manager(None)


# ─────────────────────────────────────────────────────────────────────
# POST /auth/login
# ─────────────────────────────────────────────────────────────────────

class TestLoginConDatabaseNonDisponibile:

    def test_errore_db_risponde_503(self, client_con_db):
        mock_db = MagicMock()
        mock_db.get_user_credentials = MagicMock(side_effect=_errore_db())
        client = client_con_db(mock_db)

        r = client.post(LOGIN_URL, json={"username": "admin", "password": "x"})

        assert r.status_code == 503
        assert r.json()["detail"] == "Database non disponibile"

    def test_utente_inesistente_risponde_401(self, client_con_db):
        mock_db = MagicMock()
        mock_db.get_user_credentials = MagicMock(return_value=None)
        client = client_con_db(mock_db)

        r = client.post(LOGIN_URL, json={"username": "nessuno", "password": "x"})

        assert r.status_code == 401
        assert r.json()["detail"] == "Credenziali non valide"

    def test_password_errata_risponde_401(self, client_con_db):
        mock_db = MagicMock()
        mock_db.get_user_credentials = MagicMock(return_value={
            "id": 1, "username": "admin", "password_hash": _hash("giusta"),
            "nome_completo": "Admin", "ruolo": "admin", "attivo": True,
        })
        client = client_con_db(mock_db)

        r = client.post(LOGIN_URL, json={"username": "admin", "password": "sbagliata"})

        assert r.status_code == 401
        assert r.json()["detail"] == "Credenziali non valide"

    def test_credenziali_corrette_rispondono_200(self, client_con_db):
        mock_db = MagicMock()
        mock_db.get_user_credentials = MagicMock(return_value={
            "id": 7, "username": "archivista", "password_hash": _hash("giusta"),
            "nome_completo": "Archivista", "ruolo": "editor", "attivo": True,
        })
        client = client_con_db(mock_db)

        r = client.post(LOGIN_URL, json={"username": "archivista", "password": "giusta"})

        assert r.status_code == 200
        corpo = r.json()
        assert corpo["user_id"] == 7
        assert corpo["token"]


# ─────────────────────────────────────────────────────────────────────
# get_db con pool non inizializzato
# ─────────────────────────────────────────────────────────────────────

class _ManagerSenzaPool:
    """Manager reale nella forma che conta qui: ``pool`` e ``initialize_main_pool``.

    Non e' un MagicMock perche' su un MagicMock ``pool`` sarebbe sempre un
    oggetto vero e il caso "pool assente" non si presenterebbe mai.
    """

    def __init__(self, init_riesce: bool = False):
        self.pool = None
        self.init_riesce = init_riesce
        self.tentativi_init = 0
        self.get_user_credentials = MagicMock(return_value=None)

    def initialize_main_pool(self) -> bool:
        self.tentativi_init += 1
        if self.init_riesce:
            self.pool = object()
            return True
        return False


@pytest.fixture
def orologio(monkeypatch):
    """Orologio monotono controllabile per il throttling dei tentativi."""
    import api.deps as deps

    stato = {"t": 1000.0}
    monkeypatch.setattr(deps.time, "monotonic", lambda: stato["t"])
    return stato


class TestGetDbSenzaPool:

    def test_pool_assente_e_db_giu_risponde_503(self, client_con_db, orologio):
        mgr = _ManagerSenzaPool(init_riesce=False)
        client = client_con_db(mgr)

        r = client.post(LOGIN_URL, json={"username": "admin", "password": "x"})

        assert r.status_code == 503
        assert r.json()["detail"] == "Database non disponibile"
        mgr.get_user_credentials.assert_not_called()

    def test_pool_assente_ritenta_e_si_riprende_quando_il_db_risale(
        self, client_con_db, orologio
    ):
        mgr = _ManagerSenzaPool(init_riesce=True)
        client = client_con_db(mgr)

        r = client.post(LOGIN_URL, json={"username": "nessuno", "password": "x"})

        # Il pool si e' inizializzato al volo: la richiesta arriva al
        # controllo delle credenziali, che risponde 401 per l'utente inesistente.
        assert mgr.tentativi_init == 1
        assert r.status_code == 401
        mgr.get_user_credentials.assert_called_once_with("nessuno")

    def test_tentativi_di_inizializzazione_limitati_nel_tempo(
        self, client_con_db, orologio
    ):
        import api.deps as deps

        mgr = _ManagerSenzaPool(init_riesce=False)
        client = client_con_db(mgr)

        for _ in range(3):
            assert client.post(
                LOGIN_URL, json={"username": "a", "password": "b"}
            ).status_code == 503
        # Tre richieste ravvicinate: un solo tentativo verso il database.
        assert mgr.tentativi_init == 1

        orologio["t"] += deps._POOL_RETRY_INTERVAL_S + 0.1
        assert client.post(
            LOGIN_URL, json={"username": "a", "password": "b"}
        ).status_code == 503
        assert mgr.tentativi_init == 2

    def test_manager_assente_risponde_ancora_503(self, client_con_db):
        client = client_con_db(None)

        r = client.post(LOGIN_URL, json={"username": "admin", "password": "x"})

        assert r.status_code == 503
        assert r.json()["detail"] == "Database non disponibile"
