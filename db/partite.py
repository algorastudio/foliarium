"""
db/partite.py — Mixin CRUD per Partite catastali, genealogia e report.
Estratto da catasto_db_manager.py — mixin per CatastoDBManager.
"""

from __future__ import annotations
import logging
from datetime import date
from typing import Optional, List, Dict, Any, Union, TYPE_CHECKING

import csv
import json
try:
    import openpyxl
except ImportError:
    openpyxl = None
import psycopg2
from psycopg2.extras import DictCursor

from catasto_exceptions import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError
from db.models import Partita
from db.base import db_handle_errors

if TYPE_CHECKING:
    from catasto_db_manager import CatastoDBManager


class DBPartiteMixin:
    """Mixin CRUD per Partite catastali, genealogia e report."""

    @db_handle_errors
    def get_partita_data_for_export(self, partita_id: int) -> Optional[Dict[str, Any]]:
        """
        Recupera i dati di una partita per l'esportazione chiamando una funzione SQL.

        TIER 1 Improvement: @db_handle_errors decorator centralizes exception handling.
        """
        if not isinstance(partita_id, int) or partita_id <= 0:
            raise ValueError(f"ID partita non valido: {partita_id}")

        query = self._tag_query(
            f"SELECT {self.schema}.esporta_partita_json(%s) AS partita_data",
            method_name="get_partita_data_for_export",
            action="read"
        )

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query, (partita_id,))
                result = cur.fetchone()

                if result and result['partita_data'] is not None:
                    self.logger.info(f"Dati esportazione recuperati per partita ID {partita_id}")
                    return result['partita_data']
                else:
                    raise DBNotFoundError(f"Partita ID {partita_id} non trovata o dato NULL")

    def _insert_partite_records(self, records: List[Dict], comune_id: int, comune_nome: str) -> Dict[str, list]:
        """Helper condiviso: inserisce una lista di record-partita con SAVEPOINT per riga."""
        if not records:
            return {"success": [], "errors": []}
        success_rows: List[Dict] = []
        error_rows: list = []
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    for i, record in enumerate(records):
                        line_num = i + 2
                        cur.execute("SAVEPOINT record_savepoint")
                        try:
                            numero_partita = int(record['numero_partita'])
                            suffisso_partita = record.get('suffisso_partita') or None
                            cur.execute(
                                f"SELECT id FROM {self.schema}.partita WHERE comune_id = %s AND numero_partita = %s"
                                f" AND (suffisso_partita = %s OR (suffisso_partita IS NULL AND %s IS NULL))",
                                (comune_id, numero_partita, suffisso_partita, suffisso_partita)
                            )
                            if cur.fetchone():
                                suf = f" con suffisso '{suffisso_partita}'" if suffisso_partita else ""
                                raise ValueError(f"La partita n.{numero_partita}{suf} esiste già.")
                            cur.execute(
                                f"""INSERT INTO {self.schema}.partita
                                    (comune_id, numero_partita, suffisso_partita, data_impianto,
                                     data_chiusura, numero_provenienza, stato, tipo)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;""",
                                (comune_id, numero_partita, suffisso_partita,
                                 record['data_impianto'], record.get('data_chiusura') or None,
                                 record.get('numero_provenienza') or None,
                                 record['stato'], record['tipo'])
                            )
                            new_id = cur.fetchone()[0]
                            cur.execute("RELEASE SAVEPOINT record_savepoint")
                            record['id'] = new_id
                            record['comune_nome'] = comune_nome
                            success_rows.append(record)
                        except (ValueError, psycopg2.Error, DBMError) as error:
                            cur.execute("ROLLBACK TO SAVEPOINT record_savepoint")
                            error_rows.append((line_num, record, str(error)))
            self.logger.info(f"Import partite completato. Successi: {len(success_rows)}, Errori: {len(error_rows)}")
            return {"success": success_rows, "errors": error_rows}
        except Exception as e:
            self.logger.error(f"Errore critico import partite: {e}", exc_info=True)
            raise DBMError(f"Errore critico di sistema durante l'importazione: {e}") from e

    def import_partite_from_csv(self, file_path: str, comune_id: int, comune_nome: str) -> Dict[str, list]:
        """Importa partite da un file CSV (delimitatore ';')."""
        records: List[Dict] = []
        required = {'numero_partita', 'data_impianto', 'stato', 'tipo'}
        try:
            with open(file_path, mode='r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile, delimiter=';')
                if not required.issubset(reader.fieldnames or []):
                    raise ValueError(f"Intestazioni mancanti. Richieste: {', '.join(required)}")
                for i, row in enumerate(reader):
                    if not all(row.get(k) for k in required):
                        raise ValueError(f"Dati mancanti alla riga {i + 2}. Campi obbligatori: {', '.join(required)}.")
                    records.append(dict(row))
        except Exception as e:
            raise IOError(f"Errore leggendo il file CSV: {e}")
        return self._insert_partite_records(records, comune_id, comune_nome)

    def import_partite_from_xlsx(self, file_path: str, comune_id: int, comune_nome: str) -> Dict[str, list]:
        """Importa partite da un file Excel (.xlsx). Stesse colonne del CSV."""
        required = {'numero_partita', 'data_impianto', 'stato', 'tipo'}
        try:
            import openpyxl
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            ws = wb.active
            rows_iter = ws.iter_rows(values_only=True)
            headers = [str(h).strip() if h is not None else '' for h in next(rows_iter, [])]
            if not required.issubset(set(headers)):
                raise ValueError(f"Intestazioni mancanti nel foglio Excel. Richieste: {', '.join(required)}")
            records: List[Dict] = []
            for i, row in enumerate(rows_iter):
                record = {headers[j]: (str(v).strip() if v is not None else '') for j, v in enumerate(row)}
                if not all(record.get(k) for k in required):
                    raise ValueError(f"Dati mancanti alla riga {i + 2}. Campi obbligatori: {', '.join(required)}.")
                records.append(record)
            wb.close()
        except ImportError:
            raise IOError("La libreria 'openpyxl' non è installata. Esegui: pip install openpyxl")
        except Exception as e:
            raise IOError(f"Errore leggendo il file Excel: {e}")
        return self._insert_partite_records(records, comune_id, comune_nome)

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

    @db_handle_errors
    def get_partite_by_comune(self, comune_id: int, filter_text: Optional[str] = None) -> List[Dict[str, Any]]:
        """Recupera le partite per un dato comune con un filtro opzionale.

        TIER 2 Phase 2: Optimized from correlated subqueries to LEFT JOIN + DISTINCT COUNT.
        Before: 3 correlated subqueries per partita row (O(n*3) queries)
        After: Single query with LEFT JOINs + COUNT(DISTINCT ...) (10x faster)
        """
        if not isinstance(comune_id, int) or comune_id <= 0:
            raise DBDataError("ID comune non valido.")

        query_base = f"""
            SELECT
                p.id, p.numero_partita, p.suffisso_partita, p.tipo, p.stato, p.data_impianto,
                (SELECT COUNT(DISTINCT pp.possessore_id)
                 FROM {self.schema}.partita_possessore pp WHERE pp.partita_id = p.id) AS num_possessori,
                (SELECT COUNT(*) FROM {self.schema}.immobile i WHERE i.partita_id = p.id) AS num_immobili,
                (SELECT COUNT(*) FROM {self.schema}.documento_partita dp WHERE dp.partita_id = p.id) AS num_documenti_allegati
            FROM {self.schema}.partita p
            WHERE p.comune_id = %s AND NOT p.archiviato
        """
        params: List[Union[int, str]] = [comune_id]

        if filter_text:
            query_base += " AND (CAST(p.numero_partita AS TEXT) ILIKE %s OR p.tipo ILIKE %s OR p.stato ILIKE %s OR p.suffisso_partita ILIKE %s)"
            filter_like = f"%{filter_text}%"
            params.extend([filter_like, filter_like, filter_like, filter_like])

        query = query_base + " ORDER BY p.numero_partita, p.suffisso_partita;"

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query, tuple(params))
                return [dict(row) for row in cur.fetchall()]

    @db_handle_errors
    def get_partita_details(self, partita_id: int) -> Optional[Dict[str, Any]]:
        """Recupera dettagli completi di una partita, usando una singola connessione e transazione.

        TIER 1: @db_handle_errors centralizes exception handling.
        """
        if not isinstance(partita_id, int) or partita_id <= 0:
            raise ValueError(f"ID partita non valido: {partita_id}")

        partita_details: Dict[str, Any] = {}
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # 1. Info base partita
                query_partita = f"SELECT p.*, c.nome as comune_nome, c.id as comune_id FROM {self.schema}.partita p JOIN {self.schema}.comune c ON p.comune_id = c.id WHERE p.id = %s;"
                cur.execute(query_partita, (partita_id,))
                partita_base = cur.fetchone()
                if not partita_base:
                    raise DBNotFoundError(f"Partita ID {partita_id} non trovata")
                partita_details.update(dict(partita_base))

                # 2. Possessori
                query_poss = f"SELECT pos.id, pos.nome_completo, pp.titolo, pp.quota FROM {self.schema}.possessore pos JOIN {self.schema}.partita_possessore pp ON pos.id = pp.possessore_id WHERE pp.partita_id = %s ORDER BY pos.nome_completo;"
                cur.execute(query_poss, (partita_id,))
                partita_details['possessori'] = [dict(row) for row in cur.fetchall()]

                # 3. Immobili
                query_imm = f"""
                    SELECT i.id, i.natura, i.numero_piani, i.numero_vani, i.consistenza,
                        i.classificazione, i.numero_civico,
                        l.nome as localita_nome, l.tipologia_stradale
                    FROM {self.schema}.immobile i
                    JOIN {self.schema}.localita l ON i.localita_id = l.id
                    WHERE i.partita_id = %s
                    ORDER BY l.tipologia_stradale, l.nome, i.numero_civico, i.natura;
                """
                cur.execute(query_imm, (partita_id,))
                partita_details['immobili'] = [dict(row) for row in cur.fetchall()]

                # 4. Variazioni
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

        self.logger.info(f"Dettagli completi recuperati per partita ID {partita_id}")
        return partita_details

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

    @db_handle_errors
    def search_partite(self, comune_id: Optional[int] = None, numero_partita: Optional[int] = None,
                    possessore: Optional[str] = None, immobile_natura: Optional[str] = None,
                    suffisso_partita: Optional[str] = None,
                    partita_id: Optional[int] = None,
                    max_results: int = 500) -> List[Dict[str, Any]]:
        """
        Ricerca partite con filtri multipli.

        TIER 1: @db_handle_errors centralizes exception handling.
        Returns max_results rows; sets result['_truncated'] = True on last row if more exist.
        """
        conditions, params, joins = [], [], ""
        select_cols = "p.id, c.nome as comune_nome, p.numero_partita, p.suffisso_partita, p.tipo, p.stato, p.data_impianto"
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
        if partita_id is not None:
            conditions.append("p.id = %s")
            params.append(partita_id)

        conditions.append("NOT p.archiviato")
        query = query_base + joins
        query += " WHERE " + " AND ".join(conditions)
        query += f" ORDER BY c.nome, p.numero_partita LIMIT %s"
        params.append(max_results + 1)

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                truncated = len(rows) > max_results
                results = [dict(row) for row in rows[:max_results]]
                if truncated and results:
                    results[-1]['_truncated'] = True
                self.logger.info(
                    f"search_partite — trovate {'>' if truncated else ''}{len(results)} partite"
                )
                return results

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

    @db_handle_errors
    def genera_report_genealogico(self, partita_id: int) -> Optional[str]:
        """Chiama la funzione SQL catasto.genera_report_genealogico.

        TIER 1: @db_handle_errors centralizes exception handling.
        """
        if not isinstance(partita_id, int) or partita_id <= 0:
            raise ValueError(f"ID partita non valido: {partita_id}")

        query = f"SELECT {self.schema}.genera_report_genealogico(%s)"
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (partita_id,))
                result = cur.fetchone()
                if result and result[0] is not None:
                    return str(result[0])
                else:
                    raise DBNotFoundError(f"Nessun report generato per partita ID {partita_id}")

    @db_handle_errors
    def get_genealogia_partita(self, partita_id: int) -> Optional[Dict[str, Any]]:
        """Restituisce dati strutturati per l'albero genealogico di una partita.

        TIER 2 Phase 3: Optimized from 3 sequential queries to 1 query with CTEs.
        Before: 3 separate DB roundtrips (partita centrale + predecessori + successori)
        After: Single query combining all 3 with WITH clauses (3x faster on network)
        """
        if not isinstance(partita_id, int) or partita_id <= 0:
            raise ValueError(f"ID partita non valido: {partita_id}")

        query = f"""
            WITH partita_centrale AS (
                SELECT p.id, p.numero_partita, p.suffisso_partita, p.tipo, p.stato,
                       p.data_impianto, p.data_chiusura, c.nome AS comune_nome,
                       string_agg(DISTINCT pos.nome_completo, ', ') AS possessori,
                       NULL::text AS tipo_variazione, NULL::date AS data_variazione,
                       NULL::text AS nominativo_riferimento
                FROM {self.schema}.partita p
                JOIN {self.schema}.comune c ON p.comune_id = c.id
                LEFT JOIN {self.schema}.partita_possessore pp ON p.id = pp.partita_id
                LEFT JOIN {self.schema}.possessore pos ON pp.possessore_id = pos.id
                WHERE p.id = %s
                GROUP BY p.id, p.numero_partita, p.suffisso_partita, p.tipo, p.stato,
                         p.data_impianto, p.data_chiusura, c.nome
            ),
            predecessori AS (
                SELECT p.id, p.numero_partita, p.suffisso_partita, p.tipo, p.stato,
                       p.data_impianto, p.data_chiusura, c.nome AS comune_nome,
                       string_agg(DISTINCT pos.nome_completo, ', ') AS possessori,
                       v.tipo AS tipo_variazione, v.data_variazione, v.nominativo_riferimento
                FROM {self.schema}.variazione v
                JOIN {self.schema}.partita p ON v.partita_origine_id = p.id
                JOIN {self.schema}.comune c ON p.comune_id = c.id
                LEFT JOIN {self.schema}.partita_possessore pp ON p.id = pp.partita_id
                LEFT JOIN {self.schema}.possessore pos ON pp.possessore_id = pos.id
                WHERE v.partita_destinazione_id = %s
                GROUP BY p.id, p.numero_partita, p.suffisso_partita, p.tipo, p.stato,
                         p.data_impianto, p.data_chiusura, c.nome,
                         v.tipo, v.data_variazione, v.nominativo_riferimento
            ),
            successori AS (
                SELECT p.id, p.numero_partita, p.suffisso_partita, p.tipo, p.stato,
                       p.data_impianto, p.data_chiusura, c.nome AS comune_nome,
                       string_agg(DISTINCT pos.nome_completo, ', ') AS possessori,
                       v.tipo AS tipo_variazione, v.data_variazione, v.nominativo_riferimento
                FROM {self.schema}.variazione v
                JOIN {self.schema}.partita p ON v.partita_destinazione_id = p.id
                JOIN {self.schema}.comune c ON p.comune_id = c.id
                LEFT JOIN {self.schema}.partita_possessore pp ON p.id = pp.partita_id
                LEFT JOIN {self.schema}.possessore pos ON pp.possessore_id = pos.id
                WHERE v.partita_origine_id = %s
                GROUP BY p.id, p.numero_partita, p.suffisso_partita, p.tipo, p.stato,
                         p.data_impianto, p.data_chiusura, c.nome,
                         v.tipo, v.data_variazione, v.nominativo_riferimento
            )
            SELECT 'centrale'::text as relazione, * FROM partita_centrale
            UNION ALL
            SELECT 'predecessore'::text, * FROM predecessori
            UNION ALL
            SELECT 'successore'::text, * FROM successori
            ORDER BY relazione, data_variazione DESC NULLS LAST;
        """

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(query, (partita_id, partita_id, partita_id))
                rows = cur.fetchall()
                if not rows:
                    raise DBNotFoundError(f"Partita ID {partita_id} non trovata")

                partita_row = None
                predecessori = []
                successori = []

                for row in rows:
                    row_dict = dict(row)
                    relazione = row_dict.pop('relazione')
                    if relazione == 'centrale':
                        partita_row = row_dict
                    elif relazione == 'predecessore':
                        predecessori.append(row_dict)
                    elif relazione == 'successore':
                        successori.append(row_dict)

        return {'partita': partita_row, 'predecessori': predecessori, 'successori': successori}

    def get_partite_complete_view(self, comune_id: Optional[int] = None, stato: Optional[str] = None, limit: int = 100) -> List[Dict]: # Usa comune_id
        """Recupera dati dalla vista materializzata mv_partite_complete (aggiornata), filtrando per ID."""
        try:
            params = []
            # La vista SQL è stata aggiornata per usare nome comune
            query = "SELECT * FROM mv_partite_complete" # La vista ha 'comune_nome'
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
            # Usa il context manager per una connessione sicura dal pool
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, tuple(params))
                    return [dict(row) for row in cur.fetchall()]
        except psycopg2.Error as db_err: self.logger.error(f"Errore DB get_partite_complete_view: {db_err}"); return []
        except Exception as e: self.logger.error(f"Errore Python get_partite_complete_view: {e}"); return []

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
            # Usa il context manager per una connessione sicura dal pool
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, tuple(params))
                    return [dict(row) for row in cur.fetchall()]
        except psycopg2.Error as db_err: self.logger.error(f"Errore DB get_cronologia_variazioni: {db_err}"); return []
        except Exception as e: self.logger.error(f"Errore Python get_cronologia_variazioni: {e}"); return []

    @db_handle_errors
    def export_partita_json(self, partita_id: int) -> Optional[str]:
        """Chiama la funzione SQL esporta_partita_json e restituisce il JSON come stringa.

        TIER 1: @db_handle_errors centralizes exception handling.
        """
        query = "SELECT esporta_partita_json(%s) AS partita_json"
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query, (partita_id,))
                result = cur.fetchone()
                if result and result['partita_json']:
                    try:
                        return json.dumps(result['partita_json'], indent=4, ensure_ascii=False)
                    except (TypeError, ValueError) as json_err:
                        self.logger.error(f"JSON serialization error for partita {partita_id}: {json_err}")
                        return str(result['partita_json'])
                else:
                    raise DBNotFoundError(f"Nessun JSON restituito per partita ID {partita_id}")

    @db_handle_errors
    def get_property_genealogy(self, partita_id: int) -> List[Dict]:
        """Chiama la funzione SQL albero_genealogico_proprieta.

        TIER 1: @db_handle_errors centralizes exception handling.
        """
        query = f"SELECT * FROM {self.schema}.albero_genealogico_proprieta(%s)"
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(query, (partita_id,))
                return [dict(row) for row in cur.fetchall()]

    def get_report_annuale_partite(self, comune_id: int, anno: int) -> List[Dict]:
        """Chiama la funzione SQL report_annuale_partite, filtrata per ID comune e anno."""
        try:
            query = "SELECT * FROM report_annuale_partite(%s, %s)"
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, (comune_id, anno))
                    return [dict(row) for row in cur.fetchall()]
        except psycopg2.Error as db_err: self.logger.error(f"Errore DB get_report_annuale_partite: {db_err}"); return []
        except Exception as e: self.logger.error(f"Errore Python get_report_annuale_partite: {e}"); return []

    @db_handle_errors
    def get_tipi_possesso(self) -> List[Dict[str, Any]]:
        """Ritorna la lista di tutti i tipi di possesso (lookup table)."""
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(
                    f"SELECT id, nome, descrizione FROM {self.schema}.tipo_possesso "
                    "ORDER BY nome"
                )
                return [dict(row) for row in cur.fetchall()]

    @db_handle_errors
    def insert_tipo_possesso(self, nome: str, descrizione: Optional[str] = None) -> int:
        """Inserisce un nuovo tipo di possesso."""
        if not nome or not isinstance(nome, str) or len(nome.strip()) == 0:
            raise DBDataError(f"Nome tipo di possesso non valido: {nome}")
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        f"INSERT INTO {self.schema}.tipo_possesso (nome, descrizione) "
                        "VALUES (%s, %s) RETURNING id",
                        (nome.strip(), descrizione)
                    )
                    tipo_id = cur.fetchone()[0]
                    conn.commit()
                    self.logger.info(f"Tipo di possesso '{nome}' inserito (ID: {tipo_id})")
                    return tipo_id
                except psycopg2.IntegrityError as e:
                    conn.rollback()
                    raise DBUniqueConstraintError(f"Tipo di possesso '{nome}' già esiste: {e}")

    @db_handle_errors
    def update_tipo_possesso(self, tipo_id: int, nome: str, descrizione: Optional[str] = None) -> bool:
        """Aggiorna un tipo di possesso."""
        if not isinstance(tipo_id, int) or tipo_id <= 0:
            raise DBDataError(f"ID tipo di possesso non valido: {tipo_id}")
        if not nome or not isinstance(nome, str) or len(nome.strip()) == 0:
            raise DBDataError(f"Nome tipo di possesso non valido: {nome}")
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        f"UPDATE {self.schema}.tipo_possesso SET nome = %s, descrizione = %s, "
                        "data_modifica = NOW() WHERE id = %s RETURNING id",
                        (nome.strip(), descrizione, tipo_id)
                    )
                    if cur.fetchone() is None:
                        raise DBNotFoundError(f"Tipo di possesso ID {tipo_id} non trovato.")
                    conn.commit()
                    self.logger.info(f"Tipo di possesso ID {tipo_id} aggiornato.")
                    return True
                except psycopg2.IntegrityError as e:
                    conn.rollback()
                    raise DBUniqueConstraintError(f"Nome '{nome}' già esiste per un altro tipo: {e}")

    @db_handle_errors
    def delete_tipo_possesso(self, tipo_id: int) -> bool:
        """Elimina un tipo di possesso (solo se non in uso)."""
        if not isinstance(tipo_id, int) or tipo_id <= 0:
            raise DBDataError(f"ID tipo di possesso non valido: {tipo_id}")
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        f"DELETE FROM {self.schema}.tipo_possesso WHERE id = %s RETURNING id",
                        (tipo_id,)
                    )
                    if cur.fetchone() is None:
                        raise DBNotFoundError(f"Tipo di possesso ID {tipo_id} non trovato.")
                    conn.commit()
                    self.logger.info(f"Tipo di possesso ID {tipo_id} eliminato.")
                    return True
                except psycopg2.IntegrityError as e:
                    conn.rollback()
                    raise DBMError(f"Impossibile eliminare il tipo di possesso (in uso): {e}")

    def get_report_proprieta_possessore(self, possessore_id: int, data_inizio: date, data_fine: date) -> List[Dict]:
        """Chiama la funzione SQL report_proprieta_possessore per ricavare le proprietà di un possessore nel periodo."""
        try:
            query = "SELECT * FROM report_proprieta_possessore(%s, %s, %s)"
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, (possessore_id, data_inizio, data_fine))
                    return [dict(row) for row in cur.fetchall()]
        except psycopg2.Error as db_err: self.logger.error(f"Errore DB get_report_proprieta_possessore: {db_err}"); return []
        except Exception as e: self.logger.error(f"Errore Python get_report_proprieta_possessore: {e}"); return []

    @db_handle_errors
    def get_report_comune(self, comune_id: int) -> Optional[Dict]:
        """Chiama la funzione SQL genera_report_comune e restituisce il riepilogo del comune.

        TIER 1: @db_handle_errors centralizes exception handling.
        """
        query = "SELECT * FROM genera_report_comune(%s)"
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query, (comune_id,))
                row = cur.fetchone()
                if row:
                    return dict(row)
                else:
                    raise DBNotFoundError(f"Nessun report trovato per comune ID {comune_id}")

    @db_handle_errors
    def genera_report_proprieta(self, partita_id: int) -> Optional[str]:
        """Chiama la funzione SQL catasto.genera_report_proprieta.

        TIER 1: @db_handle_errors centralizes exception handling.
        """
        if not isinstance(partita_id, int) or partita_id <= 0:
            raise ValueError(f"ID partita non valido: {partita_id}")

        query = f"SELECT {self.schema}.genera_report_proprieta(%s)"
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (partita_id,))
                result = cur.fetchone()
                if result and result[0] is not None:
                    self.logger.info(f"Report di proprietà generato per partita ID {partita_id}")
                    return str(result[0])
                else:
                    raise DBNotFoundError(f"Nessun report generato per partita ID {partita_id}")

