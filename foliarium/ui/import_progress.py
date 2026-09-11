"""
foliarium.ui.import_progress — Import di massa con avanzamento e annullamento.

Gli import CSV/Excel giravano nel thread della GUI con il solo cursore a
clessidra: su un file di qualche migliaio di righe la finestra smetteva di
rispondere e l'utente non aveva modo di sapere se stesse procedendo, ne' di
fermarla.

Qui l'import viene eseguito in un QThread mentre la finestra mostra righe
elaborate su totali e un pulsante Annulla.

Nota sull'annullamento: l'import e' transazionale *per riga* (ogni riga ha
il suo SAVEPOINT), quindi fermarsi a meta' lascia registrate le righe gia'
importate. Il riepilogo lo dichiara esplicitamente.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import QProgressDialog

_log = logging.getLogger("CatastoGUI.import")


class ImportWorker(QThread):
    """Esegue una funzione di import passandole un callback di avanzamento."""

    progresso = pyqtSignal(int, int)        # (elaborate, totali)
    finito = pyqtSignal(dict)               # risultato dell'import
    fallito = pyqtSignal(object)            # eccezione

    def __init__(self, funzione: Callable[..., Dict[str, Any]], *args, parent=None):
        super().__init__(parent)
        self._funzione = funzione
        self._args = args
        self._annullato = False

    def annulla(self) -> None:
        """Richiesta di interruzione: ha effetto alla riga successiva."""
        self._annullato = True

    def _callback(self, elaborate: int, totali: int) -> bool:
        self.progresso.emit(elaborate, totali)
        return not self._annullato

    def run(self) -> None:
        try:
            risultato = self._funzione(*self._args, progress_cb=self._callback)
            self.finito.emit(risultato or {})
        except Exception as e:            # l'eccezione viaggia al thread GUI
            self.fallito.emit(e)


def esegui_import_con_progresso(
    parent,
    titolo: str,
    funzione: Callable[..., Dict[str, Any]],
    *args,
    logger: Optional[logging.Logger] = None,
) -> Optional[Dict[str, Any]]:
    """Esegue l'import mostrando avanzamento e Annulla. Ritorna il risultato.

    Ritorna ``None`` se l'import e' fallito (l'errore e' gia' stato mostrato
    all'utente). Il dizionario restituito contiene le chiavi ``success``,
    ``errors`` e ``interrotto``.
    """
    log = logger or _log

    finestra = QProgressDialog("Preparazione…", "Annulla", 0, 0, parent)
    finestra.setWindowTitle(titolo)
    finestra.setWindowModality(Qt.WindowModality.WindowModal)
    finestra.setMinimumWidth(420)
    finestra.setAutoClose(False)
    finestra.setAutoReset(False)
    # Senza questo la finestra compare anche per un file di dieci righe,
    # lampeggiando per una frazione di secondo.
    finestra.setMinimumDuration(400)

    worker = ImportWorker(funzione, *args, parent=parent)
    esito: Dict[str, Any] = {}
    errore: list = []

    def _su_progresso(elaborate: int, totali: int) -> None:
        if totali and finestra.maximum() != totali:
            finestra.setMaximum(totali)
        finestra.setValue(elaborate)
        finestra.setLabelText(f"Importazione in corso… {elaborate} di {totali} righe")

    def _su_fine(risultato: Dict[str, Any]) -> None:
        esito.update(risultato)
        finestra.reset()

    def _su_errore(e: Exception) -> None:
        errore.append(e)
        finestra.reset()

    worker.progresso.connect(_su_progresso)
    worker.finito.connect(_su_fine)
    worker.fallito.connect(_su_errore)
    finestra.canceled.connect(worker.annulla)

    from PyQt6.QtWidgets import QApplication

    worker.start()
    while not worker.isFinished():
        # Tiene viva la finestra di avanzamento senza bloccare il thread GUI.
        worker.wait(50)
        QApplication.processEvents()
    worker.wait()
    # I segnali fra thread sono accodati: senza questo giro finale l'ultimo
    # 'finito' potrebbe restare in coda e l'esito tornare vuoto.
    QApplication.processEvents()
    finestra.close()

    if errore:
        from foliarium.ui.errors import show_user_error
        show_user_error(parent, titolo, errore[0], logger=log)
        return None

    return esito


__all__ = ["ImportWorker", "esegui_import_con_progresso"]
