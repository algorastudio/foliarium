#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup Test Suite per Sistema Catasto Storico
==========================================
Configurazione base per l'esecuzione dei test
"""

# tests/conftest.py

import pytest
import psycopg2
import tempfile
import os
from datetime import datetime
from unittest.mock import Mock, patch
import logging

# Configurazione per test
TEST_DB_CONFIG = {
    'dbname': 'catasto_test',
    'user': 'catasto_test_user',
    'password': 'test_password',
    'host': 'localhost',
    'port': 5432,
    'schema': 'catasto'
}

# Disabilita logging durante i test
logging.disable(logging.CRITICAL)


@pytest.fixture(scope='session')
def test_db_setup():
    """Setup del database di test - eseguito una volta per sessione"""
    # Connessione come superuser per creare il database di test
    admin_conn = psycopg2.connect(
        dbname='postgres',
        user='postgres',
        password='postgres',  # Modificare secondo configurazione
        host='localhost'
    )
    admin_conn.autocommit = True
    
    with admin_conn.cursor() as cur:
        # Drop database se esiste
        cur.execute(f"DROP DATABASE IF EXISTS {TEST_DB_CONFIG['dbname']}")
        # Crea database di test
        cur.execute(f"CREATE DATABASE {TEST_DB_CONFIG['dbname']}")
        # Crea utente di test se non esiste
        cur.execute(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = '{TEST_DB_CONFIG['user']}') THEN
                    CREATE USER {TEST_DB_CONFIG['user']} WITH PASSWORD '{TEST_DB_CONFIG['password']}';
                END IF;
            END $$;
        """)
        cur.execute(f"GRANT ALL PRIVILEGES ON DATABASE {TEST_DB_CONFIG['dbname']} TO {TEST_DB_CONFIG['user']}")
    
    admin_conn.close()
    
    # Connessione al database di test per creare lo schema
    test_conn = psycopg2.connect(**TEST_DB_CONFIG)
    test_conn.autocommit = True
    
    with test_conn.cursor() as cur:
        # Crea schema
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {TEST_DB_CONFIG['schema']}")
        cur.execute(f"SET search_path TO {TEST_DB_CONFIG['schema']}, public")
        
        # Crea estensioni necessarie
        cur.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
        cur.execute("CREATE EXTENSION IF NOT EXISTS \"pg_trgm\"")
        
        # Esegui script di creazione tabelle (semplificato per test)
        _create_test_tables(cur)
    
    test_conn.close()
    
    yield TEST_DB_CONFIG
    
    # Cleanup
    admin_conn = psycopg2.connect(
        dbname='postgres',
        user='postgres',
        password='postgres',
        host='localhost'
    )
    admin_conn.autocommit = True
    
    with admin_conn.cursor() as cur:
        # Termina connessioni attive
        cur.execute(f"""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = '{TEST_DB_CONFIG['dbname']}'
            AND pid <> pg_backend_pid()
        """)
        # Drop database
        cur.execute(f"DROP DATABASE IF EXISTS {TEST_DB_CONFIG['dbname']}")
    
    admin_conn.close()


