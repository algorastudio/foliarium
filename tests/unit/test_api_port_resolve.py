"""
tests/unit/test_api_port_resolve.py
===================================
Test del nuovo sistema di porta API pinnabile (api/main.py::resolve_api_port).

Verifica:
* Env var FOLIARIUM_API_PORT prevale su tutto.
* Sezione [api] port di config.ini se env vuota.
* Fallback su scan dinamico se nessuna config.
* Porta fissa occupata -> PinnedPortBusyError.
* Porte fuori range / non numeriche -> fallback senza crash.
"""

from __future__ import annotations

import socket
from unittest.mock import patch

import pytest


pytestmark = pytest.mark.unit


def _occupy_port(port: int):
    """Crea un socket in ascolto su localhost:port da chiudere con .close()."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
    s.bind(("127.0.0.1", port))
    s.listen(1)
    return s


# ─────────────────────────────────────────────────────────────────────
# resolve_api_port — happy path
# ─────────────────────────────────────────────────────────────────────

class TestResolveApiPort:

    def test_env_var_wins(self, monkeypatch):
        from api.main import resolve_api_port
        # Trova una porta libera per il test
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            free_port = s.getsockname()[1]
        monkeypatch.setenv("FOLIARIUM_API_PORT", str(free_port))
        with patch("config._ini_get", return_value=""):
            assert resolve_api_port() == free_port

    def test_config_ini_used_when_no_env(self, monkeypatch):
        from api.main import resolve_api_port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            free_port = s.getsockname()[1]
        monkeypatch.delenv("FOLIARIUM_API_PORT", raising=False)
        with patch("config._ini_get", return_value=str(free_port)):
            assert resolve_api_port() == free_port

    def test_dynamic_fallback_when_nothing_configured(self, monkeypatch):
        from api.main import resolve_api_port
        monkeypatch.delenv("FOLIARIUM_API_PORT", raising=False)
        with patch("config._ini_get", return_value=""):
            port = resolve_api_port(default_start=10000)
        assert 10000 <= port < 10100

    def test_pinned_port_busy_raises(self, monkeypatch):
        from api.main import resolve_api_port, PinnedPortBusyError
        # Occupa una porta
        sock = _occupy_port(0)  # 0 = kernel sceglie libera
        try:
            busy = sock.getsockname()[1]
            monkeypatch.setenv("FOLIARIUM_API_PORT", str(busy))
            with patch("config._ini_get", return_value=""):
                with pytest.raises(PinnedPortBusyError) as ei:
                    resolve_api_port()
            assert ei.value.port == busy
            assert str(busy) in str(ei.value)
            assert "FOLIARIUM_API_PORT" in str(ei.value)
        finally:
            sock.close()


# ─────────────────────────────────────────────────────────────────────
# Edge case — input non valido
# ─────────────────────────────────────────────────────────────────────

class TestResolveApiPortInvalid:

    def test_non_numeric_falls_back_to_scan(self, monkeypatch, caplog):
        from api.main import resolve_api_port
        monkeypatch.setenv("FOLIARIUM_API_PORT", "non-un-numero")
        with patch("config._ini_get", return_value=""):
            port = resolve_api_port(default_start=10000)
        assert 10000 <= port < 10100

    def test_port_out_of_range_falls_back(self, monkeypatch):
        from api.main import resolve_api_port
        monkeypatch.setenv("FOLIARIUM_API_PORT", "70000")  # > 65535
        with patch("config._ini_get", return_value=""):
            port = resolve_api_port(default_start=10000)
        assert 10000 <= port < 10100

    def test_port_too_low_falls_back(self, monkeypatch):
        from api.main import resolve_api_port
        monkeypatch.setenv("FOLIARIUM_API_PORT", "80")  # privilegiata
        with patch("config._ini_get", return_value=""):
            port = resolve_api_port(default_start=10000)
        assert 10000 <= port < 10100


# ─────────────────────────────────────────────────────────────────────
# PinnedPortBusyError
# ─────────────────────────────────────────────────────────────────────

class TestPinnedPortBusyError:

    def test_carries_port_attribute(self):
        from api.main import PinnedPortBusyError
        e = PinnedPortBusyError(9999)
        assert e.port == 9999

    def test_message_mentions_config(self):
        from api.main import PinnedPortBusyError
        msg = str(PinnedPortBusyError(8765))
        assert "FOLIARIUM_API_PORT" in msg
        assert "8765" in msg
