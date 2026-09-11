"""
foliarium.ui.undo — Annullamento dell'ultima operazione reversibile.

Perche' non un QUndoStack
-------------------------
QUndoStack e' fatto per una pila profonda di comandi su un documento in
memoria. Qui le operazioni sono gia' scritte su un database condiviso da
piu' archivisti: annullare la quinta azione a ritroso, mezz'ora dopo,
significherebbe sovrascrivere lavoro altrui senza che nessuno se ne
accorga. E su un archivio catastale la scrittura silenziosa e' il danno
peggiore.

Quello che serve davvero e' coprire l'errore appena commesso ("ho
archiviato la partita sbagliata"), quindi:

  * una sola azione annullabile per volta, la piu' recente;
  * con una scadenza (di default due minuti), oltre la quale sparisce;
  * annullata eseguendo l'operazione inversa sul database, non
    riscrivendo lo stato a mano;
  * azzerata al cambio utente.

La sicurezza in presenza di altri utenti arriva dal database: le
operazioni inverse (``ripristina_*``) filtrano sullo stato di partenza
(``WHERE id = %s AND archiviato``), quindi se nel frattempo qualcun altro
e' intervenuto l'annullamento fallisce con un errore esplicito invece di
sovrascrivere.

Cosa e' annullabile: archiviazione e ripristino, cioe' le operazioni che
hanno gia' un inverso esatto nel layer DB. Aggiornamenti ed eliminazioni
definitive restano fuori: il primo richiederebbe di conservare lo stato
precedente per intero, il secondo per definizione non ha inverso.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

_log = logging.getLogger("CatastoGUI.undo")

#: Quanto resta offerta l'azione di annullamento (millisecondi).
DURATA_PREDEFINITA_MS = 120_000


@dataclass
class AzioneAnnullabile:
    """Un'operazione appena eseguita e la sua inversa.

    Attributes:
        descrizione: frase al passato mostrata all'utente, es.
            "Comune «Savona» archiviato".
        annulla: esegue l'operazione inversa sul database. Puo' sollevare:
            l'eccezione viene mostrata come un normale errore utente.
        al_termine: opzionale, invocata dopo un annullamento riuscito per
            aggiornare la vista che aveva originato l'operazione.
    """

    descrizione: str
    annulla: Callable[[], None]
    al_termine: Optional[Callable[[], None]] = None


class GestoreAnnullamento(QObject):
    """Conserva l'ultima azione annullabile e ne gestisce la scadenza."""

    #: Emesso quando c'e' un'azione da offrire (porta la descrizione).
    disponibile = pyqtSignal(str)
    #: Emesso quando non c'e' piu' nulla da annullare (scadenza o consumo).
    esaurito = pyqtSignal()

    def __init__(self, parent=None, durata_ms: int = DURATA_PREDEFINITA_MS):
        super().__init__(parent)
        self._azione: Optional[AzioneAnnullabile] = None
        self._durata_ms = durata_ms
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.dimentica)

    # -- stato ------------------------------------------------------------

    @property
    def azione_corrente(self) -> Optional[AzioneAnnullabile]:
        return self._azione

    def ha_azione(self) -> bool:
        return self._azione is not None

    # -- registrazione ------------------------------------------------------

    def registra(self, azione: AzioneAnnullabile) -> None:
        """Rende annullabile l'operazione appena eseguita.

        Sostituisce l'eventuale azione precedente: se ne tiene una sola.
        """
        self._azione = azione
        self._timer.start(self._durata_ms)
        _log.debug("Azione annullabile registrata: %s", azione.descrizione)
        self.disponibile.emit(azione.descrizione)

    def dimentica(self) -> None:
        """Scarta l'azione corrente senza eseguirla (scadenza, logout…)."""
        self._timer.stop()
        if self._azione is not None:
            _log.debug("Azione annullabile scaduta: %s", self._azione.descrizione)
        self._azione = None
        self.esaurito.emit()

    # -- esecuzione ---------------------------------------------------------

    def annulla_ultima(self) -> Optional[str]:
        """Esegue l'operazione inversa. Ritorna la descrizione annullata.

        Ritorna None se non c'era nulla da annullare. Le eccezioni
        dell'operazione inversa vengono propagate al chiamante, che le
        mostra come un normale errore: il caso tipico e' un altro utente
        che e' gia' intervenuto sullo stesso record.
        """
        azione = self._azione
        if azione is None:
            return None

        # Si consuma subito: un annullamento fallito non va ritentato al
        # buio, e uno riuscito non va eseguito due volte.
        self._azione = None
        self._timer.stop()
        try:
            azione.annulla()
        finally:
            self.esaurito.emit()

        if azione.al_termine is not None:
            try:
                azione.al_termine()
            except Exception:      # pragma: no cover - solo aggiornamento vista
                _log.debug("Aggiornamento vista dopo annullamento fallito",
                           exc_info=True)
        _log.info("Annullata: %s", azione.descrizione)
        return azione.descrizione


# ---------------------------------------------------------------------------
# Istanza condivisa
# ---------------------------------------------------------------------------
#
# I widget che eseguono l'operazione non conoscono la finestra principale:
# passano da qui, la finestra si limita ad ascoltare i segnali.

_gestore: Optional[GestoreAnnullamento] = None


def gestore_annullamento() -> GestoreAnnullamento:
    """Il gestore condiviso dell'applicazione (creato alla prima chiamata)."""
    global _gestore
    # Un QObject senza genitore vive quanto il suo riferimento Python: se
    # il wrapper viene raccolto, l'oggetto C++ sparisce e ogni uso
    # successivo solleva RuntimeError. Appenderlo alla QApplication gli da'
    # una proprieta' stabile per tutta la durata del processo.
    if _gestore is not None:
        try:
            _gestore.objectName()      # tocca l'oggetto C++
        except RuntimeError:
            _gestore = None
    if _gestore is None:
        from PyQt6.QtWidgets import QApplication
        _gestore = GestoreAnnullamento(parent=QApplication.instance())
    return _gestore


def registra_azione_annullabile(
    descrizione: str,
    annulla: Callable[[], None],
    al_termine: Optional[Callable[[], None]] = None,
) -> None:
    """Scorciatoia: registra un'azione annullabile sul gestore condiviso."""
    gestore_annullamento().registra(
        AzioneAnnullabile(descrizione=descrizione, annulla=annulla,
                          al_termine=al_termine)
    )


__all__ = [
    "AzioneAnnullabile",
    "GestoreAnnullamento",
    "gestore_annullamento",
    "registra_azione_annullabile",
    "DURATA_PREDEFINITA_MS",
]
