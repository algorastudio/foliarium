"""api/routes/possessori.py — Ricerca, dettaglio e creazione possessori."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
import psycopg2.extras

from api.deps import get_db, get_current_session

router = APIRouter(prefix="/possessori", tags=["possessori"])


class NuovoPossessoreRequest(BaseModel):
    nome_completo: str
    cognome_nome: Optional[str] = None
    paternita: Optional[str] = None
    comune_id: int


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
            raise HTTPException(status_code=400, detail="Impossibile assegnare il possessore alla partita")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{possessore_id}")
def get_possessore(possessore_id: int, session=Depends(get_current_session), db=Depends(get_db)):
    schema = db.schema
    with db._get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                f"SELECT id, nome_completo, cognome_nome, paternita FROM {schema}.possessore WHERE id = %s",
                (possessore_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Possessore non trovato")
            info = dict(row)

    partite = db.get_partite_per_possessore(possessore_id)
    return {**info, "partite": partite}


@router.post("", status_code=201)
def create_possessore(req: NuovoPossessoreRequest, session=Depends(get_current_session), db=Depends(get_db)):
    try:
        possessore_id = db.create_possessore(
            nome_completo=req.nome_completo.strip(),
            comune_riferimento_id=req.comune_id,
            paternita=req.paternita.strip() if req.paternita else None,
            cognome_nome=req.cognome_nome.strip() if req.cognome_nome else None,
        )
        return {"id": possessore_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
