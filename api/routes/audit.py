"""api/routes/audit.py — Audit log e statistiche giornaliere."""
from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.deps import get_db, require_scope

router = APIRouter(prefix="/audit", tags=["audit"])


_OP_LABELS = {
    "I": "insert",
    "U": "update",
    "D": "delete",
    "S": "view",
}


def _serialize(row: dict) -> dict:
    out = {}
    for k, v in row.items():
        if isinstance(v, (datetime, date)):
            out[k] = v.isoformat()
        else:
            out[k] = v
    op = out.get("operazione")
    if isinstance(op, str):
        out["operazione_label"] = _OP_LABELS.get(op, op.lower())
    return out


@router.get("")
def list_audit(
    table_name: Optional[str] = Query(None),
    username: Optional[str] = Query(None),
    operation: Optional[str] = Query(None, description="I, U, D, S"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    session=Depends(require_scope("read:audit")),
    db=Depends(get_db),
):
    filters: dict = {}
    if table_name:
        filters["table_name"] = table_name
    if username:
        filters["username"] = username
    if operation:
        filters["operation_char"] = operation.upper()[:1]

    try:
        logs, total = db.get_audit_logs(
            filters=filters, page=page, page_size=page_size,
            sort_by="timestamp", sort_order="DESC",
        )
    except Exception:
        logs, total = [], 0

    return {
        "items": [_serialize(r) for r in logs],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/summary")
def audit_summary(session=Depends(require_scope("read:audit")), db=Depends(get_db)):
    """KPI per la pagina audit: azioni oggi, utenti attivi, export, anomalie."""
    today = date.today()
    start = datetime.combine(today, datetime.min.time())
    end = datetime.combine(today, datetime.max.time())

    try:
        logs, total = db.get_audit_logs(
            filters={"start_datetime": start, "end_datetime": end},
            page=1, page_size=1000,
        )
    except Exception:
        logs, total = [], 0

    users_today = {r.get("username") for r in logs if r.get("username")}
    exports = sum(1 for r in logs if "export" in (r.get("tabella") or "").lower()
                  or "export" in str(r.get("dettagli") or "").lower())
    anomalie = sum(1 for r in logs if (r.get("operazione") == "D"))

    return {
        "azioni_oggi": total,
        "utenti_attivi": len(users_today),
        "export_effettuati": exports,
        "anomalie": anomalie,
    }
