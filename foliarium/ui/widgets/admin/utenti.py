"""Gestione utenti: model + widget account (solo admin)."""
from __future__ import annotations

import csv
import json
import os
import logging
from datetime import date
from typing import Optional, Dict, List, Any, TYPE_CHECKING

from PyQt6.QtCore import (
    QAbstractTableModel, QDateTime, QModelIndex, QPoint, QProcess, QProcessEnvironment,
    QSettings, QSortFilterProxyModel, Qt, pyqtSlot,
)
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication,
    QComboBox, QDateTimeEdit, QDialog, QDialogButtonBox,
    QFileDialog, QFormLayout, QFrame, QGroupBox, QHBoxLayout, QHeaderView,
    QInputDialog, QLabel, QLineEdit, QMenu,
    QMessageBox, QProgressBar, QPushButton, QSpinBox, QStyle,
    QTabWidget, QTableView, QTableWidget, QTableWidgetItem,
    QTextEdit, QVBoxLayout, QWidget,
    QSplitter,
)

from catasto_exceptions import (
    DBMError, DBUniqueConstraintError, DBDataError,
)
from foliarium.ui.widgets.custom import LazyLoadedWidget
from dialogs import (
    CreateUserDialog, PeriodoStoricoEditDialog,
    _hash_password,
)

if TYPE_CHECKING:
    from catasto_db_manager import CatastoDBManager

logger = logging.getLogger("CatastoGUI.admin_widgets")


from foliarium.ui.widgets.custom import show_status_message as _show_status_message


_USERS_COLS = ["ID", "Username", "Nome Completo", "Email", "Ruolo", "Stato"]


class UtentiTableModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: List[Dict[str, Any]] = []

    def load(self, utenti: List[Dict[str, Any]]) -> None:
        self.beginResetModel()
        self._data = utenti
        self.endResetModel()

    def user_id_at(self, source_row: int) -> Optional[int]:
        if 0 <= source_row < len(self._data):
            try:
                return int(self._data[source_row]['id'])
            except (KeyError, ValueError, TypeError):
                return None
        return None

    def row_dict(self, source_row: int) -> Dict[str, Any]:
        return self._data[source_row] if 0 <= source_row < len(self._data) else {}

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._data)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(_USERS_COLS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return _USERS_COLS[section] if 0 <= section < len(_USERS_COLS) else None
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row, col = index.row(), index.column()
        if not (0 <= row < len(self._data) and 0 <= col < len(_USERS_COLS)):
            return None
        user = self._data[row]
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if col == 0:
                val = user.get('id')
                if role == Qt.ItemDataRole.EditRole and val is not None:
                    return int(val)
                return str(val) if val is not None else ''
            if col == 1: return user.get('username', '') or ''
            if col == 2: return user.get('nome_completo', '') or ''
            if col == 3: return user.get('email', 'N/D') or 'N/D'
            if col == 4: return user.get('ruolo', '') or ''
            if col == 5: return "Attivo" if user.get('attivo') else "Non Attivo"
        if role == Qt.ItemDataRole.TextAlignmentRole and col == 0:
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return None

    def flags(self, index):
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def sort(self, column, order=Qt.SortOrder.AscendingOrder):
        if not self._data:
            return
        _keys = {0: 'id', 1: 'username', 2: 'nome_completo', 3: 'email', 4: 'ruolo', 5: 'attivo'}
        key = _keys.get(column, 'username')
        self.layoutAboutToBeChanged.emit()
        self._data.sort(
            key=lambda r: (r.get(key) is None, r.get(key) if r.get(key) is not None else ''),
            reverse=(order == Qt.SortOrder.DescendingOrder),
        )
        self.layoutChanged.emit()




class GestioneUtentiWidget(LazyLoadedWidget):
    def __init__(self, db_manager: 'CatastoDBManager', current_user_info: Optional[Dict], parent=None):
        super().__init__(parent)  # Chiama il costruttore della classe base
        self.db_manager = db_manager
        self.current_user_info = current_user_info
        self.is_admin = self.current_user_info.get('ruolo') == 'admin' if self.current_user_info else False
        
        self._initUI()
        # La chiamata a refresh_user_list() viene rimossa da qui

    def _initUI(self):
        """Crea e assembla i componenti dell'interfaccia utente."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        title = QLabel("Gestione Utenti")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        subtitle = QLabel("Crea, modifica e gestisci gli account utente. Solo gli amministratori possono modificare i ruoli.")
        subtitle.setObjectName("pageSubtitle")
        layout.addWidget(subtitle)

        # Pulsanti Azioni
        action_layout = QHBoxLayout()
        self.btn_crea_utente = QPushButton(
            QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder),
            " Crea Nuovo Utente")
        self.btn_crea_utente.clicked.connect(self.crea_nuovo_utente)
        self.btn_crea_utente.setEnabled(self.is_admin)
        self.btn_refresh_list = QPushButton(
            QApplication.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload),
            " Aggiorna")
        self.btn_refresh_list.setObjectName("secondaryButton")
        self.btn_refresh_list.clicked.connect(self.refresh_user_list)

        action_layout.addWidget(self.btn_crea_utente)
        action_layout.addStretch()
        action_layout.addWidget(self.btn_refresh_list)
        layout.addLayout(action_layout)

        # Tabella Utenti (model/view)
        self._users_model = UtentiTableModel(self)
        self._users_proxy = QSortFilterProxyModel(self)
        self._users_proxy.setSourceModel(self._users_model)
        self._users_proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._users_proxy.setFilterKeyColumn(-1)

        self.user_table = QTableView()
        self.user_table.setModel(self._users_proxy)
        self.user_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.user_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.user_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.user_table.setAlternatingRowColors(True)
        self.user_table.setSortingEnabled(True)
        self.user_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.user_table.horizontalHeader().setStretchLastSection(True)
        self.user_table.setColumnWidth(0, 40)
        self.user_table.setColumnWidth(1, 130)
        self.user_table.setColumnWidth(2, 180)
        self.user_table.setColumnWidth(3, 180)
        self.user_table.setColumnWidth(4, 100)
        self.user_table.selectionModel().selectionChanged.connect(self._update_action_buttons_state)
        self.user_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.user_table.customContextMenuRequested.connect(self._apri_menu_contestuale_utente)
        layout.addWidget(self.user_table)

        # Pulsanti di gestione per utente selezionato
        manage_layout = QHBoxLayout()
        self.btn_modifica_utente = QPushButton("Modifica Utente")
        self.btn_modifica_utente.setObjectName("secondaryButton")
        self.btn_modifica_utente.clicked.connect(self.modifica_utente_selezionato)

        self.btn_reset_password = QPushButton("Resetta Password")
        self.btn_reset_password.setObjectName("secondaryButton")
        self.btn_reset_password.clicked.connect(self.reset_password_utente_selezionato)

        self.btn_toggle_stato = QPushButton("Attiva/Disattiva")
        self.btn_toggle_stato.setObjectName("secondaryButton")
        self.btn_toggle_stato.clicked.connect(self.toggle_stato_utente_selezionato)

        self.btn_delete_utente = QPushButton("Elimina Utente")
        self.btn_delete_utente.setObjectName("dangerButton")
        self.btn_delete_utente.clicked.connect(self.elimina_utente_selezionato)

        manage_layout.addWidget(self.btn_modifica_utente)
        manage_layout.addWidget(self.btn_reset_password)
        manage_layout.addWidget(self.btn_toggle_stato)
        manage_layout.addStretch()
        manage_layout.addWidget(self.btn_delete_utente)
        layout.addLayout(manage_layout)
        
        # Imposta lo stato iniziale dei pulsanti
        self._update_action_buttons_state()

    def _load_data_on_first_show(self):
        """Carica la lista degli utenti la prima volta che il tab viene mostrato."""
        self.logger.info("GestioneUtentiWidget: Esecuzione lazy loading della lista utenti...")
        self.refresh_user_list()

    def refresh_user_list(self):
        """Carica o ricarica la lista degli utenti dal database e la visualizza."""
        self.logger.info("Aggiornamento della lista utenti in corso...")
        try:
            utenti = self.db_manager.get_utenti() or []
            self._users_model.load(utenti)
            self.user_table.resizeColumnsToContents()
            self.logger.info("Lista utenti aggiornata con successo.")
        except DBMError as e:
            self.logger.error(f"Errore DB durante l'aggiornamento della lista utenti: {e}")
            QMessageBox.critical(self, "Errore Database", f"Impossibile caricare la lista degli utenti:\n{e}")

    def _update_action_buttons_state(self):
        """Abilita i pulsanti di gestione solo se un utente è selezionato."""
        has_selection = self.user_table.selectionModel().hasSelection()
        self.btn_modifica_utente.setEnabled(has_selection and self.is_admin)
        self.btn_reset_password.setEnabled(has_selection and self.is_admin)
        self.btn_toggle_stato.setEnabled(has_selection and self.is_admin)
        self.btn_delete_utente.setEnabled(has_selection and self.is_admin)

    def crea_nuovo_utente(self):
        # CreateUserDialog come definito prima
        dialog = CreateUserDialog(self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_user_list()
            _show_status_message("Nuovo utente creato.", 4000)
            # --- Notifica email creazione account ---
            try:
                from foliarium.core.services.email import EmailService, EmailWorker
                from config import SETTINGS_EMAIL_ON_CREATE
                _svc = EmailService(QSettings())
                if _svc.is_configured() and QSettings().value(SETTINGS_EMAIL_ON_CREATE, True, type=bool):
                    _email = dialog.email_edit.text().strip()
                    if _email:
                        _to, _subj, _body = _svc.notify_account_created(
                            _email, dialog.username_edit.text().strip(),
                            dialog.nome_edit.text().strip(),
                            dialog.ruolo_combo.currentText())
                        _w = EmailWorker(_svc, _to, _subj, _body)
                        _w.result.connect(
                            lambda ok, err: self.logger.warning(f"Email crea account: {err}") if not ok else None)
                        _w.start()
                        self._email_workers = getattr(self, '_email_workers', [])
                        self._email_workers.append(_w)
            except Exception as _e:
                self.logger.warning(f"Notifica email creazione non inviata: {_e}")

    def _get_selected_user_id(self) -> Optional[int]:
        selected_rows = self.user_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Nessuna Selezione",
                                "Per favore, seleziona un utente dalla lista.")
            return None
        source_row = self._users_proxy.mapToSource(selected_rows[0]).row()
        user_id = self._users_model.user_id_at(source_row)
        if user_id is None:
            QMessageBox.critical(
                self, "Errore", "Impossibile ottenere l'ID dell'utente selezionato.")
            return None
        return user_id

    def modifica_utente_selezionato(self):
        user_id = self._get_selected_user_id()
        if user_id is None:
            return

        utente_attuale = self.db_manager.get_utente_by_id(user_id)
        if not utente_attuale:
            QMessageBox.critical(
                self, "Errore", f"Utente con ID {user_id} non trovato.")
            return

        # Qui aprirebbe un dialogo per modificare i dettagli, simile a CreateUserDialog ma pre-popolato
        # Per semplicità, usiamo QInputDialog per alcuni campi
        nome_attuale = utente_attuale.get('nome_completo', '')
        new_nome, ok = QInputDialog.getText(
            self, "Modifica Nome", f"Nuovo nome completo (attuale: '{nome_attuale}'):", text=nome_attuale)
        if not ok:
            return  # Annullato

        email_attuale = utente_attuale.get('email', '')
        new_email, ok = QInputDialog.getText(
            self, "Modifica Email", f"Nuova email (attuale: '{email_attuale}'):", text=email_attuale)
        if not ok:
            return

        ruoli = ["admin", "archivista", "consultatore"]
        ruolo_attuale = utente_attuale.get('ruolo', 'consultatore')
        new_ruolo, ok = QInputDialog.getItem(self, "Modifica Ruolo", f"Nuovo ruolo (attuale: '{ruolo_attuale}'):", ruoli, ruoli.index(
            ruolo_attuale) if ruolo_attuale in ruoli else 0, False)
        if not ok:
            return

        update_params = {}
        if new_nome and new_nome != nome_attuale:
            update_params['nome_completo'] = new_nome
        if new_email and new_email != email_attuale:
            update_params['email'] = new_email
        if new_ruolo and new_ruolo != ruolo_attuale:
            update_params['ruolo'] = new_ruolo

        if update_params:
            if self.db_manager.update_user_details(user_id, **update_params):
                _show_status_message("Dettagli utente aggiornati.", 4000)
                self.refresh_user_list()
                # --- Notifica email cambio ruolo ---
                if 'ruolo' in update_params:
                    try:
                        from foliarium.core.services.email import EmailService, EmailWorker
                        from config import SETTINGS_EMAIL_ON_ROLE
                        _svc = EmailService(QSettings())
                        if _svc.is_configured() and QSettings().value(SETTINGS_EMAIL_ON_ROLE, True, type=bool):
                            _email = (new_email if (new_email and new_email != email_attuale)
                                      else email_attuale)
                            if _email:
                                _to, _subj, _body = _svc.notify_role_changed(
                                    _email, utente_attuale.get('username', ''),
                                    nome_attuale, ruolo_attuale, new_ruolo)
                                _w = EmailWorker(_svc, _to, _subj, _body)
                                _w.result.connect(
                                    lambda ok, err: self.logger.warning(f"Email cambio ruolo: {err}") if not ok else None)
                                _w.start()
                                self._email_workers = getattr(self, '_email_workers', [])
                                self._email_workers.append(_w)
                    except Exception as _e:
                        self.logger.warning(f"Notifica email cambio ruolo non inviata: {_e}")
            else:
                QMessageBox.critical(
                    self, "Errore", "Aggiornamento fallito. Controllare i log.")
        else:
            QMessageBox.information(
                self, "Info", "Nessuna modifica apportata.")

    def reset_password_utente_selezionato(self):
        user_id = self._get_selected_user_id()
        if user_id is None:
            return
        if user_id == self.current_user_info.get('id'):
            QMessageBox.warning(self, "Azione Non Permessa",
                                "Non puoi resettare la tua password da questa interfaccia.")
            return

        utente_target = self.db_manager.get_utente_by_id(user_id)

        new_password, ok = QInputDialog.getText(
            self, "Reset Password", "Inserisci la nuova password temporanea:", QLineEdit.EchoMode.Password)
        if ok and new_password:
            from dialogs import _validate_password_strength
            pwd_ok, pwd_err = _validate_password_strength(new_password)
            if not pwd_ok:
                QMessageBox.warning(self, "Password non valida", pwd_err)
                return
            new_password_confirm, ok_confirm = QInputDialog.getText(
                self, "Conferma Password", "Conferma la nuova password temporanea:", QLineEdit.EchoMode.Password)
            if ok_confirm and new_password == new_password_confirm:
                try:
                    new_hash = _hash_password(new_password)
                    if self.db_manager.reset_user_password(user_id, new_hash):
                        QMessageBox.information(
                            self, "Successo", f"Password per utente ID {user_id} resettata.")
                        # --- Notifica email cambio password ---
                        try:
                            from foliarium.core.services.email import EmailService, EmailWorker
                            from config import SETTINGS_EMAIL_ON_PASSWD
                            _svc = EmailService(QSettings())
                            if _svc.is_configured() and QSettings().value(SETTINGS_EMAIL_ON_PASSWD, True, type=bool):
                                _email = (utente_target or {}).get('email')
                                if _email:
                                    _username = (utente_target or {}).get('username', 'N/D')
                                    _nome = (utente_target or {}).get('nome_completo') or _username
                                    _to, _subj, _body = _svc.notify_password_changed(_email, _username, _nome)
                                    _w = EmailWorker(_svc, _to, _subj, _body)
                                    _w.result.connect(
                                        lambda ok, err: self.logger.warning(f"Email cambio password: {err}") if not ok else None)
                                    _w.start()
                                    self._email_workers = getattr(self, '_email_workers', [])
                                    self._email_workers.append(_w)
                        except Exception as _e:
                            self.logger.warning(f"Notifica email password non inviata: {_e}")
                    else:
                        QMessageBox.critical(
                            self, "Errore", "Reset password fallito.")
                except Exception as e:
                    QMessageBox.critical(
                        self, "Errore Hashing", f"Errore durante l'hashing: {e}")
            elif ok_confirm:  # ma password non coincidono
                QMessageBox.warning(
                    self, "Errore", "Le password non coincidono.")
        elif ok:  # password vuota
            QMessageBox.warning(
                self, "Errore", "La password non può essere vuota.")

    def toggle_stato_utente_selezionato(self):
        user_id = self._get_selected_user_id()
        if user_id is None:
            return
        if user_id == self.current_user_info.get('id'):
            QMessageBox.warning(self, "Azione Non Permessa",
                                "Non puoi modificare lo stato del tuo account.")
            return

        utente_target = self.db_manager.get_utente_by_id(user_id)
        if not utente_target:
            QMessageBox.critical(self, "Errore", "Utente non trovato.")
            return

        nuovo_stato_attivo = not utente_target['attivo']
        azione_str = "RIATTIVARE" if nuovo_stato_attivo else "DISATTIVARE"

        reply = QMessageBox.question(self, "Conferma Stato",
                                     f"L'utente '{utente_target['username']}' è attualmente {'ATTIVO' if utente_target['attivo'] else 'NON ATTIVO'}.\n"
                                     f"Vuoi {azione_str} questo utente?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            success = False
            if nuovo_stato_attivo:
                success = self.db_manager.activate_user(user_id)
            else:
                success = self.db_manager.deactivate_user(user_id)

            if success:
                QMessageBox.information(
                    self, "Successo", f"Stato utente '{utente_target['username']}' aggiornato.")
                self.refresh_user_list()
            else:
                QMessageBox.critical(
                    self, "Errore", "Aggiornamento stato fallito.")

    def elimina_utente_selezionato(self):
        user_id = self._get_selected_user_id()
        if user_id is None:
            return
        if user_id == self.current_user_info.get('id'):
            QMessageBox.warning(self, "Azione Non Permessa",
                                "Non puoi eliminare te stesso.")
            return

        utente_target = self.db_manager.get_utente_by_id(user_id)
        if not utente_target:
            QMessageBox.critical(self, "Errore", "Utente non trovato.")
            return

        reply = QMessageBox.warning(self, "Conferma Eliminazione",
                                    f"ATTENZIONE: Stai per eliminare PERMANENTEMENTE l'utente '{utente_target['username']}' (ID: {user_id}).\n"
                                    "Questa operazione è IRREVERSIBILE e i riferimenti nei log verranno impostati a NULL (se configurato).\n"
                                    "Sei assolutamente sicuro?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            # Ulteriore conferma digitando lo username
            confirm_username, ok = QInputDialog.getText(self, "Conferma Finale",
                                                        f"Per confermare l'eliminazione permanente di '{utente_target['username']}', riscrivi il suo username:")
            if ok and confirm_username == utente_target['username']:
                if self.db_manager.delete_user_permanently(user_id):
                    QMessageBox.information(
                        self, "Successo", f"Utente '{utente_target['username']}' eliminato permanentemente.")
                    self.refresh_user_list()
                else:
                    QMessageBox.critical(
                        self, "Errore", "Eliminazione fallita. Controllare i log (es. è l'unico admin attivo?).")
            elif ok:  # Username non corrispondente
                QMessageBox.warning(
                    self, "Annullato", "Username non corrispondente. Eliminazione annullata.")
            # else: l'utente ha premuto annulla su QInputDialog

    def _apri_menu_contestuale_utente(self, position: QPoint):
        """Context menu sulla tabella utenti."""
        proxy_idx = self.user_table.indexAt(position)
        if not proxy_idx.isValid():
            return
        source_row = self._users_proxy.mapToSource(proxy_idx).row()
        user = self._users_model.row_dict(source_row)
        username = user.get('username', '') or ''
        nome = user.get('nome_completo', '') or ''
        email = user.get('email', '') or ''

        menu = QMenu(self.user_table)
        menu.addAction(
            QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView),
            "Modifica utente"
        ).triggered.connect(self.modifica_utente_selezionato)
        menu.addAction("Reset password").triggered.connect(self.reset_password_utente_selezionato)
        menu.addSeparator()
        if username:
            menu.addAction(f"Copia username  ({username})").triggered.connect(
                lambda: QApplication.clipboard().setText(username))
        if nome:
            menu.addAction(f"Copia nome  ({nome})").triggered.connect(
                lambda: QApplication.clipboard().setText(nome))
        if email and email != "N/D":
            menu.addAction(f"Copia email  ({email})").triggered.connect(
                lambda: QApplication.clipboard().setText(email))
        menu.exec(self.user_table.viewport().mapToGlobal(position))




