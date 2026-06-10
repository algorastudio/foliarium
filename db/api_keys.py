"""db/api_keys.py — Gestione chiavi API per integrazioni esterne.

La chiave in chiaro ha formato `flr_<32 hex>` (16 byte random). La sua
controparte persistita è lo SHA-256 in `key_hash`. Il prefisso (primi 12
caratteri) viene memorizzato in chiaro per consentire alla UI di
amministrazione di identificare le chiavi senza esporre il segreto.

Il segreto viene restituito dall'API una sola volta al momento della
creazione (`create_api_key`). Tutte le operazioni successive parlano in
termini di id o prefix.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime
from typing import List, Optional

import psycopg2
import psycopg2.extras


_logger = logging.getLogger("CatastoGUI.db.api_keys")

_KEY_BYTES = 16  # 32 hex chars → spazio chiavi 2^128
_KEY_PREFIX = "flr_"
_PREFIX_LEN = 12  # "flr_" + 8 hex


def _generate_plaintext_key() -> str:
    return f"{_KEY_PREFIX}{secrets.token_hex(_KEY_BYTES)}"


def _hash_key(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


class DBApiKeysMixin:
    """Mixin CRUD per la tabella `catasto.api_keys`."""

    def create_api_key(
        self,
        name: str,
        scopes: List[str],
        created_by: Optional[int] = None,
        expires_at: Optional[datetime] = None,
        rate_limit_per_min: int = 60,
    ) -> tuple[int, str]:
        """Crea una nuova chiave API.

        Returns:
            Tupla (id, plaintext_key). Il plaintext NON è recuperabile in
            seguito: va mostrato all'utente una sola volta.

        Raises:
            ValueError: se `name` è vuoto o scopes è None.
        """
        if not name or not name.strip():
            raise ValueError("name non può essere vuoto")
        if scopes is None:
            raise ValueError("scopes non può essere None (usare lista vuota)")

        plaintext = _generate_plaintext_key()
        key_hash = _hash_key(plaintext)
        prefix = plaintext[:_PREFIX_LEN]

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"INSERT INTO {self.schema}.api_keys "
                    f"  (name, key_hash, prefix, scopes, created_by, "
                    f"   expires_at, rate_limit_per_min) "
                    f"VALUES (%s, %s, %s, %s, %s, %s, %s) "
                    f"RETURNING id",
                    (name.strip(), key_hash, prefix, list(scopes),
                     created_by, expires_at, rate_limit_per_min),
                )
                new_id = cur.fetchone()[0]
            conn.commit()

        _logger.info(
            "Creata API key id=%d name=%r prefix=%s scopes=%s by=%s",
            new_id, name, prefix, scopes, created_by,
        )
        return new_id, plaintext

    def list_api_keys(self, include_revoked: bool = False) -> List[dict]:
        """Elenca le chiavi API. Non restituisce mai il plaintext né lo hash."""
        sql = (
            f"SELECT k.id, k.name, k.prefix, k.scopes, k.created_by, "
            f"       u.username AS created_by_username, "
            f"       k.created_at, k.expires_at, k.revoked_at, "
            f"       k.last_used_at, k.rate_limit_per_min "
            f"FROM {self.schema}.api_keys k "
            f"LEFT JOIN {self.schema}.utente u ON u.id = k.created_by "
        )
        if not include_revoked:
            sql += "WHERE k.revoked_at IS NULL "
        sql += "ORDER BY k.created_at DESC"

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql)
                return [dict(r) for r in cur.fetchall()]

    def revoke_api_key(self, key_id: int) -> bool:
        """Marca la chiave come revocata. Idempotente."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE {self.schema}.api_keys "
                    f"SET revoked_at = NOW() "
                    f"WHERE id = %s AND revoked_at IS NULL",
                    (key_id,),
                )
                affected = cur.rowcount
            conn.commit()

        if affected:
            _logger.info("Revocata API key id=%d", key_id)
        return affected > 0

    def validate_api_key(self, plaintext: str) -> Optional[dict]:
        """Verifica una chiave API. Restituisce dict con metadati se valida.

        Aggiorna `last_used_at` come effetto collaterale (best-effort).

        Returns:
            None se la chiave è invalida, scaduta o revocata. Altrimenti:
            ``{id, name, prefix, scopes, created_by, created_by_username,
               rate_limit_per_min}``.
        """
        if not plaintext or not plaintext.startswith(_KEY_PREFIX):
            return None
        key_hash = _hash_key(plaintext)

        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(
                        f"SELECT k.id, k.name, k.prefix, k.scopes, k.created_by, "
                        f"       u.username AS created_by_username, "
                        f"       u.ruolo   AS created_by_ruolo, "
                        f"       k.expires_at, k.revoked_at, k.rate_limit_per_min "
                        f"FROM {self.schema}.api_keys k "
                        f"LEFT JOIN {self.schema}.utente u ON u.id = k.created_by "
                        f"WHERE k.key_hash = %s",
                        (key_hash,),
                    )
                    row = cur.fetchone()
                    if row is None:
                        return None
                    if row["revoked_at"] is not None:
                        return None
                    if row["expires_at"] is not None and row["expires_at"] < datetime.now(
                        row["expires_at"].tzinfo
                    ):
                        return None

                    cur.execute(
                        f"UPDATE {self.schema}.api_keys "
                        f"SET last_used_at = NOW() WHERE id = %s",
                        (row["id"],),
                    )
                conn.commit()

            return {
                "id": row["id"],
                "name": row["name"],
                "prefix": row["prefix"],
                "scopes": list(row["scopes"] or []),
                "created_by": row["created_by"],
                "created_by_username": row["created_by_username"],
                "created_by_ruolo": row["created_by_ruolo"],
                "rate_limit_per_min": row["rate_limit_per_min"],
            }
        except psycopg2.Error as e:
            _logger.warning("validate_api_key: errore DB (%s)", e)
            return None


__all__ = ["DBApiKeysMixin"]
