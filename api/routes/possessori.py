"""api/routes/possessori.py — Ricerca e dettaglio possessori."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from api.deps import get_db, get_current_session

router = APIRouter(prefix="/possessori", tags=["possessori"])


@router.get("")
def search_possessori(
    q: Optional[str] = Query(None, description="Termine di ricerca"),
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    if not q or len(q.strip()) < 2:
        return []
    return db.search_possessori_by_term_globally(q.strip())


@router.get("/{possessore_id}")
def get_possessore(possessore_id: int, session=Depends(get_current_session), db=Depends(get_db)):
    schema = db.schema
    with db._get_connection() as conn:
        import psycopg2.extras
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
