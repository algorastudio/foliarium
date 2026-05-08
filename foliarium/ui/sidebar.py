"""
foliarium.ui.sidebar — SidebarWidget

Navigazione verticale in stile VS Code, con sezioni e bottoni
filtrati per ruolo. Estratta da gui_main.py in fase C.5 del refactoring.
"""
from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import (QFrame, QLabel, QPushButton, QScrollArea,
                             QSizePolicy, QVBoxLayout, QWidget)

from app_paths import get_icon_path


class SidebarWidget(QWidget):
    page_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(220)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._container = QWidget()
        self._nav_layout = QVBoxLayout(self._container)
        self._nav_layout.setContentsMargins(0, 8, 0, 8)
        self._nav_layout.setSpacing(0)
        self._nav_layout.addStretch()

        scroll.setWidget(self._container)
        outer.addWidget(scroll)

        # Dict page_name -> QPushButton
        self._buttons: dict[str, QPushButton] = {}

    def build_nav(self, is_admin: bool, fuzzy_available: bool = False):
        """Costruisce i bottoni di navigazione in base al ruolo."""
        # Rimuove widget esistenti (tranne lo stretch finale)
        while self._nav_layout.count() > 1:
            item = self._nav_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._buttons.clear()

        layout = self._nav_layout

        def insert(lbl, page, icon=""):
            self._add_nav_button(layout, lbl, page, icon)

        # Home
        insert("Home", "home", "home")

        # ARCHIVIO — consultazione e ricerca
        self._add_section(layout, "ARCHIVIO")
        insert("Comuni", "comuni", "building")
        insert("Ricerca Partite", "partite", "search")
        insert("Ricerca Immobili", "immobili", "search")
        insert("Ricerca Documenti", "documenti", "file-text")
        if fuzzy_available:
            insert("Ricerca Globale", "fuzzy", "globe")
        # Archivio (record archiviati): è un'operazione di consultazione/recupero,
        # non di configurazione — collocato qui sotto ARCHIVIO è semanticamente corretto.
        if is_admin:
            insert("Archiviati", "archivio", "archive")

        # INSERIMENTO — il wizard guida il flusso Comune → Possessore → Partita
        self._add_section(layout, "INSERIMENTO")
        insert("Nuova Partita (Wizard)", "ins_wizard", "magic")
        insert("Comune", "ins_comune", "building")
        insert("Possessore", "ins_possessore", "user")
        insert("Partita", "ins_partita", "file-text")
        insert("Località", "ins_localita", "map-pin")
        insert("Reg. Proprietà", "reg_proprieta", "key")
        insert("Reg. Consultazione", "reg_consult", "book")

        # ANALISI
        self._add_section(layout, "ANALISI")
        insert("Esportazioni", "esportazioni", "download")
        insert("Report", "report", "report")
        insert("Statistiche", "statistiche", "bar-chart")

        # AMMINISTRAZIONE (admin only) — fonde le precedenti CONFIGURAZIONE e SISTEMA
        if is_admin:
            self._add_section(layout, "AMMINISTRAZIONE")
            insert("Operazioni", "operazioni", "settings")
            insert("Utenti", "utenti", "users")
            insert("Backup", "backup", "database")
            insert("Audit Log", "audit", "shield")
            insert("Tabelle di sistema", "tabelle_sistema", "table")

        layout.addStretch()

    def _add_section(self, layout: QVBoxLayout, label: str):
        lbl = QLabel(label)
        lbl.setObjectName("sectionLabel")
        lbl.setEnabled(False)
        layout.addWidget(lbl)

    def _add_nav_button(self, layout: QVBoxLayout, label: str, page_name: str,
                        icon_name: str = ""):
        btn = QPushButton(label)
        btn.setObjectName("navButton")
        btn.setFlat(True)
        btn.setCheckable(False)
        btn.setProperty("active", "false")
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn.setMinimumHeight(36)
        if icon_name:
            icon_path = get_icon_path(icon_name)
            if icon_path.exists():
                from PyQt6.QtGui import QIcon
                btn.setIcon(QIcon(str(icon_path)))
                btn.setIconSize(QSize(18, 18))
        btn.clicked.connect(lambda _, p=page_name: self.page_requested.emit(p))
        self._buttons[page_name] = btn
        layout.addWidget(btn)

    def set_active(self, page_name: str):
        """Imposta il bottone attivo e rimuove lo stile dagli altri."""
        for name, btn in self._buttons.items():
            active = (name == page_name)
            btn.setProperty("active", "true" if active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def set_button_visible(self, page_name: str, visible: bool):
        if page_name in self._buttons:
            self._buttons[page_name].setVisible(visible)

    def get_page_names(self) -> list:
        """Restituisce la lista ordinata dei nomi pagina (per shortcut Ctrl+N)."""
        return list(self._buttons.keys())
