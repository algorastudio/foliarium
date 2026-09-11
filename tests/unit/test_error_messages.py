"""
tests/unit/test_error_messages.py
=================================
Unit test di foliarium.ui.errors.

L'archivista non deve mai leggere il testo grezzo di psycopg2: questi test
fissano la traduzione dei codici SQLSTATE piu' frequenti e garantiscono che
il testo tecnico resti comunque disponibile per il supporto.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import PyQt6.QtWidgets  # noqa: F401
    _QT_OK = True
except ImportError:
    _QT_OK = False

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(not _QT_OK, reason="PyQt6 non disponibile"),
]


class _Diag:
    def __init__(self, constraint_name=None, table_name=None):
        self.constraint_name = constraint_name
        self.table_name = table_name


class _ErroreDriver(Exception):
    """Sostituto di psycopg2.Error: espone pgcode e diag come l'originale."""

    def __init__(self, messaggio, pgcode, constraint=None, table=None):
        super().__init__(messaggio)
        self.pgcode = pgcode
        self.diag = _Diag(constraint, table)


def _incatena(wrapper: Exception, causa: Exception) -> Exception:
    """Riproduce il 'raise ... from e' del decoratore db_handle_errors."""
    try:
        raise wrapper from causa
    except Exception as e:
        return e


class TestDescribeError:

    def test_vincolo_noto_ha_messaggio_specifico(self):
        from catasto_exceptions import DBUniqueConstraintError
        from foliarium.ui.errors import describe_error

        errore = _incatena(
            DBUniqueConstraintError("duplicate key value"),
            _ErroreDriver("duplicate key", "23505",
                          "partita_unique_numero_suffisso_comune", "partita"),
        )
        messaggio, suggerimento, dettagli = describe_error(errore)

        assert "Esiste già una partita con questo numero" in messaggio
        assert suggerimento
        assert "23505" in dettagli
        assert "partita_unique_numero_suffisso_comune" in dettagli

    def test_vincolo_sconosciuto_usa_il_nome_della_tabella(self):
        from catasto_exceptions import DBUniqueConstraintError
        from foliarium.ui.errors import describe_error

        errore = _incatena(
            DBUniqueConstraintError("duplicate key value"),
            _ErroreDriver("duplicate key", "23505", "comune_nome_key", "comune"),
        )
        messaggio, _, _ = describe_error(errore)
        assert messaggio == "Esiste già un comune con questi dati."

    def test_chiave_esterna_spiega_il_collegamento(self):
        from catasto_exceptions import DBMError
        from foliarium.ui.errors import describe_error

        errore = _incatena(
            DBMError("Foreign key constraint violated"),
            _ErroreDriver("FK violation", "23503", None, "possessore"),
        )
        messaggio, suggerimento, _ = describe_error(errore)
        assert "collegato" in messaggio
        assert "Rimuovi o riassegna" in suggerimento

    @pytest.mark.parametrize("pgcode,atteso", [
        ("23502", "Manca un dato obbligatorio."),
        ("22001", "Un testo inserito è troppo lungo."),
        ("28P01", "Utente o password del database non corretti."),
        ("53300", "Il database ha raggiunto il numero massimo di connessioni."),
    ])
    def test_codici_mappati(self, pgcode, atteso):
        from catasto_exceptions import DBMError
        from foliarium.ui.errors import describe_error

        errore = _incatena(DBMError("errore"), _ErroreDriver("x", pgcode))
        messaggio, _, _ = describe_error(errore)
        assert messaggio == atteso

    def test_classe_di_connessione_08(self):
        """Tutti i codici 08xxx parlano di collegamento interrotto."""
        from catasto_exceptions import DBMError
        from foliarium.ui.errors import describe_error

        errore = _incatena(DBMError("unreachable"), _ErroreDriver("x", "08006"))
        messaggio, suggerimento, _ = describe_error(errore)
        assert "Collegamento al database interrotto." == messaggio
        assert "PostgreSQL" in suggerimento

    def test_errore_non_db_resta_comprensibile(self):
        from foliarium.ui.errors import describe_error

        messaggio, suggerimento, dettagli = describe_error(ValueError("boom"))
        assert messaggio == "L'operazione non è stata completata."
        assert "Esporta log" in suggerimento
        assert "ValueError: boom" in dettagli

    def test_il_testo_tecnico_non_finisce_nel_messaggio(self):
        """Il punto dell'esercizio: niente gergo del driver in prima pagina."""
        from catasto_exceptions import DBUniqueConstraintError
        from foliarium.ui.errors import describe_error

        grezzo = ('duplicate key value violates unique constraint '
                  '"comune_nome_key"\nDETAIL: Key (nome)=(Savona) already exists.')
        errore = _incatena(
            DBUniqueConstraintError(grezzo),
            _ErroreDriver(grezzo, "23505", "comune_nome_key", "comune"),
        )
        messaggio, suggerimento, dettagli = describe_error(errore)

        for frase in ("duplicate key", "DETAIL", "constraint"):
            assert frase not in messaggio
            assert frase not in suggerimento
        assert "duplicate key" in dettagli   # ma resta per il supporto
