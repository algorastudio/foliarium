"""Dialog relativi ai possessori."""
from __future__ import annotations

import logging
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (QApplication,
                             QCheckBox, QComboBox, QDialog, QFormLayout,
                             QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QStyle,
                             QVBoxLayout, QDialogButtonBox)

from catasto_db_manager import CatastoDBManager
from foliarium.ui.widgets.custom import show_status_message as _show_status_message

try:
    from catasto_db_manager import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError
except ImportError:
    class DBMError(Exception): pass
    class DBUniqueConstraintError(DBMError): pass
    class DBNotFoundError(DBMError): pass
    class DBDataError(DBMError): pass

from foliarium.ui.dialogs.entity.selezione import ComuneSelectionDialog


class DettagliLegamePossessoreDialog(QDialog):
    def __init__(self, nome_possessore_selezionato: str, partita_tipo: str,
                 titolo_attuale: Optional[str] = None,
                 quota_attuale: Optional[str] = None,
                 db_manager: Optional['CatastoDBManager'] = None,
                 parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")
        self.setWindowTitle(
            f"Dettagli Legame per {nome_possessore_selezionato}")
        self.setMinimumWidth(400)

        self.titolo: Optional[str] = None
        self.quota: Optional[str] = None

        layout = QFormLayout(self)

        self.titolo_combo = QComboBox()
        self.titolo_combo.setPlaceholderText("Seleziona un tipo di possesso...")
        self._load_tipi_possesso(titolo_attuale)
        layout.addRow("Titolo di Possesso (*):", self.titolo_combo)

        self.quota_edit = QLineEdit()
        self.quota_edit.setPlaceholderText(
            "Es. 1/1, 1/2 (lasciare vuoto se non applicabile)")
        self.quota_edit.setText(
            quota_attuale if quota_attuale is not None else "")  # Pre-compila
        layout.addRow("Quota (opzionale):", self.quota_edit)

        # ... (pulsanti OK/Annulla e metodo _accept_details come prima) ...
        buttons_layout = QHBoxLayout()
        self.ok_button = QPushButton(
            QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DialogOkButton), "OK")
        self.ok_button.clicked.connect(self._accept_details)
        self.cancel_button = QPushButton(QApplication.style().standardIcon(
            QStyle.StandardPixmap.SP_DialogCancelButton), "Annulla")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addRow(buttons_layout)
        self.setLayout(layout)
        self.titolo_combo.setFocus()

    def _load_tipi_possesso(self, titolo_attuale: Optional[str] = None):
        """Carica i tipi di possesso dal database."""
        self.titolo_combo.clear()
        self.titolo_combo.addItem("--- Seleziona ---", None)
        try:
            if self.db_manager:
                tipi = self.db_manager.get_tipi_possesso()
                for tipo in tipi:
                    self.titolo_combo.addItem(tipo['nome'], tipo['id'])
        except Exception as e:
            self.logger.error(f"Errore caricamento tipi possesso: {e}")
            self.titolo_combo.addItem("Errore caricamento", None)

        if titolo_attuale:
            idx = self.titolo_combo.findText(titolo_attuale)
            if idx >= 0:
                self.titolo_combo.setCurrentIndex(idx)

    def _accept_details(self):
        titolo_val = self.titolo_combo.currentText()
        if titolo_val == "--- Seleziona ---" or not titolo_val:
            QMessageBox.warning(self, "Dato Mancante",
                                "Il titolo di possesso è obbligatorio.")
            self.titolo_combo.setFocus()
            return
        self.titolo = titolo_val
        self.quota = self.quota_edit.text().strip() or None
        self.accept()

    # Metodo statico per l'inserimento (come prima)

    @staticmethod
    def get_details_for_new_legame(nome_possessore: str, tipo_partita_attuale: str, parent=None, db_manager: Optional['CatastoDBManager'] = None) -> Optional[Dict[str, Any]]:
        if db_manager is None and hasattr(parent, 'db_manager'):
            db_manager = parent.db_manager
        dialog = DettagliLegamePossessoreDialog(
            nome_possessore_selezionato=nome_possessore,
            partita_tipo=tipo_partita_attuale,
            db_manager=db_manager,
            parent=parent
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return {
                "titolo": dialog.titolo,
                "quota": dialog.quota,
            }
        return None

    @staticmethod
    def get_details_for_edit_legame(nome_possessore: str, tipo_partita_attuale: str,
                                    titolo_init: str, quota_init: Optional[str],
                                    parent=None, db_manager: Optional['CatastoDBManager'] = None) -> Optional[Dict[str, Any]]:
        if db_manager is None and hasattr(parent, 'db_manager'):
            db_manager = parent.db_manager
        dialog = DettagliLegamePossessoreDialog(nome_possessore, tipo_partita_attuale,
                                                titolo_attuale=titolo_init,
                                                quota_attuale=quota_init,
                                                db_manager=db_manager,
                                                parent=parent)
        dialog.setWindowTitle(f"Modifica Legame per {nome_possessore}")
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return {
                "titolo": dialog.titolo,
                "quota": dialog.quota,
            }
        return None




class ModificaPossessoreDialog(QDialog):
    def __init__(self, db_manager: CatastoDBManager, possessore_id: int, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.possessore_id = possessore_id
        self.possessore_data_originale = None
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")
        # Per l'audit, se vuoi confrontare i dati vecchi e nuovi
        # self.current_user_info = getattr(QApplication.instance().main_window, 'logged_in_user_info', None) # Modo per prendere utente
        # se main_window è accessibile

        self.setWindowTitle(
            f"Modifica Dati Possessore ID: {self.possessore_id}")
        self.setMinimumWidth(450)

        self._init_ui()
        self._load_possessore_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.id_label = QLabel(str(self.possessore_id))
        form_layout.addRow("ID Possessore:", self.id_label)

        self.nome_completo_edit = QLineEdit()
        form_layout.addRow("Nome Completo (*):", self.nome_completo_edit)

        # Campo che avevi nello schema per ricerca/ordinamento
        self.cognome_nome_edit = QLineEdit()
        form_layout.addRow("Cognome e Nome (per ricerca):",
                           self.cognome_nome_edit)

        self.paternita_edit = QLineEdit()
        form_layout.addRow("Paternità:", self.paternita_edit)
        
        # --- INIZIO NUOVA AGGIUNTA: Pulsante Genera Nome Completo ---
        self.btn_genera_nome_completo = QPushButton("Genera Nome Completo")
        # Collega il pulsante al nuovo metodo _genera_nome_completo
        self.btn_genera_nome_completo.clicked.connect(self._genera_nome_completo)
        # Aggiungi il pulsante al layout (es. sotto Paternità o tra i campi)
        form_layout.addRow(self.btn_genera_nome_completo) 
        # --- FINE NUOVA AGGIUNTA ---

        self.attivo_checkbox = QCheckBox("Possessore Attivo")
        form_layout.addRow(self.attivo_checkbox)

        # Comune di Riferimento
        comune_ref_layout = QHBoxLayout()
        self.comune_ref_label = QLabel(
            "Comune non specificato")  # Verrà popolato
        self.btn_cambia_comune_ref = QPushButton("Cambia...")
        self.btn_cambia_comune_ref.clicked.connect(
            self._cambia_comune_riferimento)
        comune_ref_layout.addWidget(self.comune_ref_label)
        comune_ref_layout.addStretch()
        comune_ref_layout.addWidget(self.btn_cambia_comune_ref)
        form_layout.addRow("Comune di Riferimento:", comune_ref_layout)

        # ID del comune di riferimento (nascosto, ma utile da tenere)
        self.selected_comune_ref_id: Optional[int] = None

        layout.addLayout(form_layout)

        # Pulsanti
        buttons_layout = QHBoxLayout()
        self.btn_archivia = QPushButton("Archivia Possessore")
        self.btn_archivia.setObjectName("dangerButton")
        self.btn_archivia.setToolTip("Archivia questo possessore (non viene eliminato, solo nascosto)")
        self.btn_archivia.clicked.connect(self._archivia_possessore)
        self.save_button = QPushButton(QApplication.style().standardIcon(
            QStyle.StandardPixmap.SP_DialogSaveButton), "Salva Modifiche")
        self.save_button.clicked.connect(self._save_changes)
        self.cancel_button = QPushButton(QApplication.style().standardIcon(
            QStyle.StandardPixmap.SP_DialogCancelButton), "Annulla")
        self.cancel_button.clicked.connect(self.reject)

        buttons_layout.addWidget(self.btn_archivia)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)
        
    def _genera_nome_completo(self):
        """
        Genera il campo 'Nome Completo' dalla concatenazione di 'Cognome e Nome' e 'Paternità'.
        """
        cognome_nome = self.cognome_nome_edit.text().strip()
        paternita = self.paternita_edit.text().strip()

        if cognome_nome and paternita:
            full_name = f"{cognome_nome} di {paternita}"
        elif cognome_nome:
            full_name = cognome_nome
        else:
            full_name = "" # O "N/D" a seconda delle preferenze

        self.nome_completo_edit.setText(full_name)
        self.logger.debug(f"Nome completo generato: '{full_name}'")

    def _load_possessore_data(self):
        # Metodo da creare in CatastoDBManager: get_possessore_details(possessore_id)
        # Dovrebbe restituire un dizionario con tutti i campi di possessore,
        # incluso comune_id e il nome del comune (comune_riferimento_nome).
        self.possessore_data_originale = self.db_manager.get_possessore_full_details(
            self.possessore_id)  # Rinominato per chiarezza

        if not self.possessore_data_originale:
            QMessageBox.critical(self, "Errore Caricamento",
                                 f"Impossibile caricare i dati per il possessore ID: {self.possessore_id}.\n"
                                 "Il dialogo verrà chiuso.")
            from PyQt6.QtCore import QTimer
            # Chiudi dopo che il messaggio è stato processato
            QTimer.singleShot(0, self.reject)
            return

        self.nome_completo_edit.setText(
            self.possessore_data_originale.get('nome_completo', ''))
        self.cognome_nome_edit.setText(self.possessore_data_originale.get(
            'cognome_nome', ''))
        self.paternita_edit.setText(
            self.possessore_data_originale.get('paternita', ''))
        self.attivo_checkbox.setChecked(
            self.possessore_data_originale.get('attivo', True))

        self.selected_comune_ref_id = self.possessore_data_originale.get(
            'comune_riferimento_id')  # Salva l'ID
        nome_comune_ref = self.possessore_data_originale.get(
            'comune_riferimento_nome', "Nessun comune assegnato")
        self.comune_ref_label.setText(
            f"{nome_comune_ref} (ID: {self.selected_comune_ref_id or 'N/A'})")

    def _cambia_comune_riferimento(self):
        # Usa ComuneSelectionDialog per cambiare il comune di riferimento
        dialog = ComuneSelectionDialog(
            self.db_manager, self, title="Seleziona Nuovo Comune di Riferimento")
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_comune_id:
            self.selected_comune_ref_id = dialog.selected_comune_id
            self.comune_ref_label.setText(
                f"{dialog.selected_comune_name} (ID: {self.selected_comune_ref_id})")
            logging.getLogger("CatastoGUI").info(
                f"Nuovo comune di riferimento selezionato per possessore (non ancora salvato): ID {self.selected_comune_ref_id}, Nome: {dialog.selected_comune_name}")

    def _save_changes(self):
        logging.getLogger("CatastoGUI").info(
            # NUOVA STAMPA
            f"DEBUG: _save_changes chiamato per possessore ID {self.possessore_id}")
        dati_modificati = {
            "nome_completo": self.nome_completo_edit.text().strip(),
            "cognome_nome": self.cognome_nome_edit.text().strip() or None,  # Può essere nullo
            "paternita": self.paternita_edit.text().strip() or None,    # Può essere nullo
            "attivo": self.attivo_checkbox.isChecked(),
            "comune_riferimento_id": self.selected_comune_ref_id,  # L'ID del comune selezionato
        }
        logging.getLogger("CatastoGUI").info(
            f"DEBUG: Dati dalla UI: {dati_modificati}")  # NUOVA STAMPA

        if not dati_modificati["nome_completo"]:
            QMessageBox.warning(
                self, "Dati Mancanti", "Il 'Nome Completo' del possessore è obbligatorio.")
            self.nome_completo_edit.setFocus()
            return

        if dati_modificati["comune_riferimento_id"] is None:
            QMessageBox.warning(self, "Dati Mancanti",
                                "Il 'Comune di Riferimento' è obbligatorio.")
            # Non c'è un campo input diretto per il focus, ma l'utente deve usare il pulsante
            self.btn_cambia_comune_ref.setFocus()
            return

        try:
            logging.getLogger("CatastoGUI").info(
                # NUOVA STAMPA
                f"DEBUG: Chiamata a db_manager.update_possessore per ID {self.possessore_id}")
            logging.getLogger("CatastoGUI").info(
                f"Tentativo di aggiornare il possessore ID {self.possessore_id} con i dati: {dati_modificati}")
            # Metodo da creare in CatastoDBManager: update_possessore(possessore_id, dati_modificati)
            self.db_manager.update_possessore(
                self.possessore_id, dati_modificati)

            logging.getLogger("CatastoGUI").info(
                f"Possessore ID {self.possessore_id} aggiornato con successo.")
            logging.getLogger("CatastoGUI").info(
                # NUOVA STAMPA
                f"DEBUG: db_manager.update_possessore completato per ID {self.possessore_id}")
            self.accept()  # Chiude il dialogo e restituisce QDialog.DialogCode.Accepted

        # Gestione eccezioni simile a quella di update_partita (DBUniqueConstraintError, DBDataError, DBMError, etc.)
        # Ad esempio, se nome_completo + comune_id deve essere univoco, o altri vincoli.
        # Per ora, un gestore generico per errori DB e altri errori.
        except (DBMError, DBDataError) as dbe_poss:  # Usa le tue eccezioni personalizzate
            logging.getLogger("CatastoGUI").error(
                f"Errore DB durante aggiornamento possessore ID {self.possessore_id}: {dbe_poss}", exc_info=True)
            QMessageBox.critical(self, "Errore Database",
                                 f"Errore durante il salvataggio delle modifiche al possessore:\n{dbe_poss.message if hasattr(dbe_poss, 'message') else str(dbe_poss)}")
        except AttributeError as ae:
            logging.getLogger("CatastoGUI").critical(
                f"Metodo 'update_possessore' non trovato o altro AttributeError: {ae}", exc_info=True)
            QMessageBox.critical(self, "Errore Implementazione",
                                 "Funzionalità per aggiornare possessore non completamente implementata o errore interno.")
        except Exception as e_poss:
            logging.getLogger("CatastoGUI").critical(
                f"Errore critico imprevisto durante il salvataggio del possessore ID {self.possessore_id}: {e_poss}", exc_info=True)
            QMessageBox.critical(self, "Errore Critico Imprevisto",
                                 f"Si è verificato un errore di sistema imprevisto:\n{type(e_poss).__name__}: {e_poss}")

    def _archivia_possessore(self):
        nome = self.nome_completo_edit.text()
        risposta = QMessageBox.question(
            self, "Conferma Archiviazione",
            f"Archiviare il possessore '{nome}'?\n\nNon verrà eliminato, solo nascosto dalle ricerche.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if risposta != QMessageBox.StandardButton.Yes:
            return
        try:
            self.db_manager.archivia_possessore(self.possessore_id)
            _show_status_message(f"Possessore '{nome}' archiviato.", 4000)
            self.reject()  # Chiude il dialog
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile archiviare il possessore:\n{e}")

# In dialogs.py, SOSTITUISCI l'intera classe ModificaComuneDialog con questa:




class CreatePossessoreDialog(QDialog):
    """Dialogo semplificato per la creazione di un nuovo possessore."""
    def __init__(self, db_manager: 'CatastoDBManager', parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.nuovo_possessore_id = None
        self.nuovo_possessore_dati = None
        self.setWindowTitle("Crea Nuovo Possessore")
        self.setMinimumWidth(450)
        self.setModal(True)

        # UI
        layout = QFormLayout(self)
        self.cognome_nome_edit = QLineEdit()
        self.paternita_edit = QLineEdit()
        self.nome_completo_edit = QLineEdit()
        self.btn_genera_nome = QPushButton("Genera da campi precedenti")
        self.comune_combo = QComboBox()
        self.attivo_check = QCheckBox("Attivo"); self.attivo_check.setChecked(True)

        layout.addRow("Cognome e Nome (*):", self.cognome_nome_edit)
        layout.addRow("Paternità:", self.paternita_edit)
        layout.addRow(self.btn_genera_nome)
        layout.addRow("Nome Completo (*):", self.nome_completo_edit)
        layout.addRow("Comune di Riferimento (*):", self.comune_combo)
        layout.addRow(self.attivo_check)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addRow(self.button_box)

        # Connessioni e caricamento dati
        self.btn_genera_nome.clicked.connect(self._genera_nome)
        self.button_box.accepted.connect(self._salva_e_accetta)
        self.button_box.rejected.connect(self.reject)

        self._carica_comuni()

    def _carica_comuni(self):
        self.comune_combo.addItem("--- Seleziona ---", None)
        try:
            comuni = self.db_manager.get_elenco_comuni_semplice()
            for cid, nome in comuni:
                self.comune_combo.addItem(nome, cid)
        except DBMError as e:
            QMessageBox.critical(self, "Errore", f"Impossibile caricare i comuni: {e}")

    def _genera_nome(self):
        nome = self.cognome_nome_edit.text().strip()
        paternita = self.paternita_edit.text().strip()
        self.nome_completo_edit.setText(f"{nome} {paternita}".strip())

    def _salva_e_accetta(self):
        nome_completo = self.nome_completo_edit.text().strip()
        cognome_nome = self.cognome_nome_edit.text().strip()
        comune_id = self.comune_combo.currentData()

        if not nome_completo or not cognome_nome or comune_id is None:
            QMessageBox.warning(self, "Dati Mancanti", "Cognome/Nome, Nome Completo e Comune sono obbligatori.")
            return

        try:
            self.nuovo_possessore_id = self.db_manager.create_possessore(
                nome_completo=nome_completo,
                cognome_nome=cognome_nome,
                paternita=self.paternita_edit.text().strip() or None,
                comune_riferimento_id=comune_id,
                attivo=self.attivo_check.isChecked()
            )
            self.nuovo_possessore_dati = self.db_manager.get_possessore_full_details(self.nuovo_possessore_id)
            self.accept()
        except (DBMError, DBUniqueConstraintError) as e:
            QMessageBox.critical(self, "Errore Creazione", str(e))




