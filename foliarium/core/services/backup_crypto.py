"""foliarium/core/services/backup_crypto.py — Cifratura at-rest dei backup DB.

I file prodotti da ``pg_dump`` sono in chiaro e contengono l'intero archivio
(inclusi i dati personali dei possessori). Questo modulo li cifra con
**AES-256-GCM in modalità streaming**: il file viene letto a blocchi da 1 MiB,
ognuno cifrato e autenticato singolarmente, così anche backup di grandi
dimensioni non vengono caricati interamente in memoria.

La chiave (32 byte) è custodita nel **keyring di sistema**: un file ``.enc``
sottratto (USB, disco rubato, copia di rete) è inutilizzabile senza accesso al
keyring della macchina su cui è stato creato. La protezione *non* dipende
quindi dalla posizione del file di backup.

Formato del file cifrato::

    MAGIC (10 byte)
    poi, ripetuto per ogni blocco fino a EOF:
        nonce (12 byte)
        ct_len (4 byte, uint32 big-endian)
        ciphertext (ct_len byte, include il tag GCM da 16 byte)

``ciphertext = AESGCM(key).encrypt(nonce, plaintext_chunk, MAGIC)`` — MAGIC è
usato come *associated data*, così l'intestazione è autenticata insieme ai dati.
"""
from __future__ import annotations

import base64
import os
import struct
import tempfile
from typing import Optional

MAGIC = b"FLRBKENC1\n"
_CHUNK = 1024 * 1024          # 1 MiB di plaintext per blocco
_NONCE_LEN = 12
_KEY_BYTES = 32               # AES-256
_LEN_STRUCT = struct.Struct(">I")

#: Suffisso aggiunto ai backup cifrati.
ENC_SUFFIX = ".enc"

#: Coordinate della chiave nel keyring di sistema.
KEYRING_SERVICE = "Foliarium_BackupKey"
KEYRING_USERNAME = "backup"


class BackupCryptoError(RuntimeError):
    """Errore di cifratura/decifratura o di gestione della chiave di backup."""


def is_available() -> bool:
    """True se le dipendenze (cryptography + keyring) sono disponibili."""
    try:
        import cryptography  # noqa: F401
        import keyring  # noqa: F401
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Gestione chiave (keyring)
# ---------------------------------------------------------------------------

def generate_key() -> bytes:
    """Genera una nuova chiave AES-256 casuale."""
    return os.urandom(_KEY_BYTES)


def get_backup_key(create: bool = True) -> bytes:
    """Recupera la chiave di backup dal keyring.

    Args:
        create: se True (default) genera e memorizza una nuova chiave quando
            non ne esiste ancora una. Se False solleva ``BackupCryptoError``.
    """
    import keyring
    raw = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
    if raw:
        try:
            key = base64.b64decode(raw)
        except Exception as e:  # base64 corrotto
            raise BackupCryptoError("Chiave di backup nel keyring corrotta.") from e
        if len(key) != _KEY_BYTES:
            raise BackupCryptoError("Chiave di backup nel keyring di lunghezza non valida.")
        return key
    if not create:
        raise BackupCryptoError(
            "Nessuna chiave di backup trovata nel keyring: impossibile decifrare."
        )
    key = generate_key()
    keyring.set_password(
        KEYRING_SERVICE, KEYRING_USERNAME, base64.b64encode(key).decode("ascii")
    )
    return key


# ---------------------------------------------------------------------------
# Cifratura / decifratura streaming
# ---------------------------------------------------------------------------

def _aesgcm(key: bytes):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    if len(key) != _KEY_BYTES:
        raise BackupCryptoError("Chiave di lunghezza non valida (attesi 32 byte).")
    return AESGCM(key)


def is_encrypted_file(path: str) -> bool:
    """True se il file inizia con il magic dei backup cifrati Foliarium."""
    try:
        with open(path, "rb") as f:
            return f.read(len(MAGIC)) == MAGIC
    except OSError:
        return False


def encrypt_file(src_path: str, dst_path: str, key: bytes) -> None:
    """Cifra ``src_path`` scrivendo il risultato in ``dst_path``."""
    aes = _aesgcm(key)
    try:
        with open(src_path, "rb") as fin, open(dst_path, "wb") as fout:
            fout.write(MAGIC)
            while True:
                chunk = fin.read(_CHUNK)
                if not chunk:
                    break
                nonce = os.urandom(_NONCE_LEN)
                ct = aes.encrypt(nonce, chunk, MAGIC)
                fout.write(nonce)
                fout.write(_LEN_STRUCT.pack(len(ct)))
                fout.write(ct)
            fout.flush()
            os.fsync(fout.fileno())
    except OSError as e:
        raise BackupCryptoError(f"Errore I/O durante la cifratura: {e}") from e


