"""api/routes/comuni.py — Elenco, creazione comuni e località per comune."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from api.deps import get_db, get_current_session

router = APIRouter(prefix="/comuni", tags=["comuni"])


class NuovoComuneRequest(BaseModel):
    nome: str
    provincia: str
    regione: str
    codice_catastale: Optional[str] = None


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


@router.post("", status_code=201)
def create_comune(req: NuovoComuneRequest, session=Depends(get_current_session), db=Depends(get_db)):
    try:
        cid = db.registra_comune_nel_db(
            nome=req.nome.strip(),
            provincia=req.provincia.strip(),
            regione=req.regione.strip(),
        )
        if cid is None:
            raise HTTPException(status_code=400, detail="Comune già esistente o errore di inserimento")
        return {"id": cid}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{comune_id}/localita")
def list_localita(comune_id: int, session=Depends(get_current_session), db=Depends(get_db)):
    rows = db.get_localita_by_comune(comune_id)
    return rows
