"""
db/io.py — Mixin per import/export CSV, JSON e SQL.
Estratto da catasto_db_manager.py — mixin per CatastoDBManager.
"""

from __future__ import annotations
import logging
from typing import Optional, List, Dict, Any, TYPE_CHECKING

import os
from datetime import date, datetime
import psycopg2
from psycopg2.extras import DictCursor

from catasto_exceptions import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError

if TYPE_CHECKING:
    from catasto_db_manager import CatastoDBManager


class DBIOMixin:
    """Mixin per import/export CSV, JSON e SQL."""

    def import_comuni_from_rows(self, rows: List[Dict[str, Any]]) -> Dict[str, list]:
        """
        Importa una lista di comuni da una lista di dizionari, gestendo gli errori riga per riga.
        Ogni dict deve avere 'nome', 'provincia', 'regione' (obbligatori).
        Campi opzionali: 'codice_catastale', 'data_istituzione', 'data_soppressione', 'note'.
        Restituisce {"success": [...], "errors": [(line_num, row, msg), ...]}.
        """
        if not rows:
            return {"success": [], "errors": []}

        success_rows: list = []
        error_rows: list = []

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

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    for i, record in enumerate(rows):
                        line_num = i + 2
                        cur.execute("SAVEPOINT record_savepoint")
                        try:
                            nome = str(record.get('nome', '')).strip()
                            provincia = str(record.get('provincia', '')).strip()
                            regione = str(record.get('regione', '')).strip()
                            if not nome or not provincia or not regione:
                                raise ValueError("I campi 'nome', 'provincia' e 'regione' sono obbligatori.")

                            codice_catastale = str(record.get('codice_catastale', '')).strip() or None
                            data_istituzione = _parse_date(record.get('data_istituzione'))
                            data_soppressione = _parse_date(record.get('data_soppressione'))
                            note = str(record.get('note', '')).strip() or None

                            query = f"""
                                INSERT INTO {self.schema}.comune
                                    (nome, provincia, regione, codice_catastale,
                                     data_istituzione, data_soppressione, note)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                RETURNING id;
                            """
                            cur.execute(query, (nome, provincia, regione, codice_catastale,
                                                data_istituzione, data_soppressione, note))
                            result = cur.fetchone()
                            if not result:
                                raise DBMError("Inserimento fallito, nessun ID restituito.")
                            new_id = result[0]
                            cur.execute("RELEASE SAVEPOINT record_savepoint")
                            success_rows.append({'id': new_id, 'nome': nome, 'provincia': provincia, 'regione': regione})

                        except psycopg2.errors.UniqueViolation:
                            cur.execute("ROLLBACK TO SAVEPOINT record_savepoint")
                            error_rows.append((line_num, record, f"Il comune '{record.get('nome', '')}' esiste già."))
                        except (ValueError, psycopg2.Error, DBMError) as error:
                            cur.execute("ROLLBACK TO SAVEPOINT record_savepoint")
                            error_rows.append((line_num, record, str(error)))

            self.logger.info(f"Import comuni completato. Successi: {len(success_rows)}, Errori: {len(error_rows)}")
            return {"success": success_rows, "errors": error_rows}

        except Exception as e:
            self.logger.error(f"Errore critico durante import comuni: {e}", exc_info=True)
            raise DBMError(f"Errore critico di sistema durante l'importazione: {e}") from e

    def import_localita_from_rows(self, comune_id: int, rows: List[Dict[str, Any]]) -> Dict[str, list]:
        """
        Importa una lista di località da una lista di dizionari per un comune dato.
        Ogni dict deve avere 'nome' (obbligatorio), 'tipo' (stringa, es. 'Via'), 'civico' (opzionale).
        Restituisce {"success": [...], "errors": [(line_num, row, msg), ...]}.
        """
        if not rows:
            return {"success": [], "errors": []}

        tipi = self.get_tipi_localita()
        tipo_map = {t['nome'].lower(): t['id'] for t in tipi}
        fallback_tipo_id = tipo_map.get('altro')

        success_rows: list = []
        error_rows: list = []

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    for i, record in enumerate(rows):
                        line_num = i + 2
                        cur.execute("SAVEPOINT record_savepoint")
                        try:
                            nome = str(record.get('nome', '')).strip()
                            if not nome:
                                raise ValueError("Il campo 'nome' è obbligatorio.")

                            # Civico è ormai incorporato nel nome (v1.6.1)
                            # Supporto per CSV con civico separato: concatenare al nome
                            civico_raw = str(record.get('civico', '')).strip()
                            if civico_raw:
                                nome = f"{nome} {civico_raw}".strip()

                            tipologia_stradale = str(record.get('tipo', '')).strip() or None

                            query_insert = f"""
                                INSERT INTO {self.schema}.localita (comune_id, nome, tipologia_stradale)
                                VALUES (%s, %s, %s)
                                ON CONFLICT (comune_id, nome) DO NOTHING
                                RETURNING id;
                            """
                            cur.execute(query_insert, (comune_id, nome, tipologia_stradale))
                            insert_result = cur.fetchone()

                            if insert_result:
                                new_id = insert_result[0]
                            else:
                                cur.execute(
                                    f"SELECT id FROM {self.schema}.localita WHERE comune_id=%s AND nome=%s;",
                                    (comune_id, nome)
                                )
                                existing = cur.fetchone()
                                if existing:
                                    raise ValueError(f"La località '{nome}' esiste già per questo comune.")
                                else:
                                    raise DBMError(f"Impossibile inserire o trovare la località '{nome}'.")

                            cur.execute("RELEASE SAVEPOINT record_savepoint")
                            success_rows.append({'id': new_id, 'nome': nome})

                        except (ValueError, psycopg2.Error, DBMError) as error:
                            cur.execute("ROLLBACK TO SAVEPOINT record_savepoint")
                            error_rows.append((line_num, record, str(error)))

            self.logger.info(f"Import località completato. Successi: {len(success_rows)}, Errori: {len(error_rows)}")
            return {"success": success_rows, "errors": error_rows}

        except Exception as e:
            self.logger.error(f"Errore critico durante import località: {e}", exc_info=True)
            raise DBMError(f"Errore critico di sistema durante l'importazione: {e}") from e

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
        Colonne: nome;tipo;civico
        """
        query = f"""
            SELECT
                l.nome,
                COALESCE(tl.nome, '') AS tipo,
                COALESCE(CAST(l.civico AS TEXT), '') AS civico
            FROM {self.schema}.localita l
            LEFT JOIN {self.schema}.tipo_localita tl ON l.tipo_id = tl.id
            WHERE l.comune_id = %s
            ORDER BY l.nome;
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

    def create_clean_environment(self) -> 'QProcessEnvironment':
        """Crea un ambiente pulito per QProcess, ereditando le variabili di sistema."""
        from PyQt6.QtCore import QProcessEnvironment
        env = QProcessEnvironment.systemEnvironment()
        return env

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

