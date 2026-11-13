#!/usr/bin/env python3
"""
docker/demo/visualizza_pdf.py — anteprima dei PDF nella demo.

Foliarium apre i PDF che genera con il programma predefinito del sistema
(QDesktopServices.openUrl). Nel container della demo non c'e' un ambiente
desktop: senza un programma associato ai PDF, il pulsante «Apri» dopo
un'esportazione non farebbe nulla. Questa finestra e' quel programma; la
associa ai PDF il file foliarium-pdf.desktop.

Usa QPdfView, lo stesso componente del visualizzatore di documenti interno
a Foliarium: nessun pacchetto in piu' nell'immagine e lo stesso aspetto.

Uso:
    python visualizza_pdf.py <file.pdf>
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox, QToolBar

PASSO_ZOOM = 1.25
ZOOM_MINIMO = 0.25
ZOOM_MASSIMO = 5.0


class ErroreAnteprima(Exception):
    """Il file non esiste o non e' un PDF leggibile."""


class FinestraAnteprima(QMainWindow):
    """Finestra con le pagine del PDF in sequenza, adattate alla larghezza."""

    def __init__(self, percorso: Path):
        super().__init__()
        percorso = Path(percorso)

        self.documento = QPdfDocument(self)
        esito = self.documento.load(str(percorso))
        if esito != QPdfDocument.Error.None_ or self.documento.pageCount() < 1:
            raise ErroreAnteprima(f"Impossibile aprire «{percorso.name}» come PDF.")

        self.setWindowTitle(f"{percorso.name} — Anteprima PDF")
        # Nella demo non c'e' una barra delle applicazioni: una finestra
        # finita dietro quella principale non si ritroverebbe piu'.
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.resize(900, 760)

        self.vista = QPdfView(self)
        self.vista.setDocument(self.documento)
        self.vista.setPageMode(QPdfView.PageMode.MultiPage)
        self.vista.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        self.setCentralWidget(self.vista)

        barra = QToolBar("Anteprima", self)
        barra.setMovable(False)
        barra.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.addToolBar(barra)

        self._azione(barra, "Zoom &+", self.ingrandisci, QKeySequence.StandardKey.ZoomIn)
        self._azione(barra, "Zoom &−", self.riduci, QKeySequence.StandardKey.ZoomOut)
        self._azione(barra, "&Adatta alla larghezza", self.adatta_alla_larghezza, None)
        barra.addSeparator()
        self._azione(barra, "&Chiudi", self.close, QKeySequence(Qt.Key.Key_Escape))

    def _azione(self, barra: QToolBar, testo: str, funzione, scorciatoia) -> None:
        azione = QAction(testo, self)
        if scorciatoia is not None:
            azione.setShortcut(scorciatoia)
        azione.triggered.connect(lambda _attivo=False: funzione())
        barra.addAction(azione)

    def _fattore_corrente(self) -> float:
        fattore = self.vista.zoomFactor()
        return fattore if fattore > 0 else 1.0

    def _imposta_zoom(self, fattore: float) -> None:
        # Si legge il fattore PRIMA di passare a Custom: in modalita'
        # "adatta alla larghezza" quello riportato e' l'ultimo impostato a
        # mano, non quello effettivo.
        self.vista.setZoomMode(QPdfView.ZoomMode.Custom)
        self.vista.setZoomFactor(max(ZOOM_MINIMO, min(ZOOM_MASSIMO, fattore)))

    def ingrandisci(self) -> None:
        self._imposta_zoom(self._fattore_corrente() * PASSO_ZOOM)

    def riduci(self) -> None:
        self._imposta_zoom(self._fattore_corrente() / PASSO_ZOOM)

    def adatta_alla_larghezza(self) -> None:
        self.vista.setZoomMode(QPdfView.ZoomMode.FitToWidth)


def main(argv: List[str]) -> int:
    if len(argv) != 2:
        print("uso: visualizza_pdf.py <file.pdf>", file=sys.stderr)
        return 2

    app = QApplication(argv[:1])
    app.setApplicationName("Anteprima PDF")
    try:
        finestra = FinestraAnteprima(Path(argv[1]))
    except ErroreAnteprima as errore:
        QMessageBox.critical(None, "Anteprima PDF", str(errore))
        return 1
    finestra.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
