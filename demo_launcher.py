"""
demo_launcher.py — Gestione PostgreSQL portabile per la versione Demo di Foliarium

Struttura attesa accanto a Foliarium_Demo.exe:
  pgsql/
    bin/
      pg_ctl.exe
      pg_isready.exe
      postgres.exe
    lib/
      ...
  demo_data/          ← cartella dati PostgreSQL pre-inizializzata
    postgresql.conf
    pg_hba.conf
    base/
    ...

Al primo avvio, se demo_data/ è in sola lettura (es. estratto su CD/USB
protetto), viene copiato in %LOCALAPPDATA%\\Foliarium\\demo_data.

Porta usata: 15432 (evita conflitti con PostgreSQL eventualmente installato).
"""
from __future__ import annotations

import atexit
import logging
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger("CatastoGUI")

# Porta dedicata alla demo (non standard — evita conflitti con PG in produzione)
DEMO_PG_PORT = 15432
# Utente superuser del PostgreSQL portabile
DEMO_PG_SUPERUSER = "postgres"
# Secondi max di attesa per l'avvio del server
_STARTUP_TIMEOUT = 30
# Nome del processo pg_ctl su Windows
_PG_CTL = "pg_ctl.exe" if platform.system() == "Windows" else "pg_ctl"
_PG_ISREADY = "pg_isready.exe" if platform.system() == "Windows" else "pg_isready"

# Flag per nascondere la finestra console nera su Windows
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0


# ---------------------------------------------------------------------------
# Risoluzione dei percorsi
# ---------------------------------------------------------------------------

def _bundle_root() -> Path:
    """
    Radice del bundle: directory dell'eseguibile (build PyInstaller one-dir)
    oppure directory del file sorgente (sviluppo).
    """
    if getattr(sys, "frozen", False):
        # PyInstaller one-dir: sys.executable è Foliarium_Demo.exe
        return Path(sys.executable).parent
    return Path(__file__).parent


def _pgsql_bin() -> Optional[Path]:
    """Percorso della directory bin/ di PostgreSQL portabile."""
    candidate = _bundle_root() / "pgsql" / "bin"
    if candidate.exists():
        return candidate
    return None


def _default_data_dir_source() -> Path:
    """Cartella demo_data/ nel bundle (può essere in sola lettura)."""
    return _bundle_root() / "demo_data"


def _writable_data_dir() -> Path:
    """
    Cartella dati PostgreSQL scrivibile.
    Se demo_data/ nel bundle è in sola lettura, usa
    %LOCALAPPDATA%\\Foliarium\\demo_data  (Windows)
    ~/.local/share/Foliarium/demo_data    (Linux/Mac)
    """
    src = _default_data_dir_source()

    # Controlla se è scrivibile tentando di creare un file temporaneo
    try:
        test = src / ".write_test"
        test.touch()
        test.unlink()
        return src  # scrivibile: usa direttamente
    except (OSError, PermissionError):
        pass

    # Fallback: copia in AppData locale
    if platform.system() == "Windows":
        appdata = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        appdata = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    dest = appdata / "Foliarium" / "demo_data"

    if not dest.exists():
        logger.info(f"[DemoLauncher] Copia demo_data in {dest} (bundle in sola lettura)")
        shutil.copytree(str(src), str(dest))

    return dest


# ---------------------------------------------------------------------------
# Avvio / arresto PostgreSQL
# ---------------------------------------------------------------------------

