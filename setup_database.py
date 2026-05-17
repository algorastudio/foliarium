#!/usr/bin/env python3
"""
setup_database.py — Inizializzazione cross-platform di PostgreSQL per Foliarium.

Funziona su Windows, Linux e macOS. Eseguito automaticamente dall'installer
o manualmente dopo l'estrazione del pacchetto.

Operazioni (modalità bundle — pgsql/ incluso nell'installer):
  1. Rileva la porta libera (5432, 5433, 5434)
  2. initdb — crea cluster PostgreSQL in pg_data/
  3. Configura pg_hba.conf (scram-sha-256) e postgresql.conf
  4. Registra come servizio (Windows Service / systemd / launchd)
  5. Avvia il servizio e attende che sia pronto
  6. Crea ruolo applicativo e database catasto_storico
  7. Esegue gli script SQL (schema, procedure, user management)
  8. Scrive config.ini con le credenziali generate

Modalità sviluppo (PostgreSQL di sistema già installato):
  python setup_database.py --pg-bin "C:\\Program Files\\PostgreSQL\\16\\bin"
  python setup_database.py --pg-bin auto            # ricerca automatica nel PATH
  python setup_database.py --pg-bin auto --admin-password MiaPass

  Usa un PostgreSQL già in esecuzione: salta initdb, pg_ctl e registrazione
  servizio. Richiede che postgres sia raggiungibile su 127.0.0.1:5432 senza
  password (trust) o con la password passata via --postgres-password.

Uso (modalità bundle):
  python setup_database.py                        # auto-detect install_dir
  python setup_database.py --install-dir /opt/foliarium
  python setup_database.py --db-password MyPass   # password specifica
  python setup_database.py --skip-service         # no servizio, solo DB
  python setup_database.py --uninstall            # rimuove servizio e dati
"""
from __future__ import annotations

import argparse
import configparser
import os
import platform
import secrets
import shutil
import socket
import string
import subprocess
import sys
import textwrap
import time
from pathlib import Path

# ============================================================================
# Costanti
# ============================================================================
DB_NAME = "catasto_storico"
DB_USER = "foliarium"
SERVICE_NAME = "FoliariumDB"
DEFAULT_PORT = 5432

SYSTEM = platform.system()  # "Windows", "Linux", "Darwin"
IS_WIN = SYSTEM == "Windows"
IS_MAC = SYSTEM == "Darwin"
IS_LINUX = SYSTEM == "Linux"
EXE = ".exe" if IS_WIN else ""

# Ordine di applicazione su DB fresco. Il bootstrap admin (07a) e' gestito
# a parte perche' richiede la variabile psql admin_password (vedi codice).
# Da v1.0.0: lookup tipo_possesso/tipo_localita, soft-delete e tabella sessioni
# sono integrati in 02 e 07_user-management (vedi sql_scripts/README.md).
SQL_SCRIPTS = [
    "schema/01_tables.sql",
    "functions/01_core.sql",
    "functions/02_crud.sql",
    "functions/03_workflow.sql",
    "functions/04_search.sql",
    "functions/05_reporting.sql",
    "functions/06_audit.sql",
    "functions/07_features.sql",
    "admin/01_users.sql",
    "admin/02_backup.sql",
    "admin/03_performance.sql",
    "schema/02_trigram_indexes.sql",  # CONCURRENTLY: deve stare fuori transazione
]

BOOTSTRAP_ADMIN_SCRIPT = "admin/04_bootstrap_admin.sql"


# ============================================================================
# Utilità
# ============================================================================

def find_system_pgbin() -> Path | None:
    """Cerca psql nel PATH o nelle posizioni comuni su Windows/Linux/macOS."""
    found = shutil.which("psql")
    if found:
        return Path(found).parent
    if IS_WIN:
        for ver in range(20, 13, -1):
            for base in [r"C:\Program Files\PostgreSQL", r"C:\Program Files (x86)\PostgreSQL"]:
                candidate = Path(base) / str(ver) / "bin"
                if (candidate / "psql.exe").exists():
                    return candidate
    return None


def log(msg: str) -> None:
    print(f"  {msg}", flush=True)


def run(cmd: list, **kw) -> subprocess.CompletedProcess:
    """Esegue un comando e logga. Su errore, stampa stdout/stderr catturati."""
    display = " ".join(str(c) for c in cmd)
    log(f"$ {display}")
    try:
        return subprocess.run(cmd, check=True, **kw)
    except subprocess.CalledProcessError as e:
        # Se l'output era catturato, mostralo per non perdere il messaggio reale
        if e.stdout:
            sys.stdout.write(e.stdout.decode(errors="replace") if isinstance(e.stdout, bytes) else e.stdout)
        if e.stderr:
            sys.stderr.write(e.stderr.decode(errors="replace") if isinstance(e.stderr, bytes) else e.stderr)
        raise


