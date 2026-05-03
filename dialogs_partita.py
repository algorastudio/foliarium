"""
dialogs_partita.py — Dialog relativi alle partite catastali.

Classi estratte da dialogs.py:
  PartitaDetailsDialog, ModificaPartitaDialog, DuplicaPartitaOptionsDialog,
  PossessoreSelectionDialog, ModificaImmobileDialog, ImmobileDialog,
  AggiungiDocumentoDialog, AlberoGeneralogicoDialog, ConfrontoPartiteDialog
"""
from __future__ import annotations

import logging
import os
import csv
import json
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Tuple

from PyQt6.QtCore import (QDate, QDateTime, QPoint, QSettings,
                          QSize, Qt, QTimer, QUrl, pyqtSignal)
from PyQt6.QtGui import (QBrush, QColor, QDesktopServices, QFont,
                         QIcon, QPalette, QPixmap, QAction)
from PyQt6.QtWidgets import (QAbstractItemView, QApplication,
                             QCheckBox, QComboBox, QDateEdit,
                             QDialog, QDoubleSpinBox,
                             QFileDialog, QFormLayout, QFrame, QGridLayout,
                             QGroupBox, QHBoxLayout, QHeaderView, QInputDialog,
                             QLabel, QLineEdit, QListWidget, QListWidgetItem,
                             QMenu, QMessageBox, QProgressBar,
                             QPushButton, QScrollArea, QSizePolicy, QSpacerItem,
                             QSpinBox, QStyle, QTabWidget,
                             QSplitter, QTableWidget, QTableWidgetItem, QTextEdit,
                             QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget,
                             QTextBrowser, QDialogButtonBox)
from PyQt6.QtGui import QPainter
from app_paths import get_resource_path

from config import (
    SETTINGS_DB_HOST, SETTINGS_DB_PORT,
    SETTINGS_DB_NAME, SETTINGS_DB_USER,
)
from catasto_db_manager import CatastoDBManager
from custom_widgets import QPasswordLineEdit, ImmobiliTableWidget

from app_utils import (gui_esporta_partita_pdf, gui_esporta_partita_json, gui_esporta_partita_csv,
                       gui_esporta_possessore_pdf, gui_esporta_possessore_json, gui_esporta_possessore_csv,
                       GenericTextReportPDF, FPDF_AVAILABLE, prompt_to_open_file, PDFApreviewDialog)

from dialogs_admin import datetime_to_qdate, qdate_to_datetime

try:
    from catasto_db_manager import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError
except ImportError:
    class DBMError(Exception): pass
    class DBUniqueConstraintError(DBMError): pass
    class DBNotFoundError(DBMError): pass
    class DBDataError(DBMError): pass

class PartitaDetailsDialog(QDialog):
    def __init__(self, partita_data, parent=None):
        super(PartitaDetailsDialog, self).__init__(parent)
        self.partita = partita_data
        self.db_manager = getattr(parent, 'db_manager', None) 
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")

        self.setWindowTitle(
            f"Dettagli Partita {partita_data['numero_partita']}")
        self.setMinimumSize(700, 500)

        self._init_ui()
        self._load_all_data() # <--- Assicurati che sia chiamato solo qui
        self._update_document_tab_title() 

        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        

        

        # Sostituisci questa riga:
        # title_label = QLabel(f"<h2>Partita N.{self.partita['numero_partita']} ({self.partita['suffisso_partita']}) - {self.partita['comune_nome']}</h2>")

        # Con questa logica più robusta:
        header_layout = QHBoxLayout()
        suffisso_db = self.partita.get('suffisso_partita')

        # Controlliamo se il suffisso esiste e non è una stringa vuota
        suffisso_display = f" ({suffisso_db.strip()})" if suffisso_db and suffisso_db.strip() else ""

        titolo_completo = f"<h2>Partita N.{self.partita['numero_partita']}{suffisso_display} - {self.partita['comune_nome']}</h2>"
        title_label = QLabel(titolo_completo)

        
        header_layout.addWidget(title_label)
        layout.addLayout(header_layout)

        # Informazioni generali
        info_group = QGroupBox("Informazioni Generali")
        info_layout = QGridLayout()

        info_layout.addWidget(QLabel("<b>ID:</b>"), 0, 0)
        info_layout.addWidget(QLabel(str(self.partita['id'])), 0, 1)

        info_layout.addWidget(QLabel("<b>Tipo:</b>"), 0, 2)
        info_layout.addWidget(QLabel(self.partita['tipo']), 0, 3)

        info_layout.addWidget(QLabel("<b>Stato:</b>"), 1, 0)
        info_layout.addWidget(QLabel(self.partita['stato']), 1, 1)

        info_layout.addWidget(QLabel("<b>Data Impianto:</b>"), 1, 2)
        info_layout.addWidget(QLabel(str(self.partita['data_impianto'])), 1, 3)

        # NUOVA RIGA: Suffisso Partita
        info_layout.addWidget(QLabel("<b>Suffisso:</b>"), 2, 2) # Adatta la riga/colonna
        info_layout.addWidget(QLabel(self.partita.get('suffisso_partita', 'N/A')), 2, 3)

        if self.partita.get('data_chiusura'):
            info_layout.addWidget(QLabel("<b>Data Chiusura:</b>"), 2, 0) # Adatta la riga
            info_layout.addWidget(QLabel(str(self.partita['data_chiusura'])), 2, 1)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Tabs per possessori, immobili, variazioni, documenti
        self.tabs = QTabWidget() # Rinomina a self.tabs per coerenza
        layout.addWidget(self.tabs)

        # Tab Possessori
        possessori_tab = QWidget()
        possessori_layout = QVBoxLayout(possessori_tab)
        possessori_table = QTableWidget()
        possessori_table.setColumnCount(4)
        possessori_table.setHorizontalHeaderLabels(["ID", "Nome Completo", "Titolo", "Quota"])
        possessori_table.setAlternatingRowColors(True)
        # --- INIZIO MODIFICA ---
        # Aggiungi queste righe per gestire il ridimensionamento delle colonne
        header_possessori = possessori_table.horizontalHeader()
        # La colonna "ID" (indice 0) si adatta al contenuto
        header_possessori.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        # La colonna "Nome Completo" (indice 1) si espande per riempire lo spazio
        header_possessori.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        # Le colonne "Titolo" e "Quota" (indici 2 e 3) si adattano al contenuto
        header_possessori.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header_possessori.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
