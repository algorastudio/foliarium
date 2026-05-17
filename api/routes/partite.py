"""api/routes/partite.py — Ricerca, dettaglio, creazione partite + immobili/variazioni inline."""
from typing import Optional
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
    tipologia_stradale: str
    natura: str
    numero_civico: Optional[str] = None
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


class AggiungiPossessoreRequest(BaseModel):
    possessore_id: int
    titolo: str = "proprietà esclusiva"
    quota: Optional[str] = None
    tipo_partita: Optional[str] = None  # 'principale' o 'secondaria'; default = tipo della partita


class PatchPartitaRequest(BaseModel):
    stato: Optional[str] = None
    data_chiusura: Optional[date] = None
    suffisso_partita: Optional[str] = None
    numero_provenienza: Optional[int] = None
    tipo: Optional[str] = None


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


@router.patch("/{partita_id}")
def patch_partita(
    partita_id: int,
    req: PatchPartitaRequest,
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    dati = req.model_dump(exclude_unset=True)
    if not dati:
        raise HTTPException(status_code=422, detail="Nessun campo fornito.")
    try:
        db.update_partita(partita_id, dati)
    except DBMError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


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

            # Find or create locality (univoca per comune+nome+tipologia)
            nome = req.localita_nome.strip()
            tipologia = req.tipologia_stradale.strip()
            cur.execute(
                f"SELECT id FROM {schema}.localita "
                f"WHERE comune_id = %s AND nome = %s AND tipologia_stradale = %s",
                (comune_id, nome, tipologia),
            )
            loc_row = cur.fetchone()
            if loc_row:
                localita_id = loc_row["id"]
            else:
                cur.execute(
                    f"INSERT INTO {schema}.localita (comune_id, nome, tipologia_stradale) "
                    f"VALUES (%s, %s, %s) RETURNING id",
                    (comune_id, nome, tipologia),
                )
                localita_id = cur.fetchone()["id"]

            # Insert immobile
            cur.execute(
                f"""INSERT INTO {schema}.immobile
                    (partita_id, localita_id, numero_civico, natura,
                     numero_piani, numero_vani, consistenza, classificazione)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                (partita_id, localita_id, req.numero_civico, req.natura,
                 req.numero_piani, req.numero_vani, req.consistenza, req.classificazione),
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


@router.post("/{partita_id}/possessori", status_code=201)
def add_possessore_to_partita(
    partita_id: int,
    req: AggiungiPossessoreRequest,
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    schema = db.schema
    # Determina tipo_partita di default dalla partita stessa
    tipo_rel = (req.tipo_partita or "").strip().lower() or None
    if tipo_rel is None:
        with db._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(f"SELECT tipo FROM {schema}.partita WHERE id = %s", (partita_id,))
                row = cur.fetchone()
                if row is None:
                    raise HTTPException(status_code=404, detail="Partita non trovata")
                tipo_rel = (row["tipo"] or "principale").lower()

    if tipo_rel not in ("principale", "secondaria"):
        raise HTTPException(status_code=422, detail="tipo_partita deve essere 'principale' o 'secondaria'")

    try:
        db.aggiungi_possessore_a_partita(
            partita_id=partita_id,
            possessore_id=req.possessore_id,
            tipo_partita_rel=tipo_rel,
            titolo=req.titolo,
            quota=req.quota,
        )
    except DBMError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


@router.delete("/{partita_id}/possessori/{possessore_id}", status_code=204)
def remove_possessore_from_partita(
    partita_id: int,
    possessore_id: int,
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    schema = db.schema
    with db._get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT id FROM {schema}.partita_possessore WHERE partita_id = %s AND possessore_id = %s",
                (partita_id, possessore_id),
            )
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Legame partita-possessore non trovato")
            relazione_id = row[0]

    try:
        db.rimuovi_possessore_da_partita(relazione_id)
    except DBMError as e:
        raise HTTPException(status_code=400, detail=str(e))
