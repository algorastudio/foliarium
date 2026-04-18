"""api/routes/possessori.py — Ricerca possessori."""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from api.deps import get_db, get_current_session

router = APIRouter(prefix="/possessori", tags=["possessori"])


@router.get("")
def search_possessori(
    q: Optional[str] = Query(None, description="Termine di ricerca"),
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    if not q or len(q.strip()) < 2:
        return []
    return db.search_possessori_by_term_globally(q.strip())


@router.get("/{possessore_id}")
def get_possessore(possessore_id: int, session=Depends(get_current_session), db=Depends(get_db)):
    rows = db.get_possessore_details(possessore_id)
    return rows
