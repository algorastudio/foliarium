"""
tests/unit/test_demo_visualizza_pdf.py
======================================
Anteprima dei PDF nella demo in Docker (`docker/demo/visualizza_pdf.py`).

Foliarium apre i PDF che genera con il programma predefinito del sistema
(`QDesktopServices.openUrl`). Nel container della demo non c'e' un sistema
desktop: senza un programma associato ai PDF, il pulsante «Apri» non
farebbe nulla. Questa finestra e' quel programma.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtPdfWidgets import QPdfView


pytestmark = [pytest.mark.unit, pytest.mark.gui]

MODULO = Path(__file__).resolve().parents[2] / "docker" / "demo" / "visualizza_pdf.py"


@pytest.fixture(scope="module")
def vp():
    spec = importlib.util.spec_from_file_location("demo_visualizza_pdf", MODULO)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture
def pdf_due_pagine(tmp_path) -> Path:
    from fpdf import FPDF

    documento = FPDF()
    for testo in ("Prima pagina", "Seconda pagina"):
        documento.add_page()
        documento.set_font("Helvetica", size=14)
        documento.cell(0, 10, testo)
    percorso = tmp_path / "relazione città.pdf"
    documento.output(str(percorso))
    return percorso


def test_titolo_con_il_nome_del_file(vp, qapp, pdf_due_pagine):
    finestra = vp.FinestraAnteprima(pdf_due_pagine)
    assert finestra.windowTitle() == "relazione città.pdf — Anteprima PDF"


def test_carica_tutte_le_pagine(vp, qapp, pdf_due_pagine):
    finestra = vp.FinestraAnteprima(pdf_due_pagine)
    assert finestra.documento.pageCount() == 2


def test_pagine_in_sequenza_adattate_alla_larghezza(vp, qapp, pdf_due_pagine):
    finestra = vp.FinestraAnteprima(pdf_due_pagine)
    assert finestra.vista.pageMode() == QPdfView.PageMode.MultiPage
    assert finestra.vista.zoomMode() == QPdfView.ZoomMode.FitToWidth


def test_lo_zoom_ingrandisce_e_riduce(vp, qapp, pdf_due_pagine):
    finestra = vp.FinestraAnteprima(pdf_due_pagine)
    finestra.ingrandisci()
    assert finestra.vista.zoomMode() == QPdfView.ZoomMode.Custom
    ingrandito = finestra.vista.zoomFactor()
    finestra.riduci()
    assert finestra.vista.zoomFactor() < ingrandito
    finestra.adatta_alla_larghezza()
    assert finestra.vista.zoomMode() == QPdfView.ZoomMode.FitToWidth


def test_lo_zoom_ha_un_limite(vp, qapp, pdf_due_pagine):
    finestra = vp.FinestraAnteprima(pdf_due_pagine)
    for _ in range(50):
        finestra.ingrandisci()
    assert finestra.vista.zoomFactor() <= vp.ZOOM_MASSIMO
    for _ in range(100):
        finestra.riduci()
    assert finestra.vista.zoomFactor() >= vp.ZOOM_MINIMO


def test_resta_sopra_la_finestra_principale(vp, qapp, pdf_due_pagine):
    # Senza barra delle applicazioni una finestra finita dietro quella
    # principale non si ritroverebbe piu'.
    finestra = vp.FinestraAnteprima(pdf_due_pagine)
    assert finestra.windowFlags() & Qt.WindowType.WindowStaysOnTopHint


def test_file_inesistente(vp, qapp, tmp_path):
    with pytest.raises(vp.ErroreAnteprima):
        vp.FinestraAnteprima(tmp_path / "non-esiste.pdf")


def test_file_che_non_e_un_pdf(vp, qapp, tmp_path):
    finto = tmp_path / "finto.pdf"
    finto.write_text("questo non e' un PDF", encoding="utf-8")
    with pytest.raises(vp.ErroreAnteprima):
        vp.FinestraAnteprima(finto)


def test_senza_argomenti_esce_con_errore_d_uso(vp):
    assert vp.main(["visualizza_pdf.py"]) == 2
