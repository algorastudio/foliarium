import pytest
import os
import sys

# Aggiungi la directory principale al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from catasto_db_manager import CatastoDBManager

@pytest.fixture(scope="session")
def test_db_setup():
    """Fornisce i parametri di connessione al database di test."""
    return {
        'host': os.environ.get('DB_HOST', 'localhost'),
        'dbname': os.environ.get('DB_NAME', 'catasto_storico'),
        'user': os.environ.get('DB_USER', 'postgres'),
        'password': os.environ.get('DB_PASS', 'testpassword'),
        'port': os.environ.get('DB_PORT', '5432')
    }

@pytest.fixture
def db_manager(test_db_setup):
    """Inizializza il CatastoDBManager con i parametri di test."""
    manager = CatastoDBManager(**test_db_setup)
    
    # QUI LA CORREZIONE: usiamo initialize_main_pool()
    manager.initialize_main_pool() 
    
    yield manager
    
    # Chiude il pool alla fine dei test
    manager.close_pool()

@pytest.fixture
def clean_db(db_manager):
    """Fornisce un database pulito prima di ogni singolo test."""
    with db_manager._get_connection() as conn:
        with conn.cursor() as cur:
            # Svuota le tabelle principali a cascata
            cur.execute("TRUNCATE TABLE catasto.comune CASCADE;")
    return db_manager

@pytest.fixture
def sample_data(clean_db):
    """Fornisce un set di dati di base."""
    from datetime import date
    comune_id = clean_db.aggiungi_comune("Genova Test", "GE", "Liguria")
    possessore1_id = clean_db.create_possessore(
        nome_completo="TEST MARIO", 
        comune_riferimento_id=comune_id, 
        cognome_nome="TEST"
    )
    partita_id = clean_db.create_partita(
        comune_id=comune_id, 
        numero_partita=100, 
        tipo='principale',
        stato='attiva',
        data_impianto=date(1900, 1, 1)
    )
    return {
        'db': clean_db,
        'comune_id': comune_id,
        'possessore1_id': possessore1_id,
        'partita_id': partita_id,
        'localita_id': None 
    }

@pytest.fixture
def temp_csv_file(tmp_path):
    """Crea un file CSV temporaneo per test."""
    file_path = tmp_path / "test_import.csv"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("nome_completo;cognome_nome\n")
        f.write("VERDI GIUSEPPE fu Antonio;VERDI GIUSEPPE\n")
        f.write("NERI LUCIA fu Marco;NERI LUCIA\n")
    return str(file_path)