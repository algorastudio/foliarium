"""api/routes/partite.py — Ricerca, dettaglio, creazione partite + immobili/variazioni inline."""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from datetime import date
import psycopg2.extras

from api.deps import get_db, get_current_session
from catasto_exceptions import DBMError

router = APIRouter(prefix="/partite", tags=["partite"])

TIPI_VARIAZIONE = ('Vendita', 'Acquisto', 'Successione', 'Variazione',
                   'Frazionamento', 'Divisione', 'Trasferimento', 'Altro')


class NuovaPartitaRequest(BaseModel):
    comune_id: int
    numero_partita: int
    suffisso_partita: Optional[str] = None
    data_impianto: Optional[date] = None
    tipo: str = "Principale"
    stato: str = "attiva"
    numero_provenienza: Optional[int] = None


class NuovoImmobileRequest(BaseModel):
    localita_nome: str
    tipologia_stradale: Optional[str] = None
    natura: str
    numero_piani: Optional[int] = None
    numero_vani: Optional[int] = None
    consistenza: Optional[str] = None
    classificazione: Optional[str] = None


class NuovaVariazioneRequest(BaseModel):
    tipo: str
    data_variazione: date
    partita_destinazione_id: Optional[int] = None
    numero_riferimento: Optional[str] = None
    nominativo_riferimento: Optional[str] = None


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
    return db.search_partite(
        comune_id=comune_id,
        numero_partita=numero_partita,
        possessore=possessore,
        immobile_natura=immobile_natura,
        suffisso_partita=suffisso,
    )


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


@router.post("/{partita_id}/immobili", status_code=201)
def add_immobile(
    partita_id: int,
    req: NuovoImmobileRequest,
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    schema = db.schema
    with db._get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            # Verify partita exists and get comune_id
            cur.execute(f"SELECT comune_id FROM {schema}.partita WHERE id = %s", (partita_id,))
            partita_row = cur.fetchone()
            if partita_row is None:
                raise HTTPException(status_code=404, detail="Partita non trovata")
            comune_id = partita_row["comune_id"]

            # Find or create locality
            nome = req.localita_nome.strip()
            cur.execute(
                f"SELECT id FROM {schema}.localita WHERE comune_id = %s AND nome = %s",
                (comune_id, nome),
            )
            loc_row = cur.fetchone()
            if loc_row:
                localita_id = loc_row["id"]
            else:
                cur.execute(
                    f"INSERT INTO {schema}.localita (comune_id, nome, tipologia_stradale) VALUES (%s, %s, %s) RETURNING id",
                    (comune_id, nome, req.tipologia_stradale),
                )
                localita_id = cur.fetchone()["id"]

            # Insert immobile
            cur.execute(
                f"""INSERT INTO {schema}.immobile
                    (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione)
                    VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                (partita_id, localita_id, req.natura, req.numero_piani,
                 req.numero_vani, req.consistenza, req.classificazione),
            )
            immobile_id = cur.fetchone()["id"]

    return {"id": immobile_id}


@router.delete("/{partita_id}/immobili/{immobile_id}", status_code=204)
def remove_immobile(
    partita_id: int,
    immobile_id: int,
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    ok = db.delete_immobile(immobile_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Immobile non trovato")


@router.post("/{partita_id}/variazioni", status_code=201)
def add_variazione(
    partita_id: int,
    req: NuovaVariazioneRequest,
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    if req.tipo not in TIPI_VARIAZIONE:
        raise HTTPException(status_code=422, detail=f"Tipo non valido. Valori ammessi: {TIPI_VARIAZIONE}")

    schema = db.schema
    with db._get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(f"SELECT id FROM {schema}.partita WHERE id = %s", (partita_id,))
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail="Partita non trovata")

            cur.execute(
                f"""INSERT INTO {schema}.variazione
                    (partita_origine_id, partita_destinazione_id, tipo, data_variazione,
                     numero_riferimento, nominativo_riferimento)
                    VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                (partita_id, req.partita_destinazione_id, req.tipo, req.data_variazione,
                 req.numero_riferimento, req.nominativo_riferimento),
            )
            variazione_id = cur.fetchone()["id"]

    return {"id": variazione_id}


@router.delete("/{partita_id}/variazioni/{variazione_id}", status_code=204)
def remove_variazione(
    partita_id: int,
    variazione_id: int,
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    ok = db.delete_variazione(variazione_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Variazione non trovata")
