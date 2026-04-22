"""
db/documenti.py — Mixin per documenti storici e periodi storici.
Estratto da catasto_db_manager.py — mixin per CatastoDBManager.
"""

from __future__ import annotations
import logging
from typing import Optional, List, Dict, Any, TYPE_CHECKING

from datetime import date, datetime
import psycopg2
from psycopg2.extras import DictCursor

from catasto_exceptions import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError
from db.base import db_handle_errors

if TYPE_CHECKING:
    from catasto_db_manager import CatastoDBManager


class DBDocumentiMixin:
    """Mixin per documenti storici e periodi storici."""

    @db_handle_errors
    def aggiungi_documento_storico(self, titolo: str, tipo_documento: str, percorso_file: str,
                              descrizione: Optional[str] = None, anno: Optional[int] = None,
                              periodo_id: Optional[int] = None,
                              metadati_json: Optional[str] = None) -> int:
        """Inserisce un nuovo record nella tabella documento_storico in modo sicuro.

        TIER 1: @db_handle_errors centralizes exception handling.
        """
        query = f"""
            INSERT INTO {self.schema}.documento_storico
                (titolo, tipo_documento, percorso_file, descrizione, anno, periodo_id, metadati)
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
            RETURNING id;
        """
        params = (titolo, tipo_documento, percorso_file, descrizione, anno, periodo_id, metadati_json)

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query, params)
                result = cur.fetchone()
                if not result:
                    raise DBMError("Creazione del documento fallita, nessun ID restituito.")
                return result['id']

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

    @db_handle_errors
    def get_documenti_per_partita(self, partita_id: int) -> List[Dict[str, Any]]:
        """Recupera l'elenco dei documenti associati a una partita in modo sicuro.

        TIER 1: @db_handle_errors centralizes exception handling.
        """
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
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(query, (partita_id,))
                return [dict(row) for row in cur.fetchall()]

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

    @db_handle_errors
    def search_historical_documents(self, title: Optional[str] = None, doc_type: Optional[str] = None,
                                    period_id: Optional[int] = None, year_start: Optional[int] = None,
                                    year_end: Optional[int] = None, partita_id: Optional[int] = None) -> List[Dict]:
        """Ricerca documenti storici con query diretta (la SP aveva p.comune_nome inesistente).

        TIER 1: @db_handle_errors centralizes exception handling.
        """
        conditions = []
        params: list = []

        if title:
            conditions.append("d.titolo ILIKE %s")
            params.append(f"%{title}%")
        if doc_type:
            conditions.append("d.tipo_documento = %s")
            params.append(doc_type)
        if period_id is not None:
            conditions.append("d.periodo_id = %s")
            params.append(period_id)
        if year_start is not None:
            conditions.append("d.anno >= %s")
            params.append(year_start)
        if year_end is not None:
            conditions.append("d.anno <= %s")
            params.append(year_end)
        if partita_id is not None:
            conditions.append("dp.partita_id = %s")
            params.append(partita_id)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        query = f"""
            SELECT
                d.id AS documento_id, d.titolo, d.descrizione, d.anno, ps.nome AS periodo_nome,
                d.tipo_documento,
                string_agg(DISTINCT c.nome || ' - ' || p.numero_partita::TEXT, ', ') AS partite_correlate
            FROM documento_storico d
            JOIN periodo_storico ps ON d.periodo_id = ps.id
            LEFT JOIN documento_partita dp ON d.id = dp.documento_id
            LEFT JOIN partita p ON dp.partita_id = p.id
            LEFT JOIN comune c ON p.comune_id = c.id
            {where}
            GROUP BY d.id, d.titolo, d.descrizione, d.anno, ps.nome, d.tipo_documento
            ORDER BY d.anno DESC, d.titolo
        """
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query, params)
                return [dict(r) for r in cur.fetchall()]

    def link_document_to_partita(self, document_id: int, partita_id: int,
                                 relevance: str = 'correlata', notes: Optional[str] = None) -> bool:
        """
        Collega un documento storico a una partita (INSERT ... ON CONFLICT DO UPDATE).
        Se il link esiste già, aggiorna rilevanza e note.
        """
        if relevance not in ['primaria', 'secondaria', 'correlata']:
            self.logger.error(f"Rilevanza non valida: '{relevance}'")
            return False
        query = f"""
            INSERT INTO {self.schema}.documento_partita (documento_id, partita_id, rilevanza, note)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (documento_id, partita_id) DO UPDATE
                SET rilevanza = EXCLUDED.rilevanza, note = EXCLUDED.note
        """
        try:
            # Il commit è automatico all'uscita del context manager
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (document_id, partita_id, relevance, notes))
            self.logger.info(f"Link creato/aggiornato Doc {document_id} → Partita {partita_id}.")
            return True
        except psycopg2.Error as db_err: self.logger.error(f"Errore DB link doc-partita: {db_err}"); return False
        except Exception as e: self.logger.error(f"Errore Python link doc-partita: {e}"); return False

    @db_handle_errors
    def get_historical_periods(self) -> List[Dict[str, Any]]:
        """Recupera i periodi storici definiti dalla tabella 'periodo_storico' in modo sicuro.

        TIER 1: @db_handle_errors centralizes exception handling.
        """
        query = f"SELECT id, nome, anno_inizio, anno_fine, descrizione FROM {self.schema}.periodo_storico ORDER BY anno_inizio;"
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query)
                return [dict(row) for row in cur.fetchall()]

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

    @db_handle_errors
    def get_periodo_storico_details(self, periodo_id: int) -> Optional[Dict[str, Any]]:
        """Recupera i dettagli di un singolo periodo storico in modo sicuro.

        TIER 1: @db_handle_errors centralizes exception handling.
        """
        if not isinstance(periodo_id, int) or periodo_id <= 0:
            raise DBDataError(f"ID periodo storico non valido: {periodo_id}")

        query = f"SELECT * FROM {self.schema}.periodo_storico WHERE id = %s;"
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query, (periodo_id,))
                result = cur.fetchone()
                if result:
                    return dict(result)
                else:
                    raise DBNotFoundError(f"Periodo storico con ID {periodo_id} non trovato.")

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

    def get_cadastral_stats_by_period(self, comune_id: Optional[int] = None, year_start: int = 1900, # Usa comune_id
                                       year_end: Optional[int] = None) -> List[Dict]:
        """Chiama la funzione SQL statistiche_catastali_periodo (MODIFICATA per comune_id)."""
        self.logger.warning("La funzione SQL 'statistiche_catastali_periodo' potrebbe non essere aggiornata per comune_id.")
        try:
            if year_end is None: year_end = datetime.now().year
            query = "SELECT * FROM statistiche_catastali_periodo(%s, %s, %s)"
            params = (comune_id, year_start, year_end)
            # Usa il context manager per una connessione sicura dal pool
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, params)
                    return [dict(row) for row in cur.fetchall()]
        except psycopg2.errors.UndefinedFunction: self.logger.warning("Funzione 'statistiche_catastali_periodo' non trovata nel DB."); return []
        except psycopg2.Error as db_err: self.logger.error(f"Errore DB get_cadastral_stats_by_period: {db_err}"); return []
        except Exception as e: self.logger.error(f"Errore Python get_cadastral_stats_by_period: {e}"); return []
        return []

