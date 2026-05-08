"""
license_manager.py — Gestione licenze Foliarium

Formato del file .license (JSON firmato con HMAC-SHA256):
  {
    "licensed_to":  "Nome Cliente",
    "license_type": "standard",          // "demo" | "standard" | "enterprise"
    "max_seats":    2,                   // istanze simultanee consentite in rete
    "expiry_date":  "2027-12-31",        // null = licenza perpetua
    "hardware_id":  "a1b2c3d4e5f6g7h8", // null = floating (qualsiasi PC)
    "issued_at":    "2025-01-01",
    "signature":    "<hmac-sha256-hex>"
  }

Uso tipico:
  from foliarium.core.services.license import LicenseManager
  lm = LicenseManager()
  info = lm.validate()
  if not info.is_valid:
      show_error(info.error_message)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import socket
import time
import uuid
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

logger = logging.getLogger("CatastoGUI")


def _load_hmac_key() -> bytes:
    """
    Carica la chiave HMAC da sorgente esterna. Non deve mai essere hardcoded.

    Ordine di ricerca:
      1. Variabile d'ambiente FOLIARIUM_LICENSE_KEY
      2. File 'foliarium.key' nella directory dell'eseguibile (EXE_DIR)

    Raises:
        RuntimeError: se nessuna sorgente è disponibile.
    """
    env_key = os.environ.get("FOLIARIUM_LICENSE_KEY", "").strip()
    if env_key:
        return env_key.encode("utf-8")

    try:
        from app_paths import EXE_DIR
        key_file = Path(EXE_DIR) / "foliarium.key"
        if key_file.exists():
            data = key_file.read_bytes().strip()
            if data:
                return data
    except Exception as e:
        logger.debug("Impossibile leggere foliarium.key: %s", e)

    raise RuntimeError(
        "Chiave di licenza non trovata. "
        "Impostare la variabile d'ambiente FOLIARIUM_LICENSE_KEY "
        "oppure fornire il file foliarium.key nella cartella dell'eseguibile."
    )


# Durata massima (secondi) prima che un file-seat venga considerato stale
_SEAT_TTL_SECONDS = 120
# Intervallo di refresh del seat mentre l'app è aperta
_SEAT_REFRESH_INTERVAL_MS = 60_000  # 1 minuto


# ---------------------------------------------------------------------------
# Struttura dati licenza
# ---------------------------------------------------------------------------

@dataclass
class LicenseInfo:
    licensed_to: str
    license_type: str          # "demo" | "standard" | "enterprise"
    max_seats: int
    expiry_date: Optional[date]
    hardware_id: Optional[str]
    issued_at: date
    is_valid: bool = False
    error_message: str = ""

    def is_demo(self) -> bool:
        return self.license_type == "demo"

    def is_perpetual(self) -> bool:
        return self.expiry_date is None

    def days_to_expiry(self) -> Optional[int]:
        if self.expiry_date is None:
            return None
        return (self.expiry_date - date.today()).days


# ---------------------------------------------------------------------------
# Funzioni di basso livello
# ---------------------------------------------------------------------------

def get_hardware_fingerprint() -> str:
    """Fingerprint basato su MAC address + hostname (SHA-256 troncato a 16 hex)."""
    try:
        mac = uuid.getnode()
        hostname = socket.gethostname()
        raw = f"{mac}:{hostname}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:16]
    except Exception:
        return "unknown"


def _sign_payload(payload: dict) -> str:
    """Calcola la firma HMAC-SHA256 del payload (senza campo 'signature')."""
    payload_bytes = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hmac.new(_load_hmac_key(), payload_bytes, hashlib.sha256).hexdigest()


def generate_license(
    licensed_to: str,
    license_type: str = "standard",
    max_seats: int = 1,
    expiry_date: Optional[str] = None,
    hardware_id: Optional[str] = None,
) -> str:
    """
    Genera il contenuto JSON di un file di licenza firmato.
    Da usare SOLO internamente per emettere licenze ai clienti.
    """
    payload: dict = {
        "licensed_to": licensed_to,
        "license_type": license_type,
        "max_seats": max_seats,
        "expiry_date": expiry_date,
        "hardware_id": hardware_id,
        "issued_at": date.today().isoformat(),
    }
    payload["signature"] = _sign_payload(payload)
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _validate_file(license_path: str) -> LicenseInfo:
    """Carica e valida il file .license, restituisce un LicenseInfo."""
    try:
        with open(license_path, "r", encoding="utf-8") as f:
            data: dict = json.load(f)
    except FileNotFoundError:
        return LicenseInfo("", "standard", 1, None, None, date.today(),
                           False, "File di licenza non trovato")
    except (json.JSONDecodeError, OSError) as e:
        return LicenseInfo("", "standard", 1, None, None, date.today(),
                           False, f"File di licenza non leggibile: {e}")

    # --- Verifica firma ---
    signature = data.pop("signature", None)
    expected = _sign_payload(data)
    if not signature or not hmac.compare_digest(signature, expected):
        return LicenseInfo("", "standard", 1, None, None, date.today(),
                           False, "Firma del file di licenza non valida")
    data["signature"] = signature  # ripristina per uso successivo

    # --- Verifica hardware ID ---
    hw_id: Optional[str] = data.get("hardware_id")
    if hw_id:
        current_hw = get_hardware_fingerprint()
        if hw_id != current_hw:
            return LicenseInfo(
                data.get("licensed_to", ""),
                data.get("license_type", "standard"),
                data.get("max_seats", 1),
                None, hw_id, date.today(),
                False,
                f"Licenza non valida per questo computer\n"
                f"(ID atteso: {hw_id}, ID attuale: {current_hw})"
            )

    # --- Verifica scadenza ---
    expiry_str: Optional[str] = data.get("expiry_date")
    expiry_date: Optional[date] = None
    if expiry_str:
        try:
            expiry_date = date.fromisoformat(expiry_str)
            if expiry_date < date.today():
                return LicenseInfo(
                    data.get("licensed_to", ""),
                    data.get("license_type", "standard"),
                    data.get("max_seats", 1),
                    expiry_date, hw_id, date.today(),
                    False,
                    f"Licenza scaduta il {expiry_date.strftime('%d/%m/%Y')}"
                )
        except ValueError:
            pass

    issued_str: str = data.get("issued_at", date.today().isoformat())
    try:
        issued_date = date.fromisoformat(issued_str)
    except ValueError:
        issued_date = date.today()

    return LicenseInfo(
        licensed_to=data.get("licensed_to", ""),
        license_type=data.get("license_type", "standard"),
        max_seats=data.get("max_seats", 1),
        expiry_date=expiry_date,
        hardware_id=hw_id,
        issued_at=issued_date,
        is_valid=True,
    )


# ---------------------------------------------------------------------------
# Gestione seat di rete (file-lock su cartella condivisa)
# ---------------------------------------------------------------------------

def _seat_file_path(share_path: str, instance_id: str) -> Path:
    hostname = socket.gethostname()
    return Path(share_path) / f"foliarium_seat_{hostname}_{instance_id}.json"


def _count_active_seats(share_path: str) -> int:
    """Conta i file-seat validi (non stale) nella condivisione."""
    now = time.time()
    count = 0
    try:
        for p in Path(share_path).glob("foliarium_seat_*.json"):
            try:
                with open(p, "r") as f:
                    seat = json.load(f)
                if now - seat.get("ts", 0) <= _SEAT_TTL_SECONDS:
                    count += 1
                else:
                    # Pulisce il file stale
                    p.unlink(missing_ok=True)
            except Exception:
                pass
    except Exception as e:
        logger.debug(f"[LicenseManager] Impossibile leggere la share '{share_path}': {e}")
    return count


def acquire_network_seat(share_path: str, instance_id: str) -> tuple[bool, int, int]:
    """
    Prova ad acquisire un seat nella cartella condivisa.

    Returns:
        (success, seats_in_use, max_seats_from_caller)
        max_seats_from_caller non viene usato qui; la caller passa max_seats dalla licenza.
    """
    if not share_path:
        return True, 1, 1
    try:
        Path(share_path).mkdir(parents=True, exist_ok=True)
        current = _count_active_seats(share_path)
        seat_file = _seat_file_path(share_path, instance_id)
        # Scrivi comunque il seat (la caller decide se bloccare in base a max_seats)
        with open(seat_file, "w") as f:
            json.dump({"ts": time.time(), "host": socket.gethostname(),
                       "pid": os.getpid()}, f)
        return True, current + 1, 0
    except Exception as e:
        logger.warning(f"[LicenseManager] acquire_network_seat fallito: {e}")
        return True, 1, 0   # fail-open: non blocca l'avvio se la share non è raggiungibile


def release_network_seat(share_path: str, instance_id: str) -> None:
    """Elimina il file-seat al logout / chiusura dell'app."""
    if not share_path:
        return
    try:
        _seat_file_path(share_path, instance_id).unlink(missing_ok=True)
    except Exception as e:
        logger.debug(f"[LicenseManager] release_network_seat: {e}")


