"""api/routes/genealogia.py — Albero genealogico delle partite."""
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_db, get_current_session

router = APIRouter(prefix="/genealogia", tags=["genealogia"])


def _node(row: dict | None) -> dict | None:
    if row is None:
        return None
    out: dict[str, Any] = {}
    for k, v in row.items():
        if isinstance(v, (datetime, date)):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


@router.get("/{partita_id}")
def get_genealogia(partita_id: int, session=Depends(get_current_session), db=Depends(get_db)):
    try:
        data = db.get_genealogia_partita(partita_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

    if data is None:
        raise HTTPException(status_code=404, detail="Partita non trovata")

    return {
        "partita": _node(data.get("partita")),
        "predecessori": [_node(r) for r in data.get("predecessori") or []],
        "successori": [_node(r) for r in data.get("successori") or []],
    }
