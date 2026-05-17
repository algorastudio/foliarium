"""api/routes/dashboard.py — Statistiche per la dashboard analytics."""
import logging

from fastapi import APIRouter, Depends

from api.deps import get_db, get_current_session

logger = logging.getLogger("FoliariumAPI.dashboard")

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
def get_stats(session=Depends(get_current_session), db=Depends(get_db)):
    """Statistiche aggregate base — usate dalla pagina Analytics."""
    try:
        stats_comune = db.get_statistiche_comune() or []
    except Exception as _e:
        logger.warning("Errore stats comune: %s", _e)
        stats_comune = []

    base = {"total_comuni": 0, "total_partite": 0, "total_possessori": 0, "total_immobili": 0}
    try:
        base.update(db.get_dashboard_stats() or {})
    except Exception as _e:
        logger.warning("Errore dashboard stats: %s", _e)

    totale_partite = base.get("total_partite") or sum(r.get("num_partite", 0) for r in stats_comune)
    totale_comuni = base.get("total_comuni") or len(stats_comune)

    return {
        "totale_partite": totale_partite,
        "totale_comuni": totale_comuni,
        "totale_possessori": base.get("total_possessori", 0),
        "totale_immobili": base.get("total_immobili", 0),
        "per_comune": stats_comune[:10],
    }


@router.get("/analytics")
def get_analytics(session=Depends(get_current_session), db=Depends(get_db)):
    """Aggregati per la dashboard analytics: KPI + breakdown per comune e tipologia."""
    try:
        stats_comune = db.get_statistiche_comune() or []
    except Exception as _e:
        logger.warning("Errore stats comune: %s", _e)
        stats_comune = []

    base = {"total_comuni": 0, "total_partite": 0, "total_possessori": 0, "total_immobili": 0}
    try:
        base.update(db.get_dashboard_stats() or {})
    except Exception as _e:
        logger.warning("Errore dashboard stats: %s", _e)

    # Top 5 comuni per numero partite
    sorted_comuni = sorted(
        stats_comune,
        key=lambda r: r.get("num_partite", 0) or 0,
        reverse=True,
    )[:5]
    top_comuni = [
        {
            "comune": r.get("comune") or r.get("comune_nome") or r.get("nome") or "—",
            "num_partite": int(r.get("num_partite") or 0),
        }
        for r in sorted_comuni
    ]

    # Variazioni totali (ultimo secolo)
    variazioni = 0
    try:
        with db._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) FROM {db.schema}.variazione")
                row = cur.fetchone()
                if row:
                    variazioni = int(row[0] or 0)
    except Exception as _e:
        logger.warning("Errore conteggio variazioni: %s", _e)
        variazioni = 0

    # Distribuzione tipologie (Partite / Variazioni / Atti notarili surrogato = contratti)
    contratti = 0
    try:
        with db._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) FROM {db.schema}.contratto")
                row = cur.fetchone()
                if row:
                    contratti = int(row[0] or 0)
    except Exception as _e:
        logger.warning("Errore conteggio contratti: %s", _e)
        contratti = 0

    total_docs = (base.get("total_partite", 0) or 0) + variazioni + contratti
    if total_docs <= 0:
        distribuzione = []
    else:
        distribuzione = [
            {"label": "Partite", "value": base.get("total_partite", 0), "pct": round(100 * base.get("total_partite", 0) / total_docs, 1)},
            {"label": "Variazioni", "value": variazioni, "pct": round(100 * variazioni / total_docs, 1)},
            {"label": "Atti notarili", "value": contratti, "pct": round(100 * contratti / total_docs, 1)},
        ]

    # Utenti attivi (best-effort)
    utenti_attivi = 0
    try:
        with db._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT COUNT(*) FROM {db.schema}.utente WHERE attivo = true"
                )
                row = cur.fetchone()
                if row:
                    utenti_attivi = int(row[0] or 0)
    except Exception as _e:
        logger.warning("Errore conteggio utenti attivi: %s", _e)
        utenti_attivi = 0

    return {
        "kpi": {
            "partite": base.get("total_partite", 0),
            "particelle": base.get("total_immobili", 0),
            "variazioni": variazioni,
            "utenti_attivi": utenti_attivi,
        },
        "top_comuni": top_comuni,
        "distribuzione_documenti": distribuzione,
        "qualita_dati": {
            # Heuristica: percentuale di partite con almeno un possessore associato
            "completezza_pct": _completezza_pct(db),
            "duplicati_pct": _duplicati_pct(db),
        },
    }


def _completezza_pct(db) -> float:
    try:
        with db._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT
                      COALESCE(
                        100.0 * (SELECT COUNT(DISTINCT partita_id) FROM {db.schema}.partita_possessore)
                              / NULLIF((SELECT COUNT(*) FROM {db.schema}.partita), 0),
                        0
                      )
                    """
                )
                row = cur.fetchone()
                return round(float(row[0] or 0), 1)
    except Exception as _e:
        logger.warning("Errore calcolo metrica qualita: %s", _e)
        return 0.0


def _duplicati_pct(db) -> float:
    try:
        with db._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT
                      COALESCE(
                        100.0 * (
                          SELECT COUNT(*) FROM (
                            SELECT nome_completo FROM {db.schema}.possessore
                            GROUP BY nome_completo HAVING COUNT(*) > 1
                          ) d
                        ) / NULLIF((SELECT COUNT(*) FROM {db.schema}.possessore), 0),
                        0
                      )
                    """
                )
                row = cur.fetchone()
                return round(float(row[0] or 0), 1)
    except Exception as _e:
        logger.warning("Errore calcolo metrica qualita: %s", _e)
        return 0.0
