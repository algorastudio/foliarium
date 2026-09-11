
import logging
from typing import List, Dict

# Importazioni PyQt6
from PyQt6.QtCore import Qt

from PyQt6.QtGui import (QColor, QFont)

# QWebEngineView: opzionale, riservato a future funzionalità web
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    WEB_ENGINE_AVAILABLE = True
except ImportError:
    QWebEngineView = None
    WEB_ENGINE_AVAILABLE = False

from PyQt6.QtWidgets import (QAbstractItemView, QApplication,
                             QFrame, QLineEdit, QSizePolicy, QTableWidget,
                             QTableWidgetItem, QWidget)
# Importazione commentata (da abilitare se necessario)
# from PyQt6.QtSvgWidgets import QSvgWidget


def show_status_message(message: str, timeout_ms: int = 4000) -> None:
    """Mostra un messaggio nella status bar della finestra principale (non bloccante).

    Funziona da qualsiasi contesto (widget, dialog, thread UI) cercando la
    prima QMainWindow visibile tramite topLevelWidgets().
    """
    win = QApplication.activeWindow()
    if win is None or not hasattr(win, "statusBar"):
        for w in QApplication.topLevelWidgets():
            if hasattr(w, "statusBar") and w.isVisible():
                win = w
                break
    if win and hasattr(win, "statusBar"):
        try:
            win.statusBar().showMessage(message, timeout_ms)
        except Exception:
            pass


class ImmobiliTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super(ImmobiliTableWidget, self).__init__(parent)

        # Impostazione colonne
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(
            ["ID", "Natura", "Classificazione", "Consistenza", "Località"])

        # Altre impostazioni
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setStretchLastSection(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSortingEnabled(True)

    def populate_data(self, immobili: List[Dict]):
        """Popola la tabella con i dati degli immobili."""
        self.setRowCount(0)  # Resetta la tabella

        for immobile in immobili:
            row_position = self.rowCount()
            self.insertRow(row_position)

            # Imposta i dati per ogni cella
            self.setItem(row_position, 0, QTableWidgetItem(
                str(immobile.get('id', ''))))
            self.setItem(row_position, 1, QTableWidgetItem(
                immobile.get('natura', '')))
            self.setItem(row_position, 2, QTableWidgetItem(
                immobile.get('classificazione', '')))
            self.setItem(row_position, 3, QTableWidgetItem(
                immobile.get('consistenza', '')))

            # Informazioni sulla località (v1.7.0: tipologia + nome + civico)
            from app_utils import format_indirizzo
            localita_text = format_indirizzo(
                immobile.get('tipologia_stradale') or immobile.get('localita_tipo'),
                immobile.get('localita_nome'),
                immobile.get('numero_civico'),
            )

            self.setItem(row_position, 4, QTableWidgetItem(localita_text))

        # Adatta le dimensioni delle colonne al contenuto
        self.resizeColumnsToContents()
class QPasswordLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEchoMode(QLineEdit.EchoMode.Password)
# In custom_widgets.py


class FormDraftMixin:
    """Salva e riprende il contenuto di un modulo come bozza sul database.

    I wizard avevano gia' le bozze (``catasto.partita_draft``); i moduli di
    inserimento semplice no, quindi un modulo compilato a meta' si perdeva
    a fine giornata. Qui si riusa la stessa tabella: il payload e' lo stato
    dei campi, indicizzato per nome di attributo, e ``wizard_kind`` tiene
    separate le liste per tipo di modulo.

    Il modulo che adotta il mixin deve dichiarare:
        _DRAFT_KIND      costante wizard_kind del modulo
        _DRAFT_ETICHETTA descrizione breve usata nei messaggi
    e avere gli attributi ``db_manager`` e (se disponibile) ``utente_id``.

    Il salvataggio non ha un pulsante dedicato: passa dal dialogo che
    compare quando si lascia un modulo compilato. Aggiungere due bottoni in
    una barra che ne ha gia' cinque avrebbe peggiorato proprio cio' che
    questa revisione cerca di alleggerire.
    """

    _DRAFT_KIND: str = ""
    _DRAFT_ETICHETTA: str = "modulo"

    # -- raccolta dei campi -------------------------------------------------

    def _campi_bozza(self) -> dict:
        """Campi di input del modulo, per nome di attributo.

        Il nome dell'attributo e' una chiave stabile fra sessioni e
        versioni, a differenza dell'ordine dei widget nel layout.
        """
        from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDateEdit,
                                     QLineEdit, QSpinBox, QTextEdit)
        tipi = (QLineEdit, QTextEdit, QSpinBox, QCheckBox, QDateEdit, QComboBox)
        return {
            nome: valore for nome, valore in vars(self).items()
            if isinstance(valore, tipi)
        }

    def serializza_bozza(self) -> dict:
        """Stato corrente dei campi, in una forma salvabile come JSON."""
        from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDateEdit,
                                     QLineEdit, QSpinBox, QTextEdit)
        stato = {}
        for nome, campo in self._campi_bozza().items():
            if isinstance(campo, QLineEdit):
                stato[nome] = {"tipo": "testo", "valore": campo.text()}
            elif isinstance(campo, QTextEdit):
                stato[nome] = {"tipo": "testo_lungo", "valore": campo.toPlainText()}
            elif isinstance(campo, QSpinBox):
                stato[nome] = {"tipo": "numero", "valore": campo.value()}
            elif isinstance(campo, QCheckBox):
                stato[nome] = {"tipo": "spunta", "valore": campo.isChecked()}
            elif isinstance(campo, QDateEdit):
                stato[nome] = {"tipo": "data",
                               "valore": campo.date().toString("yyyy-MM-dd")}
            elif isinstance(campo, QComboBox):
                # Si salvano sia il dato sia il testo: alla ripresa il menu
                # puo' essere stato ripopolato in ordine diverso, e il testo
                # permette di ritrovare la voce giusta.
                dato = campo.currentData()
                stato[nome] = {
                    "tipo": "scelta",
                    "valore": dato if isinstance(dato, (int, str, type(None))) else None,
                    "testo": campo.currentText(),
                }
        return stato

    def ripristina_bozza(self, stato: dict) -> None:
        """Riporta i campi allo stato salvato, ignorando quelli spariti."""
        from PyQt6.QtCore import QDate
        from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDateEdit,
                                     QLineEdit, QSpinBox, QTextEdit)
        campi = self._campi_bozza()
        for nome, voce in (stato or {}).items():
            campo = campi.get(nome)
            if campo is None or not isinstance(voce, dict):
                continue      # il modulo e' cambiato: si salta il campo
            valore = voce.get("valore")
            if isinstance(campo, QLineEdit):
                campo.setText(str(valore or ""))
            elif isinstance(campo, QTextEdit):
                campo.setPlainText(str(valore or ""))
            elif isinstance(campo, QSpinBox):
                if isinstance(valore, int):
                    campo.setValue(valore)
            elif isinstance(campo, QCheckBox):
                campo.setChecked(bool(valore))
            elif isinstance(campo, QDateEdit):
                data = QDate.fromString(str(valore or ""), "yyyy-MM-dd")
                if data.isValid():
                    campo.setDate(data)
            elif isinstance(campo, QComboBox):
                indice = campo.findData(valore) if valore is not None else -1
                if indice < 0 and voce.get("testo"):
                    indice = campo.findText(voce["testo"])
                if indice >= 0:
                    campo.setCurrentIndex(indice)

    # -- persistenza --------------------------------------------------------

    def _titolo_bozza(self) -> str:
        from datetime import datetime
        return f"{self._DRAFT_ETICHETTA} — {datetime.now():%d/%m/%Y %H:%M}"

    def save_pending_changes(self) -> bool:
        """Salva il modulo come bozza riprendibile. True se salvata.

        Fa parte del protocollo letto da CatastoMainWindow: la sua presenza
        e' cio' che fa comparire "Salva bozza" nel dialogo di uscita.
        """
        if not self._DRAFT_KIND or getattr(self, "db_manager", None) is None:
            return False
        try:
            draft_id = self.db_manager.save_partita_draft(
                utente_id=getattr(self, "utente_id", None),
                titolo=self._titolo_bozza(),
                payload=self.serializza_bozza(),
                draft_id=getattr(self, "_draft_id_corrente", None),
                wizard_kind=self._DRAFT_KIND,
            )
        except Exception:
            self.logger.error("Salvataggio bozza fallito", exc_info=True)
            raise
        self._draft_id_corrente = int(draft_id)
        show_status_message(
            f"Bozza salvata: puoi riprenderla da «Riprendi bozza…».", 5000)
        if hasattr(self, "mark_form_clean"):
            self.mark_form_clean()
        return True

    def elenca_bozze(self) -> list:
        """Bozze salvate per questo tipo di modulo, più recenti prima."""
        if not self._DRAFT_KIND or getattr(self, "db_manager", None) is None:
            return []
        return self.db_manager.list_partita_drafts(
            utente_id=getattr(self, "utente_id", None),
            wizard_kind=self._DRAFT_KIND,
        )

    def _riprendi_bozza(self) -> None:
        """Chiede quale bozza riaprire e la carica nei campi del modulo."""
        from PyQt6.QtWidgets import QInputDialog, QMessageBox

        try:
            bozze = self.elenca_bozze()
        except Exception as e:
            from foliarium.ui.errors import show_user_error
            show_user_error(self, "Elenco bozze", e,
                            logger=getattr(self, "logger", None))
            return

        if not bozze:
            QMessageBox.information(
                self, "Nessuna bozza",
                "Non ci sono bozze salvate per questo modulo.\n\n"
                "Una bozza viene proposta quando lasci un modulo compilato "
                "senza averlo salvato.",
            )
            return

        etichette = [
            f"{b.get('titolo') or 'senza titolo'}"
            f"  (aggiornata il {b['updated_at']:%d/%m/%Y %H:%M})"
            if b.get("updated_at") else (b.get("titolo") or "senza titolo")
            for b in bozze
        ]
        scelta, ok = QInputDialog.getItem(
            self, "Riprendi bozza", "Bozza da riaprire:", etichette, 0, False)
        if not ok or not scelta:
            return

        bozza = bozze[etichette.index(scelta)]
        try:
            self.carica_bozza(int(bozza["id"]))
        except Exception as e:
            from foliarium.ui.errors import show_user_error
            show_user_error(self, "Caricamento bozza", e,
                            logger=getattr(self, "logger", None))
            return
        show_status_message("Bozza caricata nel modulo.", 4000)

    def carica_bozza(self, draft_id: int) -> None:
        """Carica la bozza indicata nei campi del modulo."""
        bozza = self.db_manager.load_partita_draft(
            draft_id,
            utente_id=getattr(self, "utente_id", None),
            wizard_kind=self._DRAFT_KIND,
        )
        self.ripristina_bozza(bozza.get("payload") or {})
        self._draft_id_corrente = int(draft_id)
        if hasattr(self, "mark_form_clean"):
            self.mark_form_clean()