def run_quiet(cmd: list, **kw) -> subprocess.CompletedProcess:
    """Esegue un comando senza check, catturando output."""
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def exe(pg_bin: Path, name: str) -> str:
    """Ritorna il percorso completo dell'eseguibile PostgreSQL."""
    return str(pg_bin / f"{name}{EXE}")


def generate_password(length: int = 16) -> str:
    """Genera una password casuale alfanumerica."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def find_free_port(start: int = 5432, attempts: int = 3) -> int:
    """Trova la prima porta libera partendo da start."""
    for port in range(start, start + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                log(f"Porta {port} occupata, provo la successiva...")
    # Fallback: restituisce la porta di partenza
    return start


def wait_ready(pg_bin: Path, port: int, attempts: int = 30) -> bool:
    """Attende che PostgreSQL sia pronto."""
    pg_isready = exe(pg_bin, "pg_isready")
    for i in range(attempts):
        r = run_quiet([pg_isready, "-h", "127.0.0.1", "-p", str(port)])
        if r.returncode == 0:
            return True
        log(f"Attesa server... ({i+1}/{attempts})")
        time.sleep(1)
    return False


def run_psql(pg_bin: Path, port: int, sql: str,
             dbname: str = "postgres", password: str = "") -> None:
    """Esegue SQL tramite psql."""
    env = os.environ.copy()
    env["PGPASSWORD"] = password
    run(
        [exe(pg_bin, "psql"), "-h", "127.0.0.1", "-p", str(port),
         "-U", "postgres", "-d", dbname, "-c", sql],
        env=env, capture_output=True,
    )


def run_psql_file(pg_bin: Path, port: int, sql_file: Path,
                  dbname: str = "postgres", password: str = "",
                  variables: dict | None = None) -> None:
    """Esegue un file SQL tramite psql, opzionalmente con variabili -v."""
    env = os.environ.copy()
    env["PGPASSWORD"] = password
    cmd = [exe(pg_bin, "psql"), "-h", "127.0.0.1", "-p", str(port),
           "-U", "postgres", "-d", dbname]
    for k, v in (variables or {}).items():
        # psql -v admin_password=valore  → variabile letterale "valore",
        # poi :'admin_password' nel file aggiunge le virgolette per il SQL.
        # NB: NON usare repr() qui, altrimenti la quotatura diventa doppia.
        cmd += ["-v", f"{k}={v}"]
    cmd += ["-f", str(sql_file)]
    run(cmd, env=env, capture_output=True)


# ============================================================================
# Gestione servizi per piattaforma
# ============================================================================

def register_service_windows(pg_bin: Path, pg_data: Path) -> bool:
    """Registra PostgreSQL come servizio Windows."""
    # Rimuovi servizio esistente se presente
    r = run_quiet(["sc", "query", SERVICE_NAME])
    if r.returncode == 0:
        run_quiet(["net", "stop", SERVICE_NAME])
        time.sleep(2)
        run_quiet(["sc", "delete", SERVICE_NAME])
        time.sleep(2)

    r = run_quiet([exe(pg_bin, "pg_ctl"), "register",
                   "-N", SERVICE_NAME, "-D", str(pg_data), "-S", "auto"])
    if r.returncode == 0:
        log(f"Servizio Windows '{SERVICE_NAME}' registrato (avvio automatico).")
        return True
    log(f"Registrazione servizio fallita: {r.stderr}")
    return False


def start_service_windows() -> bool:
    """Avvia il servizio Windows."""
    r = run_quiet(["net", "start", SERVICE_NAME])
    return r.returncode == 0


def unregister_service_windows(pg_bin: Path) -> None:
    """Ferma e rimuove il servizio Windows."""
    run_quiet(["net", "stop", SERVICE_NAME])
    time.sleep(3)
    run_quiet([exe(pg_bin, "pg_ctl"), "unregister", "-N", SERVICE_NAME])
    if run_quiet(["sc", "query", SERVICE_NAME]).returncode == 0:
        run_quiet(["sc", "delete", SERVICE_NAME])


def register_service_linux(pg_bin: Path, pg_data: Path, port: int) -> bool:
    """Crea e abilita un'unità systemd per PostgreSQL."""
    unit_name = f"{SERVICE_NAME.lower()}.service"
    unit_path = Path(f"/etc/systemd/system/{unit_name}")

    # Determina l'utente che eseguirà postgres
    pg_user = os.environ.get("SUDO_USER", os.environ.get("USER", "postgres"))

    unit_content = textwrap.dedent(f"""\
        [Unit]
        Description=Foliarium PostgreSQL Database Server
        After=network.target

        [Service]
        Type=forking
        User={pg_user}
        ExecStart={exe(pg_bin, 'pg_ctl')} start -D {pg_data} -l {pg_data}/postgresql.log -w
        ExecStop={exe(pg_bin, 'pg_ctl')} stop -D {pg_data} -m fast
        ExecReload={exe(pg_bin, 'pg_ctl')} reload -D {pg_data}
        TimeoutSec=30
        Restart=on-failure

        [Install]
        WantedBy=multi-user.target
    """)

    try:
        unit_path.write_text(unit_content, encoding="utf-8")
        run(["systemctl", "daemon-reload"], capture_output=True)
        run(["systemctl", "enable", unit_name], capture_output=True)
        log(f"Unità systemd '{unit_name}' creata e abilitata.")
        return True
    except (PermissionError, subprocess.CalledProcessError) as e:
        log(f"Impossibile creare unità systemd: {e}")
        log("Suggerimento: eseguire con sudo per registrare il servizio.")
        return False


