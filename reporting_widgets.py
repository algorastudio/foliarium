"""
reporting_widgets.py — Widget di reportistica, esportazione e consultazioni per Foliarium.

Estratto da gui_widgets.py per migliorare la modularità.
Contiene:
  - RicercaDocumentiWidget       — Ricerca full-text documenti storici
  - EsportazioniWidget           — Export CSV / XLSX / PDF
  - ReportisticaWidget           — Generazione report testuali / PDF / ODT
  - StatisticheWidget            — Statistiche e grafici
  - RegistraConsultazioneWidget  — Registrazione consultazioni archivio

Backward compatibility: gui_widgets.py re-esporta tutte le classi.
"""

from __future__ import annotations

import os
import csv
import logging
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Tuple, TYPE_CHECKING

import pandas as pd

from PyQt6.QtCore import (
    QDate, QPoint, QSettings, QStandardPaths, Qt, QTimer, QUrl, pyqtSignal,
)
from PyQt6.QtGui import (
    QColor, QDesktopServices, QFont, QIcon, QAction,
)
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication,
    QCheckBox, QComboBox, QDateEdit, QDialog,
    QFileDialog, QFormLayout, QFrame, QGridLayout,
    QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMenu, QMessageBox, QProgressBar, QProgressDialog,
    QPushButton, QScrollArea, QSizePolicy, QSpinBox,
    QSplitter, QStyle, QTabWidget,
    QTableWidget, QTableWidgetItem, QTextBrowser, QTextEdit,
    QVBoxLayout, QWidget,
)

from app_utils import BulkReportPDF, FPDF_AVAILABLE, _get_default_export_path, prompt_to_open_file
from config import (
    APP_VERSION,
    COLONNE_POSSESSORI_DETTAGLI_NUM, COLONNE_POSSESSORI_DETTAGLI_LABELS,
    COLONNE_VISUALIZZAZIONE_POSSESSORI_NUM, COLONNE_VISUALIZZAZIONE_POSSESSORI_LABELS,
    COLONNE_INSERIMENTO_POSSESSORI_NUM, COLONNE_INSERIMENTO_POSSESSORI_LABELS,
    NUOVE_ETICHETTE_POSSESSORI,
)
from dialogs import (
    AlberoGeneralogicoDialog, ConfrontoPartiteDialog,
    ComuneSelectionDialog, PartitaSearchDialog, PossessoreSelectionDialog,
)
from custom_widgets import LazyLoadedWidget

if TYPE_CHECKING:
    from catasto_db_manager import CatastoDBManager

logger = logging.getLogger("CatastoGUI.reporting_widgets")

class RicercaDocumentiWidget(QWidget):
    """Pannello di ricerca full-text nei documenti storici catastali."""

    COLONNE = ["ID", "Titolo", "Tipo", "Anno", "Comune", "Partita", "Note"]
    KEYS    = ["id", "titolo", "tipo", "anno", "comune_nome", "numero_partita", "note"]

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        # --- Filtri ---
        filtri_group = QGroupBox("Criteri di Ricerca Documenti Storici")
        filtri_layout = QGridLayout(filtri_group)
        filtri_layout.setSpacing(8)

        # Riga 0: Parole chiave titolo
        filtri_layout.addWidget(QLabel("Parole chiave (titolo):"), 0, 0)
        self.titolo_edit = QLineEdit()
        self.titolo_edit.setPlaceholderText("Es. catasto, registro, voltura… (lascia vuoto per tutti)")
        self.titolo_edit.returnPressed.connect(self._esegui_ricerca)
        filtri_layout.addWidget(self.titolo_edit, 0, 1, 1, 3)

        # Riga 1: Tipo documento
        filtri_layout.addWidget(QLabel("Tipo documento:"), 1, 0)
        self.tipo_combo = QComboBox()
        self.tipo_combo.addItem("— Qualsiasi tipo —", None)
        for t in ["Catasto", "Voltura", "Frazionamento", "Successione", "Atto notarile", "Altro"]:
            self.tipo_combo.addItem(t, t)
        filtri_layout.addWidget(self.tipo_combo, 1, 1)

        # Riga 1: Anno da / a
        filtri_layout.addWidget(QLabel("Anno da:"), 1, 2)
        self.anno_da_spin = QSpinBox()
        self.anno_da_spin.setRange(0, 2100)
        self.anno_da_spin.setValue(0)
        self.anno_da_spin.setSpecialValueText("—")
        filtri_layout.addWidget(self.anno_da_spin, 1, 3)

        filtri_layout.addWidget(QLabel("Anno a:"), 2, 2)
        self.anno_a_spin = QSpinBox()
        self.anno_a_spin.setRange(0, 2100)
        self.anno_a_spin.setValue(0)
        self.anno_a_spin.setSpecialValueText("—")
        filtri_layout.addWidget(self.anno_a_spin, 2, 3)

        # Riga 2: ID partita opzionale
        filtri_layout.addWidget(QLabel("ID Partita (opz.):"), 2, 0)
        self.partita_id_spin = QSpinBox()
        self.partita_id_spin.setRange(0, 9999999)
        self.partita_id_spin.setValue(0)
        self.partita_id_spin.setSpecialValueText("—")
        filtri_layout.addWidget(self.partita_id_spin, 2, 1)

        main_layout.addWidget(filtri_group)

        # --- Pulsanti ---
        btn_layout = QHBoxLayout()
        self.btn_cerca = QPushButton("Cerca")
        self.btn_cerca.setIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        self.btn_cerca.clicked.connect(self._esegui_ricerca)
        self.btn_reset = QPushButton("Reset Filtri")
        self.btn_reset.clicked.connect(self._reset_filtri)
        self.risultati_label = QLabel("Nessuna ricerca eseguita.")
        btn_layout.addWidget(self.btn_cerca)
        btn_layout.addWidget(self.btn_reset)
        btn_layout.addStretch()
        btn_layout.addWidget(self.risultati_label)
        main_layout.addLayout(btn_layout)

        # --- Tabella risultati ---
        self.tabella = QTableWidget()
        self.tabella.setColumnCount(len(self.COLONNE))
        self.tabella.setHorizontalHeaderLabels(self.COLONNE)
        self.tabella.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabella.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabella.setAlternatingRowColors(True)
        hdr = self.tabella.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.tabella.setSortingEnabled(True)
        self.tabella.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabella.customContextMenuRequested.connect(self._apri_menu_documento)
        main_layout.addWidget(self.tabella, 1)

    def _apri_menu_documento(self, position: QPoint):
        index = self.tabella.indexAt(position)
        if not index.isValid():
            return
        row = index.row()
        def _cell(col):
            item = self.tabella.item(row, col)
            return item.text() if item else ""
        id_doc, titolo, tipo, anno, comune, partita = (
            _cell(0), _cell(1), _cell(2), _cell(3), _cell(4), _cell(5)
        )
        menu = QMenu(self.tabella)
        menu.addAction(f"Copia titolo: {titolo[:40]}{'…' if len(titolo)>40 else ''}").triggered.connect(
            lambda: QApplication.clipboard().setText(titolo))
        if anno:
            menu.addAction(f"Copia anno: {anno}").triggered.connect(
                lambda: QApplication.clipboard().setText(anno))
        if partita:
            menu.addAction(f"Copia partita: {partita}").triggered.connect(
                lambda: QApplication.clipboard().setText(partita))
        menu.addAction(f"Copia ID: {id_doc}").triggered.connect(
            lambda: QApplication.clipboard().setText(id_doc))
        menu.exec(self.tabella.viewport().mapToGlobal(position))

    def _esegui_ricerca(self):
        titolo = self.titolo_edit.text().strip() or None
        tipo = self.tipo_combo.currentData()
        anno_da = self.anno_da_spin.value() or None
        anno_a = self.anno_a_spin.value() or None
        partita_id = self.partita_id_spin.value() or None

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            risultati = self.db_manager.search_historical_documents(
                title=titolo,
                doc_type=tipo,
                year_start=anno_da,
                year_end=anno_a,
                partita_id=partita_id,
            )
        except Exception as e:
            self.logger.error(f"Errore ricerca documenti: {e}", exc_info=True)
            risultati = []
        finally:
            QApplication.restoreOverrideCursor()

        self._popola_tabella(risultati)

    def _popola_tabella(self, righe: list):
        self.tabella.setSortingEnabled(False)
        self.tabella.setRowCount(0)
        if not righe:
            self.risultati_label.setText("Nessun documento trovato.")
            self.tabella.setSortingEnabled(True)
            return
        self.tabella.setRowCount(len(righe))
        for r, row in enumerate(righe):
            for c, key in enumerate(self.KEYS):
                val = row.get(key, '') if isinstance(row, dict) else (row[c] if c < len(row) else '')
                item = QTableWidgetItem(str(val) if val is not None else '')
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.tabella.setItem(r, c, item)
        self.tabella.setSortingEnabled(True)
        self.risultati_label.setText(f"{len(righe)} documento/i trovato/i.")

    def _reset_filtri(self):
        self.titolo_edit.clear()
        self.tipo_combo.setCurrentIndex(0)
        self.anno_da_spin.setValue(0)
        self.anno_a_spin.setValue(0)
        self.partita_id_spin.setValue(0)
        self.tabella.setRowCount(0)
        self.risultati_label.setText("Nessuna ricerca eseguita.")


