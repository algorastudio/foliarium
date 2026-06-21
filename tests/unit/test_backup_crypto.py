"""
tests/unit/test_backup_crypto.py
================================
Test della cifratura at-rest dei backup (foliarium/core/services/backup_crypto).
Usa una chiave esplicita per i test del cifrario (nessuna dipendenza dal
keyring); la gestione chiave via keyring è testata a parte con un backend finto.
"""
from __future__ import annotations

import os

import pytest


pytestmark = pytest.mark.unit

bc = pytest.importorskip(
    "foliarium.core.services.backup_crypto",
    reason="modulo backup_crypto non importabile",
)


def _crypto_available() -> bool:
    try:
        import cryptography  # noqa: F401
        return True
    except Exception:
        return False


requires_crypto = pytest.mark.skipif(
    not _crypto_available(), reason="cryptography non disponibile"
)


@pytest.fixture
def key():
    return bc.generate_key()


@requires_crypto
class TestRoundTrip:

    def _roundtrip(self, tmp_path, key, data: bytes):
        src = tmp_path / "plain.bin"
        enc = tmp_path / "plain.bin.enc"
        out = tmp_path / "restored.bin"
        src.write_bytes(data)
        bc.encrypt_file(str(src), str(enc), key)
        bc.decrypt_file(str(enc), str(out), key)
        assert out.read_bytes() == data

    def test_small(self, tmp_path, key):
        self._roundtrip(tmp_path, key, b"dati riservati possessori\n" * 10)

    def test_empty(self, tmp_path, key):
        self._roundtrip(tmp_path, key, b"")

    def test_exact_chunk_boundary(self, tmp_path, key):
        # Esattamente 2 blocchi pieni: verifica la gestione dei confini.
        self._roundtrip(tmp_path, key, os.urandom(bc._CHUNK * 2))

    def test_large_multichunk(self, tmp_path, key):
        # >2 blocchi con coda parziale.
        self._roundtrip(tmp_path, key, os.urandom(bc._CHUNK * 2 + 12345))

    def test_ciphertext_differs_from_plaintext(self, tmp_path, key):
        src = tmp_path / "p.bin"
        enc = tmp_path / "p.bin.enc"
        payload = b"SEGRETO" * 1000
        src.write_bytes(payload)
        bc.encrypt_file(str(src), str(enc), key)
        blob = enc.read_bytes()
        assert payload not in blob
        assert blob.startswith(bc.MAGIC)


@requires_crypto
class TestTamperAndWrongKey:

    def _make_enc(self, tmp_path, key):
        src = tmp_path / "p.bin"
        enc = tmp_path / "p.bin.enc"
        src.write_bytes(os.urandom(4096))
        bc.encrypt_file(str(src), str(enc), key)
        return enc

    def test_wrong_key_fails(self, tmp_path, key):
        enc = self._make_enc(tmp_path, key)
        other = bc.generate_key()
        with pytest.raises(bc.BackupCryptoError):
            bc.decrypt_file(str(enc), str(tmp_path / "o.bin"), other)

    def test_tampered_ciphertext_fails(self, tmp_path, key):
        enc = self._make_enc(tmp_path, key)
        blob = bytearray(enc.read_bytes())
        blob[-1] ^= 0xFF  # altera l'ultimo byte (tag/ciphertext)
        enc.write_bytes(bytes(blob))
        with pytest.raises(bc.BackupCryptoError):
            bc.decrypt_file(str(enc), str(tmp_path / "o.bin"), key)

    def test_truncated_fails(self, tmp_path, key):
        enc = self._make_enc(tmp_path, key)
        blob = enc.read_bytes()
        enc.write_bytes(blob[: len(blob) - 5])
        with pytest.raises(bc.BackupCryptoError):
            bc.decrypt_file(str(enc), str(tmp_path / "o.bin"), key)

    def test_decrypt_non_encrypted_file_fails(self, tmp_path, key):
        plain = tmp_path / "notenc.dump"
        plain.write_bytes(b"questo non e' cifrato")
        with pytest.raises(bc.BackupCryptoError):
            bc.decrypt_file(str(plain), str(tmp_path / "o.bin"), key)


@requires_crypto
class TestIsEncryptedFile:

    def test_detects_encrypted(self, tmp_path, key):
        src = tmp_path / "p.bin"
        enc = tmp_path / "p.bin.enc"
        src.write_bytes(b"x" * 100)
        bc.encrypt_file(str(src), str(enc), key)
        assert bc.is_encrypted_file(str(enc)) is True

    def test_plain_file_not_detected(self, tmp_path):
        plain = tmp_path / "p.dump"
        plain.write_bytes(b"PGDMP plain content")
        assert bc.is_encrypted_file(str(plain)) is False

    def test_missing_file_not_detected(self, tmp_path):
        assert bc.is_encrypted_file(str(tmp_path / "nope")) is False


@requires_crypto
class TestHighLevelHelpers:

    def test_encrypt_backup_removes_plaintext(self, tmp_path, key):
        src = tmp_path / "db.dump"
        src.write_bytes(os.urandom(5000))
        enc_path = bc.encrypt_backup(str(src), key=key)
        assert enc_path == str(src) + bc.ENC_SUFFIX
        assert os.path.exists(enc_path)
        assert not os.path.exists(str(src))  # plaintext rimosso

    def test_encrypt_backup_keep_plaintext(self, tmp_path, key):
        src = tmp_path / "db.dump"
        src.write_bytes(os.urandom(5000))
        bc.encrypt_backup(str(src), remove_plaintext=False, key=key)
        assert os.path.exists(str(src))

    def test_decrypt_backup_to_temp_roundtrip(self, tmp_path, key):
        src = tmp_path / "db.dump"
        data = os.urandom(9000)
        src.write_bytes(data)
        enc_path = bc.encrypt_backup(str(src), remove_plaintext=False, key=key)
        tmp = bc.decrypt_backup_to_temp(enc_path, key=key)
        try:
            assert open(tmp, "rb").read() == data
            assert tmp.endswith(".dump")  # estensione preservata per pg_restore
        finally:
            bc.secure_delete(tmp)
        assert not os.path.exists(tmp)


class TestKeyringManagement:
    """get_backup_key con un backend keyring in-memory (no cryptography richiesto)."""

    @pytest.fixture
    def fake_keyring(self, monkeypatch):
        keyring = pytest.importorskip("keyring", reason="keyring non disponibile")
        store = {}

        def _get(service, username):
            return store.get((service, username))

        def _set(service, username, value):
            store[(service, username)] = value

        monkeypatch.setattr(keyring, "get_password", _get)
        monkeypatch.setattr(keyring, "set_password", _set)
        return store

    def test_generates_and_persists_key(self, fake_keyring):
        k1 = bc.get_backup_key(create=True)
        assert len(k1) == 32
        # Una seconda chiamata restituisce la stessa chiave persistita.
        k2 = bc.get_backup_key(create=True)
        assert k1 == k2

    def test_no_create_raises_when_absent(self, fake_keyring):
        with pytest.raises(bc.BackupCryptoError):
            bc.get_backup_key(create=False)

    def test_corrupted_key_raises(self, fake_keyring):
        fake_keyring[(bc.KEYRING_SERVICE, bc.KEYRING_USERNAME)] = "!!!not-base64!!!"
        with pytest.raises(bc.BackupCryptoError):
            bc.get_backup_key(create=True)
