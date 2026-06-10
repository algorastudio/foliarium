"""Dialog aggiunta documento a una partita."""

import logging
import os
from typing import Optional, Dict, Any

from PyQt6.QtCore import (QDate)
from PyQt6.QtWidgets import (QComboBox, QDialog, QFileDialog, QFormLayout, QLabel, QLineEdit,
                             QMessageBox, QPushButton, QSpinBox, QTextEdit, QVBoxLayout, QDialogButtonBox)

from catasto_db_manager import CatastoDBManager



try:
    from catasto_db_manager import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError
except ImportError:
    class DBMError(Exception): pass
    class DBUniqueConstraintError(DBMError): pass
    class DBNotFoundError(DBMError): pass
    class DBDataError(DBMError): pass


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

# ---------------------------------------------------------------------------
# Import comuni e località da CSV / ISTAT
# ---------------------------------------------------------------------------


# Estratto in import_dialogs.py — backward compat re-export


