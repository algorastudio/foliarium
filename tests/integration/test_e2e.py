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
        assert dettagli["nome"] == "E2E Comune Test"
        assert dettagli["provincia"] == "GE"

    def test_update_comune(self, clean_db):
        comune_id = clean_db.aggiungi_comune("E2E Update", "SV", "Liguria")
        ok = clean_db.update_comune(comune_id, {"provincia": "IM", "note": "aggiornato"})
        assert ok is True

        dettagli = clean_db.get_comune_by_id(comune_id)
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
        """update_possessore(possessore_id, dati_modificati: dict) v1.5.0+."""
        db = sample_data["db"]
        # sample_data crea gia' un possessore "TEST MARIO" nel comune di Genova
        pid = sample_data["possessore1_id"]

        ok = db.update_possessore(pid, {"note": "aggiornato in test E2E"})
        # Alcuni mixin restituiscono True/False, altri lo lasciano implicito
        # Accettiamo entrambi (la verifica e' che la nota sia stata salvata)
        assert ok is not False

        # Verifica via get_possessori_by_comune (filter_text)
        results = db.get_possessori_by_comune(
            sample_data["comune_id"], filter_text="TEST MARIO",
        )
        match = [p for p in results if p["id"] == pid]
        assert len(match) == 1
        assert match[0].get("note") == "aggiornato in test E2E"


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
