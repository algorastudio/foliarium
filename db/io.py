"""
db/io.py — Mixin per import/export CSV, JSON e SQL.
Estratto da catasto_db_manager.py — mixin per CatastoDBManager.
"""

from __future__ import annotations
import logging
from typing import Optional, List, Dict, Any, Tuple, TYPE_CHECKING

import os
from datetime import date, datetime
import psycopg2
from psycopg2.extras import DictCursor
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from catasto_exceptions import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError
from db.base import db_handle_errors

if TYPE_CHECKING:
    from catasto_db_manager import CatastoDBManager


class DBIOMixin:
    """Mixin per import/export CSV, JSON e SQL."""

    @db_handle_errors
    def import_comuni_from_rows(self, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Importa una lista di comuni da una lista di dizionari, gestendo gli errori riga per riga.
        Ogni dict deve avere 'nome', 'provincia', 'regione' (obbligatori).
        Campi opzionali: 'codice_catastale', 'data_istituzione', 'data_soppressione', 'note'.

        TIER 1 Improvement:
        - @db_handle_errors decorator handles all exceptions
        - Uses bulk_insert_with_savepoint() for per-row fault tolerance
        - Returns {"success": [...], "errors": [...]} from helper
        """
        if not rows:
            return {"success": [], "errors": []}

        def _parse_date(val: Any) -> Optional[date]:
            if not val or not str(val).strip():
                return None
            s = str(val).strip()
            for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
                try:
                    return datetime.strptime(s, fmt).date()
                except ValueError:
                    continue
            return None

        records_prepared: List[Dict[str, Any]] = []
        for record in rows:
            nome = str(record.get('nome', '')).strip()
            provincia = str(record.get('provincia', '')).strip()
            regione = str(record.get('regione', '')).strip()

            if not nome or not provincia or not regione:
                raise ValueError("I campi 'nome', 'provincia' e 'regione' sono obbligatori.")

            codice_catastale = str(record.get('codice_catastale', '')).strip() or None
            data_istituzione = _parse_date(record.get('data_istituzione'))
            data_soppressione = _parse_date(record.get('data_soppressione'))
            note = str(record.get('note', '')).strip() or None

            records_prepared.append({
                'nome': nome,
                'provincia': provincia,
                'regione': regione,
                'codice_catastale': codice_catastale,
                'data_istituzione': data_istituzione,
                'data_soppressione': data_soppressione,
                'note': note,
            })

        result = self.bulk_insert_with_savepoint("comune", records_prepared)

        self.logger.info(
            f"Import comuni completato: {len(result['success'])} successi, "
            f"{len(result['errors'])} errori"
        )
        return result

    @db_handle_errors
    def import_localita_from_rows(self, comune_id: int, rows: List[Dict[str, Any]]) -> Dict[str, list]:
        """Importa una lista di località da una lista di dizionari per un comune dato.

        TIER 1: @db_handle_errors decorator handles all exceptions.
        """
        if not rows:
            return {"success": [], "errors": []}

        records_prepared: List[Dict[str, Any]] = []
        for record in rows:
            nome = str(record.get('nome', '')).strip()
            if not nome:
                raise ValueError("Il campo 'nome' è obbligatorio")

            # Da v1.7.0 il civico NON va nel nome località (campo separato su immobile).
            # Se il CSV contiene 'civico', lo ignoriamo silenziosamente.

            tipologia_stradale = (
                str(record.get('tipologia_stradale') or record.get('tipo') or '').strip()
            )
            if not tipologia_stradale:
                raise ValueError(
                    "Il campo 'tipologia_stradale' è obbligatorio (es. Via, Piazza, Borgata)."
                )

            records_prepared.append({
                'comune_id': comune_id,
                'nome': nome,
                'tipologia_stradale': tipologia_stradale,
            })

        result = self.bulk_insert_with_savepoint("localita", records_prepared)
        self.logger.info(
            f"Import località completato: {len(result['success'])} successi, "
            f"{len(result['errors'])} errori"
        )
        return result

    def get_comuni_export_csv(self) -> List[Dict[str, Any]]:
        """
        Restituisce tutti i comuni con i campi compatibili con il template di import.
        Colonne: nome;provincia;regione;codice_catastale;data_istituzione;data_soppressione;note
        """
        query = f"""
            SELECT
                nome,
                provincia,
                regione,
                COALESCE(codice_catastale, '') AS codice_catastale,
                TO_CHAR(data_istituzione, 'DD/MM/YYYY') AS data_istituzione,
                TO_CHAR(data_soppressione, 'DD/MM/YYYY') AS data_soppressione,
                COALESCE(note, '') AS note
            FROM {self.schema}.comune
            ORDER BY nome;
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query)
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            self.logger.error(f"Errore export CSV comuni: {e}", exc_info=True)
            raise DBMError(f"Impossibile recuperare i comuni per l'export: {e}") from e

    def get_localita_export_csv(self, comune_id: int) -> List[Dict[str, Any]]:
        """
        Restituisce le località di un comune con i campi compatibili con il template di import.
        Colonne: nome;tipologia_stradale
        Da v1.7.0 nome contiene solo la radice (es. 'Repubblica'); civico è su immobile.
        """
        query = f"""
            SELECT
                l.nome,
                l.tipologia_stradale
            FROM {self.schema}.localita l
            WHERE l.comune_id = %s
            ORDER BY l.tipologia_stradale, l.nome;
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, (comune_id,))
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            self.logger.error(f"Errore export CSV località per comune {comune_id}: {e}", exc_info=True)
            raise DBMError(f"Impossibile recuperare le località per l'export: {e}") from e

    def get_possessori_export_csv(self, comune_id: int) -> List[Dict[str, Any]]:
        """
        Restituisce i possessori di un comune con i campi compatibili con il template di import.
        Colonne: cognome_nome;nome_completo;paternita
        """
        query = f"""
            SELECT
                cognome_nome,
                nome_completo,
                COALESCE(paternita, '') AS paternita
            FROM {self.schema}.possessore
            WHERE comune_id = %s
            ORDER BY cognome_nome;
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, (comune_id,))
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            self.logger.error(f"Errore export CSV possessori per comune {comune_id}: {e}", exc_info=True)
            raise DBMError(f"Impossibile recuperare i possessori per l'export: {e}") from e

    def get_partite_export_csv(self, comune_id: int) -> List[Dict[str, Any]]:
        """
        Restituisce le partite di un comune con i campi compatibili con il template di import.
        Colonne: numero_partita;data_impianto;stato;tipo
        """
        query = f"""
            SELECT
                numero_partita,
                TO_CHAR(data_impianto, 'DD/MM/YYYY') AS data_impianto,
                stato,
                tipo
            FROM {self.schema}.partita
            WHERE comune_id = %s
            ORDER BY numero_partita;
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, (comune_id,))
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            self.logger.error(f"Errore export CSV partite per comune {comune_id}: {e}", exc_info=True)
            raise DBMError(f"Impossibile recuperare le partite per l'export: {e}") from e

    def create_clean_environment(self) -> Any:
        """Crea un ambiente pulito per QProcess, ereditando le variabili di sistema.

        Lazy-import di QProcessEnvironment così il package db/ resta utilizzabile
        in ambienti headless dove PyQt6 potrebbe non essere disponibile.
        """
        from PyQt6.QtCore import QProcessEnvironment
        return QProcessEnvironment.systemEnvironment()

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

