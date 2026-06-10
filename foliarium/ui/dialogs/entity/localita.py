"""Dialog relativi alle localita."""
from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtWidgets import (QComboBox, QDialog, QFormLayout,
                             QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QDialogButtonBox)

from catasto_db_manager import CatastoDBManager
from foliarium.ui.widgets.custom import show_status_message as _show_status_message

try:
    from catasto_db_manager import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError
except ImportError:
    class DBMError(Exception): pass
    class DBUniqueConstraintError(DBMError): pass
    class DBNotFoundError(DBMError): pass
    class DBDataError(DBMError): pass



class ModificaLocalitaDialog(QDialog):
    def __init__(self, db_manager: CatastoDBManager, localita_id: int, comune_id_parent: int, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.localita_id = localita_id
        self.comune_id_parent = comune_id_parent
        self.localita_data_originale = None
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")

        self.setWindowTitle(f"Modifica Dati Località ID: {self.localita_id}")
        self.setMinimumWidth(450)

        self._init_ui()
        self._load_localita_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        self.id_label = QLabel(str(self.localita_id))
        form_layout.addRow("ID Località:", self.id_label)
        self.comune_display_label = QLabel("Caricamento...")
        form_layout.addRow("Comune di Appartenenza:", self.comune_display_label)
        self.nome_edit = QLineEdit()
        form_layout.addRow("Nome Località (*):", self.nome_edit)
        self.tipologia_edit = QLineEdit()
        form_layout.addRow("Tipologia Stradale (*):", self.tipologia_edit)
        layout.addLayout(form_layout)

        buttons_layout = QHBoxLayout()
        self.btn_archivia = QPushButton("Archivia Località")
        self.btn_archivia.setObjectName("dangerButton")
        self.btn_archivia.setToolTip("Archivia questa località (non viene eliminata, solo nascosta)")
        self.btn_archivia.clicked.connect(self._archivia_localita)
        buttons_layout.addWidget(self.btn_archivia)
        buttons_layout.addStretch()

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self._save_changes)
        self.button_box.rejected.connect(self.reject)
        buttons_layout.addWidget(self.button_box)

        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def _load_localita_data(self):
        """Carica i dati della località da modificare."""
        self.localita_data_originale = self.db_manager.get_localita_details(self.localita_id)
        if not self.localita_data_originale:
            QMessageBox.critical(self, "Errore", "Impossibile caricare i dati della località.")
            self.reject()
            return

        self.nome_edit.setText(self.localita_data_originale.get('nome', ''))
        self.comune_display_label.setText(f"{self.localita_data_originale.get('comune_nome', 'N/D')} (ID: {self.comune_id_parent})")
        self.tipologia_edit.setText(self.localita_data_originale.get('tipologia_stradale', '') or '')

    def _save_changes(self):
        """Salva le modifiche alla località."""
        nome = self.nome_edit.text().strip()
        tipologia_stradale = self.tipologia_edit.text().strip()
        if not nome:
            QMessageBox.warning(self, "Dati Mancanti", "Il nome della località è obbligatorio.")
            return
        if not tipologia_stradale:
            QMessageBox.warning(self, "Dati Mancanti", "La tipologia stradale è obbligatoria (es. Via, Piazza, Borgata).")
            self.tipologia_edit.setFocus()
            return

        dati_modificati = {
            "nome": nome,
            "tipologia_stradale": tipologia_stradale,
        }

        try:
            self.db_manager.update_localita(self.localita_id, dati_modificati)
            self.accept()
        except (DBMError, DBDataError, DBUniqueConstraintError) as e:
            QMessageBox.critical(self, "Errore Salvataggio", str(e))

    def _archivia_localita(self):
        nome = self.nome_edit.text()
        risposta = QMessageBox.question(
            self, "Conferma Archiviazione",
            f"Archiviare la località '{nome}'?\n\nNon verrà eliminata, solo nascosta dalle ricerche.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if risposta != QMessageBox.StandardButton.Yes:
            return
        try:
            self.db_manager.archivia_localita(self.localita_id)
            _show_status_message(f"Località '{nome}' archiviata.", 4000)
            self.reject()
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile archiviare la località:\n{e}")




class CreateLocalitaDialog(QDialog):
    """Dialog inline per aggiungere una località a un comune già noto.

    Pensato per il quick-add da Registrazione Proprietà / Inserimento Immobile:
    il comune è fissato dal chiamante e mostrato in sola lettura.
    """

    def __init__(self, db_manager: 'CatastoDBManager', comune_id: int,
                 comune_nome: str, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.comune_id = comune_id
        self.comune_nome = comune_nome
        self.nuova_localita_id: Optional[int] = None
        self.nuova_localita_nome: str = ""
        self.nuova_tipologia_stradale: str = ""

        self.setWindowTitle(f"Nuova Località — {comune_nome}")
        self.setMinimumWidth(420)
        self.setModal(True)

        layout = QFormLayout(self)

        comune_lbl = QLabel(f"<b>{comune_nome}</b>")
        layout.addRow("Comune:", comune_lbl)

        self.nome_edit = QLineEdit()
        self.nome_edit.setPlaceholderText("Es. Roma, Garibaldi, Pianello (senza tipologia)")
        layout.addRow("Nome (*):", self.nome_edit)

        self.tipo_combo = QComboBox()
        self.tipo_combo.addItem("--- Seleziona ---", None)
        layout.addRow("Tipologia (*):", self.tipo_combo)

        hint = QLabel("Il civico non si inserisce qui: andrà nel singolo immobile.")
        hint.setStyleSheet("color: #666; font-size: 11px;")
        layout.addRow(hint)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addRow(self.button_box)

        self.button_box.accepted.connect(self._salva_e_accetta)
        self.button_box.rejected.connect(self.reject)
        self.nome_edit.returnPressed.connect(self._salva_e_accetta)

        self._carica_tipologie()
        self.nome_edit.setFocus()

    def _carica_tipologie(self):
        try:
            tipi = self.db_manager.get_tipi_localita()
            for tipo in tipi or []:
                self.tipo_combo.addItem(tipo['nome'], tipo['nome'])
        except DBMError as e:
            QMessageBox.critical(self, "Errore",
                                 f"Impossibile caricare le tipologie di località:\n{e}")

    def _salva_e_accetta(self):
        nome = self.nome_edit.text().strip()
        tipologia = self.tipo_combo.currentData()

        if not nome or not tipologia:
            QMessageBox.warning(self, "Dati Mancanti",
                                "Nome e Tipologia sono obbligatori.")
            return

        try:
            self.nuova_localita_id = self.db_manager.insert_localita(
                self.comune_id, nome, tipologia
            )
            self.nuova_localita_nome = nome
            self.nuova_tipologia_stradale = tipologia
            self.accept()
        except (DBMError, DBDataError, DBUniqueConstraintError) as e:
            QMessageBox.critical(self, "Errore Inserimento", str(e))




