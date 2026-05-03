"""
db/ricerca.py — Mixin per ricerche fuzzy/GIN e ricerca avanzata immobili.
Estratto da catasto_db_manager.py — mixin per CatastoDBManager.
"""

from __future__ import annotations
import logging
from datetime import date
from typing import Optional, List, Dict, Any, TYPE_CHECKING

import psycopg2
from psycopg2.extras import DictCursor

from catasto_exceptions import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError
from db.base import db_handle_errors

if TYPE_CHECKING:
    from catasto_db_manager import CatastoDBManager


class DBSearchMixin:
    """Mixin per ricerche fuzzy/GIN e ricerca avanzata immobili."""

    @db_handle_errors
    def search_all_entities_fuzzy(self, query_text: str,
                                search_possessori: bool = True,
                                search_localita: bool = True,
                                search_immobili: bool = True,
                                search_variazioni: bool = True,
                                search_contratti: bool = True,
                                search_partite: bool = True,
                                max_results_per_type: int = 50,
                                similarity_threshold: float = 0.3) -> Dict[str, List[Dict]]:
        """Metodo orchestratore per la ricerca fuzzy che riusa una singola connessione.

        TIER 1: @db_handle_errors centralizes exception handling.
        """
        all_results = {
            "possessore": [], "localita": [], "immobile": [],
            "variazione": [], "contratto": [], "partita": []
        }

        with self._get_connection() as conn:
            if search_possessori:
                all_results["possessore"] = self._search_possessori_fuzzy_internal(conn, query_text, similarity_threshold, max_results_per_type)
            if search_localita:
                all_results["localita"] = self._search_localita_fuzzy_internal(conn, query_text, similarity_threshold, max_results_per_type)
            if search_immobili:
                all_results["immobile"] = self._search_immobili_fuzzy_internal(conn, query_text, similarity_threshold, max_results_per_type)
            if search_variazioni:
                all_results["variazione"] = self._search_variazioni_fuzzy_internal(conn, query_text, similarity_threshold, max_results_per_type)
            if search_contratti:
                all_results["contratto"] = self._search_contratti_fuzzy_internal(conn, query_text, similarity_threshold, max_results_per_type)
            if search_partite:
                all_results["partita"] = self._search_partite_fuzzy_internal(conn, query_text, similarity_threshold, max_results_per_type)

        return all_results

    def _search_localita_fuzzy_internal(self, conn, query: str, threshold: float, limit: int) -> List[Dict]:
        """Ricerca fuzzy interna per le località. Civico è incorporato nel nome da v1.6.1."""
        sql = f"""
            SELECT
                l.id AS entity_id,
                l.nome AS display_text,
                'Tipologia: ' || COALESCE(l.tipologia_stradale, 'N/D') || ' | Comune: ' || c.nome AS detail_text,
                similarity(l.nome, %s) AS similarity_score,
                'nome' AS search_field,
                l.nome,
                l.tipologia_stradale,
                c.nome as comune_nome,
                COALESCE(im.num_immobili, 0) as num_immobili
            FROM {self.schema}.localita l
            JOIN {self.schema}.comune c ON l.comune_id = c.id
            LEFT JOIN (
                SELECT localita_id, COUNT(*) as num_immobili
                FROM {self.schema}.immobile
                GROUP BY localita_id
            ) im ON l.id = im.localita_id
            WHERE similarity(l.nome, %s) >= %s
            ORDER BY similarity_score DESC
            LIMIT %s;
        """
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

    @db_handle_errors
    def verify_gin_indices(self) -> Dict[str, Any]:
        """Verifica la presenza di indici GIN per la ricerca testuale nello schema specificato.

        TIER 1: @db_handle_errors centralizes exception handling.
        """
        query = """
            SELECT COUNT(*)
            FROM pg_indexes
            WHERE schemaname = %s AND indexdef LIKE '%% USING gin %%';
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (self.schema,))
                result = cur.fetchone()
                count = result[0] if result else 0
                return {'status': 'OK', 'gin_indices': count}

    @db_handle_errors
    def ricerca_avanzata_immobili_gui(self, comune_id: Optional[int] = None, localita_id: Optional[int] = None,
                                      natura_search: Optional[str] = None, classificazione_search: Optional[str] = None,
                                      consistenza_search: Optional[str] = None,
                                      piani_min: Optional[int] = None, piani_max: Optional[int] = None,
                                      vani_min: Optional[int] = None, vani_max: Optional[int] = None,
                                      nome_possessore_search: Optional[str] = None,
                                      data_inizio_possesso_search: Optional[date] = None,
                                      data_fine_possesso_search: Optional[date] = None,
                                     ) -> List[Dict[str, Any]]:
        """Ricerca avanzata immobili con query diretta (non usa stored procedure).

        TIER 1: @db_handle_errors centralizes exception handling.
        """
        conditions: List[str] = []
        params: List[Any] = []

        joins = f"""
            FROM {self.schema}.immobile i
            JOIN {self.schema}.partita p ON i.partita_id = p.id
            JOIN {self.schema}.comune c ON p.comune_id = c.id
            JOIN {self.schema}.localita l ON i.localita_id = l.id
        """

        if comune_id is not None:
            conditions.append("p.comune_id = %s"); params.append(comune_id)
        if localita_id is not None:
            conditions.append("i.localita_id = %s"); params.append(localita_id)
        if natura_search:
            conditions.append("i.natura ILIKE %s"); params.append(f"%{natura_search}%")
        if classificazione_search:
            conditions.append("i.classificazione ILIKE %s"); params.append(f"%{classificazione_search}%")
        if consistenza_search:
            conditions.append("i.consistenza ILIKE %s"); params.append(f"%{consistenza_search}%")
        if piani_min is not None:
            conditions.append("i.numero_piani >= %s"); params.append(piani_min)
        if piani_max is not None:
            conditions.append("i.numero_piani <= %s"); params.append(piani_max)
        if vani_min is not None:
            conditions.append("i.numero_vani >= %s"); params.append(vani_min)
        if vani_max is not None:
            conditions.append("i.numero_vani <= %s"); params.append(vani_max)
        if nome_possessore_search:
            joins += f"""
                JOIN {self.schema}.partita_possessore pp_f ON p.id = pp_f.partita_id
                JOIN {self.schema}.possessore pos_f ON pp_f.possessore_id = pos_f.id
            """
            conditions.append("pos_f.nome_completo ILIKE %s")
            params.append(f"%{nome_possessore_search}%")

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        query = f"""
            SELECT DISTINCT
                i.id AS id_immobile, p.numero_partita, c.nome AS comune_nome,
                l.nome AS localita_nome, l.tipologia_stradale AS localita_tipo,
                i.natura, i.classificazione, i.consistenza, i.numero_piani, i.numero_vani,
                (SELECT string_agg(DISTINCT pos_agg.nome_completo, ', ')
                 FROM {self.schema}.partita_possessore pp_agg
                 JOIN {self.schema}.possessore pos_agg ON pp_agg.possessore_id = pos_agg.id
                 WHERE pp_agg.partita_id = p.id AND pos_agg.attivo = TRUE) AS possessori_attuali
            {joins}
            {where}
            ORDER BY c.nome, p.numero_partita, i.natura
        """

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(query, params)
                return [dict(row) for row in cur.fetchall()]

