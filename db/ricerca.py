"""
db/ricerca.py — Mixin per ricerche fuzzy/GIN e ricerca avanzata immobili.
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


class DBSearchMixin:
    """Mixin per ricerche fuzzy/GIN e ricerca avanzata immobili."""

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

