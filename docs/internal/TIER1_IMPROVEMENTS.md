# TIER 1 Improvements — Guida Implementazione

Questo documento spiega come usare i 4 nuovi componenti TIER 1 nel codebase Foliarium.

**Stato**: ✅ Completato (commit 2d7fd84, 76a5464, ca076cc, 3c2288c)

---

## 📦 1. Dataclass Models (`db/models.py`)

### Cosa è
Dataclass Python per mapping type-safe di DB rows → Python objects.

### Quando usare
Quando vuoi che il codice che chiama la query conosca i campi disponibili (IDE hints + static type checking).

### Come usare

**Prima** (type-unsafe):
```python
def get_partita(self, partita_id: int) -> Optional[Dict]:
    with self._get_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(f"SELECT * FROM {self.schema}.partita WHERE id = %s", (partita_id,))
            return cur.fetchone()

# Uso
row = db.get_partita(123)
print(row['numero_partita'])  # Typo risk: row['numero_partita'] vs row['numero']
```

**Dopo** (type-safe):
```python
from db.models import Partita

def get_partita(self, partita_id: int) -> Optional[Partita]:
    with self._get_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(f"SELECT * FROM {self.schema}.partita WHERE id = %s", (partita_id,))
            row = cur.fetchone()
            if row:
                return Partita(**row)  # Unpack dict → dataclass
            return None

# Uso
partita = db.get_partita(123)
print(partita.numero_partita)  # IDE knows this attribute exists ✓
```

### Modelli disponibili
- `Partita` — partita catastale
- `Possessore` — proprietario
- `Localita` — via, piazza, etc.
- `Immobile` — fabbricato, terreno
- `Variazione` — eredità, fusione, etc.
- `Documento` — allegato partita
- `Utente` — user app
- `Comune` — comune italiano

### Zero Runtime Cost
Dataclass è pura sintassi Python — niente overhead (in Python 3.10+ è ottimizzato a C).

---

## 🛡️ 2. Error Handler Decorator (`@db_handle_errors`)

### Cosa è
Decorator che centralizza exception handling e traduce errori psycopg2 → custom exceptions.

### Quando usare
Su **tutti** i metodi DB che accedono il database per evitare try-except ripetuti.

### Come usare

**Prima** (boilerplate):
```python
def get_partita_by_numero(self, numero: int, comune_id: int) -> Optional[Dict]:
    try:
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(
                    f"SELECT * FROM {self.schema}.partita WHERE numero_partita = %s AND comune_id = %s",
                    (numero, comune_id)
                )
                return cur.fetchone()
    except psycopg2.errors.UniqueViolation as e:
        self.logger.error(f"Unique constraint: {e}")
        raise DBUniqueConstraintError(str(e)) from e
    except psycopg2.errors.OperationalError as e:
        self.logger.error(f"DB unreachable: {e}")
        raise DBMError("Database unreachable") from e
    except Exception as e:
        self.logger.error(f"Unexpected error: {e}", exc_info=True)
        raise
```

**Dopo** (clean):
```python
@db_handle_errors
def get_partita_by_numero(self, numero: int, comune_id: int) -> Optional[Dict]:
    with self._get_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                f"SELECT * FROM {self.schema}.partita WHERE numero_partita = %s AND comune_id = %s",
                (numero, comune_id)
            )
            return cur.fetchone()
```

### Cattura questi errori
- `UniqueViolation` → `DBUniqueConstraintError`
- `OperationalError` → `DBMError` (+ log in `self.last_connection_error`)
- `DataError` → `DBDataError`
- `ForeignKeyViolation` → `DBMError`

---

## 🚀 3. Bulk Insert Helper (`bulk_insert_with_savepoint()`)

### Cosa è
Generalizzazione del pattern SAVEPOINT usato in 5+ metodi per import CSV.

### Quando usare
Quando vuoi inserire >10 record fault-tolerantly (uno fallisce, altri continuano).

### Come usare

