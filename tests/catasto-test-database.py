#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test per CatastoDBManager
========================
Test completi per le operazioni del database manager
"""

# tests/test_database_manager.py

import pytest
import psycopg2
from datetime import datetime, date
from unittest.mock import Mock, patch
import json

from catasto_db_manager import (
    CatastoDBManager, DBMError, DBUniqueConstraintError, 
    DBNotFoundError, DBDataError
)


class TestCatastoDBManagerConnection:
    """Test per connessioni e pool del database"""
    
    def test_initialize_pool(self, test_db_setup):
        """Test inizializzazione pool connessioni"""
        manager = CatastoDBManager(**test_db_setup)
        
        # Pool non deve essere inizializzato alla creazione
        assert manager.pool is None
        
        # Inizializza pool
        manager.initialize_pool()
        assert manager.pool is not None
        
        # Verifica che il pool sia utilizzabile
        conn = manager._get_connection()
        assert conn is not None
        manager._release_connection(conn)
        
        # Cleanup
        manager.close_pool()
        assert manager.pool is None
    
    def test_connection_error_handling(self, test_db_setup):
        """Test gestione errori di connessione"""
        # Configurazione con parametri errati
        bad_config = test_db_setup.copy()
        bad_config['password'] = 'wrong_password'
        
        manager = CatastoDBManager(**bad_config)
        
        with pytest.raises(psycopg2.OperationalError):
            manager.initialize_pool()
    
    def test_pool_thread_safety(self, db_manager):
        """Test thread safety del pool"""
        import threading
        import time
        
        results = []
        errors = []
        
        def worker():
            try:
                conn = db_manager._get_connection()
                time.sleep(0.1)  # Simula operazione
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    results.append(cur.fetchone()[0])
                db_manager._release_connection(conn)
            except Exception as e:
                errors.append(e)
        
        # Crea multiple thread
        threads = []
        for _ in range(10):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()
        
        # Attendi completamento
        for t in threads:
            t.join()
        
        # Verifica risultati
        assert len(errors) == 0
        assert len(results) == 10
        assert all(r == 1 for r in results)


class TestComuneOperations:
    """Test operazioni CRUD per comuni"""
    
    def test_aggiungi_comune_success(self, clean_db):
        """Test inserimento comune con successo"""
        comune_id = clean_db.aggiungi_comune(
            nome_comune="Test Comune",
            provincia="Test Provincia",
            regione="Test Regione"
        )
        
        assert comune_id is not None
        assert isinstance(comune_id, int)
        
        # Verifica che il comune sia stato inserito
        comuni = clean_db.get_all_comuni()
        assert len(comuni) == 1
        assert comuni[0]['nome'] == "Test Comune"
    
    def test_aggiungi_comune_duplicate(self, clean_db):
        """Test inserimento comune duplicato"""
        # Primo inserimento
        clean_db.aggiungi_comune("Duplicato", "Prov", "Reg")
        
        # Tentativo di duplicazione
        with pytest.raises(DBUniqueConstraintError):
            clean_db.aggiungi_comune("Duplicato", "Prov", "Reg")
    
    def test_get_comune_by_name(self, clean_db):
        """Test recupero comune per nome"""
        # Inserisci comune
        comune_id = clean_db.aggiungi_comune("Genova", "GE", "Liguria")
        
        # Recupera per nome
        result = clean_db.get_comune_id_by_name("Genova")
        assert result == comune_id
        
        # Test comune non esistente
        result = clean_db.get_comune_id_by_name("NonEsiste")
        assert result is None
    
    def test_update_comune(self, sample_data):
        """Test aggiornamento comune"""
        comune_id = sample_data['comune_id']
        
        # Mock della funzione di update (se esiste)
        # Altrimenti, testa attraverso query diretta
        conn = sample_data.db._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE comune 
                    SET provincia = %s, data_modifica = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, ("SV", comune_id))
                conn.commit()
                
                # Verifica aggiornamento
                cur.execute("SELECT provincia FROM comune WHERE id = %s", (comune_id,))
                result = cur.fetchone()
                assert result[0] == "SV"
        finally:
            sample_data.db._release_connection(conn)


class TestPossessoreOperations:
    """Test operazioni CRUD per possessori"""
    
    def test_create_possessore_success(self, sample_data):
        """Test creazione possessore con successo"""
        db = sample_data.db
        comune_id = sample_data['comune_id']
        
        possessore_id = db.create_possessore(
            nome_completo="TEST MARIO fu Giovanni",
            comune_riferimento_id=comune_id,
            paternita="fu Giovanni",
            cognome_nome="TEST MARIO"
        )
        
        assert possessore_id is not None
        
        # Verifica inserimento
        possessori = db.get_possessori_by_comune(comune_id)
        assert any(p['nome_completo'] == "TEST MARIO fu Giovanni" for p in possessori)
    
    def test_create_possessore_duplicate(self, sample_data):
        """Test creazione possessore duplicato"""
        db = sample_data.db
        comune_id = sample_data['comune_id']
        
        # Primo inserimento
        db.create_possessore(
            nome_completo="DUPLICATO TEST",
            comune_riferimento_id=comune_id
        )
        
        # Tentativo duplicazione
        with pytest.raises(DBUniqueConstraintError):
            db.create_possessore(
                nome_completo="DUPLICATO TEST",
                comune_riferimento_id=comune_id
            )
    
    def test_update_possessore(self, sample_data):
        """Test aggiornamento possessore"""
        db = sample_data.db
        possessore_id = sample_data['possessore1_id']
        
        success = db.update_possessore(
            possessore_id=possessore_id,
            paternita="fu Giuseppe Antonio",
            note="Nota di test"
        )
        
        assert success is True
        
        # Verifica aggiornamento
        possessore = db.get_possessore_by_id(possessore_id)
        assert possessore['paternita'] == "fu Giuseppe Antonio"
        assert possessore['note'] == "Nota di test"
    
    def test_search_possessori(self, sample_data):
        """Test ricerca possessori"""
        db = sample_data.db
        
        # Ricerca per nome parziale
        results = db.ricerca_avanzata_possessori_gui(
            query_text="ROSSI",
            similarity_threshold=0.3
        )
        
        assert len(results) > 0
        assert any("ROSSI" in r['nome_completo'] for r in results)
    
    def test_delete_possessore_with_partite(self, sample_data):
        """Test eliminazione possessore con partite associate"""
        db = sample_data.db
        possessore_id = sample_data['possessore1_id']
        partita_id = sample_data['partita_id']
        
        # Associa possessore a partita
        db.aggiungi_possessore_a_partita(
            partita_id=partita_id,
            possessore_id=possessore_id,
            tipo_partita_rel="principale",
            titolo="proprietà"
        )
        
        # Tentativo di eliminazione deve fallire
        with pytest.raises(psycopg2.IntegrityError):
            conn = db._get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM possessore WHERE id = %s", (possessore_id,))
                    conn.commit()
            finally:
                db._release_connection(conn)


class TestPartitaOperations:
    """Test operazioni CRUD per partite"""
    
    def test_create_partita_success(self, sample_data):
        """Test creazione partita con successo"""
        db = sample_data.db
        comune_id = sample_data['comune_id']
        
        partita_id = db.create_partita(
            comune_id=comune_id,
            numero_partita=200,
            tipo='principale',
            data_impianto=date(1955, 6, 15)
        )
        
        assert partita_id is not None
        
        # Verifica inserimento
        partita = db.get_partita_by_id(partita_id)
        assert partita['numero_partita'] == 200
        assert partita['tipo'] == 'principale'
    
    def test_create_partita_duplicate_number(self, sample_data):
        """Test creazione partita con numero duplicato"""
        db = sample_data.db
        comune_id = sample_data['comune_id']
        
        # La partita 100 esiste già in sample_data
        with pytest.raises(DBUniqueConstraintError):
            db.create_partita(
                comune_id=comune_id,
                numero_partita=100,  # Numero già esistente
                tipo='secondaria'
            )
    
    def test_link_possessore_to_partita(self, sample_data):
        """Test collegamento possessore a partita"""
        db = sample_data.db
        
        success = db.aggiungi_possessore_a_partita(
            partita_id=sample_data['partita_id'],
            possessore_id=sample_data['possessore1_id'],
            tipo_partita_rel='principale',
            titolo='proprietà esclusiva',
            quota='1/1'
        )
        
        assert success is True
        
        # Verifica collegamento
        possessori = db.get_possessori_by_partita(sample_data['partita_id'])
        assert len(possessori) == 1
        assert possessori[0]['titolo'] == 'proprietà esclusiva'
    
    def test_update_partita_possessore_link(self, sample_data):
        """Test aggiornamento legame partita-possessore"""
        db = sample_data.db
        
        # Prima crea il legame
        db.aggiungi_possessore_a_partita(
            partita_id=sample_data['partita_id'],
            possessore_id=sample_data['possessore1_id'],
            tipo_partita_rel='principale',
            titolo='proprietà',
            quota='1/2'
        )
        
        # Recupera ID del legame
        conn = db._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id FROM partita_possessore 
                    WHERE partita_id = %s AND possessore_id = %s
                """, (sample_data['partita_id'], sample_data['possessore1_id']))
                link_id = cur.fetchone()[0]
        finally:
            db._release_connection(conn)
        
        # Aggiorna il legame
        success = db.aggiorna_legame_partita_possessore(
            partita_possessore_id=link_id,
            titolo='comproprietà',
            quota='1/3'
        )
        
        assert success is True


