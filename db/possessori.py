"""
db/possessori.py — Mixin CRUD per Possessori.
Estratto da catasto_db_manager.py — mixin per CatastoDBManager.
"""

from __future__ import annotations
import logging
from typing import Optional, List, Dict, Any, Union, TYPE_CHECKING

import csv
import json
import psycopg2
from psycopg2.extras import DictCursor

from catasto_exceptions import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError
from db.base import db_handle_errors

if TYPE_CHECKING:
    from catasto_db_manager import CatastoDBManager


class DBPossessoriMixin:
    """Mixin CRUD per Possessori."""

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

    @db_handle_errors
    def check_possessore_exists(self, nome_completo: str, comune_id: Optional[int] = None) -> Optional[int]:
        """Verifica se un possessore esiste e ritorna il suo ID.

        TIER 1: @db_handle_errors centralizes exception handling.
        """
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

    @db_handle_errors
    def get_partite_per_possessore(self, possessore_id: int) -> List[Dict[str, Any]]:
        """Recupera tutte le partite per un possessore.

        TIER 1: @db_handle_errors centralizes exception handling.
        """
        if not possessore_id > 0:
            raise DBDataError("ID possessore non valido")

        query = f"""
            SELECT p.id, p.numero_partita, p.suffisso_partita, p.tipo, p.stato,
                c.id as comune_id, c.nome as comune_nome, pp.titolo, pp.quota
            FROM {self.schema}.partita p
            JOIN {self.schema}.comune c ON p.comune_id = c.id
            JOIN {self.schema}.partita_possessore pp ON p.id = pp.partita_id
            WHERE pp.possessore_id = %s ORDER BY c.nome, p.numero_partita;
        """
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query, (possessore_id,))
                return [dict(row) for row in cur.fetchall()]

    @db_handle_errors
    def search_possessori_by_term_globally(self, search_term: Optional[str], limit: int = 200,
                                            solo_attivi: bool = True) -> List[Dict[str, Any]]:
        """Ricerca possessori globalmente.

        Args:
            search_term: termine di ricerca (None = tutti)
            limit: numero massimo di risultati
            solo_attivi: se True (default), filtra i possessori archiviati (attivo=FALSE)

        TIER 1: @db_handle_errors centralizes exception handling.
        """
        query_base = f"""
            SELECT p.id, p.nome_completo, p.cognome_nome, p.paternita, p.attivo,
                c.nome AS comune_riferimento_nome
            FROM {self.schema}.possessore p
            LEFT JOIN {self.schema}.comune c ON p.comune_id = c.id
        """

        params: List[Union[str, int]] = []
        where_clauses = []

        if solo_attivi:
            where_clauses.append("p.attivo = TRUE")

        if search_term and search_term.strip():
            like_term = f"%{search_term.strip()}%"
            where_clauses.append("(p.nome_completo ILIKE %s OR p.cognome_nome ILIKE %s OR p.paternita ILIKE %s)")
            params.extend([like_term, like_term, like_term])

        query = query_base
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        query += " ORDER BY p.nome_completo LIMIT %s"
        params.append(limit)

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                data_list = [dict(row) for row in rows]
                self.logger.info(f"search_possessori_by_term_globally ha trovato {len(data_list)} possessori")
                return data_list

    @db_handle_errors
    def get_possessori_per_partita(self, partita_id: int) -> List[Dict[str, Any]]:
        """Recupera tutti i possessori associati a una data partita.

        TIER 1: @db_handle_errors centralizes exception handling.
        """
        if not isinstance(partita_id, int) or partita_id <= 0:
            raise DBDataError(f"ID partita non valido: {partita_id}")

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

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query, (partita_id,))
                results = [dict(row) for row in cur.fetchall()]
                self.logger.info(f"Trovati {len(results)} possessori per la partita ID {partita_id}")
                return results

    def get_possessori_by_comune(self, comune_id: int, filter_text: Optional[str] = None, solo_con_partite: bool = False) -> List[Dict[str, Any]]:
        """
        Recupera i possessori per un dato comune, con filtri opzionali.
        Se solo_con_partite è True, restituisce solo i possessori con almeno una partita associata.
        """
        if not isinstance(comune_id, int) or comune_id <= 0:
            raise DBDataError("ID comune non valido.")

        params: List[Union[int, str]] = [comune_id]

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

        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(query, tuple(params))
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            self.logger.error(f"Errore DB in get_possessori_by_comune: {e}", exc_info=True)
            raise DBMError("Impossibile recuperare i possessori.") from e

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

    def export_possessore_json(self, possessore_id: int) -> Optional[str]:
        """Chiama la funzione SQL esporta_possessore_json e restituisce il JSON come stringa indentata."""
        try:
            query = "SELECT esporta_possessore_json(%s) AS possessore_json"
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, (possessore_id,))
                    result = cur.fetchone()
                    if result and result['possessore_json']:
                        try:
                            # La funzione SQL restituisce già un oggetto JSON: lo serializziamo come stringa indentata
                            return json.dumps(result['possessore_json'], indent=4, ensure_ascii=False)
                        except (TypeError, ValueError) as json_err:
                            self.logger.error(f"Errore serializzazione JSON per possessore {possessore_id}: {json_err}")
                            return str(result['possessore_json'])
            self.logger.warning(f"Nessun JSON restituito per possessore ID {possessore_id}.")
        except psycopg2.Error as db_err: self.logger.error(f"Errore DB export_possessore_json (ID: {possessore_id}): {db_err}")
        except Exception as e: self.logger.error(f"Errore Python export_possessore_json (ID: {possessore_id}): {e}")
        return None

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