def start_service_linux() -> bool:
    """Avvia il servizio systemd."""
    unit_name = f"{SERVICE_NAME.lower()}.service"
    r = run_quiet(["systemctl", "start", unit_name])
    return r.returncode == 0


def unregister_service_linux() -> None:
    """Ferma, disabilita e rimuove l'unità systemd."""
    unit_name = f"{SERVICE_NAME.lower()}.service"
    run_quiet(["systemctl", "stop", unit_name])
    run_quiet(["systemctl", "disable", unit_name])
    unit_path = Path(f"/etc/systemd/system/{unit_name}")
    if unit_path.exists():
        unit_path.unlink()
    run_quiet(["systemctl", "daemon-reload"])


def register_service_macos(pg_bin: Path, pg_data: Path, port: int) -> bool:
    """Crea e carica un plist launchd per PostgreSQL."""
    plist_label = f"com.foliarium.{SERVICE_NAME.lower()}"
    plist_path = Path.home() / "Library" / "LaunchAgents" / f"{plist_label}.plist"
    plist_path.parent.mkdir(parents=True, exist_ok=True)

    plist_content = textwrap.dedent(f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
          "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
        <plist version="1.0">
        <dict>
            <key>Label</key>
            <string>{plist_label}</string>
            <key>ProgramArguments</key>
            <array>
                <string>{exe(pg_bin, 'postgres')}</string>
                <string>-D</string>
                <string>{pg_data}</string>
                <string>-p</string>
                <string>{port}</string>
            </array>
            <key>RunAtLoad</key>
            <true/>
            <key>KeepAlive</key>
            <true/>
            <key>StandardErrorPath</key>
            <string>{pg_data}/postgresql.log</string>
            <key>StandardOutPath</key>
            <string>{pg_data}/postgresql.log</string>
        </dict>
        </plist>
    """)

    try:
        plist_path.write_text(plist_content, encoding="utf-8")
        run(["launchctl", "load", str(plist_path)], capture_output=True)
        log(f"Agente launchd '{plist_label}' creato e caricato.")
        return True
    except (PermissionError, subprocess.CalledProcessError) as e:
        log(f"Impossibile creare agente launchd: {e}")
        return False


def start_service_macos() -> bool:
    """Avvia l'agente launchd."""
    plist_label = f"com.foliarium.{SERVICE_NAME.lower()}"
    r = run_quiet(["launchctl", "start", plist_label])
    return r.returncode == 0


def unregister_service_macos() -> None:
    """Scarica e rimuove l'agente launchd."""
    plist_label = f"com.foliarium.{SERVICE_NAME.lower()}"
    plist_path = Path.home() / "Library" / "LaunchAgents" / f"{plist_label}.plist"
    run_quiet(["launchctl", "unload", str(plist_path)])
    if plist_path.exists():
        plist_path.unlink()


# ============================================================================
# Funzioni dispatcher cross-platform
# ============================================================================

def register_service(pg_bin: Path, pg_data: Path, port: int) -> bool:
    if IS_WIN:
        return register_service_windows(pg_bin, pg_data)
    elif IS_LINUX:
        return register_service_linux(pg_bin, pg_data, port)
    elif IS_MAC:
        return register_service_macos(pg_bin, pg_data, port)
    log(f"Piattaforma '{SYSTEM}' non supportata per la registrazione del servizio.")
    return False


def start_service() -> bool:
    if IS_WIN:
        return start_service_windows()
    elif IS_LINUX:
        return start_service_linux()
    elif IS_MAC:
        return start_service_macos()
    return False


def unregister_service(pg_bin: Path) -> None:
    if IS_WIN:
        unregister_service_windows(pg_bin)
    elif IS_LINUX:
        unregister_service_linux()
    elif IS_MAC:
        unregister_service_macos()


# ============================================================================
# Modalità sviluppo: PostgreSQL di sistema già in esecuzione
# ============================================================================

def _setup_on_external_pg(
    install_dir: Path,
    pg_bin: Path,
    db_password: str,
    admin_password: str,
    postgres_password: str,
    port: int,
    db_name: str = DB_NAME,
    db_user: str = DB_USER,
    config_file: Path | None = None,
) -> bool:
    """
    Crea il DB su un PostgreSQL già in esecuzione (modalità sviluppo).
    Non esegue initdb, non modifica pg_hba.conf, non registra servizi.
    """
    sql_dir = install_dir / "sql_scripts"
    if config_file is None:
        config_file = install_dir / "config.ini"

    print(f"\n{'='*60}")
    print(f" Foliarium — Setup DB su PostgreSQL di sistema ({SYSTEM})")
    print(f"{'='*60}")
    log(f"PostgreSQL bin: {pg_bin}")
    log(f"Host/porta:     127.0.0.1:{port}")
    log(f"Database:       {db_name}")
    log(f"Utente app:     {db_user}")

    if not (pg_bin / f"psql{EXE}").exists():
        log(f"ERRORE: psql non trovato in '{pg_bin}'")
        return False

    if not wait_ready(pg_bin, port, attempts=5):
        log(f"ERRORE: PostgreSQL non risponde su 127.0.0.1:{port}.")
        log("Verificare che il servizio sia in esecuzione.")
        return False

    print(f"\n[1/4] Creazione ruolo '{db_user}' e database '{db_name}'...")
    try:
        run_psql(pg_bin, port,
                 f"DO $$ BEGIN "
                 f"IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='{db_user}') THEN "
                 f"CREATE ROLE {db_user} LOGIN PASSWORD '{db_password}'; "
                 f"END IF; END $$;",
                 password=postgres_password)

        env = os.environ.copy()
        env["PGPASSWORD"] = postgres_password
        r = run_quiet([exe(pg_bin, "psql"),
                       "-h", "127.0.0.1", "-p", str(port),
                       "-U", "postgres", "-d", "postgres",
                       "-tc", f"SELECT 1 FROM pg_database WHERE datname='{db_name}'"],
                      env=env)
        if "1" not in r.stdout:
            run_psql(pg_bin, port,
                     f"CREATE DATABASE {db_name} OWNER postgres ENCODING 'UTF8';",
                     password=postgres_password)
            log(f"Database '{db_name}' creato.")
        else:
            log(f"Database '{db_name}' già esistente.")

        run_psql(pg_bin, port,
                 f"GRANT CONNECT ON DATABASE {db_name} TO {db_user};",
                 dbname=db_name, password=postgres_password)

    except subprocess.CalledProcessError as e:
        log(f"ERRORE nella creazione del DB: {e}")
        log("Suggerimento: usare --postgres-password se postgres richiede autenticazione.")
        return False

    print("\n[2/4] Esecuzione script SQL...")
    try:
        for script_name in SQL_SCRIPTS:
            sql_file = sql_dir / script_name
            if sql_file.exists():
                log(f"→ {script_name}")
                run_psql_file(pg_bin, port, sql_file,
                              dbname=db_name, password=postgres_password)
            else:
                log(f"ATTENZIONE: {script_name} non trovato, saltato.")

        bootstrap_file = sql_dir / BOOTSTRAP_ADMIN_SCRIPT
        if bootstrap_file.exists():
            log(f"→ {BOOTSTRAP_ADMIN_SCRIPT}")
            run_psql_file(pg_bin, port, bootstrap_file,
                          dbname=db_name, password=postgres_password,
                          variables={
                              "admin_password": admin_password,
                              "admin_email": "admin@archivio.local",
                          })
        else:
            log(f"ATTENZIONE: {BOOTSTRAP_ADMIN_SCRIPT} non trovato — admin non creato!")

        run_psql(pg_bin, port,
                 f"GRANT USAGE ON SCHEMA catasto TO {db_user}; "
                 f"GRANT USAGE ON SCHEMA public TO {db_user}; "
                 f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA catasto TO {db_user}; "
                 f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {db_user}; "
                 f"GRANT USAGE ON ALL SEQUENCES IN SCHEMA catasto TO {db_user}; "
                 f"GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO {db_user}; "
                 f"ALTER DEFAULT PRIVILEGES IN SCHEMA catasto "
                 f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {db_user}; "
                 f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                 f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {db_user};",
                 dbname=db_name, password=postgres_password)

    except subprocess.CalledProcessError as e:
        log(f"ERRORE nell'esecuzione degli script SQL: {e}")
        return False

    print("\n[3/4] Scrittura config.ini...")
    config = configparser.ConfigParser()
    config["database"] = {
        "host": "127.0.0.1",
        "port": str(port),
        "dbname": db_name,
        "user": db_user,
        "password": db_password,
    }
    config["service"] = {
        "name": "external",
        "pg_bin": str(pg_bin),
        "pg_data": "",
        "platform": SYSTEM,
    }
    with open(config_file, "w", encoding="utf-8") as f:
        f.write("# Foliarium — Configurazione database (PostgreSQL di sistema)\n")
        f.write(f"# Generato da setup_database.py --pg-bin ({SYSTEM})\n\n")
        config.write(f)
    log(f"config.ini scritto in: {config_file}")

    print("\n[4/4] Verifica connessione finale...")
    if not wait_ready(pg_bin, port, attempts=3):
        log("ATTENZIONE: verifica finale non superata.")
    else:
        log("Connessione OK.")

    print(f"\n{'='*60}")
    print(" Setup completato!")
    print(f"{'='*60}")
    log(f"Porta:    {port}  |  Database: {db_name}")
    log(f"Utente DB app:   {db_user}")
    log(f"Config:          {config_file}")
    log(f"Utente admin:    admin  /  {admin_password}")
    log("IMPORTANTE: cambiare la password admin al primo accesso!")
    print(f"{'='*60}\n")
    return True


# ============================================================================
# Setup principale
# ============================================================================

def detect_install_dir() -> Path:
    """Rileva la directory di installazione (dove si trova questo script)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def setup(
    install_dir: Path,
    db_password: str | None = None,
    skip_service: bool = False,
    logfile: Path | None = None,
    admin_password: str | None = None,
    config_file: Path | None = None,
) -> bool:
    """
    Esegue l'intera sequenza di setup del database.
    Ritorna True se tutto è andato a buon fine.
    """
    pg_bin = install_dir / "pgsql" / "bin"
    # Su Windows, pg_data deve stare FUORI da Program Files perche' initdb
    # droppa i privilegi e l'utente non-admin non puo' scrivere li'.
    # Location standard Windows per dati condivisi: %ProgramData%\Foliarium\pg_data
    if IS_WIN:
        data_root = Path(os.environ.get("ProgramData", r"C:\ProgramData")) / "Foliarium"
        data_root.mkdir(parents=True, exist_ok=True)
        pg_data = data_root / "pg_data"
    else:
        pg_data = install_dir / "pg_data"
    sql_dir = install_dir / "sql_scripts"
    if config_file is None:
        config_file = install_dir / "config.ini"

    if not pg_bin.exists():
        log(f"ERRORE: cartella pgsql/bin non trovata in '{install_dir}'")
        log("Assicurarsi che PostgreSQL sia incluso nel pacchetto di installazione.")
        return False

    if db_password is None:
        db_password = generate_password(16)
    if admin_password is None:
        admin_password = generate_password(16)

    print(f"\n{'='*60}")
    print(f" Foliarium — Inizializzazione Database ({SYSTEM})")
    print(f"{'='*60}")
    log(f"Directory installazione: {install_dir}")
    log(f"PostgreSQL bin:          {pg_bin}")
    log(f"Data directory:          {pg_data}")

    # --- 1. Trova porta libera ---
    print("\n[1/8] Ricerca porta libera...")
    port = find_free_port(DEFAULT_PORT)
    log(f"Porta selezionata: {port}")

    # --- 2. initdb ---
    print("\n[2/8] Inizializzazione cluster PostgreSQL...")
    if (pg_data / "PG_VERSION").exists():
        log("Cluster già esistente, skip initdb.")
    else:
        env = os.environ.copy()
        env.pop("PGDATA", None)
        try:
            run([exe(pg_bin, "initdb"),
                 "-D", str(pg_data),
                 "-U", "postgres",
                 "--locale=C",
                 "--encoding=UTF8",
                 "--no-instructions"],
                env=env, capture_output=True)
        except subprocess.CalledProcessError as e:
            log(f"ERRORE initdb: {e}")
            return False

    # --- 3. Configurazione ---
    print("\n[3/8] Configurazione PostgreSQL...")

    # pg_hba.conf
    hba = pg_data / "pg_hba.conf"
    hba.write_text(
        "# TYPE  DATABASE  USER       ADDRESS        METHOD\n"
        "local   all       all                       scram-sha-256\n"
        "host    all       all        127.0.0.1/32   scram-sha-256\n"
        "host    all       all        ::1/128        scram-sha-256\n",
        encoding="utf-8",
    )

    # postgresql.conf
    conf = pg_data / "postgresql.conf"
    conf_text = conf.read_text(encoding="utf-8") if conf.exists() else ""
    conf_overrides = (
        f"\n# === Foliarium (generato da setup_database.py) ===\n"
        f"port = {port}\n"
        f"listen_addresses = '127.0.0.1'\n"
        f"max_connections = 30\n"
        f"shared_buffers = 64MB\n"
        f"work_mem = 4MB\n"
        f"logging_collector = on\n"
        f"log_directory = 'log'\n"
        f"log_min_messages = warning\n"
        f"password_encryption = scram-sha-256\n"
    )
    conf.write_text(conf_text + conf_overrides, encoding="utf-8")

    # --- 4. Avvio temporaneo per impostare password superuser ---
    print("\n[4/8] Avvio temporaneo per configurazione iniziale...")

    # Prima: avvia con trust per impostare la password postgres
    # (pg_hba.conf è scram, ma initdb era trust → sovrascriviamo temporaneamente)
    hba_temp = (
        "# Configurazione temporanea per setup iniziale\n"
        "local   all       all                       trust\n"
        "host    all       all        127.0.0.1/32   trust\n"
        "host    all       all        ::1/128        trust\n"
    )
    hba.write_text(hba_temp, encoding="utf-8")

    pg_log = pg_data / "pg_setup.log"
    try:
        run([exe(pg_bin, "pg_ctl"), "start",
             "-D", str(pg_data), "-l", str(pg_log),
             "-w", "-t", "30",
             "-o", f"-p {port} -h 127.0.0.1"],
            capture_output=True)
    except subprocess.CalledProcessError as e:
        log(f"ERRORE avvio PostgreSQL: {e}")
        return False

    if not wait_ready(pg_bin, port):
        log("ERRORE: PostgreSQL non risponde.")
        return False

    try:
        # Imposta password superuser
        run_psql(pg_bin, port,
                 f"ALTER USER postgres PASSWORD '{db_password}';")
        log("Password superuser impostata.")

        # Ora ripristina pg_hba.conf con scram-sha-256
        hba.write_text(
            "# TYPE  DATABASE  USER       ADDRESS        METHOD\n"
            "local   all       all                       scram-sha-256\n"
            "host    all       all        127.0.0.1/32   scram-sha-256\n"
            "host    all       all        ::1/128        scram-sha-256\n",
            encoding="utf-8",
        )

        # Ricarica configurazione
        run_quiet([exe(pg_bin, "pg_ctl"), "reload", "-D", str(pg_data)])
        time.sleep(1)

        # --- 5/6. Creazione ruolo e database ---
        print(f"\n[5/8] Creazione ruolo '{DB_USER}' e database '{DB_NAME}'...")

        env = os.environ.copy()
        env["PGPASSWORD"] = db_password

        run_psql(pg_bin, port,
                 f"DO $$ BEGIN "
                 f"IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='{DB_USER}') THEN "
                 f"CREATE ROLE {DB_USER} LOGIN PASSWORD '{db_password}'; "
                 f"END IF; END $$;",
                 password=db_password)

        # Verifica se DB esiste
        r = run_quiet([exe(pg_bin, "psql"),
                       "-h", "127.0.0.1", "-p", str(port),
                       "-U", "postgres", "-d", "postgres",
                       "-tc", f"SELECT 1 FROM pg_database WHERE datname='{DB_NAME}'"],
                      env=env)

        if "1" not in r.stdout:
            run_psql(pg_bin, port,
                     f"CREATE DATABASE {DB_NAME} OWNER postgres ENCODING 'UTF8';",
                     password=db_password)

        run_psql(pg_bin, port,
                 f"GRANT CONNECT ON DATABASE {DB_NAME} TO {DB_USER};",
                 dbname=DB_NAME, password=db_password)

        # --- 7. Script SQL ---
        print("\n[6/8] Esecuzione script SQL (schema, funzioni, feature)...")
        for script_name in SQL_SCRIPTS:
            sql_file = sql_dir / script_name
            if sql_file.exists():
                log(f"→ {script_name}")
                run_psql_file(pg_bin, port, sql_file,
                              dbname=DB_NAME, password=db_password)
            else:
                log(f"ATTENZIONE: {script_name} non trovato, saltato.")

        # Bootstrap admin: passa admin_password come variabile psql.
        # CRITICO per fresh install: senza questo non si puo' accedere al primo avvio.
        bootstrap_file = sql_dir / BOOTSTRAP_ADMIN_SCRIPT
        if bootstrap_file.exists():
            log(f"→ {BOOTSTRAP_ADMIN_SCRIPT} (password admin dinamica)")
            run_psql_file(
                pg_bin, port, bootstrap_file,
                dbname=DB_NAME, password=db_password,
                variables={
                    "admin_password": admin_password,
                    "admin_email": "admin@archivio.local",
                },
            )
        else:
            log(f"ATTENZIONE: {BOOTSTRAP_ADMIN_SCRIPT} non trovato — admin non creato!")

        # Grant permessi su tutte le tabelle create
        run_psql(pg_bin, port,
                 f"GRANT USAGE ON SCHEMA catasto TO {DB_USER}; "
                 f"GRANT USAGE ON SCHEMA public TO {DB_USER}; "
                 f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA catasto TO {DB_USER}; "
                 f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {DB_USER}; "
                 f"GRANT USAGE ON ALL SEQUENCES IN SCHEMA catasto TO {DB_USER}; "
                 f"GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO {DB_USER}; "
                 f"ALTER DEFAULT PRIVILEGES IN SCHEMA catasto "
                 f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {DB_USER}; "
                 f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                 f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {DB_USER};",
                 dbname=DB_NAME, password=db_password)

    finally:
        # Ferma il server temporaneo
        log("Arresto server temporaneo...")
        run_quiet([exe(pg_bin, "pg_ctl"), "stop",
                   "-D", str(pg_data), "-m", "fast"])
        time.sleep(2)

    # --- Registrazione e avvio servizio ---
    if not skip_service:
        print(f"\n[7/8] Registrazione servizio ({SYSTEM})...")
        service_ok = register_service(pg_bin, pg_data, port)

        if service_ok:
            log("Avvio servizio...")
            if not start_service():
                log("Avvio servizio fallito, provo avvio diretto...")
                run_quiet([exe(pg_bin, "pg_ctl"), "start",
                           "-D", str(pg_data), "-l", str(pg_log),
                           "-w", "-t", "30"])
        else:
            log("Servizio non registrato. Avvio manuale con:")
            log(f"  {exe(pg_bin, 'pg_ctl')} start -D {pg_data}")
            # Avvia comunque per questa sessione
            run_quiet([exe(pg_bin, "pg_ctl"), "start",
                       "-D", str(pg_data), "-l", str(pg_log),
                       "-w", "-t", "30"])
    else:
        log("Skip registrazione servizio (--skip-service).")

    # --- 8. Scrittura config.ini ---
    print("\n[8/8] Scrittura config.ini...")
    config = configparser.ConfigParser()
    config["database"] = {
        "host": "127.0.0.1",
        "port": str(port),
        "dbname": DB_NAME,
        "user": DB_USER,
        "password": db_password,
    }
    config["service"] = {
        "name": SERVICE_NAME,
        "pg_bin": str(pg_bin),
        "pg_data": str(pg_data),
        "platform": SYSTEM,
    }

    with open(config_file, "w", encoding="utf-8") as f:
        f.write("# Foliarium — Configurazione database locale\n")
        f.write(f"# Generato da setup_database.py ({SYSTEM})\n")
        f.write("# NON modificare manualmente a meno che non si sappia cosa si fa.\n\n")
        config.write(f)

    log(f"config.ini scritto in: {config_file}")

    # --- Riepilogo ---
    print(f"\n{'='*60}")
    print(" Installazione completata!")
    print(f"{'='*60}")
    log(f"Piattaforma:  {SYSTEM}")
    log(f"Porta:        {port}")
    log(f"Database:     {DB_NAME}")
    log(f"Utente DB:    {DB_USER}")
    log(f"Servizio:     {SERVICE_NAME}")
    log(f"Config:       {config_file}")
    print()
    log("Credenziali amministratore applicativo:")
    log("  Utente:   admin")
    log("  Password: admin123")
    log("  IMPORTANTE: cambiare la password al primo accesso!")
    print(f"{'='*60}\n")

    return True


# ============================================================================
# Disinstallazione
# ============================================================================

def uninstall(install_dir: Path) -> None:
    """Rimuove il servizio PostgreSQL e i dati."""
    pg_bin = install_dir / "pgsql" / "bin"
    # Stessa logica di setup(): su Windows pg_data e' in %ProgramData%
    if IS_WIN:
        data_root = Path(os.environ.get("ProgramData", r"C:\ProgramData")) / "Foliarium"
        pg_data = data_root / "pg_data"
    else:
        data_root = None
        pg_data = install_dir / "pg_data"

    print(f"\n{'='*60}")
    print(f" Foliarium — Rimozione Database ({SYSTEM})")
    print(f"{'='*60}")

    log("Arresto e rimozione servizio...")
    unregister_service(pg_bin)

    if pg_data.exists():
        log(f"Rimozione dati database: {pg_data}")
        shutil.rmtree(pg_data, ignore_errors=True)

    # Rimuovi anche la cartella padre %ProgramData%\Foliarium se vuota
    if IS_WIN and data_root and data_root.exists():
        try:
            data_root.rmdir()  # fallisce se non vuota — e' ok
        except OSError:
            pass

    config_file = install_dir / "config.ini"
    if config_file.exists():
        config_file.unlink()
        log("config.ini rimosso.")

    log("Pulizia completata.")
    print(f"{'='*60}\n")


# ============================================================================
# Entry point
# ============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inizializzazione database PostgreSQL per Foliarium",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Esempi modalità sviluppo (PostgreSQL di sistema già installato):\n"
            "  python setup_database.py --pg-bin auto\n"
            "  python setup_database.py --pg-bin auto --admin-password MiaPass\n"
            r'  python setup_database.py --pg-bin "C:\Program Files\PostgreSQL\16\bin"'
            "\n  python setup_database.py --pg-bin auto --postgres-password postgres"
        ),
    )
    parser.add_argument("--install-dir", default=None,
                        help="Directory di installazione (default: auto-detect)")
    parser.add_argument("--db-password", default=None,
                        help="Password per il database (default: generata casualmente)")
    parser.add_argument("--admin-password", default=None,
                        help="Password per l'utente admin applicativo "
                             "(default: 'admin123' — CAMBIARLA al primo accesso)")
    parser.add_argument("--skip-service", action="store_true",
                        help="Non registrare come servizio di sistema")
    parser.add_argument("--uninstall", action="store_true",
                        help="Rimuovi servizio e dati database")
    # Modalità sviluppo
    parser.add_argument(
        "--pg-bin", default=None, metavar="PATH|auto",
        help=(
            "Percorso alla cartella bin di PostgreSQL di sistema "
            "(es. C:\\Program Files\\PostgreSQL\\16\\bin) oppure 'auto' per "
            "ricerca automatica. Usa un PostgreSQL già in esecuzione: "
            "salta initdb, pg_ctl e registrazione servizio."
        ),
    )
    parser.add_argument(
        "--postgres-password", default="",
        help="Password del superuser postgres (default: stringa vuota = trust/peer)",
    )
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT,
        help=f"Porta PostgreSQL (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--db-name", default=DB_NAME,
        help=f"Nome del database da creare (default: {DB_NAME})",
    )
    parser.add_argument(
        "--db-user", default=DB_USER,
        help=f"Ruolo PostgreSQL dell'applicazione (default: {DB_USER})",
    )
    parser.add_argument(
        "--config-file", default=None, metavar="FILE",
        help="Percorso del file di configurazione da scrivere (default: config.ini nella directory di installazione)",
    )
    args = parser.parse_args()

    install_dir = Path(args.install_dir) if args.install_dir else detect_install_dir()
    install_dir = install_dir.resolve()

    if args.uninstall:
        uninstall(install_dir)
        return

    # Modalità sviluppo: --pg-bin fornito
    if args.pg_bin is not None:
        if args.pg_bin.lower() == "auto":
            pg_bin = find_system_pgbin()
            if pg_bin is None:
                print("  ERRORE: PostgreSQL non trovato nel PATH né nelle posizioni standard.")
                print("  Specificare il percorso esatto con --pg-bin <cartella>")
                sys.exit(1)
            log(f"PostgreSQL trovato in: {pg_bin}")
        else:
            pg_bin = Path(args.pg_bin)

        _db_pwd = args.db_password or generate_password(16)
        _admin_pwd = args.admin_password or generate_password(16)
        ok = _setup_on_external_pg(
            install_dir=install_dir,
            pg_bin=pg_bin,
            db_password=_db_pwd,
            admin_password=_admin_pwd,
            postgres_password=args.postgres_password,
            port=args.port,
            db_name=args.db_name,
            db_user=args.db_user,
            config_file=Path(args.config_file) if args.config_file else None,
        )
        sys.exit(0 if ok else 1)

    # Modalità bundle: pgsql/ incluso nell'installer
    ok = setup(install_dir, args.db_password, args.skip_service,
               admin_password=args.admin_password,
               config_file=Path(args.config_file) if args.config_file else None)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
