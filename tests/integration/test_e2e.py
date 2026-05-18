"""
tests/integration/test_e2e.py
=============================
Test E2E DB layer post-rebrand v1.5.0+ (riscritto ex-novo nello Sprint 3.9
six-hats — opzione B.6).

Scope: esercita l'API attuale di CatastoDBManager (post-mixin refactor)
su Postgres reale via fixture `db_manager` / `clean_db` / `sample_data`.
Non testa la GUI — i widget hanno la propria copertura in
`tests/integration/test_gui_widgets.py` e nei test unitari.

Cinque scenari critici, allineati al "golden path" dell'archivista:
  1. Comune CRUD: aggiungi → update → archivia
  2. Possessore lifecycle: create → update → search
  3. Partita workflow: create → assegna possessore → details → close
  4. Immobile workflow: inserisci → search → update → transfer
  5. Ricerca avanzata: ricerca_avanzata_immobili_gui restituisce risultati

Tutti i test usano marker `integration` e dipendono da una connessione
Postgres viva. In assenza di DB (es. esecuzione locale rapida senza
servizio) i test che dipendono da `db_manager` falliscono al setup della
fixture; in CI la fixture e' garantita dal servizio postgres del job.
"""

from __future__ import annotations

from datetime import date

import pytest


pytestmark = [pytest.mark.integration]


# ---------------------------------------------------------------------------
# 1. Comune CRUD
# ---------------------------------------------------------------------------

class TestComuneCRUD:
    """Lifecycle completo di un comune: insert, update, archivio."""

    def test_aggiungi_e_recupera(self, clean_db):
        """Insert produce id intero > 0 e il comune e' recuperabile."""
        comune_id = clean_db.aggiungi_comune(
            nome_comune="E2E Comune Test",
            provincia="GE",
            regione="Liguria",
        )
        assert isinstance(comune_id, int) and comune_id > 0

        dettagli = clean_db.get_comune_by_id(comune_id)
        assert dettagli is not None
        # get_comune_by_id aliasing: SELECT nome AS nome_comune
        assert dettagli["nome_comune"] == "E2E Comune Test"
        assert dettagli["provincia"] == "GE"

    def test_update_comune(self, clean_db):
        comune_id = clean_db.aggiungi_comune("E2E Update", "SV", "Liguria")
        ok = clean_db.update_comune(comune_id, {"provincia": "IM", "note": "aggiornato"})
        assert ok is True

        dettagli = clean_db.get_comune_by_id(comune_id)
        assert dettagli is not None
        assert dettagli["provincia"] == "IM"

    def test_archivia_comune(self, clean_db):
        comune_id = clean_db.aggiungi_comune("E2E Archivia", "CN", "Piemonte")
        ok = clean_db.archivia_comune(comune_id)
        assert ok is True

        # Il comune archiviato non compare nell'elenco standard
        elenco = clean_db.get_all_comuni_details()
        ids_attivi = [c["id"] for c in elenco]
        assert comune_id not in ids_attivi


# ---------------------------------------------------------------------------
# 2. Possessore lifecycle
# ---------------------------------------------------------------------------

class TestPossessoreLifecycle:
    """Insert + update con dati_modificati: dict (signature v1.5.0)."""

    def test_create_e_recupera(self, sample_data):
        db = sample_data["db"]
        comune_id = sample_data["comune_id"]

        possessore_id = db.create_possessore(
            nome_completo="E2E ROSSI MARIO fu Antonio",
            comune_riferimento_id=comune_id,
            paternita="fu Antonio",
            cognome_nome="ROSSI MARIO",
        )
        assert isinstance(possessore_id, int) and possessore_id > 0

        # Comparisce in get_possessori_by_comune
        possessori = db.get_possessori_by_comune(comune_id)
        nomi = [p["nome_completo"] for p in possessori]
        assert "E2E ROSSI MARIO fu Antonio" in nomi

    def test_update_con_dati_dict(self, sample_data):
        """update_possessore(possessore_id, dati_modificati: dict) v1.5.0+.

        I campi accettati dalla whitelist sono: nome_completo, cognome_nome,
        paternita, attivo, comune_riferimento_id. 'note' NON e' editabile via
        update_possessore — e' un campo gestito altrove.
        """
        db = sample_data["db"]
        pid = sample_data["possessore1_id"]

        # paternita e' nella whitelist → la modifica deve persistere
        db.update_possessore(pid, {"paternita": "fu Antonio E2E"})

        results = db.get_possessori_by_comune(
            sample_data["comune_id"], filter_text="TEST MARIO",
        )
        match = [p for p in results if p["id"] == pid]
        assert len(match) == 1
        assert match[0].get("paternita") == "fu Antonio E2E"


