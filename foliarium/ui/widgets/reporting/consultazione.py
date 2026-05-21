"""Widget registrazione consultazioni archivio."""
from __future__ import annotations

import os
import csv
import logging
from datetime import date, datetime
from typing import Optional, List, Dict, Any, TYPE_CHECKING

import pandas as pd

from PyQt6.QtCore import (
    QAbstractTableModel, QDate, QModelIndex, QPoint, Qt, QUrl,
)
from PyQt6.QtGui import (
    QDesktopServices,
)
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication,
    QComboBox, QDateEdit, QDialog, QFileDialog,
    QFormLayout, QFrame, QGridLayout, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMenu, QMessageBox, QProgressDialog,
    QPushButton, QSpinBox, QStyle, QTabWidget,
    QTableView, QTextBrowser, QTextEdit, QVBoxLayout,
    QWidget,
)

from app_utils import BulkReportPDF, FPDF_AVAILABLE, GenericTextReportPDF, _get_default_export_path
from catasto_exceptions import DBMError, DBDataError, DBNotFoundError, DBUniqueConstraintError  # noqa: F401
from dialogs import (
    AlberoGeneralogicoDialog, ConfrontoPartiteDialog,
    ComuneSelectionDialog, PartitaSearchDialog, PossessoreSelectionDialog,
)
from foliarium.ui.widgets.custom import LazyLoadedWidget

if TYPE_CHECKING:
    from catasto_db_manager import CatastoDBManager

logger = logging.getLogger("CatastoGUI.reporting_widgets")


