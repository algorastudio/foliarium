"""api/routes/partite.py — Ricerca, dettaglio e creazione partite."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from datetime import date

from api.deps import get_db, get_current_session
from catasto_exceptions import DBMError

router = APIRouter(prefix="/partite", tags=["partite"])


class NuovaPartitaRequest(BaseModel):
    comune_id: int
    numero_partita: int
    suffisso_partita: Optional[str] = None
    data_impianto: Optional[date] = None
    tipo: str = "Principale"
    stato: str = "attiva"
    numero_provenienza: Optional[int] = None


@router.get("")
def search_partite(
    comune_id: Optional[int] = Query(None),
    numero_partita: Optional[int] = Query(None),
    possessore: Optional[str] = Query(None),
    immobile_natura: Optional[str] = Query(None),
    suffisso: Optional[str] = Query(None),
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    rows = db.search_partite(
        comune_id=comune_id,
        numero_partita=numero_partita,
        possessore=possessore,
        immobile_natura=immobile_natura,
        suffisso_partita=suffisso,
    )
    return rows


@router.get("/{partita_id}")
def get_partita(partita_id: int, session=Depends(get_current_session), db=Depends(get_db)):
    try:
        detail = db.get_partita_details(partita_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    if detail is None:
        raise HTTPException(status_code=404, detail="Partita non trovata")
    return detail


@router.post("", status_code=201)
def create_partita(req: NuovaPartitaRequest, session=Depends(get_current_session), db=Depends(get_db)):
    try:
        partita_id = db.create_partita(
            comune_id=req.comune_id,
            numero_partita=req.numero_partita,
            suffisso_partita=req.suffisso_partita,
            data_impianto=req.data_impianto,
            tipo=req.tipo,
            stato=req.stato,
            numero_provenienza=req.numero_provenienza,
        )
        return {"id": partita_id}
    except DBMError as e:
        raise HTTPException(status_code=400, detail=str(e))
