#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestore Database Catasto Storico (MODIFICATO per comune.id PK)
==============================================================
Script per la gestione del database catastale con supporto
per operazioni CRUD, chiamate alle stored procedure, gestione utenti,
audit, backup e funzionalità avanzate.

Autore: Marco Santoro (Versione rivista e pulita)
Data: 29/04/2025
"""

import psycopg2
import psycopg2.errors # Importa specificamente gli errori
from psycopg2.extras import DictCursor
from psycopg2.extensions import ISOLATION_LEVEL_SERIALIZABLE,ISOLATION_LEVEL_AUTOCOMMIT

from psycopg2 import sql, extras, pool
import sys, csv
import logging
from datetime import date, datetime
from typing import List, Dict, Any, Optional, Tuple, Union
import json
import uuid
import os
import shutil # Per trovare i percorsi degli eseguibili
from contextlib import contextmanager
from PyQt5.QtWidgets import (QAbstractItemView, QAction, QApplication, 
                             QCheckBox, QComboBox, QDateEdit, QDateTimeEdit,
                             QDialog, QDialogButtonBox, QDoubleSpinBox,
                             QFileDialog, QFormLayout, QFrame, QGridLayout,
                             QGroupBox, QHBoxLayout, QHeaderView, QInputDialog,
                             QLabel, QLineEdit, QListWidget, QListWidgetItem,
                             QMainWindow, QMenu, QMessageBox, QProgressBar,
                             QPushButton, QScrollArea, QSizePolicy, QSpacerItem,
                             QSpinBox, QStyle, QStyleFactory, QTabWidget,
                             QTableWidget, QTableWidgetItem, QTextEdit,
                             QVBoxLayout,QProgressDialog)
from PyQt5.QtCore import (QDate, QDateTime, QPoint, QProcess, QSettings, 
                          QSize, QStandardPaths, Qt, QTimer, QUrl, 
                          pyqtSignal,QProcessEnvironment,QObject)





COLONNE_POSSESSORI_DETTAGLI_NUM = 6 # Esempio: ID, Nome Compl, Cognome/Nome, Paternità, Quota, Titolo
COLONNE_POSSESSORI_DETTAGLI_LABELS = ["ID Poss.", "Nome Completo", "Cognome Nome", "Paternità", "Quota", "Titolo"]

import logging
logger = logging.getLogger(__name__)
# ------------ ECCEZIONI PERSONALIZZATE ------------
class DBMError(Exception):
    """Classe base per errori specifici del DBManager."""
    pass

class DBUniqueConstraintError(DBMError):
    """Sollevata quando un vincolo di unicità viene violato."""
    def __init__(self, message, constraint_name=None, details=None):
        super().__init__(message)
        self.constraint_name = constraint_name
        self.details = details

class DBNotFoundError(DBMError):
    """Sollevata quando un record atteso non viene trovato per un'operazione."""
    pass

class DBDataError(DBMError):
    """Sollevata per errori relativi a dati o parametri forniti non validi."""
    pass
# -------------------------------------------------

class CatastoDBManager:
    
    def __init__(self, dbname, user, password, host, port,
                 schema="catasto",
                 application_name="CatastoApp_Pool",
                 log_file="catasto_db_manager.log",
                 log_level=logging.DEBUG, # O il suo default
                 min_conn=2,
                 max_conn=20):
       
        
        self._main_db_conn_params = {"dbname": dbname, "user": user, "password": password, "host": host, "port": port}
        self._maintenance_db_name = "postgres" 
        self.schema = schema
        self.application_name = application_name
        self._min_conn_pool = min_conn
        self._max_conn_pool = max_conn
        # --- AGGIUNGERE QUESTA RIGA ---
        self.last_connection_error = None # Per memorizzare i dettagli dell'ultimo errore
        # -----------------------------

        self.logger = logging.getLogger(f"CatastoDB_{dbname}_{host}_{port}")
        # ... (resto della configurazione del logger come prima) ...
        self.logger.info(f"Inizializzato gestore DB (parametri memorizzati) per {dbname}@{host}")
        self.pool = None # Il pool viene inizializzato esplicitamente dopo
    # In catasto_db_manager.py, SOSTITUISCI il metodo initialize_main_pool con questo:

    def initialize_main_pool(self) -> bool:
        if self.pool:
            self.logger.info("Pool principale già inizializzato.")
            return True

        self.last_connection_error = None
        target_dbname = self._main_db_conn_params.get("dbname")
        
        pool_config = {
            "minconn": self._min_conn_pool,
            "maxconn": self._max_conn_pool,
            **self._main_db_conn_params,
            "options": f"-c search_path={self.schema},public -c application_name='{self.application_name}_{target_dbname}'"
        }
        
        try:
            self.logger.info(f"Tentativo di inizializzazione pool per DB '{target_dbname}'...")
            self.pool = psycopg2.pool.ThreadedConnectionPool(**pool_config)
            
            conn_test = self.pool.getconn()
            self.pool.putconn(conn_test)
            
            self.logger.info(f"Pool di connessioni per DB '{target_dbname}' inizializzato e testato con successo.")
            return True

        except (psycopg2.pool.PoolError, psycopg2.Error) as e_init:
            
            # --- NUOVA LOGICA ROBUSTA DI ANALISI DELL'ERRORE ---
            error_string = str(e_init).lower()
            custom_pgcode = "UNKNOWN_DB_ERROR" # Default

            if "password authentication failed" in error_string or "autenticazione con password fallita" in error_string:
                custom_pgcode = "28P01" # Codice per Authentication Failure
            elif 'database' in error_string and ('does not exist' in error_string or 'non esiste' in error_string):
                custom_pgcode = "3D000" # Codice per Invalid Catalog Name
            elif "connection refused" in error_string or "connessione rifiutata" in error_string or "timed out" in error_string or "could not connect" in error_string:
                custom_pgcode = "08001" # Codice per Connection Exception

            self.last_connection_error = {
                'pgcode': custom_pgcode,
                'pgerror': str(e_init).strip() # Salva sempre il messaggio completo
            }
            # --- FINE NUOVA LOGICA ---
            
            self.logger.critical(f"FALLIMENTO inizializzazione pool per DB '{target_dbname}'. Errore: {e_init}", exc_info=False)
            self.logger.critical(f"   Dettagli Errore Analizzati: pgcode={self.last_connection_error['pgcode']}, pgerror='{self.last_connection_error['pgerror']}'")
            
            if self.pool:
                self.pool.closeall()
            self.pool = None
            return False
            
        except Exception as e_generic:
            self.last_connection_error = {'pgcode': 'GENERIC_PYTHON_ERROR', 'pgerror': str(e_generic)}
            self.logger.critical(f"FALLIMENTO inizializzazione pool per DB '{target_dbname}'. Errore generico: {e_generic}", exc_info=True)
            if self.pool:
                self.pool.closeall()
            self.pool = None
            return False

    def close_pool(self):
        """
        Chiude tutte le connessioni nel pool e imposta self.pool a None.
        Questo metodo dovrebbe essere chiamato quando l'applicazione si chiude
        o quando il database a cui il pool è connesso viene cancellato.
        """
        if self.pool:
            try:
                pool_name_app = self.pool._kwargs.get('application_name', self.application_name) # Tenta di ottenere il nome specifico del pool
                db_name_pooled = self.pool._kwargs.get('dbname', 'N/D')
                self.logger.info(f"Tentativo di chiusura del pool di connessioni '{pool_name_app}' per il database '{db_name_pooled}'...")
                self.pool.closeall()
                self.logger.info(f"Pool di connessioni '{pool_name_app}' (DB: '{db_name_pooled}') chiuso con successo.")
            except Exception as e:
                self.logger.error(f"Errore durante la chiusura del pool di connessioni: {e}", exc_info=True)
            finally:
                self.pool = None # Assicura che il pool sia None dopo il tentativo di chiusura, anche in caso di errore.
        else:
            self.logger.info("close_pool chiamato, ma il pool non era attivo o già None.")

    def _get_maintenance_connection(self, db_user_admin: str, db_password_admin: str, maintenance_dbname: str = "postgres"):
        """Ottiene una connessione singola a un database di manutenzione (es. postgres)."""
        maint_conn_params = self._main_db_conn_params.copy()
        maint_conn_params["dbname"] = maintenance_dbname
        # Usa le credenziali dell'utente admin del DB fornite, non quelle dell'app per catasto_storico
        maint_conn_params["user"] = db_user_admin
        maint_conn_params["password"] = db_password_admin 
        
        self.logger.info(f"Tentativo di connessione al DB di manutenzione '{maintenance_dbname}' come utente '{db_user_admin}'.")
        try:
            conn = psycopg2.connect(**maint_conn_params)
            conn.autocommit = True # Utile per comandi come CREATE DATABASE
            return conn
        except psycopg2.Error as e:
            self.logger.error(f"Errore connessione al DB di manutenzione '{maintenance_dbname}': {e}", exc_info=True)
            raise DBMError(f"Impossibile connettersi al database '{maintenance_dbname}': {e}") from e

    def check_database_exists(self, target_dbname: str, admin_user: str, admin_password: str) -> bool:
        """Verifica se un database specifico esiste connettendosi a 'postgres'."""
        conn_maint = None
        exists = False
        try:
            conn_maint = self._get_maintenance_connection(admin_user, admin_password, maintenance_dbname="postgres")
            with conn_maint.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (target_dbname,))
                exists = cur.fetchone() is not None
                self.logger.info(f"Controllo esistenza database '{target_dbname}': {'Esiste' if exists else 'Non esiste'}.")
        except DBMError as e: # Errore di connessione al DB di manutenzione
            self.logger.error(f"Impossibile verificare esistenza DB '{target_dbname}' due to error connecting to maintenance DB: {e}")
            # In questo caso, non possiamo sapere se esiste, consideriamo che non esista o sia inaccessibile
            exists = False 
        except psycopg2.Error as e: # Altri errori SQL
            self.logger.error(f"Errore DB verificando esistenza database '{target_dbname}': {e}", exc_info=True)
            exists = False
        finally:
            if conn_maint:
                conn_maint.close()
        return exists

    def create_target_database(self, target_dbname: str, admin_user: str, admin_password: str) -> bool:
        """Crea il database target (es. catasto_storico) se non esiste, connettendosi a 'postgres'."""
        conn_maint = None
        try:
            # Prima verifica se esiste per evitare errore CREATE se esiste già
            if self.check_database_exists(target_dbname, admin_user, admin_password):
                self.logger.info(f"Il database '{target_dbname}' esiste già. Nessuna azione di creazione eseguita.")
                return True # Considera successo se esiste già

            conn_maint = self._get_maintenance_connection(admin_user, admin_password, maintenance_dbname="postgres")
            with conn_maint.cursor() as cur: # autocommit è True sulla connessione
                self.logger.info(f"Tentativo di creare il database '{target_dbname}'...")
                # Usa sql.SQL per formattare nomi di database in modo sicuro
                cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target_dbname)))
                self.logger.info(f"Database '{target_dbname}' creato con successo.")
            return True
        except DBMError as e: # Errore di connessione al DB di manutenzione
            self.logger.error(f"Impossibile creare DB '{target_dbname}' due to error connecting to maintenance DB: {e}")
            return False
        except psycopg2.Error as e: # Altri errori SQL, es. "database ... already exists" se il check precedente fallisce
            self.logger.error(f"Errore DB durante la creazione del database '{target_dbname}': {getattr(e, 'pgerror', str(e))}", exc_info=False)
            if "already exists" in str(e).lower(): # Se esiste già, consideralo OK
                self.logger.info(f"Database '{target_dbname}' esisteva già (errore CREATE DATABASE ignorato).")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Errore Python imprevisto durante la creazione del database '{target_dbname}': {e}", exc_info=True)
            return False
        finally:
            if conn_maint:
                conn_maint.close()
# In catasto_db_manager.py, all'interno della classe CatastoDBManager

    @contextmanager
    def _get_connection(self):
        """
        Context manager per ottenere e rilasciare in sicurezza una connessione dal pool.
        Garantisce che putconn() sia sempre chiamato.
        """
        conn = None
        try:
            if not self.pool:
                raise psycopg2.pool.PoolError("Il pool di connessioni non è inizializzato.")
            conn = self.pool.getconn()
            yield conn
            # Il commit qui è implicito all'uscita del blocco 'with' senza eccezioni
            # Non chiamare conn.commit() se le transazioni sono gestite dall'esterno
            # (es. se autocommit è True per qualche operazione, o se il client gestisce i commit)
            # Per transazioni implicite, `commit()` qui è appropriato.
            # Se la connessione è stata usata per CALL PROCEDURE, spesso il commit è automatico.
            # Se si tratta di DML classiche, serve un commit esplicito.
            conn.commit() # Manteniamo questo per operazioni DML standard
        except psycopg2.pool.PoolError as pe:
            self.logger.error(f"Errore critico nell'ottenere una connessione dal pool: {pe}")
            raise psycopg2.OperationalError(f"Impossibile ottenere una connessione valida dal pool: {pe}")
        except Exception as e:
            if conn:
                try:
                    conn.rollback() # Annulla la transazione in caso di altri errori
                except psycopg2.Error as rollback_err:
                    self.logger.error(f"Errore durante il rollback della connessione (potrebbe essere già chiusa): {rollback_err}", exc_info=True)
                    # Se il rollback fallisce perché la connessione è già chiusa,
                    # e l'errore originale era OperationalError (connessione persa),
                    # è un segnale che il pool potrebbe essere corrotto.
                    if isinstance(e, psycopg2.OperationalError):
                        self.logger.critical("Errore operativo critico: il server ha chiuso la connessione. Il pool potrebbe essere invalido.", exc_info=True)
                        self.close_pool() # Forziamo la chiusura del pool in questo caso critico
            self.logger.error(f"Errore durante l'uso della connessione: {e}", exc_info=True)
            raise # Rilancia l'eccezione originale
        finally:
            if conn:
                self.pool.putconn(conn)
    
    def disconnect_pool_temporarily(self) -> bool:
        self.logger.info("Chiusura temporanea del pool di connessioni per operazione di ripristino...")
        self.close_pool() # Chiude e nullifica self.pool
        return True # Assume successo; close_pool gestisce i suoi log
    # In catasto_db_manager.py 

    def reconnect_pool_if_needed(self) -> bool:
        """
        Tenta di reinizializzare il pool di connessioni se non è attivo e ne verifica il funzionamento.
        Utilizza il pattern corretto con il context manager _get_connection.
        """
        self.logger.info("Tentativo di ricreare/verificare il pool di connessioni...")
        
        # 1. Tenta di inizializzare il pool se è None
        if not self.pool:
            self.logger.info("Pool non attivo. Tentativo di reinizializzazione...")
            if not self.initialize_main_pool():
                self.logger.error("Fallimento nella reinizializzazione del pool durante reconnect_pool_if_needed.")
                return False
                
        # 2. Verifica che il pool esista e sia funzionante tentando di ottenere una connessione
        if self.pool:
            try:
                # CORREZIONE: Usa 'with' per ottenere e rilasciare automaticamente la connessione.
                # Se questo blocco viene eseguito senza errori, significa che il pool funziona.
                with self._get_connection() as conn_test:
                    # La connessione è valida se siamo arrivati qui. Non dobbiamo fare altro.
                    self.logger.info("Pool ricreato/verificato e testato con successo dopo riconnessione.")
                return True
            except (DBMError, psycopg2.pool.PoolError) as e:
                # _get_connection solleverà una di queste eccezioni se il pool ha problemi.
                self.logger.error(f"Pool sembra esistere, ma il test di connessione è fallito: {e}", exc_info=False)
                return False
        else:
            # Se self.pool è ancora None dopo il tentativo di initialize_main_pool()
            self.logger.error("Fallimento critico: il pool è ancora None dopo il tentativo di reinizializzazione.")
            return False

    def get_current_dbname(self) -> Optional[str]:
        if hasattr(self, '_main_db_conn_params') and self._main_db_conn_params: # DEVE USARE _main_db_conn_params
            return self._main_db_conn_params.get("dbname")
        # Aggiorna anche il messaggio di log se vuoi essere preciso
        self.logger.warning("Tentativo di accesso a dbname fallito: _main_db_conn_params non trovato o vuoto.")
        return None

    def get_current_user(self) -> Optional[str]:
        if hasattr(self, '_main_db_conn_params') and self._main_db_conn_params: # DEVE USARE _main_db_conn_params
            return self._main_db_conn_params.get("user")
        self.logger.warning("Tentativo di accesso a user fallito: _main_db_conn_params non trovato o vuoto.")
        return None

    def get_connection_parameters(self) -> Dict[str, Any]:
        if hasattr(self, '_main_db_conn_params') and self._main_db_conn_params: # DEVE USARE _main_db_conn_params
            params_copy = self._main_db_conn_params.copy()
            params_copy.pop('password', None) 
            return params_copy
        self.logger.warning("Tentativo di accesso ai parametri di connessione fallito: _main_db_conn_params non definito.")
        return {}
    # --- AGGIUNGERE QUESTO NUOVO METODO ALLA CLASSE ---
    def get_last_connect_error_details(self) -> Optional[Dict[str, str]]:
        """Restituisce i dettagli dell'ultimo errore di connessione occorso."""
        return self.last_connection_error
    # -------------------------------------------------
    

    
    def fetchall(self) -> List[Dict]:
        """Recupera tutti i risultati dell'ultima query come lista di dizionari."""
        # Utilizza self.cursor, che è impostato da execute_query
        if self.cursor and not self.cursor.closed:
            try:
                # Il DictCursor restituisce già dict-like rows, quindi dict(row) potrebbe essere ridondante
                # ma non è dannoso. Se self.cursor.fetchall() restituisce già una lista di dict (o DictRow),
                # la conversione esplicita potrebbe non essere necessaria.
                # Per sicurezza e chiarezza, lasciamola se DictCursor non restituisce dict nativi.
                # Se DictCursor restituisce oggetti DictRow, sono già simili a dizionari.
                risultati = self.cursor.fetchall()
                # Se DictCursor è usato, ogni 'row' in 'risultati' è già un oggetto simile a un dizionario.
                # La conversione [dict(row) for row in ...] è sicura.
                return risultati # Se DictCursor restituisce direttamente una lista di dizionari (o oggetti DictRow)
                # oppure: return [dict(row) for row in risultati] # Se necessario convertire esplicitamente
            except psycopg2.ProgrammingError: # Si verifica se si tenta di fetch da una query che non restituisce risultati
                logger.warning("Nessun risultato da recuperare per l'ultima query (fetchall).")
                return []
            except Exception as e:
                logger.error(f"Errore generico durante fetchall: {e}")
                return []
        else: # self.cursor è None o è chiuso
            logger.warning("Tentativo di fetchall senza un cursore valido o su un cursore chiuso.")
            return []

    def fetchone(self) -> Optional[Dict[str, Any]]:
        """Recupera una riga dal cursore."""
        if self.cursor: # Verifica che il cursore esista
            try:
                return self.cursor.fetchone()
            except psycopg2.Error as e:
                logger.error(f"Errore DB durante fetchone: {e}")
                return None
        else:
            logger.warning("Tentativo di fetchone senza un cursore valido.")
            return None
    
        # --- Metodi CRUD e Ricerca Base (MODIFICATI per comune_id) ---
 # All'interno della classe CatastoDBManager in catasto_db_manager.py
