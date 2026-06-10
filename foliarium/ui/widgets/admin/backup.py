"""Backup e ripristino del database."""
from __future__ import annotations

import os
import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import (
    QDateTime, QProcess, QProcessEnvironment,
    pyqtSlot,
)
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMessageBox, QProgressBar, QPushButton, QStyle,
    QTextEdit, QVBoxLayout, QWidget,
)


if TYPE_CHECKING:
    from catasto_db_manager import CatastoDBManager

logger = logging.getLogger("CatastoGUI.admin_widgets")




class BackupWidget(QWidget):
    def __init__(self, db_manager: 'CatastoDBManager', parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")
        self.setWindowTitle("Backup e Ripristino Database")

        # Processi per pg_dump e pg_restore
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self._handle_stdout)
        self.process.readyReadStandardError.connect(self._handle_stderr)
        self.process.finished.connect(self._handle_process_finished)

        self._init_ui()

    def _log_to_output_box(self, message: str, level: str = "INFO"):
        """
        Scrive un messaggio nella casella di output con un colore basato sul livello.
        I livelli possibili sono: INFO, WARNING, ERROR, CRITICAL, SUCCESS, DEBUG.
        """
        color_map = {
            "INFO": "#34495e",    # Grigio scuro / Blu-grigio per routine
            "WARNING": "#e67e22", # Arancione per avvisi
            "ERROR": "#c0392b",   # Rosso scuro per errori
            "CRITICAL": "#e74c3c",# Rosso più vivo per critico
            "SUCCESS": "#27ae60", # Verde per successo
            "DEBUG": "#7f8c8d"    # Grigio chiaro per debug (normalmente non visibile all'utente)
        }
        
        display_color = color_map.get(level.upper(), "#34495e") # Default a grigio scuro
        
        # Aggiunge un timestamp al messaggio
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
        formatted_message = f"<span style='color: {display_color};'>[{timestamp}] {message}</span>"
        
        self.output_text_edit.append(formatted_message)
        
        # Assicurati che l'output sia scrollato verso il basso
        self.output_text_edit.verticalScrollBar().setValue(self.output_text_edit.verticalScrollBar().maximum())

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Sezione Backup ---
        backup_group = QGroupBox("Backup Database")
        backup_layout = QFormLayout(backup_group)

        self.backup_file_path_edit = QLineEdit()
        self.backup_file_path_edit.setPlaceholderText(
            "Seleziona percorso e nome del file di backup...")
        self.backup_file_path_edit.setReadOnly(True)
        btn_browse_backup_path = QPushButton("Sfoglia...")
        btn_browse_backup_path.clicked.connect(
            self._browse_backup_file_save_path)
        backup_path_layout = QHBoxLayout()
        backup_path_layout.addWidget(self.backup_file_path_edit)
        backup_path_layout.addWidget(btn_browse_backup_path)
        backup_layout.addRow("File di Backup:", backup_path_layout)

        self.backup_format_combo = QComboBox()
        self.backup_format_combo.addItems([
            "Custom (compresso, per pg_restore - raccomandato)",
            "Plain SQL (testo semplice)"
        ])
        backup_layout.addRow("Formato Backup:", self.backup_format_combo)

        self.pg_dump_path_edit = QLineEdit()
        self.pg_dump_path_edit.setPlaceholderText(
            "Es. C:\\Program Files\\PostgreSQL\\17\\bin\\pg_dump.exe (opzionale)")
        backup_layout.addRow(
            "Percorso pg_dump (opz.C:\\Program Files\\PostgreSQL\\17\\bin\\pg_dump.exe):", self.pg_dump_path_edit)

        self.backup_button = QPushButton(QApplication.style().standardIcon(
            QStyle.StandardPixmap.SP_DialogSaveButton), "Esegui Backup")
        self.backup_button.clicked.connect(self._start_backup)
        backup_layout.addRow(self.backup_button)

        main_layout.addWidget(backup_group)

        # --- Sezione Ripristino ---
        restore_group = QGroupBox("Ripristino Database")
        restore_layout = QFormLayout(restore_group)

        self.restore_file_path_edit = QLineEdit()
        self.restore_file_path_edit.setPlaceholderText(
            "Seleziona il file di backup da ripristinare...")
        self.restore_file_path_edit.setReadOnly(True)
        btn_browse_restore_path = QPushButton("Sfoglia...")
        btn_browse_restore_path.clicked.connect(
            self._browse_restore_file_open_path)
        restore_path_layout = QHBoxLayout()
        restore_path_layout.addWidget(self.restore_file_path_edit)
        restore_path_layout.addWidget(btn_browse_restore_path)
        restore_layout.addRow("File di Backup:", restore_path_layout)

        self.pg_restore_path_edit = QLineEdit()
        self.pg_restore_path_edit.setPlaceholderText(
            "Es. ...\\bin\\pg_restore.exe o ...\\bin\\psql.exe (opz.)")
        restore_layout.addRow(
            "Percorso pg_restore/psql (opz.):", self.pg_restore_path_edit)

        self.restore_button = QPushButton(QApplication.style().standardIcon(
            QStyle.StandardPixmap.SP_DialogApplyButton), "Esegui Ripristino")
        self.restore_button.clicked.connect(self._start_restore)
        restore_layout.addRow(self.restore_button)
        restore_layout.addRow(QLabel(
            "<font color='red'><b>ATTENZIONE:</b> Il ripristino sovrascriverà i dati correnti nel database. Procedere con cautela.</font>"))

        main_layout.addWidget(restore_group)

        # --- Output e Progresso ---
        output_group = QGroupBox("Output Operazione")
        output_layout = QVBoxLayout(output_group)
        self.output_text_edit = QTextEdit()
        self.output_text_edit.setReadOnly(True)
        self.output_text_edit.setLineWrapMode(
            QTextEdit.LineWrapMode.NoWrap)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)

        output_layout.addWidget(self.output_text_edit)
        output_layout.addWidget(self.progress_bar)
        main_layout.addWidget(output_group, 1)

        self.setLayout(main_layout)

    def _browse_backup_file_save_path(self):
        current_dbname = self.db_manager.get_current_dbname()
        default_db_name = current_dbname if current_dbname else "catasto_storico"

        default_filename = f"{default_db_name}_backup_{QDateTime.currentDateTime().toString('yyyyMMdd_HHmmss')}"

        if self.backup_format_combo.currentIndex() == 0:
            filter_str = "File di Backup PostgreSQL Custom (*.dump *.backup);;Tutti i file (*)"
            default_filename += ".dump"
        else:
            filter_str = "File SQL (*.sql);;Tutti i file (*)"
            default_filename += ".sql"

        filePath, _ = QFileDialog.getSaveFileName(
            self, "Salva Backup Database", default_filename, filter_str)
        if filePath:
            self.backup_file_path_edit.setText(filePath)

    def _browse_restore_file_open_path(self):
        filter_str = "File di Backup PostgreSQL (*.dump *.backup *.sql);;File Custom (*.dump *.backup);;File SQL (*.sql);;Tutti i file (*)"
        filePath, _ = QFileDialog.getOpenFileName(
            self, "Seleziona File di Backup per Ripristino", "", filter_str)
        if filePath:
            self.restore_file_path_edit.setText(filePath)

    def _update_ui_for_process(self, is_running: bool):
        self.backup_button.setEnabled(not is_running)
        self.restore_button.setEnabled(not is_running)
        self.progress_bar.setVisible(is_running)
        if is_running:
            self.progress_bar.setRange(0, 0)
            self.output_text_edit.clear()
        else:
            self.progress_bar.setRange(0, 1)
            self.progress_bar.setValue(0)

    # --- Modificato: Utilizza _log_to_output_box ---
    @pyqtSlot()
    def _handle_stdout(self):
        data = self.process.readAllStandardOutput().data().decode(errors='ignore')
        for line in data.splitlines():
            self._log_to_output_box(line, "INFO")

    # --- Modificato: Utilizza _log_to_output_box e analizza il contenuto ---
    @pyqtSlot()
    def _handle_stderr(self):
        data = self.process.readAllStandardError().data().decode(errors='ignore')
        for line in data.splitlines():
            lower_line = line.lower()
            if "warning" in lower_line or "avviso" in lower_line:
                self._log_to_output_box(line, "WARNING")
            elif "error" in lower_line or "errore" in lower_line or "failed" in lower_line or "fallito" in lower_line:
                self._log_to_output_box(line, "ERROR")
            else:
                self._log_to_output_box(line, "INFO") # Output standard in stderr che non è un errore/warning esplicito

    # --- Modificato: Utilizza _log_to_output_box ---
    @pyqtSlot(int, QProcess.ExitStatus)
    def _handle_process_finished(self, exitCode, exitStatus):
        is_restore = self.process.property("is_restore_operation")
        self.process.setProperty("is_restore_operation", False)

        self._log_to_output_box(f"Processo terminato. ExitCode: {exitCode}, ExitStatus: {exitStatus}, Operazione Ripristino: {is_restore}", "DEBUG")
        
        self._update_ui_for_process(False)

        operation_name_display = "Ripristino del database" if is_restore else "Backup del database"
        
        user_message_title = f"Esito {operation_name_display}"
        user_message_text = ""
        message_box_type = QMessageBox.Icon.Information

        if exitStatus == QProcess.ExitStatus.CrashExit:
            user_message_title = f"Errore Grave durante il {operation_name_display}"
            user_message_text = (
                f"Si è verificato un errore inaspettato e grave durante il {operation_name_display}. "
                "Il processo è terminato in modo anomalo (crash). "
                "Controllare attentamente i dettagli nell'area 'Output Operazione' per informazioni tecniche. "
                "Si consiglia di riprovare l'operazione."
            )
            message_box_type = QMessageBox.Icon.Critical
            self._log_to_output_box(
                f"ERRORE CRITICO: Il processo di {operation_name_display.lower()} è terminato inaspettatamente (crash).", "CRITICAL")
            
        elif exitCode != 0:
            user_message_title = f"Operazione di {operation_name_display} Fallita"
            user_message_text = (
                f"L'operazione di {operation_name_display} è fallita con un codice d'errore ({exitCode}). "
                "Ciò indica che il comando esterno non è stato completato correttamente. "
                "Controllare i messaggi in rosso nell'area 'Output Operazione' per capire la causa dell'errore (ad es., password errata, permessi mancanti, file non trovato)."
            )
            message_box_type = QMessageBox.Icon.Warning
            self._log_to_output_box(
                f"FALLITO: Il processo di {operation_name_display.lower()} è terminato con codice d'errore: {exitCode}.", "ERROR")
        else: # exitCode == 0, il processo stesso ha terminato con successo
            user_message_title = f"Operazione di {operation_name_display} Completata"
            user_message_text = (
                f"L'operazione di {operation_name_display} è stata completata con successo. "
                "Si consiglia di controllare l'area 'Output Operazione' per eventuali messaggi informativi o di avviso da parte dello strumento."
            )
            message_box_type = QMessageBox.Icon.Information
            self._log_to_output_box(
                f"Comando di {operation_name_display.lower()} terminato (exit code 0).", "SUCCESS")
            
        # --- Gestione Riconnessione Pool e Messaggio Finale per l'Utente ---
        if is_restore:
            self._log_to_output_box("Tentativo di ripristinare le connessioni dell'applicazione al database...", "INFO")
            QApplication.processEvents()

            if self.db_manager and self.db_manager.reconnect_pool_if_needed():
                self._log_to_output_box("Connessioni dell'applicazione al database ripristinate con successo.", "INFO")
                if message_box_type == QMessageBox.Icon.Information:
                    user_message_text += "\nLe connessioni dell'applicazione al database sono state ripristinate. L'applicazione è ora pronta all'uso."
                else:
                    user_message_text += "\nATTENZIONE: Le connessioni dell'applicazione sono state ripristinate, ma si sono verificati errori durante il ripristino stesso. Verificare l'integrità dei dati."
                QMessageBox(message_box_type, user_message_title, user_message_text, QMessageBox.StandardButton.Ok, self).exec()
                QMessageBox.information(self, "Verifica Importante",
                                         "Dopo un ripristino, si consiglia sempre di verificare l'integrità dei dati nel database. Se si riscontrano problemi, riavviare l'applicazione.")

            else: # Riconnessione pool fallita dopo un restore
                self._log_to_output_box(
                    "FALLITO: Impossibile ripristinare le connessioni al database. Si prega di RIAVVIARE L'APPLICAZIONE.", "CRITICAL")
                user_message_title = "Errore Critico: Riconnessione Database Fallita"
                user_message_text = (
                    f"L'operazione di {operation_name_display} è terminata, ma l'applicazione non è riuscita a riconnettersi al database. "
                    "Questo è un errore critico. Si prega di chiudere e riavviare l'applicazione immediatamente."
                )
                QMessageBox.critical(self, user_message_title, user_message_text, QMessageBox.StandardButton.Ok, self).exec()

        else: # Non è un'operazione di ripristino (es. Backup)
            QMessageBox(message_box_type, user_message_title, user_message_text, QMessageBox.StandardButton.Ok, self).exec()


    # --- Modificato: Utilizza _log_to_output_box ---
    def _start_backup(self):
        backup_file = self.backup_file_path_edit.text()
        if not backup_file:
            QMessageBox.warning(
                self, "Percorso Mancante", "Selezionare un percorso e un nome file per il backup.")
            return

        if os.path.exists(backup_file):
            reply = QMessageBox.question(self, "Conferma Sovrascrittura",
                                        f"Il file '{os.path.basename(backup_file)}' esiste già.\nVuoi sovrascriverlo?",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return

        db_user_for_prompt = self.db_manager.get_current_user() or "N/Utente"
        db_name_for_prompt = self.db_manager.get_current_dbname() or "N/Database"

        password, ok = QInputDialog.getText(self, "Autenticazione Database per Backup",
                                            f"Inserisci la password per l'utente '{db_user_for_prompt}' "
                                            f"sul database '{db_name_for_prompt}':",
                                            QLineEdit.EchoMode.Password)
        if not ok:
            self._log_to_output_box("Backup annullato dall'utente (dialogo password chiuso).", "INFO")
            return
        if not password.strip():
            QMessageBox.warning(self, "Password Mancante",
                                 "La password non può essere vuota.")
            self._log_to_output_box("Backup fallito: password non fornita.", "WARNING")
            self._update_ui_for_process(False)
            return

        self._update_ui_for_process(True)
        self.output_text_edit.clear()
        self._log_to_output_box(f"Avvio backup su: {backup_file}...", "INFO")

        command_parts = self.db_manager.get_backup_command_parts(
            backup_file_path=backup_file,
            pg_dump_executable_path_ui=self.pg_dump_path_edit.text().strip(),
            format_type="custom" if self.backup_format_combo.currentIndex() == 0 else "plain",
            include_blobs=False
        )

        if not command_parts:
            self._log_to_output_box(
                "ERRORE: Impossibile costruire il comando di backup. Verificare il percorso di pg_dump e i log.", "ERROR")
            self._update_ui_for_process(False)
            QMessageBox.critical(
                self, "Errore Comando", "Impossibile preparare il comando di backup. Controllare i log dell'applicazione.")
            return

        executable = command_parts[0]
        args = command_parts[1:]

        self._log_to_output_box(
            f"Comando da eseguire: {executable} {' '.join(args)}", "INFO")

        process_env = QProcessEnvironment.systemEnvironment() # Inizia con l'ambiente di sistema pulito
        self._log_to_output_box(
            f"Tentativo di impostare PGPASSWORD per l'utente '{db_user_for_prompt}'...", "INFO")
        try:
            process_env.insert("PGPASSWORD", password)
            self.process.setProcessEnvironment(process_env)
            self._log_to_output_box("PGPASSWORD impostata per questo processo.", "INFO")
        except Exception as e:
            self._log_to_output_box(
                f"ERRORE nell'impostare PGPASSWORD: {e}", "ERROR")
            self._log_to_output_box(
                "Il backup potrebbe fallire o rimanere bloccato.", "WARNING")

        self.process.setProperty("is_restore_operation", False)
        self.process.start(executable, args)

    # --- Modificato: Utilizza _log_to_output_box ---
    def _start_restore(self):
        restore_file = self.restore_file_path_edit.text()
        if not restore_file:
            QMessageBox.warning(
                self, "File Mancante", "Selezionare un file di backup da cui ripristinare.")
            return
        if not os.path.exists(restore_file):
            QMessageBox.critical(
                self, "Errore File", f"Il file di backup '{restore_file}' non è stato trovato.")
            return

        dbname_to_restore = self.db_manager.get_current_dbname() or "Database Sconosciuto"
        db_host_for_prompt = self.db_manager.get_connection_parameters().get('host', 'N/Host') # Uso get_connection_parameters per essere coerente
        db_user_for_prompt = self.db_manager.get_current_user() or "Utente Sconosciuto"

        if dbname_to_restore == "Database Sconosciuto":
            QMessageBox.critical(self, "Errore Configurazione",
                                 "Nome del database di destinazione non recuperabile.")
            return

        reply = QMessageBox.warning(self, "Conferma Ripristino Critico",
                                     f"<b>ATTENZIONE ESTREMA!</b>\n\n"
                                     f"Stai per ripristinare il database dal file:\n'{os.path.basename(restore_file)}'\n"
                                     f"sul database di destinazione:\n<b>'{dbname_to_restore}'</b> "
                                     f"(Host: {db_host_for_prompt}, Utente DB: {db_user_for_prompt}).\n\n"
                                     "<b>Questa operazione SOVRASCRIVERÀ tutti i dati correnti nel database di destinazione e NON PUÒ ESSERE ANNULLATA.</b>\n\n"
                                     "Si raccomanda VIVAMENTE di aver effettuato un backup recente e verificato del database corrente prima di procedere.\n\n"
                                     "Sei assolutamente sicuro di voler continuare?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel)
        if reply == QMessageBox.StandardButton.Cancel:
            self._log_to_output_box("Ripristino annullato dall'utente (prima conferma).", "INFO")
            return

        text_confirm, ok = QInputDialog.getText(self, "Conferma Finale Ripristino Obbligatoria",
                                                 f"Per confermare il ripristino che sovrascriverà PERMANENTEMENTE il database '{dbname_to_restore}',\n"
                                                 f"digita il nome del database qui sotto (deve corrispondere esattamente):")
        if not ok:
            self._log_to_output_box("Ripristino annullato dall'utente (dialogo conferma nome DB chiuso).", "INFO")
            return
        if text_confirm.strip() != dbname_to_restore:
            QMessageBox.critical(self, "Ripristino Annullato",
                                 f"Il nome del database inserito ('{text_confirm.strip()}') non corrisponde a '{dbname_to_restore}'.\n"
                                 "Ripristino annullato per sicurezza.")
            self._log_to_output_box("Ripristino annullato: conferma nome database fallita.", "ERROR")
            return

        password, ok = QInputDialog.getText(self, "Autenticazione Database per Ripristino",
                                            f"Inserisci la password per l'utente '{db_user_for_prompt}' "
                                            f"per il database '{dbname_to_restore}':",
                                            QLineEdit.EchoMode.Password)
        if not ok:
            self._log_to_output_box("Ripristino annullato (dialogo password chiuso).", "INFO")
            return
        if not password.strip():
            QMessageBox.warning(
                self, "Password Mancante", "La password non può essere vuota per il ripristino.")
            self._log_to_output_box("Ripristino fallito: password non fornita.", "WARNING")
            self._update_ui_for_process(False)
            return

        self._update_ui_for_process(True)
        self.output_text_edit.clear()
        self._log_to_output_box(
            f"Avvio ripristino del database '{dbname_to_restore}' da: {restore_file}...", "INFO")
        self._log_to_output_box(
            "AVVISO: L'applicazione potrebbe non rispondere durante l'operazione di ripristino. Attendere il completamento.", "WARNING")
        QApplication.processEvents()

        self._log_to_output_box(
            "Tentativo di chiudere le connessioni attive dell'applicazione al database...", "INFO")
        QApplication.processEvents()
        if not self.db_manager.disconnect_pool_temporarily():
            QMessageBox.critical(self, "Errore Critico Ripristino",
                                 "Impossibile chiudere le connessioni esistenti al database prima del ripristino.\n"
                                 "L'operazione è stata annullata per sicurezza.")
            self._log_to_output_box(
                "FALLITO: Impossibile chiudere le connessioni al database. Ripristino annullato.", "ERROR")
            self._update_ui_for_process(False)
            return
        self._log_to_output_box("Connessioni dell'applicazione al database chiuse temporaneamente.", "INFO")
        QApplication.processEvents()

        command_parts = self.db_manager.get_restore_command_parts(
            backup_file_path=restore_file,
            pg_tool_executable_path_ui=self.pg_restore_path_edit.text().strip()
        )

        if not command_parts:
            self._log_to_output_box(
                "ERRORE: Impossibile costruire il comando di ripristino. Controllare il percorso dell'eseguibile e i log.", "ERROR")
            self._update_ui_for_process(False)
            self._log_to_output_box(
                "Tentativo di ripristinare le connessioni dell'applicazione (dopo fallimento preparazione comando)...", "INFO")
            if not self.db_manager.reconnect_pool_if_needed():
                self._log_to_output_box(
                    "FALLITO riconnessione pool. Riavviare l'app.", "CRITICAL")
            else:
                self._log_to_output_box("Connessioni applicazione ripristinate.", "INFO")
            QMessageBox.critical(
                self, "Errore Comando", "Impossibile preparare il comando di ripristino.")
            return

        executable = command_parts[0]
        args = command_parts[1:]
        self._log_to_output_box(
            f"Comando da eseguire: {executable} {' '.join(args)}", "INFO")

        process_env = QProcessEnvironment.systemEnvironment() # Inizia con l'ambiente di sistema
        self._log_to_output_box(
            f"Tentativo di impostare PGPASSWORD per l'utente '{db_user_for_prompt}'...", "INFO")
        try:
            process_env.insert("PGPASSWORD", password)
            self.process.setProcessEnvironment(process_env)
            self._log_to_output_box("PGPASSWORD impostata per questo processo.", "INFO")
        except Exception as e:
            self._log_to_output_box(
                f"ERRORE nell'impostare PGPASSWORD: {e}", "ERROR")

        self.process.setProperty("is_restore_operation", True)
        self.process.start(executable, args)




