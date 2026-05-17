"""
fuzzy.py — Ricerca fuzzy unificata su partite, possessori, immobili, variazioni e contratti.

Estratto da search_widgets.py (Sprint 3 refactor — six-hats).
Le classi sono anche re-esportate da search_widgets per preservare la
backward compatibility con i consumer esistenti.
"""
from __future__ import annotations

import csv
import logging
from datetime import date, datetime
from typing import Dict, List, Optional, TYPE_CHECKING

from PyQt6.QtCore import (
    QAbstractTableModel, QModelIndex, QPoint, QSize, QSortFilterProxyModel,
    Qt, QThread, QTimer, pyqtSignal,
)
from PyQt6.QtGui import QColor, QIcon
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog,
    QFileDialog, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMenu, QMessageBox, QProgressBar, QPushButton,
    QSlider, QSpinBox, QStyle, QTabWidget, QTableView, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from app_paths import get_icon_path
from app_utils import BulkReportPDF, FPDF_AVAILABLE, format_indirizzo, prompt_to_open_file
from foliarium.ui.widgets.custom import show_status_message as _show_status_message
from dialogs import (
    ComuneSelectionDialog, LocalitaSelectionDialog,
    ModificaImmobileDialog, ModificaLocalitaDialog, ModificaPossessoreDialog,
    PartitaDetailsDialog,
)

try:
    from catasto_db_manager import DBMError
except ImportError:
    class DBMError(Exception):
        pass

if TYPE_CHECKING:
    from catasto_db_manager import CatastoDBManager  # noqa: F401

logger = logging.getLogger("CatastoGUI.search.fuzzy")


class FuzzyResultsModel(QAbstractTableModel):
    """Modello per i risultati di ricerca fuzzy.

    Ogni riga è (entity_data, mapped_values). entity_data può essere
    l'entità grezza (tabelle individuali) o un wrapper {'type': t, 'data': entity}
    (tabella unificata). similarity_col abilita la colorazione del background
    sulla colonna di similarità; type_icons mappa entity_type→QIcon per la
    decoration nella colonna 0.
    """

    def __init__(self, headers, similarity_col=None, type_icons=None, parent=None):
        super().__init__(parent)
        self._headers = list(headers)
        self._similarity_col = similarity_col
        self._type_icons = type_icons or {}
        self._rows: list[tuple] = []

    def load(self, rows: list[tuple]) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()

    def clear(self) -> None:
        self.load([])

    def item_at(self, row: int) -> dict:
        if 0 <= row < len(self._rows):
            entity = self._rows[row][0]
            return entity if isinstance(entity, dict) else {}
        return {}

    def row_count(self) -> int:
        return len(self._rows)

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._headers)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self._headers[section] if 0 <= section < len(self._headers) else None
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row, col = index.row(), index.column()
        if not (0 <= row < len(self._rows) and 0 <= col < len(self._headers)):
            return None
        entity, values = self._rows[row]
        val = values[col] if col < len(values) else None
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if role == Qt.ItemDataRole.EditRole and col == self._similarity_col:
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return 0.0
            return str(val) if val is not None else ''
        if role == Qt.ItemDataRole.BackgroundRole and self._similarity_col is not None and col == self._similarity_col:
            try:
                sim = float(val)
            except (ValueError, TypeError):
                return None
            if sim > 0.7:
                return QColor("#d4edda")
            if sim > 0.5:
                return QColor("#fff3cd")
            return QColor("#f8d7da")
        if role == Qt.ItemDataRole.DecorationRole and col == 0 and self._type_icons:
            if isinstance(entity, dict):
                t = entity.get('type')
                if t and t in self._type_icons:
                    return self._type_icons[t]
        return None

    def flags(self, index):
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def sort(self, column, order=Qt.SortOrder.AscendingOrder):
        if not self._rows or column >= len(self._headers):
            return
        self.layoutAboutToBeChanged.emit()
        def _key(r):
            vals = r[1]
            v = vals[column] if column < len(vals) else None
            return (v is None, v if v is not None else '')
        self._rows.sort(key=_key, reverse=(order == Qt.SortOrder.DescendingOrder))
        self.layoutChanged.emit()