def imposta_nomi_accessibili(contenitore, nomi: dict) -> None:
    """Dà un nome parlante ai campi per le tecnologie assistive.

    Le etichette dei moduli sono QLabel separate, per giunta in rich text
    (contengono l'asterisco rosso dei campi obbligatori): Qt non le associa
    da solo al campo che descrivono, quindi uno screen reader annuncia
    "casella di testo" e basta. ``setAccessibleName`` colma la distanza
    senza toccare quello che si vede a schermo.

    Args:
        contenitore: il widget del modulo.
        nomi: attributo del widget -> nome da annunciare.
    """
    for attributo, nome in nomi.items():
        campo = getattr(contenitore, attributo, None)
        if campo is not None:
            campo.setAccessibleName(nome)


class UnsavedFormMixin:
    """Rileva se un form contiene dati compilati e non ancora salvati.

    Invece di elencare i campi a mano form per form, confronta lo stato
    corrente dei widget di input con uno scatto preso quando il form era
    pulito. Cosi' un default (la provincia "SV", la data di oggi) non viene
    scambiato per lavoro dell'utente.

    Il form deve chiamare ``mark_form_clean()`` quando torna in uno stato
    pulito: dopo il caricamento iniziale dei menu a tendina, dopo "Pulisci
    campi" e dopo un salvataggio riuscito. Finche' non viene chiamato,
    ``has_unsaved_changes()`` risponde False: meglio nessun avviso che un
    avviso sbagliato.
    """

    _form_baseline = None

    def _form_snapshot(self) -> tuple:
        """Stato dei campi, diviso fra testo digitato e selezioni.

        La distinzione serve alla soglia di ``has_unsaved_changes()``: del
        testo scritto a mano e' lavoro da proteggere, un indice di menu a
        tendina cambiato da solo no.
        """
        from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDateEdit,
                                     QLineEdit, QSpinBox, QTextEdit)
        testo = {}
        for campo in self.findChildren(QLineEdit):
            testo[id(campo)] = campo.text()
        for campo in self.findChildren(QTextEdit):
            testo[id(campo)] = campo.toPlainText()

        selezioni = {}
        for campo in self.findChildren(QSpinBox):
            selezioni[id(campo)] = campo.value()
        for campo in self.findChildren(QCheckBox):
            selezioni[id(campo)] = campo.isChecked()
        for campo in self.findChildren(QDateEdit):
            selezioni[id(campo)] = campo.date()
        for campo in self.findChildren(QComboBox):
            selezioni[id(campo)] = campo.currentIndex()
        return testo, selezioni

    def mark_form_clean(self) -> None:
        """Registra lo stato attuale come 'nessuna modifica da salvare'."""
        self._form_baseline = self._form_snapshot()

    def has_unsaved_changes(self) -> bool:
        """True se c'e' lavoro dell'utente che andrebbe perso.

        Soglia deliberatamente alta: del testo digitato basta da solo, ma
        per le sole selezioni ne servono almeno due. Un utente che apre il
        modulo e sfiora un menu a tendina non deve ricevere un avviso —
        avvisi che si rivelano infondati insegnano a ignorarli.
        """
        if self._form_baseline is None:
            return False
        try:
            testo, selezioni = self._form_snapshot()
        except RuntimeError:
            # Widget gia' distrutti durante la chiusura: niente da salvare.
            return False

        testo_base, selezioni_base = self._form_baseline
        if any(valore != testo_base.get(chiave, valore)
               for chiave, valore in testo.items()):
            return True
        cambiate = sum(1 for chiave, valore in selezioni.items()
                       if valore != selezioni_base.get(chiave, valore))
        return cambiate >= 2

    def discard_pending_changes(self) -> None:
        """L'utente ha accettato di perdere i dati: non si riavvisa."""
        self.mark_form_clean()


