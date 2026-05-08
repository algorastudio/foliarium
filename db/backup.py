"""
db/backup.py — Mixin per backup, restore e script PostgreSQL.
Estratto da catasto_db_manager.py — mixin per CatastoDBManager.
"""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, TYPE_CHECKING

import os
import shutil
import psycopg2
from psycopg2.extras import DictCursor

from catasto_exceptions import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError

if TYPE_CHECKING:
    from catasto_db_manager import CatastoDBManager


class DBBackupMixin:
    """Mixin per backup, restore e script PostgreSQL."""

    def register_backup_log(self, nome_file: str, utente: str, tipo: str, esito: bool,
                            percorso_file: str, dimensione_bytes: Optional[int] = None,
                            messaggio: Optional[str] = None) -> Optional[int]:
        """Chiama la funzione SQL registra_backup e restituisce l'ID del log creato."""
        try:
            query = "SELECT registra_backup(%s, %s, %s, %s, %s, %s, %s) AS backup_id"
            params = (nome_file, utente, dimensione_bytes, tipo, esito, messaggio, percorso_file)
            # La funzione SQL restituisce l'ID del record inserito nella tabella backup_registro
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, params)
                    result = cur.fetchone()
                    backup_id = result['backup_id'] if result else None
            if backup_id:
                self.logger.info(f"Log backup registrato con ID {backup_id} per '{nome_file}'")
            else:
                self.logger.error(f"registra_backup non ha restituito un ID per '{nome_file}'.")
            return backup_id
        except psycopg2.Error as db_err: self.logger.error(f"Errore DB reg log backup '{nome_file}': {db_err}")
        except Exception as e: self.logger.error(f"Errore Python reg log backup '{nome_file}': {e}")
        return None

    def _find_executable(self, name: str) -> Optional[str]:
        executable_path = shutil.which(name)
        if executable_path:
            self.logger.info(f"Trovato eseguibile '{name}' in: {executable_path}")
            return executable_path
        else:
            self.logger.warning(f"Eseguibile '{name}' non trovato nel PATH di sistema.")
            return None # Modificato da return "" per coerenza con Optional[str]

    def get_backup_command_parts(self,
                                 backup_file_path: str,
                                 pg_dump_executable_path_ui: str,
                                 format_type: str = "custom",
                                 include_blobs: bool = False
                                ) -> Optional[List[str]]:
        
        actual_pg_dump_path = self._resolve_executable_path(pg_dump_executable_path_ui, "pg_dump.exe")
        if not actual_pg_dump_path:
            return None

        # USA L'ATTRIBUTO CORRETTO: _main_db_conn_params
        db_user = self._main_db_conn_params.get("user")
        db_host = self._main_db_conn_params.get("host")
        db_port = str(self._main_db_conn_params.get("port"))
        db_name = self._main_db_conn_params.get("dbname")

        if not all([db_user, db_host, db_port, db_name]):
            self.logger.error("Parametri di connessione mancanti per il backup (da _main_db_conn_params).")
            return None

        backup_file_path = str(Path(backup_file_path).resolve())

        command = [actual_pg_dump_path, "-U", db_user, "-h", db_host, "-p", db_port]

        if format_type == "custom": command.append("-Fc")
        elif format_type == "plain": command.append("-Fp")
        else:
            self.logger.error(f"Formato di backup non supportato: {format_type}"); return None
        command.extend(["--file", backup_file_path])
        if include_blobs: command.append("--blobs")
        command.append(db_name)
        self.logger.info(f"Comando di backup preparato: {' '.join(command)}")
        return command

    def get_restore_command_parts(self,
                                  backup_file_path: str,
                                  pg_tool_executable_path_ui: str
                                 ) -> Optional[List[str]]:
        # USA L'ATTRIBUTO CORRETTO: _main_db_conn_params
        db_user = self._main_db_conn_params.get("user")
        db_host = self._main_db_conn_params.get("host")
        db_port = str(self._main_db_conn_params.get("port"))
        db_name = self._main_db_conn_params.get("dbname")

        if not all([db_user, db_host, db_port, db_name]):
            self.logger.error("Parametri di connessione mancanti per il ripristino (da _main_db_conn_params).")
            return None

        backup_file_path = str(Path(backup_file_path).resolve())

        command: List[str] = []
        _, file_extension = os.path.splitext(backup_file_path)
        file_extension = file_extension.lower()
        actual_pg_tool_path = None

        if file_extension in [".dump", ".backup", ".custom"]:
            actual_pg_tool_path = self._resolve_executable_path(pg_tool_executable_path_ui, "pg_restore.exe")
            if not actual_pg_tool_path: return None
            command = [actual_pg_tool_path, "-U", db_user, "-h", db_host, "-p", db_port, "-d", db_name]
            command.extend(["--clean", "--if-exists", "--verbose"]) # Opzioni comuni per pg_restore
            command.append(backup_file_path)
        elif file_extension == ".sql":
            actual_pg_tool_path = self._resolve_executable_path(pg_tool_executable_path_ui, "psql.exe")
            if not actual_pg_tool_path: return None
            command = [actual_pg_tool_path, "-U", db_user, "-h", db_host, "-p", db_port, "-d", db_name]
            command.extend(["-f", backup_file_path, "-v", "ON_ERROR_STOP=1"]) # Esegui script SQL con psql
        else:
            self.logger.error(f"Formato file di backup non riconosciuto o non supportato: '{file_extension}'"); return None
        self.logger.info(f"Comando di ripristino preparato: {' '.join(command)}")
        return command

    def _resolve_executable_path(self, user_provided_path: str, default_name: str) -> Optional[str]:
        if user_provided_path and os.path.isabs(user_provided_path) and os.path.exists(user_provided_path) and os.path.isfile(user_provided_path):
            self.logger.info(f"Utilizzo del percorso eseguibile fornito: {user_provided_path}")
            return user_provided_path
        elif user_provided_path:
             self.logger.warning(f"Percorso fornito '{user_provided_path}' per '{default_name}' non valido. Tento ricerca nel PATH.")
        
        found_path_in_system = shutil.which(default_name)
        if found_path_in_system:
            self.logger.info(f"Trovato eseguibile '{default_name}' nel PATH: {found_path_in_system}")
            return found_path_in_system
        else:
            self.logger.error(f"Eseguibile '{default_name}' non trovato nel PATH e nessun percorso valido fornito.")
            # Fornire un messaggio all'utente nella GUI che il tool non è stato trovato e deve essere configurato
            return None

    def cleanup_old_backup_logs(self, giorni_conservazione: int = 30) -> bool:
        """Chiama la procedura SQL pulizia_backup_vecchi per eliminare log più vecchi di N giorni."""
        try:
            call_proc = "CALL pulizia_backup_vecchi(%s)"
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(call_proc, (giorni_conservazione,))
            self.logger.info(f"Pulizia log backup: eliminati record più vecchi di {giorni_conservazione} giorni.")
            return True
        except psycopg2.Error as db_err: self.logger.error(f"Errore DB pulizia log backup: {db_err}"); return False
        except Exception as e: self.logger.error(f"Errore Python pulizia log backup: {e}"); return False

    def generate_backup_script(self, backup_dir: str) -> Optional[str]:
        """Chiama la funzione SQL genera_script_backup_automatico e restituisce lo script come stringa."""
        try:
            query = "SELECT genera_script_backup_automatico(%s) AS script_content"
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, (backup_dir,))
                    result = cur.fetchone()
                    return result['script_content'] if result else None
        except psycopg2.Error as db_err: self.logger.error(f"Errore DB generazione script backup: {db_err}"); return None
        except Exception as e: self.logger.error(f"Errore Python generazione script backup: {e}"); return None

    def get_backup_logs(self, limit: int = 20) -> List[Dict]:
        """Recupera gli ultimi N log di backup dal registro."""
        query = f"SELECT * FROM {self.schema}.backup_registro ORDER BY timestamp DESC LIMIT %s"
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(query, (limit,))
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            self.logger.error(f"Errore DB get_backup_logs: {e}", exc_info=True)
            return []

    def execute_restore_from_file_emergency(self, backup_file_path: str) -> Tuple[bool, str]:
        """
        Esegue un ripristino DRUPIDO E DISTRUTTIVO del database.
        1. CANCELLA il database esistente.
        2. LO RICREA vuoto.
        3. LO RIPRISTINA dal file di backup.
        Questa operazione richiede una connessione al database di manutenzione (es. 'postgres').
        """
        # Ottieni i parametri necessari dal gestore stesso
        db_user = self._main_db_conn_params.get("user")
        db_password = self._main_db_conn_params.get("password") # Richiede la password per i tool
        db_host = self._main_db_conn_params.get("host")
        db_port = str(self._main_db_conn_params.get("port"))
        db_name = self._main_db_conn_params.get("dbname")

        # Trova i percorsi degli eseguibili
        dropdb_path = self._resolve_executable_path(None, "dropdb.exe")
        createdb_path = self._resolve_executable_path(None, "createdb.exe")
        pg_restore_path = self._resolve_executable_path(None, "pg_restore.exe")

        if not all([dropdb_path, createdb_path, pg_restore_path]):
            msg = "Impossibile trovare gli eseguibili di PostgreSQL (dropdb, createdb, pg_restore) nel PATH di sistema."
            self.logger.error(msg)
            return False, msg

        # Comando per CANCELLARE il database esistente
        drop_command = [dropdb_path, "-U", db_user, "-h", db_host, "-p", db_port, "--if-exists", "-f", db_name]

        # Comando per RICREARE il database vuoto
        create_command = [createdb_path, "-U", db_user, "-h", db_host, "-p", db_port, "-T", "template0", db_name]

        # Comando per RIPRISTINARE il backup
        restore_command = [pg_restore_path, "-U", db_user, "-h", db_host, "-p", db_port, "-d", db_name, "--clean", "--if-exists", "-v", backup_file_path]

        commands = [
            ("Cancellazione DB esistente", drop_command),
            ("Creazione DB vuoto", create_command),
            ("Ripristino dati da backup", restore_command)
        ]

        # Imposta la variabile d'ambiente per la password
        env = os.environ.copy()
        env['PGPASSWORD'] = db_password

        # Lazy-import Qt per mantenere il package db/ utilizzabile in ambienti headless
        from PyQt6.QtCore import QProcess, QProcessEnvironment

        for description, command in commands:
            self.logger.info(f"Esecuzione emergenza: {description}...")
            process = QProcess()
            process.setProcessEnvironment(self.create_clean_environment()) # Usa un ambiente pulito
            # Crea un oggetto QProcessEnvironment
            env_process = QProcessEnvironment()
            for k, v in env.items():
                env_process.insert(k, v)

            # Imposta l'ambiente del processo
            process.setProcessEnvironment(env_process)

            process.start(command[0], command[1:])
            if not process.waitForFinished(-1):
                error_msg = f"Timeout o errore durante: {description}. Errore: {process.errorString()}"
                self.logger.error(error_msg)
                return False, error_msg

            exit_code = process.exitCode()
            if exit_code != 0:
                error_output = process.readAllStandardError().data().decode('utf-8', errors='ignore')
                error_msg = f"Fallimento durante '{description}' (codice: {exit_code}).\nErrore:\n{error_output}"
                self.logger.error(error_msg)
                return False, error_msg

        success_msg = f"Ripristino del database '{db_name}' completato con successo."
        self.logger.info(success_msg)
        return True, success_msg

