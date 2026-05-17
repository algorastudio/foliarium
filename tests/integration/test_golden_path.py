"""
tests/integration/test_golden_path.py
======================================
Test end-to-end del workflow archivistico critico, **senza GUI**.

Protegge il "golden path" che l'utente esegue ogni giorno:

    Crea comune
       → crea località
       → crea possessore
       → crea partita principale
       → associa possessore alla partita
       → inserisce un immobile
       → registra una variazione (vendita) + contratto notarile
       → chiude la partita originale e crea la partita di destinazione
       → genera il report di proprietà e lo esporta in PDF

Se questo test passa, le regressioni più gravi sul dominio sono escluse
prima di toccare la GUI. Eseguibile in CI con PostgreSQL ma senza
QApplication: marker `integration` + `golden_path`.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pytest

from app_utils import FPDF_AVAILABLE


pytestmark = [
    pytest.mark.integration,
    pytest.mark.golden_path,
]


def _insert_variazione_and_contratto(db, partita_origine_id: int,
                                     nominativo: str,
                                     notaio: str, repertorio: str) -> int:
    """
    Inserisce una coppia variazione + contratto direttamente sul DB.
    Restituisce l'ID della variazione creata.

    Tenuto come helper locale per evitare di dipendere da procedure SQL
    di alto livello che potrebbero cambiare firma (registra_passaggio_…).
    """
    with db._get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO {db.schema}.variazione
                    (partita_origine_id, tipo, data_variazione,
                     nominativo_riferimento)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (partita_origine_id, "Vendita", date.today(), nominativo),
            )
            variazione_id = cur.fetchone()[0]

            cur.execute(
                f"""
                INSERT INTO {db.schema}.contratto
                    (variazione_id, tipo, data_contratto, notaio, repertorio)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    variazione_id,
                    "Atto di Compravendita",
                    date.today(),
                    notaio,
                    repertorio,
                ),
            )
            conn.commit()
    return variazione_id


def test_golden_path_partita_variazione_export_pdf(clean_db, tmp_path):
    """
    Happy-path completo: comune → possessore → partita → variazione → PDF.

    Asserzioni minime sul comportamento "visibile all'utente":
      * la partita originale finisce con stato 'chiusa'
      * la partita di destinazione è 'attiva' e ha la provenienza corretta
      * il PDF viene generato come file non vuoto e contiene almeno la magic
        di un PDF valido
    """
    if not FPDF_AVAILABLE:
        pytest.skip("fpdf2 non disponibile in questo ambiente")

    db = clean_db

    # ── 1. Anagrafica base ────────────────────────────────────────────────
    comune_id = db.aggiungi_comune("Golden Path Test", "GP", "Liguria")
    assert isinstance(comune_id, int) and comune_id > 0

    localita_id = db.insert_localita(
        comune_id=comune_id,
        nome="Repubblica",
        tipologia_stradale="Via",
    )
    assert isinstance(localita_id, int) and localita_id > 0

    venditore_id = db.create_possessore(
        nome_completo="ROSSI MARIO fu Antonio",
        comune_riferimento_id=comune_id,
        cognome_nome="ROSSI MARIO",
    )
    acquirente_id = db.create_possessore(
        nome_completo="BIANCHI ANNA fu Pietro",
        comune_riferimento_id=comune_id,
        cognome_nome="BIANCHI ANNA",
    )
    assert venditore_id > 0 and acquirente_id > 0

    # ── 2. Partita originale ──────────────────────────────────────────────
    partita_orig_id = db.create_partita(
        comune_id=comune_id,
        numero_partita=2001,
        tipo="principale",
        stato="attiva",
        data_impianto=date(1905, 6, 15),
    )
    assert partita_orig_id > 0

    ok = db.aggiungi_possessore_a_partita(
        partita_id=partita_orig_id,
        possessore_id=venditore_id,
        tipo_partita_rel="principale",
        titolo="proprietà esclusiva",
        quota="1/1",
    )
    assert ok is True

    immobile_id = db.inserisci_immobile(
        partita_id=partita_orig_id,
        natura="Casa di abitazione",
        localita_id=localita_id,
        numero_civico="17",
        classificazione="Civile",
        consistenza="vani 4",
        numero_piani=2,
        numero_vani=4,
    )
    assert immobile_id and immobile_id > 0

    # ── 3. Variazione + contratto ────────────────────────────────────────
    variazione_id = _insert_variazione_and_contratto(
        db,
        partita_origine_id=partita_orig_id,
        nominativo="BIANCHI ANNA fu Pietro",
        notaio="Notaio Verdi Luigi",
        repertorio="9876/1910",
    )
    assert variazione_id > 0

    # ── 4. Partita di destinazione e chiusura della precedente ───────────
    partita_nuova_id = db.create_partita(
        comune_id=comune_id,
        numero_partita=2002,
        tipo="principale",
        stato="attiva",
        data_impianto=date(1910, 11, 3),
        numero_provenienza=2001,
    )
    db.aggiungi_possessore_a_partita(
        partita_id=partita_nuova_id,
        possessore_id=acquirente_id,
        tipo_partita_rel="principale",
        titolo="proprietà esclusiva",
        quota="1/1",
    )
    db.update_partita(
        partita_id=partita_orig_id,
        dati_modificati={"stato": "inattiva", "data_chiusura": date.today()},
    )

    dettagli_orig = db.get_partita_details(partita_orig_id)
    dettagli_nuova = db.get_partita_details(partita_nuova_id)
    assert dettagli_orig is not None
    assert dettagli_nuova is not None
    assert dettagli_orig["stato"] in ("inattiva", "chiusa")
    assert dettagli_nuova["stato"] == "attiva"
    # numero_provenienza puo' essere serializzato come stringa (TEXT) o int
    # a seconda della versione dello schema (v1.6+ usa TEXT)
    assert str(dettagli_nuova.get("numero_provenienza")) == "2001"
    assert len(dettagli_nuova.get("possessori", [])) == 1
    assert dettagli_nuova["possessori"][0]["id"] == acquirente_id

    # ── 5. Export PDF del report di proprietà ────────────────────────────
    report_text = db.genera_report_proprieta(partita_nuova_id)
    assert isinstance(report_text, str) and len(report_text) > 0

    from app_utils import GenericTextReportPDF

    # Trattino normale (non em-dash U+2014) per evitare
    # FPDFUnicodeEncodingException: i font core di fpdf2 sono latin-1.
    pdf = GenericTextReportPDF(
        report_title=f"Partita {dettagli_nuova['numero_partita']} - "
                     f"{dettagli_nuova['comune_nome']}"
    )
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.add_report_text(report_text)

    out_path: Path = tmp_path / "golden_path_partita_2002.pdf"
    pdf.output(str(out_path))

    assert out_path.exists(), "Il file PDF non è stato creato"
    size = out_path.stat().st_size
    assert size > 1024, f"PDF troppo piccolo ({size} byte): probabile pagina vuota"

    with open(out_path, "rb") as fh:
        header = fh.read(5)
    assert header == b"%PDF-", "Il file generato non è un PDF valido"
