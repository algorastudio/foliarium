"""api/rate_limit.py — Rate limiting in-memory per le chiavi API.

Il server API è un'unica istanza uvicorn locale (single-process), quindi un
contatore in-memory è sufficiente e non richiede storage esterno (Redis ecc.).

Strategia: **fixed window** per minuto. Per ogni `api_key_id` si tiene il
minuto corrente (epoch // 60) e il numero di richieste in quel minuto. Quando
il contatore supera ``rate_limit_per_min`` la richiesta viene rifiutata con
``429`` finché non inizia la finestra successiva.

Solo le chiavi API hanno un rate limit; le sessioni umane (bearer) non sono
soggette a throttling. ``limit <= 0`` significa "nessun limite".
"""
from __future__ import annotations

import threading
import time

_lock = threading.Lock()

# api_key_id -> {"window": int, "count": int}
_buckets: dict[int, dict] = {}


def check_and_increment(api_key_id: int, limit_per_min: int | None) -> tuple[bool, int]:
    """Registra una richiesta per la chiave e indica se è consentita.

    Args:
        api_key_id: identificativo della chiave API.
        limit_per_min: tetto di richieste al minuto. ``None`` o ``<= 0`` =
            nessun limite.

    Returns:
        ``(allowed, retry_after_seconds)``. Quando ``allowed`` è ``False``,
        ``retry_after_seconds`` indica tra quanti secondi inizia la finestra
        successiva (per l'header ``Retry-After``).
    """
    if not limit_per_min or limit_per_min <= 0 or api_key_id is None:
        return True, 0

    now = time.time()
    window = int(now // 60)

    with _lock:
        entry = _buckets.get(api_key_id)
        if entry is None or entry["window"] != window:
            _buckets[api_key_id] = {"window": window, "count": 1}
            return True, 0
        if entry["count"] >= limit_per_min:
            retry_after = 60 - int(now % 60)
            return False, max(retry_after, 1)
        entry["count"] += 1
        return True, 0


def reset() -> None:
    """Azzera tutti i contatori (usato dai test e all'avvio del server)."""
    with _lock:
        _buckets.clear()
