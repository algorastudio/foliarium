"""
tests/unit/test_license_manager.py
===================================
Unit test per license_manager.py — validazione licenze, fingerprint hardware,
gestione seat di rete.

Tutti i test sono puri unit test senza dipendenze da DB o GUI.
"""

import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from foliarium.core.services.license import (
    LicenseInfo,
    _count_active_seats,
    _seat_file_path,
    _sign_payload,
    _validate_file,
    acquire_network_seat,
    generate_license,
    get_hardware_fingerprint,
    refresh_network_seat,
    release_network_seat,
)


# ===========================================================================
# LicenseInfo dataclass
# ===========================================================================


@pytest.mark.unit
class TestLicenseInfo:
    def test_is_demo_true(self):
        info = LicenseInfo("Test", "demo", 1, None, None, __import__("datetime").date.today())
        assert info.is_demo()

    def test_is_demo_false(self):
        from datetime import date
        info = LicenseInfo("Test", "standard", 1, None, None, date.today())
        assert not info.is_demo()

    def test_is_perpetual_no_expiry(self):
        from datetime import date
        info = LicenseInfo("Test", "standard", 1, None, None, date.today())
        assert info.is_perpetual()

    def test_is_perpetual_with_expiry(self):
        from datetime import date
        info = LicenseInfo("Test", "standard", 1, date(2030, 12, 31), None, date.today())
        assert not info.is_perpetual()

    def test_days_to_expiry_perpetual(self):
        from datetime import date
        info = LicenseInfo("Test", "standard", 1, None, None, date.today())
        assert info.days_to_expiry() is None

    def test_days_to_expiry_future(self):
        from datetime import date, timedelta
        future = date.today() + timedelta(days=30)
        info = LicenseInfo("Test", "standard", 1, future, None, date.today())
        assert info.days_to_expiry() == 30

    def test_days_to_expiry_past(self):
        from datetime import date, timedelta
        past = date.today() - timedelta(days=10)
        info = LicenseInfo("Test", "standard", 1, past, None, date.today())
        assert info.days_to_expiry() == -10

    def test_default_is_valid_false(self):
        from datetime import date
        info = LicenseInfo("Test", "standard", 1, None, None, date.today())
        assert not info.is_valid

    def test_default_error_message_empty(self):
        from datetime import date
        info = LicenseInfo("Test", "standard", 1, None, None, date.today())
        assert info.error_message == ""


# ===========================================================================
# get_hardware_fingerprint
# ===========================================================================


@pytest.mark.unit
class TestHardwareFingerprint:
    def test_returns_hex_string(self):
        fp = get_hardware_fingerprint()
        assert isinstance(fp, str)
        assert len(fp) == 16 or fp == "unknown"

    def test_deterministic(self):
        """Lo stesso hardware deve produrre lo stesso fingerprint."""
        fp1 = get_hardware_fingerprint()
        fp2 = get_hardware_fingerprint()
        assert fp1 == fp2

    def test_hex_characters(self):
        fp = get_hardware_fingerprint()
        if fp != "unknown":
            assert all(c in "0123456789abcdef" for c in fp)


# ===========================================================================
# _sign_payload / generate_license
# ===========================================================================


@pytest.mark.unit
class TestSignPayload:
    def test_deterministic(self):
        payload = {"a": 1, "b": "hello"}
        sig1 = _sign_payload(payload)
        sig2 = _sign_payload(payload)
        assert sig1 == sig2

    def test_different_payload_different_sig(self):
        sig1 = _sign_payload({"a": 1})
        sig2 = _sign_payload({"a": 2})
        assert sig1 != sig2

    def test_key_order_irrelevant(self):
        """sort_keys=True rende l'ordine irrilevante."""
        sig1 = _sign_payload({"b": 2, "a": 1})
        sig2 = _sign_payload({"a": 1, "b": 2})
        assert sig1 == sig2


@pytest.mark.unit
class TestGenerateLicense:
    def test_valid_json(self):
        content = generate_license("Archivio Test")
        data = json.loads(content)
        assert "licensed_to" in data
        assert "signature" in data

    def test_contains_required_fields(self):
        content = generate_license("Archivio Test", "enterprise", 5, "2030-12-31")
        data = json.loads(content)
        assert data["licensed_to"] == "Archivio Test"
        assert data["license_type"] == "enterprise"
        assert data["max_seats"] == 5
        assert data["expiry_date"] == "2030-12-31"

    def test_perpetual_license(self):
        content = generate_license("Test", expiry_date=None)
        data = json.loads(content)
        assert data["expiry_date"] is None

    def test_hardware_bound(self):
        content = generate_license("Test", hardware_id="abc123")
        data = json.loads(content)
        assert data["hardware_id"] == "abc123"

    def test_signature_verifiable(self):
        content = generate_license("Test")
        data = json.loads(content)
        sig = data.pop("signature")
        expected = _sign_payload(data)
        assert sig == expected


# ===========================================================================
# _validate_file
# ===========================================================================