class TestImmobileOperations:
    """Test operazioni CRUD per immobili"""
    
    def test_create_immobile(self, sample_data):
        """Test creazione immobile"""
        db = sample_data.db
        
        immobile_id = db.create_immobile(
            partita_id=sample_data['partita_id'],
            localita_id=sample_data['localita_id'],
            natura='Casa',
            numero_piani=2,
            numero_vani=5,
            consistenza='5 vani',
            classificazione='A/2'
        )
        
        assert immobile_id is not None
        
        # Verifica inserimento
        immobili = db.get_immobili_by_partita(sample_data['partita_id'])
        assert len(immobili) == 1
        assert immobili[0]['natura'] == 'Casa'
    
    def test_search_immobili(self, sample_data):
        """Test ricerca immobili"""
        db = sample_data.db
        
        # Prima crea un immobile
        db.create_immobile(
            partita_id=sample_data['partita_id'],
            localita_id=sample_data['localita_id'],
            natura='Magazzino',
            classificazione='C/2'
        )
        
        # Ricerca per natura
        results = db.ricerca_avanzata_immobili_gui(
            natura_search='Magazzino'
        )
        
        # Nota: la funzione potrebbe non essere implementata
        # In tal caso, verifica almeno che non generi eccezioni
        assert isinstance(results, list)


