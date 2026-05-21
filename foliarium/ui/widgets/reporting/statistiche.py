"""Widget statistiche e grafici."""
from __future__ import annotations

import os
import csv
import logging
from datetime import date, datetime
from typing import Optional, List, Dict, Any, TYPE_CHECKING

import pandas as pd

from PyQt6.QtCore import (
    QAbstractTableModel, QDate, QModelIndex, QPoint, Qt, QUrl,
)
from PyQt6.QtGui import (
    QDesktopServices,
)
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication,
    QComboBox, QDateEdit, QDialog, QFileDialog,
    QFormLayout, QFrame, QGridLayout, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMenu, QMessageBox, QProgressDialog,
    QPushButton, QSpinBox, QStyle, QTabWidget,
    QTableView, QTextBrowser, QTextEdit, QVBoxLayout,
    QWidget,
)

from app_utils import BulkReportPDF, FPDF_AVAILABLE, GenericTextReportPDF, _get_default_export_path
from catasto_exceptions import DBMError, DBDataError, DBNotFoundError, DBUniqueConstraintError  # noqa: F401
from dialogs import (
    AlberoGeneralogicoDialog, ConfrontoPartiteDialog,
    ComuneSelectionDialog, PartitaSearchDialog, PossessoreSelectionDialog,
)
from foliarium.ui.widgets.custom import LazyLoadedWidget

if TYPE_CHECKING:
    from catasto_db_manager import CatastoDBManager

logger = logging.getLogger("CatastoGUI.reporting_widgets")
from foliarium.ui.widgets.reporting.model import SimpleRowsModel


