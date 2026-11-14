"""
tests/unit/test_setup_database.py
=================================
Unit test delle helper di `setup_database.py` che l'installer usa.

Non viene esercitata la sequenza completa di setup (richiede un cluster
PostgreSQL e la registrazione di un servizio di sistema): qui stanno le
funzioni pure, dove un errore si manifesterebbe solo sulla macchina del
cliente a installazione gia' avviata.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

import setup_database as sdb


pytestmark = pytest.mark.unit


class TestResolveSqlDir:
    """
    Nel bundle PyInstaller 'onedir' gli script SQL sono una risorsa e
    finiscono in `_internal/sql_scripts`, non accanto all'eseguibile.
    """

    def _make_sql_tree(self, root: Path) -> Path:
        sql_dir = root / "sql_scripts"
        (sql_dir / "admin").mkdir(parents=True)
        (sql_dir / sdb.BOOTSTRAP_ADMIN_SCRIPT).write_text("-- bootstrap", encoding="utf-8")
        return sql_dir

    def test_trova_gli_script_accanto_all_eseguibile(self, tmp_path):
        atteso = self._make_sql_tree(tmp_path)
        assert sdb.resolve_sql_dir(tmp_path) == atteso

    def test_trova_gli_script_dentro_internal(self, tmp_path):
        """Il caso del bundle onedir: e' quello che l'installer produce."""
        atteso = self._make_sql_tree(tmp_path / "_internal")
        assert sdb.resolve_sql_dir(tmp_path) == atteso

    def test_la_cartella_accanto_all_eseguibile_ha_la_precedenza(self, tmp_path):
        accanto = self._make_sql_tree(tmp_path)
        self._make_sql_tree(tmp_path / "_internal")
        assert sdb.resolve_sql_dir(tmp_path) == accanto

    def test_una_cartella_senza_bootstrap_non_viene_scelta(self, tmp_path):
        """
        Una `sql_scripts/` vuota accanto all'eseguibile non deve mettere in
        ombra quella completa in `_internal/`: il setup creerebbe un database
        senza schema e senza utente admin, e l'errore si vedrebbe solo al
        primo accesso.
        """
        (tmp_path / "sql_scripts").mkdir()
        atteso = self._make_sql_tree(tmp_path / "_internal")
        assert sdb.resolve_sql_dir(tmp_path) == atteso

    def test_senza_nessuna_cartella_ritorna_il_percorso_atteso(self, tmp_path):
        """Il fallback nomina il percorso atteso, per un errore leggibile."""
        assert sdb.resolve_sql_dir(tmp_path) == tmp_path / "sql_scripts"

    def test_include_le_risorse_dell_eseguibile_se_presenti(self, tmp_path, monkeypatch):
        atteso = self._make_sql_tree(tmp_path / "meipass")
        monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "meipass"), raising=False)
        assert sdb.resolve_sql_dir(tmp_path / "vuota") == atteso


class TestWriteCredentialsFile:
    """
    La password di `admin` e' generata a caso e in DB resta solo l'hash
    bcrypt: se non finisce in questo file, l'installazione riesce ma
    nessuno puo' accedere.
    """

    def test_scrive_la_password_e_i_dati_tecnici(self, tmp_path):
        out = tmp_path / "PRIMO-ACCESSO.txt"
        sdb.write_credentials_file(out, "Segreta123", "catasto_storico", "foliarium", 5433)

        testo = out.read_text(encoding="utf-8")
        assert "Segreta123" in testo
        assert "admin" in testo
        assert "catasto_storico" in testo
        assert "5433" in testo
        assert "CAMBIARE LA PASSWORD" in testo

    def test_un_percorso_non_scrivibile_non_interrompe_l_installazione(
        self, tmp_path, capsys,
    ):
        """
        Il database e' gia' stato creato quando questo file viene scritto:
        fallire qui butterebbe via un'installazione riuscita. La password
        resta comunque nel riepilogo a schermo.
        """
        non_scrivibile = tmp_path / "cartella-inesistente" / "out.txt"
        sdb.write_credentials_file(non_scrivibile, "Segreta123", "db", "user", 5432)

        assert "ATTENZIONE" in capsys.readouterr().out
        assert not non_scrivibile.exists()


class TestLogERedazione:
    """
    L'installer esegue setup_db.exe con la console nascosta: il file di log
    e' l'unica diagnostica che resta. Ma resta anche sul disco del cliente, e
    la documentazione invita a inviarlo all'assistenza.
    """

    @pytest.fixture(autouse=True)
    def _log_isolato(self, monkeypatch):
        """Ogni test parte senza log e senza segreti registrati."""
        monkeypatch.setattr(sdb, "_LOG_FILE", None)
        monkeypatch.setattr(sdb, "_SECRETS", [])

    def test_il_log_viene_scritto_su_file(self, tmp_path):
        logfile = tmp_path / "setup_database.log"
        sdb.configure_logfile(logfile)
        sdb.log("prima riga")
        sdb.log("seconda riga")

        testo = logfile.read_text(encoding="utf-8")
        assert "Foliarium" in testo          # intestazione
        assert "prima riga" in testo
        assert "seconda riga" in testo

    def test_le_password_non_finiscono_nel_file_di_log(self, tmp_path, capsys):
        logfile = tmp_path / "setup_database.log"
        sdb.configure_logfile(logfile)
        sdb.register_secret("PasswordSegreta123")

        sdb.log("CREATE ROLE foliarium PASSWORD 'PasswordSegreta123';")

        assert "PasswordSegreta123" not in logfile.read_text(encoding="utf-8")
        assert "***" in logfile.read_text(encoding="utf-8")
        # Sulla console resta leggibile: serve a chi esegue il setup a mano.
        assert "PasswordSegreta123" in capsys.readouterr().out

    def test_le_stringhe_corte_non_vengono_registrate(self):
        """
        Una password di 3-4 caratteri maschererebbe pezzi di parole comuni
        rendendo il log illeggibile — e non e' una password da proteggere.
        """
        sdb.register_secret("abc")
        assert sdb.redact("abcdef") == "abcdef"

    def test_una_password_assente_non_viene_registrata(self):
        sdb.register_secret(None)
        sdb.register_secret("")
        assert sdb._SECRETS == []

    def test_un_log_non_scrivibile_non_interrompe_il_setup(self, tmp_path, capsys):
        """Il log e' diagnostica: non e' un motivo per fallire."""
        # Un file al posto della cartella padre: mkdir e write falliscono.
        ostacolo = tmp_path / "ostacolo"
        ostacolo.write_text("non sono una cartella", encoding="utf-8")

        sdb.configure_logfile(ostacolo / "sub" / "setup.log")

        assert sdb._LOG_FILE is None
        assert "ATTENZIONE" in capsys.readouterr().out
        sdb.log("il setup continua")  # non deve sollevare


class TestCostanti:

    def test_il_nome_del_database_e_allineato_al_resto_del_progetto(self):
        """
        config.example.ini, setup_database.bat e la pipeline CI usano tutti
        "catasto_storico". Una divergenza qui non rompe il setup in se' (che
        scrive il proprio config.ini coerente) ma disallinea documentazione,
        script di backup e istruzioni di assistenza.

        Il confronto e' con i file del repo, non con `config.ENV_DB_NAME`:
        quello dipende dall'ambiente in cui girano i test.
        """
        import configparser

        radice = Path(sdb.__file__).parent

        esempio = configparser.ConfigParser()
        esempio.read(radice / "config.example.ini", encoding="utf-8")

        bat = (radice / "setup_database.bat").read_text(encoding="utf-8", errors="replace")

        assert sdb.DB_NAME == "catasto_storico"
        assert esempio.get("database", "dbname") == sdb.DB_NAME
        assert f'set "DB_NAME={sdb.DB_NAME}"' in bat

    def test_lo_script_di_bootstrap_e_fuori_dalla_lista_ordinata(self):
        """Va eseguito a parte: richiede la variabile psql admin_password."""
        assert sdb.BOOTSTRAP_ADMIN_SCRIPT not in sdb.SQL_SCRIPTS


class _EsitoPsql:
    """Controfigura di subprocess.CompletedProcess per le chiamate a psql."""

    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestRunPsqlFile:
    """
    Per anni gli script SQL sono stati eseguiti senza ON_ERROR_STOP e con
    l'output di psql catturato e poi scartato: un'istruzione fallita non
    lasciava traccia da nessuna parte. E' cosi' che la chiave esterna
    audit_log -> utente non e' mai stata creata dall'installer.
    """

    @pytest.fixture(autouse=True)
    def _log_isolato(self, monkeypatch, tmp_path):
        monkeypatch.setattr(sdb, "_SECRETS", [])
        self.logfile = tmp_path / "setup_database.log"
        sdb.configure_logfile(self.logfile)
        yield
        sdb.configure_logfile(None)

    @pytest.fixture
    def psql(self, monkeypatch):
        """Sostituisce subprocess.run e registra comando e ambiente."""
        chiamate: list[dict] = []
        esito = _EsitoPsql()

        def finto_run(cmd, **kw):
            chiamate.append({"cmd": [str(c) for c in cmd], "env": kw.get("env") or {}})
            return esito

        monkeypatch.setattr(sdb.subprocess, "run", finto_run)
        return chiamate, esito

    def _esegui(self, **kw):
        return sdb.run_psql_file(
            Path("/pg/bin"), 5432, Path("/sql/schema/01_tables.sql"),
            dbname="catasto_storico", password="Segreta-123456", **kw,
        )

    def test_modalita_rigorosa_ferma_psql_al_primo_errore(self, psql):
        chiamate, _ = psql
        self._esegui(strict=True)

        cmd = chiamate[0]["cmd"]
        assert cmd[cmd.index("ON_ERROR_STOP=1") - 1] == "-v"
        # Le variabili vanno dichiarate prima del file che le usa.
        assert cmd.index("ON_ERROR_STOP=1") < cmd.index("-f")

    def test_modalita_tollerante_non_ferma_psql(self, psql):
        chiamate, _ = psql
        self._esegui(strict=False)
        assert "ON_ERROR_STOP=1" not in chiamate[0]["cmd"]

    def test_le_variabili_arrivano_a_psql(self, psql):
        chiamate, _ = psql
        self._esegui(strict=True, variables={"admin_password": "Abc-123456"})
        cmd = chiamate[0]["cmd"]
        assert cmd[cmd.index("admin_password=Abc-123456") - 1] == "-v"

    def test_solo_gli_errori_arrivano_da_psql(self, psql, monkeypatch):
        """
        Con client_min_messages=error su stderr restano i soli errori: si
        possono contare senza interpretarne il testo, che dipende dalla
        lingua del server (ERROR, ERRORE, FEHLER...).
        """
        monkeypatch.setenv("PGOPTIONS", "-c statement_timeout=0")
        chiamate, _ = psql
        self._esegui(strict=True)

        env = chiamate[0]["env"]
        assert "client_min_messages=error" in env["PGOPTIONS"]
        # Le opzioni gia' presenti nell'ambiente non vanno perse.
        assert "statement_timeout=0" in env["PGOPTIONS"]
        assert env["PGPASSWORD"] == "Segreta-123456"

    def test_un_errore_in_modalita_rigorosa_interrompe_e_finisce_nel_log(self, psql):
        _, esito = psql
        esito.returncode = 3
        esito.stderr = (
            'psql:/sql/functions/06_audit.sql:244: ERROR:  relation '
            '"catasto.utente" does not exist\n'
            "LINE 19:     catasto.utente u ON al.app_user_id = u.id;\n"
        )

        with pytest.raises(sdb.subprocess.CalledProcessError):
            self._esegui(strict=True)

        testo = self.logfile.read_text(encoding="utf-8")
        assert 'relation "catasto.utente" does not exist' in testo
        assert "LINE 19:" in testo

    def test_gli_errori_tollerati_vengono_contati_e_scritti_nel_log(self, psql):
        _, esito = psql
        esito.returncode = 0
        esito.stderr = (
            'psql:/sql/schema/01_tables.sql:84: ERROR:  relation "comune" already exists\n'
            'psql:/sql/schema/01_tables.sql:443: ERRORE:  un valore chiave duplicato '
            'viola il vincolo univoco "app_metadata_pkey"\n'
            "DETAIL:  Key (key)=(schema_version) already exists.\n"
        )

        assert self._esegui(strict=False) == 2

        testo = self.logfile.read_text(encoding="utf-8")
        assert 'relation "comune" already exists' in testo
        assert "app_metadata_pkey" in testo

    def test_senza_errori_il_conteggio_e_zero(self, psql):
        assert self._esegui(strict=False) == 0
        assert self._esegui(strict=True) == 0

    def test_psql_che_non_parte_interrompe_anche_in_modalita_tollerante(self, psql):
        # Codice 2: connessione fallita. Non e' un errore di uno script.
        _, esito = psql
        esito.returncode = 2
        esito.stderr = "psql: error: connection to server failed\n"
        with pytest.raises(sdb.subprocess.CalledProcessError):
            self._esegui(strict=False)

    def test_le_password_negli_errori_non_finiscono_nel_log(self, psql):
        _, esito = psql
        sdb.register_secret("Abc-123456")
        esito.returncode = 3
        esito.stderr = (
            "psql:/sql/admin/04_bootstrap_admin.sql:48: ERROR:  qualcosa non va\n"
            "LINE 5:     crypt('Abc-123456', gen_salt('bf', 12)),\n"
        )

        with pytest.raises(sdb.subprocess.CalledProcessError):
            self._esegui(strict=True, variables={"admin_password": "Abc-123456"})

        testo = self.logfile.read_text(encoding="utf-8")
        assert "Abc-123456" not in testo
        assert "qualcosa non va" in testo


class TestRigoreSecondoLoStatoDelDatabase:
    """
    Su un database appena creato ogni errore e' un difetto degli script e
    deve fermare il setup. Su un database che esiste gia' (reinstallazione
    o aggiornamento sopra l'archivio del cliente) gli stessi script
    producono decine di «already exists» innocui: li' si prosegue, ma gli
    errori vengono comunque scritti nel log.
    """

    @pytest.fixture(autouse=True)
    def _log_isolato(self, monkeypatch):
        monkeypatch.setattr(sdb, "_LOG_FILE", None)
        monkeypatch.setattr(sdb, "_SECRETS", [])

    def _prepara(self, tmp_path, monkeypatch, *, database_esistente: bool):
        pg_bin = tmp_path / "bin"
        pg_bin.mkdir()
        (pg_bin / f"psql{sdb.EXE}").write_text("", encoding="utf-8")

        sql_dir = tmp_path / "sql_scripts"
        for rel in sdb.SQL_SCRIPTS + [sdb.BOOTSTRAP_ADMIN_SCRIPT]:
            (sql_dir / rel).parent.mkdir(parents=True, exist_ok=True)
            (sql_dir / rel).write_text("-- vuoto", encoding="utf-8")

        applicati: list[tuple[str, bool]] = []

        def finto_run_psql_file(pg_bin, port, sql_file, dbname="postgres",
                                password="", variables=None, strict=True):
            applicati.append((Path(sql_file).relative_to(sql_dir).as_posix(), strict))
            return 0

        monkeypatch.setattr(sdb, "wait_ready", lambda *a, **kw: True)
        monkeypatch.setattr(sdb, "run_psql", lambda *a, **kw: None)
        monkeypatch.setattr(sdb, "run_psql_file", finto_run_psql_file)
        monkeypatch.setattr(
            sdb, "run_quiet",
            lambda *a, **kw: _EsitoPsql(stdout=" 1\n" if database_esistente else "\n"),
        )
        return pg_bin, applicati

    def _setup(self, tmp_path, pg_bin):
        return sdb._setup_on_external_pg(
            install_dir=tmp_path, pg_bin=pg_bin,
            db_password="PasswordDb-123456", admin_password="PasswordAdmin-123456",
            postgres_password="", port=5432,
            config_file=tmp_path / "config.ini",
        )

    def test_database_nuovo_script_applicati_in_modo_rigoroso(self, tmp_path, monkeypatch):
        pg_bin, applicati = self._prepara(tmp_path, monkeypatch, database_esistente=False)

        assert self._setup(tmp_path, pg_bin) is True

        assert [nome for nome, _ in applicati] == sdb.SQL_SCRIPTS + [sdb.BOOTSTRAP_ADMIN_SCRIPT]
        assert all(rigoroso for _, rigoroso in applicati)

    def test_database_esistente_script_riapplicati_tollerando_gli_errori(self, tmp_path, monkeypatch):
        pg_bin, applicati = self._prepara(tmp_path, monkeypatch, database_esistente=True)

        assert self._setup(tmp_path, pg_bin) is True

        per_nome = dict(applicati)
        assert not any(per_nome[nome] for nome in sdb.SQL_SCRIPTS)
        # Il bootstrap dell'admin e' idempotente e resta rigoroso: se
        # fallisce, nessuno puo' entrare nell'applicazione.
        assert per_nome[sdb.BOOTSTRAP_ADMIN_SCRIPT] is True

    def test_un_errore_su_database_nuovo_fa_fallire_il_setup(self, tmp_path, monkeypatch):
        pg_bin, _ = self._prepara(tmp_path, monkeypatch, database_esistente=False)

        def fallisce(*a, **kw):
            raise sdb.subprocess.CalledProcessError(3, ["psql"])

        monkeypatch.setattr(sdb, "run_psql_file", fallisce)

        assert self._setup(tmp_path, pg_bin) is False
        # Un setup fallito non deve lasciare un config.ini che sembra valido.
        assert not (tmp_path / "config.ini").exists()


class TestAvvioDelServerNonBloccaIlSetup:
    """
    Su Windows l'installazione restava ferma per sempre su «Configurazione
    del database in corso». ``pg_ctl start`` era lanciato con l'output
    catturato: Python aspetta che il canale si chiuda, ma su Windows il
    server avviato da pg_ctl eredita quel canale e, restando acceso, non lo
    chiude mai.

    Su Linux il vero pg_ctl ridirige l'output del server e il problema non
    si vede. Qui un finto pg_ctl riproduce il comportamento di Windows:
    lascia acceso un processo figlio che tiene aperto il canale ereditato.
    """

    DURATA_FIGLIO = 8

    @pytest.fixture(autouse=True)
    def _log_isolato(self, monkeypatch):
        monkeypatch.setattr(sdb, "_LOG_FILE", None)
        monkeypatch.setattr(sdb, "_SECRETS", [])

    def _finto_pg_ctl(self, tmp_path, uscita: int = 0) -> Path:
        if sys.platform == "win32":
            pytest.skip("il finto pg_ctl è uno script di shell")
        pg_bin = tmp_path / "bin"
        pg_bin.mkdir()
        script = pg_bin / f"pg_ctl{sdb.EXE}"
        script.write_text(
            "#!/bin/sh\n"
            # Il «server»: resta acceso con il canale ereditato aperto.
            f"sleep {self.DURATA_FIGLIO} &\n"
            "echo 'waiting for server to start.... done'\n"
            f"exit {uscita}\n",
            encoding="utf-8",
        )
        script.chmod(0o755)
        return pg_bin

    def test_l_avvio_ritorna_anche_se_il_server_resta_acceso(self, tmp_path):
        pg_bin = self._finto_pg_ctl(tmp_path)
        inizio = time.monotonic()
        esito = sdb.avvia_postgres(pg_bin, tmp_path / "data", tmp_path / "pg.log", porta=5432)
        durata = time.monotonic() - inizio
        assert esito is True
        assert durata < self.DURATA_FIGLIO / 2, f"bloccato per {durata:.1f} s"

    def test_un_avvio_fallito_lo_dice_e_lascia_traccia_nel_log(self, tmp_path, monkeypatch):
        logfile = tmp_path / "setup.log"
        monkeypatch.setattr(sdb, "_LOG_FILE", logfile)
        pg_bin = self._finto_pg_ctl(tmp_path, uscita=1)
        assert sdb.avvia_postgres(pg_bin, tmp_path / "data", tmp_path / "pg.log") is False
        testo = logfile.read_text(encoding="utf-8")
        assert "codice 1" in testo
        # Il messaggio di pg_ctl non va perso.
        assert "waiting for server to start" in testo

    def test_ogni_avvio_con_pg_ctl_passa_da_avvia_postgres(self):
        # «net start», «systemctl start» e «launchctl start» non hanno il
        # problema: il servizio lo avvia il sistema, non un processo figlio
        # che erediti i canali. «pg_ctl start» invece compare una volta sola,
        # dentro avvia_postgres.
        import re
        sorgente = Path(sdb.__file__).read_text(encoding="utf-8")
        avvii = re.findall(r'"pg_ctl"\),\s*"start"', sorgente)
        assert len(avvii) == 1, avvii
        funzione = sorgente.split("def avvia_postgres", 1)[1].split("\ndef ", 1)[0]
        assert re.search(r'"pg_ctl"\),\s*"start"', funzione)
        assert "capture_output" not in funzione