**Prima** (duplicato):
```python
def import_partite_from_csv(self, records: List[Dict]) -> Dict[str, list]:
    success = []
    errors = []
    
    try:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                for i, record in enumerate(records):
                    line_num = i + 2
                    cur.execute("SAVEPOINT record_sp")
                    try:
                        numero = int(record['numero_partita'])
                        cur.execute(
                            f"INSERT INTO {self.schema}.partita (numero_partita, stato) VALUES (%s, %s)",
                            (numero, record.get('stato', 'Attiva'))
                        )
                        success.append(record)
                    except Exception as e:
                        cur.execute("ROLLBACK TO SAVEPOINT record_sp")
                        errors.append({"row": line_num, "error": str(e), "data": record})
                conn.commit()
    except Exception as e:
        self.logger.error(f"bulk import failed: {e}", exc_info=True)
        raise
    
    return {"success": success, "errors": errors}
```

**Dopo** (1 line):
```python
def import_partite_from_csv(self, records: List[Dict]) -> Dict[str, list]:
    return self.bulk_insert_with_savepoint("partita", records)
```

### Firma
```python
def bulk_insert_with_savepoint(
    self,
    table: str,
    records: List[Dict[str, Any]],
    check_unique: Optional[Tuple[str, ...]] = None
) -> Dict[str, Any]:
    """
    Returns: {
        "success": [record, ...],
        "errors": [{"row": line_num, "error": msg, "data": record}, ...]
    }
    """
```

### Mixin che potrebbero beneficiarne
- `db/io.py` — `import_partite_from_xlsx()`, `import_localita_from_rows()`
- `db/comuni.py` — bulk insert comuni
- `db/possessori.py` — bulk import possessori
- `db/documenti.py` — batch insert documenti

---

## 🏷️ 4. Query Tagging (`_tag_query()`)

### Cosa è
Prepend SQL comment con metodo + azione per debugging con `pg_stat_statements`.

### Quando usare
Su query critiche / lente per tracciare source in production.

### Come usare

```python
@db_handle_errors
def get_partite_by_comune(self, comune_id: int, limit: int = 100) -> List[Dict]:
    query = self._tag_query(
        f"SELECT * FROM {self.schema}.partita WHERE comune_id = %s LIMIT %s",
        method_name="get_partite_by_comune",
        action="read"
    )
    with self._get_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(query, (comune_id, limit))
            return cur.fetchall()
```

**Risultato SQL eseguito**:
```sql
/* get_partite_by_comune:read */ SELECT * FROM public.partita WHERE comune_id = %s LIMIT %s
```

### In pg_stat_statements
```sql
SELECT query, calls, mean_time FROM pg_stat_statements 
WHERE query LIKE '%get_partite_by_comune%'
ORDER BY mean_time DESC;
```

Mostra exactamente quale metodo Python ha generato la query.

---

## 📚 Safe SQL Query Builder (`db/sql_builder.py`)

### Cosa è
Query builder (non ORM) che usa `psycopg2.sql` per prevenir SQL injection.

### Quando usare
Su query custom dove non vuoi string concatenation.

### Come usare

```python
from db.sql_builder import SafeQuery

# INSERT
query = SafeQuery.insert("partita", ["numero_partita", "stato"])
cur.execute(query, (123, "Attiva"))

# SELECT
query = SafeQuery.select(["id", "numero_partita", "stato"], "partita")
full_query = sql.SQL("{} WHERE comune_id = %s").format(query)
cur.execute(full_query, (5,))

# WHERE clause
where_sql, values = SafeQuery.where_clause({
    "numero_partita": 123,
    "stato": "Attiva"
})
full_query = sql.SQL("SELECT * FROM partita WHERE {}").format(where_sql)
cur.execute(full_query, tuple(values))

# UPDATE
query = SafeQuery.update("partita", ["stato", "data_modifica"])
full_query = sql.SQL("{} WHERE id = %s").format(query)
cur.execute(full_query, ("Inattiva", datetime.now(), 123))

# DELETE
query = SafeQuery.delete("partita")
full_query = sql.SQL("{} WHERE id = %s").format(query)
cur.execute(full_query, (123,))
```