def decrypt_file(src_path: str, dst_path: str, key: bytes) -> None:
    """Decifra ``src_path`` (prodotto da :func:`encrypt_file`) in ``dst_path``.

    Solleva ``BackupCryptoError`` se la chiave è errata, il file è manomesso o
    troncato.
    """
    from cryptography.exceptions import InvalidTag
    aes = _aesgcm(key)
    try:
        with open(src_path, "rb") as fin, open(dst_path, "wb") as fout:
            if fin.read(len(MAGIC)) != MAGIC:
                raise BackupCryptoError(
                    "File non riconosciuto come backup Foliarium cifrato."
                )
            while True:
                nonce = fin.read(_NONCE_LEN)
                if not nonce:
                    break  # EOF pulito
                if len(nonce) != _NONCE_LEN:
                    raise BackupCryptoError("File cifrato troncato (nonce).")
                len_bytes = fin.read(_LEN_STRUCT.size)
                if len(len_bytes) != _LEN_STRUCT.size:
                    raise BackupCryptoError("File cifrato troncato (lunghezza blocco).")
                (ct_len,) = _LEN_STRUCT.unpack(len_bytes)
                ct = fin.read(ct_len)
                if len(ct) != ct_len:
                    raise BackupCryptoError("File cifrato troncato (dati blocco).")
                try:
                    pt = aes.decrypt(nonce, ct, MAGIC)
                except InvalidTag as e:
                    raise BackupCryptoError(
                        "Decifratura fallita: chiave errata o file manomesso."
                    ) from e
                fout.write(pt)
    except OSError as e:
        raise BackupCryptoError(f"Errore I/O durante la decifratura: {e}") from e


# ---------------------------------------------------------------------------
# Helper di alto livello (usati dalla GUI di backup)
# ---------------------------------------------------------------------------

def secure_delete(path: str) -> None:
    """Sovrascrive (best-effort) e rimuove un file di plaintext.

    Su SSD/flash la sovrascrittura non è garantita (wear-leveling): la vera
    protezione resta la cifratura + la chiave nel keyring. Si raccomanda
    comunque il full-disk-encryption della macchina.
    """
    try:
        if not os.path.isfile(path):
            return
        size = os.path.getsize(path)
        with open(path, "r+b", buffering=0) as f:
            written = 0
            while written < size:
                block = os.urandom(min(_CHUNK, size - written))
                f.write(block)
                written += len(block)
            f.flush()
            os.fsync(f.fileno())
    except OSError:
        pass
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def encrypt_backup(plaintext_path: str, *, remove_plaintext: bool = True,
                   key: Optional[bytes] = None) -> str:
    """Cifra un backup appena prodotto.

    Returns:
        Il percorso del file cifrato (``<plaintext_path>.enc``).
    """
    if key is None:
        key = get_backup_key(create=True)
    enc_path = plaintext_path + ENC_SUFFIX
    encrypt_file(plaintext_path, enc_path, key)
    if remove_plaintext:
        secure_delete(plaintext_path)
    return enc_path


def decrypt_backup_to_temp(enc_path: str, *, key: Optional[bytes] = None) -> str:
    """Decifra un backup cifrato in un file temporaneo per il ripristino.

    Il chiamante è responsabile della rimozione del file temporaneo (usare
    :func:`secure_delete`) al termine del ripristino.
    """
    if key is None:
        key = get_backup_key(create=False)
    base = enc_path[:-len(ENC_SUFFIX)] if enc_path.endswith(ENC_SUFFIX) else enc_path
    suffix = os.path.splitext(base)[1] or ".dump"
    fd, tmp = tempfile.mkstemp(prefix="foliarium_restore_", suffix=suffix)
    os.close(fd)
    try:
        decrypt_file(enc_path, tmp, key)
    except Exception:
        secure_delete(tmp)
        raise
    return tmp


__all__ = [
    "BackupCryptoError", "ENC_SUFFIX", "KEYRING_SERVICE", "KEYRING_USERNAME",
    "is_available", "generate_key", "get_backup_key",
    "is_encrypted_file", "encrypt_file", "decrypt_file",
    "secure_delete", "encrypt_backup", "decrypt_backup_to_temp",
]
