"""api/routes/comuni.py — Elenco comuni e località per comune."""
from fastapi import APIRouter, Depends
from api.deps import get_db, get_current_session

router = APIRouter(prefix="/comuni", tags=["comuni"])


@router.get("")
def list_comuni(session=Depends(get_current_session), db=Depends(get_db)):
    rows = db.get_elenco_comuni_semplice()
    result = []
    for r in rows:
        if isinstance(r, dict):
            result.append(r)
        else:
            result.append({"id": r[0], "nome": r[1], "provincia": r[2] if len(r) > 2 else ""})
    return result


@router.get("/{comune_id}/localita")
def list_localita(comune_id: int, session=Depends(get_current_session), db=Depends(get_db)):
    rows = db.get_localita_by_comune(comune_id)
    return rows
