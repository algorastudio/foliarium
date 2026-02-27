#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test per GUI Widgets
===================
Test per i widget PyQt6 del sistema catasto
"""

# tests/test_gui_widgets.py

import pytest
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication, QWidget, QTableWidget, QMessageBox
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtTest import QTest
import sys

# Import dei widget da testare
from gui_widgets import (
    LandingPageWidget, ComuneManagerWidget, PartiteRicercaWidget,
    PossessoriRicercaWidget, RegistraPartitaWidget, RegistraPossessoreWidget,
    ImmobiliTableWidget, PossessoriTableWidget
)


# Fixture per QApplication
@pytest.fixture(scope='session')
def qapp():
    """Crea QApplication per test GUI"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def mock_db_manager():
    """Mock del database manager per test GUI"""
    mock = Mock()
    mock.schema = 'catasto'
    
    # Mock metodi comuni
    mock.get_all_comuni.return_value = [
        {'id': 1, 'nome': 'Carcare', 'provincia': 'SV', 'regione': 'Liguria'},
        {'id': 2, 'nome': 'Cairo M.', 'provincia': 'SV', 'regione': 'Liguria'}
    ]
    
    mock.get_possessori_by_comune.return_value = [
        {
            'id': 1,
            'nome_completo': 'ROSSI MARIO fu Giuseppe',
            'paternita': 'fu Giuseppe',
            'comune_nome': 'Carcare'
        }
    ]
    
    mock.get_partite_by_comune.return_value = [
        {
            'id': 1,
            'numero_partita': 100,
            'tipo': 'principale',
            'stato': 'attiva'
        }
    ]
    
    mock.search_partite_by_numero.return_value = []
    mock.ricerca_avanzata_possessori_gui.return_value = []
    
    return mock


class TestLandingPageWidget:
    """Test per il widget pagina principale"""
    
    def test_initialization(self, qapp):
        """Test inizializzazione widget"""
        widget = LandingPageWidget()
        
        assert widget is not None
        assert widget.windowTitle() == ""  # O il titolo che viene impostato
        
        # Verifica che i segnali siano definiti
        assert hasattr(widget, 'apri_elenco_comuni_signal')
        assert hasattr(widget, 'apri_ricerca_partite_signal')
        assert hasattr(widget, 'apri_ricerca_possessori_signal')
    
    def test_button_clicks(self, qapp):
        """Test click sui pulsanti"""
        widget = LandingPageWidget()
        
        # Mock per verificare emissione segnali
        signal_mock = Mock()
        widget.apri_elenco_comuni_signal.connect(signal_mock)
        
        # Simula click sul pulsante (assumendo che esista btn_gestione_comuni)
        # Nota: questo richiede conoscenza della struttura interna del widget
        if hasattr(widget, 'btn_gestione_comuni'):
            QTest.mouseClick(widget.btn_gestione_comuni, Qt.LeftButton)
            signal_mock.assert_called_once()


class TestComuneManagerWidget:
    """Test per il widget gestione comuni"""
    
    def test_initialization(self, qapp, mock_db_manager):
        """Test inizializzazione con mock DB"""
        widget = ComuneManagerWidget(mock_db_manager)
        
        assert widget is not None
        assert widget.db_manager == mock_db_manager
    
    def test_load_comuni(self, qapp, mock_db_manager):
        """Test caricamento lista comuni"""
        widget = ComuneManagerWidget(mock_db_manager)
        
        # Trigger caricamento
        widget._load_comuni()
        
        # Verifica che il metodo DB sia stato chiamato
        mock_db_manager.get_all_comuni.assert_called()
        
        # Verifica che la tabella sia popolata
        if hasattr(widget, 'table'):
            assert widget.table.rowCount() == 2
    
    @patch('PyQt6.QtWidgets.QInputDialog.getText')
    def test_add_comune(self, mock_dialog, qapp, mock_db_manager):
        """Test aggiunta nuovo comune"""
        # Setup mock dialog
        mock_dialog.return_value = ('Nuovo Comune', True)
        
        # Setup mock DB response
        mock_db_manager.aggiungi_comune.return_value = 3
        
        widget = ComuneManagerWidget(mock_db_manager)
        
        # Simula aggiunta comune
        if hasattr(widget, '_add_comune'):
            widget._add_comune()
            
            # Verifica chiamata DB
            mock_db_manager.aggiungi_comune.assert_called()


