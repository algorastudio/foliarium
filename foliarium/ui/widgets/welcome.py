"""
foliarium/ui/widgets/welcome.py — Schermata di benvenuto + accettazione EULA.

Estratto da gui_widgets.py (Sprint 3.8 refactor — six-hats).

Mostrata all'avvio se la EULA della versione corrente non e' stata accettata
in QSettings. Layout split: branding (sinistra) + EULA + checkbox (destra).
"""

from __future__ import annotations

import logging
import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from app_paths import get_logo_path, get_resource_path
from config import APP_NAME, APP_SUBTITLE, APP_VERSION


logger = logging.getLogger("CatastoGUI.welcome")


class WelcomeScreen(QDialog):
    """Splash/EULA screen mostrata all'avvio se la EULA non è ancora stata accettata.
    Layout split: pannello sinistro (branding Indigo) + pannello destro (EULA + accettazione).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")
        self.setWindowTitle("Benvenuto in Foliarium — Accettazione Licenza")
        self.setModal(True)
        self.setMinimumSize(900, 620)
        self.resize(1060, 680)
        self.setWindowFlags(Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._init_ui()

    # ── UI ──────────────────────────────────────────────────────────────────

    def _init_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Pannello sinistro (branding) ────────────────────────────────────
        left = QFrame()
        left.setObjectName("welcomeBranding")
        left.setFixedWidth(320)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(28, 40, 28, 28)
        left_layout.setSpacing(12)

        # Logo
        logo_path = get_logo_path()
        logo_path_str = str(logo_path)
        if os.path.exists(logo_path_str):
            if logo_path_str.lower().endswith('.svg'):
                try:
                    from PyQt6.QtSvgWidgets import QSvgWidget
                    logo_w = QSvgWidget(logo_path_str)
                    logo_w.setFixedSize(100, 100)
                    logo_layout = QHBoxLayout()
                    logo_layout.addStretch()
                    logo_layout.addWidget(logo_w)
                    logo_layout.addStretch()
                    left_layout.addLayout(logo_layout)
                except ImportError:
                    pass
            else:
                lbl = QLabel()
                px = QPixmap(logo_path_str)
                lbl.setPixmap(px.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation))
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                left_layout.addWidget(lbl)

        left_layout.addSpacing(16)

        app_lbl = QLabel(APP_NAME)
        app_lbl.setObjectName("welcomeAppTitle")
        app_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(app_lbl)

        sub_lbl = QLabel(APP_SUBTITLE)
        sub_lbl.setObjectName("welcomeAppSubtitle")
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_lbl.setWordWrap(True)
        left_layout.addWidget(sub_lbl)

        left_layout.addStretch(1)

        separator = QFrame()
        separator.setObjectName("welcomeSeparator")
        separator.setFrameShape(QFrame.Shape.HLine)
        left_layout.addWidget(separator)

        algora_lbl = QLabel("Algora Studio")
        algora_lbl.setObjectName("welcomeStudio")
        algora_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(algora_lbl)

        copy_lbl = QLabel(f"© 2025 Algora Studio\nVersione {APP_VERSION}")
        copy_lbl.setObjectName("welcomeCopyright")
        copy_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(copy_lbl)

        root.addWidget(left)

        # ── Pannello destro (EULA) ──────────────────────────────────────────
        right = QFrame()
        right.setObjectName("welcomeBody")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(32, 32, 32, 24)
        right_layout.setSpacing(14)

        title_lbl = QLabel("Contratto di Licenza")
        title_lbl.setObjectName("welcomeTitle")
        right_layout.addWidget(title_lbl)

        info_lbl = QLabel(
            "Leggi attentamente il contratto di licenza prima di utilizzare Foliarium.\n"
            "Devi accettare i termini per continuare."
        )
        info_lbl.setObjectName("welcomeInfo")
        info_lbl.setWordWrap(True)
        right_layout.addWidget(info_lbl)

        # Testo EULA
        self.eula_browser = QTextBrowser()
        self.eula_browser.setObjectName("eulaBrowser")
        self.eula_browser.setReadOnly(True)
        self.eula_browser.setFont(QFont("Consolas", 9))
        eula_path = get_resource_path("EULA.txt")
        try:
            with open(str(eula_path), "r", encoding="utf-8") as f:
                self.eula_browser.setPlainText(f.read())
        except Exception as _e:
            logger.warning("Impossibile caricare EULA da '%s': %s", eula_path, _e)
            self.eula_browser.setPlainText(
                "Impossibile caricare il testo della licenza.\n"
                "Contatta Algora Studio per una copia del contratto."
            )
        right_layout.addWidget(self.eula_browser, 1)

        # Checkbox accettazione
        self.accept_cb = QCheckBox(
            "Ho letto e accetto i termini del Contratto di Licenza con l'Utente Finale (EULA)"
        )
        self.accept_cb.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.accept_cb.toggled.connect(self._on_accept_toggled)
        right_layout.addWidget(self.accept_cb)

        # Pulsanti
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.help_btn = QPushButton("Manuale Utente")
        self.help_btn.setObjectName("secondaryButton")
        self.help_btn.setMinimumHeight(36)
        self.help_btn.setToolTip("Apri il manuale utente integrato")
        self.help_btn.clicked.connect(self._open_help)
        btn_row.addWidget(self.help_btn)

        btn_row.addStretch()

        self.cancel_btn = QPushButton("Annulla")
        self.cancel_btn.setObjectName("secondaryButton")
        self.cancel_btn.setMinimumHeight(36)
        self.cancel_btn.setMinimumWidth(90)
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)

        self.continue_btn = QPushButton("Continua →")
        self.continue_btn.setMinimumHeight(36)
        self.continue_btn.setMinimumWidth(110)
        self.continue_btn.setEnabled(False)
        self.continue_btn.setDefault(True)
        self.continue_btn.clicked.connect(self._on_continue)
        btn_row.addWidget(self.continue_btn)

        right_layout.addLayout(btn_row)
        root.addWidget(right, 1)

    # ── Handlers ────────────────────────────────────────────────────────────

    def _on_accept_toggled(self, checked: bool):
        self.continue_btn.setEnabled(checked)

    def _on_continue(self):
        if self.accept_cb.isChecked():
            self.logger.info("EULA accettata dall'utente.")
            self.accept()

    def _open_help(self):
        """Apre il manuale utente integrato (HelpViewerDialog se disponibile)."""
        try:
            from dialogs import HelpViewerDialog
            dlg = HelpViewerDialog(self)
            dlg.exec()
        except Exception as e:
            self.logger.warning(f"Impossibile aprire HelpViewerDialog: {e}")
            QMessageBox.information(
                self, "Manuale",
                "Il manuale utente integrato non è disponibile in questo momento.\n"
                "Consulta la documentazione fornita con il software."
            )


__all__ = ["WelcomeScreen"]
