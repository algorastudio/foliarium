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
