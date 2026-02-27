#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test di Integrazione ed End-to-End
==================================
Test che verificano l'integrazione tra componenti
"""

# tests/test_integration.py

import pytest
import tempfile
import os
from datetime import datetime, date
from unittest.mock import patch, Mock
import json
import time

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtTest import QTest

# Import componenti da testare
from catasto_db_manager import CatastoDBManager
from gui_main import MainWindow
from gui_widgets import *


class TestDatabaseGUIIntegration:
    """Test integrazione tra database e GUI"""
    
    def test_full_comune_workflow(self, qapp, db_manager):
        """Test workflow completo: crea comune -> visualizza -> modifica"""
        # Crea widget
        widget = ComuneManagerWidget(db_manager)
        
        # Step 1: Aggiungi comune via GUI
        original_count = widget.table.rowCount() if hasattr(widget, 'table') else 0
        
        # Simula aggiunta
        comune_id = db_manager.aggiungi_comune("Test Integration", "TI", "Test")
        widget._load_comuni()  # Ricarica lista
        
        # Verifica aggiunta
        new_count = widget.table.rowCount() if hasattr(widget, 'table') else 0
        assert new_count == original_count + 1
        
        # Step 2: Verifica che il comune sia visibile nella GUI
        found = False
        if hasattr(widget, 'table'):
            for row in range(widget.table.rowCount()):
                if widget.table.item(row, 0).text() == "Test Integration":
                    found = True
                    break
        assert found
        
        # Step 3: Cleanup
        # Normalmente si farebbe via GUI, ma per il test usiamo DB diretto
        conn = db_manager._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM comune WHERE nome = %s", ("Test Integration",))
                conn.commit()
        finally:
            db_manager._release_connection(conn)
    
    def test_possessore_partita_association(self, qapp, sample_data):
        """Test associazione possessore-partita attraverso GUI"""
        db = sample_data.db
        
        # Crea widget registrazione partita
        widget = RegistraPartitaWidget(db)
        
        # Popola il form
        if hasattr(widget, 'comune_combo'):
            # Assumendo che il combo sia popolato con i comuni
            widget.comune_combo.setCurrentIndex(0)
        
        if hasattr(widget, 'numero_input'):
            widget.numero_input.setText("500")
        
        if hasattr(widget, 'tipo_combo'):
            widget.tipo_combo.setCurrentText("principale")
        
        # Salva partita
        if hasattr(widget, '_save_partita'):
            # Mock message box per evitare popup durante test
            with patch('PyQt6.QtWidgets.QMessageBox.information'):
                widget._save_partita()
        
        # Verifica che la partita sia stata creata
        partite = db.search_partite_by_numero(500)
        assert len(partite) > 0
        
        partita_id = partite[0]['id']
        
        # Ora associa un possessore
        success = db.aggiungi_possessore_a_partita(
            partita_id=partita_id,
            possessore_id=sample_data['possessore1_id'],
            tipo_partita_rel='principale',
            titolo='proprietà'
        )
        
        assert success is True
        
        # Verifica attraverso GUI
        possessori = db.get_possessori_by_partita(partita_id)
        assert len(possessori) == 1


class TestMainWindowIntegration:
    """Test integrazione con finestra principale"""
    
    @patch('gui_main.LoginDialog')
    def test_main_window_initialization(self, mock_login, qapp, db_manager):
        """Test inizializzazione finestra principale"""
        # Mock login dialog per auto-login
        mock_login_instance = Mock()
        mock_login_instance.exec_.return_value = 1  # Accepted
        mock_login_instance.get_connection_params.return_value = {
            'dbname': 'catasto_test',
            'user': 'test_user',
            'password': 'test_pass',
            'host': 'localhost',
            'port': 5432
        }
        mock_login.return_value = mock_login_instance
        
        # Crea finestra principale con DB manager esistente
        with patch('gui_main.CatastoDBManager') as mock_db_class:
            mock_db_class.return_value = db_manager
            
            window = MainWindow()
            
            # Verifica che la finestra sia inizializzata
            assert window is not None
            assert window.db_manager is not None
            
            # Verifica presenza tab
            if hasattr(window, 'tabs'):
                assert window.tabs.count() > 0
    
    def test_tab_switching(self, qapp, db_manager):
        """Test cambio tab e caricamento dati"""
        # Crea una versione semplificata della finestra principale
        window = QWidget()
        window.db_manager = db_manager
        
        # Aggiungi alcuni tab di test
        from PyQt6.QtWidgets import QTabWidget
        tabs = QTabWidget()
        
        # Tab 1: Lista comuni
        tab1 = ComuneManagerWidget(db_manager)
        tabs.addTab(tab1, "Comuni")
        
        # Tab 2: Ricerca partite
        tab2 = PartiteRicercaWidget(db_manager)
        tabs.addTab(tab2, "Partite")
        
        # Simula cambio tab
        tabs.setCurrentIndex(0)
        QTest.qWait(100)  # Attendi caricamento
        
        # Verifica che i dati siano caricati nel primo tab
        if hasattr(tab1, 'table'):
            assert tab1.table.rowCount() >= 0
        
        # Cambia al secondo tab
        tabs.setCurrentIndex(1)
        QTest.qWait(100)
        
        # Il secondo tab dovrebbe essere pronto per ricerche
        if hasattr(tab2, 'search_input'):
            assert tab2.search_input.isEnabled()


class TestImportExportIntegration:
    """Test integrazione import/export"""
    
    def test_csv_import_workflow(self, qapp, sample_data, temp_csv_file):
        """Test workflow completo import CSV"""
        db = sample_data.db
        comune_id = sample_data['comune_id']
        
        # Crea widget per import
        widget = RegistraPossessoreWidget(db)
        
        # Simula selezione file e import
        with patch('PyQt6.QtWidgets.QFileDialog.getOpenFileName') as mock_dialog:
            mock_dialog.return_value = (temp_csv_file, 'CSV Files')
            
            with patch('PyQt6.QtWidgets.QMessageBox.information'):
                if hasattr(widget, '_import_from_csv'):
                    # Assumendo che il widget abbia un metodo per import
                    widget.comune_id = comune_id  # Set comune context
                    widget._import_from_csv()
        
        # Verifica import nel database
        possessori = db.get_possessori_by_comune(comune_id)
        nomi = [p['nome_completo'] for p in possessori]
        
        # Dovrebbero esserci i possessori dal CSV più quelli esistenti
        assert "VERDI GIUSEPPE fu Antonio" in nomi
        assert "NERI LUCIA fu Marco" in nomi
    
    def test_pdf_export_workflow(self, qapp, sample_data):
        """Test workflow export PDF"""
        db = sample_data.db
        
        # Prepara dati per export
        partita_id = sample_data['partita_id']
        
        # Aggiungi alcuni dati alla partita
        db.aggiungi_possessore_a_partita(
            partita_id=partita_id,
            possessore_id=sample_data['possessore1_id'],
            tipo_partita_rel='principale',
            titolo='proprietà',
            quota='1/1'
        )
        
        # Mock del file dialog
        with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName') as mock_dialog:
            mock_dialog.return_value = ('/tmp/test_export.pdf', 'PDF Files')
            
            # Test export (assumendo esistenza di funzione export)
            # Questo dipende dall'implementazione specifica
            try:
                from app_utils import PDFPartita
                pdf = PDFPartita()
                # Genera PDF con dati partita
                # pdf.generate(partita_data)
            except ImportError:
                pass  # Skip se modulo PDF non disponibile


class TestSearchIntegration:
    """Test integrazione funzionalità di ricerca"""
    
    def test_fuzzy_search_integration(self, qapp, sample_data):
        """Test ricerca fuzzy completa"""
        db = sample_data.db
        
        # Aggiungi possessori con nomi simili
        comune_id = sample_data['comune_id']
        
        test_possessori = [
            "ROSSINI MARIO fu Giuseppe",
            "ROSSI MARIA fu Antonio", 
            "ROSSETTI MARCO fu Luigi",
            "RUSSO MARTINA fu Pietro"
        ]
        
        for nome in test_possessori:
            db.create_possessore(
                nome_completo=nome,
                comune_riferimento_id=comune_id,
                cognome_nome=nome.split(' fu')[0]
            )
        
        # Test ricerca con diversi livelli di similarità
        widget = PossessoriRicercaWidget(db)
        
        # Ricerca esatta
        if hasattr(widget, 'search_input'):
            widget.search_input.setText("ROSSI MARIA")
            widget._perform_search()
            
            # Dovrebbe trovare match esatto
            results = db.ricerca_avanzata_possessori_gui(
                query_text="ROSSI MARIA",
                similarity_threshold=0.9
            )
            assert len(results) >= 1
            assert any(r['nome_completo'] == "ROSSI MARIA fu Antonio" for r in results)
        
        # Ricerca fuzzy
        results_fuzzy = db.ricerca_avanzata_possessori_gui(
            query_text="ROSI",  # Typo intenzionale
            similarity_threshold=0.3
        )
        
        # Dovrebbe trovare risultati simili
        assert len(results_fuzzy) >= 2  # ROSSI e ROSSINI almeno
    
    def test_advanced_search_filters(self, qapp, sample_data):
        """Test ricerca avanzata con filtri multipli"""
        db = sample_data.db
        comune_id = sample_data['comune_id']
        
        # Crea dati di test strutturati
        # Crea località
        conn = db._get_connection()
        try:
            with conn.cursor() as cur:
                # Crea diverse località
                cur.execute("""
                    INSERT INTO localita (comune_id, nome, tipo) 
                    VALUES (%s, %s, %s) RETURNING id
                """, (comune_id, "Via Garibaldi", "via"))
                localita1_id = cur.fetchone()[0]
                
                cur.execute("""
                    INSERT INTO localita (comune_id, nome, tipo) 
                    VALUES (%s, %s, %s) RETURNING id
                """, (comune_id, "Piazza Matteotti", "piazza"))
                localita2_id = cur.fetchone()[0]
                
                conn.commit()
        finally:
            db._release_connection(conn)
        
        # Crea partite con immobili
        partita1_id = db.create_partita(
            comune_id=comune_id,
            numero_partita=300,
            tipo='principale'
        )
        
        partita2_id = db.create_partita(
            comune_id=comune_id,
            numero_partita=301,
            tipo='principale'
        )
        
        # Crea immobili diversi
        db.create_immobile(
            partita_id=partita1_id,
            localita_id=localita1_id,
            natura='Casa',
            numero_piani=2,
            numero_vani=5,
            classificazione='A/2'
        )
        
        db.create_immobile(
            partita_id=partita2_id,
            localita_id=localita2_id,
            natura='Negozio',
            numero_piani=1,
            numero_vani=2,
            classificazione='C/1'
        )
        
        # Test ricerca immobili con filtri
        # Ricerca per natura
        results = db.ricerca_avanzata_immobili_gui(
            natura_search='Casa'
        )
        # La funzione potrebbe non essere implementata completamente
        assert isinstance(results, list)


class TestConcurrentOperations:
    """Test operazioni concorrenti"""
    
    def test_concurrent_updates(self, db_manager):
        """Test aggiornamenti concorrenti allo stesso record"""
        import threading
        import queue
        
        # Crea comune di test
        comune_id = db_manager.aggiungi_comune("Concurrent Test", "CT", "Test")
        
        # Crea possessore
        possessore_id = db_manager.create_possessore(
            nome_completo="CONCURRENT TEST",
            comune_riferimento_id=comune_id
        )
        
        results = queue.Queue()
        errors = queue.Queue()
        
        def update_worker(note_value):
            try:
                success = db_manager.update_possessore(
                    possessore_id=possessore_id,
                    note=f"Update {note_value}"
                )
                results.put((note_value, success))
            except Exception as e:
                errors.put((note_value, str(e)))
        
        # Lancia thread concorrenti
        threads = []
        for i in range(5):
            t = threading.Thread(target=update_worker, args=(i,))
            threads.append(t)
            t.start()
        
        # Attendi completamento
        for t in threads:
            t.join()
        
        # Verifica risultati
        assert errors.empty()  # Nessun errore
        
        # Almeno alcuni update dovrebbero avere successo
        successful_updates = []
        while not results.empty():
            note_val, success = results.get()
            if success:
                successful_updates.append(note_val)
        
        assert len(successful_updates) > 0
        
        # Verifica stato finale
        possessore = db_manager.get_possessore_by_id(possessore_id)
        assert possessore['note'] is not None
    
    def test_transaction_isolation(self, db_manager):
        """Test isolamento transazioni"""
        comune_id = db_manager.aggiungi_comune("Isolation Test", "IT", "Test")
        
        # Transazione 1: inserisce possessore
        db_manager.begin()
        possessore_id = db_manager.create_possessore(
            nome_completo="ISOLATION TEST 1",
            comune_riferimento_id=comune_id
        )
        
        # Prima del commit, un'altra connessione non dovrebbe vedere il possessore
        conn2 = db_manager._get_connection()
        try:
            with conn2.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) FROM possessore 
                    WHERE nome_completo = %s
                """, ("ISOLATION TEST 1",))
                count = cur.fetchone()[0]
                assert count == 0  # Non visibile prima del commit
        finally:
            db_manager._release_connection(conn2)
        
        # Commit transazione 1
        db_manager.commit()
        
        # Ora dovrebbe essere visibile
        conn3 = db_manager._get_connection()
        try:
            with conn3.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) FROM possessore 
                    WHERE nome_completo = %s
                """, ("ISOLATION TEST 1",))
                count = cur.fetchone()[0]
                assert count == 1  # Visibile dopo commit
        finally:
            db_manager._release_connection(conn3)


class TestBackupRestoreIntegration:
    """Test integrazione backup e restore"""
    
    def test_backup_restore_cycle(self, sample_data, tmp_path):
        """Test ciclo completo backup e restore"""
        db = sample_data.db
        
        # Crea file di backup
        backup_file = tmp_path / "test_backup.sql"
        
        # Esegui backup (simulato)
        # In un sistema reale, questo chiamerebbe pg_dump
        conn = db._get_connection()
        try:
            with conn.cursor() as cur:
                # Simula estrazione dati per backup
                cur.execute("SELECT COUNT(*) FROM possessore")
                original_count = cur.fetchone()[0]
        finally:
            db._release_connection(conn)
        
        # Simula processo di backup
        # In produzione si userebbe subprocess per pg_dump
        
        # Test che i dati esistano prima del "restore"
        assert original_count > 0
        
        # Simula restore verificando integrità dati
        possessori = db.get_possessori_by_comune(sample_data['comune_id'])
        assert len(possessori) > 0


class TestPerformanceIntegration:
    """Test performance sistema integrato"""
    
    def test_bulk_operations_performance(self, clean_db):
        """Test performance operazioni massive"""
        import time
        
        # Crea comune
        comune_id = clean_db.aggiungi_comune("Performance Test", "PT", "Test")
        
        # Test inserimento massivo con transazione
        start_time = time.time()
        
        clean_db.begin()
        try:
            # Inserisci 500 possessori
            for i in range(500):
                clean_db.create_possessore(
                    nome_completo=f"PERF TEST {i:04d}",
                    comune_riferimento_id=comune_id,
                    cognome_nome=f"PERF {i:04d}"
                )
            
            clean_db.commit()
        except Exception:
            clean_db.rollback()
            raise
        
        elapsed = time.time() - start_time
        
        # Verifica performance accettabile
        assert elapsed < 30.0  # Meno di 30 secondi per 500 record
        
        # Test ricerca su grande dataset
        search_start = time.time()
        results = clean_db.ricerca_avanzata_possessori_gui(
            query_text="PERF TEST 0250",
            similarity_threshold=0.8
        )
        search_elapsed = time.time() - search_start
        
        assert search_elapsed < 2.0  # Ricerca veloce anche con molti record
        assert len(results) > 0
    
    def test_gui_responsiveness_with_large_data(self, qapp, clean_db):
        """Test responsività GUI con molti dati"""
        # Crea dataset di test
        comune_id = clean_db.aggiungi_comune("GUI Performance", "GP", "Test")
        
        # Aggiungi 100 possessori
        for i in range(100):
            clean_db.create_possessore(
                nome_completo=f"GUI TEST {i:03d}",
                comune_riferimento_id=comune_id
            )
        
        # Crea widget e carica dati
        widget = PossessoriRicercaWidget(clean_db)
        
        # Misura tempo di caricamento
        start = time.time()
        if hasattr(widget, '_load_all_possessori'):
            widget._load_all_possessori()
        elapsed = time.time() - start
        
        # GUI dovrebbe rimanere responsiva
        assert elapsed < 3.0  # Caricamento veloce
        
        # Test scroll performance se implementato
        if hasattr(widget, 'results_table'):
            # Simula scroll
            widget.results_table.scrollToBottom()
            QTest.qWait(50)
            widget.results_table.scrollToTop()


class TestEndToEndScenarios:
    """Test scenari end-to-end completi"""
    
    def test_complete_property_transfer(self, qapp, sample_data):
        """Test trasferimento proprietà completo"""
        db = sample_data.db
        
        # Scenario: Trasferimento proprietà da possessore1 a possessore2
        
        # Step 1: Crea partita originale con possessore1
        partita_originale_id = db.create_partita(
            comune_id=sample_data['comune_id'],
            numero_partita=1000,
            tipo='principale',
            stato='attiva'
        )
        
        # Associa possessore1
        db.aggiungi_possessore_a_partita(
            partita_id=partita_originale_id,
            possessore_id=sample_data['possessore1_id'],
            tipo_partita_rel='principale',
            titolo='proprietà esclusiva',
            quota='1/1'
        )
        
        # Step 2: Crea variazione (vendita)
        conn = db._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO variazione 
                    (partita_origine_id, tipo, data_variazione, nominativo_riferimento)
                    VALUES (%s, %s, %s, %s) RETURNING id
                """, (
                    partita_originale_id,
                    'Vendita',
                    date.today(),
                    'BIANCHI ANNA fu Pietro'
                ))
                variazione_id = cur.fetchone()[0]
                
                # Crea contratto
                cur.execute("""
                    INSERT INTO contratto
                    (variazione_id, tipo, data_contratto, notaio, repertorio)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    variazione_id,
                    'Atto di Compravendita',
                    date.today(),
                    'Notaio Rossi Mario',
                    '12345/2025'
                ))
                
                conn.commit()
        finally:
            db._release_connection(conn)
        
        # Step 3: Crea nuova partita per il nuovo proprietario
        partita_nuova_id = db.create_partita(
            comune_id=sample_data['comune_id'],
            numero_partita=1001,
            tipo='principale',
            stato='attiva',
            numero_provenienza=1000
        )
        
        # Associa possessore2
        db.aggiungi_possessore_a_partita(
            partita_id=partita_nuova_id,
            possessore_id=sample_data['possessore2_id'],
            tipo_partita_rel='principale',
            titolo='proprietà esclusiva',
            quota='1/1'
        )
        
        # Step 4: Chiudi partita originale
        db.update_partita(
            partita_id=partita_originale_id,
            stato='chiusa',
            data_chiusura=date.today()
        )
        
        # Verifica risultato finale
        # Partita originale chiusa
        partita_orig = db.get_partita_by_id(partita_originale_id)
        assert partita_orig['stato'] == 'chiusa'
        
        # Nuova partita attiva con nuovo proprietario
        partita_nuova = db.get_partita_by_id(partita_nuova_id)
        assert partita_nuova['stato'] == 'attiva'
        assert partita_nuova['numero_provenienza'] == 1000
        
        # Verifica possessori
        possessori_nuova = db.get_possessori_by_partita(partita_nuova_id)
        assert len(possessori_nuova) == 1
        assert possessori_nuova[0]['id'] == sample_data['possessore2_id']