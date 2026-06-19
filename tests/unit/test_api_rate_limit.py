"""
tests/unit/test_api_rate_limit.py
=================================
Test del rate limiting per le chiavi API (api/rate_limit.py + wiring in
api/deps.py). Le sessioni umane non sono soggette a throttling.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest


pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clean_buckets():
    import api.rate_limit as rl
    rl.reset()
    yield
    rl.reset()


# ─────────────────────────────────────────────────────────────────────
# check_and_increment (logica pura)
# ─────────────────────────────────────────────────────────────────────

class TestCheckAndIncrement:

    def test_no_limit_when_zero_or_none(self):
        from api.rate_limit import check_and_increment
        for limit in (0, None, -5):
            for _ in range(1000):
                allowed, retry = check_and_increment(1, limit)
                assert allowed is True
                assert retry == 0

    def test_allows_up_to_limit_then_blocks(self):
        from api.rate_limit import check_and_increment
        for _ in range(3):
            allowed, _ = check_and_increment(42, 3)
            assert allowed is True
        allowed, retry = check_and_increment(42, 3)
        assert allowed is False
        assert 1 <= retry <= 60

    def test_separate_keys_have_separate_budgets(self):
        from api.rate_limit import check_and_increment
        assert check_and_increment(1, 1)[0] is True
        assert check_and_increment(1, 1)[0] is False  # chiave 1 esaurita
        assert check_and_increment(2, 1)[0] is True    # chiave 2 indipendente

    def test_new_window_resets_counter(self, monkeypatch):
        import api.rate_limit as rl
        fake = {"now": 1000.0}
        monkeypatch.setattr(rl.time, "time", lambda: fake["now"])

        assert rl.check_and_increment(7, 1)[0] is True
        assert rl.check_and_increment(7, 1)[0] is False
        # Avanza di un minuto → nuova finestra
        fake["now"] += 60.0
        assert rl.check_and_increment(7, 1)[0] is True


# ─────────────────────────────────────────────────────────────────────
# Enforcement end-to-end attraverso l'app reale
# ─────────────────────────────────────────────────────────────────────

def _api_key_info(rate_limit):
    return {
        "id": 99, "name": "throttled", "prefix": "flr_rl000001",
        "scopes": ["*:*"],
        "created_by": None, "created_by_username": None,
        "created_by_ruolo": None, "rate_limit_per_min": rate_limit,
    }


@pytest.fixture
def app_factory():
    from fastapi.testclient import TestClient
    from api.main import create_app

    def _factory(rate_limit):
        mock_db = MagicMock()
        mock_db.validate_api_key = MagicMock(return_value=_api_key_info(rate_limit))
        mock_db.search_partite = MagicMock(return_value=[])
        app = create_app(db_manager=mock_db)
        return TestClient(app)

    yield _factory
    import api.deps as deps
    deps._db_manager = None


class TestRateLimitEnforcement:

    def test_requests_blocked_after_limit(self, app_factory):
        client = app_factory(rate_limit=2)
        hdr = {"X-Foliarium-Api-Key": "flr_x"}
        assert client.get("/api/v1/partite", headers=hdr).status_code == 200
        assert client.get("/api/v1/partite", headers=hdr).status_code == 200
        r = client.get("/api/v1/partite", headers=hdr)
        assert r.status_code == 429
        assert "Retry-After" in r.headers
        assert int(r.headers["Retry-After"]) >= 1

    def test_zero_limit_means_unlimited(self, app_factory):
        client = app_factory(rate_limit=0)
        hdr = {"X-Foliarium-Api-Key": "flr_x"}
        for _ in range(50):
            assert client.get("/api/v1/partite", headers=hdr).status_code == 200

    def test_human_session_not_throttled(self, app_factory):
        """Le sessioni bearer non hanno rate limit anche se la chiave lo avrebbe."""
        from api.auth import create_session
        client = app_factory(rate_limit=1)
        tok = create_session(1, "marco", "admin")
        hdr = {"Authorization": f"Bearer {tok}"}
        for _ in range(10):
            assert client.get("/api/v1/partite", headers=hdr).status_code == 200
