"""api/routes/comuni.py — Elenco e dettaglio comuni."""
from fastapi import APIRouter, Depends
from api.deps import get_db, get_current_session

router = APIRouter(prefix="/comuni", tags=["comuni"])


@router.get("")
def list_comuni(session=Depends(get_current_session), db=Depends(get_db)):
    rows = db.get_elenco_comuni_semplice()
    # rows è lista di tuple (id, nome, provincia, ...)
    result = []
    for r in rows:
        if isinstance(r, dict):
            result.append(r)
        else:
            result.append({"id": r[0], "nome": r[1], "provincia": r[2] if len(r) > 2 else ""})
    return result
