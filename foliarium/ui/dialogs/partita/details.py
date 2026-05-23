"""Dialog dettagli partita catastale."""

import logging
import os
from datetime import date
from typing import Optional, Dict, Any

from PyQt6.QtCore import (QDate, Qt, QTimer)
from PyQt6.QtGui import (QBrush, QColor)
from PyQt6.QtWidgets import (QAbstractItemView, QApplication,
                             QCheckBox, QComboBox, QDateEdit,
                             QDialog, QDoubleSpinBox,
                             QFileDialog, QFormLayout, QGridLayout, QGroupBox,
                             QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                             QMessageBox, QPushButton, QSpinBox, QStyle,
                             QTabWidget, QSplitter, QTableWidget,
                             QTableWidgetItem, QTextEdit, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget, QTextBrowser,
                             QDialogButtonBox)

from catasto_db_manager import CatastoDBManager
from foliarium.ui.widgets.custom import ImmobiliTableWidget
from foliarium.ui.widgets.timeline_partita import TimelinePartitaWidget
from foliarium.ui.widgets.document_viewer import DocumentViewerWidget

from app_utils import (GenericTextReportPDF, FPDF_AVAILABLE, prompt_to_open_file)
from foliarium.ui.dialogs.export_ import PDFApreviewDialog

from foliarium.ui.dialogs.admin import datetime_to_qdate, qdate_to_datetime

try:
    from catasto_db_manager import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError
except ImportError:
    class DBMError(Exception): pass
    class DBUniqueConstraintError(DBMError): pass
    class DBNotFoundError(DBMError): pass
    class DBDataError(DBMError): pass
from foliarium.ui.dialogs.partita.genealogia import AlberoGeneralogicoDialog


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
        # Aggiungi queste righe per gestire il ridimensionamento delle colonne
        header_possessori = possessori_table.horizontalHeader()
        # La colonna "ID" (indice 0) si adatta al contenuto
        header_possessori.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        # La colonna "Nome Completo" (indice 1) si espande per riempire lo spazio
        header_possessori.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        # Le colonne "Titolo" e "Quota" (indici 2 e 3) si adattano al contenuto
        header_possessori.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header_possessori.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
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

        # Tab Variazioni — Timeline cronologica
        variazioni_tab = QWidget()
        variazioni_layout = QVBoxLayout(variazioni_tab)
        variazioni_layout.setContentsMargins(0, 0, 0, 0)
        self.timeline_widget = TimelinePartitaWidget(
            variazioni=self.partita.get('variazioni') or [],
            current_partita_id=self.partita.get('id'),
        )
        variazioni_layout.addWidget(self.timeline_widget)
        self.tabs.addTab(variazioni_tab, "Variazioni")


        # Tab Documenti Allegati — lista a sinistra, viewer integrato a destra
        self.documents_tab_widget = QWidget()
        self.documents_tab_layout = QVBoxLayout(self.documents_tab_widget)
        self.documents_tab_layout.setContentsMargins(0, 0, 0, 0)

        doc_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Pannello sinistro: tabella + pulsanti
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(4, 4, 4, 4)

        self.documents_table = QTableWidget()
        self.documents_table.setColumnCount(6)
        self.documents_table.setHorizontalHeaderLabels(["ID Doc.", "Titolo", "Tipo Doc.", "Anno", "Rilevanza", "Percorso"])
        self.documents_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.documents_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.documents_table.horizontalHeader().setStretchLastSection(True)
        self.documents_table.setSortingEnabled(True)
        self.documents_table.itemSelectionChanged.connect(self._update_details_doc_buttons_state)
        self.documents_table.itemSelectionChanged.connect(self._on_document_selection_changed)
        left_layout.addWidget(self.documents_table, 1)

        doc_buttons_layout = QHBoxLayout()
        self.btn_apri_doc_details_dialog = QPushButton(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton), "Apri Esternamente")
        self.btn_apri_doc_details_dialog.setToolTip(
            "Apri il documento con il programma associato dal sistema operativo.")
        self.btn_apri_doc_details_dialog.clicked.connect(self._apri_documento_selezionato_from_details_dialog)
        self.btn_apri_doc_details_dialog.setEnabled(False)
        doc_buttons_layout.addWidget(self.btn_apri_doc_details_dialog)
        doc_buttons_layout.addStretch()
        left_layout.addLayout(doc_buttons_layout)

        doc_splitter.addWidget(left_panel)

        # Pannello destro: viewer integrato
        self.document_viewer = DocumentViewerWidget()
        doc_splitter.addWidget(self.document_viewer)

        doc_splitter.setStretchFactor(0, 1)
        doc_splitter.setStretchFactor(1, 2)
        doc_splitter.setSizes([320, 640])

        self.documents_tab_layout.addWidget(doc_splitter)
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
                from app_utils import format_indirizzo
                localita_info = format_indirizzo(
                    imm.get('tipologia_stradale') or imm.get('localita_tipo'),
                    imm.get('localita_nome'),
                    imm.get('numero_civico') or imm.get('civico'),
                )
                report_lines.append(f"    Località: {localita_info or 'N/A'}")
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

    def _on_document_selection_changed(self):
        """Carica il documento selezionato nel viewer integrato."""
        if not hasattr(self, "document_viewer"):
            return
        row = self.documents_table.currentRow()
        if row < 0:
            self.document_viewer.show_placeholder("Nessun documento selezionato.")
            return
        path_item = self.documents_table.item(row, 5)
        if not path_item:
            return
        # Il percorso completo è memorizzato in UserRole; il testo visibile
        # potrebbe essere troncato.
        percorso = path_item.data(Qt.ItemDataRole.UserRole) or path_item.text()
        title_item = self.documents_table.item(row, 1)
        title = title_item.text() if title_item else None
        self.document_viewer.load_document(percorso, title=title)

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