class EsportazioniWidget(LazyLoadedWidget):
    HEADER_MAPPINGS = {
        "Elenco Possessori": {
            "id": "ID Possessore", "comune_nome": "Comune di Riferimento", "nome_completo": "Nome Completo",
            "attivo": "Stato Attivo", "num_partite": "Numero Partite"
        },
        "Elenco Partite": {
            "id": "ID Partita", "numero_partita": "Numero Partita", "suffisso_partita": "Suffisso",
            "stato": "Stato", "data_impianto": "Data Impianto", "num_possessori": "Num. Possessori",
            "num_immobili": "Num. Immobili"
        },
        "Elenco Immobili": {
            "id_immobile": "ID Immobile", "natura": "Natura", "classificazione": "Classificazione",
            "localita_nome": "Località", "numero_partita": "Numero Partita", "comune_nome": "Comune"
        },
        "Elenco Località": {
            "id": "ID Località", "nome": "Nome", "tipo": "Tipo", "civico": "Civico", "comune_nome": "Comune"
        },
        "Elenco Variazioni": {
            "variazione_id": "ID Variazione", "tipo_variazione": "Tipo Variazione", "data_variazione": "Data",
            "partita_origine_numero": "Partita Origine", "partita_origine_comune": "Comune Origine",
            "partita_dest_numero": "Partita Destinazione", "partita_dest_comune": "Comune Destinazione",
            "tipo_contratto": "Tipo Contratto", "notaio": "Notaio"
        }
    }

    def __init__(self, db_manager: CatastoDBManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self._initUI()


    def _initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        selection_group = QGroupBox("Selezione Dati da Esportare")
        selection_layout = QFormLayout(selection_group)
        selection_layout.setSpacing(10)

        self.export_type_combo = QComboBox()
        self.export_type_combo.addItems([
            "Elenco Possessori", "Elenco Partite", "Elenco Immobili", "Elenco Località",
            "Elenco Variazioni", "Report Consistenza Patrimoniale" # <-- NUOVE OPZIONI
        ])
        selection_layout.addRow("Tipo di Esportazione:", self.export_type_combo)

        self.comune_filter_combo = QComboBox()
        selection_layout.addRow("Filtra per Comune (*):", self.comune_filter_combo)
        
        main_layout.addWidget(selection_group)

        format_group = QGroupBox("Formato di Esportazione")
        format_layout = QHBoxLayout(format_group)
        format_layout.setSpacing(10)
        format_layout.setContentsMargins(10, 10, 10, 10)
        self.btn_export_csv = QPushButton("Esporta in CSV")
        self.btn_export_csv.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.btn_export_csv.clicked.connect(self._handle_export_csv)
        format_layout.addWidget(self.btn_export_csv)
        
        # --- NUOVI PULSANTI ---
        self.btn_export_xls = QPushButton("Esporta in XLS (Excel)")
        self.btn_export_xls.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.btn_export_xls.clicked.connect(self._handle_export_xls)
        format_layout.addWidget(self.btn_export_xls)

        self.btn_export_pdf = QPushButton("Esporta in PDF")
        self.btn_export_pdf.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.btn_export_pdf.clicked.connect(self._handle_export_pdf)
        self.btn_export_pdf.setEnabled(FPDF_AVAILABLE)
        format_layout.addWidget(self.btn_export_pdf)

        self.btn_export_xlsx_completo = QPushButton("Archivio Completo (.xlsx)")
        self.btn_export_xlsx_completo.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.btn_export_xlsx_completo.setToolTip("Esporta partite, possessori, immobili e variazioni del comune in un unico file Excel multi-foglio")
        self.btn_export_xlsx_completo.clicked.connect(self._handle_export_xlsx_completo)
        format_layout.addWidget(self.btn_export_xlsx_completo)
        # --- FINE NUOVI PULSANTI ---

        format_layout.addStretch()
        main_layout.addWidget(format_group)

        self.status_log = QTextEdit()
        self.status_log.setReadOnly(True)
        
        # --- SEZIONE MODIFICATA: Log di stato ---
        # Sostituiamo QTextEdit con QTextBrowser per una gestione dei link più robusta
        self.status_log = QTextBrowser()
        self.status_log.setPlaceholderText("I messaggi di stato dell'esportazione appariranno qui...")
        
        # QTextBrowser è già di sola lettura di default, non serve setReadOnly(True)
        
        # Questo metodo ESISTE su QTextBrowser e ci dà il controllo sui click
        self.status_log.setOpenLinks(False)
        
        # Il segnale anchorClicked è garantito su QTextBrowser
        self.status_log.anchorClicked.connect(self._open_export_file_link)
        
        main_layout.addWidget(self.status_log, 1)

        self.setLayout(main_layout)
        # --- FINE SEZIONE MODIFICATA ---

        main_layout.addWidget(self.status_log, 1)

        self.setLayout(main_layout)

    # I metodi load_initial_data, _get_export_parameters, _fetch_data_for_export, _handle_export_csv
    # rimangono invariati rispetto alla versione precedente. Li includo per completezza.

    def _load_data_on_first_show(self):
        if self._data_loaded: return
        try:
            comuni = self.db_manager.get_elenco_comuni_semplice()
            self.comune_filter_combo.clear()
            # Rimuovo l'opzione "Tutti i Comuni" per ora, per semplicità
            self.comune_filter_combo.addItem("--- Seleziona un Comune ---", None)
            for id_comune, nome in comuni:
                self.comune_filter_combo.addItem(nome, id_comune)
            self._data_loaded = True
        except DBMError as e:
            QMessageBox.critical(self, "Errore Caricamento", f"Impossibile caricare l'elenco dei comuni:\n{e}")
    # In gui_widgets.py, nella classe EsportazioniWidget, SOSTITUISCI il metodo log_status

    def log_status(self, message: str, error: bool = False, link: Optional[str] = None):
        """
        Aggiunge un messaggio al log, con timestamp e formattazione opzionale
        per errori e link cliccabili.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Costruisce il messaggio base
        log_message = f"[{timestamp}] {message}"

        # Se è stato fornito un link, lo aggiunge come HTML
        if link and os.path.exists(link):
            file_url = QUrl.fromLocalFile(link).toString()
            base_name = os.path.basename(link)
            # Aggiunge il link cliccabile al messaggio
            log_message += f" -> <a href='{file_url}'>{base_name}</a>"

        # Applica il colore per gli errori o per i successi con link
        if error:
            # Usa il tag <font> per colorare il testo di rosso
            self.status_log.append(f"<font color='red'>{log_message}</font>")
        elif link:
            # Se c'è un link, coloriamo il testo di verde per indicare successo
            self.status_log.append(f"<font color='green'>{log_message}</font>")
        else:
            # Messaggio standard senza formattazione speciale
            self.status_log.append(log_message)

        # Scorri automaticamente verso il basso per mostrare l'ultimo messaggio
        self.status_log.verticalScrollBar().setValue(
            self.status_log.verticalScrollBar().maximum())

        # Forza l'aggiornamento della UI per mostrare il messaggio immediatamente
        QApplication.processEvents()

    def _get_export_parameters(self):
        export_type = self.export_type_combo.currentText()
        comune_id = self.comune_filter_combo.currentData()
        comune_name = self.comune_filter_combo.currentText()
        if export_type == "Report Consistenza Patrimoniale" and comune_id is None:
            QMessageBox.warning(self, "Selezione Mancante", "Il 'Report Consistenza Patrimoniale' richiede la selezione di un comune specifico.")
            return None, None, None
        elif comune_id is None:
            QMessageBox.warning(self, "Selezione Mancante", "Per favore, seleziona un comune.")
            return None, None, None

        return export_type, comune_id, comune_name

    def _fetch_data_for_export(self, export_type, comune_id):
        """Recupera i dati dal DB Manager in base al tipo di esportazione selezionato."""
        self.log_status(f"Recupero dati per '{export_type}' del comune ID {comune_id}...")
        QApplication.processEvents()

        if export_type == "Elenco Possessori":
            return self.db_manager.get_possessori_by_comune(comune_id)
        elif export_type == "Elenco Partite":
            return self.db_manager.get_partite_by_comune(comune_id)
        # --- INIZIO NUOVA LOGICA ---
        elif export_type == "Elenco Immobili":
            return self.db_manager.get_elenco_immobili_per_esportazione(comune_id)
        elif export_type == "Elenco Località":
            return self.db_manager.get_elenco_localita_per_esportazione(comune_id)
        elif export_type == "Elenco Variazioni":
            return self.db_manager.get_elenco_variazioni_per_esportazione(comune_id)
        elif export_type == "Report Consistenza Patrimoniale":
            return self.db_manager.get_report_consistenza_patrimoniale(comune_id)
        return None
    
# In gui_widgets.py, all'interno della classe EsportazioniWidget

    def _handle_export_csv(self):
        export_type, comune_id, comune_name = self._get_export_parameters()
        if not export_type: return

        data = self._fetch_data_for_export(export_type, comune_id)

        # Controllo fondamentale - deve essere il primo punto di uscita
        if not data:
            QMessageBox.warning(self, "Nessun Dato da Esportare",
                                "Non sono presenti dati da esportare in formato CSV. La query non ha restituito risultati.")
            self.logger.info("Tentativo di esportazione CSV fallito: nessun dato da esportare.")
            return

        # Gestione speciale per il Report Consistenza Patrimoniale che restituisce un dizionario
        if export_type == "Report Consistenza Patrimoniale":
            # Per questo report speciale, convertiamo il dizionario in una lista piatta
            flat_data = []
            for possessore_nome, partite_list in data.items():
                for partita in partite_list:
                    flat_row = {
                        'possessore_nome': possessore_nome,
                        'numero_partita': partita.get('numero_partita'),
                        'suffisso_partita': partita.get('suffisso_partita'),
                        'titolo': partita.get('titolo'),
                        'quota': partita.get('quota'),
                        'stato': partita.get('stato')
                    }
                    flat_data.append(flat_row)
            
            # Sostituiamo data con la versione appiattita
            data = flat_data
            
            # Header mapping specifico per questo report
            header_map = {
                'possessore_nome': 'Nome Possessore',
                'numero_partita': 'Numero Partita',
                'suffisso_partita': 'Suffisso',
                'titolo': 'Titolo',
                'quota': 'Quota',
                'stato': 'Stato'
            }
        else:
            # Per tutti gli altri tipi di export, usa il mapping esistente
            header_map = self.HEADER_MAPPINGS.get(export_type, {})

        # Ora data è garantito essere una lista di dizionari
        if not data:  # Controllo aggiuntivo dopo la conversione
            QMessageBox.warning(self, "Nessun Dato da Esportare",
                                "Non sono presenti dati da esportare.")
            return

        # Determina le chiavi ordinate e le intestazioni user-friendly
        ordered_keys = list(header_map.keys()) if header_map else list(data[0].keys())
        user_friendly_headers = list(header_map.values()) if header_map else ordered_keys

        type_slug = export_type.lower().replace(" ", "_")
        default_filename_base = f"{type_slug}_{comune_name.replace(' ', '_')}_{date.today().isoformat()}.csv"
        full_default_path = _get_default_export_path(default_filename_base)
        
        filename, _ = QFileDialog.getSaveFileName(self, f"Esporta {export_type} in CSV", full_default_path, "File CSV (*.csv)")
        if not filename: return

        try:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile, delimiter=';')
                writer.writerow(user_friendly_headers)
                # Scrive i dati accedendoli tramite le chiavi originali ordinate
                for row_dict in data:
                    writer.writerow([row_dict.get(key) for key in ordered_keys])
            
            self.log_status(f"Esportazione CSV completata con successo.", link=filename)
            QMessageBox.information(self, "Successo", f"{len(data)} record esportati con successo.")
            # --- Audit log export ---
            try:
                import os as _os
                win = QApplication.activeWindow()
                uid = getattr(win, 'logged_in_user_id', None)
                sid = getattr(win, 'current_session_id', None)
                self.db_manager.log_app_event(uid, sid, "export_csv",
                    {"filename": _os.path.basename(filename),
                     "tipo": export_type, "n_record": len(data)})
            except Exception:
                pass
        except Exception as e:
            self.logger.error(f"Errore durante l'esportazione CSV: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Esportazione", f"Impossibile salvare il file CSV:\n{e}")

    def _handle_export_xls(self):
        export_type, comune_id, comune_name = self._get_export_parameters()
        if not export_type: return
        # --- INIZIO LOGICA DEDICATA PER IL REPORT AVANZATO ---
        if export_type == "Report Consistenza Patrimoniale":
            self._export_consistenza_patrimoniale_xls(comune_id, comune_name)
            return
        # --- FINE LOGICA DEDICATA --
        data = self._fetch_data_for_export(export_type, comune_id)
        if not data:
            QMessageBox.information(self, "Nessun Dato", "Nessun dato trovato per l'esportazione.")
            return

        header_map = self.HEADER_MAPPINGS.get(export_type, {})

        type_slug = export_type.lower().replace(" ", "_")
        default_filename_base = f"{type_slug}_{comune_name.replace(' ', '_')}_{date.today().isoformat()}.xlsx"
        full_default_path = _get_default_export_path(default_filename_base)

        filename, _ = QFileDialog.getSaveFileName(self, f"Esporta {export_type} in Excel", full_default_path, "File Excel (*.xlsx)")
        if not filename: return
            
        try:
            df = pd.DataFrame(data)
            # Seleziona solo le colonne che abbiamo mappato, nell'ordine corretto
            if header_map:
                df = df[list(header_map.keys())]
            # Converte date objects in stringhe ISO (gestisce date pre-1900 non supportate da Excel)
            for col in df.columns:
                df[col] = df[col].apply(
                    lambda x: x.isoformat() if hasattr(x, 'isoformat') and not isinstance(x, str) else x)
            # Rinomina le colonne del DataFrame usando la nostra mappa
            df.rename(columns=header_map, inplace=True)

            df.to_excel(filename, index=False, engine='openpyxl')
            
            # Crea il link cliccabile per il log
            file_url = QUrl.fromLocalFile(filename).toString()
            base_name = os.path.basename(filename)
            success_message = f"<font color='green'>Esportazione Excel completata: <a href='{file_url}'>{base_name}</a></font>"
            self.status_log.append(success_message)
            QMessageBox.information(self, "Successo", f"{len(data)} record esportati con successo.")
            # --- Audit log export ---
            try:
                win = QApplication.activeWindow()
                uid = getattr(win, 'logged_in_user_id', None)
                sid = getattr(win, 'current_session_id', None)
                self.db_manager.log_app_event(uid, sid, "export_xlsx",
                    {"filename": os.path.basename(filename),
                     "tipo": export_type, "n_record": len(data)})
            except Exception:
                pass

        except ImportError:
            self.logger.error("La libreria 'pandas' o 'openpyxl' non è installata.")
            QMessageBox.critical(self, "Libreria Mancante", "L'esportazione in Excel richiede le librerie 'pandas' e 'openpyxl'.\nInstallale con il comando: pip install pandas openpyxl")
        except Exception as e:
            self.logger.error(f"Errore durante l'esportazione Excel di '{export_type}': {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Esportazione", f"Impossibile salvare il file Excel:\n{e}")

    def _handle_export_pdf(self):
        export_type, comune_id, comune_name = self._get_export_parameters()
        if not export_type: return
            # --- INIZIO MODIFICA: Gestione dedicata per il report speciale ---
        if export_type == "Report Consistenza Patrimoniale":
            self._export_consistenza_patrimoniale_pdf(comune_id, comune_name)
            return # Termina qui l'esecuzione per questo report
        # --- FINE MODIFICA ---
        data = self._fetch_data_for_export(export_type, comune_id)
        if not data:
            QMessageBox.information(self, "Nessun Dato", "Nessun dato trovato per l'esportazione.")
            return

        header_map = self.HEADER_MAPPINGS.get(export_type, {})
        ordered_keys = list(header_map.keys()) if header_map else list(data[0].keys())
        user_friendly_headers = list(header_map.values()) if header_map else ordered_keys

        type_slug = export_type.lower().replace(" ", "_")
        default_filename_base = f"{type_slug}_{comune_name.replace(' ', '_')}_{date.today().isoformat()}.pdf"
        full_default_path = _get_default_export_path(default_filename_base)
        
        filename, _ = QFileDialog.getSaveFileName(self, f"Esporta {export_type} in PDF", full_default_path, "File PDF (*.pdf)")
        if not filename: return

        try:
            pdf_title = f"{export_type} - Comune di {comune_name}"
            pdf = BulkReportPDF(report_title=pdf_title)
            pdf.alias_nb_pages()
            pdf.set_auto_page_break(auto=True, margin=15)
            
            
            # Trasforma i dati per la tabella PDF, usando le chiavi ordinate
            data_rows = [[str(row.get(key, '')) for key in ordered_keys] for row in data]
            
            pdf.print_table(user_friendly_headers, data_rows) # Usa le intestazioni "belle"
            pdf.output(filename)
            
            file_url = QUrl.fromLocalFile(filename).toString()
            base_name = os.path.basename(filename)
            success_message = f"<font color='green'>Esportazione PDF completata: <a href='{file_url}'>{base_name}</a></font>"
            self.status_log.append(success_message)
            QMessageBox.information(self, "Successo", f"{len(data)} record esportati con successo.")
        except Exception as e:
            self.logger.error(f"Errore durante l'esportazione PDF di '{export_type}': {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Esportazione", f"Impossibile salvare il file PDF:\n{e}")
    def _handle_export_xlsx_completo(self):
        """Esporta partite, possessori, immobili e variazioni in un unico .xlsx multi-foglio."""
        comune_id = self.comune_filter_combo.currentData()
        comune_name = self.comune_filter_combo.currentText()
        if comune_id is None:
            QMessageBox.warning(self, "Comune Non Selezionato",
                                "Seleziona un comune prima di esportare l'archivio completo.")
            return

        default_filename = f"archivio_completo_{comune_name.replace(' ', '_')}_{date.today().isoformat()}.xlsx"
        filename, _ = QFileDialog.getSaveFileName(
            self, "Salva Archivio Completo Excel",
            _get_default_export_path(default_filename),
            "File Excel (*.xlsx)"
        )
        if not filename:
            return

        fogli = [
            ("Partite",     "Elenco Partite",     lambda: self.db_manager.get_partite_by_comune(comune_id)),
            ("Possessori",  "Elenco Possessori",  lambda: self.db_manager.get_possessori_by_comune(comune_id)),
            ("Immobili",    "Elenco Immobili",    lambda: self.db_manager.get_elenco_immobili_per_esportazione(comune_id)),
            ("Variazioni",  "Elenco Variazioni",  lambda: self.db_manager.get_elenco_variazioni_per_esportazione(comune_id)),
        ]

        try:
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                totali = []
                for sheet_name, export_type, fetch_fn in fogli:
                    self.log_status(f"Recupero {sheet_name}...")
                    QApplication.processEvents()
                    data = fetch_fn()
                    if not data:
                        self.log_status(f"  → Nessun dato per {sheet_name}, foglio vuoto inserito.")
                        pd.DataFrame().to_excel(writer, sheet_name=sheet_name, index=False)
                        totali.append((sheet_name, 0))
                        continue
                    header_map = self.HEADER_MAPPINGS.get(export_type, {})
                    df = pd.DataFrame(data)
                    if header_map:
                        cols_presenti = [c for c in header_map.keys() if c in df.columns]
                        df = df[cols_presenti].rename(columns=header_map)
                    for col in df.columns:
                        df[col] = df[col].apply(
                            lambda x: x.isoformat() if hasattr(x, 'isoformat') and not isinstance(x, str) else x)
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    totali.append((sheet_name, len(df)))

            riepilogo = ", ".join(f"{n}: {t}" for n, t in totali)
            self.log_status(f"Archivio completo esportato ({riepilogo}).", link=filename)
            QMessageBox.information(self, "Successo",
                                    f"File Excel multi-foglio creato con successo.\n{riepilogo}")
        except ImportError:
            QMessageBox.critical(self, "Libreria Mancante",
                                 "L'esportazione richiede 'pandas' e 'openpyxl'.\n"
                                 "Installa con: pip install pandas openpyxl")
        except Exception as e:
            self.logger.error(f"Errore export archivio completo: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Esportazione", f"Impossibile salvare il file:\n{e}")

    def _export_consistenza_patrimoniale_xls(self, comune_id: int, comune_name: str):
        """Logica di esportazione specifica per il report di consistenza patrimoniale."""
        self.log_status("Recupero dati per Report Consistenza Patrimoniale...")
        QApplication.processEvents()

        try:
            report_data = self._fetch_data_for_export("Report Consistenza Patrimoniale", comune_id)
            if not report_data:
                QMessageBox.information(self, "Nessun Dato", f"Nessun possessore con proprietà trovato per il comune di {comune_name}.")
                return

            default_filename = f"report_consistenza_{comune_name.replace(' ', '_')}_{date.today()}.xlsx"
            filename, _ = QFileDialog.getSaveFileName(self, "Salva Report Excel", default_filename, "File Excel (*.xlsx)")
            if not filename: return

            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                for possessore_nome, partite_list in report_data.items():
                    # Tronca il nome del foglio se troppo lungo per Excel (max 31 caratteri)
                    sheet_name = possessore_nome.replace('[', '').replace(']', '').replace('*', '').replace(':', '').replace('?', '/').replace('\\', '')
                    sheet_name = sheet_name[:31]

                    df = pd.DataFrame(partite_list)
                    df.to_excel(writer, sheet_name=sheet_name, index=False)

            self.log_status(f"Report Consistenza Patrimoniale per {comune_name} esportato con successo.", link=filename)
        except Exception as e:
            self.log_status(f"Errore durante l'esportazione del report di consistenza: {e}", error=True)
            QMessageBox.critical(self, "Errore Esportazione", f"Impossibile creare il file Excel:\n{e}")
    # In gui_widgets.py, aggiungi questo metodo alla classe EsportazioniWidget

    def _export_consistenza_patrimoniale_pdf(self, comune_id: int, comune_name: str):
        """Logica di esportazione specifica per il PDF del report di consistenza patrimoniale."""
        self.log_status("Recupero dati per Report Consistenza Patrimoniale (PDF)...")
        QApplication.processEvents()

        try:
            report_data = self._fetch_data_for_export("Report Consistenza Patrimoniale", comune_id)
            if not report_data:
                QMessageBox.information(self, "Nessun Dato", f"Nessun possessore con proprietà trovato per il comune di {comune_name}.")
                return

            default_filename = f"report_consistenza_{comune_name.replace(' ', '_')}_{date.today()}.pdf"
            full_default_path = _get_default_export_path(default_filename)
            filename, _ = QFileDialog.getSaveFileName(self, "Salva Report PDF", full_default_path, "File PDF (*.pdf)")
            if not filename: return

            pdf = BulkReportPDF(report_title=f"Report Consistenza Patrimoniale - Comune di {comune_name}")
            pdf.alias_nb_pages()
            pdf.add_page()

            # --- INIZIO LOGICA DI RENDERIZZAZIONE CORRETTA ---
            for possessore_nome, partite_list in report_data.items():
                pdf.set_font('Helvetica', 'B', 14)
                # Usiamo multi_cell per il nome del possessore nel caso sia molto lungo
                pdf.multi_cell(0, 8, f"Possessore: {possessore_nome}", border='B', align='L')
                pdf.ln(5) # Spazio dopo il nome del possessore

                for partita in partite_list:
                    # Intestazione della Partita
                    pdf.set_font('Helvetica', 'B', 11)
                    suffisso = f" (suffisso: {partita.get('suffisso_partita')})" if partita.get('suffisso_partita') else ""
                    # Indentiamo leggermente l'intestazione della partita
                    pdf.set_x(pdf.l_margin + 5)
                    pdf.cell(0, 6, f"- Partita N. {partita.get('numero_partita')}{suffisso}", ln=True)

                    # Dettagli della Partita
                    pdf.set_font('Helvetica', '', 10)

                    # Usiamo celle separate e indentate per ogni dettaglio per un controllo migliore
                    pdf.set_x(pdf.l_margin + 10) # Indentazione maggiore per i dettagli
                    pdf.cell(0, 5, f"Titolo: {partita.get('titolo', 'N/D')}", ln=True)

                    pdf.set_x(pdf.l_margin + 10)
                    pdf.cell(0, 5, f"Quota: {partita.get('quota') or 'N/A'}", ln=True)

                    pdf.set_x(pdf.l_margin + 10)
                    pdf.cell(0, 5, f"Stato: {partita.get('stato', 'N/D')}", ln=True)

                    pdf.ln(3) # Aggiunge un piccolo spazio prima della prossima partita

                pdf.ln(7) # Aggiunge uno spazio più grande tra un possessore e l'altro

            # --- FINE LOGICA DI RENDERIZZAZIONE CORRETTA ---
            pdf.output(filename)
            self.log_status(f"Report PDF per {comune_name} esportato con successo.", link=filename)

        except Exception as e:
            self.log_status(f"Errore durante l'esportazione del report PDF: {e}", error=True)
            QMessageBox.critical(self, "Errore Esportazione", f"Impossibile creare il file PDF:\n{e}")


    
    def _open_export_file_link(self, url: QUrl):
        """Apre il file locale puntato dall'URL cliccato nel log."""
        self.logger.info(f"Tentativo di aprire il file dal link: {url.toLocalFile()}")
        QDesktopServices.openUrl(url)
    def _on_export_type_changed(self, text):
        """Disabilita "Tutti i Comuni" se viene scelto un report che lo richiede."""
        if text == "Report Consistenza Patrimoniale":
            if self.comune_filter_combo.itemText(0) == "Tutti i Comuni":
                self.comune_filter_combo.removeItem(0)
        elif self.comune_filter_combo.itemText(0) != "Tutti i Comuni":
            self.comune_filter_combo.insertItem(0, "Tutti i Comuni", None)


class ReportisticaWidget(LazyLoadedWidget):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_report_content = ""  # Memorizza il report corrente
        self._initUI()

    def _initUI(self):
        main_layout = QVBoxLayout(self)

        # Contenitore principale per tutti i controlli di generazione report
        generation_group = QGroupBox("Seleziona il Report da Generare")
        generation_layout = QVBoxLayout(generation_group)

        # Creiamo il QTabWidget interno con un nome coerente
        self.tabs_report_specifici = QTabWidget()

        # Creazione e aggiunta dei sotto-tab
        self.tabs_report_specifici.addTab(self._create_report_proprieta_tab(), "Proprietà")
        self.tabs_report_specifici.addTab(self._create_report_genealogico_tab(), "Genealogico")
        self.tabs_report_specifici.addTab(self._create_report_possessore_tab(), "Possessore")
        self.tabs_report_specifici.addTab(self._create_report_consultazioni_tab(), "Consultazioni")

        generation_layout.addWidget(self.tabs_report_specifici)
        main_layout.addWidget(generation_group)

        # Area di output per i report e log esportazioni
        output_group = QGroupBox("Anteprima Report e Log Esportazioni")
        output_layout = QVBoxLayout(output_group)
        self.report_output_browser = QTextBrowser()
        self.report_output_browser.setOpenLinks(False)
        # --- INIZIO CORREZIONE ---
        # Collega il segnale al nuovo metodo corretto
        self.report_output_browser.anchorClicked.connect(self._open_export_file_link)
        # --- FINE CORREZIONE ---
        self.report_output_browser.setPlaceholderText("L'anteprima del report generato apparirà qui.")
        output_layout.addWidget(self.report_output_browser)

        export_buttons_layout = QHBoxLayout()
        self.export_txt_button = QPushButton("Esporta come TXT"); self.export_txt_button.clicked.connect(self._export_current_report_txt)
        self.export_pdf_button = QPushButton("Esporta come PDF"); self.export_pdf_button.clicked.connect(self._export_current_report_pdf); self.export_pdf_button.setEnabled(FPDF_AVAILABLE)
        self.export_odt_button = QPushButton("Esporta come ODT"); self.export_odt_button.clicked.connect(self._export_current_report_odt)
        self.export_odt_button.setToolTip("Esporta il report in formato ODT (LibreOffice Writer)")
        export_buttons_layout.addStretch()
        export_buttons_layout.addWidget(self.export_txt_button)
        export_buttons_layout.addWidget(self.export_pdf_button)
        export_buttons_layout.addWidget(self.export_odt_button)
        output_layout.addLayout(export_buttons_layout)

        main_layout.addWidget(output_group, 1)

    # --- Metodi per creare i singoli sotto-tab ---

    def _create_report_proprieta_tab(self) -> QWidget:
        widget = QWidget(); layout = QFormLayout(widget)
        select_layout = QHBoxLayout()
        self.partita_id_edit = QSpinBox(); self.partita_id_edit.setRange(1, 9999999)
        self.search_partita_prop_button = QPushButton("Cerca..."); self.search_partita_prop_button.clicked.connect(self.search_partita_prop)
        select_layout.addWidget(self.partita_id_edit); select_layout.addWidget(self.search_partita_prop_button)
        layout.addRow("ID Partita (*):", select_layout)
        self.partita_info_label_prop = QLabel("Nessuna partita selezionata."); layout.addRow(self.partita_info_label_prop)
        self.generate_cert_button = QPushButton("Genera Report Proprietà"); self.generate_cert_button.clicked.connect(self.generate_report_proprieta)
        layout.addRow(self.generate_cert_button)
        return widget

    def _create_report_genealogico_tab(self) -> QWidget:
        widget = QWidget(); layout = QFormLayout(widget)
        select_layout = QHBoxLayout()
        self.partita_id_gen_edit = QSpinBox(); self.partita_id_gen_edit.setRange(1, 9999999)
        self.search_partita_gen_button = QPushButton("Cerca..."); self.search_partita_gen_button.clicked.connect(self.search_partita_gen)
        select_layout.addWidget(self.partita_id_gen_edit); select_layout.addWidget(self.search_partita_gen_button)
        layout.addRow("ID Partita A (*):", select_layout)
        self.partita_info_label_gen = QLabel("Nessuna partita selezionata."); layout.addRow(self.partita_info_label_gen)
        self.generate_gen_button = QPushButton("Genera Report Genealogico"); self.generate_gen_button.clicked.connect(self.generate_genealogico)
        self.albero_gen_button = QPushButton("Visualizza Albero Genealogico"); self.albero_gen_button.clicked.connect(self._apri_albero_genealogico)
        gen_buttons_layout = QHBoxLayout()
        gen_buttons_layout.addWidget(self.generate_gen_button)
        gen_buttons_layout.addWidget(self.albero_gen_button)
        layout.addRow(gen_buttons_layout)

        # --- Confronto versioni ---
        layout.addRow(QLabel(""))  # spaziatore
        confronto_label = QLabel("<b>Confronto tra due partite</b>"); layout.addRow(confronto_label)
        select_b_layout = QHBoxLayout()
        self.partita_id_gen_b_edit = QSpinBox(); self.partita_id_gen_b_edit.setRange(1, 9999999)
        select_b_layout.addWidget(self.partita_id_gen_b_edit)
        layout.addRow("ID Partita B (*):", select_b_layout)
        self.confronta_button = QPushButton("Confronta Partite (Diff Visuale)")
        self.confronta_button.clicked.connect(self._apri_confronto_partite)
        layout.addRow(self.confronta_button)
        return widget

    def _create_report_possessore_tab(self) -> QWidget:
        widget = QWidget(); layout = QFormLayout(widget)
        select_layout = QHBoxLayout()
        self.possessore_id_edit = QSpinBox(); self.possessore_id_edit.setRange(1, 9999999)
        self.search_possessore_button = QPushButton("Cerca..."); self.search_possessore_button.clicked.connect(self.search_possessore)
        select_layout.addWidget(self.possessore_id_edit); select_layout.addWidget(self.search_possessore_button)
        layout.addRow("ID Possessore (*):", select_layout)
        self.generate_pos_button = QPushButton("Genera Report Possessore"); self.generate_pos_button.clicked.connect(self.generate_possessore)
        layout.addRow(self.generate_pos_button)
        return widget

    def _create_report_consultazioni_tab(self) -> QWidget:
        widget = QWidget(); layout = QFormLayout(widget)
        self.consult_data_inizio_edit = QDateEdit(calendarPopup=True); self.consult_data_inizio_edit.setDate(QDate.currentDate().addMonths(-1))
        self.consult_data_fine_edit = QDateEdit(calendarPopup=True); self.consult_data_fine_edit.setDate(QDate.currentDate())
        self.consult_richiedente_edit = QLineEdit(); self.consult_richiedente_edit.setPlaceholderText("Lascia vuoto per tutti")
        layout.addRow("Data Inizio:", self.consult_data_inizio_edit)
        layout.addRow("Data Fine:", self.consult_data_fine_edit)
        layout.addRow("Richiedente (contiene):", self.consult_richiedente_edit)
        self.generate_consult_button = QPushButton("Genera Report Consultazioni"); self.generate_consult_button.clicked.connect(self.generate_report_consultazioni)
        layout.addRow(self.generate_consult_button)
        return widget
    
    def generate_report_consultazioni(self):
        data_inizio = self.consult_data_inizio_edit.date().toPyDate()
        data_fine = self.consult_data_fine_edit.date().toPyDate()
        richiedente = self.consult_richiedente_edit.text().strip() or None

        try:
            report_text = self.db_manager.genera_report_consultazioni(data_inizio, data_fine, richiedente)
            self.current_report_content = report_text or "Nessuna consultazione trovata per i criteri specificati."
            self.report_output_browser.setPlainText(self.current_report_content)
        except DBMError as e:
            QMessageBox.critical(self, "Errore Report", f"Impossibile generare il report delle consultazioni:\n{e}")
    def _update_partita_info_label(self, label_widget, partita_id):
        """Aggiorna una label con i dettagli (numero, suffisso, comune) di una partita."""
        if partita_id is None:
            label_widget.setText("Nessuna partita selezionata.")
            return
        
        details = self.db_manager.get_partita_details(partita_id)
        if details:
            suffisso_str = f"(Suffisso: {details.get('suffisso_partita')})" if details.get('suffisso_partita') else "(Nessun Suffisso)"
            label_widget.setText(f"Selezionata: N. {details.get('numero_partita')} {suffisso_str} - Comune: {details.get('comune_nome')}")
        else:
            label_widget.setText(f"<font color='red'>Partita ID {partita_id} non trovata.</font>")

    def search_partita_prop(self):
        dialog = PartitaSearchDialog(self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_partita_id:
            self.partita_id_edit.setValue(dialog.selected_partita_id)
            self._update_partita_info_label(self.partita_info_label_prop, dialog.selected_partita_id)

    def search_partita_gen(self):
        dialog = PartitaSearchDialog(self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_partita_id:
            self.partita_id_gen_edit.setValue(dialog.selected_partita_id)
            self._update_partita_info_label(self.partita_info_label_gen, dialog.selected_partita_id)

    def search_possessore(self):
        dialog = PossessoreSelectionDialog(db_manager=self.db_manager, comune_id=None, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_possessore:
            self.possessore_id_edit.setValue(dialog.selected_possessore.get('id', 0))

    def generate_report_proprieta(self):
        partita_id = self.partita_id_edit.value()
        if partita_id <= 0: return QMessageBox.warning(self, "Errore", "Selezionare un ID partita valido.")

        report_text = self.db_manager.genera_report_proprieta(partita_id)
        # --- INIZIO CORREZIONE ---
        self.current_report_content = report_text or f"Nessun report generato per la partita ID {partita_id}."

        # 1. Pulisci completamente il widget
        self.report_output_browser.clear()
        # 2. Imposta il nuovo contenuto come testo semplice
        self.report_output_browser.setPlainText(self.current_report_content)
        # --- FINE CORREZIONE ---

    def generate_genealogico(self):
        partita_id = self.partita_id_gen_edit.value()
        if partita_id <= 0: return QMessageBox.warning(self, "Errore", "Selezionare un ID partita valido.")

        report_text = self.db_manager.genera_report_genealogico(partita_id)
        self.current_report_content = report_text or f"Nessun report generato per la partita ID {partita_id}."

        # 1. Pulisci completamente il widget
        self.report_output_browser.clear()
        # 2. Imposta il nuovo contenuto come testo semplice
        self.report_output_browser.setPlainText(self.current_report_content)
        # --- FINE CORREZIONE ---

    def _apri_albero_genealogico(self):
        partita_id = self.partita_id_gen_edit.value()
        if partita_id <= 0:
            QMessageBox.warning(self, "ID Non Valido", "Selezionare un ID partita valido.")
            return
        AlberoGeneralogicoDialog(partita_id, self.db_manager, self).exec()

    def _apri_confronto_partite(self):
        id_a = self.partita_id_gen_edit.value()
        id_b = self.partita_id_gen_b_edit.value()
        if id_a <= 0 or id_b <= 0:
            QMessageBox.warning(self, "ID Non Valido", "Inserire ID validi per entrambe le partite.")
            return
        ConfrontoPartiteDialog(self.db_manager, id_a, id_b, self).exec()

    def generate_possessore(self):
        possessore_id = self.possessore_id_edit.value()
        if possessore_id <= 0: return QMessageBox.warning(self, "Errore", "Selezionare un ID possessore valido.")

        report_text = self.db_manager.genera_report_possessore(possessore_id)
        self.current_report_content = report_text or f"Nessun report generato per il possessore ID {possessore_id}."

        # 1. Pulisci completamente il widget
        self.report_output_browser.clear()
        # 2. Imposta il nuovo contenuto come testo semplice
        self.report_output_browser.setPlainText(self.current_report_content)
        # --- FINE CORREZIONE ---

    # In gui_widgets.py, nella classe ReportisticaWidget

    def _export_current_report_txt(self):
        if not self.current_report_content.strip():
            QMessageBox.warning(self, "Nessun Contenuto", "Generare un report prima di esportarlo.")
            return

        default_filename_base = f"report_catasto_{date.today().isoformat()}.txt"
        full_default_path = _get_default_export_path(default_filename_base)

        filename, _ = QFileDialog.getSaveFileName(self, "Salva Report TXT", full_default_path, "File di testo (*.txt)")
        if not filename: return

        # Gestione migliorata degli errori
        max_attempts = 3
        attempt = 0
        
        while attempt < max_attempts:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.current_report_content)
                
                # Se arriviamo qui, il file è stato salvato con successo
                self.report_output_browser.clear()
                self.report_output_browser.setPlainText(self.current_report_content)
                
                file_url = QUrl.fromLocalFile(filename).toString()
                base_name = os.path.basename(filename)
                link_html = f"<hr><p style='color:green;'>Report esportato con successo: <a href='{file_url}'>{base_name}</a></p>"
                self.report_output_browser.append(link_html)
                
                # Chiedi se aprire il file
                reply = QMessageBox.question(
                    self, 
                    "File Salvato", 
                    f"Report salvato con successo!\n\nVuoi aprire il file ora?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    QDesktopServices.openUrl(QUrl.fromLocalFile(filename))
                
                break  # Esci dal loop se tutto è andato bene
                
            except PermissionError as e:
                attempt += 1
                if attempt >= max_attempts:
                    QMessageBox.critical(
                        self, 
                        "Errore di Accesso al File",
                        f"Impossibile salvare il file '{base_name}'.\n\n"
                        f"Il file potrebbe essere aperto in un altro programma.\n"
                        f"Chiudi il file e riprova.\n\n"
                        f"Dettagli errore: {str(e)}"
                    )
                else:
                    # Proponi un nome alternativo
                    base, ext = os.path.splitext(filename)
                    timestamp = datetime.now().strftime("%H%M%S")
                    new_filename = f"{base}_{timestamp}{ext}"
                    
                    reply = QMessageBox.question(
                        self,
                        "File in Uso",
                        f"Il file '{base_name}' sembra essere in uso.\n\n"
                        f"Vuoi salvare con un nome diverso?\n"
                        f"Nuovo nome proposto: {os.path.basename(new_filename)}",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
                    )
                    
                    if reply == QMessageBox.StandardButton.Yes:
                        filename = new_filename
                    elif reply == QMessageBox.StandardButton.No:
                        # Riprova con lo stesso nome
                        QMessageBox.information(
                            self,
                            "Suggerimento",
                            "Chiudi il file nel programma che lo sta utilizzando e premi OK."
                        )
                    else:
                        # Cancel
                        break
                        
            except IOError as e:
                QMessageBox.critical(
                    self, 
                    "Errore di Scrittura",
                    f"Errore durante il salvataggio del file:\n{str(e)}\n\n"
                    f"Verifica di avere i permessi di scrittura nella cartella selezionata."
                )
                break
                
            except Exception as e:
                QMessageBox.critical(
                    self, 
                    "Errore Imprevisto",
                    f"Si è verificato un errore inatteso:\n{str(e)}"
                )
                break

    def _export_current_report_pdf(self):
        if not self.current_report_content.strip():
            QMessageBox.warning(self, "Nessun Contenuto", "Generare un report prima di esportarlo.")
            return

        default_filename_base = f"report_catasto_{date.today().isoformat()}.pdf"
        full_default_path = _get_default_export_path(default_filename_base)

        filename, _ = QFileDialog.getSaveFileName(self, "Salva Report PDF", full_default_path, "File PDF (*.pdf)")
        if not filename: return

        # Progress dialog per PDF (può richiedere tempo)
        progress = QProgressDialog("Generazione PDF in corso...", "Annulla", 0, 100, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(10)
        
        max_attempts = 3
        attempt = 0
        
        while attempt < max_attempts:
            try:
                if progress.wasCanceled():
                    break
                    
                progress.setValue(30)
                pdf = GenericTextReportPDF(report_title="Report Catasto Storico")
                
                progress.setValue(50)
                pdf.add_page()
                pdf.add_report_text(self.current_report_content)
                
                progress.setValue(80)
                pdf.output(filename)
                
                progress.setValue(100)
                
                # Successo
                self.report_output_browser.clear()
                self.report_output_browser.setPlainText(self.current_report_content)
                
                file_url = QUrl.fromLocalFile(filename).toString()
                base_name = os.path.basename(filename)
                link_html = f"<hr><p style='color:green;'>Report PDF esportato: <a href='{file_url}'>{base_name}</a></p>"
                self.report_output_browser.append(link_html)
                
                # Chiedi se aprire il file
                reply = QMessageBox.question(
                    self, 
                    "PDF Creato", 
                    f"PDF creato con successo!\n\nVuoi aprire il file ora?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    QDesktopServices.openUrl(QUrl.fromLocalFile(filename))
                    
                break
                
            except PermissionError:
                attempt += 1
                base_name = os.path.basename(filename)
                
                if attempt >= max_attempts:
                    QMessageBox.critical(
                        self, 
                        "Errore di Accesso al File PDF",
                        f"Impossibile salvare il file '{base_name}'.\n\n"
                        f"Il file PDF potrebbe essere aperto in un lettore PDF.\n"
                        f"Chiudi il file e riprova."
                    )
                else:
                    # Proponi nome alternativo
                    base, ext = os.path.splitext(filename)
                    timestamp = datetime.now().strftime("%H%M%S")
                    new_filename = f"{base}_{timestamp}{ext}"
                    
                    reply = QMessageBox.warning(
                        self,
                        "PDF in Uso",
                        f"Il file '{base_name}' è aperto in un altro programma.\n\n"
                        f"Opzioni:\n"
                        f"• Salvare con nome: {os.path.basename(new_filename)}\n"
                        f"• Chiudere il PDF e riprovare\n"
                        f"• Annullare l'operazione",
                        QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Retry | QMessageBox.StandardButton.Cancel,
                        QMessageBox.StandardButton.Save
                    )
                    
                    if reply == QMessageBox.StandardButton.Save:
                        filename = new_filename
                    elif reply == QMessageBox.StandardButton.Retry:
                        continue
                    else:
                        break
                        
            except Exception as e:
                QMessageBox.critical(
                    self, 
                    "Errore Generazione PDF",
                    f"Impossibile generare il PDF:\n{str(e)}"
                )
                break
            finally:
                progress.close()    
    def _export_current_report_odt(self):
        """Esporta il report corrente in formato ODT (LibreOffice Writer)."""
        if not self.current_report_content.strip():
            QMessageBox.warning(self, "Nessun Contenuto", "Generare un report prima di esportarlo.")
            return
        default_filename_base = f"report_catasto_{date.today().isoformat()}.odt"
        full_default_path = _get_default_export_path(default_filename_base)
        filename, _ = QFileDialog.getSaveFileName(
            self, "Salva Report ODT", full_default_path, "File ODT (*.odt)"
        )
        if not filename:
            return
        try:
            from odf.opendocument import OpenDocumentText
            from odf.text import P, H
            from odf.style import Style, TextProperties, ParagraphProperties

            doc = OpenDocumentText()

            # Stile titolo
            s_title = Style(name="Titolo", family="paragraph")
            s_title.addElement(TextProperties(fontsize="16pt", fontweight="bold"))
            s_title.addElement(ParagraphProperties(marginbottom="6pt"))
            doc.styles.addElement(s_title)

            # Stile corpo
            s_body = Style(name="Corpo", family="paragraph")
            s_body.addElement(TextProperties(fontsize="10pt"))
            doc.styles.addElement(s_body)

            # Titolo documento
            doc.text.addElement(H(outlinelevel=1, stylename="Titolo",
                                  text="Report Catasto Storico"))

            # Contenuto testo (riga per riga)
            for line in self.current_report_content.splitlines():
                doc.text.addElement(P(stylename="Corpo", text=line if line else " "))

            doc.save(filename)

            file_url = QUrl.fromLocalFile(filename).toString()
            base_name = os.path.basename(filename)
            self.report_output_browser.append(
                f"<p style='color:green;'>Report ODT esportato: "
                f"<a href='{file_url}'>{base_name}</a></p>"
            )
            QMessageBox.information(self, "Successo", f"File ODT creato:\n{filename}")
        except ImportError:
            QMessageBox.critical(self, "Libreria Mancante",
                                 "La libreria 'odfpy' non è installata.\n"
                                 "Installa con: pip install odfpy")
        except Exception as e:
            self.logger.error(f"Errore export ODT: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Esportazione ODT", f"Impossibile salvare il file:\n{e}")

    def _open_export_file_link(self, url: QUrl):
        """Apre il file locale puntato dall'URL cliccato nel log."""
        self.logger.info(f"Tentativo di aprire il file dal link: {url.toLocalFile()}")
        # QDesktopServices è il modo corretto e multipiattaforma per aprire file e URL
        if not QDesktopServices.openUrl(url):
            QMessageBox.warning(self, "Errore Apertura", f"Impossibile aprire il link:\n{url.toString()}")


class StatisticheWidget(LazyLoadedWidget):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)  # Chiama il costruttore della classe base
        self.db_manager = db_manager
        self.comune_filter_id = None
        # Il self.logger e self._data_loaded sono già gestiti da LazyLoadedWidget

        self._initUI()

    def _initUI(self):
        """Crea l'interfaccia utente, riorganizzata per maggiore chiarezza."""
        main_layout = QVBoxLayout(self)
        
        # Tab principale per separare Statistiche da Manutenzione
        self.main_tabs = QTabWidget()
        main_layout.addWidget(self.main_tabs)

        # --- Contenitore per il tab Statistiche ---
        stats_container_widget = QWidget()
        stats_container_layout = QVBoxLayout(stats_container_widget)
        
        # Sotto-tab per i diversi tipi di statistiche
        stats_sub_tabs = QTabWidget()
        stats_container_layout.addWidget(stats_sub_tabs)
        
        # --- Aggiunta dei tab statistici al sotto-tab ---
        stats_comune_tab = self._create_stats_comune_tab()
        stats_sub_tabs.addTab(stats_comune_tab, "Statistiche per Comune")
        
        immobili_tab = self._create_immobili_tipologia_tab()
        stats_sub_tabs.addTab(immobili_tab, "Immobili per Tipologia")

        grafici_tab = self._create_grafici_tab()
        stats_sub_tabs.addTab(grafici_tab, "Grafici")

        # --- Contenitore per il tab Manutenzione ---
        maintenance_tab = self._create_maintenance_tab()

        # Aggiunta dei tab principali
        self.main_tabs.addTab(stats_container_widget, "📊 Statistiche")
        self.main_tabs.addTab(maintenance_tab, "🔧 Manutenzione Database")
        
    def _create_stats_comune_tab(self):
        """Crea il widget per il tab 'Statistiche per Comune'."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        refresh_button = QPushButton("Aggiorna Statistiche Comuni")
        refresh_button.clicked.connect(self.refresh_stats_comune)
        self.stats_comune_table = QTableWidget()
        self.stats_comune_table.setColumnCount(7)
        self.stats_comune_table.setHorizontalHeaderLabels(["Comune", "Provincia", "Totale Partite", "Partite Attive", "Partite Inattive", "Totale Possessori", "Totale Immobili"])
        self.stats_comune_table.setAlternatingRowColors(True)
        self.stats_comune_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.stats_comune_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.stats_comune_table.customContextMenuRequested.connect(self._apri_menu_stats_comune)
        layout.addWidget(refresh_button)
        layout.addWidget(self.stats_comune_table)
        return widget

    def _create_immobili_tipologia_tab(self):
        """Crea il widget per il tab 'Immobili per Tipologia'."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        filter_layout = QHBoxLayout()
        self.comune_filter_button = QPushButton("Filtra per Comune...")
        self.comune_filter_button.clicked.connect(self.filter_immobili_per_comune)
        self.comune_filter_display = QLabel("Visualizzando tutti i comuni")
        self.clear_filter_button = QPushButton("Rimuovi Filtro")
        self.clear_filter_button.clicked.connect(self.clear_immobili_filter)
        filter_layout.addWidget(self.comune_filter_button)
        filter_layout.addWidget(self.comune_filter_display)
        filter_layout.addWidget(self.clear_filter_button)
        layout.addLayout(filter_layout)
        refresh_button = QPushButton("Aggiorna Statistiche Immobili")
        refresh_button.clicked.connect(self.refresh_immobili_tipologia)
        layout.addWidget(refresh_button)
        self.immobili_table = QTableWidget()
        self.immobili_table.setColumnCount(6)
        self.immobili_table.setHorizontalHeaderLabels(["Comune", "Classificazione", "Numero Immobili", "Totale Piani", "Totale Vani", "Media Vani/Immobile"])
        self.immobili_table.setAlternatingRowColors(True)
        self.immobili_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.immobili_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.immobili_table.customContextMenuRequested.connect(self._apri_menu_immobili_stats)
        layout.addWidget(self.immobili_table)
        return widget

    def _create_grafici_tab(self):
        """Crea il tab con grafici statistici via matplotlib."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        try:
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
            from matplotlib.figure import Figure
            import matplotlib
            matplotlib.use('QtAgg')

            btn_aggiorna = QPushButton("Aggiorna Grafici")
            btn_aggiorna.clicked.connect(self._aggiorna_grafici)
            layout.addWidget(btn_aggiorna)

            # Figura matplotlib con 3 assi
            self._fig = Figure(figsize=(10, 8), tight_layout=True)
            self._ax_partite = self._fig.add_subplot(2, 2, 1)
            self._ax_stato   = self._fig.add_subplot(2, 2, 2)
            self._ax_variaz  = self._fig.add_subplot(2, 1, 2)
            self._canvas = FigureCanvas(self._fig)
            layout.addWidget(self._canvas, 1)
            self._matplotlib_ok = True
        except Exception as e:
            self._matplotlib_ok = False
            lbl = QLabel(f"Grafici non disponibili: {e}\n\nInstalla matplotlib: pip install matplotlib")
            lbl.setWordWrap(True)
            layout.addWidget(lbl)

        return widget

    def _aggiorna_grafici(self):
        if not getattr(self, '_matplotlib_ok', False):
            return
        try:
            stats = self.db_manager.get_statistiche_comune() or []

            # --- Grafico 1: Partite per comune (bar orizzontale, top 10) ---
            ax = self._ax_partite
            ax.clear()
            dati = sorted(stats, key=lambda r: r.get('totale_partite', 0), reverse=True)[:10]
            comuni = [r.get('comune', '') for r in dati]
            totali = [r.get('totale_partite', 0) for r in dati]
            ax.barh(comuni[::-1], totali[::-1], color='steelblue')
            ax.set_title('Partite per comune (top 10)')
            ax.set_xlabel('Totale partite')

            # --- Grafico 2: Stato partite (torta attive/inattive) ---
            ax2 = self._ax_stato
            ax2.clear()
            tot_attive  = sum(r.get('partite_attive', 0)   for r in stats)
            tot_inattive = sum(r.get('partite_inattive', 0) for r in stats)
            if tot_attive + tot_inattive > 0:
                ax2.pie([tot_attive, tot_inattive],
                        labels=['Attive', 'Inattive'],
                        colors=['#4CAF50', '#F44336'],
                        autopct='%1.1f%%', startangle=90)
            ax2.set_title('Stato partite (totale)')

            # --- Grafico 3: Variazioni per anno ---
            ax3 = self._ax_variaz
            ax3.clear()
            try:
                variaz = self.db_manager.get_elenco_variazioni_per_esportazione(None) or []
                anni: dict = {}
                for v in variaz:
                    data = v.get('data_variazione') or ''
                    anno = str(data)[:4]
                    if anno.isdigit():
                        anni[anno] = anni.get(anno, 0) + 1
                if anni:
                    anni_ord = sorted(anni.keys())
                    ax3.bar(anni_ord, [anni[a] for a in anni_ord], color='darkorange')
                    ax3.set_title('Variazioni per anno')
                    ax3.set_xlabel('Anno')
                    ax3.set_ylabel('N. variazioni')
                    ax3.tick_params(axis='x', rotation=45)
            except Exception:
                ax3.set_title('Variazioni per anno (dati non disponibili)')

            self._canvas.draw()
        except Exception as e:
            self.logger.error(f"Errore aggiornamento grafici: {e}", exc_info=True)

    def _create_maintenance_tab(self):
        """Crea il widget per il tab 'Manutenzione'."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        group = QGroupBox("Operazioni di Manutenzione")
        group_layout = QVBoxLayout(group)
        
        # Sezione Viste
        viste_label = QLabel("Le viste materializzate migliorano le performance delle statistiche. Aggiornale periodicamente.")
        viste_label.setWordWrap(True)
        self.update_views_button = QPushButton("Aggiorna Tutte le Viste Materializzate")
        self.update_views_button.clicked.connect(self.update_all_views)
        group_layout.addWidget(viste_label)
        group_layout.addWidget(self.update_views_button)
        
        group_layout.addWidget(QFrame(self, frameShape=QFrame.Shape.HLine))

        
        layout.addWidget(group)

        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setPlaceholderText("L'esito delle operazioni di manutenzione apparirà qui...")
        layout.addWidget(self.status_text, 1) # Dà più spazio al log
        return widget

    def _load_data_on_first_show(self):
        """Carica i dati iniziali la prima volta che il tab viene mostrato."""
        self.logger.info("StatisticheWidget: Esecuzione lazy loading...")
        self.refresh_stats_comune()
        self.refresh_immobili_tipologia()
        self._aggiorna_grafici()

    def refresh_stats_comune(self):
        self.logger.info("Aggiornamento statistiche comuni...")
        self.stats_comune_table.setRowCount(0)
        try:
            stats = self.db_manager.get_statistiche_comune()
            if stats:
                self.stats_comune_table.setRowCount(len(stats))
                for i, s in enumerate(stats):
                    self.stats_comune_table.setItem(i, 0, QTableWidgetItem(s.get('comune', '')))
                    self.stats_comune_table.setItem(i, 1, QTableWidgetItem(s.get('provincia', '')))
                    self.stats_comune_table.setItem(i, 2, QTableWidgetItem(str(s.get('totale_partite', 0))))
                    self.stats_comune_table.setItem(i, 3, QTableWidgetItem(str(s.get('partite_attive', 0))))
                    self.stats_comune_table.setItem(i, 4, QTableWidgetItem(str(s.get('partite_inattive', 0))))
                    self.stats_comune_table.setItem(i, 5, QTableWidgetItem(str(s.get('totale_possessori', 0))))
                    self.stats_comune_table.setItem(i, 6, QTableWidgetItem(str(s.get('totale_immobili', 0))))
                self.stats_comune_table.resizeColumnsToContents()
            self.log_status("Statistiche comuni aggiornate con successo.")
        except DBMError as e:
            self.log_status(f"Errore DB durante l'aggiornamento delle statistiche comuni: {e}", error=True)
            QMessageBox.critical(self, "Errore", f"Impossibile caricare le statistiche:\n{e}")

    def filter_immobili_per_comune(self):
        dialog = ComuneSelectionDialog(self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_comune_id:
            self.comune_filter_id = dialog.selected_comune_id
            self.comune_filter_display.setText(f"Comune: {dialog.selected_comune_name}")
            self.refresh_immobili_tipologia()

    def clear_immobili_filter(self):
        self.comune_filter_id = None
        self.comune_filter_display.setText("Visualizzando tutti i comuni")
        self.refresh_immobili_tipologia()

    def refresh_immobili_tipologia(self):
        self.logger.info("Aggiornamento statistiche immobili per tipologia...")
        self.immobili_table.setRowCount(0)
        try:
            stats = self.db_manager.get_immobili_per_tipologia(self.comune_filter_id)
            if stats:
                self.immobili_table.setRowCount(len(stats))
                for i, s in enumerate(stats):
                    self.immobili_table.setItem(i, 0, QTableWidgetItem(s.get('comune_nome', '')))
                    self.immobili_table.setItem(i, 1, QTableWidgetItem(s.get('classificazione', 'N/D')))
                    num_immobili = s.get('numero_immobili', 0)
                    self.immobili_table.setItem(i, 2, QTableWidgetItem(str(num_immobili)))
                    self.immobili_table.setItem(i, 3, QTableWidgetItem(str(s.get('totale_piani', 0))))
                    totale_vani = s.get('totale_vani', 0)
                    self.immobili_table.setItem(i, 4, QTableWidgetItem(str(totale_vani)))
                    media_vani = round(totale_vani / num_immobili, 2) if num_immobili > 0 else 0
                    self.immobili_table.setItem(i, 5, QTableWidgetItem(str(media_vani)))
                self.immobili_table.resizeColumnsToContents()
            status_text = "Statistiche immobili aggiornate"
            if self.comune_filter_id:
                status_text += f" (filtrate per {self.comune_filter_display.text()})"
            self.log_status(status_text + ".")
        except DBMError as e:
            self.log_status(f"Errore DB durante l'aggiornamento delle statistiche immobili: {e}", error=True)
            QMessageBox.critical(self, "Errore", f"Impossibile caricare le statistiche:\n{e}")

    def update_all_views(self):
        self.log_status("Avvio aggiornamento di tutte le viste materializzate...")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            if self.db_manager.refresh_materialized_views():
                self.log_status("Aggiornamento viste completato con successo.")
                self.refresh_stats_comune()
                self.refresh_immobili_tipologia()
            else:
                self.log_status("ERRORE: Aggiornamento viste non riuscito. Controllare i log.", error=True)
        finally:
            QApplication.restoreOverrideCursor()

    

    def log_status(self, message, error=False):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        if error:
            self.status_text.append(f"<font color='red'>{formatted_message}</font>")
        else:
            self.status_text.append(formatted_message)
        self.status_text.verticalScrollBar().setValue(self.status_text.verticalScrollBar().maximum())
        QApplication.processEvents()

    def _apri_menu_stats_comune(self, position: QPoint):
        """Context menu sulla tabella statistiche per comune."""
        index = self.stats_comune_table.indexAt(position)
        if not index.isValid():
            return
        row = index.row()
        comune_item = self.stats_comune_table.item(row, 0)
        prov_item = self.stats_comune_table.item(row, 1)
        comune = comune_item.text() if comune_item else ""
        prov = prov_item.text() if prov_item else ""

        menu = QMenu(self.stats_comune_table)
        if comune:
            menu.addAction(f"Copia comune  ({comune})").triggered.connect(
                lambda: QApplication.clipboard().setText(comune))
        if prov:
            menu.addAction(f"Copia provincia  ({prov})").triggered.connect(
                lambda: QApplication.clipboard().setText(prov))
        menu.addSeparator()
        def _copia_riga():
            parts = []
            for col in range(self.stats_comune_table.columnCount()):
                item = self.stats_comune_table.item(row, col)
                parts.append(item.text() if item else "")
            QApplication.clipboard().setText("\t".join(parts))
        menu.addAction("Copia riga intera").triggered.connect(_copia_riga)
        menu.exec(self.stats_comune_table.viewport().mapToGlobal(position))

    def _apri_menu_immobili_stats(self, position: QPoint):
        """Context menu sulla tabella statistiche immobili per tipologia."""
        index = self.immobili_table.indexAt(position)
        if not index.isValid():
            return
        row = index.row()
        comune_item = self.immobili_table.item(row, 0)
        class_item = self.immobili_table.item(row, 1)
        comune = comune_item.text() if comune_item else ""
        classificazione = class_item.text() if class_item else ""

        menu = QMenu(self.immobili_table)
        if comune:
            menu.addAction(f"Copia comune  ({comune})").triggered.connect(
                lambda: QApplication.clipboard().setText(comune))
        if classificazione:
            menu.addAction(f"Copia classificazione  ({classificazione})").triggered.connect(
                lambda: QApplication.clipboard().setText(classificazione))
        menu.addSeparator()
        def _copia_riga():
            parts = []
            for col in range(self.immobili_table.columnCount()):
                item = self.immobili_table.item(row, col)
                parts.append(item.text() if item else "")
            QApplication.clipboard().setText("\t".join(parts))
        menu.addAction("Copia riga intera").triggered.connect(_copia_riga)
        menu.exec(self.immobili_table.viewport().mapToGlobal(position))


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

