"""
tests/integration/test_migration_10_drop_tipo_id.py
===================================================
Integration test per lo script di migrazione 10_migrate_drop_tipo_id.sql.
Verifica che la colonna 'tipo_id' venga correttamente rimossa dalla tabella 'localita'.
"""

import os
import sys
import pytest
from pathlib import Path

# Aggiungi la root del progetto al sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


@pytest.mark.integration
@pytest.mark.skip(reason="richiede fixture 'db_connection' non implementata in conftest — da riscrivere")
def test_migration_10_drop_tipo_id(db_connection):
    """
    Testa l'applicazione della migrazione 10_migrate_drop_tipo_id.sql.
    Richiede la fixture 'db_connection' che fornisca una connessione psycopg2 al DB di test.
    """
    cursor = db_connection.cursor()
    
    # 1. Setup dello stato pre-migrazione: crea la tabella (se non esiste) con la colonna obsoleta
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS localita (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(255) NOT NULL,
            tipo_id INTEGER
        );
    """)
    db_connection.commit()
    
    # Verifica che la colonna esista prima di applicare la migrazione
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='localita' AND column_name='tipo_id';
    """)
    assert cursor.fetchone() is not None, "La colonna 'tipo_id' deve esistere prima della migrazione"
    
    # 2. Esegui lo script di migrazione
    migration_path = Path(__file__).parent.parent.parent / "sql_scripts" / "migrations" / "10_migrate_drop_tipo_id.sql"
    with open(migration_path, "r", encoding="utf-8") as f:
        cursor.execute(f.read())
    db_connection.commit()
    
    # 3. Verifica dello stato post-migrazione: la colonna non deve più esistere
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='localita' AND column_name='tipo_id';
    """)
    assert cursor.fetchone() is None, "La colonna 'tipo_id' non è stata rimossa dalla migrazione"
    
    cursor.close()