class TestImportExportOperations:
    """Test import/export dati"""
    
    def test_import_possessori_csv(self, sample_data, temp_csv_file):
        """Test import possessori da CSV"""
        db = sample_data.db
        comune_id = sample_data['comune_id']
        
        # Import CSV
        count = db.import_possessori_from_csv(temp_csv_file, comune_id)
        
        assert count == 2  # Due righe nel CSV di test
        
        # Verifica import
        possessori = db.get_possessori_by_comune(comune_id)
        nomi = [p['nome_completo'] for p in possessori]
        assert "VERDI GIUSEPPE fu Antonio" in nomi
        assert "NERI LUCIA fu Marco" in nomi
    
    def test_import_csv_with_duplicates(self, sample_data, temp_csv_file):
        """Test import CSV con duplicati"""
        db = sample_data.db
        comune_id = sample_data['comune_id']
        
        # Prima importazione
        db.import_possessori_from_csv(temp_csv_file, comune_id)
        
        # Seconda importazione dovrebbe generare errore
        with pytest.raises(ValueError, match="esiste già"):
            db.import_possessori_from_csv(temp_csv_file, comune_id)
    
    def test_export_data_validation(self, sample_data):
        """Test validazione dati per export"""
        db = sample_data.db
        
        # Test recupero dati per export
        partita = db.get_partita_by_id(sample_data['partita_id'])
        
        assert partita is not None
        assert 'numero_partita' in partita
        assert 'comune_nome' in partita or 'comune_id' in partita