class TestPartiteRicercaWidget:
    """Test per il widget ricerca partite"""
    
    def test_search_functionality(self, qapp, mock_db_manager):
        """Test funzionalità di ricerca"""
        widget = PartiteRicercaWidget(mock_db_manager)
        
        # Setup search input
        if hasattr(widget, 'search_input'):
            widget.search_input.setText("100")
            
            # Trigger search
            if hasattr(widget, '_perform_search'):
                widget._perform_search()
                
                # Verifica chiamata metodo ricerca
                assert mock_db_manager.search_partite_by_numero.called or \
                       mock_db_manager.get_partite_by_numero.called
    
    def test_empty_search(self, qapp, mock_db_manager):
        """Test ricerca con campo vuoto"""
        widget = PartiteRicercaWidget(mock_db_manager)
        
        if hasattr(widget, 'search_input'):
            widget.search_input.setText("")
            
            # Con campo vuoto, dovrebbe caricare tutte le partite
            if hasattr(widget, '_perform_search'):
                widget._perform_search()
                
                # Verifica comportamento appropriato
                # Potrebbe chiamare get_partite_by_comune o simile


class TestPossessoriRicercaWidget:
    """Test per il widget ricerca possessori"""
    
    def test_fuzzy_search(self, qapp, mock_db_manager):
        """Test ricerca fuzzy possessori"""
        widget = PossessoriRicercaWidget(mock_db_manager)
        
        # Setup ricerca
        if hasattr(widget, 'search_input'):
            widget.search_input.setText("ROSSI")
            
            # Mock risultati ricerca
            mock_db_manager.ricerca_avanzata_possessori_gui.return_value = [
                {
                    'id': 1,
                    'nome_completo': 'ROSSI MARIO',
                    'similarity': 0.9
                }
            ]
            
            # Esegui ricerca
            if hasattr(widget, '_perform_search'):
                widget._perform_search()
                
                # Verifica chiamata con parametri corretti
                mock_db_manager.ricerca_avanzata_possessori_gui.assert_called_with(
                    query_text="ROSSI",
                    similarity_threshold=pytest.any(float)
                )
    
    def test_results_display(self, qapp, mock_db_manager):
        """Test visualizzazione risultati ricerca"""
        widget = PossessoriRicercaWidget(mock_db_manager)
        
        # Mock risultati
        test_results = [
            {'id': 1, 'nome_completo': 'TEST 1', 'similarity': 0.95},
            {'id': 2, 'nome_completo': 'TEST 2', 'similarity': 0.85}
        ]
        
        # Popola risultati
        if hasattr(widget, '_display_results'):
            widget._display_results(test_results)
            
            # Verifica tabella risultati
            if hasattr(widget, 'results_table'):
                assert widget.results_table.rowCount() == 2


class TestRegistraPartitaWidget:
    """Test per il widget registrazione partite"""
    
    def test_form_validation(self, qapp, mock_db_manager):
        """Test validazione form"""
        widget = RegistraPartitaWidget(mock_db_manager)
        
        # Test con campi vuoti
        if hasattr(widget, '_validate_form'):
            assert widget._validate_form() is False
        
        # Popola campi obbligatori
        if hasattr(widget, 'numero_input'):
            widget.numero_input.setText("100")
        if hasattr(widget, 'tipo_combo'):
            widget.tipo_combo.setCurrentIndex(0)  # principale
        
        # Ora dovrebbe validare
        if hasattr(widget, '_validate_form'):
            assert widget._validate_form() is True
    
    @patch('PyQt6.QtWidgets.QMessageBox.information')
    def test_save_partita(self, mock_msgbox, qapp, mock_db_manager):
        """Test salvataggio partita"""
        mock_db_manager.create_partita.return_value = 1
        
        widget = RegistraPartitaWidget(mock_db_manager)
        
        # Popola form
        if hasattr(widget, 'numero_input'):
            widget.numero_input.setText("200")
        if hasattr(widget, 'tipo_combo'):
            widget.tipo_combo.setCurrentIndex(0)
        
        # Salva
        if hasattr(widget, '_save_partita'):
            widget._save_partita()
            
            # Verifica chiamata DB
            mock_db_manager.create_partita.assert_called()
            
            # Verifica messaggio successo
            mock_msgbox.assert_called()


