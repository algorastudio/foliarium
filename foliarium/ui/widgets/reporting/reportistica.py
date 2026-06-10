"""Widget generazione report testuali / PDF / ODT."""
from __future__ import annotations

import os
import logging
from datetime import date, datetime
from typing import TYPE_CHECKING


from PyQt6.QtCore import (
    QDate, Qt, QUrl,
)
from PyQt6.QtGui import (
    QDesktopServices,
)
from PyQt6.QtWidgets import (
    QDateEdit, QDialog, QFileDialog,
    QFormLayout, QGroupBox,
    QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QProgressDialog,
    QPushButton, QSpinBox, QTabWidget,
    QTextBrowser, QVBoxLayout,
    QWidget,
)

from app_utils import FPDF_AVAILABLE, GenericTextReportPDF, _get_default_export_path
from catasto_exceptions import DBMError, DBDataError, DBNotFoundError, DBUniqueConstraintError  # noqa: F401
from dialogs import (
    AlberoGeneralogicoDialog, ConfrontoPartiteDialog,
    PartitaSearchDialog, PossessoreSelectionDialog,
)
from foliarium.ui.widgets.custom import LazyLoadedWidget

if TYPE_CHECKING:
    pass

logger = logging.getLogger("CatastoGUI.reporting_widgets")


class ReportisticaWidget(LazyLoadedWidget):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_report_content = ""  # Memorizza il report corrente
        self._initUI()

    def _initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(12)

        title = QLabel("Reportistica")
        title.setObjectName("pageTitle")
        main_layout.addWidget(title)
        subtitle = QLabel("Genera report in PDF, TXT o ODT su proprietà, genealogie, possessori e consultazioni.")
        subtitle.setObjectName("pageSubtitle")
        main_layout.addWidget(subtitle)

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
        # Collega il segnale al nuovo metodo corretto
        self.report_output_browser.anchorClicked.connect(self._open_export_file_link)
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
        self.current_report_content = report_text or f"Nessun report generato per la partita ID {partita_id}."

        # 1. Pulisci completamente il widget
        self.report_output_browser.clear()
        # 2. Imposta il nuovo contenuto come testo semplice
        self.report_output_browser.setPlainText(self.current_report_content)

    def generate_genealogico(self):
        partita_id = self.partita_id_gen_edit.value()
        if partita_id <= 0: return QMessageBox.warning(self, "Errore", "Selezionare un ID partita valido.")

        report_text = self.db_manager.genera_report_genealogico(partita_id)
        self.current_report_content = report_text or f"Nessun report generato per la partita ID {partita_id}."

        # 1. Pulisci completamente il widget
        self.report_output_browser.clear()
        # 2. Imposta il nuovo contenuto come testo semplice
        self.report_output_browser.setPlainText(self.current_report_content)

    def _apri_albero_genealogico(self):
        partita_id = self.partita_id_gen_edit.value()
        if partita_id <= 0:
            QMessageBox.warning(self, "ID Non Valido", "Selezionare un ID partita valido.")
            return
        AlberoGeneralogicoDialog(self.db_manager, partita_id, self).exec()

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
                    "Report salvato con successo!\n\nVuoi aprire il file ora?",
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
                    "PDF creato con successo!\n\nVuoi aprire il file ora?",
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




