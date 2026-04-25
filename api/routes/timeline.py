"""api/routes/timeline.py — Timeline cronologica della proprietà di una partita."""
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_db, get_current_session

router = APIRouter(prefix="/timeline", tags=["timeline"])


def _iso(v: Any) -> Any:
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return v


@router.get("/partita/{partita_id}")
def partita_timeline(partita_id: int, session=Depends(get_current_session), db=Depends(get_db)):
    """Eventi cronologici di una partita: impianto + variazioni in entrata/uscita + chiusura."""
    try:
        gen = db.get_genealogia_partita(partita_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    if gen is None or not gen.get("partita"):
        raise HTTPException(status_code=404, detail="Partita non trovata")

    eventi: list[dict] = []
    p = gen["partita"]
    if p.get("data_impianto"):
        eventi.append({
            "data": _iso(p["data_impianto"]),
            "tipo": "impianto",
            "label": "Impianto catastale",
            "dettagli": p.get("possessori") or "",
        })

    for pred in gen.get("predecessori") or []:
        if pred.get("data_variazione"):
            eventi.append({
                "data": _iso(pred["data_variazione"]),
                "tipo": pred.get("tipo_variazione") or "variazione",
                "label": (pred.get("tipo_variazione") or "Variazione").capitalize(),
                "dettagli": pred.get("nominativo_riferimento") or pred.get("possessori") or "",
                "partita_origine": pred.get("numero_partita"),
            })

    for succ in gen.get("successori") or []:
        if succ.get("data_variazione"):
            eventi.append({
                "data": _iso(succ["data_variazione"]),
                "tipo": succ.get("tipo_variazione") or "variazione",
                "label": (succ.get("tipo_variazione") or "Variazione").capitalize(),
                "dettagli": succ.get("nominativo_riferimento") or succ.get("possessori") or "",
                "partita_destinazione": succ.get("numero_partita"),
            })

    if p.get("data_chiusura"):
        eventi.append({
            "data": _iso(p["data_chiusura"]),
            "tipo": "chiusura",
            "label": "Chiusura partita",
            "dettagli": "",
        })

    eventi.sort(key=lambda e: e.get("data") or "")
    return {"partita_id": partita_id, "eventi": eventi}