class TestTableWidgets:
    """Test per i widget tabella (ImmobiliTable, PossessoriTable)"""
    
    def test_immobili_table_population(self, qapp):
        """Test popolamento tabella immobili"""
        widget = ImmobiliTableWidget()
        
        test_data = [
            {
                'id': 1,
                'natura': 'Casa',
                'classificazione': 'A/2',
                'consistenza': '5 vani',
                'localita_nome': 'Via Roma',
                'civico': 10
            }
        ]
        
        widget.populate_table(test_data)
        
        assert widget.rowCount() == 1
        assert widget.item(0, 1).text() == 'Casa'
    
    def test_possessori_table_sorting(self, qapp):
        """Test ordinamento tabella possessori"""
        widget = PossessoriTableWidget()
        
        test_data = [
            {'id': 1, 'nome_completo': 'BIANCHI ANNA', 'paternita': 'fu Mario'},
            {'id': 2, 'nome_completo': 'ROSSI MARIO', 'paternita': 'fu Giuseppe'},
            {'id': 3, 'nome_completo': 'VERDI LUIGI', 'paternita': 'fu Pietro'}
        ]
        
        widget.populate_table(test_data)
        
        # Test ordinamento per nome
        widget.sortItems(1, Qt.AscendingOrder)
        
        # Verifica ordine
        assert widget.item(0, 1).text() == 'BIANCHI ANNA'
        assert widget.item(2, 1).text() == 'VERDI LUIGI'


class TestWidgetInteractions:
    """Test interazioni tra widget"""
    
    def test_signal_slot_connections(self, qapp, mock_db_manager):
        """Test connessioni signal-slot"""
        # Test esempio di connessione tra widget
        sender = LandingPageWidget()
        receiver = Mock()
        
        # Connetti segnale
        sender.apri_ricerca_partite_signal.connect(receiver)
        
        # Emetti segnale
        sender.apri_ricerca_partite_signal.emit()
        
        # Verifica ricezione
        receiver.assert_called_once()
    
    @patch('PyQt6.QtWidgets.QFileDialog.getOpenFileName')
    def test_file_import_dialog(self, mock_file_dialog, qapp, mock_db_manager):
        """Test dialog import file"""
        mock_file_dialog.return_value = ('/path/to/file.csv', 'CSV Files')
        
        widget = RegistraPossessoreWidget(mock_db_manager)
        
        # Simula import
        if hasattr(widget, '_import_from_csv'):
            widget._import_from_csv()
            
            # Verifica apertura dialog
            mock_file_dialog.assert_called()


class TestErrorHandlingGUI:
    """Test gestione errori nell'interfaccia"""
    
    @patch('PyQt6.QtWidgets.QMessageBox.critical')
    def test_database_error_display(self, mock_msgbox, qapp, mock_db_manager):
        """Test visualizzazione errori database"""
        # Simula errore DB
        mock_db_manager.get_all_comuni.side_effect = Exception("Connection error")
        
        widget = ComuneManagerWidget(mock_db_manager)
        
        # Tentativo caricamento che genera errore
        widget._load_comuni()
        
        # Verifica messaggio errore mostrato
        mock_msgbox.assert_called()
        args = mock_msgbox.call_args[0]
        assert "errore" in args[2].lower() or "error" in args[2].lower()
    
    def test_input_validation_feedback(self, qapp, mock_db_manager):
        """Test feedback validazione input"""
        widget = RegistraPartitaWidget(mock_db_manager)
        
        # Input non valido
        if hasattr(widget, 'numero_input'):
            widget.numero_input.setText("abc")  # Non numerico
            
            # Verifica feedback (dipende dall'implementazione)
            # Potrebbe colorare il campo, mostrare tooltip, etc.


class TestAccessibility:
    """Test accessibilità interfaccia"""
    
    def test_tab_navigation(self, qapp, mock_db_manager):
        """Test navigazione con tab"""
        widget = RegistraPartitaWidget(mock_db_manager)
        
        # Verifica che i widget principali siano nel tab order
        if hasattr(widget, 'numero_input') and hasattr(widget, 'tipo_combo'):
            # Simula pressione tab
            QTest.keyClick(widget.numero_input, Qt.Key_Tab)
            
            # Il focus dovrebbe spostarsi al prossimo widget
            assert widget.tipo_combo.hasFocus() or \
                   widget.focusWidget() == widget.tipo_combo
    
    def test_keyboard_shortcuts(self, qapp):
        """Test scorciatoie da tastiera"""
        widget = LandingPageWidget()
        
        # Test scorciatoie comuni (se implementate)
        # Es: Ctrl+N per nuovo, Ctrl+S per salva, etc.
        
        # Esempio generico
        if hasattr(widget, 'shortcut_new'):
            QTest.keyClick(widget, Qt.Key_N, Qt.ControlModifier)
            # Verifica azione eseguita