# ---------------------------------------------------------------------------
# 3. Partita workflow
# ---------------------------------------------------------------------------

class TestPartitaWorkflow:
    """create → aggiungi_possessore_a_partita → get_partita_details → update."""

    def test_create_e_dettagli(self, sample_data):
        db = sample_data["db"]
        partita_id = db.create_partita(
            comune_id=sample_data["comune_id"],
            numero_partita=42001,
            tipo="principale",
            stato="attiva",
            data_impianto=date(1910, 1, 1),
        )
        assert isinstance(partita_id, int) and partita_id > 0

        dettagli = db.get_partita_details(partita_id)
        assert dettagli is not None
        assert dettagli["numero_partita"] == 42001
        assert dettagli["stato"] == "attiva"
        assert dettagli["tipo"] == "principale"

    def test_aggiungi_possessore_e_chiusura(self, sample_data):
        db = sample_data["db"]
        # Riusiamo partita_id + possessore1_id da sample_data
        partita_id = sample_data["partita_id"]
        possessore_id = sample_data["possessore1_id"]

        ok = db.aggiungi_possessore_a_partita(
            partita_id=partita_id,
            possessore_id=possessore_id,
            tipo_partita_rel="principale",
            titolo="proprietà esclusiva",
            quota="1/1",
        )
        assert ok is True

        dettagli = db.get_partita_details(partita_id)
        ids_possessori = [p["id"] for p in dettagli.get("possessori", [])]
        assert possessore_id in ids_possessori

        # Chiusura partita via update_partita (dati_modificati: dict)
        ok = db.update_partita(partita_id, {
            "stato": "inattiva",
            "data_chiusura": date.today(),
        })
        assert ok is not False

        dettagli = db.get_partita_details(partita_id)
        assert dettagli["stato"] in ("inattiva", "chiusa")


# ---------------------------------------------------------------------------
# 4. Immobile workflow
# ---------------------------------------------------------------------------

class TestImmobileWorkflow:
    """inserisci_immobile → search_immobili → update → transfer."""

    def _crea_localita(self, db, comune_id):
        """Helper: crea una localita di servizio (richiesta da inserisci_immobile)."""
        return db.insert_localita(
            comune_id=comune_id,
            nome="Via Test E2E",
            tipologia_stradale="Via",
        )

    def test_inserisci_e_search(self, sample_data):
        db = sample_data["db"]
        localita_id = self._crea_localita(db, sample_data["comune_id"])

        immobile_id = db.inserisci_immobile(
            partita_id=sample_data["partita_id"],
            natura="Casa di abitazione",
            localita_id=localita_id,
            numero_civico="10",
            classificazione="Civile",
            consistenza="vani 3",
        )
        assert isinstance(immobile_id, int) and immobile_id > 0

        risultati = db.search_immobili(partita_id=sample_data["partita_id"])
        assert isinstance(risultati, list)
        ids = [im.get("id") for im in risultati]
        assert immobile_id in ids

    def test_update_immobile(self, sample_data):
        db = sample_data["db"]
        localita_id = self._crea_localita(db, sample_data["comune_id"])
        immobile_id = db.inserisci_immobile(
            partita_id=sample_data["partita_id"],
            natura="Casa",
            localita_id=localita_id,
        )

        # update_immobile(immobile_id, **kwargs) — kwargs come da signature db/immobili.py:101
        ok = db.update_immobile(
            immobile_id,
            natura="Casa di abitazione",
            classificazione="Civile",
        )
        assert ok is True

    def test_transfer_immobile(self, sample_data):
        """transfer_immobile sposta l'immobile a un'altra partita esistente."""
        db = sample_data["db"]
        localita_id = self._crea_localita(db, sample_data["comune_id"])
        immobile_id = db.inserisci_immobile(
            partita_id=sample_data["partita_id"],
            natura="Magazzino",
            localita_id=localita_id,
        )

        # Crea partita destinataria
        partita_dest = db.create_partita(
            comune_id=sample_data["comune_id"],
            numero_partita=42999,
            tipo="principale",
            stato="attiva",
            data_impianto=date(1910, 1, 1),
        )
        ok = db.transfer_immobile(immobile_id, partita_dest, registra_variazione=False)
        assert ok is True

        # Ora l'immobile appartiene alla nuova partita
        risultati = db.search_immobili(partita_id=partita_dest)
        ids = [im.get("id") for im in risultati]
        assert immobile_id in ids


# ---------------------------------------------------------------------------
# 5. Ricerca avanzata
# ---------------------------------------------------------------------------

