"""
db/comuni.py — Mixin CRUD per Comuni catastali.
Estratto da catasto_db_manager.py — mixin per CatastoDBManager.
"""

from __future__ import annotations
import logging
from typing import Optional, List, Dict, Any, TYPE_CHECKING

import psycopg2
from psycopg2.extras import DictCursor

from catasto_exceptions import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError

if TYPE_CHECKING:
    from catasto_db_manager import CatastoDBManager


class DBComuniMixin:
    """Mixin CRUD per Comuni catastali."""

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
        """Recupera un elenco di tutti i comuni (ID e nome) per popolare una scelta utente."""
        def _fetch():
            query = f"SELECT id, nome FROM {self.schema}.comune ORDER BY nome"
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                    return cur.fetchall()
        try:
            return self._try_with_cache("comuni_semplice", _fetch)
        except Exception as e:
            self.logger.error(f"Errore nel recuperare l'elenco dei comuni: {e}", exc_info=True)
            raise DBMError("Impossibile recuperare l'elenco dei comuni.") from e

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

