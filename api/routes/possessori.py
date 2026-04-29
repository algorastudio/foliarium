"""api/routes/possessori.py — Ricerca e creazione possessori."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.deps import get_db, get_current_session
from catasto_exceptions import DBMError

router = APIRouter(prefix="/possessori", tags=["possessori"])


class NuovoPossessoreRequest(BaseModel):
    nome_completo: str
    cognome_nome: Optional[str] = None
    paternita: Optional[str] = None
    comune_riferimento_id: int


class AssegnaPossessoreRequest(BaseModel):
    possessore_id: int
    partita_id: int
    titolo: str = "Proprietario"
    quota: Optional[str] = None
    tipo_partita_rel: str = "principale"


@router.get("")
def search_possessori(
    q: Optional[str] = Query(None, description="Termine di ricerca"),
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    if not q or len(q.strip()) < 2:
        return []
    return db.search_possessori_by_term_globally(q.strip())


@router.post("", status_code=201)
def create_possessore(req: NuovoPossessoreRequest, session=Depends(get_current_session), db=Depends(get_db)):
    try:
        pid = db.create_possessore(
            nome_completo=req.nome_completo,
            comune_riferimento_id=req.comune_riferimento_id,
            paternita=req.paternita,
            cognome_nome=req.cognome_nome,
        )
        return {"id": pid}
    except DBMError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/assegna", status_code=201)
def assegna_possessore(req: AssegnaPossessoreRequest, session=Depends(get_current_session), db=Depends(get_db)):
    try:
        ok = db.aggiungi_possessore_a_partita(
            partita_id=req.partita_id,
            possessore_id=req.possessore_id,
            tipo_partita_rel=req.tipo_partita_rel,
            titolo=req.titolo,
            quota=req.quota,
        )
        if not ok:
            raise HTTPException(status_code=400, detail="Impossibile assegnare il possessore")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{possessore_id}")
def get_possessore(possessore_id: int, session=Depends(get_current_session), db=Depends(get_db)):
    rows = db.get_possessore_details(possessore_id)
    return rows


@router.get("/{possessore_id}/partite")
def get_partite_possessore(possessore_id: int, session=Depends(get_current_session), db=Depends(get_db)):
    return db.get_partite_per_possessore(possessore_id)