### Benefici vs raw SQL strings
```python
# ❌ BAD — SQL injection risk
table = request.form['table']  # Could be "partita; DROP TABLE ..."
cur.execute(f"SELECT * FROM {table}")

# ✅ GOOD — Safe
table = "partita"
query = SafeQuery.select(["*"], table)
cur.execute(query)
```

---

## 🎯 Integration Checklist

### Fase 1: Models (opt-in, graduale)
- [ ] Convert 5 high-value methods in `db/partite.py` to return `Partita` instead of `Dict`
- [ ] Convert 3 methods in `db/possessori.py` to return `Possessore`
- [ ] Convert 2 methods in `db/localita.py` to return `Localita`
- [ ] Update call sites to use `.attribute` instead of `['key']`

### Fase 2: Error Decorator (graduale)
- [ ] Apply `@db_handle_errors` to 10 methods in `db/partite.py`
- [ ] Remove try-except blocks from these methods
- [ ] Apply to `db/possessori.py` (5-10 methods)
- [ ] Test that error handling still works as before

### Fase 3: Bulk Insert Helper (immediate)
- [ ] Replace bulk insert in `db/io.py` with `bulk_insert_with_savepoint()`
- [ ] Verify test suite passes
- [ ] Replace in `db/comuni.py` if used
- [ ] Replace in `db/documenti.py` if used

### Fase 4: Query Tagging (opt-in, low priority)
- [ ] Add `_tag_query()` to 5-10 critical/slow queries
- [ ] Enable `FOLIARIUM_PROFILE=1` in dev for testing
- [ ] Review `pg_stat_statements` output

### Fase 5: SafeQuery Builder (future)
- [ ] Review current raw SQL in 5 methods
- [ ] Replace string concatenation with SafeQuery builders
- [ ] Verify injection protection in test

---

## 💡 Best Practices

### 1. Combine Decorator + Models + Type Hints
```python
from db.models import Partita
from functools import wraps

@db_handle_errors
def get_partita(self, partita_id: int) -> Optional[Partita]:
    """Type-safe, error-safe, clean."""
    with self._get_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(f"SELECT * FROM {self.schema}.partita WHERE id = %s", (partita_id,))
            row = cur.fetchone()
            return Partita(**row) if row else None
```

### 2. Use Bulk Insert for CSV Imports
```python
@db_handle_errors
def import_partite_csv(self, csv_file: str) -> Dict:
    """Import CSV with per-row error isolation."""
    records = self._read_csv(csv_file)
    return self.bulk_insert_with_savepoint("partita", records)
```

### 3. Tag Slow Queries
```python
@db_handle_errors
def get_partite_fuzzy_search(self, query: str) -> List[Partita]:
    """Search with fuzzy matching."""
    sql_query = self._tag_query(
        f"SELECT * FROM {self.schema}.partita WHERE numero_partita ILIKE %s",
        method_name="get_partite_fuzzy_search",
        action="search"
    )
    # ... execute and return
```

---

## 📊 Expected Impact

| Improvement | LOC Saved | Type Safety | Readability | Est. Effort |
|-------------|-----------|-------------|-------------|-------------|
| Models | 0 (opt-in) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 2h |
| Error Decorator | 30-40% | ⭐⭐⭐ | ⭐⭐⭐⭐ | 1h |
| Bulk Insert Helper | 80% on bulk ops | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 1.5h |
| Query Tagging | 0 (opt-in) | ⭐⭐ | ⭐⭐⭐ | 0.5h |
| SafeQuery Builder | 20-30% | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 2h |

**Total TIER 1**: ~5 hours work → massive code quality improvement

---

## 🧪 Testing

All TIER 1 improvements tested in `tests/test_tier1_improvements.py`:
```bash
pytest tests/test_tier1_improvements.py -v
```

Run locally before committing changes to mixin methods.

---

## 🚀 Next Steps

After TIER 1 integration complete, consider:

### TIER 2 (4-8 hours)
- Query Performance Profiler
- Schema Version Tracking
- SQL Injection Helper

### TIER 3 (8+ hours, optional)
- Alembic Integration
- Extended Test Coverage
- Connection Health Monitoring

---

**Document Version**: 1.0  
**Last Updated**: 2026-04-22  
**Status**: ✅ Implementation Complete