class TestRicercaAvanzata:
    """ricerca_avanzata_immobili_gui restituisce list[dict] anche se vuoto."""

    def test_ricerca_per_comune_attivo(self, sample_data):
        db = sample_data["db"]
        risultati = db.ricerca_avanzata_immobili_gui(
            comune_id=sample_data["comune_id"],
        )
        # Indipendentemente dal contenuto, la signature deve restituire una lista
        assert isinstance(risultati, list)

    def test_ricerca_senza_filtri(self, sample_data):
        db = sample_data["db"]
        # Senza filtri: deve restituire una lista (eventualmente limitata da LIMIT interno)
        risultati = db.ricerca_avanzata_immobili_gui()
        assert isinstance(risultati, list)


# ---------------------------------------------------------------------------
# 6. Unique constraints — equivalente di TestComune/PossessoreOperations
#    duplicate del vecchio test_database_manager.py (skippato per drift).
# ---------------------------------------------------------------------------

class TestUniqueConstraints:
    """Verifica che gli insert duplicati sollevino DBUniqueConstraintError."""

    def test_aggiungi_comune_duplicato(self, clean_db):
        from catasto_exceptions import DBUniqueConstraintError

        clean_db.aggiungi_comune("DupComune", "PV", "Test")
        with pytest.raises(DBUniqueConstraintError):
            clean_db.aggiungi_comune("DupComune", "PV", "Test")

    def test_create_possessore_duplicato(self, sample_data):
        from catasto_exceptions import DBUniqueConstraintError

        db = sample_data["db"]
        comune_id = sample_data["comune_id"]
        db.create_possessore(
            nome_completo="DUPLICATO TEST E2E",
            comune_riferimento_id=comune_id,
        )
        with pytest.raises(DBUniqueConstraintError):
            db.create_possessore(
                nome_completo="DUPLICATO TEST E2E",
                comune_riferimento_id=comune_id,
            )


# ---------------------------------------------------------------------------
# 7. Error raising — equivalente di TestErrorHandling skippato
# ---------------------------------------------------------------------------

class TestErrorRaising:
    """Le exceptions custom in catasto_exceptions devono propagare correttamente."""

    def test_data_error_su_id_invalido(self, clean_db):
        """ID negativo / non int → DBDataError."""
        from catasto_exceptions import DBDataError

        with pytest.raises(DBDataError):
            clean_db.get_localita_by_comune(comune_id=-1)
        with pytest.raises(DBDataError):
            clean_db.create_possessore(
                nome_completo="X",
                comune_riferimento_id=0,  # non valido (>0 richiesto)
            )

    def test_update_possessore_id_inesistente(self, clean_db):
        """update_possessore su ID inesistente: ritorna senza errore
        (no rows affected, log info, ritorno None implicito)."""
        # Non deve sollevare — il design di update_possessore loggar e basta
        result = clean_db.update_possessore(
            possessore_id=99999999,
            dati_modificati={"paternita": "test"},
        )
        # Comportamento documentato: ritorna senza crash
        assert result is None or result is False


# ---------------------------------------------------------------------------
# 8. Transaction management via context manager — equivalente di
#    TestTransactionManagement skippato. begin/commit/rollback come metodi
#    top-level non esistono in v1.5.0+; le transazioni si fanno sulla
#    connessione ottenuta via context manager.
# ---------------------------------------------------------------------------

class TestTransactionContextManager:
    """Verifica le semantiche di commit/rollback sulla connessione."""

    def test_commit_persiste_dopo_uscita_context(self, clean_db):
        """conn.commit() esplicito + uscita pulita → dato persiste."""
        with clean_db._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO catasto.comune (nome, provincia, regione) "
                    "VALUES (%s, %s, %s) RETURNING id",
                    ("CommitTest", "PV", "Test"),
                )
                new_id = cur.fetchone()[0]
                conn.commit()

        # Dato visibile dopo l'uscita del context
        dettagli = clean_db.get_comune_by_id(new_id)
        assert dettagli is not None
        assert dettagli["nome_comune"] == "CommitTest"

    def test_rollback_esplicito_annulla(self, clean_db):
        """conn.rollback() prima dell'uscita → dato NON persiste."""
        new_id = None
        with clean_db._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO catasto.comune (nome, provincia, regione) "
                    "VALUES (%s, %s, %s) RETURNING id",
                    ("RollbackTest", "PV", "Test"),
                )
                new_id = cur.fetchone()[0]
                conn.rollback()

        # Dato NON visibile (rollback ha annullato l'insert)
        if new_id is not None:
            dettagli = clean_db.get_comune_by_id(new_id)
            assert dettagli is None