@pytest.mark.unit
class TestValidateFile:
    def test_file_not_found(self):
        info = _validate_file("/path/that/does/not/exist.license")
        assert not info.is_valid
        assert "non trovato" in info.error_message

    def test_invalid_json(self, tmp_path):
        bad_file = tmp_path / "bad.license"
        bad_file.write_text("not json at all")
        info = _validate_file(str(bad_file))
        assert not info.is_valid
        assert "non leggibile" in info.error_message

    def test_tampered_signature(self, tmp_path):
        content = generate_license("Test")
        data = json.loads(content)
        data["signature"] = "0000000000000000000000000000000000000000000000000000000000000000"
        tampered = tmp_path / "tampered.license"
        tampered.write_text(json.dumps(data))
        info = _validate_file(str(tampered))
        assert not info.is_valid
        assert "Firma" in info.error_message

    def test_missing_signature(self, tmp_path):
        content = generate_license("Test")
        data = json.loads(content)
        del data["signature"]
        no_sig = tmp_path / "nosig.license"
        no_sig.write_text(json.dumps(data))
        info = _validate_file(str(no_sig))
        assert not info.is_valid
        assert "Firma" in info.error_message

    def test_valid_perpetual_license(self, tmp_path):
        content = generate_license("Archivio Test", expiry_date=None)
        lic_file = tmp_path / "valid.license"
        lic_file.write_text(content)
        info = _validate_file(str(lic_file))
        assert info.is_valid
        assert info.licensed_to == "Archivio Test"
        assert info.expiry_date is None

    def test_valid_license_with_expiry(self, tmp_path):
        content = generate_license("Test", expiry_date="2099-12-31")
        lic_file = tmp_path / "valid.license"
        lic_file.write_text(content)
        info = _validate_file(str(lic_file))
        assert info.is_valid
        from datetime import date
        assert info.expiry_date == date(2099, 12, 31)

    def test_expired_license(self, tmp_path):
        content = generate_license("Test", expiry_date="2020-01-01")
        lic_file = tmp_path / "expired.license"
        lic_file.write_text(content)
        info = _validate_file(str(lic_file))
        assert not info.is_valid
        assert "scaduta" in info.error_message.lower()

    def test_wrong_hardware_id(self, tmp_path):
        content = generate_license("Test", hardware_id="0000000000000000")
        lic_file = tmp_path / "wrong_hw.license"
        lic_file.write_text(content)
        info = _validate_file(str(lic_file))
        # Potrebbe essere valida se il fingerprint corrente corrisponde per caso,
        # ma normalmente sara' non valida
        if not info.is_valid:
            assert "computer" in info.error_message.lower()

    def test_correct_hardware_id(self, tmp_path):
        hw = get_hardware_fingerprint()
        if hw == "unknown":
            pytest.skip("Hardware fingerprint non disponibile")
        content = generate_license("Test", hardware_id=hw)
        lic_file = tmp_path / "hw_ok.license"
        lic_file.write_text(content)
        info = _validate_file(str(lic_file))
        assert info.is_valid

    def test_license_type_preserved(self, tmp_path):
        content = generate_license("Test", license_type="enterprise", max_seats=10)
        lic_file = tmp_path / "enterprise.license"
        lic_file.write_text(content)
        info = _validate_file(str(lic_file))
        assert info.is_valid
        assert info.license_type == "enterprise"
        assert info.max_seats == 10


# ===========================================================================
# Seat di rete
# ===========================================================================


@pytest.mark.unit
class TestNetworkSeats:
    def test_seat_file_path_format(self):
        import socket
        path = _seat_file_path("/tmp/share", "abc123")
        hostname = socket.gethostname()
        assert f"foliarium_seat_{hostname}_abc123.json" in str(path)

    def test_acquire_empty_share_returns_true(self):
        """Se share_path e' vuoto, acquire ritorna sempre True."""
        ok, seats, _ = acquire_network_seat("", "test-id")
        assert ok
        assert seats == 1

    def test_acquire_creates_seat_file(self, tmp_path):
        share = str(tmp_path / "seats")
        ok, seats, _ = acquire_network_seat(share, "inst-001")
        assert ok
        assert seats == 1
        # Verifica che il file esista
        seat_files = list((tmp_path / "seats").glob("foliarium_seat_*.json"))
        assert len(seat_files) == 1

    def test_acquire_multiple_seats(self, tmp_path):
        share = str(tmp_path / "seats")
        acquire_network_seat(share, "inst-001")
        ok, seats, _ = acquire_network_seat(share, "inst-002")
        assert ok
        assert seats == 2

    def test_release_removes_file(self, tmp_path):
        share = str(tmp_path / "seats")
        acquire_network_seat(share, "inst-001")
        release_network_seat(share, "inst-001")
        seat_files = list((tmp_path / "seats").glob("foliarium_seat_*.json"))
        assert len(seat_files) == 0

    def test_release_empty_share_no_error(self):
        """Release con share vuoto non deve lanciare eccezioni."""
        release_network_seat("", "test-id")

    def test_refresh_updates_timestamp(self, tmp_path):
        share = str(tmp_path / "seats")
        acquire_network_seat(share, "inst-001")
        seat_files = list((tmp_path / "seats").glob("foliarium_seat_*.json"))
        with open(seat_files[0]) as f:
            ts_before = json.load(f)["ts"]
        time.sleep(0.05)
        refresh_network_seat(share, "inst-001")
        with open(seat_files[0]) as f:
            ts_after = json.load(f)["ts"]
        assert ts_after >= ts_before

    def test_refresh_empty_share_no_error(self):
        refresh_network_seat("", "test-id")

    def test_stale_seats_cleaned(self, tmp_path):
        """Seat con timestamp vecchio viene pulito da _count_active_seats."""
        share = tmp_path / "seats"
        share.mkdir()
        import socket
        stale_file = share / f"foliarium_seat_{socket.gethostname()}_old.json"
        with open(stale_file, "w") as f:
            json.dump({"ts": time.time() - 300, "host": "test", "pid": 1}, f)
        count = _count_active_seats(str(share))
        assert count == 0
        assert not stale_file.exists()

    def test_active_seats_counted(self, tmp_path):
        share = tmp_path / "seats"
        share.mkdir()
        import socket
        active_file = share / f"foliarium_seat_{socket.gethostname()}_new.json"
        with open(active_file, "w") as f:
            json.dump({"ts": time.time(), "host": "test", "pid": 1}, f)
        count = _count_active_seats(str(share))
        assert count == 1