# Assicurati che le importazioni e le definizioni delle eccezioni siano presenti.
# import datetime
# from typing import Optional, Dict, Any, List 
# from datetime import date # Già importato se datetime è importato

    # In catasto_db_manager.py, SOSTITUISCI il metodo aggiungi_comune con questo:

    def aggiungi_comune(self,
                        nome_comune: str,
                        provincia: str,
                        regione: str,
                        periodo_id: Optional[int] = None,
                        codice_catastale: Optional[str] = None,
                        data_istituzione: Optional[date] = None,
                        data_soppressione: Optional[date] = None,
                        note: Optional[str] = None,
                        utente: Optional[str] = None
                       ) -> int:
        
        # Validazione base dei campi obbligatori
        if not nome_comune or not provincia or not regione:
            raise DBDataError("Nome, Provincia e Regione sono campi obbligatori.")
        
        # --- Query aggiornata per includere i nuovi campi opzionali ---
        query = f"""
            INSERT INTO {self.schema}.comune 
                (nome, provincia, regione, periodo_id, codice_catastale, data_istituzione, data_soppressione, note)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """
        params = (
            nome_comune.strip(),
            provincia.strip(),
            regione.strip(),
            periodo_id,
            codice_catastale.strip() if codice_catastale else None,
            data_istituzione,
            data_soppressione,
            note.strip() if note else None
        )
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    self.logger.info(f"Esecuzione aggiungi_comune per: {nome_comune.strip()}")
                    cur.execute(query, params)
                    result = cur.fetchone()
                    if result and result[0] is not None:
                        new_comune_id = result[0]
                        self.logger.info(f"Comune '{nome_comune.strip()}' aggiunto con successo. ID: {new_comune_id}.")
                        return new_comune_id
                    else:
                        raise DBMError("Creazione del comune fallita, nessun ID restituito.")
        
        except psycopg2.errors.UniqueViolation as e:
            # Assumiamo che il vincolo di unicità sia sul nome
            raise DBUniqueConstraintError(f"Impossibile aggiungere il comune: il nome '{nome_comune}' esiste già.", details=str(e)) from e
        
        except Exception as e:
            self.logger.error(f"Errore generico in aggiungi_comune: {e}", exc_info=True)
            raise DBMError(f"Errore database durante l'aggiunta del comune: {e}") from e
    def registra_comune_nel_db(self, nome: str, provincia: str, regione: str) -> Optional[int]:
            comune_id: Optional[int] = None
            query_insert = """
            INSERT INTO catasto.comune (nome, provincia, regione)
            VALUES (%s, %s, %s)
            ON CONFLICT (nome) DO NOTHING
            RETURNING id;
            """
            query_select = "SELECT id FROM catasto.comune WHERE nome = %s;"

            try:
                if self.execute_query(query_insert, (nome, provincia, regione)):
                    # execute_query DEVE aver impostato self.cursor se ha restituito True
                    if self.cursor is None: # Controllo di sicurezza aggiuntivo
                        logger.error(f"Errore critico: self.cursor è None dopo execute_query riuscita per INSERT comune '{nome}'.")
                        self.rollback()
                        return None

                    risultato_insert = None
                    if self.cursor.description: # Verifica se la query poteva ritornare risultati
                        try:
                            risultato_insert = self.cursor.fetchone() # Prova a fare fetch
                        except psycopg2.ProgrammingError as pe: # Es. "no results to fetch"
                            logger.warning(f"Nessun risultato da fetchone() per INSERT comune '{nome}' (probabile ON CONFLICT DO NOTHING): {pe}")
                            risultato_insert = None

                    if risultato_insert and 'id' in risultato_insert:
                        comune_id = risultato_insert['id']
                        self.commit()
                        logger.info(f"Comune '{nome}' (ID: {comune_id}) inserito con successo nel database.")
                        return comune_id
                    else: # L'INSERT non ha inserito (ON CONFLICT DO NOTHING) o ID non recuperato
                        logger.info(f"Comune '{nome}' non inserito da INSERT (probabile conflitto). Tentativo di SELECT.")
                        if self.execute_query(query_select, (nome,)):
                            if self.cursor is None: # Controllo di sicurezza
                                logger.error(f"Errore critico: self.cursor è None dopo execute_query riuscita per SELECT comune '{nome}'.")
                                self.rollback()
                                return None
                            
                            risultato_select = self.fetchone() # fetchone() ora dovrebbe usare il cursore del SELECT
                            if risultato_select and 'id' in risultato_select:
                                comune_id = risultato_select['id']
                                self.commit() 
                                logger.info(f"Comune '{nome}' (ID: {comune_id}) già esistente, operazione confermata.")
                                return comune_id
                            else:
                                logger.error(f"Errore logico: Comune '{nome}' non inserito e non trovato dopo ON CONFLICT e successivo SELECT.")
                                self.rollback()
                                return None
                        else: # Errore durante il SELECT
                            # execute_query dovrebbe aver già gestito il rollback
                            logger.error(f"Errore DB nel selezionare il comune '{nome}' dopo un potenziale conflitto.")
                            return None
                else: # Errore durante l'INSERT iniziale
                    # execute_query dovrebbe aver già gestito il rollback
                    logger.error(f"Errore DB iniziale durante l'inserimento del comune '{nome}'.")
                    return None

            except psycopg2.Error as db_err:
                logger.error(f"Errore database (psycopg2) in registra_comune_nel_db per '{nome}': {db_err}")
                self.rollback()
                return None
            except AttributeError as ae: # Specifico per l'errore 'has no attribute cursor' se persiste
                logger.error(f"AttributeError in registra_comune_nel_db per '{nome}': {ae}. Controllare gestione self.cursor.")
                self.rollback()
                return None
            except Exception as e:
                logger.error(f"Errore Python generico in registra_comune_nel_db per '{nome}': {e}")
                self.rollback()
                return None
    
    def get_comuni(self, search_term: Optional[str] = None) -> List[Dict[str, Any]]:
        query = f"SELECT id, nome, provincia, regione FROM {self.schema}.comune"
        params = []
        if search_term:
            query += " WHERE nome ILIKE %s"
            params.append(f"%{search_term}%")
        query += " ORDER BY nome"
        
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, params)
                    results = cur.fetchall()
                    self.logger.info(f"Recuperati {len(results)} comuni (search_term: '{search_term}').")
                    return [dict(row) for row in results]
        except Exception as e:
            self.logger.error(f"Errore DB in get_comuni: {e}", exc_info=True)
            # In caso di errore, restituisce una lista vuota per non bloccare la UI
            return []
    
    # In catasto_db_manager.py, dentro la classe CatastoDBManager
    def get_partita_data_for_export(self, partita_id: int) -> Optional[Dict[str, Any]]:
        """
        Recupera i dati di una partita per l'esportazione chiamando una funzione SQL,
        in modo sicuro e transazionale.
        """
        if not isinstance(partita_id, int) or partita_id <= 0:
            self.logger.error(f"get_partita_data_for_export: ID partita non valido: {partita_id}")
            return None
            
        query = f"SELECT {self.schema}.esporta_partita_json(%s) AS partita_data;"
        
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    self.logger.debug(f"Esecuzione get_partita_data_for_export per ID partita: {partita_id}")
                    cur.execute(query, (partita_id,))
                    result = cur.fetchone()
                    
                    if result and result['partita_data'] is not None:
                        self.logger.info(f"Dati per esportazione recuperati per partita ID {partita_id}.")
                        return result['partita_data']
                    else:
                        self.logger.warning(f"Nessun dato trovato per partita ID {partita_id} o il risultato era NULL.")
                        return None
                        
        except Exception as e:
            self.logger.error(f"Errore DB in get_partita_data_for_export (ID: {partita_id}): {e}", exc_info=True)
            return None # Restituisce None in caso di qualsiasi errore
    def get_all_comuni_details(self):
        self.logger.info(">>> ESECUZIONE di get_all_comuni_details...")
        
        # --- QUERY AGGIORNATA PER SELEZIONARE TUTTE LE COLONNE NECESSARIE ---
        query = """
            SELECT 
                id, 
                nome AS nome_comune, 
                codice_catastale,
                provincia, 
                regione,
                data_istituzione,
                data_soppressione,
                note,
                data_creazione, 
                data_modifica
            FROM catasto.comune ORDER BY nome;
        """
        # --- FINE QUERY AGGIORNATA ---

        self.logger.info(f"Query in esecuzione:\n\t\t\t{query}")
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(query)
                    results = cur.fetchall()
                    self.logger.info(f"--- RISULTATO RICEVUTO da db_manager: Tipo={type(results)}, Lunghezza={len(results)} ---")
                    return results
        except (Exception, psycopg2.Error) as error:
            self.logger.error(f"Errore DB in get_all_comuni_details: {error}", exc_info=True)
            return [] # Restituisci una lista vuota in caso di errore

    
    # In catasto_db_manager.py, aggiungi questi metodi

    def get_tipi_localita(self) -> List[Dict[str, Any]]:
        """Recupera tutte le tipologie di località disponibili."""
        query = "SELECT id, nome, descrizione FROM catasto.tipo_localita ORDER BY nome;"
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(query)
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            self.logger.error(f"Errore nel recuperare i tipi di località: {e}", exc_info=True)
            raise DBMError("Impossibile recuperare le tipologie di località.") from e

    def gestisci_tipo_localita(self, tipo_id: Optional[int], nome: str, descrizione: Optional[str] = None) -> int:
        """Crea o aggiorna una tipologia di località."""
        if not nome or not nome.strip():
            raise DBDataError("Il nome della tipologia non può essere vuoto.")
        
        nome = nome.strip()
        descrizione = descrizione.strip() if descrizione else None

        if tipo_id: # Modalità aggiornamento
            query = "UPDATE catasto.tipo_localita SET nome = %s, descrizione = %s WHERE id = %s RETURNING id;"
            params = (nome, descrizione, tipo_id)
        else: # Modalità inserimento
            query = "INSERT INTO catasto.tipo_localita (nome, descrizione) VALUES (%s, %s) ON CONFLICT (nome) DO NOTHING RETURNING id;"
            params = (nome, descrizione)
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    result = cur.fetchone()
                    if result:
                        return result[0]
                    # Se ON CONFLICT non ha fatto nulla, l'ID non viene restituito. Potremmo voler gestire questo caso.
                    raise DBUniqueConstraintError(f"Una tipologia con nome '{nome}' esiste già.")
        except psycopg2.errors.UniqueViolation:
            raise DBUniqueConstraintError(f"Una tipologia con nome '{nome}' esiste già.") from None
        except Exception as e:
            self.logger.error(f"Errore in gestisci_tipo_localita: {e}", exc_info=True)
            raise DBMError("Operazione sulla tipologia di località fallita.") from e

    # Potresti voler aggiungere anche un metodo per l'eliminazione
    def elimina_tipo_localita(self, tipo_id: int) -> bool:
        """Elimina una tipologia di località, solo se non è utilizzata."""
        query = "DELETE FROM catasto.tipo_localita WHERE id = %s;"
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (tipo_id,))
                    return cur.rowcount > 0
        except psycopg2.errors.ForeignKeyViolation:
            raise DBMError("Impossibile eliminare: questa tipologia è utilizzata da una o più località.") from None
        except Exception as e:
            self.logger.error(f"Errore in elimina_tipo_localita: {e}", exc_info=True)
            raise DBMError("Eliminazione della tipologia fallita.") from e
    # In catasto_db_manager.py, aggiungi questo nuovo metodo

    # In catasto_db_manager.py, SOSTITUISCI il metodo get_immobili_by_comune

    def get_immobili_by_comune(self, comune_id: int) -> List[Dict[str, Any]]:
        """Recupera un elenco di tutti gli immobili presenti in un dato comune."""
        if not isinstance(comune_id, int) or comune_id <= 0:
            return []

        # --- INIZIO CORREZIONE: Aggiunto l.id AS localita_id alla query ---
        query = f"""
            SELECT 
                i.id, 
                i.natura, 
                l.nome AS localita_nome, 
                l.civico, 
                tl.nome as tipo_localita,
                l.id as localita_id -- Aggiungi questa colonna fondamentale
            FROM {self.schema}.immobile i
            JOIN {self.schema}.partita p ON i.partita_id = p.id
            JOIN {self.schema}.localita l ON i.localita_id = l.id
            LEFT JOIN {self.schema}.tipo_localita tl ON l.tipo_id = tl.id
            WHERE p.comune_id = %s
            ORDER BY l.nome, i.natura;
        """
        # --- FINE CORREZIONE ---
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(query, (comune_id,))
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            self.logger.error(f"Errore DB in get_immobili_by_comune per comune ID {comune_id}: {e}", exc_info=True)
            return []
    
    def get_elenco_comuni_semplice(self) -> List[Tuple]:
        """
        Recupera un elenco di tutti i comuni (ID e nome) per popolare una scelta utente.
        """
        query = f"SELECT id, nome FROM {self.schema}.comune ORDER BY nome"
        try:
            with self._get_connection() as conn:
                # Qui non usiamo DictCursor perché la firma del metodo prevede una lista di tuple
                with conn.cursor() as cur:
                    cur.execute(query)
                    return cur.fetchall()
        except Exception as e:
            self.logger.error(f"Errore nel recuperare l'elenco dei comuni: {e}", exc_info=True)
            # Solleviamo un'eccezione personalizzata per informare il chiamante del fallimento
            raise DBMError("Impossibile recuperare l'elenco dei comuni.") from e
    # In catasto_db_manager.py, sostituisci la vecchia funzione con questa:

    def import_possessori_from_csv(self, file_path: str, comune_id: int, comune_nome: str) -> Dict[str, list]:
        """
        Importa una lista di possessori da un file CSV, gestendo gli errori riga per riga.
        Restituisce un dizionario con i risultati dettagliati ('success' e 'errors').
        L'operazione è transazionale a livello di singola riga usando SAVEPOINT.
        """
        records_to_import = []
        try:
            # La fase di lettura del file rimane invariata
            with open(file_path, mode='r', encoding='utf-8') as csvfile:
                # Usiamo il punto e virgola come delimitatore, comune in Italia
                reader = csv.DictReader(csvfile, delimiter=';')
                required_headers = {'cognome_nome', 'nome_completo'}
                if not required_headers.issubset(reader.fieldnames or []):
                    raise ValueError(f"Intestazioni mancanti nel CSV. Richieste: {', '.join(required_headers)}")

                for i, row in enumerate(reader):
                    line_num = i + 2
                    if not row.get('cognome_nome') or not row.get('nome_completo'):
                        raise ValueError(f"Dati mancanti alla riga {line_num}. 'cognome_nome' e 'nome_completo' sono obbligatori.")
                    records_to_import.append(row)
        except FileNotFoundError:
            raise FileNotFoundError(f"File non trovato: {file_path}")
        except Exception as e:
            raise IOError(f"Errore leggendo il file CSV: {e}")

        if not records_to_import:
            return {"success": [], "errors": []}

        # Liste per raccogliere i risultati
        success_rows = []
        error_rows = []

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    for i, record in enumerate(records_to_import):
                        line_num = i + 2
                        
                        # Definiamo un SAVEPOINT per isolare la transazione di questa riga
                        cur.execute("SAVEPOINT record_savepoint")
                        
                        try:
                            nome_completo = record['nome_completo'].strip()
                            cognome_nome = record['cognome_nome'].strip()
                            paternita = record.get('paternita', '').strip() or None

                            # Controlla l'esistenza del possessore
                            cur.execute(
                                f"SELECT id FROM {self.schema}.possessore WHERE nome_completo = %s AND comune_id = %s",
                                (nome_completo, comune_id)
                            )
                            if cur.fetchone():
                                # Se esiste già, lo trattiamo come un errore per questa riga
                                raise ValueError(f"Il possessore '{nome_completo}' esiste già in questo comune.")

                            # Inserisce il nuovo possessore e recupera il suo ID
                            cur.execute(
                                f"""
                                INSERT INTO {self.schema}.possessore (comune_id, cognome_nome, paternita, nome_completo, attivo)
                                VALUES (%s, %s, %s, %s, %s)
                                RETURNING id;
                                """,
                                (comune_id, cognome_nome, paternita, nome_completo, True)
                            )
                            
                            new_id_result = cur.fetchone()
                            if not new_id_result:
                                raise DBMError("Inserimento fallito, nessun ID restituito dal database.")
                            
                            new_id = new_id_result[0]

                            # Rilascia il savepoint, rendendo l'inserimento permanente (al commit finale)
                            cur.execute("RELEASE SAVEPOINT record_savepoint")
                            
                            # Aggiungi ai successi
                            success_rows.append({
                                'id': new_id,
                                'nome_completo': nome_completo,
                                'comune_nome': comune_nome # Aggiungiamo il nome del comune per il report
                            })

                        except (ValueError, psycopg2.Error, DBMError) as error:
                            # Se si verifica un errore, torna al savepoint, annullando l'inserimento di questa riga
                            cur.execute("ROLLBACK TO SAVEPOINT record_savepoint")
                            # Aggiungi agli errori
                            error_rows.append((line_num, record, str(error)))

            # Se il ciclo 'with' termina senza errori gravi, la transazione principale viene committata,
            # salvando tutti gli inserimenti per cui è stato fatto "RELEASE SAVEPOINT".
            self.logger.info(f"Importazione CSV completata. Successi: {len(success_rows)}, Errori: {len(error_rows)}")
            return {"success": success_rows, "errors": error_rows}

        except Exception as e:
            # Questo cattura errori gravi (es. connessione persa)
            self.logger.error(f"Errore critico durante l'importazione CSV dei possessori: {e}", exc_info=True)
            # Rilancia come DBMError per informare il chiamante
            raise DBMError(f"Errore critico di sistema durante l'importazione: {e}") from e
    # In catasto_db_manager.py, SOSTITUISCI la vecchia funzione con questa

    def import_partite_from_csv(self, file_path: str, comune_id: int, comune_nome: str) -> Dict[str, list]:
        """
        Importa una lista di partite da un file CSV, gestendo gli errori riga per riga.
        Restituisce un dizionario con i risultati dettagliati ('success' e 'errors').
        """
        records_to_import = []
        try:
            with open(file_path, mode='r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile, delimiter=';')
                required_headers = {'numero_partita', 'data_impianto', 'stato', 'tipo'}
                if not required_headers.issubset(reader.fieldnames or []):
                    raise ValueError(f"Intestazioni mancanti nel CSV. Richieste: {', '.join(required_headers)}")
                for i, row in enumerate(reader):
                    if not all(row.get(key) for key in required_headers):
                        raise ValueError(f"Dati mancanti alla riga {i + 2}. Campi obbligatori: {', '.join(required_headers)}.")
                    records_to_import.append(row)
        except Exception as e:
            raise IOError(f"Errore leggendo il file CSV: {e}")

        if not records_to_import:
            return {"success": [], "errors": []}

        success_rows = []
        error_rows = []

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    for i, record in enumerate(records_to_import):
                        line_num = i + 2
                        cur.execute("SAVEPOINT record_savepoint")
                        try:
                            numero_partita = int(record['numero_partita'])
                            suffisso_partita = record.get('suffisso_partita') or None
                            
                            cur.execute(
                                f"SELECT id FROM {self.schema}.partita WHERE comune_id = %s AND numero_partita = %s AND (suffisso_partita = %s OR (suffisso_partita IS NULL AND %s IS NULL))",
                                (comune_id, numero_partita, suffisso_partita, suffisso_partita)
                            )
                            if cur.fetchone():
                                suffisso_str = f" con suffisso '{suffisso_partita}'" if suffisso_partita else ""
                                raise ValueError(f"La partita n.{numero_partita}{suffisso_str} esiste già.")

                            cur.execute(
                                f"""
                                INSERT INTO {self.schema}.partita (comune_id, numero_partita, suffisso_partita, data_impianto, data_chiusura, numero_provenienza, stato, tipo)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
                                """,
                                (comune_id, numero_partita, suffisso_partita, record['data_impianto'], record.get('data_chiusura') or None, record.get('numero_provenienza') or None, record['stato'], record['tipo'])
                            )
                            new_id = cur.fetchone()[0]
                            cur.execute("RELEASE SAVEPOINT record_savepoint")
                            record['id'] = new_id
                            record['comune_nome'] = comune_nome
                            success_rows.append(record)
                        
                        except (ValueError, psycopg2.Error, DBMError) as error:
                            cur.execute("ROLLBACK TO SAVEPOINT record_savepoint")
                            error_rows.append((line_num, record, str(error)))
            
            self.logger.info(f"Importazione CSV partite completata. Successi: {len(success_rows)}, Errori: {len(error_rows)}")
            return {"success": success_rows, "errors": error_rows}

        except Exception as e:
            self.logger.error(f"Errore critico durante l'importazione CSV delle partite: {e}", exc_info=True)
            raise DBMError(f"Errore critico di sistema durante l'importazione: {e}") from e
    def check_possessore_exists(self, nome_completo: str, comune_id: Optional[int] = None) -> Optional[int]:
        """Verifica se un possessore esiste e ritorna il suo ID, usando il pattern corretto."""
        try:
            if comune_id is not None:
                query = f"SELECT id FROM {self.schema}.possessore WHERE nome_completo = %s AND comune_id = %s AND attivo = TRUE"
                params = (nome_completo, comune_id)
            else:
                query = f"SELECT id FROM {self.schema}.possessore WHERE nome_completo = %s AND attivo = TRUE"
                params = (nome_completo,)
            
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, params)
                    result = cur.fetchone()
                    return result['id'] if result else None
        except Exception as e:
            self.logger.error(f"Errore in check_possessore_exists: {e}", exc_info=True)
            return None
    def create_possessore(self, nome_completo: str, comune_riferimento_id: int, paternita: Optional[str] = None, attivo: bool = True, cognome_nome: Optional[str] = None) -> int:
            query = f"INSERT INTO {self.schema}.possessore (nome_completo, paternita, comune_id, attivo, cognome_nome) VALUES (%s, %s, %s, %s, %s) RETURNING id;"
            params = (nome_completo.strip(), paternita, comune_riferimento_id, attivo, cognome_nome)
            try:
                with self._get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(query, params)
                        result = cur.fetchone()
                        if not result:
                            raise DBMError("Creazione possessore fallita, nessun ID restituito.")
                        return result[0]
            except psycopg2.errors.UniqueViolation as e:
                raise DBUniqueConstraintError("Un possessore con questi dati esiste già.", details=str(e)) from e
            except Exception as e:
                self.logger.error(f"Errore in create_possessore: {e}", exc_info=True)
                raise DBMError(f"Errore database: {e}") from e

    
    # In catasto_db_manager.py, aggiungi questo nuovo metodo alla classe

    def create_partita(self, comune_id: int, numero_partita: int, tipo: str, stato: str, data_impianto: date,
                       suffisso_partita: Optional[str] = None, data_chiusura: Optional[date] = None,
                       numero_provenienza: Optional[int] = None) -> int:
        """
        Crea una nuova, singola partita nel database e restituisce il suo ID.
        """
        # Validazione base
        if not all([comune_id, numero_partita, tipo, stato, data_impianto]):
            raise DBDataError("Comune, Numero Partita, Tipo, Stato e Data Impianto sono obbligatori.")

        query = f"""
            INSERT INTO {self.schema}.partita
                (comune_id, numero_partita, suffisso_partita, data_impianto, data_chiusura, numero_provenienza, stato, tipo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """
        params = (comune_id, numero_partita, suffisso_partita, data_impianto,
                  data_chiusura, numero_provenienza, stato, tipo)

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    result = cur.fetchone()
                    if result and result[0]:
                        self.logger.info(f"Partita N.{numero_partita} creata con successo. ID: {result[0]}")
                        return result[0]
                    else:
                        raise DBMError("Creazione partita fallita, nessun ID restituito.")
        except psycopg2.errors.UniqueViolation as e:
            # Rileva violazione del vincolo di unicità (comune_id, numero_partita, suffisso_partita)
            raise DBUniqueConstraintError(f"Esiste già una partita con questo numero e suffisso nel comune selezionato.") from e
        except Exception as e:
            self.logger.error(f"Errore DB durante la creazione della partita: {e}", exc_info=True)
            raise DBMError(f"Errore imprevisto durante la creazione della partita: {e}") from e
    

    # In catasto_db_manager.py

    def get_elenco_variazioni_per_esportazione(self, comune_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Recupera un elenco completo di variazioni, usando la vista aggiornata."""
        query = f"SELECT * FROM {self.schema}.v_variazioni_complete"
        params = []
        
        if comune_id:
            # Recupera il nome del comune dall'ID per filtrare sulla vista
            # Questa è una chiamata aggiuntiva al DB.
            # Se la vista potesse includere direttamente l'ID, sarebbe più efficiente.
            comune_info = self.get_comune_by_id(comune_id) # Presumo esista o lo creiamo
            if comune_info and comune_info.get('nome_comune'): # Usa 'nome_comune' come chiave
                comune_nome = comune_info['nome_comune']
                # --- INIZIO CORREZIONE: Filtra sulla colonna 'partita_origine_comune' ---
                query += " WHERE partita_origine_comune = %s"
                params.append(comune_nome)
                # --- FINE CORREZIONE ---
            else:
                self.logger.warning(f"Nome comune non trovato per ID {comune_id}. Impossibile filtrare le variazioni.")
                # Se il comune ID non è valido o non trova il nome, non aggiunge il filtro.
                # Questo potrebbe portare a un elenco completo anziché filtrato.
                # Decidi se vuoi sollevare un'eccezione o restituire una lista vuota in questo caso.
                # Per ora, non filtra e procede con l'elenco completo.

        query += " ORDER BY data_variazione DESC;"

        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(query, params)
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            # Incapsula l'errore per dare più contesto al chiamante GUI
            raise DBMError(f"Impossibile recuperare l'elenco delle variazioni: {e}") from e

    # --- NUOVO METODO: Aggiungi questo metodo alla classe CatastoDBManager ---
    def get_comune_by_id(self, comune_id: int) -> Optional[Dict[str, Any]]:
        """Recupera i dettagli di un comune tramite il suo ID."""
        if not isinstance(comune_id, int) or comune_id <= 0:
            self.logger.error(f"get_comune_by_id: ID comune non valido: {comune_id}")
            return None
        
        query = f"""
            SELECT id, nome AS nome_comune, provincia, regione, codice_catastale, periodo_id,
                   data_istituzione, data_soppressione, note
            FROM {self.schema}.comune
            WHERE id = %s;
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(query, (comune_id,))
                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            self.logger.error(f"Errore DB in get_comune_by_id (ID: {comune_id}): {e}", exc_info=True)
            return None
    def get_report_consistenza_patrimoniale(self, comune_id: int) -> Dict[str, List[Dict]]:
        """
        Genera i dati per un report di consistenza patrimoniale per un dato comune.
        Logica corretta: trova le proprietà nel comune e poi raggruppa per possessore.
        """
        if not comune_id:
            raise DBDataError("È necessario specificare un comune per questo report.")

        report_data = {}

        # 1. Trova tutti i possessori unici che hanno partite nel comune specificato
        query_possessori = f"""
            SELECT DISTINCT pos.id, pos.nome_completo
            FROM {self.schema}.possessore pos
            JOIN {self.schema}.partita_possessore pp ON pos.id = pp.possessore_id
            JOIN {self.schema}.partita p ON pp.partita_id = p.id
            WHERE p.comune_id = %s AND pos.attivo = TRUE
            ORDER BY pos.nome_completo;
        """

        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(query_possessori, (comune_id,))
                    possessori_nel_comune = [dict(row) for row in cur.fetchall()]

            # 2. Per ogni possessore trovato, recupera i dettagli delle sue partite in quel comune
            for p in possessori_nel_comune:
                possessore_id = p['id']
                possessore_nome = p['nome_completo']

                # Questa funzione recupera tutte le partite di un possessore
                tutte_le_partite = self.get_partite_per_possessore(possessore_id)

                # Filtriamo in Python per mantenere solo quelle del comune richiesto
                partite_nel_comune_selezionato = []
                for partita in tutte_le_partite:
                    # Dobbiamo unire i dati del comune per poter filtrare.
                    # Modifichiamo get_partite_per_possessore per includere comune_id.
                    if partita.get('comune_id') == comune_id:
                        partite_nel_comune_selezionato.append(partita)

                if partite_nel_comune_selezionato:
                    report_data[possessore_nome] = partite_nel_comune_selezionato

            return report_data

        except Exception as e:
            self.logger.error(f"Errore DB durante generazione report consistenza per comune ID {comune_id}: {e}", exc_info=True)
            raise DBMError(f"Impossibile generare il report di consistenza: {e}") from e


    def get_possessori_by_comune(self, comune_id: int, filter_text: Optional[str] = None, solo_con_partite: bool = False) -> List[Dict[str, Any]]:
        """
        Recupera i possessori per un dato comune, con filtri opzionali.
        Se solo_con_partite è True, restituisce solo i possessori con almeno una partita associata.
        """
        if not isinstance(comune_id, int) or comune_id <= 0:
            raise DBDataError("ID comune non valido.")

        params: List[Union[int, str]] = [comune_id]

        # --- INIZIO CORREZIONE: Query modificata per conteggio e filtro partite ---
        query_base = f"""
            SELECT 
                p.id, 
                c.nome as comune_nome, 
                p.cognome_nome, 
                p.paternita, 
                p.nome_completo, 
                p.attivo,
                COUNT(pp.partita_id) as num_partite
            FROM {self.schema}.possessore p
            JOIN {self.schema}.comune c ON p.comune_id = c.id
            LEFT JOIN {self.schema}.partita_possessore pp ON p.id = pp.possessore_id
            WHERE p.comune_id = %s
        """

        where_clauses = []
        if filter_text:
            where_clauses.append("(p.nome_completo ILIKE %s OR p.cognome_nome ILIKE %s)")
            params.extend([f"%{filter_text}%", f"%{filter_text}%"])

        if where_clauses:
            query_base += " AND " + " AND ".join(where_clauses)

        # Raggruppiamo sempre per calcolare num_partite
        query_base += " GROUP BY p.id, c.nome"

        # Aggiungiamo il filtro HAVING se richiesto
        if solo_con_partite:
            query_base += " HAVING COUNT(pp.partita_id) > 0"

        query = query_base + " ORDER BY p.nome_completo;"
        # --- FINE CORREZIONE ---

        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(query, tuple(params))
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            self.logger.error(f"Errore DB in get_possessori_by_comune: {e}", exc_info=True)
            raise DBMError("Impossibile recuperare i possessori.") from e
    
    
    def get_partite_per_possessore(self, possessore_id: int) -> List[Dict[str, Any]]:
            if not possessore_id > 0: raise DBDataError("ID possessore non valido.")
            query = f"""
                SELECT p.id, p.numero_partita, p.suffisso_partita, p.tipo, p.stato, 
                    c.id as comune_id, c.nome as comune_nome, pp.titolo, pp.quota
                FROM {self.schema}.partita p
                JOIN {self.schema}.comune c ON p.comune_id = c.id
                JOIN {self.schema}.partita_possessore pp ON p.id = pp.partita_id
                WHERE pp.possessore_id = %s ORDER BY c.nome, p.numero_partita;
            """
            try:
                with self._get_connection() as conn:
                    with conn.cursor(cursor_factory=DictCursor) as cur:
                        cur.execute(query, (possessore_id,))
                        return [dict(row) for row in cur.fetchall()]
            except Exception as e:
                self.logger.error(f"Errore in get_partite_per_possessore: {e}", exc_info=True)
                raise DBMError("Impossibile recuperare le partite per il possessore.") from e
    

    def get_elenco_immobili_per_esportazione(self, comune_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Recupera un elenco completo di immobili per l'esportazione."""
        query = f"""
            SELECT 
                i.id AS id_immobile, i.natura, i.classificazione, i.consistenza,
                i.numero_piani, i.numero_vani, l.nome AS localita_nome, 
                tl.nome AS localita_tipo, l.civico, p.numero_partita, 
                p.suffisso_partita, c.nome AS comune_nome
            FROM {self.schema}.immobile i
            JOIN {self.schema}.partita p ON i.partita_id = p.id
            JOIN {self.schema}.comune c ON p.comune_id = c.id
            JOIN {self.schema}.localita l ON i.localita_id = l.id
            LEFT JOIN {self.schema}.tipo_localita tl ON l.tipo_id = tl.id
        """
        params = []
        if comune_id:
            query += " WHERE p.comune_id = %s"
            params.append(comune_id)
        query += " ORDER BY c.nome, p.numero_partita, l.nome, i.natura;"
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(query, params)
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            raise DBMError(f"Impossibile recuperare l'elenco degli immobili: {e}") from e

    def get_elenco_localita_per_esportazione(self, comune_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Recupera un elenco completo di località per l'esportazione."""
        query = f"""
            SELECT l.id, l.nome, tl.nome AS tipo, l.civico, c.nome AS comune_nome
            FROM {self.schema}.localita l
            JOIN {self.schema}.comune c ON l.comune_id = c.id
            LEFT JOIN {self.schema}.tipo_localita tl ON l.tipo_id = tl.id
        """
        params = []
        if comune_id:
            query += " WHERE l.comune_id = %s"
            params.append(comune_id)
        query += " ORDER BY c.nome, l.nome;"
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(query, params)
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            raise DBMError(f"Impossibile recuperare l'elenco delle località: {e}") from e
    
    def get_localita_by_comune(self, comune_id: int, filter_text: Optional[str] = None) -> List[Dict[str, Any]]:
        """Recupera località per comune_id, unendo il nome del tipo dalla nuova tabella."""
        if not isinstance(comune_id, int) or comune_id <= 0:
            raise DBDataError("ID comune non valido.")

        # --- INIZIO CORREZIONE: Query aggiornata con JOIN ---
        query_base = f"""
            SELECT 
                loc.id, 
                loc.nome, 
                tl.nome AS tipo,  -- Selezioniamo il nome dalla tabella tipo_localita
                loc.civico 
            FROM {self.schema}.localita loc
            LEFT JOIN {self.schema}.tipo_localita tl ON loc.tipo_id = tl.id
            WHERE loc.comune_id = %s
        """
        # --- FINE CORREZIONE ---

        params: List[Union[int, str]] = [comune_id]

        if filter_text:
            query_base += " AND loc.nome ILIKE %s"
            params.append(f"%{filter_text}%")

        query = query_base + " ORDER BY tl.nome, loc.nome, loc.civico;"

        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, tuple(params))
                    results = [dict(row) for row in cur.fetchall()]
                    self.logger.info(f"Recuperate {len(results)} località per comune ID {comune_id} (filtro: '{filter_text}').")
                    return results
        except Exception as e:
            self.logger.error(f"Errore DB in get_localita_by_comune: {e}", exc_info=True)
            return [] # Restituisce lista vuota in caso di errore
    def search_possessori_by_term_globally(self, search_term: Optional[str], limit: int = 200) -> List[Dict[str, Any]]:
        """
        Ricerca possessori globalmente, usando il nuovo pattern di connessione.
        """
        query_base = f"""
            SELECT p.id, p.nome_completo, p.cognome_nome, p.paternita, p.attivo,
                c.nome AS comune_riferimento_nome 
            FROM {self.schema}.possessore p
            LEFT JOIN {self.schema}.comune c ON p.comune_id = c.id 
        """
        
        params: List[Union[str, int]] = []
        where_clauses = []

        if search_term and search_term.strip():
            like_term = f"%{search_term.strip()}%"
            where_clauses.append("(p.nome_completo ILIKE %s OR p.cognome_nome ILIKE %s OR p.paternita ILIKE %s)")
            params.extend([like_term, like_term, like_term])
        
        query = query_base
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY p.nome_completo LIMIT %s;"
        params.append(limit)
        
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, tuple(params))
                    rows = cur.fetchall()
                    data_list = [dict(row) for row in rows]
                    self.logger.info(f"search_possessori_by_term_globally ha trovato {len(data_list)} possessori.")
                    return data_list
        except Exception as e:
            self.logger.error(f"Errore DB in search_possessori_by_term_globally: {e}", exc_info=True)
            return []
        
    def get_possessori_per_partita(self, partita_id: int) -> List[Dict[str, Any]]:
        """
        Recupera tutti i possessori associati a una data partita, inclusi i dettagli
        del legame dalla tabella partita_possessore.
        """
        if not isinstance(partita_id, int) or partita_id <= 0:
            self.logger.error("get_possessori_per_partita: partita_id non valido.")
            return []

        query = f"""
            SELECT
                pp.id AS id_relazione_partita_possessore,
                pos.id AS possessore_id,
                pos.nome_completo AS nome_completo_possessore,
                pos.paternita AS paternita_possessore, 
                pp.titolo AS titolo_possesso,
                pp.quota AS quota_possesso,
                pp.tipo_partita AS tipo_partita_rel 
            FROM {self.schema}.partita_possessore pp
            JOIN {self.schema}.possessore pos ON pp.possessore_id = pos.id
            WHERE pp.partita_id = %s
            ORDER BY pos.nome_completo;
        """
        
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, (partita_id,))
                    results = [dict(row) for row in cur.fetchall()]
                    self.logger.info(f"Trovati {len(results)} possessori per la partita ID {partita_id}.")
                    return results
        except Exception as e:
            self.logger.error(f"Errore DB durante il recupero dei possessori per la partita ID {partita_id}: {e}", exc_info=True)
            # In caso di errore, restituisce una lista vuota per stabilità
            return []
    def insert_localita(self, comune_id: int, nome: str, tipo_id: int, civico: Optional[int] = None) -> int:
        """
        Inserisce una nuova località usando tipo_id (FK) e gestisce i conflitti.
        """
        if not all([isinstance(comune_id, int), comune_id > 0, isinstance(nome, str), nome.strip(), isinstance(tipo_id, int), tipo_id > 0]):
            raise DBDataError("Parametri per l'inserimento della località non validi.")

        actual_civico = civico if civico is not None and civico > 0 else None

        # La colonna ora è 'tipo_id'
        query_insert = f"INSERT INTO {self.schema}.localita (comune_id, nome, tipo_id, civico) VALUES (%s, %s, %s, %s) ON CONFLICT (comune_id, nome, civico) DO NOTHING RETURNING id;"
        # Anche la query di select deve usare tipo_id, ma per ora non è strettamente necessaria se il recupero avviene dopo
        query_select = f"SELECT id FROM {self.schema}.localita WHERE comune_id = %s AND nome = %s AND tipo_id = %s AND ((civico IS NULL AND %s IS NULL) OR (civico = %s));"

        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(query_insert, (comune_id, nome.strip(), tipo_id, actual_civico))
                    insert_result = cur.fetchone()

                    if insert_result and insert_result['id']:
                        localita_id = insert_result['id']
                        self.logger.info(f"Località '{nome}' inserita con successo. ID: {localita_id}.")
                    else: # Conflitto, recupera l'ID esistente
                        cur.execute(query_select, (comune_id, nome.strip(), tipo_id, actual_civico, actual_civico))
                        select_result = cur.fetchone()
                        if select_result and select_result['id']:
                            localita_id = select_result['id']
                            self.logger.info(f"Località '{nome}' già esistente trovata. ID: {localita_id}.")
                        else:
                            raise DBMError(f"Logica inconsistente: impossibile inserire o trovare la località '{nome}'.")
            return localita_id
        except Exception as e:
            self.logger.error(f"Errore in insert_localita per '{nome}': {e}", exc_info=True)
            raise DBMError(f"Errore database durante l'operazione sulla località: {e}") from e

    def get_localita_details(self, localita_id: int) -> Optional[Dict[str, Any]]:
        """Recupera i dettagli di una singola località, incluso il nome del comune."""
        if not isinstance(localita_id, int) or localita_id <= 0: return None

        query = f"""
            SELECT loc.id, loc.nome, loc.tipo, loc.civico, loc.comune_id, com.nome AS comune_nome
            FROM {self.schema}.localita loc
            JOIN {self.schema}.comune com ON loc.comune_id = com.id
            WHERE loc.id = %s;
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, (localita_id,))
                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            self.logger.error(f"Errore DB in get_localita_details per ID {localita_id}: {e}", exc_info=True)
            return None
    def update_localita(self, localita_id: int, dati_modificati: Dict[str, Any]):
        """Aggiorna i dati di una località esistente, usando tipo_id."""
        if not (isinstance(localita_id, int) and localita_id > 0): raise DBDataError("ID località non valido.")
        if not isinstance(dati_modificati, dict) or not dati_modificati: raise DBDataError("Dati per aggiornamento non validi.")

        set_clauses = []
        params = []

        if "nome" in dati_modificati and dati_modificati["nome"] and dati_modificati["nome"].strip():
            set_clauses.append("nome = %s")
            params.append(dati_modificati["nome"].strip())

        # --- MODIFICA CHIAVE QUI ---
        if "tipo_id" in dati_modificati and dati_modificati["tipo_id"] is not None:
            set_clauses.append("tipo_id = %s")
            params.append(dati_modificati["tipo_id"])
        # --- FINE MODIFICA ---

        if "civico" in dati_modificati:
            set_clauses.append("civico = %s")
            params.append(dati_modificati["civico"] if dati_modificati["civico"] else None)

        if not set_clauses:
            self.logger.info(f"Nessun campo valido fornito per aggiornare località ID {localita_id}.")
            return

        set_clauses.append("data_modifica = CURRENT_TIMESTAMP")
        query = f"UPDATE {self.schema}.localita SET {', '.join(set_clauses)} WHERE id = %s;"
        params.append(localita_id)

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, tuple(params))
                    if cur.rowcount == 0:
                        raise DBNotFoundError(f"Nessuna località trovata con ID {localita_id} da aggiornare.")
            self.logger.info(f"Località ID {localita_id} aggiornata con successo.")
        except Exception as e:
            self.logger.error(f"Errore DB aggiornando località ID {localita_id}: {e}", exc_info=True)
            raise DBMError(f"Impossibile aggiornare la località: {e}") from e


    
    def get_partite_by_comune(self, comune_id: int, filter_text: Optional[str] = None) -> List[Dict[str, Any]]:
        """Recupera le partite per un dato comune con un filtro opzionale."""
        if not isinstance(comune_id, int) or comune_id <= 0:
            raise DBDataError("ID comune non valido.")

        query_base = f"""
            SELECT
                p.id, p.numero_partita, p.suffisso_partita, p.tipo, p.stato, p.data_impianto,
                (SELECT COUNT(*) FROM {self.schema}.partita_possessore pp WHERE pp.partita_id = p.id) as num_possessori,
                (SELECT COUNT(*) FROM {self.schema}.immobile i WHERE i.partita_id = p.id) as num_immobili,
                (SELECT COUNT(*) FROM {self.schema}.documento_partita dp WHERE dp.partita_id = p.id) as num_documenti_allegati
            FROM {self.schema}.partita p
            WHERE p.comune_id = %s
        """
        params: List[Union[int, str]] = [comune_id]

        if filter_text:
            query_base += " AND (CAST(p.numero_partita AS TEXT) ILIKE %s OR p.tipo ILIKE %s OR p.stato ILIKE %s OR p.suffisso_partita ILIKE %s)"
            filter_like = f"%{filter_text}%"
            params.extend([filter_like, filter_like, filter_like, filter_like])

        query = query_base + " ORDER BY p.numero_partita, p.suffisso_partita;"

        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, tuple(params))
                    partite_list = [dict(row) for row in cur.fetchall()]
                    self.logger.info(f"Recuperate {len(partite_list)} partite per comune ID {comune_id}.")
                    return partite_list
        except Exception as e:
            self.logger.error(f"Errore DB in get_partite_by_comune: {e}", exc_info=True)
            raise DBMError(f"Errore di sistema durante il recupero delle partite: {e}") from e
    def get_partita_details(self, partita_id: int) -> Optional[Dict[str, Any]]:
        """Recupera dettagli completi di una partita, usando una singola connessione e transazione."""
        if not isinstance(partita_id, int) or partita_id <= 0:
            return None

        partita_details: Dict[str, Any] = {}
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    # 1. Info base partita (invariato)
                    query_partita = f"SELECT p.*, c.nome as comune_nome, c.id as comune_id FROM {self.schema}.partita p JOIN {self.schema}.comune c ON p.comune_id = c.id WHERE p.id = %s;"
                    cur.execute(query_partita, (partita_id,))
                    partita_base = cur.fetchone()
                    if not partita_base:
                        self.logger.warning(f"Partita ID {partita_id} non trovata.")
                        return None
                    partita_details.update(dict(partita_base))

                    # 2. Possessori (invariato)
                    query_poss = f"SELECT pos.id, pos.nome_completo, pp.titolo, pp.quota FROM {self.schema}.possessore pos JOIN {self.schema}.partita_possessore pp ON pos.id = pp.possessore_id WHERE pp.partita_id = %s ORDER BY pos.nome_completo;"
                    cur.execute(query_poss, (partita_id,))
                    partita_details['possessori'] = [dict(row) for row in cur.fetchall()]

                    # --- INIZIO CORREZIONE QUI ---
                    # 3. Immobili (query aggiornata con JOIN a tipo_localita)
                    query_imm = f"""
                        SELECT i.id, i.natura, i.numero_piani, i.numero_vani, i.consistenza, 
                            i.classificazione, l.nome as localita_nome, tl.nome as localita_tipo, l.civico 
                        FROM {self.schema}.immobile i 
                        JOIN {self.schema}.localita l ON i.localita_id = l.id
                        LEFT JOIN {self.schema}.tipo_localita tl ON l.tipo_id = tl.id
                        WHERE i.partita_id = %s 
                        ORDER BY l.nome, i.natura;
                    """
                    # --- FINE CORREZIONE QUI ---
                    cur.execute(query_imm, (partita_id,))
                    partita_details['immobili'] = [dict(row) for row in cur.fetchall()]

                    # 4. Variazioni (invariato)
                    query_var = f"""
                        SELECT v.*, con.tipo as tipo_contratto, con.data_contratto, con.notaio, con.repertorio, con.note as contratto_note,
                            po.numero_partita AS origine_numero_partita, co.nome AS origine_comune_nome,
                            pd.numero_partita AS destinazione_numero_partita, cd.nome AS destinazione_comune_nome
                        FROM {self.schema}.variazione v 
                        LEFT JOIN {self.schema}.contratto con ON v.id = con.variazione_id
                        LEFT JOIN {self.schema}.partita po ON v.partita_origine_id = po.id
                        LEFT JOIN {self.schema}.comune co ON po.comune_id = co.id
                        LEFT JOIN {self.schema}.partita pd ON v.partita_destinazione_id = pd.id
                        LEFT JOIN {self.schema}.comune cd ON pd.comune_id = cd.id
                        WHERE v.partita_origine_id = %s OR v.partita_destinazione_id = %s
                        ORDER BY v.data_variazione DESC;
                    """
                    cur.execute(query_var, (partita_id, partita_id))
                    partita_details['variazioni'] = [dict(row) for row in cur.fetchall()]

            self.logger.info(f"Dettagli completi recuperati per partita ID {partita_id}.")
            return partita_details

        except Exception as e:
            self.logger.error(f"Errore DB in get_partita_details (ID: {partita_id}): {e}", exc_info=True)
            return None
    def update_partita(self, partita_id: int, dati_modificati: Dict[str, Any]):
        """Aggiorna i dati di una partita esistente in modo transazionale e sicuro."""
        if not isinstance(partita_id, int) or partita_id <= 0:
            raise DBDataError(f"ID partita non valido: {partita_id}")
        if not dati_modificati:
            self.logger.info("Nessun dato fornito per l'aggiornamento della partita.")
            return

        allowed_fields = ["numero_partita", "tipo", "stato", "data_impianto", "data_chiusura", "numero_provenienza"]
        set_clauses = [f"{field} = %s" for field in allowed_fields if field in dati_modificati]
        params = [dati_modificati[field] for field in allowed_fields if field in dati_modificati]

        if "suffisso_partita" in dati_modificati:
            set_clauses.append("suffisso_partita = %s")
            params.append(dati_modificati["suffisso_partita"])
        
        if not set_clauses:
            self.logger.info("Nessun campo valido fornito per l'aggiornamento della partita.")
            return

        set_clauses.append("data_modifica = CURRENT_TIMESTAMP")
        params.append(partita_id)
        query = f"UPDATE {self.schema}.partita SET {', '.join(set_clauses)} WHERE id = %s;"

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, tuple(params))
                    if cur.rowcount == 0:
                        # L'eccezione causerà un rollback automatico
                        raise DBNotFoundError(f"Nessuna partita trovata con ID {partita_id} per l'aggiornamento.")
            # Il commit è automatico qui
            self.logger.info(f"Partita ID {partita_id} aggiornata con successo.")
        except Exception as e:
            self.logger.error(f"Errore DB aggiornando partita ID {partita_id}: {e}", exc_info=True)
            # Rilancia come DBMError per il chiamante
            raise DBMError(f"Impossibile aggiornare la partita: {e}") from e
    def update_comune(self, comune_id: int, dati_modificati: Dict[str, Any]) -> bool:
        """
        Aggiorna i dati di un comune esistente in modo transazionale e sicuro.
        """
        if not isinstance(comune_id, int) or comune_id <= 0:
            raise DBDataError(f"ID comune non valido per l'aggiornamento: {comune_id}")
        if not dati_modificati:
            self.logger.info(f"Nessun dato fornito per aggiornare comune ID {comune_id}.")
            return True

        # La logica per costruire la query dinamicamente rimane invariata
        allowed_fields_map = {
            "nome": "nome", "provincia": "provincia", "regione": "regione",
            "codice_catastale": "codice_catastale", "periodo_id": "periodo_id",
            "data_istituzione": "data_istituzione", "data_soppressione": "data_soppressione",
            "note": "note"
        }
        set_clauses = [f"{col_db} = %s" for key_dict, col_db in allowed_fields_map.items() if key_dict in dati_modificati]
        params = [dati_modificati[key] for key in allowed_fields_map if key in dati_modificati]

        if not set_clauses:
            self.logger.info(f"Nessun campo valido fornito per aggiornare comune ID {comune_id}.")
            return True 

        set_clauses.append("data_modifica = CURRENT_TIMESTAMP")
        query = f"UPDATE {self.schema}.comune SET {', '.join(set_clauses)} WHERE id = %s"
        params.append(comune_id)
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, tuple(params))
                    if cur.rowcount == 0:
                        # Se non sono state modificate righe, verifichiamo se il comune esiste.
                        # Se non esiste, solleviamo un errore che causerà un rollback automatico.
                        cur.execute(f"SELECT 1 FROM {self.schema}.comune WHERE id = %s", (comune_id,))
                        if not cur.fetchone():
                            raise DBNotFoundError(f"Comune con ID {comune_id} non trovato per l'aggiornamento.")
                        self.logger.info(f"Nessuna modifica effettiva per comune ID {comune_id} (dati già aggiornati).")
            
            # Il commit viene eseguito automaticamente qui se non ci sono state eccezioni
            self.logger.info(f"Comune ID {comune_id} aggiornato con successo.")
            return True
            
        except (DBNotFoundError, DBDataError, DBUniqueConstraintError, psycopg2.errors.ForeignKeyViolation) as e:
            self.logger.error(f"Errore previsto aggiornando comune ID {comune_id}: {e}", exc_info=True)
            # Rilancia l'eccezione specifica per una gestione mirata nell'UI
            raise e
        except Exception as e:
            self.logger.error(f"Errore imprevisto DB aggiornando comune ID {comune_id}: {e}", exc_info=True)
            raise DBMError(f"Impossibile aggiornare il comune: {e}") from e
    
    def update_possessore(self, possessore_id: int, dati_modificati: Dict[str, Any]):
        """Aggiorna i dati di un possessore esistente in modo transazionale e sicuro."""
        if not isinstance(possessore_id, int) or possessore_id <= 0:
            raise DBDataError(f"ID possessore non valido: {possessore_id}")
        if not dati_modificati:
            self.logger.info(f"Nessun dato fornito per aggiornare possessore ID {possessore_id}.")
            return

        # Logica di costruzione query (invariata)
        set_clauses, params = [], []
        allowed_fields = {
            "nome_completo": "nome_completo", "cognome_nome": "cognome_nome",
            "paternita": "paternita", "attivo": "attivo",
            "comune_riferimento_id": "comune_id",
        }
        for key, col in allowed_fields.items():
            if key in dati_modificati:
                set_clauses.append(f"{col} = %s")
                params.append(dati_modificati[key])

        if not set_clauses:
            self.logger.info(f"Nessun campo valido da aggiornare per possessore {possessore_id}.")
            return
            
        set_clauses.append("data_modifica = CURRENT_TIMESTAMP")
        query = f"UPDATE {self.schema}.possessore SET {', '.join(set_clauses)} WHERE id = %s;"
        params.append(possessore_id)

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, tuple(params))
                    if cur.rowcount == 0:
                        raise DBNotFoundError(f"Nessun possessore trovato con ID {possessore_id} da aggiornare.")
            
            self.logger.info(f"Possessore ID {possessore_id} aggiornato con successo.")

        except (DBNotFoundError, DBDataError, DBUniqueConstraintError) as e:
            self.logger.error(f"Errore previsto aggiornando possessore {possessore_id}: {e}", exc_info=True)
            raise e
        except Exception as e:
            self.logger.error(f"Errore imprevisto DB aggiornando possessore {possessore_id}: {e}", exc_info=True)
            raise DBMError(f"Impossibile aggiornare il possessore: {e}") from e
        
    def search_partite(self, comune_id: Optional[int] = None, numero_partita: Optional[int] = None,
                    possessore: Optional[str] = None, immobile_natura: Optional[str] = None,
                    suffisso_partita: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Ricerca partite con filtri multipli, usando il nuovo pattern di connessione sicuro.
        """
        try:
            # La logica di costruzione della query rimane invariata
            conditions, params, joins = [], [], ""
            select_cols = "p.id, c.nome as comune_nome, p.numero_partita, p.suffisso_partita, p.tipo, p.stato" 
            query_base = f"SELECT DISTINCT {select_cols} FROM {self.schema}.partita p JOIN {self.schema}.comune c ON p.comune_id = c.id"

            if possessore:
                joins += f" JOIN {self.schema}.partita_possessore pp ON p.id = pp.partita_id JOIN {self.schema}.possessore pos ON pp.possessore_id = pos.id"
                conditions.append("pos.nome_completo ILIKE %s")
                params.append(f"%{possessore}%")
            if immobile_natura:
                joins += f" JOIN {self.schema}.immobile i ON p.id = i.partita_id"
                conditions.append("i.natura ILIKE %s")
                params.append(f"%{immobile_natura}%")
            if comune_id is not None:
                conditions.append("p.comune_id = %s")
                params.append(comune_id)
            if numero_partita is not None:
                conditions.append("p.numero_partita = %s")
                params.append(numero_partita)
            if suffisso_partita is not None:
                if suffisso_partita.strip() == "":
                    conditions.append("p.suffisso_partita IS NULL")
                else:
                    conditions.append("p.suffisso_partita ILIKE %s")
                    params.append(f"%{suffisso_partita.strip()}%")

            query = query_base + joins
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY c.nome, p.numero_partita"

            self.logger.debug(f"search_partite - Query: {query} - Params: {tuple(params)}")

            # Esecuzione della query con il context manager
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, tuple(params))
                    results = [dict(row) for row in cur.fetchall()]
                    self.logger.info(f"search_partite - Trovate {len(results)} partite.")
                    return results

        except Exception as e:
            self.logger.error(f"Errore DB in search_partite: {e}", exc_info=True)
            return [] # Restituisce una lista vuota in caso di errore
    def search_immobili(self, partita_id: Optional[int] = None, comune_id: Optional[int] = None, # Usa comune_id
                        localita_id: Optional[int] = None, natura: Optional[str] = None,
                        classificazione: Optional[str] = None) -> List[Dict]:
        """Chiama la funzione SQL cerca_immobili (MODIFICATA per comune_id)."""
        try:
            # Funzione SQL aggiornata per comune_id
            query = "SELECT * FROM cerca_immobili(%s, %s, %s, %s, %s)"
            params = (partita_id, comune_id, localita_id, natura, classificazione) # Passa ID
            if self.execute_query(query, params): return self.fetchall()
        except psycopg2.Error as db_err: logger.error(f"Errore DB in search_immobili: {db_err}")
        except Exception as e: logger.error(f"Errore Python in search_immobili: {e}")
        return []

    def search_variazioni(self, tipo: Optional[str] = None, data_inizio: Optional[date] = None,
                          data_fine: Optional[date] = None, partita_origine_id: Optional[int] = None,
                          partita_destinazione_id: Optional[int] = None, comune_id: Optional[int] = None) -> List[Dict]: # Usa comune_id
        """Chiama la funzione SQL cerca_variazioni (MODIFICATA per comune_id)."""
        try:
            # Funzione SQL aggiornata per comune_id
            query = "SELECT * FROM cerca_variazioni(%s, %s, %s, %s, %s, %s)"
            params = (tipo, data_inizio, data_fine, partita_origine_id, partita_destinazione_id, comune_id) # Passa ID
            if self.execute_query(query, params): return self.fetchall()
        except psycopg2.Error as db_err: logger.error(f"Errore DB in search_variazioni: {db_err}")
        except Exception as e: logger.error(f"Errore Python in search_variazioni: {e}")
        return []

    def search_consultazioni(self, data_inizio: Optional[date] = None, data_fine: Optional[date] = None,
                             richiedente: Optional[str] = None, funzionario: Optional[str] = None) -> List[Dict]:
        """Chiama la funzione SQL cerca_consultazioni (invariata rispetto a comune_id)."""
        try:
            query = "SELECT * FROM cerca_consultazioni(%s, %s, %s, %s)"
            params = (data_inizio, data_fine, richiedente, funzionario)
            if self.execute_query(query, params): return self.fetchall()
        except psycopg2.Error as db_err: logger.error(f"Errore DB in search_consultazioni: {db_err}")
        except Exception as e: logger.error(f"Errore Python in search_consultazioni: {e}")
        return []

    # --- Metodi CRUD specifici (invariati rispetto a comune_id) ---
    def update_immobile(self, immobile_id: int, **kwargs) -> bool:
        """Chiama la procedura SQL aggiorna_immobile."""
        params = {'p_id': immobile_id, 'p_natura': kwargs.get('natura'), 'p_numero_piani': kwargs.get('numero_piani'),
                  'p_numero_vani': kwargs.get('numero_vani'), 'p_consistenza': kwargs.get('consistenza'),
                  'p_classificazione': kwargs.get('classificazione'), 'p_localita_id': kwargs.get('localita_id')}
        call_proc = "CALL aggiorna_immobile(%(p_id)s, %(p_natura)s, %(p_numero_piani)s, %(p_numero_vani)s, %(p_consistenza)s, %(p_classificazione)s, %(p_localita_id)s)"
        try:
            if self.execute_query(call_proc, params): self.commit(); logger.info(f"Immobile ID {immobile_id} aggiornato."); return True
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB aggiornamento immobile ID {immobile_id}: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python aggiornamento immobile ID {immobile_id}: {e}"); self.rollback(); return False

    def delete_immobile(self, immobile_id):
        """
        Elimina un immobile dal database utilizzando una procedura memorizzata
        e gestendo la transazione in modo sicuro con il connection pool.
        """
        call_proc = "SELECT public.delete_immobile_by_id(%s);"
        conn = None  # Inizializza la variabile della connessione
        try:
            # 1. Ottieni una connessione dal pool
            conn = self.pool.getconn()
            
            # 2. Utilizza la connessione con un blocco 'with' per il cursore
            with conn.cursor() as cur:
                # 3. Esegui la query/procedura sul cursore
                cur.execute(call_proc, (immobile_id,))
                
                # 4. Esegui il commit sulla connessione
                conn.commit()
                
                logger.info(f"Immobile ID {immobile_id} eliminato con successo.")
                return True
                
        except Exception as e:
            # Se si verifica un errore, esegui il rollback
            if conn:
                conn.rollback()
            logger.error(f"Errore durante l'eliminazione dell'immobile ID {immobile_id}: {e}")
            return False
            
        finally:
            # 5. Rilascia SEMPRE la connessione al pool
            if conn:
                self.pool.putconn(conn)
    def update_variazione(self, variazione_id: int, **kwargs) -> bool:
        """Chiama la procedura SQL aggiorna_variazione."""
        params = {'p_variazione_id': variazione_id, 'p_tipo': kwargs.get('tipo'), 'p_data_variazione': kwargs.get('data_variazione'),
                  'p_numero_riferimento': kwargs.get('numero_riferimento'), 'p_nominativo_riferimento': kwargs.get('nominativo_riferimento')}
        call_proc = "CALL aggiorna_variazione(%(p_variazione_id)s, %(p_tipo)s, %(p_data_variazione)s, %(p_numero_riferimento)s, %(p_nominativo_riferimento)s)"
        try:
            if self.execute_query(call_proc, params): self.commit(); logger.info(f"Variazione ID {variazione_id} aggiornata."); return True
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB aggiornamento variazione ID {variazione_id}: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python aggiornamento variazione ID {variazione_id}: {e}"); self.rollback(); return False

    def delete_variazione(self, variazione_id: int, force: bool = False, restore_partita: bool = False) -> bool:
        """Chiama la procedura SQL elimina_variazione."""
        call_proc = "CALL elimina_variazione(%s, %s, %s)"
        try:
            if self.execute_query(call_proc, (variazione_id, force, restore_partita)): self.commit(); logger.info(f"Variazione ID {variazione_id} eliminata."); return True
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB eliminazione variazione ID {variazione_id}: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python eliminazione variazione ID {variazione_id}: {e}"); self.rollback(); return False

    def insert_contratto(self, variazione_id: int, tipo: str, data_contratto: date,
                         notaio: Optional[str] = None, repertorio: Optional[str] = None,
                         note: Optional[str] = None) -> bool:
        """Chiama la procedura SQL inserisci_contratto."""
        call_proc = "CALL inserisci_contratto(%s, %s, %s, %s, %s, %s)"
        params = (variazione_id, tipo, data_contratto, notaio, repertorio, note)
        try:
            if self.execute_query(call_proc, params): self.commit(); logger.info(f"Contratto inserito per variazione ID {variazione_id}."); return True
            return False
        except psycopg2.Error as db_err:
        # --- INIZIO CORREZIONE ---
        # Verifica se è l'eccezione specifica di contratto duplicato sollevata dalla procedura
        # Controlla il codice SQLSTATE ('P0001' per raise_exception) E il messaggio
            if hasattr(db_err, 'pgcode') and db_err.pgcode == 'P0001' and 'Esiste già un contratto' in str(db_err):
                logger.warning(f"Contratto per variazione ID {variazione_id} esiste già.")
            # --- FINE CORREZIONE ---
            else:
                # Logga altri errori DB generici
                logger.error(f"Errore DB inserimento contratto var ID {variazione_id}: {db_err}")
                # Potresti voler loggare anche db_err.pgcode e db_err.pgerror qui per più dettagli
                # logger.error(f"SQLSTATE: {db_err.pgcode} - Errore: {db_err.pgerror}")
            # In entrambi i casi (duplicato o altro errore DB), ritorna False
        return False
    def update_contratto(self, contratto_id: int, **kwargs) -> bool:
        """Chiama la procedura SQL aggiorna_contratto."""
        params = {'p_id': contratto_id, 'p_tipo': kwargs.get('tipo'), 'p_data_contratto': kwargs.get('data_contratto'),
                  'p_notaio': kwargs.get('notaio'), 'p_repertorio': kwargs.get('repertorio'), 'p_note': kwargs.get('note')}
        call_proc = "CALL aggiorna_contratto(%(p_id)s, %(p_tipo)s, %(p_data_contratto)s, %(p_notaio)s, %(p_repertorio)s, %(p_note)s)"
        try:
            if self.execute_query(call_proc, params): self.commit(); logger.info(f"Contratto ID {contratto_id} aggiornato."); return True
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB aggiornamento contratto ID {contratto_id}: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python aggiornamento contratto ID {contratto_id}: {e}"); self.rollback(); return False

    def delete_contratto(self, contratto_id: int) -> bool:
        """Chiama la procedura SQL elimina_contratto."""
        call_proc = "CALL elimina_contratto(%s)"
        try:
            if self.execute_query(call_proc, (contratto_id,)): self.commit(); logger.info(f"Contratto ID {contratto_id} eliminato."); return True
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB eliminazione contratto ID {contratto_id}: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python eliminazione contratto ID {contratto_id}: {e}"); self.rollback(); return False

    def update_consultazione(self, consultazione_id: int, **kwargs) -> bool:
        """Chiama la procedura SQL aggiorna_consultazione."""
        params = {'p_id': consultazione_id, 'p_data': kwargs.get('data'), 'p_richiedente': kwargs.get('richiedente'),
                  'p_documento_identita': kwargs.get('documento_identita'), 'p_motivazione': kwargs.get('motivazione'),
                  'p_materiale_consultato': kwargs.get('materiale_consultato'), 'p_funzionario_autorizzante': kwargs.get('funzionario_autorizzante')}
        call_proc = "CALL aggiorna_consultazione(%(p_id)s, %(p_data)s, %(p_richiedente)s, %(p_documento_identita)s, %(p_motivazione)s, %(p_materiale_consultato)s, %(p_funzionario_autorizzante)s)"
        try:
            if self.execute_query(call_proc, params): self.commit(); logger.info(f"Consultazione ID {consultazione_id} aggiornata."); return True
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB aggiornamento consultazione ID {consultazione_id}: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python aggiornamento consultazione ID {consultazione_id}: {e}"); self.rollback(); return False

    def delete_consultazione(self, consultazione_id: int) -> bool:
        """Chiama la procedura SQL elimina_consultazione."""
        call_proc = "CALL elimina_consultazione(%s)"
        try:
            if self.execute_query(call_proc, (consultazione_id,)): self.commit(); logger.info(f"Consultazione ID {consultazione_id} eliminata."); return True
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB eliminazione consultazione ID {consultazione_id}: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python eliminazione consultazione ID {consultazione_id}: {e}"); self.rollback(); return False

    # --- Metodi per Workflow Complessi (MODIFICATI per comune_id) ---
    def registra_nuova_consultazione(self,
                                    data_consultazione: date,
                                    richiedente: str,
                                    materiale_consultato: str,
                                    funzionario_autorizzante: Optional[str],
                                    documento_identita: Optional[str] = None,
                                    motivazione: Optional[str] = None
                                    ) -> int:
        """
        Registra una nuova consultazione nel database in modo transazionale e sicuro.
        """
        if not all([data_consultazione, richiedente, materiale_consultato]):
            raise DBDataError("Data, Richiedente e Materiale Consultato sono campi obbligatori.")

        query = f"""
            INSERT INTO {self.schema}.consultazione
                (data, richiedente, documento_identita, motivazione, materiale_consultato, funzionario_autorizzante)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id;
        """
        params = (
            data_consultazione,
            richiedente.strip(),
            documento_identita.strip() if documento_identita else None,
            motivazione.strip() if motivazione else None,
            materiale_consultato.strip(),
            funzionario_autorizzante.strip() if funzionario_autorizzante else None
        )
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    result = cur.fetchone()
                    if result and result[0] is not None:
                        new_id = result[0]
                        self.logger.info(f"Nuova consultazione registrata con successo. ID: {new_id}")
                        # Il commit è automatico all'uscita del blocco with
                        return new_id
                    else:
                        # Se non viene restituito un ID, solleva un'eccezione che causerà il rollback automatico
                        raise DBMError("Fallimento registrazione consultazione: nessun ID restituito.")
        except Exception as e:
            self.logger.error(f"Errore DB in registra_nuova_consultazione: {e}", exc_info=True)
            # Il rollback è automatico, rilanciamo un'eccezione chiara per il chiamante
            raise DBMError(f"Impossibile registrare la consultazione: {e}") from e

    # In catasto_db_manager.py, SOSTITUISCI il metodo registra_nuova_proprieta con questo:

    def registra_nuova_proprieta(self, comune_id: int, numero_partita: int, data_impianto: date,
                                 possessori_json_str: str,
                                 immobili_json_str: str,
                                 suffisso_partita: Optional[str] = None
                                ) -> int:
        """
        Chiama la procedura SQL per registrare una nuova proprietà, gestendo
        specificamente l'errore di partita duplicata.
        """
        if not (isinstance(comune_id, int) and comune_id > 0): raise DBDataError("ID comune non valido.")
        if not (isinstance(numero_partita, int) and numero_partita > 0): raise DBDataError("Numero partita non valido.")
        try:
            json.loads(possessori_json_str); json.loads(immobili_json_str)
        except json.JSONDecodeError as je:
            raise DBDataError(f"Dati JSON non validi: {je}") from je
        
        actual_suffisso_partita = suffisso_partita.strip() if isinstance(suffisso_partita, str) else None

        call_proc = f"CALL {self.schema}.registra_nuova_proprieta(%s, %s, %s, %s::jsonb, %s::jsonb, %s::TEXT);"
        params_call = (comune_id, numero_partita, data_impianto, possessori_json_str, immobili_json_str, actual_suffisso_partita)
        
        query_select_id = f"""
            SELECT id FROM {self.schema}.partita 
            WHERE comune_id = %s AND numero_partita = %s AND 
                (suffisso_partita = %s OR (suffisso_partita IS NULL AND %s IS NULL))
            ORDER BY id DESC LIMIT 1; 
        """
        params_select = (comune_id, numero_partita, actual_suffisso_partita, actual_suffisso_partita)

        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    self.logger.debug(f"Chiamata procedura registra_nuova_proprieta per C:{comune_id}, N:{numero_partita}")
                    cur.execute(call_proc, params_call)
                    
                    self.logger.debug("Recupero ID della partita appena creata.")
                    cur.execute(query_select_id, params_select)
                    result = cur.fetchone()

                    if result and result['id']:
                        new_partita_id = result['id']
                        self.logger.info(f"Nuova proprietà registrata. Partita ID: {new_partita_id}.")
                        return new_partita_id
                    else:
                        raise DBMError("Fallimento nel recuperare l'ID della nuova partita dopo la registrazione.")
        
        # --- BLOCCO DI GESTIONE ECCEZIONI MIGLIORATO ---
        except psycopg2.errors.UniqueViolation as uve:
            # Controlliamo il nome del vincolo violato per dare un messaggio specifico
            constraint_name = getattr(uve.diag, 'constraint_name', '')
            if constraint_name == 'partita_unique_numero_suffisso_comune':
                messaggio = "Impossibile registrare: una partita con lo stesso numero e suffisso esiste già in questo comune."
                raise DBUniqueConstraintError(messaggio, constraint_name=constraint_name) from uve
            else:
                # Se è un altro vincolo di unicità, diamo un messaggio più generico
                messaggio_generico = f"Violazione di un vincolo di unicità '{constraint_name}'. Controllare i dati."
                raise DBUniqueConstraintError(messaggio_generico, constraint_name=constraint_name) from uve
        
        except Exception as e:
            # Cattura tutte le altre eccezioni
            self.logger.error(f"Errore in registra_nuova_proprieta: {e}", exc_info=True)
            raise DBMError(f"Impossibile registrare la nuova proprietà: {e}") from e
        # --- FINE BLOCCO MIGLIORATO ---
    
    def registra_passaggio_proprieta(self, partita_origine_id: int, comune_id_nuova_partita: int, 
                                 numero_nuova_partita: int, tipo_variazione: str, data_variazione: date, 
                                 tipo_contratto: str, data_contratto: date,
                                 notaio: Optional[str] = None, repertorio: Optional[str] = None,
                                 nuovi_possessori_list: Optional[List[Dict[str, Any]]] = None, 
                                 immobili_da_trasferire_ids: Optional[List[int]] = None, 
                                 note_variazione: Optional[str] = None,
                                 suffisso_nuova_partita: Optional[str] = None) -> bool:
        """Chiama la procedura SQL catasto.registra_passaggio_proprieta in modo transazionale e con cast espliciti."""
        try:
            nuovi_possessori_jsonb = json.dumps(nuovi_possessori_list) if nuovi_possessori_list else None
            
            # --- MODIFICA CHIAVE: Aggiunti cast espliciti per tutti i tipi che possono essere NULL ---
            # Questo garantisce che PostgreSQL riceva i tipi corretti anche per i valori None.
            call_proc_str = f"""
                CALL {self.schema}.registra_passaggio_proprieta(
                    %s,                    -- p_partita_origine_id INTEGER
                    %s,                    -- p_comune_id_nuova_partita INTEGER
                    %s,                    -- p_numero_nuova_partita INTEGER
                    %s::VARCHAR(20),       -- p_suffisso_nuova_partita VARCHAR(20)
                    %s::TEXT,              -- p_tipo_variazione TEXT
                    %s,                    -- p_data_variazione DATE
                    %s::TEXT,              -- p_tipo_contratto TEXT
                    %s,                    -- p_data_contratto DATE
                    %s::TEXT,              -- p_notaio TEXT
                    %s::TEXT,              -- p_repertorio TEXT
                    %s::JSONB,             -- p_nuovi_possessori_json JSONB
                    %s::INTEGER[],         -- p_immobili_da_trasferire_ids INTEGER[]
                    %s::TEXT               -- p_note_variazione TEXT
                );
            """
            
            params = (
                partita_origine_id, comune_id_nuova_partita, numero_nuova_partita, suffisso_nuova_partita,
                tipo_variazione, data_variazione, tipo_contratto, data_contratto,
                notaio, repertorio, nuovi_possessori_jsonb, immobili_da_trasferire_ids, note_variazione
            )
            
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    self.logger.info(f"Tentativo di registrare passaggio proprietà da Partita ID {partita_origine_id}...")
                    cur.execute(call_proc_str, params)
            
            self.logger.info("Passaggio di proprietà registrato con successo tramite procedura.")
            return True
        except psycopg2.Error as db_err:
            pgerror_msg = getattr(db_err, 'pgerror', str(db_err))
            self.logger.error(f"Errore DB durante registrazione passaggio proprietà: {pgerror_msg}", exc_info=True)
            raise DBMError(f"Errore database: {pgerror_msg}") from db_err
        except Exception as e:
            self.logger.error(f"Errore Python durante registrazione passaggio proprietà: {e}", exc_info=True)
            raise DBMError(f"Errore di sistema: {e}") from e
    def registra_consultazione(self, data: date, richiedente: str, documento_identita: Optional[str],
                             motivazione: Optional[str], materiale_consultato: Optional[str],
                             funzionario_autorizzante: Optional[str]) -> bool:
        """Chiama la procedura SQL registra_consultazione (invariata rispetto a comune_id)."""
        try:
            call_proc = "CALL registra_consultazione(%s, %s, %s, %s, %s, %s)"
            params = (data, richiedente, documento_identita, motivazione, materiale_consultato, funzionario_autorizzante)
            if self.execute_query(call_proc, params): self.commit(); logger.info(f"Registrata consultazione: Richiedente '{richiedente}', Data {data}"); return True
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB registrazione consultazione: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python registrazione consultazione: {e}"); self.rollback(); return False

    def duplicate_partita(self, partita_id_originale: int, nuovo_numero_partita: int,
                      mantenere_possessori: bool = True, mantenere_immobili: bool = False,
                      nuovo_suffisso: Optional[str] = None) -> bool:
        """Chiama la procedura SQL per duplicare una partita in modo transazionale."""
        call_proc_str = f"CALL {self.schema}.duplica_partita(%s, %s, %s, %s, %s);"
        params = (partita_id_originale, nuovo_numero_partita, mantenere_possessori, mantenere_immobili, nuovo_suffisso)
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    self.logger.info(f"Tentativo di duplicare partita ID {partita_id_originale} in Nuovo N.{nuovo_numero_partita}")
                    cur.execute(call_proc_str, params)
            
            self.logger.info(f"Partita ID {partita_id_originale} duplicata con successo.")
            return True
        except psycopg2.Error as db_err:
            pgerror_msg = getattr(db_err, 'pgerror', str(db_err))
            self.logger.error(f"Errore DB durante duplicazione partita ID {partita_id_originale}: {pgerror_msg}", exc_info=True)
            raise DBMError(f"Errore database durante la duplicazione: {pgerror_msg}") from db_err
        except Exception as e:
            self.logger.error(f"Errore Python durante duplicazione partita ID {partita_id_originale}: {e}", exc_info=True)
            raise DBMError(f"Errore di sistema durante la duplicazione: {e}") from e

    def transfer_immobile(self, immobile_id: int, nuova_partita_id: int, registra_variazione: bool = False) -> bool:
        """
        Chiama la procedura SQL per trasferire un immobile a una nuova partita in modo transazionale.
        """
        call_proc_str = f"CALL {self.schema}.trasferisci_immobile(%s, %s, %s);"
        params = (immobile_id, nuova_partita_id, registra_variazione)
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    self.logger.info(f"Trasferimento immobile ID {immobile_id} a partita ID {nuova_partita_id}...")
                    cur.execute(call_proc_str, params)
            
            # Il commit è automatico qui se la procedura non ha sollevato eccezioni
            self.logger.info(f"Immobile ID {immobile_id} trasferito con successo.")
            return True
            
        except psycopg2.Error as db_err:
            # Il rollback è automatico
            pgerror_msg = getattr(db_err, 'pgerror', str(db_err))
            self.logger.error(f"Errore DB durante trasferimento immobile ID {immobile_id}: {pgerror_msg}", exc_info=True)
            raise DBMError(f"Errore database durante il trasferimento: {pgerror_msg}") from db_err
        except Exception as e:
            self.logger.error(f"Errore imprevisto durante trasferimento immobile ID {immobile_id}: {e}", exc_info=True)
            raise DBMError(f"Errore di sistema imprevisto durante il trasferimento: {e}") from e
    def genera_report_proprieta(self, partita_id: int) -> Optional[str]:
        """Chiama la funzione SQL catasto.genera_report_proprieta in modo sicuro."""
        if not isinstance(partita_id, int) or partita_id <= 0:
            self.logger.error(f"ID partita non valido: {partita_id}")
            return None
        
        query = f"SELECT {self.schema}.genera_report_proprieta(%s);"
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (partita_id,))
                    result = cur.fetchone()
                    if result and result[0] is not None:
                        self.logger.info(f"Report di proprietà generato per partita ID {partita_id}.")
                        return str(result[0])
                    else:
                        self.logger.warning(f"Nessun report generato per partita ID {partita_id}.")
                        return None
        except Exception as e:
            self.logger.error(f"Errore DB in genera_report_proprieta (ID: {partita_id}): {e}", exc_info=True)
            return None
    def genera_report_genealogico(self, partita_id: int) -> Optional[str]:
        """Chiama la funzione SQL catasto.genera_report_genealogico in modo sicuro."""
        if not isinstance(partita_id, int) or partita_id <= 0:
            self.logger.error(f"ID partita non valido: {partita_id}")
            return None

        query = f"SELECT {self.schema}.genera_report_genealogico(%s);"
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (partita_id,))
                    result = cur.fetchone()
                    return str(result[0]) if result and result[0] is not None else None
        except Exception as e:
            self.logger.error(f"Errore DB in genera_report_genealogico (ID: {partita_id}): {e}", exc_info=True)
            return None
    def genera_report_possessore(self, possessore_id: int) -> Optional[str]:
        """Chiama la funzione SQL catasto.genera_report_possessore in modo sicuro."""
        if not isinstance(possessore_id, int) or possessore_id <= 0:
            self.logger.error(f"ID possessore non valido: {possessore_id}")
            return None
                
        query = f"SELECT {self.schema}.genera_report_possessore(%s);"
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (possessore_id,))
                    result = cur.fetchone()
                    return str(result[0]) if result and result[0] is not None else None
        except Exception as e:
            self.logger.error(f"Errore DB in genera_report_possessore (ID: {possessore_id}): {e}", exc_info=True)
            return None
    def genera_report_consultazioni(self, data_inizio: Optional[date] = None, 
                                data_fine: Optional[date] = None,
                                richiedente: Optional[str] = None) -> str:
        """Chiama la funzione SQL catasto.genera_report_consultazioni in modo sicuro."""
        query = f"SELECT {self.schema}.genera_report_consultazioni(%s, %s, %s);"
        params = (data_inizio, data_fine, richiedente)
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    self.logger.debug(f"Esecuzione genera_report_consultazioni con filtri: {params}")
                    cur.execute(query, params)
                    result = cur.fetchone()
                    if result and result[0] is not None:
                        self.logger.info("Report consultazioni generato.")
                        return str(result[0])
                    else:
                        self.logger.warning("Nessun report consultazioni generato o risultato NULL.")
                        return "Nessun dato trovato per i criteri specificati."
        except Exception as e:
            self.logger.error(f"Errore in genera_report_consultazioni: {e}", exc_info=True)
            return "Errore durante la generazione del report."

    def get_statistiche_comune(self) -> List[Dict[str, Any]]:
        """Recupera dati dalla vista materializzata mv_statistiche_comune in modo sicuro."""
        query = f"SELECT * FROM {self.schema}.mv_statistiche_comune ORDER BY comune;"
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query)
                    results = [dict(row) for row in cur.fetchall()]
                    self.logger.info(f"Recuperate {len(results)} righe da mv_statistiche_comune.")
                    return results
        except Exception as e:
            self.logger.error(f"Errore DB in get_statistiche_comune: {e}", exc_info=True)
            return []

    def get_immobile_details(self, immobile_id: int) -> Optional[Dict[str, Any]]:
        """Recupera i dettagli completi di un singolo immobile in modo sicuro."""
        if not isinstance(immobile_id, int) or immobile_id <= 0:
            self.logger.error(f"get_immobile_details: immobile_id non valido: {immobile_id}")
            return None

        query = f"""
            SELECT
                i.id, i.partita_id, i.localita_id, i.natura, i.classificazione, i.consistenza,
                i.numero_piani, i.numero_vani,
                p.numero_partita, p.suffisso_partita,
                c.nome AS comune_nome,
                l.nome AS localita_nome, l.tipo AS localita_tipo, l.civico
            FROM {self.schema}.immobile i
            JOIN {self.schema}.partita p ON i.partita_id = p.id
            JOIN {self.schema}.comune c ON p.comune_id = c.id
            JOIN {self.schema}.localita l ON i.localita_id = l.id
            WHERE i.id = %s;
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, (immobile_id,))
                    immobile_data = cur.fetchone()
                    if immobile_data:
                        self.logger.info(f"Dettagli recuperati per immobile ID {immobile_id}.")
                        return dict(immobile_data)
                    else:
                        self.logger.warning(f"Nessun immobile trovato con ID {immobile_id}.")
                        return None
        except Exception as e:
            self.logger.error(f"Errore DB in get_immobile_details per ID {immobile_id}: {e}", exc_info=True)
            return None
    def get_immobili_per_tipologia(self, comune_id: Optional[int] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Recupera dati dalla vista materializzata mv_immobili_per_tipologia in modo sicuro."""
        params = []
        
        if comune_id is not None:
            query = f"""
                SELECT m.* FROM {self.schema}.mv_immobili_per_tipologia m
                JOIN {self.schema}.comune c ON m.comune_nome = c.nome
                WHERE c.id = %s
                ORDER BY m.comune_nome, m.classificazione LIMIT %s;
            """
            params = [comune_id, limit]
        else:
            query = f"SELECT * FROM {self.schema}.mv_immobili_per_tipologia ORDER BY comune_nome, classificazione LIMIT %s;"
            params = [limit]
        
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, tuple(params))
                    results = [dict(row) for row in cur.fetchall()]
                    self.logger.info(f"Recuperate {len(results)} righe da mv_immobili_per_tipologia.")
                    return results
        except Exception as e:
            self.logger.error(f"Errore DB in get_immobili_per_tipologia: {e}", exc_info=True)
            return []

    def get_partite_complete_view(self, comune_id: Optional[int] = None, stato: Optional[str] = None, limit: int = 100) -> List[Dict]: # Usa comune_id
        """Recupera dati dalla vista materializzata mv_partite_complete (aggiornata), filtrando per ID."""
        try:
            params = []
            # La vista SQL è stata aggiornata per usare nome comune
            query = "SELECT * FROM mv_partite_complete" # La vista ha 'comune_nome'
            where_clauses = []
            if comune_id is not None:
                 # Filtra con JOIN
                 query = """
                     SELECT m.* FROM mv_partite_complete m
                     JOIN comune c ON m.comune_nome = c.nome
                     WHERE c.id = %s
                 """
                 params.append(comune_id)
                 if stato and stato.lower() in ['attiva', 'inattiva']:
                     query += " AND m.stato = %s"; params.append(stato.lower())
            elif stato and stato.lower() in ['attiva', 'inattiva']:
                 query += " WHERE stato = %s"; params.append(stato.lower())

            query += " ORDER BY comune_nome, numero_partita LIMIT %s"; params.append(limit)
            if self.execute_query(query, tuple(params)): return self.fetchall()
        except psycopg2.Error as db_err: logger.error(f"Errore DB get_partite_complete_view: {db_err}"); return []
        except Exception as e: logger.error(f"Errore Python get_partite_complete_view: {e}"); return []

    def aggiorna_legame_partita_possessore(self, partita_possessore_id: int, titolo: str, quota: Optional[str]) -> bool:
        """Aggiorna i dettagli di un legame partita-possessore in modo transazionale."""
        if not (isinstance(partita_possessore_id, int) and partita_possessore_id > 0):
            raise DBDataError(f"ID relazione non valido: {partita_possessore_id}")
        if not (isinstance(titolo, str) and titolo.strip()):
            raise DBDataError("Il titolo di possesso è obbligatorio.")
        
        actual_quota = quota.strip() if isinstance(quota, str) and quota.strip() else None

        set_clauses = ["titolo = %s", "quota = %s", "data_modifica = CURRENT_TIMESTAMP"]
        params = [titolo.strip(), actual_quota, partita_possessore_id]

        query = f"UPDATE {self.schema}.partita_possessore SET {', '.join(set_clauses)} WHERE id = %s;"
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, tuple(params))
                    if cur.rowcount == 0:
                        # Se non viene aggiornata nessuna riga, solleva un errore.
                        # Il context manager gestirà automaticamente il rollback.
                        raise DBNotFoundError(f"Legame partita-possessore con ID {partita_possessore_id} non trovato.")
            
            # Il commit è automatico se nessuna eccezione è stata sollevata
            self.logger.info(f"Legame partita-possessore ID {partita_possessore_id} aggiornato.")
            return True

        except (DBNotFoundError, DBDataError, psycopg2.errors.CheckViolation) as e:
            # Rilancia eccezioni specifiche per una gestione mirata
            self.logger.error(f"Errore previsto aggiornando legame {partita_possessore_id}: {e}", exc_info=True)
            raise e
        except Exception as e:
            # Gestisce tutti gli altri errori
            self.logger.error(f"Errore imprevisto aggiornando legame {partita_possessore_id}: {e}", exc_info=True)
            raise DBMError(f"Impossibile aggiornare il legame: {e}") from e
    
    def aggiungi_possessore_a_partita(self, partita_id: int, possessore_id: int, tipo_partita_rel: str, titolo: str, quota: Optional[str]) -> bool:
        """Aggiunge un legame partita-possessore in modo transazionale e sicuro."""
        # La validazione dei parametri iniziali resta invariata
        if not all([...]): # (logica di validazione originale)
            raise DBDataError("Parametri non validi forniti.")
            
        actual_quota = quota.strip() if isinstance(quota, str) and quota.strip() else None

        query = f"""
            INSERT INTO {self.schema}.partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota)
            VALUES (%s, %s, %s, %s, %s) RETURNING id; 
        """
        params = (partita_id, possessore_id, tipo_partita_rel, titolo.strip(), actual_quota)
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    new_relation_id = cur.fetchone()[0] if cur.rowcount > 0 else None
                    if not new_relation_id:
                        raise DBMError("Inserimento del legame fallito, nessun ID restituito.")
            
            self.logger.info(f"Possessore ID {possessore_id} associato a partita ID {partita_id}. ID Relazione: {new_relation_id}.")
            return True

        except psycopg2.errors.UniqueViolation as e:
            msg = "Questo possessore è già associato a questa partita."
            raise DBUniqueConstraintError(msg, constraint_name=getattr(e.diag, 'constraint_name', 'N/D'), details=str(e)) from e
        except psycopg2.errors.ForeignKeyViolation as e:
            msg = "La partita o il possessore specificati non esistono."
            raise DBMError(msg) from e
        except psycopg2.errors.CheckViolation as e:
            msg = f"Il valore '{tipo_partita_rel}' non è valido per il tipo di legame."
            raise DBDataError(msg) from e
        except Exception as e:
            self.logger.error(f"Errore imprevisto in aggiungi_possessore_a_partita: {e}", exc_info=True)
            raise DBMError(f"Impossibile associare il possessore: {e}") from e

    def rimuovi_possessore_da_partita(self, partita_possessore_id: int) -> bool:
        """Rimuove un legame partita-possessore in modo transazionale e sicuro."""
        if not (isinstance(partita_possessore_id, int) and partita_possessore_id > 0):
            raise DBDataError(f"ID relazione partita-possessore non valido: {partita_possessore_id}")

        query = f"DELETE FROM {self.schema}.partita_possessore WHERE id = %s;"
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (partita_possessore_id,))
                    
                    if cur.rowcount == 0:
                        # Se non viene cancellata nessuna riga, il legame non esisteva.
                        # Solleviamo un errore, che causerà un rollback automatico.
                        self.logger.warning(f"Tentativo di rimuovere legame ID {partita_possessore_id} non trovato.")
                        raise DBNotFoundError(f"Nessun legame partita-possessore trovato con ID {partita_possessore_id}.")
            
            # Il commit è automatico qui se l'operazione ha successo
            self.logger.info(f"Legame partita-possessore ID {partita_possessore_id} rimosso con successo.")
            return True

        except (DBNotFoundError, DBDataError) as e:
            self.logger.error(f"Errore previsto rimuovendo legame {partita_possessore_id}: {e}", exc_info=True)
            raise e  # Rilancia l'eccezione specifica
        except Exception as e:
            self.logger.error(f"Errore imprevisto rimuovendo legame {partita_possessore_id}: {e}", exc_info=True)
            raise DBMError(f"Impossibile rimuovere il legame: {e}") from e
    def get_possessore_full_details(self, possessore_id: int) -> Optional[Dict[str, Any]]:
        """Recupera i dettagli completi di un singolo possessore in modo sicuro."""
        if not isinstance(possessore_id, int) or possessore_id <= 0:
            self.logger.error(f"ID possessore non valido: {possessore_id}")
            return None

        query = f"""
            SELECT
                p.id, p.cognome_nome, p.paternita, p.nome_completo, p.attivo,
                p.comune_id AS comune_riferimento_id, 
                c.nome AS comune_riferimento_nome,
                p.data_creazione, p.data_modifica
            FROM {self.schema}.possessore p
            LEFT JOIN {self.schema}.comune c ON p.comune_id = c.id
            WHERE p.id = %s;
        """
        
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, (possessore_id,))
                    possessore_data = cur.fetchone()
                    
                    if possessore_data:
                        self.logger.info(f"Dettagli recuperati per il possessore ID {possessore_id}.")
                        return dict(possessore_data)
                    else:
                        self.logger.warning(f"Nessun possessore trovato con ID {possessore_id}.")
                        return None
        except Exception as e:
            self.logger.error(f"Errore DB in get_possessore_full_details per ID {possessore_id}: {e}", exc_info=True)
            return None
    
    def get_cronologia_variazioni(self, comune_origine_id: Optional[int] = None, tipo_variazione: Optional[str] = None, limit: int = 100) -> List[Dict]: # Usa comune_id
        """Recupera dati dalla vista materializzata mv_cronologia_variazioni (aggiornata), filtrando per ID."""
        try:
            params = []
            # La vista SQL è stata aggiornata per usare nomi comuni
            query = "SELECT * FROM mv_cronologia_variazioni" # Vista ha 'comune_origine' come nome
            if comune_origine_id is not None:
                query = """
                    SELECT m.* FROM mv_cronologia_variazioni m
                    JOIN comune c ON m.comune_origine = c.nome
                    WHERE c.id = %s
                """
                params.append(comune_origine_id)
                if tipo_variazione: query += " AND m.tipo_variazione = %s"; params.append(tipo_variazione)
            elif tipo_variazione:
                query += " WHERE tipo_variazione = %s"; params.append(tipo_variazione)

            query += " ORDER BY data_variazione DESC LIMIT %s"; params.append(limit)
            if self.execute_query(query, tuple(params)): return self.fetchall()
        except psycopg2.Error as db_err: logger.error(f"Errore DB get_cronologia_variazioni: {db_err}"); return []
        except Exception as e: logger.error(f"Errore Python get_cronologia_variazioni: {e}"); return []

    # --- Metodi Funzioni Avanzate di Report (MODIFICATI) ---

    def get_report_annuale_partite(self, comune_id: int, anno: int) -> List[Dict]: # Usa comune_id
        """Chiama la funzione SQL report_annuale_partite (MODIFICATA per comune_id)."""
        try:
            # Funzione SQL aggiornata per comune_id
            query = "SELECT * FROM report_annuale_partite(%s, %s)"
            if self.execute_query(query, (comune_id, anno)): return self.fetchall()
        except psycopg2.Error as db_err: logger.error(f"Errore DB get_report_annuale_partite: {db_err}"); return []
        except Exception as e: logger.error(f"Errore Python get_report_annuale_partite: {e}"); return []

    def get_report_proprieta_possessore(self, possessore_id: int, data_inizio: date, data_fine: date) -> List[Dict]:
        """Chiama la funzione SQL report_proprieta_possessore (SQL aggiornata per nome comune)."""
        try:
            # Funzione SQL aggiornata per JOIN
            query = "SELECT * FROM report_proprieta_possessore(%s, %s, %s)"
            if self.execute_query(query, (possessore_id, data_inizio, data_fine)): return self.fetchall()
        except psycopg2.Error as db_err: logger.error(f"Errore DB get_report_proprieta_possessore: {db_err}"); return []
        except Exception as e: logger.error(f"Errore Python get_report_proprieta_possessore: {e}"); return []

    def get_report_comune(self, comune_id: int) -> Optional[Dict]: # Usa comune_id
        """Chiama la funzione SQL genera_report_comune (MODIFICATA per comune_id)."""
        try:
            # Funzione SQL aggiornata per comune_id
            query = "SELECT * FROM genera_report_comune(%s)"
            if self.execute_query(query, (comune_id,)): return self.fetchone()
        except psycopg2.Error as db_err: logger.error(f"Errore DB get_report_comune: {db_err}"); return None
        except Exception as e: logger.error(f"Errore Python get_report_comune: {e}"); return None

    def export_partita_json(self, partita_id: int) -> Optional[str]:
        """Chiama la funzione SQL esporta_partita_json (SQL aggiornata)."""
        try:
            # Funzione SQL aggiornata per fare JOIN
            query = "SELECT esporta_partita_json(%s) AS partita_json"
            if self.execute_query(query, (partita_id,)):
                result = self.fetchone()
                if result and result.get('partita_json'):
                     try: return json.dumps(result['partita_json'], indent=4, ensure_ascii=False)
                     except (TypeError, ValueError) as json_err: logger.error(f"Errore JSON export partita {partita_id}: {json_err}"); return str(result['partita_json'])
            logger.warning(f"Nessun JSON per partita ID {partita_id}.")
        except psycopg2.Error as db_err: logger.error(f"Errore DB export_partita_json (ID: {partita_id}): {db_err}")
        except Exception as e: logger.error(f"Errore Python export_partita_json (ID: {partita_id}): {e}")
        return None

    def export_possessore_json(self, possessore_id: int) -> Optional[str]:
        """Chiama la funzione SQL esporta_possessore_json (SQL aggiornata)."""
        try:
            # Funzione SQL aggiornata per fare JOIN
            query = "SELECT esporta_possessore_json(%s) AS possessore_json"
            if self.execute_query(query, (possessore_id,)):
                result = self.fetchone()
                if result and result.get('possessore_json'):
                     try: return json.dumps(result['possessore_json'], indent=4, ensure_ascii=False)
                     except (TypeError, ValueError) as json_err: logger.error(f"Errore JSON export possessore {possessore_id}: {json_err}"); return str(result['possessore_json'])
            logger.warning(f"Nessun JSON per possessore ID {possessore_id}.")
        except psycopg2.Error as db_err: logger.error(f"Errore DB export_possessore_json (ID: {possessore_id}): {db_err}")
        except Exception as e: logger.error(f"Errore Python export_possessore_json (ID: {possessore_id}): {e}")
        return None
    


    def get_possessore_data_for_export(self, possessore_id: int) -> Optional[Dict[str, Any]]:
        """
        Recupera i dati di un possessore per l'esportazione chiamando una funzione SQL.
        """
        if not isinstance(possessore_id, int) or possessore_id <= 0:
            self.logger.error(f"ID possessore non valido: {possessore_id}")
            return None

        query = f"SELECT {self.schema}.esporta_possessore_json(%s) AS possessore_data;"
        
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, (possessore_id,))
                    result = cur.fetchone()
                    
                    if result and result['possessore_data'] is not None:
                        self.logger.info(f"Dati per esportazione recuperati per possessore ID {possessore_id}.")
                        return result['possessore_data']
                    else:
                        self.logger.warning(f"Nessun dato di export per possessore ID {possessore_id}.")
                        return None
        except Exception as e:
            self.logger.error(f"Errore DB in get_possessore_data_for_export (ID: {possessore_id}): {e}", exc_info=True)
            return None

    # --- Metodi Manutenzione e Ottimizzazione (Invariati rispetto a comune_id) ---