class UnifiedFuzzySearchThread(QThread):
    """Thread unificato per eseguire ricerche fuzzy in background."""
    results_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int)

    def __init__(self, gin_search_manager, query_text, options, parent=None):
        super().__init__(parent)
        self.gin_search_manager = gin_search_manager
        self.query_text = query_text
        self.options = options

    def run(self):
        """Esegue la ricerca fuzzy."""
        try:
            self.progress_updated.emit(10)
            
            threshold = self.options.get('threshold', 0.3)

            # --- MODIFICA: Logica di ricerca semplificata ---
            # Questo thread ora chiama un metodo unificato che a sua volta
            # orchestra le ricerche individuali.
            # Assumiamo che `gin_search_manager` abbia un metodo come `search_all_entities_fuzzy`.
            if not hasattr(self.gin_search_manager, 'search_all_entities_fuzzy'):
                self.error_occurred.emit("Il DB Manager non supporta 'search_all_entities_fuzzy'.")
                return

            self.progress_updated.emit(30)

            results_data = self.gin_search_manager.search_all_entities_fuzzy(
                query_text=self.query_text,
                search_possessori=self.options.get('search_possessori', True),
                search_localita=self.options.get('search_localita', True),
                search_immobili=self.options.get('search_immobili', True),
                search_variazioni=self.options.get('search_variazioni', True),
                search_contratti=self.options.get('search_contratti', True),
                search_partite=self.options.get('search_partite', True),
                max_results_per_type=self.options.get('max_results_per_type', 50),
                similarity_threshold=threshold
            )

            # Prepara il dizionario finale per l'emissione del segnale
            final_results = {
                'query_text': self.query_text,
                'threshold': threshold,
                'timestamp': datetime.now(),
                'total_results': sum(len(entities) for entities in results_data.values()),
                'results_by_type': results_data # Mantiene la struttura per tipo
            }

            self.progress_updated.emit(100)
            self.results_ready.emit(final_results)

        except Exception as e:
            logging.getLogger(__name__).error(f"Errore nel thread di ricerca: {e}", exc_info=True)
            self.error_occurred.emit(str(e))


# ========================================================================
# WIDGET PRINCIPALE UNIFICATO
# ========================================================================