class StatisticheWidget(LazyLoadedWidget):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)  # Chiama il costruttore della classe base
        self.db_manager = db_manager
        self.comune_filter_id = None
        # Il self.logger e self._data_loaded sono già gestiti da LazyLoadedWidget

        self._initUI()

    def _initUI(self):
        """Crea l'interfaccia utente, riorganizzata per maggiore chiarezza."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(12)

        title = QLabel("Statistiche")
        title.setObjectName("pageTitle")
        main_layout.addWidget(title)
        subtitle = QLabel("Visualizza statistiche aggregate per comune, tipologia immobili e grafici di distribuzione.")
        subtitle.setObjectName("pageSubtitle")
        main_layout.addWidget(subtitle)

        # Tab principale per separare Statistiche da Manutenzione
        self.main_tabs = QTabWidget()
        main_layout.addWidget(self.main_tabs)

        # --- Contenitore per il tab Statistiche ---
        stats_container_widget = QWidget()
        stats_container_layout = QVBoxLayout(stats_container_widget)
        
        # Sotto-tab per i diversi tipi di statistiche
        stats_sub_tabs = QTabWidget()
        stats_container_layout.addWidget(stats_sub_tabs)
        
        # --- Aggiunta dei tab statistici al sotto-tab ---
        stats_comune_tab = self._create_stats_comune_tab()
        stats_sub_tabs.addTab(stats_comune_tab, "Statistiche per Comune")
        
        immobili_tab = self._create_immobili_tipologia_tab()
        stats_sub_tabs.addTab(immobili_tab, "Immobili per Tipologia")

        grafici_tab = self._create_grafici_tab()
        stats_sub_tabs.addTab(grafici_tab, "Grafici")

        # --- Contenitore per il tab Manutenzione ---
        maintenance_tab = self._create_maintenance_tab()

        # Aggiunta dei tab principali
        self.main_tabs.addTab(stats_container_widget, "📊 Statistiche")
        self.main_tabs.addTab(maintenance_tab, "🔧 Manutenzione Database")
        
    def _create_stats_comune_tab(self):
        """Crea il widget per il tab 'Statistiche per Comune'."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        refresh_button = QPushButton("Aggiorna Statistiche Comuni")
        refresh_button.clicked.connect(self.refresh_stats_comune)
        self._stats_comune_model = SimpleRowsModel(
            ["Comune", "Provincia", "Totale Partite", "Partite Attive",
             "Partite Inattive", "Totale Possessori", "Totale Immobili"],
            parent=self, numeric_cols=[2, 3, 4, 5, 6])
        self.stats_comune_table = QTableView()
        self.stats_comune_table.setModel(self._stats_comune_model)
        self.stats_comune_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.stats_comune_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.stats_comune_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.stats_comune_table.setAlternatingRowColors(True)
        self.stats_comune_table.setSortingEnabled(True)
        self.stats_comune_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.stats_comune_table.horizontalHeader().setStretchLastSection(True)
        self.stats_comune_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.stats_comune_table.customContextMenuRequested.connect(self._apri_menu_stats_comune)
        layout.addWidget(refresh_button)
        layout.addWidget(self.stats_comune_table)
        return widget

    def _create_immobili_tipologia_tab(self):
        """Crea il widget per il tab 'Immobili per Tipologia'."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        filter_layout = QHBoxLayout()
        self.comune_filter_button = QPushButton("Filtra per Comune...")
        self.comune_filter_button.clicked.connect(self.filter_immobili_per_comune)
        self.comune_filter_display = QLabel("Visualizzando tutti i comuni")
        self.clear_filter_button = QPushButton("Rimuovi Filtro")
        self.clear_filter_button.clicked.connect(self.clear_immobili_filter)
        filter_layout.addWidget(self.comune_filter_button)
        filter_layout.addWidget(self.comune_filter_display)
        filter_layout.addWidget(self.clear_filter_button)
        layout.addLayout(filter_layout)
        refresh_button = QPushButton("Aggiorna Statistiche Immobili")
        refresh_button.clicked.connect(self.refresh_immobili_tipologia)
        layout.addWidget(refresh_button)
        self._immobili_stats_model = SimpleRowsModel(
            ["Comune", "Classificazione", "Numero Immobili", "Totale Piani",
             "Totale Vani", "Media Vani/Immobile"],
            parent=self, numeric_cols=[2, 3, 4, 5])
        self.immobili_table = QTableView()
        self.immobili_table.setModel(self._immobili_stats_model)
        self.immobili_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.immobili_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.immobili_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.immobili_table.setAlternatingRowColors(True)
        self.immobili_table.setSortingEnabled(True)
        self.immobili_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.immobili_table.horizontalHeader().setStretchLastSection(True)
        self.immobili_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.immobili_table.customContextMenuRequested.connect(self._apri_menu_immobili_stats)
        layout.addWidget(self.immobili_table)
        return widget

    def _create_grafici_tab(self):
        """Crea il tab con grafici statistici via matplotlib."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        try:
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
            from matplotlib.figure import Figure
            import matplotlib
            matplotlib.use('QtAgg')

            btn_aggiorna = QPushButton("Aggiorna Grafici")
            btn_aggiorna.clicked.connect(self._aggiorna_grafici)
            layout.addWidget(btn_aggiorna)

            # Figura matplotlib con 3 assi
            self._fig = Figure(figsize=(10, 8), tight_layout=True)
            self._ax_partite = self._fig.add_subplot(2, 2, 1)
            self._ax_stato   = self._fig.add_subplot(2, 2, 2)
            self._ax_variaz  = self._fig.add_subplot(2, 1, 2)
            self._canvas = FigureCanvas(self._fig)
            layout.addWidget(self._canvas, 1)
            self._matplotlib_ok = True
        except Exception as e:
            self._matplotlib_ok = False
            lbl = QLabel(f"Grafici non disponibili: {e}\n\nInstalla matplotlib: pip install matplotlib")
            lbl.setWordWrap(True)
            layout.addWidget(lbl)

        return widget

    def _aggiorna_grafici(self):
        if not getattr(self, '_matplotlib_ok', False):
            return
        try:
            stats = self.db_manager.get_statistiche_comune() or []

            # --- Grafico 1: Partite per comune (bar orizzontale, top 10) ---
            ax = self._ax_partite
            ax.clear()
            dati = sorted(stats, key=lambda r: r.get('totale_partite', 0), reverse=True)[:10]
            comuni = [r.get('comune', '') for r in dati]
            totali = [r.get('totale_partite', 0) for r in dati]
            ax.barh(comuni[::-1], totali[::-1], color='steelblue')
            ax.set_title('Partite per comune (top 10)')
            ax.set_xlabel('Totale partite')

            # --- Grafico 2: Stato partite (torta attive/inattive) ---
            ax2 = self._ax_stato
            ax2.clear()
            tot_attive  = sum(r.get('partite_attive', 0)   for r in stats)
            tot_inattive = sum(r.get('partite_inattive', 0) for r in stats)
            if tot_attive + tot_inattive > 0:
                ax2.pie([tot_attive, tot_inattive],
                        labels=['Attive', 'Inattive'],
                        colors=['#4CAF50', '#F44336'],
                        autopct='%1.1f%%', startangle=90)
            ax2.set_title('Stato partite (totale)')

            # --- Grafico 3: Variazioni per anno ---
            ax3 = self._ax_variaz
            ax3.clear()
            try:
                variaz = self.db_manager.get_elenco_variazioni_per_esportazione(None) or []
                anni: dict = {}
                for v in variaz:
                    data = v.get('data_variazione') or ''
                    anno = str(data)[:4]
                    if anno.isdigit():
                        anni[anno] = anni.get(anno, 0) + 1
                if anni:
                    anni_ord = sorted(anni.keys())
                    ax3.bar(anni_ord, [anni[a] for a in anni_ord], color='darkorange')
                    ax3.set_title('Variazioni per anno')
                    ax3.set_xlabel('Anno')
                    ax3.set_ylabel('N. variazioni')
                    ax3.tick_params(axis='x', rotation=45)
            except Exception:
                ax3.set_title('Variazioni per anno (dati non disponibili)')

            self._canvas.draw()
        except Exception as e:
            self.logger.error(f"Errore aggiornamento grafici: {e}", exc_info=True)

    def _create_maintenance_tab(self):
        """Crea il widget per il tab 'Manutenzione'."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        group = QGroupBox("Operazioni di Manutenzione")
        group_layout = QVBoxLayout(group)
        
        # Sezione Viste
        viste_label = QLabel("Le viste materializzate migliorano le performance delle statistiche. Aggiornale periodicamente.")
        viste_label.setWordWrap(True)
        self.update_views_button = QPushButton("Aggiorna Tutte le Viste Materializzate")
        self.update_views_button.clicked.connect(self.update_all_views)
        group_layout.addWidget(viste_label)
        group_layout.addWidget(self.update_views_button)
        
        group_layout.addWidget(QFrame(self, frameShape=QFrame.Shape.HLine))

        
        layout.addWidget(group)

        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setPlaceholderText("L'esito delle operazioni di manutenzione apparirà qui...")
        layout.addWidget(self.status_text, 1) # Dà più spazio al log
        return widget

    def _load_data_on_first_show(self):
        """Carica i dati iniziali la prima volta che il tab viene mostrato."""
        self.logger.info("StatisticheWidget: Esecuzione lazy loading...")
        self.refresh_stats_comune()
        self.refresh_immobili_tipologia()
        self._aggiorna_grafici()

    def refresh_stats_comune(self):
        self.logger.info("Aggiornamento statistiche comuni...")
        try:
            stats = self.db_manager.get_statistiche_comune() or []
            self._stats_comune_model.load([
                [s.get('comune', ''), s.get('provincia', ''),
                 s.get('totale_partite', 0), s.get('partite_attive', 0),
                 s.get('partite_inattive', 0), s.get('totale_possessori', 0),
                 s.get('totale_immobili', 0)]
                for s in stats
            ])
            if stats:
                self.stats_comune_table.resizeColumnsToContents()
            self.log_status("Statistiche comuni aggiornate con successo.")
        except DBMError as e:
            self.log_status(f"Errore DB durante l'aggiornamento delle statistiche comuni: {e}", error=True)
            QMessageBox.critical(self, "Errore", f"Impossibile caricare le statistiche:\n{e}")

    def filter_immobili_per_comune(self):
        dialog = ComuneSelectionDialog(self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_comune_id:
            self.comune_filter_id = dialog.selected_comune_id
            self.comune_filter_display.setText(f"Comune: {dialog.selected_comune_name}")
            self.refresh_immobili_tipologia()

    def clear_immobili_filter(self):
        self.comune_filter_id = None
        self.comune_filter_display.setText("Visualizzando tutti i comuni")
        self.refresh_immobili_tipologia()

    def refresh_immobili_tipologia(self):
        self.logger.info("Aggiornamento statistiche immobili per tipologia...")
        try:
            stats = self.db_manager.get_immobili_per_tipologia(self.comune_filter_id) or []
            rows = []
            for s in stats:
                num_immobili = s.get('numero_immobili', 0)
                totale_vani = s.get('totale_vani', 0)
                media_vani = round(totale_vani / num_immobili, 2) if num_immobili > 0 else 0
                rows.append([
                    s.get('comune_nome', ''), s.get('classificazione', 'N/D'),
                    num_immobili, s.get('totale_piani', 0),
                    totale_vani, media_vani,
                ])
            self._immobili_stats_model.load(rows)
            if rows:
                self.immobili_table.resizeColumnsToContents()
            status_text = "Statistiche immobili aggiornate"
            if self.comune_filter_id:
                status_text += f" (filtrate per {self.comune_filter_display.text()})"
            self.log_status(status_text + ".")
        except DBMError as e:
            self.log_status(f"Errore DB durante l'aggiornamento delle statistiche immobili: {e}", error=True)
            QMessageBox.critical(self, "Errore", f"Impossibile caricare le statistiche:\n{e}")

    def update_all_views(self):
        self.log_status("Avvio aggiornamento di tutte le viste materializzate...")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            if self.db_manager.refresh_materialized_views():
                self.log_status("Aggiornamento viste completato con successo.")
                self.refresh_stats_comune()
                self.refresh_immobili_tipologia()
            else:
                self.log_status("ERRORE: Aggiornamento viste non riuscito. Controllare i log.", error=True)
        finally:
            QApplication.restoreOverrideCursor()

    
    def log_status(self, message, error=False):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        if error:
            self.status_text.append(f"<font color='red'>{formatted_message}</font>")
        else:
            self.status_text.append(formatted_message)
        self.status_text.verticalScrollBar().setValue(self.status_text.verticalScrollBar().maximum())
        QApplication.processEvents()

    def _apri_menu_stats_comune(self, position: QPoint):
        """Context menu sulla tabella statistiche per comune."""
        index = self.stats_comune_table.indexAt(position)
        if not index.isValid():
            return
        row = index.row()
        values = self._stats_comune_model.row_at(row)
        comune = str(values[0]) if len(values) > 0 and values[0] is not None else ""
        prov = str(values[1]) if len(values) > 1 and values[1] is not None else ""

        menu = QMenu(self.stats_comune_table)
        if comune:
            menu.addAction(f"Copia comune  ({comune})").triggered.connect(
                lambda: QApplication.clipboard().setText(comune))
        if prov:
            menu.addAction(f"Copia provincia  ({prov})").triggered.connect(
                lambda: QApplication.clipboard().setText(prov))
        menu.addSeparator()
        menu.addAction("Copia riga intera").triggered.connect(
            lambda: QApplication.clipboard().setText("\t".join(str(v) if v is not None else "" for v in values)))
        menu.exec(self.stats_comune_table.viewport().mapToGlobal(position))

    def _apri_menu_immobili_stats(self, position: QPoint):
        """Context menu sulla tabella statistiche immobili per tipologia."""
        index = self.immobili_table.indexAt(position)
        if not index.isValid():
            return
        row = index.row()
        values = self._immobili_stats_model.row_at(row)
        comune = str(values[0]) if len(values) > 0 and values[0] is not None else ""
        classificazione = str(values[1]) if len(values) > 1 and values[1] is not None else ""

        menu = QMenu(self.immobili_table)
        if comune:
            menu.addAction(f"Copia comune  ({comune})").triggered.connect(
                lambda: QApplication.clipboard().setText(comune))
        if classificazione:
            menu.addAction(f"Copia classificazione  ({classificazione})").triggered.connect(
                lambda: QApplication.clipboard().setText(classificazione))
        menu.addSeparator()
        menu.addAction("Copia riga intera").triggered.connect(
            lambda: QApplication.clipboard().setText("\t".join(str(v) if v is not None else "" for v in values)))
        menu.exec(self.immobili_table.viewport().mapToGlobal(position))




