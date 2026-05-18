#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test per CatastoDBManager
========================
Test completi per le operazioni del database manager.
Migrato da tests/catasto-test-database.py (v1.0.1).
"""

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
        manager.initialize_main_pool()
        assert manager.pool is not None

        # Verifica che il pool sia utilizzabile (context manager)
        with manager._get_connection() as conn:
            assert conn is not None

        # Cleanup
        manager.close_pool()
        assert manager.pool is None
    
    def test_connection_error_handling(self, test_db_setup):
        """Test gestione errori di connessione: initialize_main_pool ritorna
        False senza sollevare (gli errori sono catturati internamente e
        riportati via get_last_connect_error_details)."""
        bad_config = test_db_setup.copy()
        bad_config['password'] = 'wrong_password'

        manager = CatastoDBManager(**bad_config)

        assert manager.initialize_main_pool() is False
        assert manager.pool is None
    
    def test_pool_thread_safety(self, db_manager):
        """Test thread safety del pool"""
        import threading
        import time
        
        results = []
        errors = []
        
        def worker():
            try:
                with db_manager._get_connection() as conn:
                    time.sleep(0.1)  # Simula operazione
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1")
                        results.append(cur.fetchone()[0])
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


# =========================================================================
# Tutte le ex-classi @pytest.mark.skip (TestComuneOperations,
# TestPossessoreOperations, TestPartitaOperations, TestImmobileOperations,
# TestImportExportOperations, TestTransactionManagement, TestErrorHandling,
# TestPerformanceAndOptimization) sono state cancellate nello Sprint 3.9
# (six-hats opzione "riscrivere ex-novo"). I test equivalenti sono ora in:
#
#   tests/integration/test_e2e.py (classi Test*CRUD/Workflow/Lifecycle
#       + TestUniqueConstraints, TestErrorRaising,
#       TestTransactionContextManager)
#
# TestPerformanceAndOptimization e' stata cancellata senza sostituto:
# i test perf su CI sono flaky e il valore segnaletico e' basso.
# =========================================================================
