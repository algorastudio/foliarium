"""Dialog relativi ai periodi storici."""
from __future__ import annotations

import logging
from typing import Optional, Dict, Any

from PyQt6.QtCore import (QDate, Qt, QTimer)
from PyQt6.QtWidgets import (QAbstractItemView, QApplication,
                             QCheckBox, QComboBox, QDateEdit,
                             QDialog, QFormLayout,
                             QGridLayout, QGroupBox, QHBoxLayout, QHeaderView,
                             QLabel, QLineEdit, QListWidget, QListWidgetItem,
                             QMessageBox, QPushButton, QSpinBox, QStyle,
                             QTabWidget, QTableWidget,
                             QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
                             QDialogButtonBox)

from catasto_db_manager import CatastoDBManager
from app_utils import format_indirizzo
from foliarium.ui.widgets.custom import show_status_message as _show_status_message

try:
    from catasto_db_manager import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError
except ImportError:
    class DBMError(Exception): pass
    class DBUniqueConstraintError(DBMError): pass
    class DBNotFoundError(DBMError): pass
    class DBDataError(DBMError): pass



class PeriodoStoricoDetailsDialog(QDialog):
    def __init__(self, db_manager: 'CatastoDBManager', periodo_id: int, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.periodo_id = periodo_id
        self.periodo_data_originale: Optional[Dict[str, Any]] = None

        self.setWindowTitle(
            f"Dettagli/Modifica Periodo Storico ID: {self.periodo_id}")
        self.setMinimumWidth(450)
        self.setModal(True)

        self._initUI()
        self._load_data()

    def _initUI(self):
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        # Campi Visualizzazione (non editabili)
        self.id_label = QLabel(str(self.periodo_id))
        self.data_creazione_label = QLabel()
        self.data_modifica_label = QLabel()

        form_layout.addRow("ID Periodo:", self.id_label)

        # Campi Editabili
        self.nome_edit = QLineEdit()
        form_layout.addRow("Nome Periodo (*):", self.nome_edit)

        self.anno_inizio_spinbox = QSpinBox()
        # Adatta il range se necessario
        self.anno_inizio_spinbox.setRange(0, 3000)
        form_layout.addRow("Anno Inizio (*):", self.anno_inizio_spinbox)

        self.anno_fine_spinbox = QSpinBox()
        self.anno_fine_spinbox.setRange(0, 3000)
        # Permetti "nessun anno fine" usando un valore speciale o gestendo 0 come "non impostato"
        self.anno_fine_spinbox.setSpecialValueText(
            " ")  # Vuoto se 0 (o il minimo)
        # 0 potrebbe significare "non specificato"
        self.anno_fine_spinbox.setMinimum(0)
        form_layout.addRow("Anno Fine (0 se aperto):", self.anno_fine_spinbox)

        self.descrizione_edit = QTextEdit()
        self.descrizione_edit.setMinimumHeight(100)
        form_layout.addRow("Descrizione:", self.descrizione_edit)

        form_layout.addRow("Data Creazione:", self.data_creazione_label)
        form_layout.addRow("Ultima Modifica:", self.data_modifica_label)

        main_layout.addLayout(form_layout)

        # Pulsanti
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self._save_changes)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self.setLayout(main_layout)

    def _load_data(self):
        self.periodo_data_originale = self.db_manager.get_periodo_storico_details(
            self.periodo_id)

        if not self.periodo_data_originale:
            QMessageBox.critical(self, "Errore Caricamento",
                                 f"Impossibile caricare i dettagli per il periodo ID: {self.periodo_id}.")
            # Chiudi il dialogo se i dati non possono essere caricati
            # Usiamo QTimer per permettere al messaggio di essere processato prima di chiudere
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, self.reject)
            return

        self.nome_edit.setText(self.periodo_data_originale.get('nome', ''))
        self.anno_inizio_spinbox.setValue(
            self.periodo_data_originale.get('anno_inizio', 0))

        anno_fine_val = self.periodo_data_originale.get('anno_fine')
        if anno_fine_val is not None:
            self.anno_fine_spinbox.setValue(anno_fine_val)
        else:  # Se anno_fine è NULL nel DB
            # Mostra testo speciale (" ")
            self.anno_fine_spinbox.setValue(self.anno_fine_spinbox.minimum())

        self.descrizione_edit.setText(
            self.periodo_data_originale.get('descrizione', ''))

        dc = self.periodo_data_originale.get('data_creazione')
        self.data_creazione_label.setText(
            dc.strftime('%Y-%m-%d %H:%M:%S') if dc else 'N/D')
        dm = self.periodo_data_originale.get('data_modifica')
        self.data_modifica_label.setText(
            dm.strftime('%Y-%m-%d %H:%M:%S') if dm else 'N/D')

    def _save_changes(self):
        dati_da_salvare = {
            "nome": self.nome_edit.text().strip(),
            "anno_inizio": self.anno_inizio_spinbox.value(),
            "descrizione": self.descrizione_edit.toPlainText().strip()
        }

        anno_fine_val_ui = self.anno_fine_spinbox.value()
        if self.anno_fine_spinbox.text() == self.anno_fine_spinbox.specialValueText() or anno_fine_val_ui == self.anno_fine_spinbox.minimum():
            # Salva NULL se vuoto o valore minimo
            dati_da_salvare["anno_fine"] = None
        else:
            dati_da_salvare["anno_fine"] = anno_fine_val_ui

        # Validazione base
        if not dati_da_salvare["nome"]:
            QMessageBox.warning(self, "Dati Mancanti",
                                "Il nome del periodo è obbligatorio.")
            self.nome_edit.setFocus()
            return
        if dati_da_salvare["anno_inizio"] <= 0:  # O altra logica per anno inizio
            QMessageBox.warning(self, "Dati Non Validi",
                                "L'anno di inizio deve essere valido.")
            self.anno_inizio_spinbox.setFocus()
            return
        if dati_da_salvare["anno_fine"] is not None and dati_da_salvare["anno_fine"] < dati_da_salvare["anno_inizio"]:
            QMessageBox.warning(
                self, "Date Non Valide", "L'anno di fine non può essere precedente all'anno di inizio.")
            self.anno_fine_spinbox.setFocus()
            return

        try:
            success = self.db_manager.update_periodo_storico(
                self.periodo_id, dati_da_salvare)
            if success:
                _show_status_message("Periodo storico aggiornato.", 4000)
                self.accept()  # Chiude il dialogo e segnala successo
            # else: # update_periodo_storico solleva eccezioni per fallimenti
            # QMessageBox.critical(self, "Errore", "Impossibile aggiornare il periodo storico.")
        except (DBUniqueConstraintError, DBDataError, DBMError) as e:
            logging.getLogger("CatastoGUI").error(
                f"Errore salvataggio periodo storico ID {self.periodo_id}: {str(e)}")
            QMessageBox.critical(self, "Errore Salvataggio", str(e))
        except Exception as e_gen:
            logging.getLogger("CatastoGUI").critical(
                f"Errore imprevisto salvataggio periodo storico ID {self.periodo_id}: {str(e_gen)}", exc_info=True)
            QMessageBox.critical(self, "Errore Imprevisto",
                                 f"Si è verificato un errore: {str(e_gen)}")
            