class EmbeddedPostgres:
    """Gestisce il ciclo di vita del PostgreSQL portabile."""

    def __init__(self):
        self._data_dir: Optional[Path] = None
        self._port: int = DEMO_PG_PORT
        self._started: bool = False

    # ------------------------------------------------------------------
    def start(self) -> Tuple[bool, str]:
        """
        Avvia il server PostgreSQL.
        Restituisce (successo, messaggio_errore).
        """
        pg_bin = _pgsql_bin()
        if pg_bin is None:
            return False, (
                "PostgreSQL portabile non trovato nel bundle demo.\n"
                "Assicurati che la cartella 'pgsql/' sia presente\n"
                "accanto a Foliarium_Demo.exe."
            )

        src_data = _default_data_dir_source()
        if not src_data.exists():
            return False, (
                "Cartella dati demo non trovata nel bundle.\n"
                f"Percorso atteso: {src_data}"
            )

        try:
            self._data_dir = _writable_data_dir()
        except Exception as e:
            return False, f"Impossibile preparare la cartella dati demo:\n{e}"

        pg_ctl = pg_bin / _PG_CTL
        log_file = self._data_dir / "pg_demo.log"

        logger.info(f"[DemoLauncher] Avvio PostgreSQL portabile (porta {self._port})…")
        logger.info(f"[DemoLauncher]   data_dir = {self._data_dir}")
        logger.info(f"[DemoLauncher]   pg_ctl   = {pg_ctl}")

        try:
            result = subprocess.run(
                [
                    str(pg_ctl), "start",
                    "-D", str(self._data_dir),
                    "-l", str(log_file),
                    "-w",           # attende che il server sia pronto
                    "-t", str(_STARTUP_TIMEOUT),
                    "-o", f"-p {self._port} -h 127.0.0.1",
                ],
                capture_output=True,
                text=True,
                timeout=_STARTUP_TIMEOUT + 5,
                creationflags=_NO_WINDOW,
            )
        except subprocess.TimeoutExpired:
            return False, "Timeout: PostgreSQL demo non si è avviato in tempo."
        except FileNotFoundError:
            return False, f"Eseguibile non trovato: {pg_ctl}"
        except Exception as e:
            return False, f"Errore avvio PostgreSQL: {e}"

        if result.returncode not in (0, 1):   # 1 = già in esecuzione
            stderr = result.stderr.strip() or result.stdout.strip()
            return False, f"pg_ctl start fallito (codice {result.returncode}):\n{stderr}"

        # Verifica finale con pg_isready
        ok = self._wait_ready(pg_bin)
        if not ok:
            return False, "PostgreSQL demo avviato ma non risponde. Controlla pg_demo.log."

        self._started = True
        logger.info(f"[DemoLauncher] PostgreSQL demo pronto su 127.0.0.1:{self._port}")
        atexit.register(self.stop)
        return True, ""

    # ------------------------------------------------------------------
    def stop(self) -> None:
        """Ferma il server PostgreSQL (fast shutdown)."""
        if not self._started or self._data_dir is None:
            return
        pg_bin = _pgsql_bin()
        if pg_bin is None:
            return
        pg_ctl = pg_bin / _PG_CTL
        logger.info("[DemoLauncher] Arresto PostgreSQL demo…")
        try:
            subprocess.run(
                [str(pg_ctl), "stop", "-D", str(self._data_dir), "-m", "fast"],
                capture_output=True,
                timeout=15,
                creationflags=_NO_WINDOW,
            )
        except Exception as e:
            logger.warning(f"[DemoLauncher] Errore arresto PostgreSQL: {e}")
        self._started = False

    # ------------------------------------------------------------------
    def _wait_ready(self, pg_bin: Path, attempts: int = 20) -> bool:
        """Poll pg_isready fino a che il server accetta connessioni."""
        pg_isready = pg_bin / _PG_ISREADY
        for _ in range(attempts):
            try:
                r = subprocess.run(
                    [str(pg_isready), "-h", "127.0.0.1", "-p", str(self._port)],
                    capture_output=True,
                    timeout=2,
                    creationflags=_NO_WINDOW,
                )
                if r.returncode == 0:
                    return True
            except Exception:
                pass
            time.sleep(0.5)
        return False

    # ------------------------------------------------------------------
    @property
    def port(self) -> int:
        return self._port

    @property
    def is_running(self) -> bool:
        return self._started


# Istanza singleton usata da gui_main.py
_embedded_pg: Optional[EmbeddedPostgres] = None


def start_demo_postgres() -> Tuple[bool, str]:
    """
    Avvia PostgreSQL portabile e aggiorna le variabili d'ambiente DEMO_DB_*.
    Chiamato da gui_main.run_gui_app() prima della connessione al DB demo.

    Returns: (successo, messaggio_errore)
    """
    global _embedded_pg
    _embedded_pg = EmbeddedPostgres()
    ok, err = _embedded_pg.start()
    if ok:
        # Aggiorna le env var in modo che config.py le legga correttamente
        os.environ["DEMO_DB_HOST"] = "127.0.0.1"
        os.environ["DEMO_DB_PORT"] = str(_embedded_pg.port)
        os.environ["DEMO_DB_NAME"] = "catasto_storico"
        os.environ["DEMO_DB_USER"] = "demo_user"
        # La password è già in DEMO_DB_PASS oppure al default
        if not os.environ.get("DEMO_DB_PASS"):
            os.environ["DEMO_DB_PASS"] = "demo2025"
    return ok, err


def stop_demo_postgres() -> None:
    """Ferma il PostgreSQL portabile. Chiamato dal closeEvent della finestra."""
    global _embedded_pg
    if _embedded_pg:
        _embedded_pg.stop()
        _embedded_pg = None


def is_embedded_available() -> bool:
    """True se il bundle contiene il PostgreSQL portabile."""
    return _pgsql_bin() is not None and _default_data_dir_source().exists()