# --- FINE MODIFICA ---
        if self.partita.get('possessori'):
            possessori_table.setRowCount(len(self.partita['possessori']))
            for i, possessore in enumerate(self.partita['possessori']):
                possessori_table.setItem(i, 0, QTableWidgetItem(str(possessore.get('id', ''))))
                possessori_table.setItem(i, 1, QTableWidgetItem(possessore.get('nome_completo', '')))
                possessori_table.setItem(i, 2, QTableWidgetItem(possessore.get('titolo', '')))
                possessori_table.setItem(i, 3, QTableWidgetItem(possessore.get('quota', '')))
        possessori_layout.addWidget(possessori_table)
        self.tabs.addTab(possessori_tab, "Possessori")

        # Tab Immobili
        immobili_tab = QWidget()
        immobili_layout = QVBoxLayout(immobili_tab)
        immobili_table = ImmobiliTableWidget()
        if self.partita.get('immobili'):
            immobili_table.populate_data(self.partita['immobili'])
        immobili_layout.addWidget(immobili_table)
        self.tabs.addTab(immobili_tab, "Immobili")

        # Tab Variazioni
        variazioni_tab = QWidget()
        variazioni_layout = QVBoxLayout()

        variazioni_table = QTableWidget()
        # Aumenta il numero di colonne per includere origine e destinazione per esteso
        variazioni_table.setColumnCount(6) # Ad es., ID, Tipo, Data, Partita Origine, Partita Destinazione, Contratto
        variazioni_table.setHorizontalHeaderLabels([
            "ID Var.", "Tipo", "Data Var.", "Partita Origine", "Partita Destinazione", "Contratto" # Etichette aggiornate
        ])
        variazioni_table.setAlternatingRowColors(True)
        variazioni_table.horizontalHeader().setStretchLastSection(True) # Per far espandere l'ultima colonna
        variazioni_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        if self.partita.get('variazioni'):
            variazioni_table.setRowCount(len(self.partita['variazioni']))
            for i, var in enumerate(self.partita['variazioni']):
                col = 0
                variazioni_table.setItem(i, col, QTableWidgetItem(str(var.get('id', '')))); col += 1
                variazioni_table.setItem(i, col, QTableWidgetItem(var.get('tipo', ''))); col += 1
                variazioni_table.setItem(i, col, QTableWidgetItem(str(var.get('data_variazione', '')))); col += 1

                # Informazioni Partita Origine
                origine_text = ""
                if var.get('partita_origine_id'): # Solo se l'ID esiste
                    num_orig = var.get('origine_numero_partita', 'N/D')
                    com_orig = var.get('origine_comune_nome', 'N/D')
                    origine_text = f"N.{num_orig} ({com_orig})"
                else:
                    origine_text = "-" # O "N/A"
                variazioni_table.setItem(i, col, QTableWidgetItem(origine_text)); col += 1

                # Informazioni Partita Destinazione
                dest_text = ""
                if var.get('partita_destinazione_id'): # Solo se l'ID esiste
                    num_dest = var.get('destinazione_numero_partita', 'N/D')
                    com_dest = var.get('destinazione_comune_nome', 'N/D')
                    dest_text = f"N.{num_dest} ({com_dest})"
                else:
                    dest_text = "-" # O "N/A"
                variazioni_table.setItem(i, col, QTableWidgetItem(dest_text)); col += 1

                # Contratto info (come prima)
                contratto_text = ""
                if var.get('tipo_contratto'):
                    contratto_text = f"{var['tipo_contratto']} del {var.get('data_contratto', '')}"
                    if var.get('notaio'):
                        contratto_text += f" - {var['notaio']}"
                variazioni_table.setItem(i, col, QTableWidgetItem(contratto_text)); col += 1

        variazioni_layout.addWidget(variazioni_table)
        variazioni_tab.setLayout(variazioni_layout)
        self.tabs.addTab(variazioni_tab, "Variazioni")


        # Tab Documenti (come prima)
        self.documents_tab_widget = QWidget()
        self.documents_tab_layout = QVBoxLayout(self.documents_tab_widget)
        self.documents_table = QTableWidget()
        self.documents_table.setColumnCount(6)
        self.documents_table.setHorizontalHeaderLabels(["ID Doc.", "Titolo", "Tipo Doc.", "Anno", "Rilevanza", "Percorso"])
        self.documents_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.documents_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.documents_table.horizontalHeader().setStretchLastSection(True)
        self.documents_table.setSortingEnabled(True)
        self.documents_table.itemSelectionChanged.connect(self._update_details_doc_buttons_state)
        self.documents_tab_layout.addWidget(self.documents_table)
        
        doc_buttons_layout = QHBoxLayout()
        self.btn_apri_doc_details_dialog = QPushButton(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton), "Apri Documento")
        self.btn_apri_doc_details_dialog.clicked.connect(self._apri_documento_selezionato_from_details_dialog)
        self.btn_apri_doc_details_dialog.setEnabled(False)
        doc_buttons_layout.addWidget(self.btn_apri_doc_details_dialog)
        doc_buttons_layout.addStretch()
        self.documents_tab_layout.addLayout(doc_buttons_layout)
        self.tabs.addTab(self.documents_tab_widget, "Documenti Allegati")


        # --- Sostituzione dei pulsanti di esportazione ---
        buttons_layout = QHBoxLayout()

        self.btn_export_txt = QPushButton("Esporta TXT")
        self.btn_export_txt.clicked.connect(self._export_partita_to_txt)
        buttons_layout.addWidget(self.btn_export_txt)

        self.btn_export_pdf = QPushButton("Esporta PDF")
        self.btn_export_pdf.clicked.connect(self._export_partita_to_pdf)
        self.btn_export_pdf.setEnabled(FPDF_AVAILABLE) # Abilita solo se FPDF è disponibile
        buttons_layout.addWidget(self.btn_export_pdf)

        # Il pulsante JSON che avevi prima era export_button. Lo rimuoviamo o lo rendiamo PDF/TXT.
        # export_button = QPushButton("Esporta in JSON")
        # export_button.clicked.connect(self.export_to_json) # Non più chiamato
        # buttons_layout.addWidget(export_button) # Rimuovi o commenta questa riga

        btn_albero = QPushButton("Albero Genealogico")
        btn_albero.clicked.connect(self._apri_albero_genealogico)
        buttons_layout.addWidget(btn_albero)

        close_button = QPushButton("Chiudi")
        close_button.clicked.connect(self.accept)

        buttons_layout.addStretch()
        # buttons_layout.addWidget(export_button) # Rimosso
        buttons_layout.addWidget(close_button)

        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def _apri_albero_genealogico(self):
        if not self.db_manager:
            QMessageBox.warning(self, "DB non disponibile", "Database manager non disponibile.")
            return
        AlberoGeneralogicoDialog(self.partita['id'], self.db_manager, self).exec()

    def _load_all_data(self):
        """Carica i dati per tutti i tab."""
        # Se il db_manager non è stato passato o non è valido
        if not self.db_manager:
            self.logger.warning("DB Manager non disponibile, impossibile caricare i dati dei documenti.")
            # Popola la tabella con un messaggio di errore o lascia vuota
            self.documents_table.setRowCount(1)
            item_msg = QTableWidgetItem("DB Manager non disponibile. Impossibile caricare documenti.")
            item_msg.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.documents_table.setItem(0, 0, item_msg)
            self.documents_table.setSpan(0, 0, 1, self.documents_table.columnCount())
            return

        # Carica i documenti e aggiorna la tabella dei documenti
        try:
            documenti_list = self.db_manager.get_documenti_per_partita(self.partita['id'])
            self.documents_table.setRowCount(0) # Pulisci prima di popolare

            if documenti_list:
                self.documents_table.setRowCount(len(documenti_list))
                for row, doc_data in enumerate(documenti_list):
                    self.documents_table.setItem(row, 0, QTableWidgetItem(str(doc_data.get('documento_id', ''))))
                    self.documents_table.setItem(row, 1, QTableWidgetItem(doc_data.get('titolo', '')))
                    self.documents_table.setItem(row, 2, QTableWidgetItem(doc_data.get('tipo_documento', '')))
                    self.documents_table.setItem(row, 3, QTableWidgetItem(str(doc_data.get('anno', ''))))
                    self.documents_table.setItem(row, 4, QTableWidgetItem(doc_data.get('rilevanza', '')))
                    
                    # Percorso, con un tooltip che mostra il percorso completo
                    percorso_file_full = doc_data.get('percorso_file', 'N/D')
                    path_item = QTableWidgetItem(os.path.basename(percorso_file_full) if percorso_file_full else "N/D")
                    path_item.setToolTip(percorso_file_full) # Il tooltip mostrerà il percorso completo
                    # Salva il percorso completo nell'UserRole per il pulsante "Apri"
                    percorso_file_full = doc_data.get('percorso_file', '')
                    path_item = QTableWidgetItem(os.path.basename(percorso_file_full) if percorso_file_full else "N/D")
                    path_item.setData(Qt.ItemDataRole.UserRole, percorso_file_full)  # Assicurati che questo sia sempre una stringa valida
                    self.documents_table.setItem(row, 5, path_item)
                self.documents_table.resizeColumnsToContents()
            else:
                self.logger.info(f"Nessun documento allegato per la partita ID {self.partita['id']}.")
                self.documents_table.setRowCount(1)
                no_docs_item = QTableWidgetItem("Nessun documento allegato a questa partita.")
                no_docs_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.documents_table.setItem(0, 0, no_docs_item)
                self.documents_table.setSpan(0, 0, 1, self.documents_table.columnCount())
        except Exception as e:
            self.logger.error(f"Errore durante il caricamento dei documenti per la partita {self.partita['id']}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Caricamento Documenti", f"Si è verificato un errore durante il caricamento dei documenti: {e}")
            self.documents_table.setRowCount(1)
            error_item = QTableWidgetItem("Errore nel caricamento dei documenti.")
            error_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.documents_table.setItem(0, 0, error_item)
            self.documents_table.setSpan(0, 0, 1, self.documents_table.columnCount())
        finally:
            self.documents_table.setSortingEnabled(True)
            self._update_document_tab_title() # Aggiorna il titolo del tab con il conteggio
            self._update_details_doc_buttons_state() # Aggiorna lo stato dei pulsanti Apri

    def _export_partita_to_txt(self):
        """Esporta i dettagli della partita in formato TXT (testo leggibile)."""
        if not self.partita:
            QMessageBox.warning(self, "Errore Dati", "Nessun dato della partita da esportare.")
            return

        partita_id = self.partita.get('id', 'sconosciuto')
        default_filename = f"dettaglio_partita_{partita_id}_{date.today().isoformat()}.txt"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Salva Dettaglio Partita in TXT",
            default_filename,
            "File di testo (*.txt);;Tutti i file (*)"
        )

        if file_path:
            try:
                # Genera un testo leggibile con le informazioni della partita
                text_content = self._generate_partita_text_report()

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text_content)

                prompt_to_open_file(self, file_path)
                self.logger.info(f"Dettaglio partita TXT salvato con successo in: {file_path}")
            except Exception as e:
                self.logger.error(f"Errore durante l'esportazione TXT del dettaglio partita: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Esportazione", f"Errore durante il salvataggio del file TXT:\n{e}")

    def _export_partita_to_pdf(self):
        """Esporta i dettagli della partita in formato PDF."""
        if not FPDF_AVAILABLE:
            QMessageBox.critical(self, "Errore Libreria", "La libreria FPDF (fpdf2) non è disponibile per generare PDF.")
            return
        if not self.partita:
            QMessageBox.warning(self, "Errore Dati", "Nessun dato della partita da esportare.")
            return

        partita_id = self.partita.get('id', 'sconosciuto')
        pdf_report_title = f"Dettaglio Partita N.{self.partita.get('numero_partita', 'N/D')} - Comune: {self.partita.get('comune_nome', 'N/D')}"
        default_filename_prefix = f"dettaglio_partita_{partita_id}"

        # Genera un testo leggibile per l'anteprima e per il PDF
        text_content = self._generate_partita_text_report()

        # Usa la classe generica per l'esportazione PDF (che include l'anteprima)
        # Nota: PDFApreviewDialog e GenericTextReportPDF sono in app_utils
        preview_dialog = PDFApreviewDialog(text_content, self, title=f"Anteprima: {pdf_report_title}")
        if preview_dialog.exec() != QDialog.DialogCode.Accepted:
            self.logger.info(f"Esportazione PDF per '{pdf_report_title}' annullata dall'utente dopo anteprima.")
            return

        filename_pdf, _ = QFileDialog.getSaveFileName(
            self, f"Salva PDF - {pdf_report_title}", f"{default_filename_prefix}_{date.today().isoformat()}.pdf", "File PDF (*.pdf)")

        if filename_pdf:
            try:
                pdf = GenericTextReportPDF(report_title=pdf_report_title)
                pdf.alias_nb_pages()
                pdf.add_page()
                pdf.add_report_text(text_content)
                pdf.output(filename_pdf)
                prompt_to_open_file(self, filename_pdf)
                self.logger.info(f"Dettaglio partita PDF salvato con successo in: {filename_pdf}")
            except Exception as e:
                self.logger.error(f"Errore durante la generazione del PDF per il dettaglio partita: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Esportazione PDF", f"Impossibile generare il PDF:\n{e}")

    def _generate_partita_text_report(self) -> str:
        """
        Genera un report testuale formattato con tutti i dettagli della partita,
        inclusi i possessori, immobili, variazioni e documenti allegati.
        """
        report_lines = []
        partita = self.partita # self.partita contiene tutti i dati recuperati da get_partita_details

        # --- SEZIONE 1: INTESTAZIONE E DATI GENERALI PARTITA ---
        report_lines.append("=" * 70)
        # Includi il suffisso nel titolo, se presente
        numero_partita_display = f"N. {partita.get('numero_partita', 'N/D')}"
        if partita.get('suffisso_partita'):
            numero_partita_display += f" ({partita['suffisso_partita']})"

        report_lines.append(f"DETTAGLIO PARTITA {numero_partita_display}")
        report_lines.append(f"Comune: {partita.get('comune_nome', 'N/D')}")
        report_lines.append(f"ID Partita: {partita.get('id', 'N/D')}")
        report_lines.append("=" * 70)

        report_lines.append(f"Tipo Partita: {partita.get('tipo', 'N/D')}")
        report_lines.append(f"Stato: {partita.get('stato', 'N/D')}")
        report_lines.append(f"Data Impianto: {partita.get('data_impianto', 'N/D')}")
        data_chiusura = partita.get('data_chiusura')
        report_lines.append(f"Data Chiusura: {data_chiusura if data_chiusura else 'N/A'}")
        numero_provenienza = partita.get('numero_provenienza')
        report_lines.append(f"Numero Provenienza: {numero_provenienza if numero_provenienza else 'N/A'}")
        report_lines.append("\n") # Linea vuota per separazione

        # --- SEZIONE 2: POSSESSORI ---
        report_lines.append("=" * 70)
        report_lines.append("POSSESSORI ASSOCIATI")
        report_lines.append("=" * 70)
        if partita.get('possessori'):
            for i, poss in enumerate(partita['possessori']):
                report_lines.append(f"  - Possessore {i+1} (ID: {poss.get('id', 'N/D')}): {poss.get('nome_completo', 'N/D')}")
                report_lines.append(f"    Titolo di Possesso: {poss.get('titolo', 'N/A')}")
                report_lines.append(f"    Quota: {poss.get('quota', 'N/A')}")
                if i < len(partita['possessori']) - 1:
                    report_lines.append("  " + "-" * 60) # Separatore tra possessori
        else:
            report_lines.append("  Nessun possessore associato a questa partita.")
        report_lines.append("\n") # Linea vuota per separazione

        # --- SEZIONE 3: IMMOBILI ---
        report_lines.append("=" * 70)
        report_lines.append("IMMOBILI CENSITI")
        report_lines.append("=" * 70)
        if partita.get('immobili'):
            for i, imm in enumerate(partita['immobili']):
                report_lines.append(f"  - Immobile {i+1} (ID: {imm.get('id', 'N/D')}): {imm.get('natura', 'N/D')}")
                localita_info = f"{imm.get('localita_nome', '')}"
                if imm.get('civico') is not None and str(imm.get('civico')).strip() != '':
                    localita_info += f", civ. {imm.get('civico')}"
                if imm.get('localita_tipo'):
                    localita_info += f" ({imm.get('localita_tipo')})"
                report_lines.append(f"    Località: {localita_info.strip() if localita_info.strip() else 'N/A'}")
                report_lines.append(f"    Classificazione: {imm.get('classificazione', 'N/A')}")
                report_lines.append(f"    Consistenza: {imm.get('consistenza', 'N/A')}")
                piani_vani_info = []
                if imm.get('numero_piani') is not None and imm.get('numero_piani') > 0:
                    piani_vani_info.append(f"Piani: {imm.get('numero_piani')}")
                if imm.get('numero_vani') is not None and imm.get('numero_vani') > 0:
                    piani_vani_info.append(f"Vani: {imm.get('numero_vani')}")
                if piani_vani_info:
                    report_lines.append(f"    Dettagli: {' | '.join(piani_vani_info)}")
                
                if i < len(partita['immobili']) - 1:
                    report_lines.append("  " + "-" * 60) # Separatore tra immobili
        else:
            report_lines.append("  Nessun immobile associato a questa partita.")
        report_lines.append("\n") # Linea vuota per separazione

        # --- SEZIONE 4: VARIAZIONI ---
        report_lines.append("=" * 70)
        report_lines.append("VARIAZIONI STORICHE")
        report_lines.append("=" * 70)
        if partita.get('variazioni'):
            for i, var in enumerate(partita['variazioni']):
                report_lines.append(f"  - Variazione {i+1} (ID: {var.get('id', 'N/D')}): {var.get('tipo', 'N/D')}")
                report_lines.append(f"    Data Variazione: {var.get('data_variazione', 'N/D')}")
                
                # Dettagli Partita Origine
                orig_part_id = var.get('partita_origine_id')
                orig_num = var.get('origine_numero_partita', 'N/D')
                orig_com = var.get('origine_comune_nome', 'N/D')
                if orig_part_id:
                    report_lines.append(f"    Partita Origine: N.{orig_num} (Comune: {orig_com}) [ID: {orig_part_id}]")
                else:
                    report_lines.append("    Partita Origine: N/A")

                # Dettagli Partita Destinazione
                dest_part_id = var.get('partita_destinazione_id')
                dest_num = var.get('destinazione_numero_partita', 'N/D')
                dest_com = var.get('destinazione_comune_nome', 'N/D')
                if dest_part_id:
                    report_lines.append(f"    Partita Destinazione: N.{dest_num} (Comune: {dest_com}) [ID: {dest_part_id}]")
                else:
                    report_lines.append("    Partita Destinazione: N/A")

                # Dettagli Contratto
                contr_info_parts = []
                if var.get('tipo_contratto'): contr_info_parts.append(f"Tipo: {var.get('tipo_contratto')}")
                if var.get('data_contratto'): contr_info_parts.append(f"Data: {var.get('data_contratto')}")
                if var.get('notaio'): contr_info_parts.append(f"Notaio: {var.get('notaio')}")
                if var.get('repertorio'): contr_info_parts.append(f"Repertorio: {var.get('repertorio')}")
                if contr_info_parts:
                    report_lines.append(f"    Contratto: {' | '.join(contr_info_parts)}")
                
                if var.get('note_variazione') : report_lines.append(f"    Note Variazione: {var.get('note_variazione')}") # Se c'è una colonna note per la variazione
                if var.get('contratto_note') : report_lines.append(f"    Note Contratto: {var.get('contratto_note')}") # Se c'è una colonna note nel contratto

                if i < len(partita['variazioni']) - 1:
                    report_lines.append("  " + "-" * 60) # Separatore tra variazioni
        else:
            report_lines.append("  Nessuna variazione registrata per questa partita.")
        report_lines.append("\n") # Linea vuota per separazione

        # --- SEZIONE 5: DOCUMENTI ALLEGATI ---
        report_lines.append("=" * 70)
        # Assicurati che self.documents_table sia popolata correttamente
        num_docs = self.documents_table.rowCount()
        # Se la tabella ha una sola riga e contiene il messaggio "Nessun documento..."
        if num_docs == 1 and self.documents_table.item(0,0) and "Nessun documento" in self.documents_table.item(0,0).text():
            num_docs = 0
        report_lines.append(f"DOCUMENTI ALLEGATI ({num_docs})")
        report_lines.append("=" * 70)
        
        if num_docs > 0:
            for r in range(self.documents_table.rowCount()):
                # Assicurati che gli item non siano None (se la tabella è vuota eccetto il placeholder)
                doc_id_item = self.documents_table.item(r,0)
                if not doc_id_item: continue # Salta se la riga è vuota (es. riga placeholder)

                doc_id = doc_id_item.text()
                titolo = self.documents_table.item(r,1).text()
                tipo_doc = self.documents_table.item(r,2).text()
                anno = self.documents_table.item(r,3).text()
                rilevanza = self.documents_table.item(r,4).text()
                percorso_short = self.documents_table.item(r,5).text()

                report_lines.append(f"  - Documento {r+1} (ID: {doc_id}): {titolo}")
                report_lines.append(f"    Tipo: {tipo_doc}, Anno: {anno}, Rilevanza: {rilevanza}")
                report_lines.append(f"    Percorso (locale): {percorso_short}")
                if r < num_docs - 1:
                    report_lines.append("  " + "-" * 60) # Separatore tra documenti
        else:
            report_lines.append("  Nessun documento allegato.")

        # --- SEZIONE FINALE ---
        report_lines.append("\n" + "=" * 70)
        report_lines.append("FINE DETTAGLIO PARTITA")
        report_lines.append("=" * 70)

        return "\n".join(report_lines)
    def _update_document_tab_title(self):
        """Aggiorna il titolo del tab "Documenti Allegati" con il conteggio."""
        count = self.documents_table.rowCount()
        # Se la tabella ha solo 1 riga e il testo è "Nessun documento allegato..." allora il conteggio è 0
        if count == 1 and self.documents_table.item(0,0) and "Nessun documento" in self.documents_table.item(0,0).text():
            count = 0
        
        tab_index = self.tabs.indexOf(self.documents_tab_widget)
        if tab_index != -1:
            self.tabs.setTabText(tab_index, f"Documenti Allegati ({count})")
            self.logger.info(f"Titolo tab documenti aggiornato a 'Documenti Allegati ({count})'.")


    def _update_details_doc_buttons_state(self):
        """Abilita/disabilita il pulsante 'Apri Documento' in base alla selezione."""
        has_selection = bool(self.documents_table.selectedItems())
        self.btn_apri_doc_details_dialog.setEnabled(has_selection)

    def _apri_documento_selezionato_from_details_dialog(self):
        selected_items = self.documents_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un documento dalla lista per aprirlo.")
            return
        
        row = self.documents_table.currentRow()
        percorso_file_item = self.documents_table.item(row, 5) 
        if percorso_file_item:
            percorso_file_completo = percorso_file_item.data(Qt.ItemDataRole.UserRole) # Recupera il percorso completo salvato
            
            if os.path.exists(percorso_file_completo):
                from PyQt6.QtGui import QDesktopServices
                from PyQt6.QtCore import QUrl
                success = QDesktopServices.openUrl(QUrl.fromLocalFile(percorso_file_completo))
                if not success:
                    QMessageBox.warning(self, "Errore Apertura", f"Impossibile aprire il file:\n{percorso_file_completo}\nVerificare che sia installata un'applicazione associata o che i permessi siano corretti.")
            else:
                QMessageBox.warning(self, "File Non Trovato", f"Il file specificato non è stato trovato al percorso:\n{percorso_file_completo}\nIl file potrebbe essere stato spostato o eliminato.")
        else:
            QMessageBox.warning(self, "Percorso Mancante", "Informazioni sul percorso del file non disponibili per il documento selezionato.")