class UnifiedFuzzySearchWidget(QWidget):
    """Widget unificato per ricerca fuzzy con una singola interfaccia robusta."""

    # --- MODIFICA: Il costruttore non ha più il parametro 'mode' ---
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.parent_window = parent
        self.logger = logging.getLogger(__name__)

        # Inizializza componenti GIN. Assumiamo che db_manager sia già esteso.
        self.gin_search = self.db_manager

        # Variabili di stato
        self.current_results = {}
        self.search_thread = None
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._perform_search)

        # Setup UI
        self._init_ui() # --- MODIFICA: Chiamata a un singolo metodo di setup UI
        self._setup_signals()
        self._check_gin_status()

  
    def _init_ui(self):
        """Configura l'interfaccia utente unificata con un layout robusto."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(12)

        # Titolo e sottotitolo pagina
        _title = QLabel("Ricerca Globale")
        _title.setObjectName("pageTitle")
        main_layout.addWidget(_title)
        _subtitle = QLabel("Ricerca fuzzy in possessori, località, immobili, variazioni, contratti e partite. Usa la soglia per ampliare o restringere i match.")
        _subtitle.setObjectName("pageSubtitle")
        main_layout.addWidget(_subtitle)

        # Contenitore principale con stretch
        content_container_widget = QWidget()
        content_layout = QVBoxLayout(content_container_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)

        # === AREA RICERCA — card bianca ===
        search_frame = QFrame()
        search_frame.setObjectName("card")
        search_frame.setMaximumHeight(130)
        search_layout = QVBoxLayout(search_frame)
        search_layout.setContentsMargins(14, 12, 14, 12)
        search_layout.setSpacing(10)

        # Riga 1: search box prominente
        search_row = QHBoxLayout()
        search_row.setSpacing(8)
        _lbl_search = QLabel()
        _lbl_search.setPixmap(QIcon(str(get_icon_path("search"))).pixmap(QSize(18, 18)))
        search_row.addWidget(_lbl_search)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Cerca in possessori, località, immobili, variazioni, contratti, partite…")
        self.search_edit.setMinimumHeight(36)
        search_row.addWidget(self.search_edit, 1)
        self.clear_btn = QPushButton()
        self.clear_btn.setObjectName("secondaryButton")
        self.clear_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_LineEditClearButton))
        self.clear_btn.setToolTip("Pulisci ricerca")
        self.clear_btn.setMaximumWidth(36)
        self.clear_btn.setMinimumWidth(36)
        search_row.addWidget(self.clear_btn)
        self.search_btn = QPushButton("Cerca")
        self.search_btn.setDefault(True)
        self.search_btn.setMinimumWidth(110)
        search_row.addWidget(self.search_btn)
        search_layout.addLayout(search_row)

        # Riga 2: controlli avanzati (soglia, max risultati, export)
        controls_row = QHBoxLayout()
        controls_row.setSpacing(10)
        _lbl_soglia = QLabel("Soglia:")
        _lbl_soglia.setProperty("muted", "true")
        controls_row.addWidget(_lbl_soglia)
        self.precision_slider = QSlider(Qt.Orientation.Horizontal)
        self.precision_slider.setRange(10, 90)
        self.precision_slider.setValue(30)
        self.precision_slider.setMaximumWidth(130)
        controls_row.addWidget(self.precision_slider)

        self.precision_label = QLabel("0.30")
        self.precision_label.setMinimumWidth(36)
        controls_row.addWidget(self.precision_label)

        controls_row.addSpacing(12)

        _lbl_max = QLabel("Max risultati:")
        _lbl_max.setProperty("muted", "true")
        controls_row.addWidget(_lbl_max)
        self.max_results_combo = QComboBox()
        self.max_results_combo.addItems(["50", "100", "200", "500"])
        self.max_results_combo.setCurrentText("100")
        self.max_results_combo.setMaximumWidth(80)
        controls_row.addWidget(self.max_results_combo)

        controls_row.addStretch()

        self.btn_export_csv = QPushButton("Esporta CSV")
        self.btn_export_csv.setObjectName("secondaryButton")
        self.btn_export_csv.setEnabled(False)
        controls_row.addWidget(self.btn_export_csv)

        self.btn_export_pdf = QPushButton("Esporta PDF")
        self.btn_export_pdf.setObjectName("secondaryButton")
        self.btn_export_pdf.setEnabled(False)
        if not FPDF_AVAILABLE:
            self.btn_export_pdf.setToolTip("Libreria FPDF2 non trovata. Funzione non disponibile.")
        controls_row.addWidget(self.btn_export_pdf)

        search_layout.addLayout(controls_row)
        # --- FINE BLOCCO DA SOSTITUIRE ---
        
        content_layout.addWidget(search_frame) # AGGIUNTO AL CONTENT_LAYOUT

        # === CHECKBOXES (da aggiungere al content_layout) ===
        types_layout = QHBoxLayout()
        types_group = QGroupBox("Cerca in:")
        types_group_layout = QHBoxLayout(types_group)
        # ... (tutte le checkbox vengono create e aggiunte a types_group_layout come prima) ...
        self.search_possessori_cb = QCheckBox("Possessori"); self.search_possessori_cb.setIcon(QIcon(str(get_icon_path("users")))); self.search_possessori_cb.setChecked(True); types_group_layout.addWidget(self.search_possessori_cb)
        self.search_localita_cb = QCheckBox("Località"); self.search_localita_cb.setIcon(QIcon(str(get_icon_path("map-pin")))); self.search_localita_cb.setChecked(True); types_group_layout.addWidget(self.search_localita_cb)
        self.search_immobili_cb = QCheckBox("Immobili"); self.search_immobili_cb.setIcon(QIcon(str(get_icon_path("building")))); self.search_immobili_cb.setChecked(True); types_group_layout.addWidget(self.search_immobili_cb)
        self.search_variazioni_cb = QCheckBox("Variazioni"); self.search_variazioni_cb.setIcon(QIcon(str(get_icon_path("report")))); self.search_variazioni_cb.setChecked(True); types_group_layout.addWidget(self.search_variazioni_cb)
        self.search_contratti_cb = QCheckBox("Contratti"); self.search_contratti_cb.setIcon(QIcon(str(get_icon_path("file-text")))); self.search_contratti_cb.setChecked(True); types_group_layout.addWidget(self.search_contratti_cb)
        self.search_partite_cb = QCheckBox("Partite"); self.search_partite_cb.setIcon(QIcon(str(get_icon_path("bar-chart")))); self.search_partite_cb.setChecked(True); types_group_layout.addWidget(self.search_partite_cb)
        types_layout.addWidget(types_group)

        content_layout.addLayout(types_layout) # AGGIUNTO AL CONTENT_LAYOUT

        # === AREA RISULTATI ===
        self.results_tabs = QTabWidget()
        self.results_tabs.setMinimumHeight(400)

        _type_icons = {
            'possessore': QIcon(str(get_icon_path("users"))),
            'localita':   QIcon(str(get_icon_path("map-pin"))),
            'immobile':   QIcon(str(get_icon_path("building"))),
            'variazione': QIcon(str(get_icon_path("report"))),
            'contratto':  QIcon(str(get_icon_path("file-text"))),
            'partita':    QIcon(str(get_icon_path("bar-chart"))),
        }

        self.unified_table, self._unified_model = self._create_table_view(
            ["Tipo", "Nome/Descrizione", "Dettagli", "Similarità", "Campo"],
            similarity_col=3, type_icons=_type_icons)
        self.results_tabs.addTab(self.unified_table, QIcon(str(get_icon_path("search"))), "Tutti")

        self.possessori_table, self._possessori_model = self._create_table_view(
            ["Nome Completo", "Comune", "Partite", "Similitud."], similarity_col=3)
        self.results_tabs.addTab(self.possessori_table, QIcon(str(get_icon_path("users"))), "Possessori")

        self.localita_table, self._localita_model = self._create_table_view(
            ["Nome", "Tipologia", "Comune", "Immobili", "Similitud."], similarity_col=4)
        self.results_tabs.addTab(self.localita_table, QIcon(str(get_icon_path("map-pin"))), "Località")

        self.immobili_table, self._immobili_model = self._create_table_view(
            ["Natura", "Classificazione", "Partita", "Suffisso", "Comune", "Similitud."], similarity_col=5)
        self.results_tabs.addTab(self.immobili_table, QIcon(str(get_icon_path("building"))), "Immobili")

        self.variazioni_table, self._variazioni_model = self._create_table_view(
            ["Tipo", "Data", "Rif. e Partita Origine", "Similitud."], similarity_col=3)
        self.results_tabs.addTab(self.variazioni_table, QIcon(str(get_icon_path("report"))), "Variazioni")

        self.contratti_table, self._contratti_model = self._create_table_view(
            ["Tipo", "Data", "Partita", "Similitud."], similarity_col=3)
        self.results_tabs.addTab(self.contratti_table, QIcon(str(get_icon_path("file-text"))), "Contratti")

        self.partite_table, self._partite_model = self._create_table_view(
            ["Numero", "Suffisso", "Possessori", "Tipo", "Stato", "Data Impianto", "Comune", "Similitud."],
            similarity_col=7)
        self.results_tabs.addTab(self.partite_table, QIcon(str(get_icon_path("bar-chart"))), "Partite")

        content_layout.addWidget(self.results_tabs) # AGGIUNTO AL CONTENT_LAYOUT

        # --- AGGIUNTA DEL CONTENITORE AL LAYOUT PRINCIPALE ---
        # Diamo a tutto il blocco dei contenuti un fattore di stretch > 0
        main_layout.addWidget(content_container_widget, 1)

        # === STATUS BAR ===
        status_frame = QFrame()
        status_frame.setObjectName("fuzzyStatusBar")
        status_frame.setMaximumHeight(32)
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(10, 4, 10, 4)
        self.stats_label = QLabel("Inserire almeno 3 caratteri per iniziare")
        self.stats_label.setProperty("muted", "true")
        status_layout.addWidget(self.stats_label)
        status_layout.addStretch()
        self.indices_status_label = QLabel("Verifica indici…")
        self.indices_status_label.setProperty("muted", "true")
        status_layout.addWidget(self.indices_status_label)

        main_layout.addWidget(status_frame)

        self.search_edit.setFocus()

    def _create_table_view(self, headers, similarity_col=None, type_icons=None):
        """Crea una QTableView con FuzzyResultsModel. Ritorna (view, model)."""
        model = FuzzyResultsModel(headers, similarity_col=similarity_col,
                                   type_icons=type_icons, parent=self)
        table = QTableView()
        table.setModel(model)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSortingEnabled(True)
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        return table, model

    def _setup_signals(self):
        """Configura i segnali."""
        self.search_edit.textChanged.connect(self._on_search_text_changed)
        self.search_btn.clicked.connect(self._perform_search)
        self.clear_btn.clicked.connect(self._clear_search)
        
        self.precision_slider.valueChanged.connect(lambda v: self.precision_label.setText(f"{v/100:.2f}"))
        self.precision_slider.sliderReleased.connect(self._trigger_search_if_text)

        self.max_results_combo.currentTextChanged.connect(self._trigger_search_if_text)
        # --- MODIFICA QUI: Colleghiamo i nuovi pulsanti ---
        # Rimuoviamo la vecchia riga: self.export_btn.clicked.connect(self._export_results)
        self.btn_export_csv.clicked.connect(self._handle_export_csv)
        self.btn_export_pdf.clicked.connect(self._handle_export_pdf)

        # Checkbox
        for cb in [self.search_possessori_cb, self.search_localita_cb, self.search_immobili_cb,
                   self.search_variazioni_cb, self.search_contratti_cb, self.search_partite_cb]: # AGGIUNTE NUOVE CHECKBOX
            cb.toggled.connect(self._trigger_search_if_text)

        # Double-click
        
        # --- MODIFICA QUI: Colleghiamo il doppio click per tutte le tabelle ---
        self.unified_table.doubleClicked.connect(self._on_unified_double_click)
        self.possessori_table.doubleClicked.connect(self._on_possessori_double_click)
        self.localita_table.doubleClicked.connect(self._on_localita_double_click)
        self.immobili_table.doubleClicked.connect(self._on_immobili_double_click)
        self.variazioni_table.doubleClicked.connect(self._on_variazioni_double_click)
        self.contratti_table.doubleClicked.connect(self._on_contratti_double_click)
        self.partite_table.doubleClicked.connect(self._on_partite_double_click)

    def _check_gin_status(self):
        """Verifica lo stato degli indici GIN."""
        if not self.gin_search or not hasattr(self.gin_search, 'verify_gin_indices'):
            self.indices_status_label.setText("Ricerca non disponibile")
            return
        try:
            result = self.gin_search.verify_gin_indices()
            if result.get('status') == 'OK' and result.get('gin_indices', 0) > 0:
                self.indices_status_label.setText(f"Indici GIN attivi ({result['gin_indices']})")
            else:
                self.indices_status_label.setText("Indici GIN mancanti o non validi")
        except Exception as e:
            self.indices_status_label.setText("Errore verifica indici")
            self.logger.error(f"Errore verifica indici GIN: {e}")

    def _on_search_text_changed(self, text):
        """Gestisce il cambiamento del testo di ricerca."""
        if len(text) >= 3:
            self.search_timer.start(800) # Delay per evitare ricerche a ogni tasto
            self.stats_label.setText("Pronto per la ricerca...")
        else:
            self.search_timer.stop()
            self._clear_results()
            self.stats_label.setText(f"Inserire almeno {3 - len(text)} caratteri in più")

    def _trigger_search_if_text(self):
        """Rilancia la ricerca se c'è abbastanza testo."""
        if len(self.search_edit.text().strip()) >= 3:
            self._perform_search()

    def _perform_search(self):
        """Esegue la ricerca vera e propria, gestendo il thread precedente."""
        query_text = self.search_edit.text().strip()
        if len(query_text) < 3:
            return

        if not self.gin_search:
            QMessageBox.warning(self, "Errore", "Sistema di ricerca fuzzy non disponibile.")
            return

        # --- MODIFICA CRUCIALE: Gestione del thread esistente ---
        if self.search_thread and self.search_thread.isRunning():
            self.logger.debug("Ricerca precedente ancora in corso. Tentativo di fermarla.")
            self.search_thread.quit()  # Chiede al thread di terminare in modo pulito
            self.search_thread.wait(500) # Attende al massimo 500ms
            if self.search_thread.isRunning():
                self.logger.warning("Il thread precedente non si è fermato in tempo, terminazione forzata.")
                self.search_thread.terminate() # Estrema ratio
                self.search_thread.wait()

        search_options = {
            'threshold': self.precision_slider.value() / 100.0,
            'max_results': int(self.max_results_combo.currentText()),
            'search_possessori': self.search_possessori_cb.isChecked(),
            'search_localita': self.search_localita_cb.isChecked(),
            'search_immobili': self.search_immobili_cb.isChecked(),
            # --- AGGIUNGERE QUESTE OPZIONI ---
            'search_variazioni': self.search_variazioni_cb.isChecked(),
            'search_contratti': self.search_contratti_cb.isChecked(),
            'search_partite': self.search_partite_cb.isChecked(),
        }

        
        self.search_btn.setEnabled(False)
        self.stats_label.setText("Ricerca in corso...")
        
        self.search_thread = UnifiedFuzzySearchThread(self.gin_search, query_text, search_options, parent=self)
        self.search_thread.results_ready.connect(self._display_results)
        self.search_thread.error_occurred.connect(self._handle_search_error)
        self.search_thread.finished.connect(lambda: self.search_btn.setEnabled(True))
        self.search_thread.start()

    def _display_results(self, results):
        """Visualizza i risultati della ricerca."""
        self.current_results = results
        results_by_type = results.get('results_by_type', {})
        
        self._populate_unified_table(results_by_type)
        self._populate_individual_tables(results_by_type)
        self._update_tab_counters(results_by_type)
        
        total = results.get('total_results', 0)
        self.stats_label.setText(f"Trovati {total} risultati per '{results.get('query_text')}'")
        # --- MODIFICA QUI ---
        self.btn_export_csv.setEnabled(total > 0)
        if FPDF_AVAILABLE:
            self.btn_export_pdf.setEnabled(total > 0)
    
    def _populate_unified_table(self, results_by_type: Dict[str, List]):
        _type_labels = {
            'possessore': 'Possessore', 'localita': 'Località', 'immobile': 'Immobile',
            'variazione': 'Variazione', 'contratto': 'Contratto', 'partita': 'Partita',
        }
        rows = []
        for entity_type, entities in results_by_type.items():
            for entity in entities:
                wrapper = {'type': entity_type, 'data': entity}
                rows.append((wrapper, [
                    _type_labels.get(entity_type, entity_type.title()),
                    entity.get('display_text', ''),
                    entity.get('detail_text', ''),
                    f"{entity.get('similarity_score', 0):.3f}",
                    entity.get('search_field', ''),
                ]))
        self._unified_model.load(rows)

    def _populate_individual_tables(self, results_by_type: Dict[str, List]):
        self._possessori_model.load([
            (p, [p.get('nome_completo', ''), p.get('comune_nome', ''),
                 p.get('num_partite', 0), f"{p.get('similarity_score', 0):.3f}"])
            for p in results_by_type.get('possessore', [])
        ])

        self._localita_model.load([
            (l, [l.get('nome', ''), l.get('tipologia_stradale', '') or l.get('tipo', '') or '',
                 l.get('comune_nome', ''), l.get('num_immobili', 0),
                 f"{l.get('similarity_score', 0):.3f}"])
            for l in results_by_type.get('localita', [])
        ])

        self._immobili_model.load([
            (i, [i.get('natura', ''), i.get('classificazione', ''),
                 i.get('numero_partita', ''), i.get('suffisso_partita', '') or '',
                 i.get('comune_nome', ''), f"{i.get('similarity_score', 0):.3f}"])
            for i in results_by_type.get('immobile', [])
        ])

        self._variazioni_model.load([
            (v, [v.get('tipo', ''), v.get('data_variazione', ''),
                 v.get('detail_text', ''), f"{v.get('similarity_score', 0):.3f}"])
            for v in results_by_type.get('variazione', [])
        ])

        self._contratti_model.load([
            (c, [c.get('tipo', ''), c.get('data_contratto', ''),
                 c.get('numero_partita', ''), f"{c.get('similarity_score', 0):.3f}"])
            for c in results_by_type.get('contratto', [])
        ])

        self._partite_model.load([
            (pt, [pt.get('numero_partita', ''), pt.get('suffisso_partita', '') or '',
                  pt.get('possessori_concatenati', '') or '', pt.get('tipo_partita', ''),
                  pt.get('stato', ''),
                  str(pt.get('data_impianto', '')) if pt.get('data_impianto') else '',
                  pt.get('comune_nome', ''), f"{pt.get('similarity_score', 0):.3f}"])
            for pt in results_by_type.get('partita', [])
        ])
    def _update_tab_counters(self, results_by_type: Dict[str, List]):
        """Aggiorna i contatori nei titoli dei tab."""
        # --- MODIFICA: La logica di base_index non è più necessaria ---
        self.results_tabs.setTabText(0, f"Tutti ({sum(len(v) for v in results_by_type.values())})")
        self.results_tabs.setTabText(1, f"Possessori ({len(results_by_type.get('possessore', []))})")
        self.results_tabs.setTabText(2, f"Località ({len(results_by_type.get('localita', []))})")
        self.results_tabs.setTabText(3, f"Immobili ({len(results_by_type.get('immobile', []))})")
        self.results_tabs.setTabText(4, f"Variazioni ({len(results_by_type.get('variazione', []))})")
        self.results_tabs.setTabText(5, f"Contratti ({len(results_by_type.get('contratto', []))})")
        self.results_tabs.setTabText(6, f"Partite ({len(results_by_type.get('partita', []))})")

    def _clear_results(self):
        """Pulisce tutti i risultati e i contatori."""
        for model in (self._unified_model, self._possessori_model, self._localita_model,
                      self._immobili_model, self._variazioni_model, self._contratti_model,
                      self._partite_model):
            model.clear()

        self._update_tab_counters({})
        
        # --- MODIFICA QUI: Disabilita i nuovi pulsanti invece del vecchio ---
        self.btn_export_csv.setEnabled(False)
        self.btn_export_pdf.setEnabled(False)
        
        self.current_results = {}

    def _handle_search_error(self, error_message):
        """Gestisce gli errori di ricerca."""
        self.search_btn.setEnabled(True)
        self.stats_label.setText("Errore ricerca")
        self.logger.error(f"Errore ricerca fuzzy: {error_message}")
        QMessageBox.critical(self, "Errore Ricerca", f"Si è verificato un errore:\n{error_message}")

    def _clear_search(self):
        """Pulisce il campo di ricerca e i risultati."""
        self.search_edit.clear()
        self._clear_results()
        self.stats_label.setText("Pronto")


    def _on_unified_double_click(self, index):
        """Gestisce il doppio click nella tabella unificata."""
        if not index.isValid():
            return
        wrapper = self._unified_model.item_at(index.row())
        if not isinstance(wrapper, dict):
            return
        entity_type = wrapper.get('type')
        entity = wrapper.get('data') or {}
        entity_id = entity.get('entity_id') if isinstance(entity, dict) else None

        if entity_type == 'partita':
            self._open_partita_dialog(entity_id)
        elif entity_type == 'possessore':
            self._open_possessore_dialog(entity_id)
        elif entity_type == 'localita':
            self._open_localita_dialog(entity_id)
        elif entity_type == 'immobile':
            self._open_immobile_dialog(entity_id)
        elif entity_type == 'variazione':
            self._show_generic_details(entity, 'variazione')
        elif entity_type == 'contratto':
            self._show_generic_details(entity, 'contratto')
        else:
            QMessageBox.warning(self, "Tipo Sconosciuto",
                                f"Nessuna azione di dettaglio definita per il tipo '{entity_type}'.")
    def _handle_export_csv(self):
        """Esporta i risultati correnti della ricerca unificata in un file CSV."""
        if not self.current_results or not self.current_results.get('total_results', 0) > 0:
            QMessageBox.warning(self, "Nessun Risultato", "Non ci sono risultati da esportare.")
            return

        query_text = self.current_results.get('query_text', 'ricerca')
        default_filename = f"ricerca_fuzzy_{query_text}_{date.today().isoformat()}.csv"
        filename, _ = QFileDialog.getSaveFileName(self, "Esporta Risultati in CSV", default_filename, "File CSV (*.csv)")

        if not filename:
            return

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                # Usiamo le intestazioni della tabella "Tutti"
                headers = ['Tipo Entità', 'Nome/Descrizione', 'Dettagli', 'Similarità', 'Campo Trovato']
                writer = csv.writer(csvfile, delimiter=';')
                writer.writerow(headers)
                
                for entity_type, entities in self.current_results.get('results_by_type', {}).items():
                    for entity in entities:
                        writer.writerow([
                            entity_type,
                            entity.get('display_text', ''),
                            entity.get('detail_text', ''),
                            f"{entity.get('similarity_score', 0):.3f}",
                            entity.get('search_field', '')
                        ])
            prompt_to_open_file(self, filename)
        except Exception as e:
            self.logger.error(f"Errore esportazione CSV fuzzy: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Esportazione", f"Impossibile salvare il file CSV:\n{e}")

    def _handle_export_pdf(self):
        """Esporta i risultati correnti della ricerca unificata in un file PDF."""
        if not self.current_results or not self.current_results.get('total_results', 0) > 0:
            QMessageBox.warning(self, "Nessun Risultato", "Non ci sono risultati da esportare.")
            return
            
        query_text = self.current_results.get('query_text', 'ricerca')
        default_filename = f"ricerca_fuzzy_{query_text}_{date.today().isoformat()}.pdf"
        filename, _ = QFileDialog.getSaveFileName(self, "Esporta Risultati in PDF", default_filename, "File PDF (*.pdf)")

        if not filename:
            return

        try:
            pdf = BulkReportPDF(report_title=f"Risultati Ricerca Fuzzy per '{query_text}'")
            pdf.alias_nb_pages()
            pdf.set_font('Times', '', 12)
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            
            for entity_type, entities in self.current_results.get('results_by_type', {}).items():
                if not entities: continue
                
                pdf.set_font('Helvetica', 'B', 12)
                pdf.cell(0, 10, f"Risultati per: {entity_type.title()} ({len(entities)})", ln=1)
                
                headers = ['Nome/Descrizione', 'Dettagli', 'Similarità']
                # Adattiamo i dati per la tabella
                data_rows = [
                    (entity.get('display_text', ''), entity.get('detail_text', ''), f"{entity.get('similarity_score', 0):.3f}")
                    for entity in entities
                ]
                # La classe BulkReportPDF gestirà la creazione della tabella
                pdf.print_table(headers, data_rows)
                pdf.ln(5)

            pdf.output(filename)
            prompt_to_open_file(self, filename)
        except Exception as e:
            self.logger.error(f"Errore esportazione PDF fuzzy: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Esportazione", f"Impossibile generare il file PDF:\n{e}")
   

    def _open_possessore_dialog(self, entity_id: Optional[int]):
        if not entity_id:
            return
        dialog = ModificaPossessoreDialog(self.db_manager, entity_id, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._perform_search()

    def _open_localita_dialog(self, entity_id: Optional[int]):
        if not entity_id:
            return
        localita_details = self.db_manager.get_localita_details(entity_id)
        if localita_details and localita_details.get('comune_id'):
            dialog = ModificaLocalitaDialog(self.db_manager, entity_id, localita_details.get('comune_id'), self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self._perform_search()
        else:
            QMessageBox.warning(self, "Errore Dati",
                                f"Impossibile caricare i dettagli per la località ID {entity_id}.")

    def _open_immobile_dialog(self, entity_id: Optional[int]):
        if not entity_id:
            return
        immobile_details = self.db_manager.get_immobile_details(entity_id)
        if immobile_details and immobile_details.get('partita_id'):
            partita_details = self.db_manager.get_partita_details(immobile_details.get('partita_id'))
            if partita_details and partita_details.get('comune_id'):
                dialog = ModificaImmobileDialog(self.db_manager, entity_id, partita_details.get('comune_id'), self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    self._perform_search()
            else:
                QMessageBox.warning(self, "Errore Dati",
                                    f"Impossibile determinare il comune per l'immobile ID {entity_id}.")
        else:
            QMessageBox.warning(self, "Errore Dati",
                                f"Impossibile caricare i dettagli per l'immobile ID {entity_id}.")

    def _open_partita_dialog(self, entity_id: Optional[int]):
        if not entity_id:
            return
        full_details = self.db_manager.get_partita_details(entity_id)
        if full_details:
            dialog = PartitaDetailsDialog(full_details, self)
            dialog.exec()
        else:
            QMessageBox.warning(self, "Errore Dati",
                                f"Impossibile caricare i dettagli per la partita ID {entity_id}.")

    def _show_generic_details(self, entity_data: dict, entity_type_name: str):
        """Mostra un popup leggibile per entità senza un dialogo di dettaglio dedicato."""
        if not isinstance(entity_data, dict):
            return
        entity_id = entity_data.get('entity_id', 'N/A')
        testo = f"<h3>Dettagli - {entity_type_name.title()} ID: {entity_id}</h3>"
        testo += "<table border='0' cellspacing='5'>"
        for key, value in entity_data.items():
            chiave = key.replace('_', ' ').title()
            testo += f"<tr><td><b>{chiave}:</b></td><td>{value}</td></tr>"
        testo += "</table>"
        QMessageBox.information(self, f"Dettagli - {entity_type_name.title()}", testo)

    def _on_possessori_double_click(self, index):
        if not index.isValid():
            return
        entity = self._possessori_model.item_at(index.row())
        self._open_possessore_dialog(entity.get('entity_id'))

    def _on_localita_double_click(self, index):
        if not index.isValid():
            return
        entity = self._localita_model.item_at(index.row())
        self._open_localita_dialog(entity.get('entity_id'))

    def _on_immobili_double_click(self, index):
        if not index.isValid():
            return
        entity = self._immobili_model.item_at(index.row())
        self._open_immobile_dialog(entity.get('entity_id'))

    def _on_partite_double_click(self, index):
        if not index.isValid():
            return
        entity = self._partite_model.item_at(index.row())
        self._open_partita_dialog(entity.get('entity_id'))

    def _on_variazioni_double_click(self, index):
        if not index.isValid():
            return
        entity = self._variazioni_model.item_at(index.row())
        self._show_generic_details(entity, 'variazione')

    def _on_contratti_double_click(self, index):
        if not index.isValid():
            return
        entity = self._contratti_model.item_at(index.row())
        self._show_generic_details(entity, 'contratto')