# In catasto_db_manager.py, SOSTITUISCI il metodo refresh_materialized_views con questo:

    def refresh_materialized_views(self, show_success_message: bool = False) -> bool:
        """Aggiorna tutte le viste materializzate del database in modo sicuro."""
        if not self.pool:
            self.logger.error("Pool di connessioni non inizializzato per refresh viste materializzate.")
            QMessageBox.critical(None, "Errore", "Pool di connessioni non attivo. Impossibile aggiornare le viste.")
            return False
        
        progress_dialog = QProgressDialog("Aggiornamento viste materializzate in corso...", "Annulla", 0, 0, None)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setCancelButton(None)
        progress_dialog.show()
        QApplication.processEvents()

        # --- CORREZIONE QUI: Rimosso CONCURRENTLY per compatibilità universale ---
        query = f"""
            DO $$
            DECLARE
                r RECORD;
            BEGIN
                FOR r IN
                    SELECT schemaname, matviewname
                    FROM pg_matviews
                    WHERE schemaname = '{self.schema}'
                LOOP
                    EXECUTE 'REFRESH MATERIALIZED VIEW ' || quote_ident(r.schemaname) 
                    || '.' || quote_ident(r.matviewname);
                END LOOP;
            END $$;
        """
        # --- FINE CORREZIONE ---
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    self.logger.info("Esecuzione dello script di aggiornamento per le viste materializzate...")
                    cur.execute(query)
                    # --- AGGIUNGERE QUESTA RIGA ALLA FINE DEL BLOCCO 'try' ---
                    self.update_last_mv_refresh_timestamp() # Aggiorna il timestamp dopo il successo
                    # --- FINE AGGIUNTA ---
                
                    progress_dialog.close()
            if show_success_message:
                QMessageBox.information(None, "Successo", "Tutte le viste materializzate sono state aggiornate con successo.")
            
            self.logger.info("Viste materializzate aggiornate con successo.")
            return True
            
        except psycopg2.Error as db_err:
            progress_dialog.close()
            error_message = f"Errore DB durante l'aggiornamento delle viste: {db_err}"
            self.logger.error(error_message, exc_info=True)
            QMessageBox.critical(None, "Errore Aggiornamento Viste", error_message)
            return False
        except Exception as e:
            progress_dialog.close()
            error_message = f"Errore critico durante l'aggiornamento delle viste: {e}"
            self.logger.error(error_message, exc_info=True)
            QMessageBox.critical(None, "Errore Aggiornamento Viste", error_message)
            return False
    
    def get_historical_name(self, entity_type: str, entity_id: int, year: Optional[int] = None) -> Optional[Dict]:
        """Chiama la funzione SQL get_nome_storico in modo sicuro."""
        if year is None: year = datetime.now().year
        query = f"SELECT * FROM {self.schema}.get_nome_storico(%s, %s, %s)"
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(query, (entity_type, entity_id, year))
                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            self.logger.error(f"Errore DB in get_historical_name ({entity_type} ID {entity_id}): {e}", exc_info=True)
            return None
    def set_session_app_user(self, user_id: Optional[int], client_ip: Optional[str] = None) -> bool:
        """
        Imposta variabili di sessione PostgreSQL per tracciamento usando il context manager.
        """
        self.logger.debug(f"Impostazione var sessione: app.user_id='{user_id}', app.ip_address='{client_ip}'")
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    user_id_str = str(user_id) if user_id is not None else None
                    ip_str = client_ip if client_ip is not None else None
                    
                    # Il terzo argomento 'false' rende l'impostazione valida per l'intera sessione
                    cur.execute("SELECT set_config('app.user_id', %s, false);", (user_id_str,))
                    cur.execute("SELECT set_config('app.ip_address', %s, false);", (ip_str,))
            
            # Il commit è automatico all'uscita del blocco 'with' senza errori
            self.logger.info(f"Variabili di sessione applicative impostate con successo.")
            return True
            
        except Exception as e:
            self.logger.error(f"Errore DB impostando var sessione applicative: {e}", exc_info=True)
            # Il rollback è automatico, restituiamo False per indicare il fallimento
            return False
    def clear_session_app_user(self):
        """Resetta le variabili di sessione PostgreSQL 'app.user_id' e 'app.ip_address'."""
        self.logger.info("Reset variabili di sessione applicative (app.user_id, app.ip_address).")
        # Richiama set_session_app_user con None per resettarle.
        # In alternativa, si potrebbe usare RESET nome_variabile;
        return self.set_session_app_user(user_id=None, client_ip=None)

    def get_audit_log(self, tabella: Optional[str]=None, operazione: Optional[str]=None,
                      record_id: Optional[int]=None, data_inizio: Optional[date]=None,
                      data_fine: Optional[date]=None, utente_db: Optional[str]=None,
                      app_user_id: Optional[int]=None, session_id: Optional[str]=None,
                      limit: int=100) -> List[Dict]:
        """Recupera log di audit con filtri opzionali dalla vista v_audit_dettagliato."""
        try:
            conditions = []; params = []
            query = "SELECT * FROM v_audit_dettagliato"
            if tabella: conditions.append("tabella = %s"); params.append(tabella)
            if operazione and operazione.upper() in ['I', 'U', 'D']: conditions.append("operazione = %s"); params.append(operazione.upper())
            if record_id is not None: conditions.append("record_id = %s"); params.append(record_id)
            if data_inizio: conditions.append("timestamp >= %s"); params.append(data_inizio)
            if data_fine: data_fine_end_day = datetime.combine(data_fine, datetime.max.time()); conditions.append("timestamp <= %s"); params.append(data_fine_end_day)
            if utente_db: conditions.append("db_user = %s"); params.append(utente_db)
            # Attenzione: filtro su app_user_id deve usare alias tabella originale se vista non lo include direttamente con alias
            # La vista v_audit_dettagliato JOIN u ON al.app_user_id = u.id, quindi al.app_user_id non è direttamente selezionato
            # Modifichiamo la vista o filtriamo su app_username? Filtriamo su ID per ora, assumendo che la vista possa essere modificata o che funzioni.
            if app_user_id is not None: conditions.append("al.app_user_id = %s"); params.append(app_user_id) # Usa al.app_user_id (potrebbe richiedere modifica vista)
            if session_id: conditions.append("session_id = %s"); params.append(session_id)

            if conditions: query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY timestamp DESC LIMIT %s"; params.append(limit)

            if self.execute_query(query, tuple(params)): return self.fetchall()
        except psycopg2.Error as db_err: logger.error(f"Errore DB get_audit_log: {db_err}"); return []
        except Exception as e: logger.error(f"Errore Python get_audit_log: {e}"); return []
        return []

    def get_record_history(self, tabella: str, record_id: int) -> List[Dict]:
        """Chiama la funzione SQL get_record_history."""
        try:
            query = "SELECT * FROM get_record_history(%s, %s)"
            if self.execute_query(query, (tabella, record_id)): return self.fetchall()
        except psycopg2.Error as db_err: logger.error(f"Errore DB get_record_history: {db_err}"); return []
        except Exception as e: logger.error(f"Errore Python get_record_history: {e}"); return []
        return []

    

    def create_user(self, username: str, password_hash: str, nome_completo: str, email: str, ruolo: str) -> bool:
        """Chiama la procedura SQL crea_utente in modo transazionale e sicuro."""
        call_proc = f"CALL {self.schema}.crea_utente(%s, %s, %s, %s, %s)"
        params = (username, password_hash, nome_completo, email, ruolo)
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    self.logger.debug(f"Chiamata procedura crea_utente per username: {username}")
                    cur.execute(call_proc, params)
            
            # Il commit è automatico qui
            self.logger.info(f"Utente '{username}' creato con successo tramite procedura.")
            return True
            
        except psycopg2.errors.UniqueViolation as uve:
            # Il rollback è automatico
            constraint = getattr(uve.diag, 'constraint_name', 'N/D')
            self.logger.error(f"Errore creazione utente '{username}': Username o Email già esistente (vincolo: {constraint}).")
            raise DBUniqueConstraintError(f"Username '{username}' o Email '{email}' già esistente.", constraint_name=constraint) from uve
            
        except psycopg2.Error as db_err:
            # Il rollback è automatico
            self.logger.error(f"Errore DB creazione utente '{username}': {db_err}", exc_info=True)
            raise DBMError(f"Errore database durante la creazione dell'utente: {getattr(db_err, 'pgerror', str(db_err))}") from db_err
            
        except Exception as e:
            self.logger.error(f"Errore Python creazione utente '{username}': {e}", exc_info=True)
            raise DBMError(f"Errore di sistema imprevisto durante la creazione dell'utente: {e}") from e

    
    def get_user_credentials(self, username: str) -> Optional[Dict]:
        """
        Recupera le credenziali e le informazioni di base dell'utente dal database.
        Utilizza il pattern 'with' per una gestione sicura della connessione.
        """
        if not username:
            return None
        
        # Adattato per usare il context manager _get_connection
        sql = f"""
            SELECT id, username, password_hash, nome_completo, ruolo, attivo
            FROM {self.schema}.utente
            WHERE username = %s;
        """
        try:
            # --- CORREZIONE CRUCIALE: Uso del 'with' statement ---
            with self._get_connection() as conn:
                # Uso del DictCursor per ottenere risultati come dizionari
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(sql, (username,))
                    user_data = cur.fetchone()
                    if user_data:
                        return dict(user_data)
            return None
        except Exception as e:
            self.logger.error(f"Errore durante il recupero delle credenziali per l'utente '{username}': {e}", exc_info=True)
            return None

    # Metodo ESISTENTE da MODIFICARE
    def register_access(self, user_id: int, action: str, esito: bool,
                    indirizzo_ip: Optional[str] = None,
                    dettagli: Optional[str] = None,
                    application_name: Optional[str] = None
                   ) -> Optional[str]:
        """
        Registra un evento di sessione in modo transazionale e sicuro.
        Genera e restituisce un UUID per la sessione in caso di login riuscito.
        """
        session_id_to_return: Optional[str] = None
        if action == 'login' and esito:
            session_id_to_return = str(uuid.uuid4())
            self.logger.info(f"Nuovo ID sessione generato per login utente {user_id}: {session_id_to_return}")
        elif action == 'fail_login':
            session_id_to_return = str(uuid.uuid4()) 
            self.logger.info(f"ID evento generato per fail_login utente {user_id}: {session_id_to_return}")

        call_proc_str = f"CALL {self.schema}.registra_evento_sessione(%s, %s, %s, %s, %s, %s, %s);"
        params = (
            user_id,
            session_id_to_return,
            action,
            esito,
            indirizzo_ip,
            application_name if application_name else self.application_name,
            dettagli
        )

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    self.logger.debug(f"Chiamata a procedura registra_evento_sessione per utente {user_id}, azione {action}")
                    cur.execute(call_proc_str, params)
            
            # Il commit è automatico se la procedura ha successo
            self.logger.info(f"Evento sessione registrato: Utente ID {user_id}, Azione {action}, Esito {esito}.")
            return session_id_to_return

        except psycopg2.Error as db_err:
            # Il rollback è automatico in caso di errore
            pgerror_msg = getattr(db_err, 'pgerror', str(db_err))
            self.logger.error(f"Errore DB in register_access per utente {user_id}: {pgerror_msg}", exc_info=True)
            raise DBMError(f"Errore database durante la registrazione dell'evento: {pgerror_msg}") from db_err
        except Exception as e:
            self.logger.error(f"Errore Python in register_access per utente {user_id}: {e}", exc_info=True)
            raise DBMError(f"Errore di sistema imprevisto durante la registrazione dell'evento: {e}") from e

   

    def logout_user(self, user_id: int, session_id: str, ip_address: Optional[str]) -> bool:
        """
        Esegue il logout e gestisce la potenziale perdita di connessione con il server.
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    call_proc_str = f"CALL {self.schema}.logout_utente_sessione(%s, %s, %s, %s);"
                    params = (user_id, session_id, ip_address, self.application_name)
                    self.logger.debug(f"Chiamata a logout_utente_sessione per utente {user_id}, sessione {session_id[:8]}...")
                    cur.execute(call_proc_str, params)

                    self.logger.debug("Pulizia delle variabili di sessione per l'audit.")
                    cur.execute(f"SELECT set_config('{self.schema}.app_user_id', NULL, false);")
                    cur.execute(f"SELECT set_config('{self.schema}.session_id', NULL, false);")
            
            self.logger.info(f"Logout per utente ID {user_id}, sessione {session_id[:8]}... completato.")
            return True

        # --- CORREZIONE: Gestione esplicita della perdita di connessione ---
        except psycopg2.OperationalError as op_err:
            self.logger.critical(f"Logout fallito: persa la connessione con il server DB. Errore: {op_err}", exc_info=True)
            # Azione critica: il pool non è più valido. Chiudiamolo forzatamente.
            self.close_pool()
            return False # Segnala il fallimento
        # --- FINE CORREZIONE ---

        except Exception as e:
            self.logger.error(f"Errore durante il processo di logout per l'utente {user_id}: {e}", exc_info=True)
            return False
    def check_permission(self, utente_id: int, permesso_nome: str) -> bool:
        """Chiama la funzione SQL ha_permesso."""
        try:
            query = "SELECT ha_permesso(%s, %s) AS permesso"
            if self.execute_query(query, (utente_id, permesso_nome)): result = self.fetchone(); return result.get('permesso', False) if result else False
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB verifica permesso '{permesso_nome}' per utente ID {utente_id}: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python verifica permesso '{permesso_nome}' per utente ID {utente_id}: {e}"); return False
    # In catasto_db_manager.py, all'interno della classe CatastoDBManager

    # In catasto_db_manager.py, all'interno della classe CatastoDBManager

    def get_recent_session_logs(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Recupera gli ultimi N eventi di sessione (login, logout, etc.)
        unendo le informazioni con i nomi degli utenti.
        """
        self.logger.info(f"Recupero degli ultimi {limit} log di sessione.")
        
        # --- INIZIO MODIFICA DEFINITIVA ---
        # La query ora usa i nomi corretti delle colonne: 'data_login' e 'indirizzo_ip'
        query = f"""
            SELECT
                sa.data_login,
                sa.azione,
                sa.esito,
                sa.indirizzo_ip,
                u.username,
                u.nome_completo
            FROM {self.schema}.sessioni_accesso sa
            LEFT JOIN {self.schema}.utente u ON sa.utente_id = u.id
            ORDER BY sa.data_login DESC
            LIMIT %s;
        """
        # --- FINE MODIFICA DEFINITIVA ---

        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(query, (limit,))
                    results = [dict(row) for row in cur.fetchall()]
                    return results
        except Exception as e:
            self.logger.error(f"Errore durante il recupero dei log di sessione recenti: {e}", exc_info=True)
            return []
    def get_utenti(self, solo_attivi: Optional[bool] = None) -> List[Dict[str, Any]]:
        """Recupera un elenco di utenti in modo sicuro, con filtro opzionale."""
        query = f"SELECT id, username, nome_completo, email, ruolo, attivo, ultimo_accesso FROM {self.schema}.utente"
        params = []

        if solo_attivi is not None:
            query += " WHERE attivo = %s"
            params.append(solo_attivi)

        query += " ORDER BY username;"
        
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, tuple(params) if params else None)
                    results = [dict(row) for row in cur.fetchall()]
                    self.logger.info(f"Recuperati {len(results)} utenti.")
                    return results
        except Exception as e:
            self.logger.error(f"Errore DB durante il recupero degli utenti: {e}", exc_info=True)
            return []
    def get_utente_by_id(self, utente_id: int) -> Optional[Dict[str, Any]]:
        """Recupera i dettagli di un singolo utente tramite ID, in modo sicuro."""
        if not isinstance(utente_id, int) or utente_id <= 0:
            self.logger.error(f"get_utente_by_id: utente_id non valido: {utente_id}")
            return None

        query = f"SELECT id, username, nome_completo, email, ruolo, attivo FROM {self.schema}.utente WHERE id = %s"
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, (utente_id,))
                    user_data = cur.fetchone()
                    if user_data:
                        return dict(user_data)
                    else:
                        self.logger.warning(f"Nessun utente trovato con ID: {utente_id}")
                        return None
        except Exception as e:
            self.logger.error(f"Errore DB in get_utente_by_id (ID: {utente_id}): {e}", exc_info=True)
            return None

    def update_user_details(self, utente_id: int, nome_completo: Optional[str] = None,
                        email: Optional[str] = None, ruolo: Optional[str] = None,
                        attivo: Optional[bool] = None) -> bool:
        """Aggiorna i dettagli di un utente in modo transazionale e sicuro."""
        if not any([nome_completo is not None, email is not None, ruolo is not None, attivo is not None]):
            self.logger.warning(f"Nessun dettaglio valido fornito per aggiornare utente ID {utente_id}.")
            return False

        fields_to_update, params = [], []
        if nome_completo is not None:
            fields_to_update.append("nome_completo = %s"); params.append(nome_completo)
        if email is not None:
            fields_to_update.append("email = %s"); params.append(email)
        if ruolo is not None:
            if ruolo not in ['admin', 'archivista', 'consultatore']:
                raise DBDataError(f"Ruolo non valido: {ruolo}")
            fields_to_update.append("ruolo = %s"); params.append(ruolo)
        if attivo is not None:
            fields_to_update.append("attivo = %s"); params.append(attivo)
        
        if not fields_to_update:
            return True # Nessuna modifica richiesta

        fields_to_update.append("data_modifica = CURRENT_TIMESTAMP")
        query = f"UPDATE {self.schema}.utente SET {', '.join(fields_to_update)} WHERE id = %s"
        params.append(utente_id)
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, tuple(params))
                    if cur.rowcount == 0:
                        raise DBNotFoundError(f"Utente con ID {utente_id} non trovato per l'aggiornamento.")
            
            self.logger.info(f"Dettagli utente ID {utente_id} aggiornati.")
            return True
        except (DBNotFoundError, DBDataError, DBUniqueConstraintError) as e:
            self.logger.error(f"Errore previsto aggiornando utente {utente_id}: {e}", exc_info=True)
            raise e
        except Exception as e:
            self.logger.error(f"Errore imprevisto DB aggiornando utente {utente_id}: {e}", exc_info=True)
            raise DBMError(f"Impossibile aggiornare l'utente: {e}") from e    
   
    def reset_user_password(self, utente_id: int, new_password_hash: str) -> bool:
        """Resetta la password di un utente in modo transazionale e sicuro."""
        query = f"UPDATE {self.schema}.utente SET password_hash = %s, data_modifica = CURRENT_TIMESTAMP WHERE id = %s"
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (new_password_hash, utente_id))
                    if cur.rowcount == 0:
                        raise DBNotFoundError(f"Utente con ID {utente_id} non trovato per reset password.")
            
            self.logger.info(f"Password resettata per utente ID {utente_id}.")
            return True
        except DBNotFoundError as e:
            self.logger.warning(e)
            raise e
        except Exception as e:
            self.logger.error(f"Errore DB durante il reset password per utente ID {utente_id}: {e}", exc_info=True)
            raise DBMError(f"Errore database durante il reset password: {e}") from e

    def _update_user_active_status(self, utente_id: int, nuovo_stato_attivo: bool) -> bool:
        """Metodo helper per attivare o disattivare un utente in modo transazionale."""
        query = f"UPDATE {self.schema}.utente SET attivo = %s, data_modifica = CURRENT_TIMESTAMP WHERE id = %s"
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (nuovo_stato_attivo, utente_id))
                    if cur.rowcount == 0:
                        raise DBNotFoundError(f"Utente con ID {utente_id} non trovato per aggiornamento stato.")
            
            status_str = "attivato" if nuovo_stato_attivo else "disattivato"
            self.logger.info(f"Utente ID {utente_id} {status_str}.")
            return True
        except (DBNotFoundError, DBMError) as e:
            self.logger.error(f"Errore previsto aggiornando stato utente {utente_id}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Errore imprevisto aggiornando stato utente {utente_id}: {e}", exc_info=True)
            raise DBMError(f"Impossibile aggiornare lo stato dell'utente: {e}") from e

    def deactivate_user(self, utente_id: int) -> bool:
        """Disattiva un utente. Utilizza _update_user_active_status."""
        return self._update_user_active_status(utente_id, False)

    def activate_user(self, utente_id: int) -> bool:
        """Riattiva un utente. Utilizza _update_user_active_status."""
        return self._update_user_active_status(utente_id, True)

    def delete_user_permanently(self, utente_id: int) -> bool:
        """Elimina fisicamente un utente in modo transazionale e sicuro."""
        utente_da_eliminare = self.get_utente_by_id(utente_id) # Usa il metodo già refattorizzato
        if not utente_da_eliminare:
            self.logger.warning(f"Tentativo di eliminare utente ID {utente_id} non trovato.")
            return False
                
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    # La logica di controllo e l'eliminazione avvengono nella stessa transazione
                    if utente_da_eliminare.get('ruolo') == 'admin':
                        cur.execute(f"SELECT COUNT(*) AS count FROM {self.schema}.utente WHERE ruolo = 'admin' AND attivo = TRUE")
                        count_result = cur.fetchone()
                        if count_result and count_result['count'] <= 1:
                            self.logger.error(f"Tentativo di eliminare l'unico admin attivo (ID: {utente_id}). Operazione negata.")
                            # Non solleviamo un'eccezione, ma restituiamo False per bloccare l'operazione
                            # Il context manager eseguirà un rollback/commit innocuo.
                            return False
                    
                    # Se i controlli sono superati, procedi con l'eliminazione
                    cur.execute(f"DELETE FROM {self.schema}.utente WHERE id = %s", (utente_id,))
                    
                    if cur.rowcount == 0:
                        # Caso limite in cui l'utente viene eliminato tra il get iniziale e qui
                        raise DBNotFoundError(f"Utente ID {utente_id} scomparso prima dell'eliminazione finale.")

            # Il commit è automatico se tutto va a buon fine
            self.logger.info(f"Utente ID {utente_id} eliminato fisicamente con successo.")
            return True

        except Exception as e:
            self.logger.error(f"Errore durante l'eliminazione dell'utente ID {utente_id}: {e}", exc_info=True)
            raise DBMError(f"Impossibile eliminare l'utente: {e}") from e
    # --- Metodi Sistema Backup (Invariati rispetto a comune_id) ---
    # In catasto_db_manager.py, SOSTITUISCI la vecchia funzione get_audit_logs

    def get_audit_logs(self,
                    filters: Optional[Dict[str, Any]] = None,
                    page: int = 1,
                    page_size: int = 50,
                    sort_by: str = 'timestamp',
                    sort_order: str = 'DESC'
                    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Recupera i record dalla vista v_audit_dettagliato con filtri, paginazione e ordinamento.
        """
        if filters is None:
            filters = {}

        query_conditions = []
        query_params = []

        # Costruzione delle condizioni WHERE in base ai filtri
        if filters.get("table_name"):
            query_conditions.append("tabella ILIKE %s")
            query_params.append(f"%{filters['table_name']}%")

        # --- NUOVO: Filtro per username ---
        if filters.get("username"):
            query_conditions.append("username ILIKE %s")
            query_params.append(f"%{filters['username']}%")
        # --- FINE NUOVO ---

        # ... (gli altri filtri come operation_char, record_id, date rimangono uguali) ...
        if filters.get("operation_char"):
            query_conditions.append("operazione = %s")
            query_params.append(filters["operation_char"])
        if filters.get("record_id") is not None:
            query_conditions.append("record_id = %s")
            query_params.append(filters["record_id"])
        if filters.get("start_datetime"):
            query_conditions.append("timestamp >= %s")
            query_params.append(filters["start_datetime"])
        if filters.get("end_datetime"):
            query_conditions.append("timestamp <= %s")
            query_params.append(filters["end_datetime"])

        where_clause = ""
        if query_conditions:
            where_clause = "WHERE " + " AND ".join(query_conditions)

        # La query ora interroga la VISTA, non la tabella diretta
        base_query = f"FROM {self.schema}.v_audit_dettagliato {where_clause}"
        count_query = f"SELECT COUNT(*) {base_query};"

        # Validazione e costruzione ORDER BY (invariato)
        allowed_sort_columns = ['id', 'timestamp', 'username', 'tabella', 'operazione', 'record_id']
        if sort_by not in allowed_sort_columns: sort_by = 'timestamp'
        if sort_order.upper() not in ['ASC', 'DESC']: sort_order = 'DESC'
        order_by_clause = f"ORDER BY {sort_by} {sort_order.upper()}"

        offset = (page - 1) * page_size

        # La query dei dati ora seleziona direttamente dalla vista
        data_query = f"""
            SELECT * {base_query}
            {order_by_clause}
            LIMIT %s OFFSET %s;
        """
        query_params_data = query_params + [page_size, offset]

        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(count_query, query_params)
                    total_records = cur.fetchone()[0]

                    if total_records > 0:
                        cur.execute(data_query, query_params_data)
                        logs = [dict(row) for row in cur.fetchall()]
                    else:
                        logs = []

        except Exception as e:
            self.logger.error(f"Errore durante il recupero dei log di audit: {e}", exc_info=True)
            return [], 0

        return logs, total_records
    def register_backup_log(self, nome_file: str, utente: str, tipo: str, esito: bool,
                            percorso_file: str, dimensione_bytes: Optional[int] = None,
                            messaggio: Optional[str] = None) -> Optional[int]:
        """Chiama la funzione SQL registra_backup."""
        try:
            query = "SELECT registra_backup(%s, %s, %s, %s, %s, %s, %s)"
            params = (nome_file, utente, dimensione_bytes, tipo, esito, messaggio, percorso_file)
            if self.execute_query(query, params):
                 result = self.fetchone(); self.commit(); backup_id = result.get('registra_backup') if result else None
                 if backup_id: logger.info(f"Log backup registrato ID: {backup_id} per '{nome_file}'")
                 else: logger.error(f"registra_backup non ha restituito ID per '{nome_file}'.")
                 return backup_id
        except psycopg2.Error as db_err: logger.error(f"Errore DB reg log backup '{nome_file}': {db_err}")
        except Exception as e: logger.error(f"Errore Python reg log backup '{nome_file}': {e}"); self.rollback()
        return None
    
    # Assicurati che anche i metodi come _find_executable, get_backup_command_parts, 
    # get_restore_command_parts siano presenti come li avevamo definiti.
    # Non interagiscono direttamente con il pool per le loro query, ma usano parametri da self.conn_params_dict
    def _find_executable(self, name: str) -> Optional[str]:
        executable_path = shutil.which(name)
        if executable_path:
            self.logger.info(f"Trovato eseguibile '{name}' in: {executable_path}")
            return executable_path
        else:
            self.logger.warning(f"Eseguibile '{name}' non trovato nel PATH di sistema.")
            return None # Modificato da return "" per coerenza con Optional[str]


    def _resolve_executable_path(self, user_provided_path: str, default_name: str) -> Optional[str]:
        # Se l'utente fornisce un percorso valido, usa quello
        if user_provided_path and os.path.isabs(user_provided_path) and os.path.exists(user_provided_path) and os.path.isfile(user_provided_path):
            self.logger.info(f"Utilizzo del percorso eseguibile fornito dall'utente: {user_provided_path} (per default {default_name})")
            return user_provided_path
        elif user_provided_path: 
            self.logger.warning(f"Percorso fornito '{user_provided_path}' per '{default_name}' non valido. Tento di cercare '{default_name}' nel PATH.")

        # Altrimenti, cerca il default_name nel PATH
        found_path_in_system = shutil.which(default_name) # default_name qui sarà "pg_restore.exe" o "psql.exe"
        if found_path_in_system:
            self.logger.info(f"Trovato eseguibile '{default_name}' nel PATH di sistema: {found_path_in_system}")
            return found_path_in_system
        else:
            self.logger.error(f"Eseguibile '{default_name}' non trovato nel PATH e nessun percorso valido fornito.")
            return None

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
        """Chiama la procedura SQL pulizia_backup_vecchi."""
        try:
            call_proc = "CALL pulizia_backup_vecchi(%s)"
            if self.execute_query(call_proc, (giorni_conservazione,)): self.commit(); logger.info(f"Eseguita pulizia log backup più vecchi di {giorni_conservazione} giorni."); return True
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB pulizia log backup: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python pulizia log backup: {e}"); self.rollback(); return False

    def generate_backup_script(self, backup_dir: str) -> Optional[str]:
        """Chiama la funzione SQL genera_script_backup_automatico."""
        try:
            query = "SELECT genera_script_backup_automatico(%s) AS script_content"
            if self.execute_query(query, (backup_dir,)): result = self.fetchone(); return result.get('script_content') if result else None
        except psycopg2.Error as db_err: logger.error(f"Errore DB gen script backup: {db_err}"); return None
        except Exception as e: logger.error(f"Errore Python gen script backup: {e}"); return None
        return None

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

    
    # --- Metodi Ricerca Avanzata (MODIFICATI) ---

    def ricerca_avanzata_possessori(self, query_text: str, similarity_threshold: Optional[float] = 0.2) -> List[Dict[str, Any]]:
        """
        Esegue una ricerca avanzata di possessori chiamando una funzione SQL in modo sicuro.
        """
        query = f"SELECT * FROM {self.schema}.ricerca_avanzata_possessori(%s::TEXT, %s::REAL);"
        params = (query_text, similarity_threshold)
        
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, params)
                    results = [dict(row) for row in cur.fetchall()]
                    self.logger.info(f"Ricerca avanzata possessori per '{query_text}' ha prodotto {len(results)} risultati.")
                    return results
        except Exception as e:
            self.logger.error(f"Errore DB durante la ricerca avanzata dei possessori: {e}", exc_info=True)
            return [] # Rilascia SEMPRE la connessione al pool

    def ricerca_avanzata_immobili_gui(self,
                                   comune_id: Optional[int] = None,
                                   localita_id: Optional[int] = None,
                                   natura_search: Optional[str] = None,
                                   classificazione_search: Optional[str] = None,
                                   consistenza_search: Optional[str] = None,
                                   piani_min: Optional[int] = None,
                                   piani_max: Optional[int] = None,
                                   vani_min: Optional[int] = None,
                                   vani_max: Optional[int] = None,
                                   nome_possessore_search: Optional[str] = None,
                                   data_inizio_possesso_search: Optional[date] = None, # Nome corretto dal metodo Python
                                   data_fine_possesso_search: Optional[date] = None   # Nome corretto dal metodo Python
                                   ) -> List[Dict[str, Any]]:
        """Chiama la funzione SQL ricerca_avanzata_immobili (DA DEFINIRE e MODIFICARE per comune_id)."""
        logger.warning("La funzione SQL 'ricerca_avanzata_immobili' potrebbe non essere definita o aggiornata per comune_id.")
        # Query con segnaposto posizionali
        query = """
            SELECT * FROM catasto.cerca_immobili_avanzato(
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            );
        """
        # I parametri devono essere NELL'ESATTO ORDINE della definizione della funzione SQL
        params = (
            comune_id,                     # p_comune_id INTEGER
            localita_id,                   # p_localita_id INTEGER
            natura_search,                 # p_natura_search TEXT
            classificazione_search,        # p_classificazione_search TEXT
            consistenza_search,            # p_consistenza_search TEXT
            piani_min,                     # p_piani_min INTEGER
            piani_max,                     # p_piani_max INTEGER
            vani_min,                      # p_vani_min INTEGER
            vani_max,                      # p_vani_max INTEGER
            nome_possessore_search,        # p_nome_possessore_search TEXT
            data_inizio_possesso_search,   # p_data_inizio_possesso DATE
            data_fine_possesso_search      # p_data_fine_possesso DATE
        )

        self.logger.debug(f"Chiamata a catasto.cerca_immobili_avanzato con parametri POSIZIONALI: {params}")

        if self.execute_query(query, params):
            results = self.fetchall()
            self.logger.info(f"Ricerca avanzata immobili GUI ha restituito {len(results)} risultati.")
            return results if results else []
        else:
            self.logger.error("Errore durante l'esecuzione di ricerca_avanzata_immobili_gui.")
            return []

    # --- Metodi Funzionalità Storiche Avanzate (MODIFICATI) ---

    def get_historical_periods(self) -> List[Dict[str, Any]]:
        """
        Recupera i periodi storici definiti dalla tabella 'periodo_storico' in modo sicuro.
        """
        query = f"SELECT id, nome, anno_inizio, anno_fine, descrizione FROM {self.schema}.periodo_storico ORDER BY anno_inizio;"
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query)
                    results = [dict(row) for row in cur.fetchall()]
                    self.logger.info(f"Recuperati {len(results)} periodi storici.")
                    return results
        except Exception as e:
            self.logger.error(f"Errore DB in get_historical_periods: {e}", exc_info=True)
            return []
    

    def register_historical_name(self, entity_type: str, entity_id: int, name: str,
                             period_id: int, year_start: int, year_end: Optional[int] = None,
                             notes: Optional[str] = None) -> bool:
        """Chiama la procedura SQL registra_nome_storico in modo sicuro."""
        call_proc = f"CALL {self.schema}.registra_nome_storico(%s, %s, %s, %s, %s, %s, %s)"
        params = (entity_type, entity_id, name, period_id, year_start, year_end, notes)
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(call_proc, params)
            self.logger.info(f"Registrato nome storico '{name}' per {entity_type} ID {entity_id}.")
            return True
        except Exception as e:
            self.logger.error(f"Errore DB in register_historical_name: {e}", exc_info=True)
            raise DBMError(f"Impossibile registrare il nome storico: {e}") from e


    def search_historical_documents(self, title: Optional[str] = None, doc_type: Optional[str] = None,
                                    period_id: Optional[int] = None, year_start: Optional[int] = None,
                                    year_end: Optional[int] = None, partita_id: Optional[int] = None) -> List[Dict]:
        """Chiama la funzione SQL ricerca_documenti_storici (SQL aggiornata per join)."""
        try:
            # Funzione SQL aggiornata per join corretti
            query = "SELECT * FROM ricerca_documenti_storici(%s, %s, %s, %s, %s, %s)"
            params = (title, doc_type, period_id, year_start, year_end, partita_id)
            if self.execute_query(query, params): return self.fetchall()
        except psycopg2.Error as db_err: logger.error(f"Errore DB search_historical_documents: {db_err}"); return []
        except Exception as e: logger.error(f"Errore Python search_historical_documents: {e}"); return []
        return []
    

    def get_periodo_storico_details(self, periodo_id: int) -> Optional[Dict[str, Any]]:
        """Recupera i dettagli di un singolo periodo storico in modo sicuro."""
        if not isinstance(periodo_id, int) or periodo_id <= 0:
            self.logger.error(f"ID periodo storico non valido: {periodo_id}")
            return None

        query = f"SELECT * FROM {self.schema}.periodo_storico WHERE id = %s;"
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, (periodo_id,))
                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            self.logger.error(f"Errore DB in get_periodo_storico_details (ID: {periodo_id}): {e}", exc_info=True)
            return None

    # All'interno della classe CatastoDBManager in catasto_db_manager.py

    def update_periodo_storico(self, periodo_id: int, dati_modificati: Dict[str, Any]) -> bool:
        """Aggiorna i dati di un periodo storico esistente in modo transazionale e sicuro."""
        if not isinstance(periodo_id, int) or periodo_id <= 0:
            raise DBDataError(f"ID periodo storico non valido: {periodo_id}")
        if not dati_modificati:
            raise DBDataError("Nessun dato fornito per l'aggiornamento.")

        set_clauses, params = [], []
        campi_permessi = {"nome": "nome", "anno_inizio": "anno_inizio", "anno_fine": "anno_fine", "descrizione": "descrizione"}

        for key, col in campi_permessi.items():
            if key in dati_modificati:
                valore = dati_modificati[key]
                if key == "nome" and not (valore and str(valore).strip()):
                    raise DBDataError("Il nome del periodo storico non può essere vuoto.")
                
                set_clauses.append(f"{col} = %s")
                params.append(valore if not isinstance(valore, str) else valore.strip())

        if not set_clauses:
            self.logger.info(f"Nessun campo aggiornabile fornito per periodo ID {periodo_id}.")
            return True

        # Se la sua tabella 'periodo_storico' avesse una colonna 'data_modifica', andrebbe aggiunta qui:
        # set_clauses.append("data_modifica = CURRENT_TIMESTAMP")
        
        query = f"UPDATE {self.schema}.periodo_storico SET {', '.join(set_clauses)} WHERE id = %s;"
        params.append(periodo_id)
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, tuple(params))
                    if cur.rowcount == 0:
                        raise DBNotFoundError(f"Periodo storico con ID {periodo_id} non trovato o dati identici.")
            
            self.logger.info(f"Periodo storico ID {periodo_id} aggiornato con successo.")
            return True

        except (DBNotFoundError, DBDataError, DBUniqueConstraintError, psycopg2.errors.CheckViolation) as e:
            self.logger.error(f"Errore previsto aggiornando periodo storico {periodo_id}: {e}", exc_info=True)
            raise e  # Rilancia l'eccezione specifica
        except Exception as e:
            self.logger.error(f"Errore imprevisto DB aggiornando periodo storico {periodo_id}: {e}", exc_info=True)
            raise DBMError(f"Impossibile aggiornare il periodo storico: {e}") from e

    def aggiungi_periodo_storico(self, nome: str, anno_inizio: int, anno_fine: Optional[int], descrizione: Optional[str]) -> int:
        """Crea un nuovo periodo storico nel database."""
        if not nome or not nome.strip():
            raise DBDataError("Il nome del periodo non può essere vuoto.")
        if anno_fine is not None and anno_fine < anno_inizio:
            raise DBDataError("L'anno di fine non può essere precedente a quello di inizio.")

        query = """
            INSERT INTO catasto.periodo_storico (nome, anno_inizio, anno_fine, descrizione)
            VALUES (%s, %s, %s, %s) RETURNING id;
        """
        params = (nome.strip(), anno_inizio, anno_fine, descrizione)

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    result = cur.fetchone()
                    if result:
                        return result[0]
                    raise DBMError("Creazione del periodo storico fallita.")
        except psycopg2.errors.UniqueViolation:
            raise DBUniqueConstraintError(f"Un periodo storico con nome '{nome}' esiste già.") from None
        except Exception as e:
            self.logger.error(f"Errore DB in aggiungi_periodo_storico: {e}", exc_info=True)
            raise DBMError("Impossibile creare il periodo storico.") from e

    def elimina_periodo_storico(self, periodo_id: int) -> bool:
        """Elimina un periodo storico, solo se non è utilizzato."""
        query = "DELETE FROM catasto.periodo_storico WHERE id = %s;"
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (periodo_id,))
                    if cur.rowcount == 0:
                        raise DBNotFoundError(f"Nessun periodo storico trovato con ID {periodo_id}.")
                    return True
        except psycopg2.errors.ForeignKeyViolation:
            raise DBMError("Impossibile eliminare: questo periodo è utilizzato da uno o più comuni.") from None
        except Exception as e:
            self.logger.error(f"Errore DB in elimina_periodo_storico: {e}", exc_info=True)
            raise DBMError("Eliminazione del periodo storico fallita.") from e

    def get_property_genealogy(self, partita_id: int) -> List[Dict]:
        """Chiama la funzione SQL albero_genealogico_proprieta in modo sicuro."""
        query = f"SELECT * FROM {self.schema}.albero_genealogico_proprieta(%s)"
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(query, (partita_id,))
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            self.logger.error(f"Errore DB in get_property_genealogy (ID: {partita_id}): {e}", exc_info=True)
            return []

    def get_cadastral_stats_by_period(self, comune_id: Optional[int] = None, year_start: int = 1900, # Usa comune_id
                                       year_end: Optional[int] = None) -> List[Dict]:
        """Chiama la funzione SQL statistiche_catastali_periodo (MODIFICATA per comune_id)."""
        logger.warning("La funzione SQL 'statistiche_catastali_periodo' potrebbe non essere aggiornata per comune_id.")
        try:
            # Assumiamo funzione SQL aggiornata per comune_id
            if year_end is None: year_end = datetime.now().year
            query = "SELECT * FROM statistiche_catastali_periodo(%s, %s, %s)"
            params = (comune_id, year_start, year_end) # Passa ID
            if self.execute_query(query, params): return self.fetchall()
        except psycopg2.errors.UndefinedFunction: logger.warning("Funzione 'statistiche_catastali_periodo' non trovata."); return []
        except psycopg2.Error as db_err: logger.error(f"Errore DB get_cadastral_stats_by_period: {db_err}"); return []
        except Exception as e: logger.error(f"Errore Python get_cadastral_stats_by_period: {e}"); return []
        return []

    def link_document_to_partita(self, document_id: int, partita_id: int,
                                 relevance: str = 'correlata', notes: Optional[str] = None) -> bool:
        """Collega un documento storico a una partita."""
        if relevance not in ['primaria', 'secondaria', 'correlata']: logger.error(f"Rilevanza non valida: '{relevance}'"); return False
        query = """
            INSERT INTO documento_partita (documento_id, partita_id, rilevanza, note) VALUES (%s, %s, %s, %s)
            ON CONFLICT (documento_id, partita_id) DO UPDATE SET rilevanza = EXCLUDED.rilevanza, note = EXCLUDED.note
        """
        try:
            if self.execute_query(query, (document_id, partita_id, relevance, notes)): self.commit(); logger.info(f"Link creato/aggiornato Doc {document_id} - Partita {partita_id}."); return True
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB link doc-partita: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python link doc-partita: {e}"); self.rollback(); return False
        
    # All'interno della classe CatastoDBManager, nel file catasto_db_manager.py

    def ricerca_avanzata_immobili_gui(self, comune_id: Optional[int] = None, localita_id: Optional[int] = None,
                                      natura_search: Optional[str] = None, classificazione_search: Optional[str] = None,
                                      consistenza_search: Optional[str] = None, # Ricerca testuale per consistenza
                                      piani_min: Optional[int] = None, piani_max: Optional[int] = None,
                                      vani_min: Optional[int] = None, vani_max: Optional[int] = None,
                                      nome_possessore_search: Optional[str] = None,
                                      data_inizio_possesso_search: Optional[date] = None, # Previsto per il futuro
                                      data_fine_possesso_search: Optional[date] = None    # Previsto per il futuro
                                     ) -> List[Dict[str, Any]]:
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    # La stringa della query ora corrisponde ai 12 parametri della funzione SQL estesa
                    # I cast ::TIPODATO sono una buona pratica se i default nella funzione SQL non sono espliciti con ::TIPODATO
                    # o se si vuole essere estremamente sicuri.
                    # Se la funzione SQL ha DEFAULT NULL e tipi chiari, i cast qui potrebbero non essere strettamente necessari
                    # ma non fanno male.
                    query = f"""
                        SELECT * FROM {self.schema}.ricerca_avanzata_immobili(
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """
                    # Nota: i parametri devono essere nell'ordine esatto definito dalla funzione SQL
                    params = (
                        comune_id, localita_id, natura_search, classificazione_search, consistenza_search,
                        piani_min, piani_max, vani_min, vani_max, nome_possessore_search,
                        data_inizio_possesso_search, data_fine_possesso_search
                    )

                    self.logger.debug(f"Chiamata a {self.schema}.ricerca_avanzata_immobili con parametri POSIZIONALI: {params}")
                    cur.execute(query, params)
                    results = [dict(row) for row in cur.fetchall()]
                    self.logger.info(f"Ricerca avanzata immobili ha restituito {len(results)} risultati.")
                    return results
        except psycopg2.Error as e:
            self.logger.error(f"Errore DB specifico durante l'esecuzione di ricerca_avanzata_immobili_gui: {e}", exc_info=True)
            # Potresti voler sollevare un'eccezione personalizzata o gestire l'errore qui
            return []
        except Exception as e:
            self.logger.error(f"Errore generico durante ricerca_avanzata_immobili_gui: {e}", exc_info=True)
            return []
    def set_audit_session_variables(self, app_user_id: Optional[int], session_id: Optional[str]) -> bool:
        """Imposta le variabili di sessione PostgreSQL per l'audit log in modo sicuro."""
        if app_user_id is None or session_id is None:
            self.logger.warning("Tentativo di impostare variabili audit con None.")
            return False
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Il terzo argomento 'false' rende l'impostazione valida per l'intera sessione
                    cur.execute("SELECT set_config(%s, %s, false);", (f"{self.schema}.app_user_id", str(app_user_id)))
                    cur.execute("SELECT set_config(%s, %s, false);", (f"{self.schema}.session_id", session_id))
            
            # Il commit è gestito automaticamente dal context manager _get_connection
            self.logger.info(f"Variabili di sessione per audit impostate: app_user_id={app_user_id}, session_id={session_id[:8]}...")
            return True
            
        except Exception as e:
            self.logger.error(f"Errore DB impostando variabili audit: {e}", exc_info=True)
            return False

    
    def execute_sql_from_file(self, file_path: str) -> Tuple[bool, str]:
        """Esegue uno script SQL da un file in modo sicuro, gestendo l'autocommit."""
        if not os.path.exists(file_path):
            return False, f"File SQL non trovato: {file_path}"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            with self._get_connection() as conn:
                # Imposta il livello di isolamento per la singola operazione
                # Questo è il modo corretto di gestire l'autocommit con un pool
                conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                with conn.cursor() as cur:
                    self.logger.info(f"Esecuzione script SQL da file: {file_path}")
                    cur.execute(sql_content)
            
            self.logger.info(f"Script SQL {file_path} eseguito con successo.")
            return True, f"Script {os.path.basename(file_path)} eseguito con successo."

        except Exception as e:
            msg = f"Errore eseguendo script {file_path}: {e}"
            self.logger.error(msg, exc_info=True)
            # Il context manager gestisce già il rollback, ma in autocommit non è rilevante.
            # La connessione verrà comunque restituita correttamente al pool.
            return False, msg
    def clear_audit_session_variables(self) -> bool:
        """Resetta le variabili di sessione per l'audit in modo sicuro."""
        self.logger.info("Reset variabili di sessione per audit...")
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Impostare a NULL è un modo esplicito e sicuro per resettare
                    cur.execute(f"SELECT set_config('{self.schema}.app_user_id', NULL, false);")
                    cur.execute(f"SELECT set_config('{self.schema}.session_id', NULL, false);")
            
            self.logger.info("Variabili di sessione per audit resettate con successo.")
            return True
        except Exception as e:
            self.logger.error(f"Errore DB resettando variabili audit: {e}", exc_info=True)
            return False

    def aggiungi_documento_storico(self, titolo: str, tipo_documento: str, percorso_file: str,
                              descrizione: Optional[str] = None, anno: Optional[int] = None,
                              periodo_id: Optional[int] = None, 
                              metadati_json: Optional[str] = None) -> int:
        """Inserisce un nuovo record nella tabella documento_storico in modo sicuro."""
        query = f"""
            INSERT INTO {self.schema}.documento_storico 
                (titolo, tipo_documento, percorso_file, descrizione, anno, periodo_id, metadati)
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
            RETURNING id;
        """
        params = (titolo, tipo_documento, percorso_file, descrizione, anno, periodo_id, metadati_json)
        
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    self.logger.info(f"Aggiunta documento: {titolo}")
                    cur.execute(query, params)
                    result = cur.fetchone()
                    if not result:
                        raise DBMError("Creazione del documento fallita, nessun ID restituito.")
                    doc_id = result['id']
            
            self.logger.info(f"Documento storico ID {doc_id} aggiunto con successo.")
            return doc_id
            
        except Exception as e:
            self.logger.error(f"Errore DB aggiungendo documento storico '{titolo}': {e}", exc_info=True)
            raise DBMError(f"Impossibile aggiungere il documento: {e}") from e

    def collega_documento_a_partita(self, documento_id: int, partita_id: int, 
                               rilevanza: str, note: Optional[str] = None) -> bool:
        """Inserisce o aggiorna un record nella tabella di collegamento documento_partita."""
        if rilevanza not in ['primaria', 'secondaria', 'correlata']:
            raise DBDataError(f"Valore di rilevanza non valido: {rilevanza}.")
        
        query = f"""
            INSERT INTO {self.schema}.documento_partita
                (documento_id, partita_id, rilevanza, note)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (documento_id, partita_id) DO UPDATE SET 
                rilevanza = EXCLUDED.rilevanza, 
                note = EXCLUDED.note;
        """
        params = (documento_id, partita_id, rilevanza, note)
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    self.logger.info(f"Collegamento doc ID {documento_id} a partita ID {partita_id}.")
                    cur.execute(query, params)
            
            self.logger.info("Documento collegato/aggiornato alla partita con successo.")
            return True
        except Exception as e:
            self.logger.error(f"Errore DB collegando doc {documento_id} a partita {partita_id}: {e}", exc_info=True)
            raise DBMError(f"Impossibile collegare il documento: {e}") from e

    # In catasto_db_manager.py, SOSTITUISCI il metodo get_documenti_per_partita

    def get_documenti_per_partita(self, partita_id: int) -> List[Dict[str, Any]]:
        """Recupera l'elenco dei documenti associati a una partita in modo sicuro."""
        # --- INIZIO CORREZIONE: Aggiunti dp.documento_id e dp.partita_id alla SELECT ---
        query = f"""
            SELECT
                ds.id as documento_id, ds.titolo, ds.tipo_documento, ds.percorso_file, ds.anno,
                dp.rilevanza, dp.note as note_legame, ps.nome as nome_periodo,
                dp.documento_id AS rel_documento_id, 
                dp.partita_id AS rel_partita_id
            FROM {self.schema}.documento_storico ds
            JOIN {self.schema}.documento_partita dp ON ds.id = dp.documento_id
            LEFT JOIN {self.schema}.periodo_storico ps ON ds.periodo_id = ps.id
            WHERE dp.partita_id = %s
            ORDER BY ds.anno DESC, ds.titolo;
        """
        # --- FINE CORREZIONE ---
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(query, (partita_id,))
                    documenti = [dict(row) for row in cur.fetchall()]
                    self.logger.info(f"Recuperati {len(documenti)} documenti per partita ID {partita_id}.")
                    return documenti
        except Exception as e:
            self.logger.error(f"Errore DB recuperando documenti per partita ID {partita_id}: {e}", exc_info=True)
            return []

    def scollega_documento_da_partita(self, documento_id: int, partita_id: int) -> bool:
        """Rimuove un legame documento-partita in modo transazionale e sicuro."""
        if not (isinstance(documento_id, int) and documento_id > 0):
            raise DBDataError(f"ID documento non valido: {documento_id}")
        if not (isinstance(partita_id, int) and partita_id > 0):
            raise DBDataError(f"ID partita non valido: {partita_id}")

        query = f"DELETE FROM {self.schema}.documento_partita WHERE documento_id = %s AND partita_id = %s;"
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (documento_id, partita_id))
                    if cur.rowcount == 0:
                        raise DBNotFoundError(f"Nessun legame trovato tra doc ID {documento_id} e partita ID {partita_id}.")
            
            self.logger.info(f"Legame tra doc {documento_id} e partita {partita_id} rimosso.")
            return True
        except DBNotFoundError as e:
            self.logger.warning(e)
            raise e
        except Exception as e:
            self.logger.error(f"Errore DB scollegando doc {documento_id} da partita {partita_id}: {e}", exc_info=True)
            raise DBMError(f"Impossibile scollegare il documento: {e}") from e
                
    # ========================================================================
    # NUOVA SEZIONE: LOGICA DI RICERCA FUZZY UNIFICATA (VERSIONE FINALE v3)
    # ========================================================================

    def search_all_entities_fuzzy(self, query_text: str,
                                search_possessori: bool = True,
                                search_localita: bool = True,
                                search_immobili: bool = True,
                                search_variazioni: bool = True,  # AGGIUNTO
                                search_contratti: bool = True,   # AGGIUNTO
                                search_partite: bool = True,     # AGGIUNTO
                                max_results_per_type: int = 50,
                                similarity_threshold: float = 0.3) -> Dict[str, List[Dict]]:
        """
        Metodo orchestratore per la ricerca fuzzy che riusa una singola connessione.
        """
        self.logger.info(f"Avvio ricerca fuzzy ottimizzata per: '{query_text}' con soglia {similarity_threshold}")
        
        all_results = {
            "possessore": [], "localita": [], "immobile": [],
            "variazione": [], "contratto": [], "partita": [] # AGGIUNTO
        }

        try:
            with self._get_connection() as conn:
                if search_possessori:
                    all_results["possessore"] = self._search_possessori_fuzzy_internal(conn, query_text, similarity_threshold, max_results_per_type)
                if search_localita:
                    all_results["localita"] = self._search_localita_fuzzy_internal(conn, query_text, similarity_threshold, max_results_per_type)
                if search_immobili:
                    all_results["immobile"] = self._search_immobili_fuzzy_internal(conn, query_text, similarity_threshold, max_results_per_type)
                # --- AGGIUNGERE QUESTE CHIAMATE ---
                if search_variazioni:
                    all_results["variazione"] = self._search_variazioni_fuzzy_internal(conn, query_text, similarity_threshold, max_results_per_type)
                if search_contratti:
                    all_results["contratto"] = self._search_contratti_fuzzy_internal(conn, query_text, similarity_threshold, max_results_per_type)
                if search_partite:
                    all_results["partita"] = self._search_partite_fuzzy_internal(conn, query_text, similarity_threshold, max_results_per_type)
                # --- FINE AGGIUNTE ---
            
            total_found = sum(len(v) for v in all_results.values())
            self.logger.info(f"Ricerca fuzzy completata. Trovati {total_found} risultati totali.")
            return all_results

        except psycopg2.pool.PoolError as pe:
            self.logger.error(f"Pool di connessioni esaurito durante la ricerca fuzzy: {pe}")
            return {}
        except Exception as e:
            self.logger.error(f"Errore critico durante search_all_entities_fuzzy: {e}", exc_info=True)
            return {}

    # --- METODI DI RICERCA INTERNI (con correzione finale a DictCursor e partita_id) ---

    def _search_variazioni_fuzzy_internal(self, conn, query: str, threshold: float, limit: int) -> List[Dict]:
        """Ricerca fuzzy interna per le variazioni (su tipo e nominativo di riferimento)."""
        # --- CORREZIONE: Sostituito v.note (inesistente) con v.nominativo_riferimento ---
        sql = f"""
            SELECT
                v.id AS entity_id,
                'Variazione ' || v.tipo || ' del ' || TO_CHAR(v.data_variazione, 'DD/MM/YYYY') AS display_text,
                'Rif: ' || COALESCE(v.nominativo_riferimento, 'N/D') || ' | Partita Origine: ' || po.numero_partita AS detail_text,
                greatest(
                    similarity(v.tipo, %s),
                    similarity(v.nominativo_riferimento, %s)
                ) AS similarity_score,
                CASE
                    WHEN similarity(v.tipo, %s) > similarity(v.nominativo_riferimento, %s) THEN 'tipo'
                    ELSE 'nominativo_riferimento'
                END AS search_field,
                v.tipo,
                v.data_variazione,
                v.nominativo_riferimento AS descrizione
            FROM {self.schema}.variazione v
            LEFT JOIN {self.schema}.partita po ON v.partita_origine_id = po.id
            WHERE greatest(
                    similarity(v.tipo, %s),
                    similarity(v.nominativo_riferimento, %s)
                ) >= %s
            ORDER BY similarity_score DESC
            LIMIT %s;
        """
        try:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                # I parametri sono ripetuti per ogni segnaposto '%' nella query
                cur.execute(sql, (query, query, query, query, query, query, threshold, limit))
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            self.logger.error(f"Errore ricerca fuzzy variazioni: {e}", exc_info=True)
            return []

    # In catasto_db_manager.py, SOSTITUISCI il metodo _search_localita_fuzzy_internal

    def _search_localita_fuzzy_internal(self, conn, query: str, threshold: float, limit: int) -> List[Dict]:
        """Ricerca fuzzy interna per le località, usando la nuova tabella tipo_localita."""
        # --- INIZIO CORREZIONE ---
        # La query ora fa un JOIN con tipo_localita per ottenere il nome del tipo
        sql = f"""
            SELECT
                l.id AS entity_id,
                l.nome AS display_text,
                'Tipo: ' || COALESCE(tl.nome, 'N/D') || ', Civico: ' || COALESCE(CAST(l.civico AS TEXT), 'N/A') || ' | Comune: ' || c.nome AS detail_text,
                similarity(l.nome, %s) AS similarity_score,
                'nome' AS search_field,
                l.nome,
                tl.nome AS tipo, -- Selezioniamo il nome dalla tabella joinata
                l.civico,
                c.nome as comune_nome,
                COALESCE(im.num_immobili, 0) as num_immobili
            FROM {self.schema}.localita l
            JOIN {self.schema}.comune c ON l.comune_id = c.id
            LEFT JOIN {self.schema}.tipo_localita tl ON l.tipo_id = tl.id -- <-- JOIN con la nuova tabella
            LEFT JOIN (
                SELECT localita_id, COUNT(*) as num_immobili
                FROM {self.schema}.immobile
                GROUP BY localita_id
            ) im ON l.id = im.localita_id
            WHERE similarity(l.nome, %s) >= %s
            ORDER BY similarity_score DESC
            LIMIT %s;
        """
        # --- FINE CORREZIONE ---
        try:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(sql, (query, query, threshold, limit))
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            self.logger.error(f"Errore ricerca fuzzy località: {e}", exc_info=True)
            return []

    def _search_possessori_fuzzy_internal(self, conn, query: str, threshold: float, limit: int) -> List[Dict]:
        """Ricerca fuzzy interna per i possessori, restituendo tutti i campi necessari."""
        sql = f"""
            SELECT
                p.id AS entity_id,
                p.nome_completo AS display_text,
                'Comune: ' || c.nome || ' | Partite: ' || COALESCE(ps.num_partite, 0) AS detail_text,
                greatest(similarity(p.nome_completo, %s), similarity(p.cognome_nome, %s)) AS similarity_score,
                CASE
                    WHEN similarity(p.nome_completo, %s) > similarity(p.cognome_nome, %s) THEN 'nome_completo'
                    ELSE 'cognome_nome'
                END AS search_field,
                p.nome_completo,
                c.nome as comune_nome,
                COALESCE(ps.num_partite, 0) as num_partite
            FROM {self.schema}.possessore p
            JOIN {self.schema}.comune c ON p.comune_id = c.id
            LEFT JOIN (
                SELECT possessore_id, COUNT(*) as num_partite
                FROM {self.schema}.partita_possessore
                GROUP BY possessore_id
            ) ps ON p.id = ps.possessore_id
            WHERE greatest(similarity(p.nome_completo, %s), similarity(p.cognome_nome, %s)) >= %s
            ORDER BY similarity_score DESC
            LIMIT %s;
        """
        try:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(sql, (query, query, query, query, query, query, threshold, limit))
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            self.logger.error(f"Errore ricerca fuzzy possessori: {e}", exc_info=True)
            return []
    def _search_immobili_fuzzy_internal(self, conn, query: str, threshold: float, limit: int) -> List[Dict]:
        """Ricerca fuzzy interna per gli immobili, includendo il suffisso della partita."""
        # --- MODIFICA: Aggiunto pa.suffisso_partita e aggiornato detail_text ---
        sql = f"""
            SELECT
                i.id AS entity_id,
                i.natura || ' - ' || i.classificazione AS display_text,
                'Partita N: ' || pa.numero_partita || COALESCE(' (' || pa.suffisso_partita || ')', '') || ' | Comune: ' || c.nome AS detail_text,
                greatest(similarity(i.natura, %s), similarity(i.classificazione, %s)) AS similarity_score,
                CASE
                    WHEN similarity(i.natura, %s) > similarity(i.classificazione, %s) THEN 'natura'
                    ELSE 'classificazione'
                END AS search_field,
                i.natura,
                i.classificazione,
                pa.numero_partita,
                pa.suffisso_partita, -- AGGIUNTO
                c.nome as comune_nome
            FROM {self.schema}.immobile i
            JOIN {self.schema}.partita pa ON i.partita_id = pa.id
            JOIN {self.schema}.comune c ON pa.comune_id = c.id
            WHERE greatest(similarity(i.natura, %s), similarity(i.classificazione, %s)) >= %s
            ORDER BY similarity_score DESC
            LIMIT %s;
        """
        try:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(sql, (query, query, query, query, query, query, threshold, limit))
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            self.logger.error(f"Errore ricerca fuzzy immobili: {e}", exc_info=True)
            return []
        
    def _search_variazioni_fuzzy_internal(self, conn, query: str, threshold: float, limit: int) -> List[Dict]:
        """Ricerca fuzzy interna per le variazioni (su tipo e nominativo di riferimento)."""
        # --- CORREZIONE: Sostituisce v.note (inesistente) con v.nominativo_riferimento (esistente) ---
        sql = f"""
            SELECT
                v.id AS entity_id,
                'Variazione ' || v.tipo || ' del ' || TO_CHAR(v.data_variazione, 'DD/MM/YYYY') AS display_text,
                'Rif: ' || COALESCE(v.nominativo_riferimento, 'N/D') || ' | Partita Origine: ' || po.numero_partita AS detail_text,
                greatest(
                    similarity(v.tipo, %s),
                    similarity(v.nominativo_riferimento, %s)
                ) AS similarity_score,
                CASE
                    WHEN similarity(v.tipo, %s) > similarity(v.nominativo_riferimento, %s) THEN 'tipo'
                    ELSE 'nominativo_riferimento'
                END AS search_field,
                v.tipo,
                v.data_variazione,
                v.nominativo_riferimento AS descrizione
            FROM {self.schema}.variazione v
            LEFT JOIN {self.schema}.partita po ON v.partita_origine_id = po.id
            WHERE greatest(
                    similarity(v.tipo, %s),
                    similarity(v.nominativo_riferimento, %s)
                ) >= %s
            ORDER BY similarity_score DESC
            LIMIT %s;
        """
        try:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(sql, (query, query, query, query, query, query, threshold, limit))
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            self.logger.error(f"Errore ricerca fuzzy variazioni: {e}", exc_info=True)
            return []
    def _search_contratti_fuzzy_internal(self, conn, query: str, threshold: float, limit: int) -> List[Dict]:
        """Ricerca fuzzy interna per i contratti (su tipo, notaio, note)."""
        sql = f"""
            SELECT
                con.id AS entity_id,
                'Contratto ' || con.tipo || ' del ' || TO_CHAR(con.data_contratto, 'DD/MM/YYYY') AS display_text,
                'Notaio: ' || COALESCE(con.notaio, 'N/D') || ' | Partita: ' || p.numero_partita AS detail_text,
                greatest(similarity(con.tipo, %s), similarity(con.notaio, %s), similarity(con.note, %s)) AS similarity_score,
                'contratto' AS search_field, -- Semplificato per ora
                con.tipo,
                con.data_contratto,
                p.numero_partita
            FROM {self.schema}.contratto con
            JOIN {self.schema}.variazione v ON con.variazione_id = v.id
            JOIN {self.schema}.partita p ON v.partita_origine_id = p.id
            WHERE greatest(similarity(con.tipo, %s), similarity(con.notaio, %s), similarity(con.note, %s)) >= %s
            ORDER BY similarity_score DESC
            LIMIT %s;
        """
        try:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(sql, (query, query, query, query, query, query, threshold, limit))
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            self.logger.error(f"Errore ricerca fuzzy contratti: {e}", exc_info=True)
            return []

    # In catasto_db_manager.py, SOSTITUISCI il metodo _search_partite_fuzzy_internal

    def _search_partite_fuzzy_internal(self, conn, query: str, threshold: float, limit: int) -> List[Dict]:
        """Ricerca fuzzy interna per le partite, ora include l'elenco dei possessori."""
        # --- MODIFICA: Aggiunto JOIN con possessori e aggregazione con string_agg ---
        sql = f"""
            SELECT
                p.id AS entity_id,
                'Partita N. ' || p.numero_partita || COALESCE(' (' || p.suffisso_partita || ')', '') AS display_text,
                'Comune: ' || c.nome || ' | Tipo: ' || p.tipo || ' | Stato: ' || p.stato AS detail_text,
                greatest(
                    similarity(CAST(p.numero_partita AS TEXT), %s),
                    similarity(p.tipo, %s),
                    similarity(p.suffisso_partita, %s)
                ) AS similarity_score,
                'partita' AS search_field,
                p.numero_partita,
                p.suffisso_partita,
                p.tipo as tipo_partita,
                c.nome as comune_nome,
                p.stato,
                p.data_impianto,
                -- Aggrega i nomi dei possessori in una singola stringa separata da virgola
                string_agg(pos.nome_completo, ', ') AS possessori_concatenati
            FROM {self.schema}.partita p
            JOIN {self.schema}.comune c ON p.comune_id = c.id
            -- LEFT JOIN per includere anche le partite senza possessori
            LEFT JOIN {self.schema}.partita_possessore pp ON p.id = pp.partita_id
            LEFT JOIN {self.schema}.possessore pos ON pp.possessore_id = pos.id
            WHERE greatest(
                    similarity(CAST(p.numero_partita AS TEXT), %s),
                    similarity(p.tipo, %s),
                    similarity(p.suffisso_partita, %s)
                ) >= %s
            -- Raggruppa per i campi della partita per permettere l'aggregazione dei possessori
            GROUP BY p.id, c.nome
            ORDER BY similarity_score DESC
            LIMIT %s;
        """
        try:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(sql, (query, query, query, query, query, query, threshold, limit))
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            self.logger.error(f"Errore ricerca fuzzy partite: {e}", exc_info=True)
            return []
    def verify_gin_indices(self) -> Dict[str, Any]:
        """
        Verifica la presenza di indici GIN per la ricerca testuale nello schema specificato.
        Restituisce un dizionario con lo stato e il numero di indici trovati.
        """
        self.logger.info(f"Verifica degli indici GIN per lo schema '{self.schema}'...")
        query = """
            SELECT COUNT(*)
            FROM pg_indexes
            WHERE schemaname = %s AND indexdef LIKE '%% USING gin %%';
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (self.schema,))
                    result = cur.fetchone()
                    count = result[0] if result else 0
                    self.logger.info(f"Trovati {count} indici GIN nello schema '{self.schema}'.")
                    return {'status': 'OK', 'gin_indices': count}
        except Exception as e:
            self.logger.error(f"Errore durante la verifica degli indici GIN: {e}", exc_info=True)
            return {'status': 'ERROR', 'message': str(e), 'gin_indices': 0}
    def get_last_mv_refresh_timestamp(self) -> Optional[datetime]:
        """Recupera il timestamp dell'ultimo aggiornamento delle viste materializzate."""
        query = f"SELECT value_timestamp FROM {self.schema}.app_metadata WHERE key = 'last_mv_refresh';"
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                    result = cur.fetchone()
                    return result[0] if result else None
        except psycopg2.errors.UndefinedTable:
            self.logger.warning("Tabella 'app_metadata' non trovata. Creare la tabella per la funzionalità di refresh intelligente.")
            return None # La tabella potrebbe non esistere ancora
        except Exception as e:
            self.logger.error(f"Errore nel recuperare il timestamp di refresh: {e}", exc_info=True)
            return None
    # In catasto_db_manager.py, aggiungi questo nuovo metodo alla classe CatastoDBManager

    def get_dashboard_stats(self) -> Dict[str, int]:
        """Recupera le statistiche di base per la dashboard in un'unica query."""
        stats = {
            "total_comuni": 0,
            "total_partite": 0,
            "total_possessori": 0,
            "total_immobili": 0,
        }
        query = f"""
            SELECT 
                (SELECT COUNT(*) FROM {self.schema}.comune) AS total_comuni,
                (SELECT COUNT(*) FROM {self.schema}.partita) AS total_partite,
                (SELECT COUNT(*) FROM {self.schema}.possessore) AS total_possessori,
                (SELECT COUNT(*) FROM {self.schema}.immobile) AS total_immobili;
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query)
                    result = cur.fetchone()
                    if result:
                        stats.update(dict(result))
            return stats
        except Exception as e:
            self.logger.error(f"Errore durante il recupero delle statistiche per la dashboard: {e}", exc_info=True)
            return stats # Restituisce il dizionario con gli zeri in caso di errore
    def update_last_mv_refresh_timestamp(self):
        """Aggiorna il timestamp dell'ultimo refresh delle viste al tempo attuale (UTC)."""
        # Usiamo un "UPSERT" per inserire la chiave se non esiste, o aggiornarla se esiste.
        query = f"""
            INSERT INTO {self.schema}.app_metadata (key, value_timestamp)
            VALUES ('last_mv_refresh', NOW() at time zone 'utc')
            ON CONFLICT (key) DO UPDATE SET value_timestamp = EXCLUDED.value_timestamp;
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
            self.logger.info("Timestamp di aggiornamento viste materializzate aggiornato con successo.")
        except Exception as e:
            self.logger.error(f"Errore nell'aggiornare il timestamp di refresh: {e}", exc_info=True)
    def cleanup_audit_logs(self, days_to_keep: int) -> int:
        """
        Elimina i record di audit_log più vecchi di un certo numero di giorni.
        Restituisce il numero di record eliminati.
        """
        if not isinstance(days_to_keep, int) or days_to_keep < 0:
            raise DBDataError("Il numero di giorni da conservare deve essere un intero non negativo.")

        query = f"""
            DELETE FROM {self.schema}.audit_log
            WHERE timestamp < NOW() - INTERVAL '{days_to_keep} days';
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                    deleted_rows = cur.rowcount
            self.logger.info(f"Eliminati {deleted_rows} record di audit log più vecchi di {days_to_keep} giorni.")
            return deleted_rows
        except Exception as e:
            self.logger.error(f"Errore durante la pulizia dei log di audit: {e}", exc_info=True)
            raise DBMError(f"Impossibile pulire i log di audit: {e}") from e
    # In catasto_db_manager.py, dentro la classe CatastoDBManager

    def close_user_session(self, session_id: str) -> bool:
        """
        Aggiorna la sessione di un utente nel database, impostando l'ora di fine (logout).

        Args:
            session_id: L'UUID della sessione da chiudere.

        Returns:
            True se la sessione è stata chiusa con successo, False altrimenti.
        """
        if not self.pool:
            logger.error("Impossibile chiudere la sessione utente: pool di connessioni non disponibile.")
            return False

        if not session_id:
            logger.warning("Nessun ID di sessione fornito, impossibile chiudere la sessione nel DB.")
            return False

        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                logger.info(f"Chiusura della sessione utente con ID: {session_id}")
                
                # Query per aggiornare la data_fine della sessione specificata
                # che non è ancora stata chiusa.
                query = """
                    UPDATE catasto.sessioni
                    SET data_fine = CURRENT_TIMESTAMP
                    WHERE id = %s AND data_fine IS NULL;
                """
                cur.execute(query, (session_id,))
                conn.commit()
                
                # psycopg2 fornisce rowcount per sapere se una riga è stata effettivamente aggiornata
                if cur.rowcount > 0:
                    logger.info(f"Sessione {session_id} chiusa con successo nel database.")
                else:
                    logger.warning(f"Tentativo di chiudere la sessione {session_id}, ma non è stata trovata o era già chiusa.")
                
                return True
        
        except (Exception, psycopg2.Error) as e:
            logger.error(f"Errore database durante la chiusura della sessione {session_id}: {e}")
            if conn:
                conn.rollback()
            return False
        
        finally:
            if conn:
                self.release_connection(conn)
    # In catasto_db_manager.py, aggiungi questo metodo alla classe

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
    # In catasto_db_manager.py, aggiungi questi metodi alla classe CatastoDBManager

    def create_clean_environment(self) -> 'QProcessEnvironment':
        """Crea un ambiente pulito per QProcess, ereditando le variabili di sistema."""
        from PyQt5.QtCore import QProcessEnvironment
        env = QProcessEnvironment.systemEnvironment()
        return env

    

    
        
# --- Esempio di utilizzo minimale (invariato) ---
if __name__ == "__main__":
    print("Esecuzione test minimale CatastoDBManager...")
    db = CatastoDBManager(password="Markus74") # Usa la tua password
    if db.connect():
        print("Connessione OK.")
        comuni_carcare = db.get_comuni("Carcare")
        carcare_id = None
        if comuni_carcare:
            carcare_id = comuni_carcare[0]['id']
            print(f"Trovato comune 'Carcare' con ID: {carcare_id}")
            possessori = db.get_possessori_by_comune(carcare_id)
            if possessori: print(f"Trovati {len(possessori)} possessori per Carcare (ID: {carcare_id}):")
            else: print(f"Nessun possessore trovato per Carcare (ID: {carcare_id}) o errore.")
        else: print("Comune 'Carcare' non trovato.")
        db.disconnect()
        print("Disconnessione OK.")
    else:
        print("Connessione fallita.")