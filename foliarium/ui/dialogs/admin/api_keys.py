"""foliarium/ui/dialogs/admin/api_keys.py — Gestione chiavi API.

Tre dialog cooperanti:

- ``ApiKeysDialog``       — elenco chiavi (tabella) + bottoni Nuova/Revoca/Aggiorna.
- ``CreateApiKeyDialog``  — form per creare una nuova chiave (nome, scope, scadenza).
- ``NewKeyResultDialog``  — mostra la chiave in chiaro una sola volta con bottone "Copia".

Modello dati alla base: il mixin ``DBApiKeysMixin`` (db/api_keys.py). Le
chiavi sono memorizzate come SHA-256 in DB; il plaintext (``flr_<32 hex>``)
viene restituito da ``create_api_key`` e mostrato a video una sola volta.

Scope tipici esposti nella UI:

* ``read:comuni``, ``read:partite``, ``read:possessori``, ``read:audit``,
  ``read:dashboard``, ``read:genealogia``, ``read:timeline``
* ``write:partite``, ``write:possessori``
* wildcard: ``read:*``, ``*:*``
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from catasto_db_manager import CatastoDBManager


_log = logging.getLogger("CatastoGUI.dialogs.api_keys")


# Scope predefiniti mostrati nella UI di creazione. L'admin può comunque
# digitare scope custom, ma questo elenco copre il 90% dei casi pratici.
DEFAULT_SCOPES: list[tuple[str, str]] = [
    ("read:comuni",      "Lettura elenco comuni"),
    ("read:partite",     "Lettura partite catastali"),
    ("read:possessori",  "Lettura possessori"),
    ("read:audit",       "Lettura audit log"),
    ("read:dashboard",   "Lettura statistiche dashboard"),
    ("read:genealogia",  "Lettura albero genealogico partite"),
    ("read:timeline",    "Lettura timeline variazioni"),
    ("write:partite",    "Creazione/modifica partite"),
    ("write:possessori", "Creazione/modifica possessori"),
    ("read:*",           "Lettura completa (wildcard)"),
    ("*:*",              "Accesso totale (wildcard, riservato)"),
]


# ─────────────────────────────────────────────────────────────────────
# Dialog: mostra la chiave appena creata (UNA SOLA VOLTA)
# ─────────────────────────────────────────────────────────────────────

class NewKeyResultDialog(QDialog):
    """Mostra la chiave in chiaro appena creata con bottone "Copia".

    Importante: il segreto non potrà più essere recuperato. La UI deve
    incoraggiare l'utente a copiarlo subito.
    """

    def __init__(self, plaintext: str, key_name: str, parent=None):
        super().__init__(parent)
        self.plaintext = plaintext
        self.setWindowTitle("Nuova chiave API creata")
        self.setMinimumWidth(560)
        self.setModal(True)

        layout = QVBoxLayout(self)

        warning = QLabel(
            "<b>⚠ Copia subito questa chiave.</b><br>"
            "Non sarà più visibile dopo la chiusura di questa finestra. "
            "In DB è memorizzato solo lo hash."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet(
            "QLabel { background-color: #FFF4D6; color: #5A3E00; "
            "border: 1px solid #E0B14B; padding: 10px; border-radius: 4px; }"
        )
        layout.addWidget(warning)

        layout.addWidget(QLabel(f"<b>Nome:</b> {key_name}"))

        layout.addWidget(QLabel("Chiave (in chiaro):"))
        self.key_field = QTextEdit()
        self.key_field.setPlainText(plaintext)
        self.key_field.setReadOnly(True)
        self.key_field.setMaximumHeight(60)
        mono = QFont("Consolas", 10)
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self.key_field.setFont(mono)
        layout.addWidget(self.key_field)

        hint = QLabel(
            "Usala come header HTTP:<br>"
            "<code>X-Foliarium-Api-Key: " + plaintext + "</code>"
        )
        hint.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        hint.setWordWrap(True)
        layout.addWidget(hint)

        btn_row = QHBoxLayout()
        self.copy_btn = QPushButton(
            QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton),
            "Copia negli appunti",
        )
        self.copy_btn.setDefault(True)
        self.copy_btn.clicked.connect(self._copy_to_clipboard)
        btn_row.addWidget(self.copy_btn)

        btn_row.addStretch()

        close_btn = QPushButton("Chiudi")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

    def _copy_to_clipboard(self):
        QApplication.clipboard().setText(self.plaintext)
        self.copy_btn.setText("✓ Copiata")
        self.copy_btn.setEnabled(False)


# ─────────────────────────────────────────────────────────────────────
# Dialog: form di creazione chiave
# ─────────────────────────────────────────────────────────────────────

class CreateApiKeyDialog(QDialog):
    """Form per definire nome, scope e scadenza di una nuova chiave."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Crea nuova chiave API")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        # ── Nome ──────────────────────────────────────────────────
        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Es. MCP server Marco, Zapier export, ...")
        self.name_edit.setMaxLength(100)
        form.addRow("Nome identificativo:", self.name_edit)

        # ── Scadenza ──────────────────────────────────────────────
        self.expiry_enabled = QCheckBox("Imposta scadenza")
        self.expiry_edit = QDateEdit()
        self.expiry_edit.setCalendarPopup(True)
        self.expiry_edit.setDate(QDate.currentDate().addYears(1))
        self.expiry_edit.setMinimumDate(QDate.currentDate().addDays(1))
        self.expiry_edit.setEnabled(False)
        self.expiry_enabled.toggled.connect(self.expiry_edit.setEnabled)

        expiry_row = QHBoxLayout()
        expiry_row.addWidget(self.expiry_enabled)
        expiry_row.addWidget(self.expiry_edit)
        expiry_row.addStretch()
        form.addRow("Validità:", _wrap(expiry_row))

        layout.addLayout(form)

        # ── Scope (checkbox) ──────────────────────────────────────
        scope_group = QGroupBox("Scope concessi")
        scope_layout = QGridLayout(scope_group)
        self.scope_checks: list[tuple[QCheckBox, str]] = []
        for i, (scope, desc) in enumerate(DEFAULT_SCOPES):
            cb = QCheckBox(f"{scope}  —  {desc}")
            cb.setObjectName(f"scope_{scope}")
            if scope.startswith("read:") and scope != "read:*":
                cb.setChecked(True)
            scope_layout.addWidget(cb, i, 0)
            self.scope_checks.append((cb, scope))
        layout.addWidget(scope_group)

        # ── Bottoni ───────────────────────────────────────────────
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.button(QDialogButtonBox.StandardButton.Ok).setText("Crea chiave")
        btns.accepted.connect(self._validate_and_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self.name_edit.setFocus()

    def _validate_and_accept(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(
                self, "Errore",
                "Il nome identificativo è obbligatorio.",
            )
            self.name_edit.setFocus()
            return
        if not any(cb.isChecked() for cb, _ in self.scope_checks):
            QMessageBox.warning(
                self, "Errore",
                "Seleziona almeno uno scope per la chiave.",
            )
            return
        self.accept()

    # ── API pubblica del dialog (post-accept) ──────────────────────
    def get_name(self) -> str:
        return self.name_edit.text().strip()

    def get_scopes(self) -> List[str]:
        return [scope for cb, scope in self.scope_checks if cb.isChecked()]

    def get_expires_at(self) -> Optional[datetime]:
        if not self.expiry_enabled.isChecked():
            return None
        qd = self.expiry_edit.date()
        return datetime(qd.year(), qd.month(), qd.day(), 23, 59, 59)


def _wrap(inner_layout) -> QFrame:
    frame = QFrame()
    frame.setLayout(inner_layout)
    return frame


# ─────────────────────────────────────────────────────────────────────
# Dialog principale: elenco chiavi
# ─────────────────────────────────────────────────────────────────────

class ApiKeysDialog(QDialog):
    """Elenco chiavi API esistenti con azioni di creazione/revoca."""

    COLUMNS = ("Nome", "Prefisso", "Scope", "Creata", "Scadenza", "Ultimo uso", "Stato", "ID")
    COL_ID = 7

    def __init__(self, db_manager: CatastoDBManager, current_user_id: Optional[int] = None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_user_id = current_user_id

        self.setWindowTitle("Gestione chiavi API")
        self.setMinimumSize(900, 460)

        layout = QVBoxLayout(self)

        intro = QLabel(
            "Le chiavi API permettono a integrazioni esterne (MCP server, "
            "Zapier, script di automazione) di accedere alla REST API di "
            "Foliarium. Ogni chiavi ha uno o più scope che ne limitano i "
            "permessi. Una chiave revocata non è più recuperabile."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #555;")
        layout.addWidget(intro)

        # ── Tabella ───────────────────────────────────────────────
        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setColumnHidden(self.COL_ID, True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)         # Nome
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)         # Scope
        for col in (1, 3, 4, 5, 6):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table)

        # ── Toggle "mostra revocate" ─────────────────────────────
        self.show_revoked = QCheckBox("Mostra anche chiavi revocate")
        self.show_revoked.toggled.connect(self._reload)
        layout.addWidget(self.show_revoked)

        # ── Bottoni ───────────────────────────────────────────────
        btn_row = QHBoxLayout()
        self.new_btn = QPushButton(
            QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder),
            "Nuova chiave...",
        )
        self.new_btn.clicked.connect(self._on_new)
        btn_row.addWidget(self.new_btn)

        self.revoke_btn = QPushButton(
            QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DialogDiscardButton),
            "Revoca selezionata",
        )
        self.revoke_btn.clicked.connect(self._on_revoke)
        btn_row.addWidget(self.revoke_btn)

        self.refresh_btn = QPushButton(
            QApplication.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload),
            "Aggiorna",
        )
        self.refresh_btn.clicked.connect(self._reload)
        btn_row.addWidget(self.refresh_btn)

        btn_row.addStretch()

        close_btn = QPushButton("Chiudi")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

        self._reload()

    # ── Caricamento dati ───────────────────────────────────────────
    def _reload(self):
        try:
            rows = self.db_manager.list_api_keys(
                include_revoked=self.show_revoked.isChecked()
            )
        except Exception as e:
            _log.error("Errore lettura chiavi API: %s", e, exc_info=True)
            QMessageBox.critical(
                self, "Errore",
                f"Impossibile leggere le chiavi API dal database:\n{e}",
            )
            return

        self.table.setRowCount(0)
        for row in rows:
            self._append_row(row)

    def _append_row(self, row: dict):
        i = self.table.rowCount()
        self.table.insertRow(i)

        def _cell(text: str) -> QTableWidgetItem:
            item = QTableWidgetItem(text)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            return item

        scopes_str = ", ".join(row.get("scopes") or [])
        created = _fmt_dt(row.get("created_at"))
        expires = _fmt_dt(row.get("expires_at")) or "—"
        last_used = _fmt_dt(row.get("last_used_at")) or "mai"

        if row.get("revoked_at"):
            stato = "Revocata"
            colore_stato = "#B71C1C"
        elif row.get("expires_at") and row["expires_at"] < datetime.now(row["expires_at"].tzinfo):
            stato = "Scaduta"
            colore_stato = "#E65100"
        else:
            stato = "Attiva"
            colore_stato = "#2E7D32"

        cells = [
            row.get("name", ""),
            row.get("prefix", ""),
            scopes_str,
            created,
            expires,
            last_used,
            stato,
            str(row.get("id", "")),
        ]
        for col, text in enumerate(cells):
            item = _cell(text)
            if col == 6:  # Stato
                item.setForeground(Qt.GlobalColor.white)
                from PyQt6.QtGui import QBrush, QColor
                item.setBackground(QBrush(QColor(colore_stato)))
            self.table.setItem(i, col, item)

    # ── Azioni ─────────────────────────────────────────────────────
    def _on_new(self):
        dlg = CreateApiKeyDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            new_id, plaintext = self.db_manager.create_api_key(
                name=dlg.get_name(),
                scopes=dlg.get_scopes(),
                created_by=self.current_user_id,
                expires_at=dlg.get_expires_at(),
            )
        except Exception as e:
            _log.error("Errore creazione chiave API: %s", e, exc_info=True)
            QMessageBox.critical(
                self, "Errore",
                f"Impossibile creare la chiave:\n{e}",
            )
            return

        _log.info("Chiave API creata id=%d name=%r", new_id, dlg.get_name())
        NewKeyResultDialog(plaintext, dlg.get_name(), self).exec()
        self._reload()

    def _on_revoke(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(
                self, "Nessuna selezione",
                "Seleziona una chiave da revocare.",
            )
            return
        i = rows[0].row()
        name_item = self.table.item(i, 0)
        id_item = self.table.item(i, self.COL_ID)
        stato_item = self.table.item(i, 6)
        if not (name_item and id_item):
            return
        if stato_item and stato_item.text() == "Revocata":
            QMessageBox.information(self, "Già revocata", "Questa chiave è già stata revocata.")
            return

        confirm = QMessageBox.question(
            self,
            "Conferma revoca",
            f"Revocare la chiave <b>{name_item.text()}</b>?<br><br>"
            "L'operazione è <b>irreversibile</b>: tutte le integrazioni che "
            "usano questa chiave smetteranno immediatamente di funzionare.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            ok = self.db_manager.revoke_api_key(int(id_item.text()))
        except Exception as e:
            _log.error("Errore revoca chiave API: %s", e, exc_info=True)
            QMessageBox.critical(self, "Errore", f"Revoca fallita:\n{e}")
            return

        if ok:
            QMessageBox.information(
                self, "Revocata",
                f"Chiave '{name_item.text()}' revocata con successo.",
            )
        else:
            QMessageBox.warning(
                self, "Nessuna modifica",
                "La chiave era già stata revocata o non esiste più.",
            )
        self._reload()


# ─────────────────────────────────────────────────────────────────────
# Utility
# ─────────────────────────────────────────────────────────────────────

def _fmt_dt(value) -> str:
    """Formatta un datetime in stringa locale leggibile. Restituisce '' se None."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    return str(value)
