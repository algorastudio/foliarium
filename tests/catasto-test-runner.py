#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Runner e Configurazione
===========================
Script per eseguire la suite di test completa
"""

# pytest.ini
"""
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    --color=yes
    --cov=.
    --cov-report=html
    --cov-report=term-missing

markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    gui: marks tests that require GUI
    db: marks tests that require database
    unit: marks tests as unit tests

# Timeout per test lunghi
timeout = 300

# Configurazione per test paralleli (opzionale)
# -n auto  # Usa pytest-xdist per test paralleli
"""

# tests/run_tests.py

import sys
import os
import pytest
import argparse
from pathlib import Path

# Aggiungi la directory principale al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestRunner:
    """Gestisce l'esecuzione dei test"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_dir = self.project_root / 'tests'
        
    def run_all_tests(self):
        """Esegue tutti i test"""
        print("🧪 Esecuzione di TUTTI i test...")
        return pytest.main([str(self.test_dir), '-v'])
    
    def run_unit_tests(self):
        """Esegue solo i test unitari"""
        print("🧪 Esecuzione test UNITARI...")
        return pytest.main([str(self.test_dir), '-v', '-m', 'unit'])
    
    def run_integration_tests(self):
        """Esegue solo i test di integrazione"""
        print("🧪 Esecuzione test di INTEGRAZIONE...")
        return pytest.main([str(self.test_dir), '-v', '-m', 'integration'])
    
    def run_gui_tests(self):
        """Esegue solo i test GUI"""
        print("🧪 Esecuzione test GUI...")
        return pytest.main([str(self.test_dir), '-v', '-m', 'gui'])
    
    def run_fast_tests(self):
        """Esegue tutti i test tranne quelli lenti"""
        print("🧪 Esecuzione test VELOCI...")
        return pytest.main([str(self.test_dir), '-v', '-m', 'not slow'])
    
    def run_specific_test(self, test_path):
        """Esegue un test specifico"""
        print(f"🧪 Esecuzione test specifico: {test_path}")
        return pytest.main([test_path, '-v'])
    
    def run_with_coverage(self):
        """Esegue test con report di coverage"""
        print("🧪 Esecuzione test con COVERAGE...")
        return pytest.main([
            str(self.test_dir), 
            '-v',
            '--cov=.',
            '--cov-report=html',
            '--cov-report=term-missing'
        ])
    
    def run_parallel(self, num_workers='auto'):
        """Esegue test in parallelo"""
        print(f"🧪 Esecuzione test in PARALLELO (workers: {num_workers})...")
        return pytest.main([
            str(self.test_dir),
            '-v',
            '-n', str(num_workers)
        ])


def main():
    """Entry point principale"""
    parser = argparse.ArgumentParser(description='Runner per test Catasto Storico')
    parser.add_argument(
        'mode',
        choices=['all', 'unit', 'integration', 'gui', 'fast', 'coverage', 'parallel'],
        nargs='?',
        default='all',
        help='Modalità di esecuzione test'
    )
    parser.add_argument(
        '--test',
        help='Path specifico al test da eseguire'
    )
    parser.add_argument(
        '--workers',
        default='auto',
        help='Numero di worker per test paralleli'
    )
    
    args = parser.parse_args()
    runner = TestRunner()
    
    # Esegui test in base alla modalità
    if args.test:
        exit_code = runner.run_specific_test(args.test)
    elif args.mode == 'all':
        exit_code = runner.run_all_tests()
    elif args.mode == 'unit':
        exit_code = runner.run_unit_tests()
    elif args.mode == 'integration':
        exit_code = runner.run_integration_tests()
    elif args.mode == 'gui':
        exit_code = runner.run_gui_tests()
    elif args.mode == 'fast':
        exit_code = runner.run_fast_tests()
    elif args.mode == 'coverage':
        exit_code = runner.run_with_coverage()
    elif args.mode == 'parallel':
        exit_code = runner.run_parallel(args.workers)
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()