class LazyLoadedWidget(QWidget):
    """
    Una classe base per tutti i widget che necessitano di caricare dati
    solo la prima volta che vengono visualizzati (lazy loading).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data_loaded = False
        # Ogni sottoclasse dovrebbe avere il proprio logger
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")

    def load_initial_data(self):
        """
        Metodo universale chiamato dalla finestra principale.
        Controlla se i dati sono già stati caricati e, in caso negativo,
        chiama il metodo di caricamento specifico della sottoclasse.
        """
        if self._data_loaded:
            return  # Non fare nulla se già caricato

        self.logger.info(f"Esecuzione lazy loading per {self.__class__.__name__}...")
        self._load_data_on_first_show() # Chiama il metodo che le sottoclassi implementeranno
        self._data_loaded = True

    def _load_data_on_first_show(self):
        """
        Metodo astratto. Le sottoclassi DEVONO sovrascrivere questo metodo
        per implementare la loro logica di caricamento dati.
        """
        # self.logger.warning(f"Metodo _load_data_on_first_show non implementato per {self.__class__.__name__}")
        # Usiamo pass per non mostrare avvisi per widget che potrebbero non averne bisogno
        

# ── StatCard ─────────────────────────────────────────────────────────────────

from PyQt6.QtGui import QPainter, QPen, QBrush
from PyQt6.QtCore import QRect, QRectF

class StatCard(QFrame):
    """Stat card pittata con QPainter: bordo arrotondato, accent bar, ombra leggera.

    Theme-aware: il colore di sfondo della card e del testo titolo
    viene letto dalla palette del widget, quindi si adatta automaticamente
    a tema chiaro/scuro.
    """

    def __init__(self, title: str, accent_color: str = "#3F51B5", parent=None):
        super().__init__(parent)
        self._title = title
        self._value = "—"
        self._accent = QColor(accent_color)
        self.setMinimumSize(120, 100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(108)

    def setValue(self, value):
        self._value = str(value)
        self.update()

    def _is_dark_theme(self) -> bool:
        """Determina se il tema corrente è scuro dalla luminanza del background."""
        from PyQt6.QtGui import QPalette
        bg = self.palette().color(QPalette.ColorRole.Window)
        # luminanza percepita (formula standard ITU BT.709)
        luminance = 0.2126 * bg.red() + 0.7152 * bg.green() + 0.0722 * bg.blue()
        return luminance < 128

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        dark = self._is_dark_theme()

        # Palette tema-aware
        if dark:
            card_bg = QColor("#1E2030")
            shadow_alpha = 80
            title_color = QColor("#A0A8BC")
            border_alpha = 100
        else:
            card_bg = QColor("#FFFFFF")
            shadow_alpha = 22
            title_color = QColor("#5A6478")
            border_alpha = 50

        # Ombra leggera (offset sotto/destra)
        shadow_rect = QRectF(3, 4, w - 4, h - 4)
        painter.setBrush(QBrush(QColor(0, 0, 0, shadow_alpha)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(shadow_rect, 10, 10)

        # Card background
        card_rect = QRectF(0, 0, w - 3, h - 3)
        painter.setBrush(QBrush(card_bg))
        painter.setPen(QPen(QColor(self._accent.red(), self._accent.green(),
                                   self._accent.blue(), border_alpha), 1))
        painter.drawRoundedRect(card_rect, 10, 10)

        # Accent bar sinistra (4px)
        bar_rect = QRectF(0, 0, 5, h - 3)
        painter.setBrush(QBrush(self._accent))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(bar_rect, 5, 5)
        # Copertura angolo destro della bar
        painter.drawRect(QRectF(3, 0, 2, h - 3))

        # Titolo
        title_font = QFont("Segoe UI", 9)
        title_font.setWeight(QFont.Weight.DemiBold)
        title_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.5)
        painter.setFont(title_font)
        painter.setPen(QPen(title_color))
        title_rect = QRect(18, 14, w - 22, 20)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         self._title.upper())

        # Valore
        value_font = QFont("Segoe UI", 24)
        value_font.setWeight(QFont.Weight.Bold)
        painter.setFont(value_font)
        # Nel tema scuro alziamo la luminosità dell'accent per migliore contrasto
        if dark:
            accent_render = self._accent.lighter(140)
        else:
            accent_render = self._accent
        painter.setPen(QPen(accent_render))
        value_rect = QRect(14, 36, w - 18, 56)
        painter.drawText(value_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         self._value)

        painter.end()