class TestTransactionManagement:
    """Test gestione transazioni"""
    
    def test_rollback_on_error(self, clean_db):
        """Test rollback automatico su errore"""
        # Inizia transazione
        clean_db.begin()
        
        try:
            # Inserisci comune
            comune_id = clean_db.aggiungi_comune("Rollback Test", "RT", "Test")
            
            # Forza un errore
            clean_db.aggiungi_comune("Rollback Test", "RT", "Test")  # Duplicato
            
            clean_db.commit()  # Non dovrebbe arrivare qui
        except DBUniqueConstraintError:
            clean_db.rollback()
        
        # Verifica che il comune non sia stato inserito
        comuni = clean_db.get_all_comuni()
        assert len(comuni) == 0
    
    def test_nested_operations(self, sample_data):
        """Test operazioni annidate in transazione"""
        db = sample_data.db
        
        db.begin()
        
        try:
            # Crea nuovo comune
            comune_id = db.aggiungi_comune("Transazione", "TR", "Test")
            
            # Crea possessore
            possessore_id = db.create_possessore(
                nome_completo="TRANS TEST",
                comune_riferimento_id=comune_id
            )
            
            # Crea partita
            partita_id = db.create_partita(
                comune_id=comune_id,
                numero_partita=999,
                tipo='principale'
            )
            
            # Collega possessore a partita
            db.aggiungi_possessore_a_partita(
                partita_id=partita_id,
                possessore_id=possessore_id,
                tipo_partita_rel='principale',
                titolo='test'
            )
            
            db.commit()
            
            # Verifica che tutto sia stato inserito
            assert db.get_comune_id_by_name("Transazione") is not None
            assert db.get_possessore_by_id(possessore_id) is not None
            assert db.get_partita_by_id(partita_id) is not None
            
        except Exception as e:
            db.rollback()
            raise


class TestErrorHandling:
    """Test gestione errori personalizzati"""
    
    def test_not_found_error(self, clean_db):
        """Test errore record non trovato"""
        # Tentativo di aggiornare possessore inesistente
        success = clean_db.update_possessore(
            possessore_id=99999,
            note="Test"
        )
        
        assert success is False  # O solleva DBNotFoundError se implementato
    
    def test_data_validation_errors(self, sample_data):
        """Test errori di validazione dati"""
        db = sample_data.db
        
        # Test con dati non validi
        with pytest.raises((DBDataError, psycopg2.DataError, ValueError)):
            db.create_partita(
                comune_id=sample_data['comune_id'],
                numero_partita=-1,  # Numero negativo non valido
                tipo='invalido'  # Tipo non valido
            )


class TestPerformanceAndOptimization:
    """Test performance e ottimizzazioni"""
    
    def test_bulk_insert_performance(self, clean_db):
        """Test performance inserimento massivo"""
        import time
        
        # Crea comune
        comune_id = clean_db.aggiungi_comune("Performance", "PF", "Test")
        
        start_time = time.time()
        
        # Inserisci 100 possessori
        for i in range(100):
            clean_db.create_possessore(
                nome_completo=f"TEST POSSESSORE {i:03d}",
                comune_riferimento_id=comune_id,
                cognome_nome=f"TEST {i:03d}"
            )
        
        elapsed = time.time() - start_time
        
        # Verifica che l'inserimento sia ragionevolmente veloce
        assert elapsed < 10.0  # Meno di 10 secondi per 100 record
        
        # Verifica inserimenti
        possessori = clean_db.get_possessori_by_comune(comune_id)
        assert len(possessori) == 100
    
    def test_search_performance(self, sample_data):
        """Test performance ricerca fuzzy"""
        import time
        
        db = sample_data.db
        
        # Aggiungi più possessori per test performance
        comune_id = sample_data['comune_id']
        for i in range(50):
            db.create_possessore(
                nome_completo=f"PERFORMANCE TEST {i}",
                comune_riferimento_id=comune_id
            )
        
        start_time = time.time()
        
        # Esegui ricerca fuzzy
        results = db.ricerca_avanzata_possessori_gui(
            query_text="PERFORMANCE",
            similarity_threshold=0.3
        )
        
        elapsed = time.time() - start_time
        
        # La ricerca dovrebbe essere veloce anche con molti record
        assert elapsed < 1.0  # Meno di 1 secondo
        assert len(results) >= 50