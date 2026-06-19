"""api/routes/immobili.py — Lista immobili per partita."""
from typing import Optional
from fastapi import APIRouter, Depends, Query

from api.deps import get_db, require_scope

router = APIRouter(prefix="/immobili", tags=["immobili"])


@router.get("")
def search_immobili(
    partita_id: Optional[int] = Query(None),
    comune_id: Optional[int] = Query(None),
    session=Depends(require_scope("read:partite")),
    db=Depends(get_db),
):
    return db.search_immobili(partita_id=partita_id, comune_id=comune_id)