class ModificaPartitaDialog(QDialog):
    def __init__(self, db_manager: 'CatastoDBManager', partita_id: int, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.partita_id = partita_id
        self.partita_data_originale: Optional[Dict[str, Any]] = None
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")

        self.setWindowTitle(f"Dettagli Partita ID: {self.partita_id}")
        self.setMinimumSize(800, 600)

        self._init_ui() # Crea i widget vuoti
        self._load_all_partita_data() # Carica i dati e popola i widget

    def _init_ui(self):
        """Crea tutti i componenti della UI, ma non li popola con i dati."""
        main_layout = QVBoxLayout(self)

        # Sezione Intestazione con placeholder
        header_group = QGroupBox("Dettagli Partita Corrente")
        header_layout = QGridLayout(header_group)
        self.title_label = QLabel("<h2>Caricamento dati partita...</h2>")
        header_layout.addWidget(self.title_label, 0, 0, 1, 4)
        main_layout.addWidget(header_group)
        
        self.tab_widget = QTabWidget(self)
        main_layout.addWidget(self.tab_widget)

        # --- Tab 1: Dati Generali ---
        self.tab_dati_generali = QWidget()
        form_layout_generali = QFormLayout(self.tab_dati_generali)
        # (Qui il codice per creare i campi di input del tab dati generali, come prima)
        self.numero_partita_spinbox = QSpinBox(); self.numero_partita_spinbox.setRange(1, 999999)
        form_layout_generali.addRow("Numero Partita (*):", self.numero_partita_spinbox)
        self.suffisso_partita_edit = QLineEdit(); self.suffisso_partita_edit.setPlaceholderText("Es. bis, A")
        form_layout_generali.addRow("Suffisso Partita (opz.):", self.suffisso_partita_edit)
        self.data_impianto_edit = QDateEdit(calendarPopup=True); self.data_impianto_edit.setDisplayFormat("yyyy-MM-dd")
        form_layout_generali.addRow("Data Impianto (*):", self.data_impianto_edit)
        self.data_chiusura_check = QCheckBox("Imposta data chiusura"); self.data_chiusura_edit = QDateEdit(calendarPopup=True); self.data_chiusura_edit.setDisplayFormat("yyyy-MM-dd"); self.data_chiusura_edit.setEnabled(False); self.data_chiusura_check.toggled.connect(self._toggle_data_chiusura)
        data_chiusura_layout = QHBoxLayout(); data_chiusura_layout.addWidget(self.data_chiusura_check); data_chiusura_layout.addWidget(self.data_chiusura_edit); form_layout_generali.addRow("Data Chiusura:", data_chiusura_layout)
        self.numero_provenienza_edit = QLineEdit(); self.numero_provenienza_edit.setPlaceholderText("Numero o testo di riferimento (opzionale)"); self.numero_provenienza_edit.setMaxLength(50)
        form_layout_generali.addRow("Numero Provenienza:", self.numero_provenienza_edit)
        self.tipo_combo = QComboBox(); self.tipo_combo.addItems(["principale", "secondaria"]); form_layout_generali.addRow("Tipo (*):", self.tipo_combo)
        self.stato_combo = QComboBox(); self.stato_combo.addItems(["attiva", "inattiva"]); form_layout_generali.addRow("Stato (*):", self.stato_combo)
        self.tab_widget.addTab(self.tab_dati_generali, "Dati Generali")

        # Tab 2: Possessori Associati ---
        self.tab_possessori = QWidget()
        # DEVI INIZIALIZZARE possessori_layout QUI
        possessori_layout = QVBoxLayout(self.tab_possessori) 
        self.possessori_table = QTableWidget()
        self.possessori_table.setColumnCount(5)
        self.possessori_table.setHorizontalHeaderLabels(["ID Rel.", "ID Poss.", "Nome Completo Possessore", "Titolo", "Quota"])
        self.possessori_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.possessori_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.possessori_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.possessori_table.setAlternatingRowColors(True)
        
        # Logica per l'espansione delle colonne
        header_possessori = self.possessori_table.horizontalHeader()
        header_possessori.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header_possessori.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header_possessori.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch) # Espande "Nome Completo"
        header_possessori.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header_possessori.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        possessori_layout.addWidget(self.possessori_table)

        # Pulsanti per la gestione dei possessori
        possessori_buttons_layout = QHBoxLayout()
        self.btn_aggiungi_possessore = QPushButton("Aggiungi Possessore...")
        self.btn_aggiungi_possessore.clicked.connect(self._aggiungi_possessore_a_partita)
        possessori_buttons_layout.addWidget(self.btn_aggiungi_possessore)

        self.btn_modifica_legame_possessore = QPushButton("Modifica Legame")
        self.btn_modifica_legame_possessore.clicked.connect(self._modifica_legame_possessore)
        self.btn_modifica_legame_possessore.setEnabled(False) 
        possessori_buttons_layout.addWidget(self.btn_modifica_legame_possessore)

        self.btn_rimuovi_possessore = QPushButton("Rimuovi Possessore")
        self.btn_rimuovi_possessore.clicked.connect(self._rimuovi_possessore_da_partita)
        self.btn_rimuovi_possessore.setEnabled(False) 
        possessori_buttons_layout.addWidget(self.btn_rimuovi_possessore)
        
        possessori_buttons_layout.addStretch() 
        possessori_layout.addLayout(possessori_buttons_layout) # Questa è la riga che causava l'errore

        # Collega il segnale itemSelectionChanged della tabella alla funzione che abilita/disabilita i pulsanti
        self.possessori_table.itemSelectionChanged.connect(self._aggiorna_stato_pulsanti_possessori)

        self.tab_widget.addTab(self.tab_possessori, "Possessori Associati")

        # --- Tab 3: Immobili Associati ---
        self.tab_immobili = QWidget()
        layout_immobili = QVBoxLayout(self.tab_immobili)

        self.immobili_table = ImmobiliTableWidget()
        self.immobili_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.immobili_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.immobili_table.itemSelectionChanged.connect(self._aggiorna_stato_pulsanti_immobili)
        layout_immobili.addWidget(self.immobili_table)

        immobili_buttons_layout = QHBoxLayout()
        self.btn_aggiungi_immobile = QPushButton("Aggiungi Immobile...")
        self.btn_aggiungi_immobile.clicked.connect(self._aggiungi_immobile_a_partita)
        immobili_buttons_layout.addWidget(self.btn_aggiungi_immobile)

        self.btn_modifica_immobile = QPushButton("Modifica Immobile...")
        self.btn_modifica_immobile.clicked.connect(self._modifica_immobile_associato)
        self.btn_modifica_immobile.setEnabled(False)
        immobili_buttons_layout.addWidget(self.btn_modifica_immobile)

        self.btn_rimuovi_immobile = QPushButton("Rimuovi Immobile")
        self.btn_rimuovi_immobile.clicked.connect(self._rimuovi_immobile_da_partita)
        self.btn_rimuovi_immobile.setEnabled(False)
        immobili_buttons_layout.addWidget(self.btn_rimuovi_immobile)
        immobili_buttons_layout.addStretch()
        layout_immobili.addLayout(immobili_buttons_layout)
        self.tab_widget.addTab(self.tab_immobili, "Immobili Associati")

        # --- Tab 4: Variazioni ---
        self.tab_variazioni = QWidget()
        layout_variazioni = QVBoxLayout(self.tab_variazioni)

        self.variazioni_table = QTableWidget()
        self.variazioni_table.setColumnCount(6)
        self.variazioni_table.setHorizontalHeaderLabels([
            "ID Var.", "Tipo", "Data Var.", "Partita Origine", "Partita Destinazione", "Contratto"
        ])
        self.variazioni_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.variazioni_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.variazioni_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.variazioni_table.horizontalHeader().setStretchLastSection(True)
        self.variazioni_table.setAlternatingRowColors(True)
        self.variazioni_table.itemSelectionChanged.connect(self._aggiorna_stato_pulsanti_variazioni)
        layout_variazioni.addWidget(self.variazioni_table)

        variazioni_buttons_layout = QHBoxLayout()
        self.btn_modifica_variazione = QPushButton("Modifica Variazione...")
        self.btn_modifica_variazione.clicked.connect(self._modifica_variazione_selezionata)
        self.btn_modifica_variazione.setEnabled(False)
        variazioni_buttons_layout.addWidget(self.btn_modifica_variazione)
        
        self.btn_elimina_variazione = QPushButton("Elimina Variazione")
        self.btn_elimina_variazione.clicked.connect(self._elimina_variazione_selezionata)
        self.btn_elimina_variazione.setEnabled(False)
        variazioni_buttons_layout.addWidget(self.btn_elimina_variazione)

        variazioni_buttons_layout.addStretch()
        layout_variazioni.addLayout(variazioni_buttons_layout)
        self.tab_widget.addTab(self.tab_variazioni, "Variazioni")

        # --- Tab 5: Documenti Allegati ---
        self.tab_documenti = QWidget()
        layout_documenti = QVBoxLayout(self.tab_documenti)

        self.documents_table = QTableWidget()
        self.documents_table.setColumnCount(6)
        self.documents_table.setHorizontalHeaderLabels([
            "ID Doc.", "Titolo", "Tipo Doc.", "Anno", "Rilevanza", "Percorso/Azione"
        ])
        self.documents_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.documents_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.documents_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.documents_table.horizontalHeader().setStretchLastSection(True)
        self.documents_table.setSortingEnabled(True)
        self.documents_table.itemSelectionChanged.connect(self._update_details_doc_buttons_state)
        
        self.documents_table.setAcceptDrops(True)
        self.documents_table.setDropIndicatorShown(True)
        self.documents_table.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.documents_table.dragEnterEvent = self.documents_table_dragEnterEvent
        self.documents_table.dragMoveEvent = self.documents_table_dragMoveEvent
        self.documents_table.dropEvent = self.documents_table_dropEvent
        
        layout_documenti.addWidget(self.documents_table)

        doc_buttons_layout = QHBoxLayout()
        self.btn_allega_nuovo = QPushButton(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileLinkIcon), "Allega Nuovo Documento...")
        self.btn_allega_nuovo.clicked.connect(self._allega_nuovo_documento_a_partita)
        doc_buttons_layout.addWidget(self.btn_allega_nuovo)

        self.btn_apri_doc_details_dialog = QPushButton(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton), "Apri Documento Selezionato")
        self.btn_apri_doc_details_dialog.clicked.connect(self._apri_documento_selezionato_from_details_dialog)
        self.btn_apri_doc_details_dialog.setEnabled(False)
        doc_buttons_layout.addWidget(self.btn_apri_doc_details_dialog)
        
        self.btn_scollega_doc = QPushButton(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon), "Scollega Documento")
        self.btn_scollega_doc.clicked.connect(self._scollega_documento_selezionato)
        self.btn_scollega_doc.setEnabled(False)
        doc_buttons_layout.addWidget(self.btn_scollega_doc)
        
        doc_buttons_layout.addStretch()
        layout_documenti.addLayout(doc_buttons_layout)
        
        self.tab_widget.addTab(self.tab_documenti, "Documenti Allegati")

        # --- Blocco Pulsanti Finale ---
        buttons_layout = QHBoxLayout()
        self.btn_archivia = QPushButton("Archivia Partita")
        self.btn_archivia.setObjectName("dangerButton")
        self.btn_archivia.setToolTip("Archivia questa partita (non viene eliminata, solo nascosta)")
        self.btn_archivia.clicked.connect(self._archivia_partita)
        self.btn_duplica_partita = QPushButton(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder), " Duplica questa Partita...")
        self.save_button = QPushButton("Salva Modifiche Dati Generali")
        self.close_dialog_button = QPushButton("Chiudi")
        self.btn_duplica_partita.clicked.connect(self._handle_duplica_partita)
        self.save_button.clicked.connect(self._save_changes)
        self.close_dialog_button.clicked.connect(self.accept)
        buttons_layout.addWidget(self.btn_archivia)
        buttons_layout.addWidget(self.btn_duplica_partita)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.close_dialog_button)
        main_layout.addLayout(buttons_layout)
        
        self.setLayout(main_layout)

    # --- Metodi per il Caricamento dei Dati (Centralizzato) ---
    def _toggle_data_chiusura(self, checked):
        """Abilita o disabilita il QDateEdit per la data di chiusura."""
        self.data_chiusura_edit.setEnabled(checked)
        if not checked:
            self.data_chiusura_edit.setDate(QDate()) # Imposta una data nulla

    def _load_all_partita_data(self):
        """Carica tutti i dati e POI popola l'intera UI."""
        self.partita_data_originale = self.db_manager.get_partita_details(self.partita_id)
        
        if not self.partita_data_originale:
            QMessageBox.critical(self, "Errore", f"Impossibile caricare i dati per la partita ID: {self.partita_id}.")
            QTimer.singleShot(0, self.reject)
            return

        # 1. Popola il titolo principale
        suffisso_db = self.partita_data_originale.get('suffisso_partita')
        suffisso_display = f" ({suffisso_db})" if suffisso_db and str(suffisso_db).strip() else ""
        titolo_text = f"<h2>Partita N.{self.partita_data_originale.get('numero_partita', 'N/D')}{suffisso_display} - {self.partita_data_originale.get('comune_nome', 'N/D')}</h2>"
        self.title_label.setText(titolo_text)
        
        # 2. Popola tutti i tab
        self._populate_dati_generali_tab()
        self._load_possessori_associati()
        self._load_immobili_associati()
        self._load_variazioni_associati()
        self._load_documenti_allegati()
        self.logger.info(f"ModificaPartitaDialog: Dati per partita ID {self.partita_id} caricati in tutti i tab.")


    def _populate_dati_generali_tab(self):
        """Popola i campi nel tab 'Dati Generali' con i dati della partita."""
        partita = self.partita_data_originale
        if not partita: return

        self.numero_partita_spinbox.setValue(partita.get('numero_partita', 0))
        self.suffisso_partita_edit.setText(partita.get('suffisso_partita', '') or '')

        tipo_idx = self.tipo_combo.findText(partita.get('tipo', ''), Qt.MatchFlag.MatchFixedString)
        if tipo_idx >= 0: self.tipo_combo.setCurrentIndex(tipo_idx)

        stato_idx = self.stato_combo.findText(partita.get('stato', ''), Qt.MatchFlag.MatchFixedString)
        if stato_idx >= 0: self.stato_combo.setCurrentIndex(stato_idx)

        self.data_impianto_edit.setDate(datetime_to_qdate(partita.get('data_impianto')))

        # Logica aggiornata per data_chiusura
        data_chiusura_db = partita.get('data_chiusura')
        if data_chiusura_db:
            self.data_chiusura_check.setChecked(True)
            self.data_chiusura_edit.setDate(datetime_to_qdate(data_chiusura_db))
        else:
            self.data_chiusura_check.setChecked(False)
            
        # Logica aggiornata per numero_provenienza
        num_prov_val = partita.get('numero_provenienza')
        self.numero_provenienza_edit.setText(str(num_prov_val) if num_prov_val is not None else "")

        self.logger.debug("Tab 'Dati Generali' popolato con la nuova logica.")


    def _load_possessori_associati(self):
        """Carica e popola la tabella dei possessori associati alla partita."""
        self.possessori_table.setRowCount(0)
        self.possessori_table.setSortingEnabled(False)
        self.possessori_table.clearSelection() # Pulisce la selezione
        self.logger.info(f"Caricamento possessori associati per partita ID: {self.partita_id}")

        try:
            possessori = self.db_manager.get_possessori_per_partita(self.partita_id)
            if possessori:
                self.possessori_table.setRowCount(len(possessori))
                for row_idx, poss_data in enumerate(possessori):
                    id_rel_val = poss_data.get('id_relazione_partita_possessore', '')
                    id_rel_item = QTableWidgetItem(str(id_rel_val))
                    id_rel_item.setData(Qt.ItemDataRole.UserRole, id_rel_val) # Salva l'ID relazione
                    self.possessori_table.setItem(row_idx, 0, id_rel_item)

                    self.possessori_table.setItem(row_idx, 1, QTableWidgetItem(str(poss_data.get('possessore_id', ''))))
                    self.possessori_table.setItem(row_idx, 2, QTableWidgetItem(poss_data.get('nome_completo_possessore', 'N/D')))
                    self.possessori_table.setItem(row_idx, 3, QTableWidgetItem(poss_data.get('titolo_possesso', 'N/D')))
                    self.possessori_table.setItem(row_idx, 4, QTableWidgetItem(poss_data.get('quota_possesso', 'N/D') or '')) # Gestisce None
                self.possessori_table.resizeColumnsToContents()
            else:
                self.logger.info(f"Nessun possessore trovato per la partita ID {self.partita_id}.")
                self.possessori_table.setRowCount(1)
                item = QTableWidgetItem("Nessun possessore associato a questa partita.")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.possessori_table.setItem(0, 0, item)
                self.possessori_table.setSpan(0, 0, 1, self.possessori_table.columnCount())
        except Exception as e:
            self.logger.error(f"Errore durante il popolamento della tabella possessori per partita ID {self.partita_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Popolamento Tabella", f"Si è verificato un errore durante la visualizzazione dei possessori associati:\n{e}")
        finally:
            self.possessori_table.setSortingEnabled(True)
            self._aggiorna_stato_pulsanti_possessori()
            self.logger.debug("Tab 'Possessori' popolato.")

    def _load_immobili_associati(self):
        """Carica e popola la tabella degli immobili associati alla partita."""
        self.immobili_table.setRowCount(0)
        self.immobili_table.setSortingEnabled(False)
        self.immobili_table.clearSelection() # Pulisce la selezione
        self.logger.info(f"Caricamento immobili associati per partita ID: {self.partita_id}")

        try:
            immobili = self.partita_data_originale.get('immobili', []) # Dati immobili sono già in partita_data_originale
            if immobili:
                self.immobili_table.setRowCount(len(immobili))
                for row_idx, imm in enumerate(immobili):
                    # La logica di ImmobiliTableWidget.populate_data è replicata qui per coerenza
                    # ma potresti anche passare i dati a immobili_table.populate_data() se è un widget riusabile
                    self.immobili_table.setItem(row_idx, 0, QTableWidgetItem(str(imm.get('id', ''))))
                    self.immobili_table.setItem(row_idx, 1, QTableWidgetItem(imm.get('natura', '')))
                    self.immobili_table.setItem(row_idx, 2, QTableWidgetItem(imm.get('classificazione', '')))
                    self.immobili_table.setItem(row_idx, 3, QTableWidgetItem(imm.get('consistenza', '')))
                    localita_text = ""
                    if 'localita_nome' in imm:
                        localita_text = imm['localita_nome']
                        if 'civico' in imm and imm['civico'] is not None:
                            localita_text += f", {imm['civico']}"
                        if 'localita_tipo' in imm:
                            localita_text += f" ({imm['localita_tipo']})"
                    self.immobili_table.setItem(row_idx, 4, QTableWidgetItem(localita_text))
                self.immobili_table.resizeColumnsToContents()
            else:
                self.logger.info(f"Nessun immobile trovato per la partita ID {self.partita_id}.")
                self.immobili_table.setRowCount(1)
                item = QTableWidgetItem("Nessun immobile associato a questa partita.")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.immobili_table.setItem(0, 0, item)
                self.immobili_table.setSpan(0, 0, 1, self.immobili_table.columnCount())
        except Exception as e:
            self.logger.error(f"Errore durante il popolamento della tabella immobili per partita ID {self.partita_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Popolamento Tabella", f"Si è verificato un errore durante la visualizzazione degli immobili associati:\n{e}")
        finally:
            self.immobili_table.setSortingEnabled(True)
            self._aggiorna_stato_pulsanti_immobili()
            self.logger.debug("Tab 'Immobili' popolato.")

    def _load_variazioni_associati(self):
        """Carica e popola la tabella delle variazioni associate alla partita."""
        self.variazioni_table.setRowCount(0)
        self.variazioni_table.setSortingEnabled(False)
        self.variazioni_table.clearSelection() # Pulisce la selezione
        self.logger.info(f"Caricamento variazioni associate per partita ID: {self.partita_id}")

        try:
            variazioni = self.partita_data_originale.get('variazioni', []) # Dati variazioni sono già in partita_data_originale
            if variazioni:
                self.variazioni_table.setRowCount(len(variazioni))
                for row_idx, var in enumerate(variazioni):
                    col = 0
                    self.variazioni_table.setItem(row_idx, col, QTableWidgetItem(str(var.get('id', '')))); col += 1
                    self.variazioni_table.setItem(row_idx, col, QTableWidgetItem(var.get('tipo', ''))); col += 1
                    self.variazioni_table.setItem(row_idx, col, QTableWidgetItem(str(var.get('data_variazione', '')))); col += 1

                    # Partita Origine
                    orig_text = ""
                    if var.get('partita_origine_id'):
                        num_orig = var.get('origine_numero_partita', 'N/D')
                        com_orig = var.get('origine_comune_nome', 'N/D')
                        orig_text = f"N.{num_orig} ({com_orig})"
                        if var.get('origine_suffisso_partita'): # Se hai il suffisso nella variazione
                            orig_text += f" ({var.get('origine_suffisso_partita')})"
                    else:
                        orig_text = "-"
                    self.variazioni_table.setItem(row_idx, col, QTableWidgetItem(orig_text)); col += 1

                    # Partita Destinazione
                    dest_text = ""
                    if var.get('partita_destinazione_id'):
                        num_dest = var.get('destinazione_numero_partita', 'N/D')
                        com_dest = var.get('destinazione_comune_nome', 'N/D')
                        dest_text = f"N.{num_dest} ({com_dest})"
                        if var.get('destinazione_suffisso_partita'): # Se hai il suffisso nella variazione
                            dest_text += f" ({var.get('destinazione_suffisso_partita')})"
                    else:
                        dest_text = "-"
                    self.variazioni_table.setItem(row_idx, col, QTableWidgetItem(dest_text)); col += 1

                    # Contratto
                    contratto_text = ""
                    if var.get('tipo_contratto'):
                        contratto_text = f"{var['tipo_contratto']} del {var.get('data_contratto', '')}"
                        if var.get('notaio'):
                            contratto_text += f" - {var['notaio']}"
                    self.variazioni_table.setItem(row_idx, col, QTableWidgetItem(contratto_text)); col += 1

                self.variazioni_table.resizeColumnsToContents()
            else:
                self.logger.info(f"Nessuna variazione trovata per la partita ID {self.partita_id}.")
                self.variazioni_table.setRowCount(1)
                item = QTableWidgetItem("Nessuna variazione associata a questa partita.")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.variazioni_table.setItem(0, 0, item)
                self.variazioni_table.setSpan(0, 0, 1, self.variazioni_table.columnCount())
        except Exception as e:
            self.logger.error(f"Errore durante il popolamento della tabella variazioni per partita ID {self.partita_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Popolamento Tabella", f"Si è verificato un errore durante la visualizzazione delle variazioni associate:\n{e}")
        finally:
            self.variazioni_table.setSortingEnabled(True)
            self._aggiorna_stato_pulsanti_variazioni()
            self.logger.debug("Tab 'Variazioni' popolato.")

    # In gui_widgets.py, nella classe ModificaPartitaDialog
