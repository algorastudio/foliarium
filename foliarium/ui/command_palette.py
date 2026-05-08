"""
foliarium.ui.command_palette — CommandPaletteDialog

Palette di navigazione rapida (Ctrl+K) in stile VS Code.
Estratta da gui_main.py in fase C.5 del refactoring.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QDialog, QFrame, QLineEdit, QListWidget,
                             QListWidgetItem, QVBoxLayout)


class CommandPaletteDialog(QDialog):
    """Palette di navigazione rapida in stile VS Code (Ctrl+K).

    Mostra le pagine disponibili filtrabili in tempo reale.
    Premendo Invio o doppio click naviga alla pagina selezionata.
    """

    page_selected = pyqtSignal(str)  # emette il page_name selezionato

    # Mappa page_name → label leggibile (per la ricerca testuale)
    _PAGE_LABELS: dict[str, str] = {
        "home":           "Home",
        "comuni":         "Comuni — archivio",
        "partite":        "Ricerca Partite",
        "immobili":       "Ricerca Immobili",
        "documenti":      "Ricerca Documenti",
        "fuzzy":          "Ricerca Globale (fuzzy)",
        "archivio":       "Archiviati",
        "ins_wizard":     "Nuova Partita (Wizard)",
        "ins_comune":     "Inserimento Comune",
        "ins_possessore": "Inserimento Possessore",
        "ins_localita":   "Inserimento Località",
        "ins_partita":    "Inserimento Partita",
        "reg_proprieta":  "Registrazione Proprietà",
        "reg_consult":    "Registrazione Consultazione",
        "operazioni":     "Operazioni partita",
        "esportazioni":   "Esportazioni",
        "report":         "Reportistica",
        "statistiche":    "Statistiche",
        "utenti":         "Gestione Utenti",
        "audit":          "Audit Log",
        "backup":         "Backup",
        "tabelle_sistema":"Tabelle di sistema",
    }

    def __init__(self, available_pages: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Vai a…")
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Cerca pagina… (Ctrl+K per chiudere)")
        self._search.setObjectName("cmdPaletteSearch")
        layout.addWidget(self._search)

        self._list = QListWidget()
        self._list.setObjectName("cmdPaletteList")
        self._list.setFrameShape(QFrame.Shape.NoFrame)
        layout.addWidget(self._list)

        # Popola con le pagine disponibili
        self._available = available_pages
        self._populate("")

        self._search.textChanged.connect(self._populate)
        self._search.returnPressed.connect(self._accept_current)
        self._list.itemDoubleClicked.connect(self._accept_item)

        # Frecce su/giù dalla search box spostano la selezione nella lista
        self._search.installEventFilter(self)

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if obj is self._search and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Down:
                cur = self._list.currentRow()
                self._list.setCurrentRow(min(cur + 1, self._list.count() - 1))
                return True
            if key == Qt.Key.Key_Up:
                self._list.setCurrentRow(max(self._list.currentRow() - 1, 0))
                return True
            if key == Qt.Key.Key_Escape:
                self.reject()
                return True
        return super().eventFilter(obj, event)

    def _populate(self, text: str = ""):
        self._list.clear()
        query = text.strip().lower()
        for page in self._available:
            label = self._PAGE_LABELS.get(page, page.replace("_", " ").title())
            if not query or query in label.lower() or query in page.lower():
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, page)
                self._list.addItem(item)
        if self._list.count():
            self._list.setCurrentRow(0)

    def _accept_current(self):
        item = self._list.currentItem()
        if item:
            self._accept_item(item)

    def _accept_item(self, item: QListWidgetItem):
        page = item.data(Qt.ItemDataRole.UserRole)
        self.page_selected.emit(page)
        self.accept()

    def showEvent(self, event):
        super().showEvent(event)
        self._search.setFocus()
        # Centra il dialog rispetto alla finestra padre
        if self.parent():
            parent_geo = self.parent().geometry()
            x = parent_geo.x() + (parent_geo.width() - self.width()) // 2
            y = parent_geo.y() + max(80, (parent_geo.height() - self.height()) // 4)
            self.move(x, y)