def refresh_network_seat(share_path: str, instance_id: str) -> None:
    """Aggiorna il timestamp del file-seat (chiamato periodicamente)."""
    if not share_path:
        return
    try:
        seat_file = _seat_file_path(share_path, instance_id)
        if seat_file.exists():
            with open(seat_file, "r") as f:
                seat = json.load(f)
            seat["ts"] = time.time()
            with open(seat_file, "w") as f:
                json.dump(seat, f)
    except Exception as e:
        logger.debug(f"[LicenseManager] refresh_network_seat: {e}")


# ---------------------------------------------------------------------------
# Classe principale
# ---------------------------------------------------------------------------

class LicenseManager:
    """
    Punto di accesso unico per la gestione della licenza.

    Uso:
        lm = LicenseManager()
        info = lm.validate()
        if not info.is_valid:
            ...
        # Al login:
        ok, seats_used, _ = lm.acquire_seat()
        # Alla chiusura:
        lm.release_seat()
    """

    def __init__(self):
        from config import SETTINGS_LICENSE_FILE_PATH, SETTINGS_LICENSE_NETWORK_SHARE, \
            LICENSE_DEFAULT_FILENAME, IS_DEMO_MODE
        from app_paths import BASE_DIR, EXE_DIR
        from PyQt6.QtCore import QSettings

        settings = QSettings()
        # Percorso file licenza: da QSettings → accanto all'eseguibile → _internal/ → directory corrente
        # IMPORTANTE: in PyInstaller 'onedir' il file .license sta ACCANTO a Foliarium.exe
        # (EXE_DIR), NON dentro _internal/ (BASE_DIR).
        saved_path = settings.value(SETTINGS_LICENSE_FILE_PATH, "", type=str)
        if saved_path and os.path.exists(saved_path):
            self.license_path = saved_path
        else:
            # Cerca prima accanto all'eseguibile, poi come fallback in BASE_DIR (dev mode / legacy)
            exe_path = Path(EXE_DIR) / LICENSE_DEFAULT_FILENAME
            base_path = Path(BASE_DIR) / LICENSE_DEFAULT_FILENAME
            if exe_path.exists():
                self.license_path = str(exe_path)
            elif base_path.exists():
                self.license_path = str(base_path)
            else:
                # Nessun file trovato: usa il percorso atteso (accanto all'exe) per il messaggio d'errore
                self.license_path = saved_path or str(exe_path)

        self.share_path: str = settings.value(SETTINGS_LICENSE_NETWORK_SHARE, "", type=str)
        self._instance_id: str = str(uuid.uuid4())[:8]
        self._info: Optional[LicenseInfo] = None
        self._is_demo = IS_DEMO_MODE

    def validate(self) -> LicenseInfo:
        """
        Valida la licenza.  In modalità demo restituisce sempre una licenza demo valida.
        """
        if self._is_demo:
            self._info = LicenseInfo(
                licensed_to="Versione Demo",
                license_type="demo",
                max_seats=1,
                expiry_date=None,
                hardware_id=None,
                issued_at=date.today(),
                is_valid=True,
            )
            return self._info

        self._info = _validate_file(self.license_path)
        return self._info

    def acquire_seat(self) -> tuple[bool, int, int]:
        """
        Acquisisce un seat di rete.  Ritorna (allowed, seats_in_use, max_seats).
        allowed=False se max_seats è già raggiunto.
        """
        if self._info is None:
            self._info = self.validate()
        if not self._info.is_valid:
            return False, 0, 0
        max_seats = self._info.max_seats
        ok, seats_used, _ = acquire_network_seat(self.share_path, self._instance_id)
        allowed = seats_used <= max_seats
        if not allowed:
            logger.warning(
                f"[LicenseManager] Numero massimo di istanze raggiunto "
                f"({seats_used}/{max_seats})"
            )
            release_network_seat(self.share_path, self._instance_id)
        return allowed, seats_used, max_seats

    def release_seat(self) -> None:
        release_network_seat(self.share_path, self._instance_id)

    def refresh_seat(self) -> None:
        refresh_network_seat(self.share_path, self._instance_id)

    @property
    def info(self) -> Optional[LicenseInfo]:
        return self._info

    @property
    def instance_id(self) -> str:
        return self._instance_id
