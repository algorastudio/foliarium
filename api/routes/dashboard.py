"""api/routes/dashboard.py — Statistiche per la dashboard."""
from fastapi import APIRouter, Depends
from api.deps import get_db, get_current_session

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
def get_stats(session=Depends(get_current_session), db=Depends(get_db)):
    try:
        stats_comune = db.get_statistiche_comune()
    except Exception:
        stats_comune = []

    totale_partite = sum(r.get("num_partite", 0) for r in stats_comune) if stats_comune else 0
    totale_comuni = len(stats_comune)

    return {
        "totale_partite": totale_partite,
        "totale_comuni": totale_comuni,
        "per_comune": stats_comune[:10],
    }