class RegistraConsultazioneWidget(QWidget):
    def __init__(self, db_manager: 'CatastoDBManager',
                 current_user_info: Optional[Dict[str, Any]],
                 parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_user_info = current_user_info

        self._initUI()

    def _initUI(self):
        main_layout = QVBoxLayout(self)
        form_group = QGroupBox("Registra Nuova Consultazione")
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(10)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.data_consultazione_edit = QDateEdit(
            calendarPopup=True)  # Nome UI: data_consultazione_edit
        self.data_consultazione_edit.setDate(QDate.currentDate())
        self.data_consultazione_edit.setDisplayFormat("yyyy-MM-dd")
        form_layout.addRow("Data Consultazione (*):",
                           self.data_consultazione_edit)  # Colonna DB: data

        self.richiedente_edit = QLineEdit()
        self.richiedente_edit.setPlaceholderText(
            "Nome e Cognome del richiedente")
        # Colonna DB: richiedente
        form_layout.addRow("Richiedente (*):", self.richiedente_edit)

        self.doc_id_edit = QLineEdit()
        self.doc_id_edit.setPlaceholderText(
            "Es. CI N. XXXXXX, Patente N. YYYYYY")
        # Colonna DB: documento_identita
        form_layout.addRow("Documento Identità (opz.):", self.doc_id_edit)

        self.motivazione_edit = QTextEdit()
        self.motivazione_edit.setPlaceholderText(
            "Motivazione della richiesta di consultazione")
        self.motivazione_edit.setMinimumHeight(80)
        # Colonna DB: motivazione
        form_layout.addRow("Motivazione (opz.):", self.motivazione_edit)

        self.materiale_edit = QTextEdit()
        self.materiale_edit.setPlaceholderText(
            "Descrizione dettagliata del materiale consultato (es. Partita N. 123 Comune X, Mappa Foglio Y)")
        self.materiale_edit.setMinimumHeight(120)
        # Colonna DB: materiale_consultato
        form_layout.addRow("Materiale Consultato (*):", self.materiale_edit)

        # Modificato da QLabel a QLineEdit per permettere modifica
        self.funzionario_edit = QLineEdit()
        if self.current_user_info and self.current_user_info.get('nome_completo'):
            self.funzionario_edit.setText(
                self.current_user_info.get('nome_completo'))
        else:
            self.funzionario_edit.setPlaceholderText("Nome del funzionario")
        # Colonna DB: funzionario_autorizzante
        form_layout.addRow("Funzionario Autorizzante (opz.):",
                           self.funzionario_edit)

        # Rimuoviamo note_interne dato che non c'è nella tabella
        # self.note_interne_edit = QTextEdit() ...
        # form_layout.addRow("Note Interne (opz.):", self.note_interne_edit)

        main_layout.addWidget(form_group)

        button_layout = QHBoxLayout()
        self.btn_registra_consultazione = QPushButton(QApplication.style(
        ).standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), " Registra Consultazione")
        self.btn_registra_consultazione.clicked.connect(
            self._salva_consultazione)
        self.btn_pulisci_campi = QPushButton(QApplication.style().standardIcon(
            QStyle.StandardPixmap.SP_DialogDiscardButton), " Pulisci Campi")
        self.btn_pulisci_campi.clicked.connect(self._pulisci_campi)
        button_layout.addStretch()
        button_layout.addWidget(self.btn_registra_consultazione)
        button_layout.addWidget(self.btn_pulisci_campi)
        main_layout.addLayout(button_layout)

        main_layout.addStretch(1)
        self.setLayout(main_layout)
        self._pulisci_campi()  # Pulisce e imposta focus iniziale

    def _pulisci_form_registrazione(self):
        """Pulisce tutti i campi del form di registrazione proprietà."""
        self.comune_id = None
        self.comune_display.setText("Nessun comune selezionato")
        self.num_partita_edit.setValue(1)  # O il suo valore di default
        self.data_edit.setDate(QDate.currentDate())
        self.possessori_data = []
        self.immobili_data = []
        # Assumendo che questi metodi aggiornino le tabelle UI
        self.update_possessori_table()
        self.update_immobili_table()
        self.num_partita_edit.setFocus()  # Focus sul primo campo utile
        self.suffisso_partita_edit.clear() # Pulisci il suffisso

    def _pulisci_campi(self):
        self.data_consultazione_edit.setDate(QDate.currentDate())
        self.richiedente_edit.clear()
        self.doc_id_edit.clear()
        self.motivazione_edit.clear()
        self.materiale_edit.clear()

        # Precompila o pulisci funzionario_edit
        if self.current_user_info and self.current_user_info.get('nome_completo'):
            self.funzionario_edit.setText(
                self.current_user_info.get('nome_completo'))
        else:
            self.funzionario_edit.clear()

        self.richiedente_edit.setFocus()

    def _salva_consultazione(self):
        data_cons = self.data_consultazione_edit.date().toPyDate()  # Nome colonna DB: 'data'
        richiedente = self.richiedente_edit.text().strip()
        materiale = self.materiale_edit.toPlainText().strip()

        doc_id = self.doc_id_edit.text().strip() or None
        motivazione = self.motivazione_edit.toPlainText().strip() or None
        funzionario_testo = self.funzionario_edit.text().strip() or None  # Testo libero

        # Validazione UI
        if not richiedente:
            QMessageBox.warning(self, "Dati Mancanti",
                                "Il campo 'Richiedente' è obbligatorio.")
            self.richiedente_edit.setFocus()
            return
        if not materiale:  # Anche se nullabile nel DB, lo rendiamo obbligatorio nella UI
            QMessageBox.warning(
                self, "Dati Mancanti", "Il campo 'Materiale Consultato' è obbligatorio.")
            self.materiale_edit.setFocus()
            return

        try:
            consultazione_id = self.db_manager.registra_nuova_consultazione(
                data_consultazione=data_cons,
                richiedente=richiedente,
                materiale_consultato=materiale,
                funzionario_autorizzante=funzionario_testo,  # Passa il testo
                documento_identita=doc_id,
                motivazione=motivazione
                # note_interne non c'è più
            )
            if consultazione_id is not None:
                QMessageBox.information(
                    self, "Successo", f"Consultazione registrata con successo (ID: {consultazione_id}).")
                self._pulisci_campi()
            # else: errore gestito da eccezioni
        except (DBDataError, DBMError) as e:
            logging.getLogger("CatastoGUI").error(
                f"Errore durante la registrazione della consultazione: {str(e)}", exc_info=False)
            QMessageBox.critical(self, "Errore Registrazione", str(e))
        except Exception as e_gen:
            logging.getLogger("CatastoGUI").critical(
                f"Errore imprevisto registrazione consultazione: {e_gen}", exc_info=True)