# Sostituisci il metodo _load_documenti_allegati() con questa versione corretta:
    def _handle_duplica_partita(self):
        """Gestisce il click sul pulsante 'Duplica', apre il dialogo delle opzioni e avvia l'operazione."""
        self.logger.info(f"Richiesta duplicazione per la partita ID {self.partita_id}.")

        # Apri il dialogo delle opzioni
        options_dialog = DuplicaPartitaOptionsDialog(self)
        if options_dialog.exec() != QDialog.DialogCode.Accepted:
            self.logger.info("Duplicazione annullata dall'utente.")
            return
            
        options = options_dialog.get_options()
        nuovo_numero = options['nuovo_numero_partita']
        nuovo_suffisso = options['nuovo_suffisso']
        
        # Validazione: verifica che la nuova partita non esista già
        # Dobbiamo usare il comune_id della partita corrente
        comune_id_corrente = self.partita_data_originale.get('comune_id')
        if comune_id_corrente:
            existing = self.db_manager.search_partite(
                comune_id=comune_id_corrente,
                numero_partita=nuovo_numero,
                suffisso_partita=nuovo_suffisso
            )
            if existing:
                QMessageBox.warning(self, "Partita Esistente", f"Esiste già una partita con numero {nuovo_numero} e suffisso '{nuovo_suffisso or ''}' in questo comune.")
                return

        # Esegui la duplicazione tramite il DB Manager
        try:
            success = self.db_manager.duplicate_partita(
                partita_id_originale=self.partita_id,
                **options # Passa le opzioni come argomenti keyword
            )
            if success:
                QMessageBox.information(self, "Successo", "Partita duplicata con successo.")
                # Opzionale: potremmo voler aggiornare qualche vista qui
            # L'eccezione verrà sollevata dal metodo in caso di fallimento
        except DBMError as e:
            self.logger.error(f"Errore durante la duplicazione della partita ID {self.partita_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Duplicazione", f"Impossibile duplicare la partita:\n{e}")

    def _load_documenti_allegati(self):
        """Carica e popola la tabella dei documenti allegati alla partita."""
        self.documents_table.setRowCount(0)
        self.documents_table.setSortingEnabled(False)
        self.documents_table.clearSelection() 
        self.logger.info(f"Caricamento documenti per partita ID {self.partita_id}.")

        try:
            # CORREZIONE: Usa self.partita_id invece di self.partita['id']
            documenti = self.db_manager.get_documenti_per_partita(self.partita_id)
            
            if documenti:
                self.documents_table.setRowCount(len(documenti))
                for row, doc in enumerate(documenti):
                    # --- INIZIO CORREZIONE: Salvataggio dati robusto ---
            # Salviamo un dizionario con gli ID di relazione nell'UserRole
                    rel_data = {
                        'doc_id': doc.get('rel_documento_id'),
                        'partita_id': doc.get('rel_partita_id')
                    }

                    # L'item nella prima colonna conterrà tutti i dati per la riga
                    item_doc_id = QTableWidgetItem(str(doc.get('documento_id', '')))
                    item_doc_id.setData(Qt.ItemDataRole.UserRole, rel_data)
                    self.documents_table.setItem(row, 0, item_doc_id)
            # --- FINE CORREZIONE ---
                    # Salviamo l'ID del documento storico e l'ID della partita per la rimozione del legame
                    item_doc_id.setData(Qt.ItemDataRole.UserRole + 1, doc.get("dp_documento_id")) # ID del documento storico nella relazione
                    item_doc_id.setData(Qt.ItemDataRole.UserRole + 2, doc.get("dp_partita_id")) # ID della partita nella relazione (che è self.partita_id)
                    
                    
                    self.documents_table.setItem(row, 1, QTableWidgetItem(doc.get("titolo") or ''))
                    self.documents_table.setItem(row, 2, QTableWidgetItem(doc.get("tipo_documento") or ''))
                    self.documents_table.setItem(row, 3, QTableWidgetItem(str(doc.get("anno", '')) or ''))
                    self.documents_table.setItem(row, 4, QTableWidgetItem(doc.get("rilevanza") or ''))
                    
                    # CORREZIONE: Assicurati che il percorso sia salvato correttamente nell'UserRole
                    percorso_file_full = doc.get("percorso_file") or ''
                    path_item = QTableWidgetItem(os.path.basename(percorso_file_full) if percorso_file_full else "N/D")
                    path_item.setData(Qt.ItemDataRole.UserRole, percorso_file_full) # Salva percorso completo per l'apertura
                    self.documents_table.setItem(row, 5, path_item)
                
                self.documents_table.resizeColumnsToContents()
            else:
                self.logger.info(f"Nessun documento trovato per la partita ID {self.partita_id}.")
                self.documents_table.setRowCount(1)
                no_docs_item = QTableWidgetItem("Nessun documento allegato a questa partita.")
                no_docs_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.documents_table.setItem(0, 0, no_docs_item)
                self.documents_table.setSpan(0, 0, 1, self.documents_table.columnCount())

        except Exception as e:
            self.logger.error(f"Errore caricamento documenti per partita ID {self.partita_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Caricamento Documenti", f"Si è verificato un errore durante il caricamento dei documenti:\n{e}")
            # Mostra messaggio di errore nella tabella
            self.documents_table.setRowCount(1)
            error_item = QTableWidgetItem(f"Errore nel caricamento dei documenti: {e}")
            error_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.documents_table.setItem(0, 0, error_item)
            self.documents_table.setSpan(0, 0, 1, self.documents_table.columnCount())
        finally:
            self.documents_table.setSortingEnabled(True)
            self._update_document_tab_title() 
            self._update_details_doc_buttons_state() 
            self.logger.debug("Tab 'Documenti' popolato.")


    # --- Metodi per la Gestione dei Pulsanti e Selezioni ---

    def _aggiorna_stato_pulsanti_possessori(self):
        """Abilita/disabilita i pulsanti per i possessori in base alla selezione."""
        has_selection = bool(self.possessori_table.selectedItems())
        self.btn_modifica_legame_possessore.setEnabled(has_selection)
        self.btn_rimuovi_possessore.setEnabled(has_selection)

    def _aggiorna_stato_pulsanti_immobili(self):
        """Abilita/disabilita i pulsanti per gli immobili in base alla selezione."""
        has_selection = bool(self.immobili_table.selectedItems())
        self.btn_modifica_immobile.setEnabled(has_selection)
        self.btn_rimuovi_immobile.setEnabled(has_selection)

    def _aggiorna_stato_pulsanti_variazioni(self):
        """Abilita/disabilita i pulsanti per le variazioni in base alla selezione."""
        has_selection = bool(self.variazioni_table.selectedItems())
        self.btn_modifica_variazione.setEnabled(has_selection)
        self.btn_elimina_variazione.setEnabled(has_selection)

    def _update_details_doc_buttons_state(self):
        """Abilita/disabilita i pulsanti per i documenti in base alla selezione."""
        has_selection = bool(self.documents_table.selectedItems())
        self.btn_apri_doc_details_dialog.setEnabled(has_selection)
        self.btn_scollega_doc.setEnabled(has_selection)

    # --- Metodi per Azioni sui Dati ---

    # -- Possessori --
    def _aggiungi_possessore_a_partita(self):
        self.logger.debug(f"Richiesta aggiunta possessore per partita ID {self.partita_id}")
        comune_id_partita = self.partita_data_originale.get('comune_id')
        if comune_id_partita is None:
            QMessageBox.warning(self, "Errore", "Comune della partita non determinato. Impossibile aggiungere possessore.")
            return

        possessore_dialog = PossessoreSelectionDialog(self.db_manager, comune_id_partita, self)
        selected_possessore_id = None
        selected_possessore_nome = None

        if possessore_dialog.exec() == QDialog.DialogCode.Accepted:
            if hasattr(possessore_dialog, 'selected_possessore') and possessore_dialog.selected_possessore:
                selected_possessore_id = possessore_dialog.selected_possessore.get('id')
                selected_possessore_nome = possessore_dialog.selected_possessore.get('nome_completo')
        if not selected_possessore_id or not selected_possessore_nome:
            self.logger.info("Nessun possessore selezionato o creato.")
            return

        self.logger.info(f"Possessore selezionato/creato: ID {selected_possessore_id}, Nome: {selected_possessore_nome}")
        tipo_partita_corrente = self.partita_data_originale.get('tipo', 'principale')
        from dialogs_entity import DettagliLegamePossessoreDialog
        dettagli_legame = DettagliLegamePossessoreDialog.get_details_for_new_legame(selected_possessore_nome, tipo_partita_corrente, self)

        if not dettagli_legame:
            self.logger.info("Inserimento dettagli legame annullato.")
            return

        try:
            success = self.db_manager.aggiungi_possessore_a_partita(
                partita_id=self.partita_id,
                possessore_id=selected_possessore_id,
                tipo_partita_rel=tipo_partita_corrente,
                titolo=dettagli_legame["titolo"],
                quota=dettagli_legame["quota"]
            )
            if success:
                self.logger.info(f"Possessore ID {selected_possessore_id} aggiunto con successo alla partita ID {self.partita_id}")
                QMessageBox.information(self, "Successo", f"Possessore '{selected_possessore_nome}' aggiunto alla partita.")
                self._load_possessori_associati()
            else:
                self.logger.error("aggiungi_possessore_a_partita ha restituito False.")
                QMessageBox.critical(self, "Errore", "Impossibile aggiungere il possessore alla partita.")
        except (DBUniqueConstraintError, DBDataError, DBMError) as e:
            self.logger.error(f"Errore DB aggiungendo possessore {selected_possessore_id} a partita {self.partita_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Database", f"Errore durante l'aggiunta del possessore alla partita:\n{e.message if hasattr(e, 'message') else str(e)}")
        except Exception as e:
            self.logger.critical(f"Errore imprevisto aggiungendo possessore {selected_possessore_id} a partita {self.partita_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore: {e}")

    def _modifica_legame_possessore(self):
        from dialogs_entity import DettagliLegamePossessoreDialog

        selected_items = self.possessori_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un possessore dalla tabella per modificarne il legame.")
            return

        current_row = selected_items[0].row()
        id_relazione_pp = self.possessori_table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)
        if id_relazione_pp is None:
            QMessageBox.critical(self, "Errore Interno", "ID relazione non trovato per il possessore selezionato.")
            return

        nome_possessore_attuale = self.possessori_table.item(current_row, 2).text()
        titolo_attuale = self.possessori_table.item(current_row, 3).text()
        quota_attuale_item = self.possessori_table.item(current_row, 4)
        quota_attuale = quota_attuale_item.text() if quota_attuale_item and quota_attuale_item.text() != 'N/D' else None

        self.logger.debug(f"Richiesta modifica legame per relazione ID {id_relazione_pp} (Possessore: {nome_possessore_attuale})")
        tipo_partita_corrente = self.partita_data_originale.get('tipo', 'principale')
        nuovi_dettagli_legame = DettagliLegamePossessoreDialog.get_details_for_edit_legame(
            nome_possessore_attuale, tipo_partita_corrente, titolo_attuale, quota_attuale, self
        )

        if not nuovi_dettagli_legame:
            self.logger.info("Modifica dettagli legame annullata.")
            return

        try:
            success = self.db_manager.aggiorna_legame_partita_possessore(
                partita_possessore_id=id_relazione_pp,
                titolo=nuovi_dettagli_legame["titolo"],
                quota=nuovi_dettagli_legame["quota"]
            )
            if success:
                self.logger.info(f"Legame ID {id_relazione_pp} aggiornato con successo.")
                QMessageBox.information(self, "Successo", "Dettagli del legame possessore aggiornati.")
                self._load_possessori_associati()
            else:
                self.logger.error("aggiorna_legame_partita_possessore ha restituito False.")
                QMessageBox.critical(self, "Errore", "Impossibile aggiornare il legame del possessore.")
        except (DBMError, DBDataError) as dbe_legame:
            self.logger.error(f"Errore DB aggiornando legame {id_relazione_pp}: {dbe_legame}", exc_info=True)
            QMessageBox.critical(self, "Errore Database", f"Errore durante l'aggiornamento del legame:\n{dbe_legame.message if hasattr(dbe_legame, 'message') else str(dbe_legame)}")
        except Exception as e_legame:
            self.logger.critical(f"Errore imprevisto aggiornando legame {id_relazione_pp}: {e_legame}", exc_info=True)
            QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore: {e_legame}")

    def _rimuovi_possessore_da_partita(self):
        selected_items = self.possessori_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un legame possessore dalla tabella da rimuovere.")
            return

        id_relazione_pp = selected_items[0].data(Qt.ItemDataRole.UserRole)
        nome_possessore = self.possessori_table.item(selected_items[0].row(), 2).text()

        if id_relazione_pp is None:
            QMessageBox.critical(self, "Errore Interno", "ID relazione non trovato per il possessore selezionato.")
            return

        reply = QMessageBox.question(self, "Conferma Rimozione Legame",
                                     f"Sei sicuro di voler rimuovere il legame con il possessore '{nome_possessore}' (ID Relazione: {id_relazione_pp}) da questa partita?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.logger.debug(f"Richiesta rimozione legame ID {id_relazione_pp}")
            try:
                success = self.db_manager.rimuovi_possessore_da_partita(id_relazione_pp)

                if success:
                    self.logger.info(f"Legame ID {id_relazione_pp} rimosso con successo.")
                    QMessageBox.information(self, "Successo", "Legame con il possessore rimosso dalla partita.")
                    self._load_possessori_associati()
                else:
                    self.logger.error("rimuovi_possessore_da_partita ha restituito False.")
                    QMessageBox.critical(self, "Errore", "Impossibile rimuovere il legame del possessore.")
            except DBNotFoundError as nfe_rel:
                self.logger.warning(f"Tentativo di rimuovere legame ID {id_relazione_pp} non trovato: {nfe_rel}")
                QMessageBox.warning(self, "Operazione Fallita", str(nfe_rel.message))
                self._load_possessori_associati()
            except (DBMError, DBDataError) as dbe_rel:
                self.logger.error(f"Errore DB rimuovendo legame {id_relazione_pp}: {dbe_rel}", exc_info=True)
                QMessageBox.critical(self, "Errore Database", f"Errore durante la rimozione del legame:\n{dbe_rel.message if hasattr(dbe_rel, 'message') else str(dbe_rel)}")
            except Exception as e_rel:
                self.logger.critical(f"Errore imprevisto rimuovendo legame {id_relazione_pp}: {e_rel}", exc_info=True)
                QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore: {e_rel}")

    # -- Immobili --
    def _aggiungi_immobile_a_partita(self):
        self.logger.debug(f"Richiesta aggiunta immobile per partita ID {self.partita_id}")
        comune_id_partita = self.partita_data_originale.get('comune_id')
        if comune_id_partita is None:
            QMessageBox.warning(self, "Errore", "Comune della partita non determinato. Impossibile aggiungere immobile.")
            return

        dialog = ImmobileDialog(self.db_manager, comune_id_partita, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.immobile_data:
            immobile_data = dialog.immobile_data
            try:
                # La procedura SQL inserisci_immobile in db_manager deve essere aggiornata
                # per accettare tutti i campi dall'immobile_data
                immobile_id = self.db_manager.inserisci_immobile(
                    partita_id=self.partita_id,
                    natura=immobile_data['natura'],
                    localita_id=immobile_data['localita_id'],
                    classificazione=immobile_data['classificazione'],
                    consistenza=immobile_data['consistenza'],
                    numero_piani=immobile_data['numero_piani'],
                    numero_vani=immobile_data['numero_vani']
                )
                if immobile_id:
                    QMessageBox.information(self, "Successo", f"Immobile '{immobile_data['natura']}' aggiunto con ID: {immobile_id}.")
                    self._load_immobili_associati() # Ricarica la tabella immobili
                else:
                    self.logger.error("inserisci_immobile ha restituito None.")
                    QMessageBox.critical(self, "Errore", "Impossibile aggiungere l'immobile.")
            except (DBDataError, DBMError) as e:
                self.logger.error(f"Errore DB aggiungendo immobile: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Database", f"Errore durante l'aggiunta dell'immobile:\n{e.message if hasattr(e, 'message') else str(e)}")
            except Exception as e:
                self.logger.critical(f"Errore imprevisto aggiungendo immobile: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore: {e}")

    def _modifica_immobile_associato(self):
        selected_items = self.immobili_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un immobile dalla tabella per modificarlo.")
            return

        row = self.immobili_table.currentRow()
        immobile_id = int(self.immobili_table.item(row, 0).text())
        
        # Recupera i dettagli attuali dell'immobile dal DB per pre-popolare il dialogo di modifica
        immobile_data = self.db_manager.get_immobile_details(immobile_id) # Questo metodo deve essere in db_manager
        if not immobile_data:
            QMessageBox.critical(self, "Errore", "Impossibile recuperare i dettagli dell'immobile per la modifica.")
            return

        # Apri un dialogo di modifica specifico per l'immobile, simile a ImmobileDialog ma per la modifica
        # Dobbiamo creare una classe ModificaImmobileDialog, oppure riadattare ImmobileDialog con un flag 'modalità_modifica'
        
        # Per semplicità, qui useremo una versione adattata di ImmobileDialog o un nuovo dialogo.
        # Creiamo un nuovo dialogo o adattiamo quello esistente (che forse non è l'ideale).
        
        # Idealmente, avresti un ModificaImmobileDialog(db_manager, immobile_id, comune_id_partita, parent)
        # Per ora, si assume che sia un dialogo che possa essere pre-popolato e salvare.
        
        # Se non esiste una ModificaImmobileDialog, questo non funzionerà.
        # Per semplicità, ipotizziamo una classe ad-hoc o un'estensione.
        # Assicurati che sia importata o creata
        dialog = ModificaImmobileDialog(self.db_manager, immobile_id, self.partita_id, self) # Passa immobile_id, partita_id
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            QMessageBox.information(self, "Successo", "Immobile modificato con successo.")
            self._load_immobili_associati() # Ricarica la tabella immobili
        else:
            self.logger.info("Modifica immobile annullata.")

    def _rimuovi_immobile_da_partita(self):
        selected_items = self.immobili_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un immobile dalla tabella per rimuoverlo.")
            return

        row = self.immobili_table.currentRow()
        immobile_id = int(self.immobili_table.item(row, 0).text())
        
        reply = QMessageBox.question(self, "Conferma Rimozione",
                                     f"Sei sicuro di voler rimuovere l'immobile ID {immobile_id} da questa partita?\n"
                                     "Questa azione non cancella l'immobile dal database, ma lo scollega dalla partita attuale, impostando il suo partita_id a NULL.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Il metodo delete_immobile in db_manager deve essere aggiornato
                # per supportare la rimozione/scollegamento senza cancellare
                # o potresti chiamare una procedura SQL specifica per scollegare.
                # Per ora, la tua procedura delete_immobile probabilemente CANCELLA.
                # Quindi, il comportamento è distruttivo.
                # Dobbiamo chiarire la semantica di "rimuovi immobile da partita":
                # 1. Cancellare l'immobile del tutto (current delete_immobile)?
                # 2. Scollegarlo dalla partita (partita_id a NULL)?
                # 3. Trasferirlo a un'altra partita (usare _esegui_trasferimento_immobile)?

                # Se l'intento è impostare partita_id a NULL (scollegare), serve un nuovo metodo in DBManager.
                # Es. db_manager.scollega_immobile_da_partita(immobile_id)
                # Per ora, usiamo l'esistente delete_immobile con un avviso, ma è probabile che non sia il comportamento desiderato.
                success = self.db_manager.delete_immobile(immobile_id) # ATTENZIONE: Questo prob. CANCELLA FISICAMENTE!

                if success:
                    QMessageBox.information(self, "Successo", f"Immobile ID {immobile_id} rimosso/cancellato dalla partita.")
                    self._load_immobili_associati()
                else:
                    self.logger.error("delete_immobile ha restituito False.")
                    QMessageBox.critical(self, "Errore", "Impossibile rimuovere/cancellare l'immobile.")
            except (DBMError, DBDataError) as e:
                self.logger.error(f"Errore DB rimuovendo immobile: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Database", f"Errore durante la rimozione dell'immobile:\n{e.message if hasattr(e, 'message') else str(e)}")
            except Exception as e:
                self.logger.critical(f"Errore imprevisto rimuovendo immobile: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore: {e}")

    # -- Variazioni --
    def _modifica_variazione_selezionata(self):
        selected_items = self.variazioni_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona una variazione dalla tabella per modificarla.")
            return

        row = self.variazioni_table.currentRow()
        # --- INIZIO MODIFICA ---
        # Controlla se la riga selezionata è una riga di placeholder
        if self.variazioni_table.rowCount() == 1 and self.variazioni_table.item(0, 0) and "Nessuna variazione" in self.variazioni_table.item(0, 0).text():
            QMessageBox.warning(self, "Nessuna Variazione", "Non ci sono variazioni valide selezionate per la modifica.")
            return
        # --- FINE MODIFICA ---

        variazione_id = int(self.variazioni_table.item(row, 0).text())

        # Apri un dialogo per modificare la variazione, simile a InserimentoVariazione (se lo hai)
        # Dobbiamo creare una classe ModificaVariazioneDialog
        from gui_widgets import ModificaVariazioneDialog # Assicurati che sia importata o creata
        dialog = ModificaVariazioneDialog(self.db_manager, variazione_id, self.partita_id, self) # Passa variazione_id, partita_id
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            QMessageBox.information(self, "Successo", "Variazione modificata con successo.")
            self._load_variazioni_associati() # Ricarica la tabella
        else:
            self.logger.info("Modifica variazione annullata.")

    def _elimina_variazione_selezionata(self):
        selected_items = self.variazioni_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona una variazione dalla tabella per eliminarla.")
            return

        row = self.variazioni_table.currentRow()
        variazione_id = int(self.variazioni_table.item(row, 0).text())
        
        reply = QMessageBox.question(self, "Conferma Eliminazione",
                                     f"Sei sicuro di voler eliminare la variazione ID {variazione_id}?\n"
                                     "Questa azione potrebbe avere effetti sulle partite collegate (es. riattivare la partita origine se chiusa).",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Il metodo delete_variazione in db_manager ha flag force e restore_partita
                success = self.db_manager.delete_variazione(variazione_id, force=True, restore_partita=False) # Decidi la politica
                
                if success:
                    QMessageBox.information(self, "Successo", f"Variazione ID {variazione_id} eliminata.")
                    # Dopo aver eliminato una variazione, è fondamentale ricaricare i dati di tutte le partite coinvolte
                    # (origine e destinazione) per riflettere eventuali cambiamenti di stato.
                    # Per ora, ricarichiamo solo la lista delle variazioni per la partita corrente.
                    self._load_variazioni_associati() 
                    # Potrebbe essere necessario ricaricare anche la partita_data_originale
                    # e le partite del comune genitore.
                else:
                    self.logger.error("delete_variazione ha restituito False.")
                    QMessageBox.critical(self, "Errore", "Impossibile eliminare la variazione.")
            except (DBMError, DBDataError) as e:
                self.logger.error(f"Errore DB eliminando variazione: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Database", f"Errore durante l'eliminazione della variazione:\n{e.message if hasattr(e, 'message') else str(e)}")
            except Exception as e:
                self.logger.critical(f"Errore imprevisto eliminando variazione: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore: {e}")

    # -- Documenti --
    # Questi metodi sono già definiti correttamente e riutilizzano DocumentViewerDialog.
    # Non è necessario riscriverli qui, ma assicurati che siano presenti nel codice finale.
    # documents_table_dragEnterEvent, documents_table_dragMoveEvent, documents_table_dropEvent,
    # _handle_dropped_file, _allega_nuovo_documento_a_partita, _apri_documento_selezionato_from_details_dialog,
    # _scollega_documento_selezionato.
    # --- NUOVI METODI PER LA GESTIONE DEL DRAG-AND-DROP ---

    def documents_table_dragEnterEvent(self, event):
        """Accetta solo eventi di drag che contengono URL (file)."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def documents_table_dragMoveEvent(self, event):
        """Mantiene l'accettazione dell'azione se ci sono URL."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def documents_table_dropEvent(self, event):
        """Elabora i file rilasciati sulla tabella."""
        self.logger.info("Drop event rilevato sulla tabella documenti.")
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                self.logger.info(f"File rilasciato: {file_path}")
                # Qui chiamiamo la stessa logica di allegazione usata dal pulsante "Allega Nuovo Documento..."
                # che a sua volta apre AggiungiDocumentoDialog.
                # Però, dobbiamo passare il file_path al dialogo in modo che sia pre-selezionato.
                self._handle_dropped_file(file_path)
            event.acceptProposedAction()
        else:
            event.ignore()

    def _handle_dropped_file(self, file_path: str):
        """Gestisce un singolo file rilasciato, aprendo il dialogo di allegazione."""
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "File Non Trovato", f"Il file rilasciato non esiste: {file_path}")
            self.logger.warning(f"File rilasciato non trovato: {file_path}")
            return
        
        if not os.path.isfile(file_path):
            QMessageBox.warning(self, "Non un File", f"L'elemento rilasciato non è un file valido: {file_path}")
            self.logger.warning(f"Elemento rilasciato non è un file: {file_path}")
            return

        # Filtra i tipi di file accettati, se necessario
        allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension not in allowed_extensions:
            QMessageBox.warning(self, "Formato Non Supportato", f"Il formato del file '{file_extension}' non è supportato. Sono accettati: {', '.join(allowed_extensions)}.")
            self.logger.warning(f"Formato file non supportato per il drop: {file_path}")
            return
        
        # Apri il dialogo AggiungiDocumentoDialog e pre-popola il campo file
        dialog = AggiungiDocumentoDialog(self.db_manager, self.partita_id, self)
        
        # Imposta il percorso del file nel dialogo appena aperto
        # Questo richiede una modifica in AggiungiDocumentoDialog per avere un metodo set_initial_file_path
        dialog.set_initial_file_path(file_path)

        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.document_data:
            doc_info = dialog.document_data
            percorso_originale = doc_info["percorso_file_originale"] # Ora sarà file_path pre-selezionato
            
            # ... (la tua logica esistente di copia file e salvataggio nel DB da _allega_nuovo_documento_a_partita) ...
            allegati_dir = os.path.join(".", "allegati_catasto", f"partita_{self.partita_id}")
            os.makedirs(allegati_dir, exist_ok=True)
            
            nome_file_originale = os.path.basename(percorso_originale)
            nome_file_dest = nome_file_originale 
            percorso_destinazione_completo = os.path.join(allegati_dir, nome_file_dest)
            
            try:
                import shutil
                shutil.copy2(percorso_originale, percorso_destinazione_completo)
                self.logger.info(f"File copiato da '{percorso_originale}' a '{percorso_destinazione_completo}'")

                percorso_file_db = percorso_destinazione_completo

                doc_id = self.db_manager.aggiungi_documento_storico(
                    titolo=doc_info["titolo"],
                    tipo_documento=doc_info["tipo_documento"],
                    percorso_file=percorso_file_db,
                    descrizione=doc_info["descrizione"],
                    anno=doc_info["anno"],
                    periodo_id=doc_info["periodo_id"],
                    metadati_json=doc_info["metadati_json"]
                )
                if doc_id:
                    success_link = self.db_manager.collega_documento_a_partita(
                        doc_id, self.partita_id, doc_info["rilevanza"], doc_info["note_legame"]
                    )
                    if success_link:
                        QMessageBox.information(self, "Successo", "Documento allegato e collegato con successo.")
                        self._load_documenti_allegati() # Aggiorna la tabella
                    else:
                        QMessageBox.warning(self, "Attenzione", "Documento salvato ma fallito il collegamento alla partita.")
                else:
                    QMessageBox.critical(self, "Errore", "Impossibile salvare le informazioni del documento nel database.")
                    if os.path.exists(percorso_destinazione_completo): os.remove(percorso_destinazione_completo)

            except FileNotFoundError:
                QMessageBox.critical(self, "Errore File", f"File sorgente non trovato: {percorso_originale}")
            except PermissionError:
                QMessageBox.critical(self, "Errore Permessi", f"Permessi non sufficienti per copiare il file in '{allegati_dir}'.")
            except DBMError as e_db:
                QMessageBox.critical(self, "Errore Database", f"Errore durante il salvataggio: {e_db}")
                if os.path.exists(percorso_destinazione_completo): os.remove(percorso_destinazione_completo)
            except Exception as e:
                QMessageBox.critical(self, "Errore Imprevisto", f"Errore durante l'allegazione del documento: {e}")
                if os.path.exists(percorso_destinazione_completo): os.remove(percorso_destinazione_completo)
                self.logger.error(f"Errore allegando documento: {e}", exc_info=True)
        else:
            self.logger.info("Aggiunta documento tramite drag-and-drop annullata dall'utente (dialogo chiuso).")

    # Modifica _allega_nuovo_documento_a_partita per riutilizzare la logica di _handle_dropped_file
    def _allega_nuovo_documento_a_partita(self):
        """Gestisce l'allegazione di un nuovo documento tramite il pulsante Sfoglia."""
        # Apri il dialogo file, come faceva prima
        filePath, _ = QFileDialog.getOpenFileName(self, "Seleziona Documento da Allegare", "",
                                                  "Documenti (*.pdf *.jpg *.jpeg *.png);;File PDF (*.pdf);;Immagini JPG (*.jpg *.jpeg);;Immagini PNG (*.png);;Tutti i file (*)")
        if filePath:
            # Reutilizza la logica di gestione del file, che ora include il dialogo
            self._handle_dropped_file(filePath)
        else:
            self.logger.info("Selezione file annullata dall'utente per l'allegazione.")
    def _apri_documento_selezionato_from_details_dialog(self):
        """
        Apre un documento selezionato dalla tabella dei documenti allegati
        usando il visualizzatore predefinito del sistema operativo.
        """
        selected_items = self.documents_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un documento dalla lista per aprirlo.")
            return
        
        row = self.documents_table.currentRow()
        # La colonna con il percorso del file è la 6a (indice 5)
        percorso_file_item = self.documents_table.item(row, 5) 
        
        if percorso_file_item:
            # Recupera il percorso completo salvato nell'UserRole
            percorso_file_completo = percorso_file_item.data(Qt.ItemDataRole.UserRole)
            
            if percorso_file_completo and os.path.exists(percorso_file_completo):
                from PyQt6.QtGui import QDesktopServices
                from PyQt6.QtCore import QUrl
                
                self.logger.info(f"Tentativo di aprire il documento: {percorso_file_completo}")
                success = QDesktopServices.openUrl(QUrl.fromLocalFile(percorso_file_completo))
                
                if not success:
                    QMessageBox.warning(self, "Errore Apertura", 
                                        f"Impossibile aprire il file:\n{percorso_file_completo}\n"
                                        "Verificare che sia installata un'applicazione associata o che i permessi siano corretti.")
            else:
                QMessageBox.warning(self, "File Non Trovato", 
                                    f"Il file specificato non è stato trovato al percorso:\n{percorso_file_completo}\n"
                                    "Il file potrebbe essere stato spostato o eliminato.")
        else:
            QMessageBox.warning(self, "Percorso Mancante", 
                                "Informazioni sul percorso del file non disponibili per il documento selezionato.")


    # In gui_widgets.py, all'interno della classe ModificaPartitaDialog

    def _scollega_documento_selezionato(self):
        """
        Scollega un documento dalla partita corrente rimuovendo il record
        dalla tabella di associazione 'documento_partita'.
        """
        selected_items = self.documents_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un documento dalla lista per scollegarlo.")
            return

        row = self.documents_table.currentRow()
        
        # Recupera gli ID salvati nei dati dell'item
        id_doc_item = self.documents_table.item(row, 0)
        titolo_doc = self.documents_table.item(row, 1).text() if self.documents_table.item(row, 1) else "Sconosciuto"

        if not id_doc_item:
            QMessageBox.critical(self, "Errore Interno", "Impossibile recuperare i dati del documento selezionato.")
            return
        # --- INIZIO CORREZIONE: Recupero dati robusto ---
        rel_data = id_doc_item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(rel_data, dict) or not rel_data.get('doc_id') or not rel_data.get('partita_id'):
            self.logger.error(f"Dati di relazione mancanti o corrotti per la riga {row}: {rel_data}")
            QMessageBox.critical(self, "Errore Dati", "Informazioni sulla relazione documento-partita non trovate.")
            return

        documento_id_da_scollegare = rel_data['doc_id']
        partita_id_da_cui_scollegare = rel_data['partita_id']
        # --- FINE CORREZIONE --
        

        if not documento_id_da_scollegare or not partita_id_da_cui_scollegare:
            self.logger.error(f"Dati di relazione mancanti per la riga {row} (DocID: {documento_id_da_scollegare}, PartitaID: {partita_id_da_cui_scollegare})")
            QMessageBox.critical(self, "Errore Dati", "Informazioni sulla relazione documento-partita non trovate. Impossibile procedere.")
            return

        reply = QMessageBox.question(self, "Conferma Scollegamento",
                                     f"Sei sicuro di voler scollegare il documento '{titolo_doc}' (ID: {documento_id_da_scollegare}) "
                                     f"dalla partita corrente (ID: {partita_id_da_cui_scollegare})?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.logger.info(f"Tentativo di scollegare doc ID {documento_id_da_scollegare} da partita ID {partita_id_da_cui_scollegare}")
                
                # Chiama il metodo del DB Manager che esegue la DELETE sulla tabella di collegamento
                success = self.db_manager.scollega_documento_da_partita(
                    documento_id=documento_id_da_scollegare,
                    partita_id=partita_id_da_cui_scollegare
                )

                if success:
                    QMessageBox.information(self, "Successo", "Documento scollegato con successo dalla partita.")
                    self._load_documenti_allegati()  # Ricarica la lista dei documenti per aggiornare la UI
                # else: scollega_documento_da_partita solleverà un'eccezione in caso di fallimento
            except DBNotFoundError as nfe:
                self.logger.warning(f"Tentativo di scollegare un legame non trovato: {nfe}")
                QMessageBox.warning(self, "Operazione Fallita", str(nfe))
            except DBMError as e_db:
                self.logger.error(f"Errore DB durante lo scollegamento del documento: {e_db}", exc_info=True)
                QMessageBox.critical(self, "Errore Database", f"Impossibile scollegare il documento: {e_db}")
            except Exception as e:
                self.logger.critical(f"Errore imprevisto durante lo scollegamento del documento: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore di sistema: {e}")
    def _update_document_tab_title(self):
        """Aggiorna il titolo del tab dei documenti con il conteggio corrente."""
        try:
            # Assicurati che self.documents_table esista prima di contarne le righe
            if hasattr(self, 'documents_table'):
                count = self.documents_table.rowCount()
                
                # Se la tabella ha solo una riga placeholder "Nessun documento...", il conteggio è 0
                if count == 1 and self.documents_table.item(0, 0) and "Nessun documento" in self.documents_table.item(0, 0).text():
                    count = 0
                
                # Trova l'indice del tab dei documenti nel QTabWidget principale
                tab_index = self.tab_widget.indexOf(self.tab_documenti)
                if tab_index != -1:
                    self.tab_widget.setTabText(tab_index, f"Documenti Allegati ({count})")
            else:
                self.logger.warning("Attributo 'documents_table' non trovato in _update_document_tab_title.")

        except Exception as e:
            self.logger.error(f"Errore imprevisto durante l'aggiornamento del titolo del tab documenti: {e}", exc_info=True)

    def _save_changes(self):
        """Salva le modifiche apportate ai dati generali della partita."""
        self.logger.info(f"Tentativo di salvare le modifiche per la partita ID: {self.partita_id}")

        # Raccoglie i dati dai widget, inclusi quelli nuovi/modificati
        data_chiusura_val = self.data_chiusura_edit.date().toPyDate() if self.data_chiusura_check.isChecked() else None
        
        dati_da_salvare = {
            "numero_partita": self.numero_partita_spinbox.value(),
            "suffisso_partita": self.suffisso_partita_edit.text().strip() or None,
            "tipo": self.tipo_combo.currentText(),
            "stato": self.stato_combo.currentText(),
            "data_impianto": qdate_to_datetime(self.data_impianto_edit.date()),
            "data_chiusura": data_chiusura_val,
            "numero_provenienza": self.numero_provenienza_edit.text().strip() or None
        }

        # La validazione e la chiamata al DB rimangono le stesse...
        try:
            self.db_manager.update_partita(self.partita_id, dati_da_salvare)
            self.logger.info(f"Dati generali della partita ID {self.partita_id} aggiornati con successo.")
            QMessageBox.information(self, "Salvataggio Riuscito", "Le modifiche ai dati generali della partita sono state salvate.")
            # Ricarica i dati per mantenere la UI sincronizzata con il DB
            self._load_all_partita_data()
        except (DBUniqueConstraintError, DBDataError, DBNotFoundError, DBMError) as e:
            self.logger.error(f"Errore durante il salvataggio dei dati per la partita ID {self.partita_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore di Salvataggio", f"Impossibile salvare le modifiche:\n{e}")
        except Exception as e_gen:
            # ...
            QMessageBox.critical(self, "Errore Critico", f"Si è verificato un errore di sistema imprevisto: {e_gen}")

    def _archivia_partita(self):
        numero = self.numero_partita_spinbox.value()
        suffisso = self.suffisso_partita_edit.text().strip()
        numero_display = f"{numero} {suffisso}" if suffisso else str(numero)
        risposta = QMessageBox.question(
            self, "Conferma Archiviazione",
            f"Archiviare la partita N.{numero_display}?\n\nNon verrà eliminata, solo nascosta dalle ricerche.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if risposta != QMessageBox.StandardButton.Yes:
            return
        try:
            self.db_manager.archivia_partita(self.partita_id)
            QMessageBox.information(self, "Operazione completata",
                                    f"Partita N.{numero_display} archiviata con successo.")
            self.reject()
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile archiviare la partita:\n{e}")


class DuplicaPartitaOptionsDialog(QDialog):
    """
    Un dialogo per raccogliere le opzioni necessarie alla duplicazione di una partita.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Opzioni di Duplicazione Partita")
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QFormLayout(self)
        layout.setSpacing(10)

        self.nuovo_numero_partita_spinbox = QSpinBox()
        self.nuovo_numero_partita_spinbox.setRange(1, 9999999)
        layout.addRow("Nuovo Numero Partita (*):", self.nuovo_numero_partita_spinbox)

        self.nuovo_suffisso_edit = QLineEdit()
        self.nuovo_suffisso_edit.setPlaceholderText("Es. bis, A (opzionale)")
        layout.addRow("Nuovo Suffisso Partita:", self.nuovo_suffisso_edit)

        self.mantieni_possessori_check = QCheckBox("Mantieni i possessori originali nella nuova partita")
        self.mantieni_possessori_check.setChecked(True)
        layout.addRow(self.mantieni_possessori_check)
        
        self.mantieni_immobili_check = QCheckBox("Copia gli immobili originali nella nuova partita")
        self.mantieni_immobili_check.setChecked(False)
        layout.addRow(self.mantieni_immobili_check)
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addRow(self.button_box)

    def get_options(self) -> Optional[Dict[str, Any]]:
        """Restituisce le opzioni selezionate come dizionario."""
        return {
            "nuovo_numero_partita": self.nuovo_numero_partita_spinbox.value(),
            "nuovo_suffisso": self.nuovo_suffisso_edit.text().strip() or None,
            "mantenere_possessori": self.mantieni_possessori_check.isChecked(),
            "mantenere_immobili": self.mantieni_immobili_check.isChecked()
        }


class ModificaImmobileDialog(QDialog):
    """
    Dialogo per la modifica dei dettagli di un singolo immobile.
    """
    def __init__(self, db_manager, immobile_id: int, comune_id_partita: int, parent=None):
        super().__init__(parent)
        
        # --- Parametri e stato interno ---
        self.db_manager = db_manager
        self.immobile_id = immobile_id
        self.comune_id_partita = comune_id_partita
        self.dati_originali = None # Conterrà i dati caricati dal DB

        # --- Setup UI ---
        self.setWindowTitle(f"Modifica Immobile ID: {self.immobile_id}")
        self.setMinimumWidth(500)
        
        self._setup_ui()
        self._load_initial_data()

    def _setup_ui(self):
        """Crea e assembla i widget dell'interfaccia."""
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # --- Creazione dei campi del modulo ---
        self.natura_combo = QComboBox()
        self.classificazione_edit = QLineEdit()
        self.indirizzo_edit = QLineEdit()
        self.localita_combo = QComboBox()
        self.foglio_edit = QLineEdit()
        self.mappale_edit = QLineEdit()
        self.subalterno_edit = QLineEdit()
        self.vani_spinbox = QDoubleSpinBox()
        self.vani_spinbox.setDecimals(2)
        self.vani_spinbox.setRange(0, 9999.99)
        self.note_edit = QTextEdit()
        self.note_edit.setMaximumHeight(80)

        # Popola i ComboBox
        self._populate_combos()

        # Aggiungi i widget al form layout
        form_layout.addRow("Natura:", self.natura_combo)
        form_layout.addRow("Classificazione:", self.classificazione_edit)
        form_layout.addRow("Indirizzo:", self.indirizzo_edit)
        form_layout.addRow("Località:", self.localita_combo)
        form_layout.addRow("Foglio:", self.foglio_edit)
        form_layout.addRow("Mappale:", self.mappale_edit)
        form_layout.addRow("Subalterno:", self.subalterno_edit)
        form_layout.addRow("Vani/Superficie:", self.vani_spinbox)
        form_layout.addRow("Note:", self.note_edit)

        main_layout.addLayout(form_layout)

        # --- Pulsanti Salva e Annulla ---
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        
        main_layout.addWidget(self.button_box)

    def _populate_combos(self):
        """Popola i QComboBox con dati dal database o valori fissi."""
        # Esempio con valori fissi per 'Natura'
        # Potresti caricarli anche da una tabella del DB
        self.natura_combo.addItems([
            "Fabbricato", "Terreno", "Area Urbana", "Lastrico Solare", "Altro"
        ])

        # Carica le località per il comune specifico
        try:
            localita_list = self.db_manager.get_localita_per_comune(self.comune_id_partita)
            for loc_id, nome_localita in localita_list:
                self.localita_combo.addItem(nome_localita, userData=loc_id)
        except Exception as e:
            self.logger.error(f"Errore nel caricamento delle località: {e}")
            self.localita_combo.addItem("Errore caricamento", -1)

    def _load_initial_data(self):
        """Carica i dati dell'immobile dal DB e popola i campi."""
        try:
            self.dati_originali = self.db_manager.get_immobile_details(self.immobile_id)
            if not self.dati_originali:
                QMessageBox.critical(self, "Errore", "Impossibile trovare i dati per l'immobile specificato.")
                # Disabilita i campi e il pulsante salva
                self.button_box.button(QDialogButtonBox.StandardButton.Save).setEnabled(False)
                for i in range(self.layout().count()):
                    widget = self.layout().itemAt(i).widget()
                    if widget: widget.setEnabled(False)
                return

            # Popola i campi
            self.natura_combo.setCurrentText(self.dati_originali.get('natura', ''))
            self.classificazione_edit.setText(self.dati_originali.get('classificazione', ''))
            self.indirizzo_edit.setText(self.dati_originali.get('indirizzo', ''))
            self.foglio_edit.setText(str(self.dati_originali.get('foglio', '')))
            self.mappale_edit.setText(str(self.dati_originali.get('mappale', '')))
            self.subalterno_edit.setText(str(self.dati_originali.get('subalterno', '')))
            self.vani_spinbox.setValue(float(self.dati_originali.get('vani_o_superficie', 0.0)))
            self.note_edit.setPlainText(self.dati_originali.get('note', ''))
            
            # Seleziona la località corretta nel ComboBox
            id_localita_originale = self.dati_originali.get('id_localita')
            if id_localita_originale:
                index = self.localita_combo.findData(id_localita_originale)
                if index != -1:
                    self.localita_combo.setCurrentIndex(index)

        except Exception as e:
            QMessageBox.critical(self, "Errore di Caricamento", f"Impossibile caricare i dati dell'immobile:\n{e}")
            self.reject() # Chiude il dialogo in caso di errore critico

    def _save_changes(self):
        """Raccoglie i dati, li valida e li salva nel database."""
        # 1. Raccogli i dati aggiornati dai widget
        dati_aggiornati = {
            'natura': self.natura_combo.currentText(),
            'classificazione': self.classificazione_edit.text().strip(),
            'indirizzo': self.indirizzo_edit.text().strip(),
            'id_localita': self.localita_combo.currentData(),
            'foglio': self.foglio_edit.text().strip(),
            'mappale': self.mappale_edit.text().strip(),
            'subalterno': self.subalterno_edit.text().strip(),
            'vani_o_superficie': self.vani_spinbox.value(),
            'note': self.note_edit.toPlainText().strip()
        }

        # 2. Validazione (esempio base)
        if not all([dati_aggiornati['natura'], dati_aggiornati['foglio'], dati_aggiornati['mappale']]):
            QMessageBox.warning(self, "Dati Mancanti", "I campi 'Natura', 'Foglio' e 'Mappale' sono obbligatori.")
            return

        # 3. Chiamata al DB Manager per l'aggiornamento
        try:
            successo = self.db_manager.update_immobile(self.immobile_id, dati_aggiornati)
            if successo:
                QMessageBox.information(self, "Successo", "Immobile aggiornato con successo.")
                return True # L'operazione è andata a buon fine
            else:
                QMessageBox.critical(self, "Errore Database", "L'aggiornamento nel database è fallito per un motivo sconosciuto.")
                return False
        except Exception as e:
            QMessageBox.critical(self, "Errore Critico", f"Si è verificato un errore durante il salvataggio:\n{e}")
            return False

    # Override del metodo accept per includere la logica di salvataggio
    def accept(self):
        """Eseguito quando si preme 'Salva'."""
        if self._save_changes():
            super().accept() # Chiude il dialogo con stato 'Accepted' solo se il salvataggio ha successo

# In dialogs.py, SOSTITUISCI l'intera classe PossessoreSelectionDialog


class PossessoreSelectionDialog(QDialog):
    def __init__(self, db_manager: CatastoDBManager, comune_id: Optional[int], parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        # comune_id ora è un filtro iniziale opzionale, non un requisito fisso
        self.comune_id_filter = comune_id
        self.selected_possessore = None
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")

        self.setWindowTitle("Seleziona o Crea Possessore")
        self.setMinimumSize(700, 500)

        self._initUI()
        self.load_data()

    def _initUI(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()

        # --- Tab 1: Seleziona Esistente ---
        select_tab = QWidget()
        select_layout = QVBoxLayout(select_tab)
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filtra per nome:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Digita per filtrare su tutti i comuni...")
        self.filter_edit.textChanged.connect(self.filter_possessori)
        filter_layout.addWidget(self.filter_edit)
        select_layout.addLayout(filter_layout)

        self.possessori_table = QTableWidget()
        # Aggiungiamo il comune di riferimento alla tabella
        self.possessori_table.setColumnCount(5)
        self.possessori_table.setHorizontalHeaderLabels(["ID", "Nome Completo", "Paternità", "Comune Riferimento", "Stato"])
        self.possessori_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.possessori_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.possessori_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.possessori_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.possessori_table.itemDoubleClicked.connect(self.handle_selection)
        select_layout.addWidget(self.possessori_table)
        self.tabs.addTab(select_tab, "Seleziona Esistente")

        # --- Tab 2: Crea Nuovo ---
        create_tab = QWidget()
        create_layout = QFormLayout(create_tab)
        self.cognome_edit = QLineEdit()
        create_layout.addRow("Cognome e Nome (*):", self.cognome_edit)
        self.paternita_edit = QLineEdit()
        create_layout.addRow("Paternità:", self.paternita_edit)
        self.nome_completo_edit = QLineEdit()
        create_layout.addRow("Nome Completo (*):", self.nome_completo_edit)

        # --- MODIFICA CHIAVE: Combo per selezionare il comune del NUOVO possessore ---
        self.new_poss_comune_combo = QComboBox()
        create_layout.addRow("Comune di Riferimento (*):", self.new_poss_comune_combo)
        # --- FINE MODIFICA ---

        self.attivo_checkbox = QCheckBox("Attivo")
        self.attivo_checkbox.setChecked(True)
        create_layout.addRow(self.attivo_checkbox)
        self.tabs.addTab(create_tab, "Crea Nuovo")

        layout.addWidget(self.tabs)

        buttons_layout = QHBoxLayout()
        self.ok_button = QPushButton("Seleziona")
        self.ok_button.clicked.connect(self.handle_selection)
        buttons_layout.addWidget(self.ok_button)
        self.cancel_button = QPushButton("Annulla")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)

    def load_data(self):
        """Carica i dati per entrambi i tab (lista possessori e lista comuni)."""
        self._load_possessori_for_table()
        self._load_comuni_for_combo()

    def _load_possessori_for_table(self, filter_text=None):
        self.possessori_table.setRowCount(0)
        try:
            # Se è stato passato un comune_id, filtra per quello. Altrimenti, ricerca globale.
            if self.comune_id_filter:
                possessori_list = self.db_manager.get_possessori_by_comune(self.comune_id_filter, filter_text)
            else:
                possessori_list = self.db_manager.search_possessori_by_term_globally(filter_text)

            self.possessori_table.setRowCount(len(possessori_list))
            for row, pos_data in enumerate(possessori_list):
                self.possessori_table.setItem(row, 0, QTableWidgetItem(str(pos_data.get('id', ''))))
                self.possessori_table.setItem(row, 1, QTableWidgetItem(pos_data.get('nome_completo', '')))
                self.possessori_table.setItem(row, 2, QTableWidgetItem(pos_data.get('paternita', '')))
                self.possessori_table.setItem(row, 3, QTableWidgetItem(pos_data.get('comune_riferimento_nome', '')))
                self.possessori_table.setItem(row, 4, QTableWidgetItem("Attivo" if pos_data.get('attivo', False) else "Non Attivo"))
            self.possessori_table.resizeColumnsToContents()
        except DBMError as e:
            QMessageBox.critical(self, "Errore", f"Impossibile caricare i possessori: {e}")

    def _load_comuni_for_combo(self):
        self.new_poss_comune_combo.clear()
        try:
            comuni = self.db_manager.get_elenco_comuni_semplice()
            self.new_poss_comune_combo.addItem("--- Seleziona Comune ---", None)
            for id, nome in comuni:
                self.new_poss_comune_combo.addItem(nome, id)
        except DBMError:
            self.new_poss_comune_combo.addItem("Errore caricamento", None)

    def filter_possessori(self):
        self._load_possessori_for_table(self.filter_edit.text().strip())

    def handle_selection(self):
        if self.tabs.currentIndex() == 0: # Tab "Seleziona Esistente"
            selected = self.possessori_table.selectedItems()
            if not selected:
                QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un possessore dalla tabella.")
                return
            row = selected[0].row()
            id_poss = int(self.possessori_table.item(row, 0).text())
            # Recuperiamo tutti i dettagli per assicurarci di averli
            self.selected_possessore = self.db_manager.get_possessore_full_details(id_poss)
            self.accept()

        elif self.tabs.currentIndex() == 1: # Tab "Crea Nuovo"
            nome_completo = self.nome_completo_edit.text().strip()
            cognome_nome = self.cognome_edit.text().strip()
            paternita = self.paternita_edit.text().strip() or None
            comune_id = self.new_poss_comune_combo.currentData()

            if not nome_completo or not cognome_nome or comune_id is None:
                QMessageBox.warning(self, "Dati Mancanti", "Nome completo, Cognome/Nome e Comune sono obbligatori.")
                return

            try:
                new_id = self.db_manager.create_possessore(
                    nome_completo=nome_completo,
                    cognome_nome=cognome_nome,
                    paternita=paternita,
                    comune_riferimento_id=comune_id,
                    attivo=self.attivo_checkbox.isChecked()
                )
                self.selected_possessore = self.db_manager.get_possessore_full_details(new_id)
                QMessageBox.information(self, "Successo", f"Nuovo possessore '{nome_completo}' creato con successo.")
                self.accept()
            except (DBMError, DBUniqueConstraintError) as e:
                QMessageBox.critical(self, "Errore Creazione", str(e))

class ImmobileDialog(QDialog):
    def __init__(self, db_manager, comune_id, parent=None):
        super(ImmobileDialog, self).__init__(parent)
        self.db_manager = db_manager
        self.comune_id = comune_id
        self.immobile_data = None
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}") # Inizializza il logger

        self.setWindowTitle("Inserisci Immobile")
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout()

        form_layout = QGridLayout()

        # Natura
        natura_label = QLabel("Natura:")
        self.natura_edit = QLineEdit()
        self.natura_edit.setPlaceholderText("Es. Casa, Terreno, Garage, ecc.")

        form_layout.addWidget(natura_label, 0, 0)
        form_layout.addWidget(self.natura_edit, 0, 1)

        # Località
        localita_label = QLabel("Località:")
        self.localita_button = QPushButton("Seleziona/Gestisci Località...") # Modificato testo del pulsante
        self.localita_button.clicked.connect(self.select_localita)
        self.localita_id = None
        self.localita_display = QLabel("Nessuna località selezionata")

        form_layout.addWidget(localita_label, 1, 0)
        form_layout.addWidget(self.localita_button, 1, 1)
        form_layout.addWidget(self.localita_display, 1, 2)

        # ... (resto dei campi del form) ...
        # Classificazione
        classificazione_label = QLabel("Classificazione:")
        self.classificazione_edit = QLineEdit()
        self.classificazione_edit.setPlaceholderText(
            "Es. Abitazione civile, Deposito, ecc.")

        form_layout.addWidget(classificazione_label, 2, 0)
        form_layout.addWidget(self.classificazione_edit, 2, 1)

        # Consistenza
        consistenza_label = QLabel("Consistenza:")
        self.consistenza_edit = QLineEdit()
        self.consistenza_edit.setPlaceholderText("Es. 120 mq")

        form_layout.addWidget(consistenza_label, 3, 0)
        form_layout.addWidget(self.consistenza_edit, 3, 1)

        # Numero piani
        piani_label = QLabel("Numero piani:")
        self.piani_edit = QSpinBox()
        self.piani_edit.setMinimum(0)
        self.piani_edit.setMaximum(99)
        self.piani_edit.setSpecialValueText("Non specificato")

        form_layout.addWidget(piani_label, 4, 0)
        form_layout.addWidget(self.piani_edit, 4, 1)

        # Numero vani
        vani_label = QLabel("Numero vani:")
        self.vani_edit = QSpinBox()
        self.vani_edit.setMinimum(0)
        self.vani_edit.setMaximum(99)
        self.vani_edit.setSpecialValueText("Non specificato")

        form_layout.addWidget(vani_label, 5, 0)
        form_layout.addWidget(self.vani_edit, 5, 1)

        layout.addLayout(form_layout)

        # Pulsanti
        buttons_layout = QHBoxLayout()

        self.ok_button = QPushButton("Inserisci")
        self.ok_button.clicked.connect(self.handle_insert)

        self.cancel_button = QPushButton("Annulla")
        self.cancel_button.clicked.connect(self.reject)

        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(self.cancel_button)

        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def select_localita(self):
        """
        Apre un dialogo per selezionare o gestire la località.
        Permetterà anche la creazione di nuove località.
        """
        if self.comune_id is None:
            QMessageBox.warning(self, "Comune Mancante",
                                "Selezionare un comune per la partita prima di scegliere una località per l'immobile.")
            return

        # Lazy import per evitare dipendenza circolare con dialogs_entity
        from dialogs_entity import LocalitaSelectionDialog

        dialog = LocalitaSelectionDialog(self.db_manager,
                                         self.comune_id,
                                         self,
                                         selection_mode=False) # <--- CAMBIATO A False
        
        # Imposta il titolo del dialogo per riflettere la possibilità di gestione/creazione
        dialog.setWindowTitle(f"Seleziona o Crea Località per Comune ID: {self.comune_id}")

        result = dialog.exec()

        # Il LocalitaSelectionDialog, se modificato per get_selected_or_created_localita,
        # dovrebbe restituire un dizionario con id e nome (compreso il civico).
        # Ad esempio: { 'id': 1, 'nome': 'Via Roma, 12 (Via)' }
        if result == QDialog.DialogCode.Accepted:
            if dialog.selected_localita_id is not None and dialog.selected_localita_name is not None:
                self.localita_id = dialog.selected_localita_id
                self.localita_display.setText(dialog.selected_localita_name)
                self.logger.info(
                    f"ImmobileDialog: Località selezionata/creata ID: {self.localita_id}, Nome: '{self.localita_display.text()}'")
            else:
                self.logger.warning(
                    "ImmobileDialog: LocalitaSelectionDialog accettato ma ID/nome località non validi (probabilmente selezione annullata dopo creazione).")
                # Se l'utente crea una località ma poi non la seleziona prima di chiudere,
                # oppure se annulla la selezione, qui potremmo voler pulire.
                self.localita_id = None
                self.localita_display.setText("Nessuna località selezionata")
        else:
            self.logger.info("Selezione/Creazione località annullata dall'utente in ImmobileDialog.")
            # Non fare nulla se l'utente annulla, la selezione precedente (o nessuna) rimane.

    def handle_insert(self):
        """Gestisce l'inserimento dell'immobile."""
        # Validazione input
        natura = self.natura_edit.text().strip()
        if not natura:
            QMessageBox.warning(
                self, "Errore", "La natura dell'immobile è obbligatoria.")
            return

        if not self.localita_id:
            QMessageBox.warning(self, "Errore", "Seleziona una località.")
            return

        # Raccoglie i dati
        classificazione = self.classificazione_edit.text().strip() or None
        consistenza = self.consistenza_edit.text().strip() or None
        numero_piani = self.piani_edit.value() if self.piani_edit.value() > 0 else None
        numero_vani = self.vani_edit.value() if self.vani_edit.value() > 0 else None

        # Crea il dizionario dei dati dell'immobile
        self.immobile_data = {
            'natura': natura,
            'localita_id': self.localita_id,
            'localita_nome': self.localita_display.text(),
            'classificazione': classificazione,
            'consistenza': consistenza,
            'numero_piani': numero_piani,
            'numero_vani': numero_vani
        }

        self.accept()

class AggiungiDocumentoDialog(QDialog):
    def __init__(self, db_manager: 'CatastoDBManager', partita_id: int, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.partita_id = partita_id
        self.selected_file_path: Optional[str] = None
        self.document_data: Optional[Dict[str, Any]] = None

        self.setWindowTitle(f"Allega Nuovo Documento alla Partita ID: {self.partita_id}")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)
        form = QFormLayout()


        self.btn_seleziona_file = QPushButton("Seleziona File (PDF, JPG)...")
        self.btn_seleziona_file.clicked.connect(self._seleziona_file)
        self.file_selezionato_label = QLabel("Nessun file selezionato.")
        form.addRow(self.btn_seleziona_file, self.file_selezionato_label)

        self.titolo_edit = QLineEdit()
        form.addRow("Titolo Documento (*):", self.titolo_edit)

        self.descrizione_edit = QTextEdit()
        self.descrizione_edit.setMinimumHeight(60)
        form.addRow("Descrizione:", self.descrizione_edit)

        self.tipo_documento_combo = QComboBox()
        # Popola con tipi comuni o da una tabella DB se preferisci
        self.tipo_documento_combo.addItems(["Atto Notarile", "Mappa Catastale", "Fotografia Storica", "Corrispondenza", "Estratto Matriciale", "Altro"])
        form.addRow("Tipo Documento (*):", self.tipo_documento_combo)

        self.anno_edit = QSpinBox()
        self.anno_edit.setRange(1000, QDate.currentDate().year() + 5) # Range ampio
        self.anno_edit.setSpecialValueText(" ") # Per anno non specificato
        self.anno_edit.setValue(self.anno_edit.minimum()) # Default a " "
        form.addRow("Anno Documento (opz.):", self.anno_edit)

        self.periodo_combo = QComboBox()
        form.addRow("Periodo Storico (opz.):", self.periodo_combo)
        self._carica_periodi_storici() # Metodo per popolare la combo

        self.rilevanza_combo = QComboBox()
        self.rilevanza_combo.addItems(['primaria', 'secondaria', 'correlata']) # Da CHECK constraint
        form.addRow("Rilevanza per la Partita (*):", self.rilevanza_combo)

        self.note_legame_edit = QLineEdit()
        form.addRow("Note sul Legame (opz.):", self.note_legame_edit)
        
        # self.metadati_edit = QTextEdit() # Per JSONB - semplice input testuale per ora
        # self.metadati_edit.setPlaceholderText("Opzionale: Inserire metadati aggiuntivi in formato JSON, es. {\"risoluzione\": \"300dpi\"}")
        # self.metadati_edit.setMinimumHeight(60)
        # form.addRow("Metadati JSON (opz.):", self.metadati_edit)

        layout.addLayout(form)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Salva Allegato")
        self.button_box.accepted.connect(self._salva_allegato)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        self.setLayout(layout)
        
    def set_initial_file_path(self, file_path: str):
        """Imposta un percorso file iniziale e aggiorna la label di visualizzazione."""
        if os.path.exists(file_path) and os.path.isfile(file_path):
            self.selected_file_path = file_path
            self.file_selezionato_label.setText(os.path.basename(file_path))
            # Puoi anche tentare di derivare un titolo iniziale dal nome del file qui
            # es. self.titolo_edit.setText(os.path.splitext(os.path.basename(file_path))[0])
        else:
            self.logger.warning(f"Tentativo di impostare un percorso file iniziale non valido in AggiungiDocumentoDialog: {file_path}")
            self.selected_file_path = None
            self.file_selezionato_label.setText("Nessun file selezionato (iniziale non valido).")

    def _seleziona_file(self):
        filePath, _ = QFileDialog.getOpenFileName(self, "Seleziona Documento", "", 
                                                  "Documenti (*.pdf *.jpg *.jpeg *.png);;File PDF (*.pdf);;Immagini JPG (*.jpg *.jpeg);;Immagini PNG (*.png);;Tutti i file (*)")
        if filePath:
            self.selected_file_path = filePath
            import os
            self.file_selezionato_label.setText(os.path.basename(filePath))
        else:
            self.selected_file_path = None
            self.file_selezionato_label.setText("Nessun file selezionato.")

    def _carica_periodi_storici(self):
        self.periodo_combo.clear()
        self.periodo_combo.addItem("Nessuno", None) # Opzione per non selezionare periodo
        try:
            periodi = self.db_manager.get_historical_periods() # Metodo esistente
            for p in periodi:
                self.periodo_combo.addItem(f"{p.get('nome')} ({p.get('anno_inizio')}-{p.get('anno_fine', 'oggi')})", p.get('id'))
        except Exception as e:
            self.periodo_combo.addItem("Errore caricamento periodi", None)
            logging.getLogger("CatastoGUI").error(f"Errore caricamento periodi storici per dialogo allegato: {e}")

    def _salva_allegato(self):
        if not self.selected_file_path:
            QMessageBox.warning(self, "File Mancante", "Selezionare un file da allegare.")
            return
        
        titolo = self.titolo_edit.text().strip()
        tipo_documento = self.tipo_documento_combo.currentText()
        rilevanza = self.rilevanza_combo.currentText()

        if not titolo or not tipo_documento or not rilevanza:
            QMessageBox.warning(self, "Dati Obbligatori Mancanti", "Titolo, Tipo Documento e Rilevanza sono obbligatori.")
            return

        descrizione = self.descrizione_edit.toPlainText().strip() or None
        anno_val = self.anno_edit.value()
        anno = anno_val if self.anno_edit.text().strip() != "" else None # Se non è " "
        
        periodo_id_data = self.periodo_combo.currentData()
        periodo_id = periodo_id_data if periodo_id_data is not None else None
        
        note_legame = self.note_legame_edit.text().strip() or None
        # metadati_str = self.metadati_edit.toPlainText().strip() or None
        # if metadati_str:
        #     try:
        #         json.loads(metadati_str) # Valida JSON
        #     except json.JSONDecodeError:
        #         QMessageBox.warning(self, "Errore Metadati", "Il testo dei metadati non è un JSON valido.")
        #         return
        metadati_str = None # Per ora non gestiamo input JSON complesso dall'utente

        # Qui la logica di copia del file e salvataggio nel DB
        self.document_data = {
            "titolo": titolo, "tipo_documento": tipo_documento, "descrizione": descrizione,
            "anno": anno, "periodo_id": periodo_id, "rilevanza": rilevanza, 
            "note_legame": note_legame, "percorso_file_originale": self.selected_file_path,
            "metadati_json": metadati_str 
        }
        self.accept()
        

# Estratto in import_dialogs.py — backward compat re-export
from import_dialogs import CSVImportResultDialog

# ---------------------------------------------------------------------------
# Import comuni e località da CSV / ISTAT
# ---------------------------------------------------------------------------


# Estratto in import_dialogs.py — backward compat re-export
from import_dialogs import (
    ISTATDownloadWorker, OSMLocalitaWorker,
    ImportComuniDialog, ImportLocalitaDialog,
    _mostra_risultati_import, _popola_preview_tabella,
)


class AlberoGeneralogicoDialog(QDialog):
    """Visualizza interattivamente la catena genealogica di una partita catastale."""

    # Colori nodi albero
    _COLOR_ROOT = QColor("#E3F2FD")
    _COLOR_SECT_PRE = QColor("#FFF3E0")
    _COLOR_NODE_PRE = QColor("#FFF8E1")
    _COLOR_SECT_SUC = QColor("#E8F5E9")
    _COLOR_NODE_SUC = QColor("#F1F8E9")

    def __init__(self, partita_id: int, db_manager, parent=None):
        super().__init__(parent)
        self.partita_id = partita_id
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")
        self.setWindowTitle("Albero Genealogico Partita")
        self.setMinimumSize(900, 600)
        self._dati = None
        self._init_ui()
        self._carica_dati()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Header
        self._header_label = QLabel()
        self._header_label.setWordWrap(True)
        layout.addWidget(self._header_label)

        # Splitter orizzontale: albero | dettaglio
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # QTreeWidget con 5 colonne
        self._tree = QTreeWidget()
        self._tree.setColumnCount(5)
        self._tree.setHeaderLabels(["Partita / Comune", "Tipo Variazione", "Data", "Possessori", "Stato"])
        self._tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.header().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._tree.header().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.itemClicked.connect(self._on_item_clicked)
        splitter.addWidget(self._tree)

        # QTextBrowser dettaglio
        self._detail = QTextBrowser()
        self._detail.setMinimumWidth(260)
        self._detail.setPlaceholderText("Seleziona un nodo per vedere i dettagli.")
        splitter.addWidget(self._detail)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

        # Barra pulsanti
        btn_layout = QHBoxLayout()
        btn_report = QPushButton("Apri Report Testo")
        btn_report.clicked.connect(self._apri_report_testo)
        btn_chiudi = QPushButton("Chiudi")
        btn_chiudi.clicked.connect(self.accept)
        btn_layout.addWidget(btn_report)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_chiudi)
        layout.addLayout(btn_layout)

    def _carica_dati(self):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self._dati = self.db_manager.get_genealogia_partita(self.partita_id)
        except Exception as e:
            self.logger.error(f"Errore caricamento genealogia: {e}", exc_info=True)
            self._dati = None
        finally:
            QApplication.restoreOverrideCursor()

        if not self._dati:
            QMessageBox.warning(self, "Partita non trovata",
                                f"Nessuna partita trovata con ID {self.partita_id}.")
            self.accept()
            return
        self._popola_albero()

    def _fmt_partita(self, p: dict) -> str:
        num = str(p.get('numero_partita', ''))
        suf = (p.get('suffisso_partita') or '').strip()
        comune = p.get('comune_nome', '')
        return f"N.{num}{(' (' + suf + ')') if suf else ''} — {comune}"

    def _fmt_data(self, val) -> str:
        if val is None:
            return ''
        return str(val)[:10]

    def _set_row_bg(self, item: QTreeWidgetItem, color: QColor):
        brush = QBrush(color)
        for col in range(5):
            item.setBackground(col, brush)

    def _popola_albero(self):
        p = self._dati['partita']
        predecessori = self._dati['predecessori']
        successori = self._dati['successori']

        # Aggiorna header
        self._header_label.setText(
            f"<b>Albero genealogico — {self._fmt_partita(p)}</b>"
            f" &nbsp;·&nbsp; Stato: <i>{p.get('stato', '')}</i>"
            f" &nbsp;·&nbsp; Impianto: {self._fmt_data(p.get('data_impianto'))}"
        )

        self._tree.clear()

        # Nodo root
        root = QTreeWidgetItem(self._tree)
        root.setText(0, self._fmt_partita(p))
        root.setText(4, p.get('stato', ''))
        root.setData(0, Qt.ItemDataRole.UserRole, {'tipo': 'root', 'dati': p})
        self._set_row_bg(root, self._COLOR_ROOT)
        font = root.font(0); font.setBold(True); root.setFont(0, font)

        # Sezione Predecessori
        sect_pre = QTreeWidgetItem(root)
        sect_pre.setText(0, f"Predecessori ({len(predecessori)})")
        self._set_row_bg(sect_pre, self._COLOR_SECT_PRE)
        font_i = sect_pre.font(0); font_i.setItalic(True); sect_pre.setFont(0, font_i)
        sect_pre.setData(0, Qt.ItemDataRole.UserRole, {'tipo': 'sezione'})
        for pre in predecessori:
            child = QTreeWidgetItem(sect_pre)
            child.setText(0, self._fmt_partita(pre))
            child.setText(1, pre.get('tipo_variazione', '') or '')
            child.setText(2, self._fmt_data(pre.get('data_variazione')))
            child.setText(3, pre.get('possessori', '') or '')
            child.setText(4, pre.get('stato', '') or '')
            child.setData(0, Qt.ItemDataRole.UserRole, {'tipo': 'predecessore', 'dati': pre})
            self._set_row_bg(child, self._COLOR_NODE_PRE)

        # Sezione Successori
        sect_suc = QTreeWidgetItem(root)
        sect_suc.setText(0, f"Successori ({len(successori)})")
        self._set_row_bg(sect_suc, self._COLOR_SECT_SUC)
        font_i2 = sect_suc.font(0); font_i2.setItalic(True); sect_suc.setFont(0, font_i2)
        sect_suc.setData(0, Qt.ItemDataRole.UserRole, {'tipo': 'sezione'})
        for suc in successori:
            child = QTreeWidgetItem(sect_suc)
            child.setText(0, self._fmt_partita(suc))
            child.setText(1, suc.get('tipo_variazione', '') or '')
            child.setText(2, self._fmt_data(suc.get('data_variazione')))
            child.setText(3, suc.get('possessori', '') or '')
            child.setText(4, suc.get('stato', '') or '')
            child.setData(0, Qt.ItemDataRole.UserRole, {'tipo': 'successore', 'dati': suc})
            self._set_row_bg(child, self._COLOR_NODE_SUC)

        self._tree.expandAll()

    def _on_item_clicked(self, item: QTreeWidgetItem, _col: int):
        payload = item.data(0, Qt.ItemDataRole.UserRole)
        if not payload or payload.get('tipo') == 'sezione':
            self._detail.clear()
            return
        d = payload.get('dati', {})
        tipo = payload.get('tipo', '')
        etichetta = {'root': 'Partita corrente', 'predecessore': 'Predecessore', 'successore': 'Successore'}.get(tipo, '')
        html = f"""
        <h3>{etichetta}</h3>
        <table cellspacing="4">
          <tr><td><b>Partita</b></td><td>{self._fmt_partita(d)}</td></tr>
          <tr><td><b>ID</b></td><td>{d.get('id', '')}</td></tr>
          <tr><td><b>Tipo</b></td><td>{d.get('tipo', '')}</td></tr>
          <tr><td><b>Stato</b></td><td>{d.get('stato', '')}</td></tr>
          <tr><td><b>Impianto</b></td><td>{self._fmt_data(d.get('data_impianto'))}</td></tr>
          <tr><td><b>Chiusura</b></td><td>{self._fmt_data(d.get('data_chiusura'))}</td></tr>
          <tr><td><b>Possessori</b></td><td>{d.get('possessori', '') or '—'}</td></tr>
        """
        if tipo in ('predecessore', 'successore'):
            html += f"""
          <tr><td><b>Variazione</b></td><td>{d.get('tipo_variazione', '') or '—'}</td></tr>
          <tr><td><b>Data variazione</b></td><td>{self._fmt_data(d.get('data_variazione'))}</td></tr>
          <tr><td><b>Nominativo rif.</b></td><td>{d.get('nominativo_riferimento', '') or '—'}</td></tr>
            """
        html += "</table>"
        self._detail.setHtml(html)

    def _apri_report_testo(self):
        if not self.db_manager:
            return
        testo = self.db_manager.genera_report_genealogico(self.partita_id)
        if not testo:
            QMessageBox.information(self, "Report", "Nessun report disponibile per questa partita.")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Report Genealogico Testuale")
        dlg.setMinimumSize(600, 450)
        v = QVBoxLayout(dlg)
        tb = QTextBrowser()
        tb.setPlainText(testo)
        v.addWidget(tb)
        btn = QPushButton("Chiudi"); btn.clicked.connect(dlg.accept)
        hl = QHBoxLayout(); hl.addStretch(); hl.addWidget(btn)
        v.addLayout(hl)
        dlg.exec()



class ConfrontoPartiteDialog(QDialog):
    """Confronto diff visuale tra due partite catastali (possessori e immobili)."""

    _COLOR_SOLO_A  = QColor("#FFCDD2")   # rosso chiaro — rimosso / solo in A
    _COLOR_SOLO_B  = QColor("#C8E6C9")   # verde chiaro — aggiunto / solo in B
    _COLOR_COMUNE  = QColor("#FFFFFF")   # bianco       — presente in entrambe

    def __init__(self, db_manager, partita_id_a: int = 0, partita_id_b: int = 0, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Confronto tra due Partite")
        self.setMinimumSize(900, 620)
        self._init_ui(partita_id_a, partita_id_b)

    def _init_ui(self, id_a: int, id_b: int):
        layout = QVBoxLayout(self)

        # --- Selezione partite ---
        sel_group = QGroupBox("Seleziona le due partite da confrontare")
        sel_layout = QHBoxLayout(sel_group)
        sel_layout.addWidget(QLabel("Partita A (base):"))
        self._spin_a = QSpinBox(); self._spin_a.setRange(1, 9999999); self._spin_a.setValue(max(id_a, 1))
        sel_layout.addWidget(self._spin_a)
        sel_layout.addSpacing(20)
        sel_layout.addWidget(QLabel("Partita B (confronto):"))
        self._spin_b = QSpinBox(); self._spin_b.setRange(1, 9999999); self._spin_b.setValue(max(id_b, 1))
        sel_layout.addWidget(self._spin_b)
        btn_confronta = QPushButton("Confronta")
        btn_confronta.clicked.connect(self._esegui_confronto)
        sel_layout.addWidget(btn_confronta)
        sel_layout.addStretch()
        layout.addWidget(sel_group)

        # --- Header riepilogativo ---
        self._header_label = QLabel("Seleziona due partite e premi Confronta.")
        self._header_label.setWordWrap(True)
        layout.addWidget(self._header_label)

        # --- Tab Possessori / Immobili ---
        self._tabs = QTabWidget()

        # Tab Possessori
        self._tbl_poss = self._make_table(["Nome Possessore", "Titolo", "Quota", "Stato"])
        self._tabs.addTab(self._tbl_poss, "Possessori")

        # Tab Immobili
        self._tbl_imm = self._make_table(["Natura", "Classificazione", "Località", "Piani", "Vani", "Consistenza", "Stato"])
        self._tabs.addTab(self._tbl_imm, "Immobili")

        layout.addWidget(self._tabs, 1)

        # Legenda
        leg_layout = QHBoxLayout()
        for color, testo in [(self._COLOR_SOLO_A, "Solo in A (rimosso)"),
                              (self._COLOR_SOLO_B, "Solo in B (aggiunto)"),
                              (self._COLOR_COMUNE, "Presente in entrambe")]:
            lbl = QLabel(f"  {testo}  ")
            lbl.setAutoFillBackground(True)
            p = lbl.palette(); p.setColor(lbl.backgroundRole(), color); lbl.setPalette(p)
            leg_layout.addWidget(lbl)
        leg_layout.addStretch()
        btn_chiudi = QPushButton("Chiudi"); btn_chiudi.clicked.connect(self.accept)
        leg_layout.addWidget(btn_chiudi)
        layout.addLayout(leg_layout)

    def _make_table(self, headers: list) -> QTableWidget:
        tbl = QTableWidget()
        tbl.setColumnCount(len(headers))
        tbl.setHorizontalHeaderLabels(headers)
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tbl.setAlternatingRowColors(False)
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, len(headers)):
            tbl.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        return tbl

    def _esegui_confronto(self):
        id_a = self._spin_a.value()
        id_b = self._spin_b.value()
        if id_a == id_b:
            QMessageBox.warning(self, "Stessa partita", "Seleziona due ID partita diversi.")
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            dati_a = self.db_manager.get_partita_details(id_a)
            dati_b = self.db_manager.get_partita_details(id_b)
        finally:
            QApplication.restoreOverrideCursor()
        if not dati_a:
            QMessageBox.warning(self, "Non trovata", f"Partita A (ID {id_a}) non trovata."); return
        if not dati_b:
            QMessageBox.warning(self, "Non trovata", f"Partita B (ID {id_b}) non trovata."); return

        lbl_a = f"N.{dati_a['numero_partita']} — {dati_a.get('comune_nome','')}"
        lbl_b = f"N.{dati_b['numero_partita']} — {dati_b.get('comune_nome','')}"
        self._header_label.setText(
            f"<b>A:</b> {lbl_a} &nbsp;|&nbsp; <b>B:</b> {lbl_b} &nbsp;·&nbsp; "
            f"Verde = aggiunto in B &nbsp;·&nbsp; Rosso = presente solo in A"
        )
        self._popola_possessori(dati_a.get('possessori', []), dati_b.get('possessori', []))
        self._popola_immobili(dati_a.get('immobili', []), dati_b.get('immobili', []))

    def _chiave_possessore(self, p: dict) -> str:
        return p.get('nome_completo', '').strip().lower()

    def _chiave_immobile(self, i: dict) -> str:
        return f"{i.get('natura','')}{i.get('localita_nome','')}{i.get('classificazione','')}".lower()

    def _set_row_color(self, tbl: QTableWidget, row: int, color: QColor):
        brush = QBrush(color)
        for col in range(tbl.columnCount()):
            item = tbl.item(row, col)
            if item:
                item.setBackground(brush)

    def _popola_possessori(self, poss_a: list, poss_b: list):
        chiavi_a = {self._chiave_possessore(p): p for p in poss_a}
        chiavi_b = {self._chiave_possessore(p): p for p in poss_b}
        tutte = sorted(set(chiavi_a) | set(chiavi_b))
        tbl = self._tbl_poss
        tbl.setRowCount(len(tutte))
        for r, k in enumerate(tutte):
            if k in chiavi_a and k in chiavi_b:
                p = chiavi_a[k]; stato = "Entrambe"; color = self._COLOR_COMUNE
            elif k in chiavi_a:
                p = chiavi_a[k]; stato = "Solo in A"; color = self._COLOR_SOLO_A
            else:
                p = chiavi_b[k]; stato = "Solo in B"; color = self._COLOR_SOLO_B
            for c, v in enumerate([p.get('nome_completo',''), p.get('titolo',''), p.get('quota',''), stato]):
                tbl.setItem(r, c, QTableWidgetItem(str(v) if v else ''))
            self._set_row_color(tbl, r, color)

    def _popola_immobili(self, imm_a: list, imm_b: list):
        chiavi_a = {self._chiave_immobile(i): i for i in imm_a}
        chiavi_b = {self._chiave_immobile(i): i for i in imm_b}
        tutte = sorted(set(chiavi_a) | set(chiavi_b))
        tbl = self._tbl_imm
        tbl.setRowCount(len(tutte))
        for r, k in enumerate(tutte):
            if k in chiavi_a and k in chiavi_b:
                i = chiavi_a[k]; stato = "Entrambe"; color = self._COLOR_COMUNE
            elif k in chiavi_a:
                i = chiavi_a[k]; stato = "Solo in A"; color = self._COLOR_SOLO_A
            else:
                i = chiavi_b[k]; stato = "Solo in B"; color = self._COLOR_SOLO_B
            vals = [i.get('natura',''), i.get('classificazione',''), i.get('localita_nome',''),
                    str(i.get('numero_piani','') or ''), str(i.get('numero_vani','') or ''),
                    str(i.get('consistenza','') or ''), stato]
            for c, v in enumerate(vals):
                tbl.setItem(r, c, QTableWidgetItem(v))
            self._set_row_color(tbl, r, color)


# ---------------------------------------------------------------------------
# SMTPSettingsDialog — Impostazioni notifiche email
# ---------------------------------------------------------------------------

