"""Dialog di gestione e visualizzazione della licenza."""
from __future__ import annotations

import logging
import os
import sys
from datetime import date
from typing import Optional, Dict, Any

from PyQt6.QtCore import (QDate, QSettings, Qt)
from PyQt6.QtGui import (QDesktopServices, QFont, QPixmap)
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtWidgets import (QAbstractItemView, QApplication,
                             QCheckBox, QComboBox, QDialog,
                             QFileDialog, QFormLayout, QFrame, QGridLayout, QGroupBox,
                             QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                             QMessageBox, QPushButton, QSpinBox, QStyle,
                             QSplitter, QTableWidget, QTableWidgetItem,
                             QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                             QWidget, QTextBrowser, QDialogButtonBox,
                             QRadioButton, QGraphicsScene, QGraphicsView)
from PyQt6.QtGui import QPainter
from app_paths import get_resource_path, get_resource_path as resource_path, get_doc_path  # noqa: F401
from config import (
    SETTINGS_DB_TYPE, SETTINGS_DB_HOST, SETTINGS_DB_PORT,
    SETTINGS_DB_NAME, SETTINGS_DB_USER, SETTINGS_DB_SCHEMA, SETTINGS_DB_PASSWORD,
    SETTINGS_SMTP_ENABLED, SETTINGS_SMTP_HOST, SETTINGS_SMTP_PORT,
    SETTINGS_SMTP_USER, SETTINGS_SMTP_USE_TLS, SETTINGS_SMTP_FROM_ADDR,
    SETTINGS_EMAIL_ON_CREATE, SETTINGS_EMAIL_ON_PASSWD,
    SETTINGS_EMAIL_ON_ROLE, SETTINGS_EMAIL_ON_LOGIN,
    SETTINGS_LICENSE_FILE_PATH, SETTINGS_LICENSE_NETWORK_SHARE,
)
from catasto_db_manager import CatastoDBManager
from catasto_exceptions import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError  # noqa: F401
from foliarium.ui.widgets.custom import QPasswordLineEdit, show_status_message as _show_status_message
from core.auth_manager import AuthManager as _AuthManager

try:
    import keyring
except ImportError:
    keyring = None

try:
    import markdown
except ImportError:
    markdown = None

try:
    import yaml
except ImportError:
    yaml = None


