#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
catasto_db_manager.py — Facade per CatastoDBManager.

La logica è ora distribuita in mixin specializzati nel package db/:
  db/base.py        — DBConnectionBase  (pool, connessione, cache)
  db/comuni.py      — DBComuniMixin
  db/localita.py    — DBLocalitaMixin
  db/possessori.py  — DBPossessoriMixin
  db/partite.py     — DBPartiteMixin
  db/immobili.py    — DBImmobiliMixin
  db/variazioni.py  — DBVariazioniMixin
  db/ricerca.py     — DBSearchMixin
  db/audit.py       — DBAuditMixin
  db/utenti.py      — DBUtentiMixin
  db/backup.py      — DBBackupMixin
  db/documenti.py   — DBDocumentiMixin
  db/stats.py       — DBStatsMixin
  db/io.py          — DBIOMixin

Backward compatibility: tutti gli import esistenti funzionano invariati.
"""

# ── Re-export eccezioni (backward compat) ──────────────────────────────────
from catasto_exceptions import (           # noqa: F401
    DBMError,
    DBUniqueConstraintError,
    DBNotFoundError,
    DBDataError,
)

# ── Costanti globali (backward compat) ─────────────────────────────────────
COLONNE_POSSESSORI_DETTAGLI_NUM    = 6
COLONNE_POSSESSORI_DETTAGLI_LABELS = ["ID Poss.", "Nome Completo", "Cognome Nome", "Paternità", "Quota", "Titolo"]

# ── Mixin imports ───────────────────────────────────────────────────────────
from db.base       import DBConnectionBase
from db.comuni     import DBComuniMixin
from db.localita   import DBLocalitaMixin
from db.possessori import DBPossessoriMixin
from db.partite    import DBPartiteMixin
from db.immobili   import DBImmobiliMixin
from db.variazioni import DBVariazioniMixin
from db.ricerca    import DBSearchMixin
from db.audit      import DBAuditMixin
from db.utenti     import DBUtentiMixin
from db.backup     import DBBackupMixin
from db.documenti  import DBDocumentiMixin
from db.stats      import DBStatsMixin
from db.io         import DBIOMixin
from db.archivio   import DBArchiviaMixin


class CatastoDBManager(
    DBArchiviaMixin,
    DBComuniMixin,
    DBLocalitaMixin,
    DBPossessoriMixin,
    DBPartiteMixin,
    DBImmobiliMixin,
    DBVariazioniMixin,
    DBSearchMixin,
    DBAuditMixin,
    DBUtentiMixin,
    DBBackupMixin,
    DBDocumentiMixin,
    DBStatsMixin,
    DBIOMixin,
    DBConnectionBase,
):
    """
    Gestore database catastale.

    Compone tutti i mixin specializzati (db/*.py) con DBConnectionBase.
    Ogni istanza ha accesso all'intera API tramite ereditarietà multipla.
    """
    pass