class PeriodoStoricoEditDialog(QDialog):
    def __init__(self, db_manager, periodo_data: Optional[Dict] = None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.periodo_data = periodo_data
        self.periodo_id = self.periodo_data.get('id') if self.periodo_data else None

        if self.periodo_id:
            self.setWindowTitle(f"Modifica Periodo Storico ID: {self.periodo_id}")
        else:
            self.setWindowTitle("Crea Nuovo Periodo Storico")

        self.setMinimumWidth(400)
        self._initUI()

    def _initUI(self):
        layout = QFormLayout(self)

        nome_default = self.periodo_data.get('nome', '') if self.periodo_data else ''
        anno_inizio_default = self.periodo_data.get('anno_inizio', 1900) if self.periodo_data else 1900
        anno_fine_default = self.periodo_data.get('anno_fine') if self.periodo_data and self.periodo_data.get('anno_fine') is not None else 0
        descrizione_default = self.periodo_data.get('descrizione', '') if self.periodo_data else ''

        self.nome_edit = QLineEdit(nome_default)
        self.anno_inizio_spin = QSpinBox()
        self.anno_inizio_spin.setRange(1000, 3000)
        self.anno_inizio_spin.setValue(anno_inizio_default)
        self.anno_fine_spin = QSpinBox()
        self.anno_fine_spin.setRange(0, 3000)
        self.anno_fine_spin.setSpecialValueText("Aperto")
        self.anno_fine_spin.setValue(anno_fine_default)
        self.descrizione_edit = QTextEdit(descrizione_default)
        self.descrizione_edit.setMinimumHeight(80)

        layout.addRow("Nome (*):", self.nome_edit)
        layout.addRow("Anno Inizio (*):", self.anno_inizio_spin)
        layout.addRow("Anno Fine (0 se Aperto):", self.anno_fine_spin)
        layout.addRow("Descrizione:", self.descrizione_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def save_and_accept(self):
        nome = self.nome_edit.text().strip()
        anno_inizio = self.anno_inizio_spin.value()
        anno_fine = self.anno_fine_spin.value() if self.anno_fine_spin.value() > 0 else None
        descrizione = self.descrizione_edit.toPlainText().strip()

        if not nome:
            QMessageBox.warning(self, "Dati Mancanti", "Il nome del periodo è obbligatorio.")
            return

        try:
            # --- CORREZIONE LOGICA: Chiama il metodo giusto per modifica o creazione ---
            if self.periodo_id:
                # Modalità Modifica
                dati_modificati = {
                    "nome": nome, "anno_inizio": anno_inizio, 
                    "anno_fine": anno_fine, "descrizione": descrizione
                }
                self.db_manager.update_periodo_storico(self.periodo_id, dati_modificati)
            else:
                # Modalità Creazione
                self.db_manager.aggiungi_periodo_storico(nome, anno_inizio, anno_fine, descrizione)

            self.accept() # Chiude il dialogo solo se il salvataggio ha successo
        except (DBMError, DBDataError, DBUniqueConstraintError) as e:
            QMessageBox.critical(self, "Errore di Salvataggio", str(e))