class LicenseDialog(QDialog):
    """
    Dialog per visualizzare lo stato della licenza, configurare il percorso
    del file .license e la cartella condivisa per il conteggio dei seat di rete.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestione Licenza — Foliarium")
        self.setMinimumWidth(540)
        self.setMinimumHeight(420)
        self._build_ui()
        self._load_settings()
        self._refresh_status()

    # ------------------------------------------------------------------
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # --- Gruppo: stato licenza ---
        grp_status = QGroupBox("Stato licenza attuale")
        grp_layout = QFormLayout(grp_status)

        self._lbl_valid    = QLabel("—")
        self._lbl_owner    = QLabel("—")
        self._lbl_type     = QLabel("—")
        self._lbl_seats    = QLabel("—")
        self._lbl_expiry   = QLabel("—")
        self._lbl_hw       = QLabel("—")
        self._lbl_fp       = QLabel("—")

        grp_layout.addRow("Stato:",          self._lbl_valid)
        grp_layout.addRow("Intestata a:",    self._lbl_owner)
        grp_layout.addRow("Tipo:",           self._lbl_type)
        grp_layout.addRow("Seat (max):",     self._lbl_seats)
        grp_layout.addRow("Scadenza:",       self._lbl_expiry)
        grp_layout.addRow("Hardware ID:",    self._lbl_hw)
        grp_layout.addRow("ID computer:",    self._lbl_fp)
        layout.addWidget(grp_status)

        # --- Gruppo: percorso file licenza ---
        grp_file = QGroupBox("File di licenza")
        file_layout = QHBoxLayout(grp_file)
        self._edit_license_path = QLineEdit()
        self._edit_license_path.setPlaceholderText("Percorso file foliarium.license …")
        btn_browse = QPushButton("Sfoglia…")
        btn_browse.clicked.connect(self._browse_license_file)
        file_layout.addWidget(self._edit_license_path)
        file_layout.addWidget(btn_browse)
        layout.addWidget(grp_file)

        # --- Gruppo: cartella condivisa per seat di rete ---
        grp_share = QGroupBox("Cartella condivisa (controllo seat di rete)")
        share_layout = QVBoxLayout(grp_share)
        lbl_help = QLabel(
            "Inserisci il percorso UNC di una cartella condivisa accessibile da tutti i PC\n"
            "dove è installato Foliarium (es. \\\\server\\Condivisa\\foliarium_seats).\n"
            "Lascia vuoto per non limitare le istanze simultanee."
        )
        lbl_help.setWordWrap(True)
        lbl_help.setProperty("muted", "true")
        share_layout.addWidget(lbl_help)
        share_row = QHBoxLayout()
        self._edit_share = QLineEdit()
        self._edit_share.setPlaceholderText("\\\\server\\condivisa\\foliarium_seats")
        btn_browse_share = QPushButton("Sfoglia…")
        btn_browse_share.clicked.connect(self._browse_share_folder)
        share_row.addWidget(self._edit_share)
        share_row.addWidget(btn_browse_share)
        share_layout.addLayout(share_row)
        layout.addWidget(grp_share)

        # --- Bottoni ---
        btn_row = QHBoxLayout()
        btn_refresh = QPushButton("Ricontrolla licenza")
        btn_refresh.clicked.connect(self._refresh_status)
        btn_generate = QPushButton("Copia ID hardware…")
        btn_generate.setToolTip("Copia negli appunti il fingerprint di questo computer da inviare per generare la licenza")
        btn_generate.clicked.connect(self._copy_hardware_id)
        btn_save = QPushButton("Salva impostazioni")
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._save_and_close)
        btn_close = QPushButton("Chiudi")
        btn_close.clicked.connect(self.reject)

        btn_row.addWidget(btn_refresh)
        btn_row.addWidget(btn_generate)
        btn_row.addStretch()
        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    def _load_settings(self):
        from PyQt6.QtCore import QSettings
        s = QSettings()
        self._edit_license_path.setText(s.value(SETTINGS_LICENSE_FILE_PATH, "", type=str))
        self._edit_share.setText(s.value(SETTINGS_LICENSE_NETWORK_SHARE, "", type=str))

    def _refresh_status(self):
        from foliarium.core.services.license import LicenseManager, get_hardware_fingerprint
        # Aggiorna il percorso nell'oggetto manager prima di validare
        lm = LicenseManager.__new__(LicenseManager)
        lm.license_path  = self._edit_license_path.text().strip() or lm.__class__.__init__.__code__.co_filename
        # Usa direttamente la funzione di validazione
        from foliarium.core.services.license import _validate_file
        from config import IS_DEMO_MODE
        if IS_DEMO_MODE:
            from datetime import date
            from foliarium.core.services.license import LicenseInfo
            info = LicenseInfo("Versione Demo", "demo", 1, None, None, date.today(), True)
        else:
            path = self._edit_license_path.text().strip()
            if not path:
                from app_paths import BASE_DIR
                from config import LICENSE_DEFAULT_FILENAME
                from pathlib import Path
                path = str(Path(BASE_DIR) / LICENSE_DEFAULT_FILENAME)
            info = _validate_file(path)

        fp = get_hardware_fingerprint()
        self._lbl_fp.setText(fp)

        if info.is_valid:
            self._lbl_valid.setText("<b style='color:green'>✔ Valida</b>")
        else:
            self._lbl_valid.setText(f"<b style='color:red'>✘ {info.error_message}</b>")

        self._lbl_owner.setText(info.licensed_to or "—")
        type_labels = {"demo": "Demo", "standard": "Standard", "enterprise": "Enterprise"}
        self._lbl_type.setText(type_labels.get(info.license_type, info.license_type))
        self._lbl_seats.setText(str(info.max_seats))
        if info.expiry_date:
            days = info.days_to_expiry()
            self._lbl_expiry.setText(
                f"{info.expiry_date.strftime('%d/%m/%Y')}  "
                f"({'scaduta' if days < 0 else f'tra {days} giorni'})"
            )
        else:
            self._lbl_expiry.setText("Perpetua")
        self._lbl_hw.setText(info.hardware_id or "Qualsiasi")

    def _browse_license_file(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleziona file licenza",
            self._edit_license_path.text() or "",
            "File licenza (*.license *.json);;Tutti i file (*)"
        )
        if path:
            self._edit_license_path.setText(path)
            self._refresh_status()

    def _browse_share_folder(self):
        from PyQt6.QtWidgets import QFileDialog
        folder = QFileDialog.getExistingDirectory(
            self, "Seleziona cartella condivisa", self._edit_share.text() or ""
        )
        if folder:
            self._edit_share.setText(folder)

    def _copy_hardware_id(self):
        from foliarium.core.services.license import get_hardware_fingerprint
        from PyQt6.QtWidgets import QApplication
        fp = get_hardware_fingerprint()
        QApplication.clipboard().setText(fp)
        QMessageBox.information(
            self, "ID copiato",
            f"ID hardware copiato negli appunti:\n\n{fp}\n\n"
            "Invia questo codice all'amministratore per generare il file di licenza."
        )

    def _save_and_close(self):
        from PyQt6.QtCore import QSettings
        s = QSettings()
        s.setValue(SETTINGS_LICENSE_FILE_PATH, self._edit_license_path.text().strip())
        s.setValue(SETTINGS_LICENSE_NETWORK_SHARE, self._edit_share.text().strip())
        s.sync()
        QMessageBox.information(self, "Salvato",
                                "Impostazioni di licenza salvate.\n"
                                "Riavvia l'applicazione per applicarle.")
        self.accept()


# ---------------------------------------------------------------------------
# LoginDialog
# ---------------------------------------------------------------------------