# tox.ini - Configurazione per test in ambienti multipli
"""
[tox]
envlist = py38,py39,py310,py311
skipsdist = True

[testenv]
deps = 
    pytest
    pytest-cov
    pytest-timeout
    pytest-xdist
    pytest-qt
    psycopg2-binary
    PyQt6
    
commands = 
    pytest {posargs}

[testenv:coverage]
deps = 
    {[testenv]deps}
    coverage
commands = 
    coverage run -m pytest
    coverage report
    coverage html

[testenv:lint]
deps = 
    pylint
    flake8
    black
commands = 
    flake8 .
    pylint catasto_db_manager.py gui_main.py
    black --check .
"""


# Makefile per comandi comuni
"""
.PHONY: test test-unit test-integration test-gui test-coverage test-parallel clean

# Esegui tutti i test
test:
	python tests/run_tests.py all

# Esegui solo test unitari
test-unit:
	python tests/run_tests.py unit

# Esegui solo test di integrazione  
test-integration:
	python tests/run_tests.py integration

# Esegui solo test GUI
test-gui:
	python tests/run_tests.py gui

# Esegui test con coverage
test-coverage:
	python tests/run_tests.py coverage

# Esegui test in parallelo
test-parallel:
	python tests/run_tests.py parallel

# Pulisci file temporanei
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf .tox

# Installa dipendenze di test
install-test-deps:
	pip install pytest pytest-cov pytest-timeout pytest-xdist pytest-qt

# Esegui linting
lint:
	flake8 .
	pylint *.py

# Formatta codice
format:
	black .

# Esegui test in Docker
test-docker:
	docker-compose -f docker-compose.test.yml up --abort-on-container-exit
	docker-compose -f docker-compose.test.yml down
"""


# requirements-test.txt
"""
# Testing dependencies
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-timeout>=2.1.0
pytest-xdist>=3.0.0
pytest-qt>=4.2.0
pytest-mock>=3.10.0

# Database
psycopg2-binary>=2.9.0

# GUI
PyQt6>=5.15.0

# Linting and formatting
pylint>=2.15.0
flake8>=5.0.0
black>=22.0.0

# Coverage
coverage>=7.0.0

# Tox for multi-environment testing
tox>=4.0.0

# Type checking
mypy>=0.990
types-psycopg2

# Documentation
sphinx>=5.0.0
sphinx-rtd-theme>=1.0.0
"""


# docker-compose.test.yml
"""
version: '3.8'

services:
  postgres-test:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: postgres
    ports:
      - "5433:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  test-runner:
    build:
      context: .
      dockerfile: Dockerfile.test
    depends_on:
      postgres-test:
        condition: service_healthy
    environment:
      - TEST_DB_HOST=postgres-test
      - TEST_DB_PORT=5432
      - TEST_DB_USER=postgres
      - TEST_DB_PASSWORD=postgres
    volumes:
      - .:/app
      - ./test-results:/app/test-results
    command: pytest -v --junitxml=/app/test-results/junit.xml

# Dockerfile.test
FROM python:3.9

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt requirements-test.txt ./
RUN pip install -r requirements.txt -r requirements-test.txt

# Copy application code
COPY . .

# Run tests
CMD ["pytest", "-v"]
"""


# Script di setup ambiente test
# setup_test_env.sh
"""
#!/bin/bash

echo "🔧 Setup ambiente di test per Catasto Storico"

# Crea directory struttura
mkdir -p tests/{unit,integration,fixtures,reports}

# Crea virtual environment
python -m venv venv-test
source venv-test/bin/activate

# Installa dipendenze
pip install --upgrade pip
pip install -r requirements-test.txt

# Setup database di test
echo "📦 Creazione database di test..."
createdb -U postgres catasto_test 2>/dev/null || echo "Database già esistente"

# Esegui test di verifica
echo "✅ Verifica installazione..."
pytest --version
python -c "import psycopg2; print('✓ psycopg2 installato')"
python -c "import PyQt6; print('✓ PyQt6 installato')"

echo "✨ Ambiente di test pronto!"
echo "   Per eseguire i test: python tests/run_tests.py"
"""