def _create_test_tables(cursor):
    """Crea tabelle di test semplificate"""
    # Tabella comune
    cursor.execute("""
        CREATE TABLE comune (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(100) NOT NULL UNIQUE,
            provincia VARCHAR(100) NOT NULL,
            regione VARCHAR(100) NOT NULL,
            data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabella possessore
    cursor.execute("""
        CREATE TABLE possessore (
            id SERIAL PRIMARY KEY,
            comune_id INTEGER REFERENCES comune(id),
            nome_completo VARCHAR(255) NOT NULL,
            cognome_nome VARCHAR(255),
            paternita VARCHAR(255),
            codice_fiscale VARCHAR(16),
            data_nascita DATE,
            attivo BOOLEAN DEFAULT true,
            note TEXT,
            data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(nome_completo, comune_id)
        )
    """)
    
    # Tabella partita
    cursor.execute("""
        CREATE TABLE partita (
            id SERIAL PRIMARY KEY,
            comune_id INTEGER REFERENCES comune(id),
            numero_partita INTEGER NOT NULL,
            tipo VARCHAR(20) CHECK (tipo IN ('principale', 'secondaria')),
            stato VARCHAR(20) DEFAULT 'attiva',
            data_impianto DATE,
            data_chiusura DATE,
            numero_provenienza INTEGER,
            data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(comune_id, numero_partita)
        )
    """)
    
    # Tabella partita_possessore
    cursor.execute("""
        CREATE TABLE partita_possessore (
            id SERIAL PRIMARY KEY,
            partita_id INTEGER REFERENCES partita(id),
            possessore_id INTEGER REFERENCES possessore(id),
            tipo_partita VARCHAR(20),
            titolo VARCHAR(100),
            quota VARCHAR(50),
            data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(partita_id, possessore_id)
        )
    """)
    
    # Tabella localita
    cursor.execute("""
        CREATE TABLE localita (
            id SERIAL PRIMARY KEY,
            comune_id INTEGER REFERENCES comune(id),
            nome VARCHAR(255) NOT NULL,
            tipo VARCHAR(50),
            civico INTEGER,
            data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabella immobile
    cursor.execute("""
        CREATE TABLE immobile (
            id SERIAL PRIMARY KEY,
            partita_id INTEGER REFERENCES partita(id),
            localita_id INTEGER REFERENCES localita(id),
            natura VARCHAR(100),
            numero_piani INTEGER,
            numero_vani INTEGER,
            consistenza VARCHAR(255),
            classificazione VARCHAR(100),
            data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabella variazione
    cursor.execute("""
        CREATE TABLE variazione (
            id SERIAL PRIMARY KEY,
            partita_origine_id INTEGER REFERENCES partita(id),
            partita_destinazione_id INTEGER REFERENCES partita(id),
            tipo VARCHAR(50),
            data_variazione DATE,
            numero_riferimento VARCHAR(50),
            nominativo_riferimento VARCHAR(255),
            data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabella contratto
    cursor.execute("""
        CREATE TABLE contratto (
            id SERIAL PRIMARY KEY,
            variazione_id INTEGER REFERENCES variazione(id),
            tipo VARCHAR(50),
            data_contratto DATE,
            notaio VARCHAR(255),
            repertorio VARCHAR(100),
            note TEXT,
            data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Indici per ricerca fuzzy
    cursor.execute("CREATE INDEX idx_possessore_nome_trgm ON possessore USING gin (nome_completo gin_trgm_ops)")
    cursor.execute("CREATE INDEX idx_possessore_cognome_trgm ON possessore USING gin (cognome_nome gin_trgm_ops)")


@pytest.fixture
def db_manager(test_db_setup):
    """Fixture per CatastoDBManager connesso al database di test"""
    from catasto_db_manager import CatastoDBManager
    
    manager = CatastoDBManager(
        dbname=test_db_setup['dbname'],
        user=test_db_setup['user'],
        password=test_db_setup['password'],
        host=test_db_setup['host'],
        port=test_db_setup['port'],
        schema=test_db_setup['schema']
    )
    
    # Inizializza pool di connessioni
    manager.initialize_pool()
    
    yield manager
    
    # Cleanup
    if manager.pool:
        manager.close_pool()


@pytest.fixture
def clean_db(db_manager):
    """Fixture che pulisce il database prima di ogni test"""
    # Ottieni connessione diretta per pulizia
    conn = db_manager._get_connection()
    
    try:
        with conn.cursor() as cur:
            # Disabilita temporaneamente i constraint
            cur.execute("SET CONSTRAINTS ALL DEFERRED")
            
            # Pulisci tutte le tabelle in ordine inverso di dipendenza
            tables = [
                'contratto', 'variazione', 'immobile', 'partita_possessore',
                'partita', 'localita', 'possessore', 'comune'
            ]
            
            for table in tables:
                cur.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
            
            conn.commit()
    finally:
        db_manager._release_connection(conn)
    
    yield db_manager
    
    # Pulizia dopo il test
    conn = db_manager._get_connection()
    try:
        with conn.cursor() as cur:
            for table in tables:
                cur.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
            conn.commit()
    finally:
        db_manager._release_connection(conn)


@pytest.fixture
def sample_data(clean_db):
    """Fixture che popola il database con dati di esempio"""
    db = clean_db
    
    # Crea comune di esempio
    comune_id = db.aggiungi_comune(
        nome_comune="Carcare",
        provincia="Savona",
        regione="Liguria"
    )
    
    # Crea possessori di esempio
    possessore1_id = db.create_possessore(
        nome_completo="ROSSI MARIO fu Giuseppe",
        comune_riferimento_id=comune_id,
        paternita="fu Giuseppe",
        cognome_nome="ROSSI MARIO"
    )
    
    possessore2_id = db.create_possessore(
        nome_completo="BIANCHI ANNA fu Pietro",
        comune_riferimento_id=comune_id,
        paternita="fu Pietro",
        cognome_nome="BIANCHI ANNA"
    )
    
    # Crea partita di esempio
    partita_id = db.create_partita(
        comune_id=comune_id,
        numero_partita=100,
        tipo='principale',
        data_impianto=datetime(1950, 1, 1).date()
    )
    
    # Crea località di esempio
    conn = db._get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO localita (comune_id, nome, tipo)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (comune_id, "Via Roma", "via"))
            localita_id = cur.fetchone()[0]
            conn.commit()
    finally:
        db._release_connection(conn)
    
    return {
        'comune_id': comune_id,
        'possessore1_id': possessore1_id,
        'possessore2_id': possessore2_id,
        'partita_id': partita_id,
        'localita_id': localita_id
    }


@pytest.fixture
def mock_file_dialog(monkeypatch):
    """Mock per QFileDialog"""
    mock = Mock()
    mock.getOpenFileName.return_value = ('/path/to/file.csv', 'CSV Files (*.csv)')
    mock.getSaveFileName.return_value = ('/path/to/output.pdf', 'PDF Files (*.pdf)')
    monkeypatch.setattr('PyQt6.QtWidgets.QFileDialog', mock)
    return mock


@pytest.fixture
def temp_csv_file():
    """Crea un file CSV temporaneo per test import"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        f.write("cognome_nome,nome_completo,paternita\n")
        f.write("VERDI GIUSEPPE,VERDI GIUSEPPE fu Antonio,fu Antonio\n")
        f.write("NERI LUCIA,NERI LUCIA fu Marco,fu Marco\n")
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


# Helper per creare mock di PyQt widgets
class MockQWidget:
    def __init__(self):
        self.parent_widget = None
        self.enabled = True
        
    def setEnabled(self, enabled):
        self.enabled = enabled
        
    def isEnabled(self):
        return self.enabled
        
    def parent(self):
        return self.parent_widget


class MockQMessageBox:
    """Mock per QMessageBox"""
    Yes = 1
    No = 0
    
    @staticmethod
    def question(parent, title, message, buttons=None, default=None):
        return MockQMessageBox.Yes
    
    @staticmethod
    def information(parent, title, message):
        pass
    
    @staticmethod
    def warning(parent, title, message):
        pass
    
    @staticmethod
    def critical(parent, title, message):
        pass