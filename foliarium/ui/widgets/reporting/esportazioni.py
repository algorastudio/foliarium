"""Widget export CSV / XLSX / PDF."""
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
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(15)

        title = QLabel("Esportazioni")
        title.setObjectName("pageTitle")
        main_layout.addWidget(title)
        subtitle = QLabel("Esporta l'archivio in CSV o Excel. Filtra per comune prima di esportare.")
        subtitle.setObjectName("pageSubtitle")
        main_layout.addWidget(subtitle)

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
            
            self.log_status("Esportazione CSV completata con successo.", link=filename)
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
        if export_type == "Report Consistenza Patrimoniale":
            self._export_consistenza_patrimoniale_pdf(comune_id, comune_name)
            return # Termina qui l'esecuzione per questo report
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




