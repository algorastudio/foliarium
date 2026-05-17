"""
foliarium/ui/widgets/dashboard.py — Dashboard principale post-login.

Estratto da gui_widgets.py (Sprint 3.8 refactor — six-hats).

Contiene:
- _DashboardLoaderWorker (QThread): esegue le 3 query dashboard in background
- DashboardWidget (QWidget): vista riepilogo statistiche + attività recente +
  ricerca globale + azioni rapide
"""

from __future__ import annotations

import logging
from typing import Dict, Optional, TYPE_CHECKING

from PyQt6.QtCore import QPoint, Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from config import APP_VERSION
from foliarium.ui.widgets.custom import StatCard

if TYPE_CHECKING:
    from catasto_db_manager import CatastoDBManager  # noqa: F401


logger = logging.getLogger("CatastoGUI.dashboard")


class _DashboardLoaderWorker(QThread):
    """Esegue le tre query della dashboard in background per non bloccare la UI."""
    stats_ready = pyqtSignal(dict)
    sessions_ready = pyqtSignal(list)
    ultimi_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self._db = db_manager

    def run(self):
        try:
            self.stats_ready.emit(self._db.get_dashboard_stats() or {})
            self.sessions_ready.emit(self._db.get_recent_session_logs(limit=5) or [])
            self.ultimi_ready.emit(self._db.get_ultimi_inserimenti_dashboard(limit=3) or {})
        except Exception as e:
            self.error_occurred.emit(str(e))


class DashboardWidget(QWidget):
    # Segnali per navigare ad altri tab
    go_to_tab_signal = pyqtSignal(str, str)  # (nome_tab_principale, nome_sotto_tab)
    ricerca_globale_richiesta = pyqtSignal(str)  # query di ricerca globale

    def __init__(self, db_manager: 'CatastoDBManager', current_user_info: Optional[Dict], parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_user_info = current_user_info

        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")
        self.is_admin = self.current_user_info.get('ruolo') == 'admin' if self.current_user_info else False
        self._initUI()
        self.load_initial_data()  # Lazy loading

    def _initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(18)

        # 1. Intestazione — titolo + sottotitolo con ruolo/data
        nome_utente = self.current_user_info.get('nome_completo', 'Utente') if self.current_user_info else 'Utente'
        ruolo_utente = self.current_user_info.get('ruolo', '') if self.current_user_info else ''
        from datetime import datetime as _dt
        try:
            import locale
            try:
                locale.setlocale(locale.LC_TIME, "it_IT.UTF-8")
            except locale.Error:
                pass
            data_str = _dt.now().strftime("%A %d %B %Y, %H:%M")
        except Exception:
            data_str = _dt.now().strftime("%d/%m/%Y, %H:%M")

        header_label = QLabel(f"Benvenuto, {nome_utente}")
        header_label.setObjectName("pageTitle")
        main_layout.addWidget(header_label)

        sub_label = QLabel(f"Ruolo: <b>{ruolo_utente}</b>  ·  {data_str}  ·  v{APP_VERSION}")
        sub_label.setObjectName("pageSubtitle")
        sub_label.setTextFormat(Qt.TextFormat.RichText)
        main_layout.addWidget(sub_label)

        # 2. Ricerca Globale
        search_group = QGroupBox("Ricerca Rapida")
        search_layout = QHBoxLayout(search_group)
        search_layout.setSpacing(10)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Cerca qualsiasi cosa nel catasto — comune, possessore, partita, immobile…")
        self.search_edit.setMinimumHeight(36)
        self.search_button = QPushButton("Cerca")
        self.search_button.setMinimumWidth(110)
        self.search_button.clicked.connect(self._avvia_ricerca_globale)
        self.search_edit.returnPressed.connect(self._avvia_ricerca_globale)
        search_layout.addWidget(self.search_edit, 1)
        search_layout.addWidget(self.search_button)
        main_layout.addWidget(search_group)

        # 3. Statistiche Rapide — StatCard pittate
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)
        self.stat_comuni_card = StatCard("Comuni", "#3F51B5")
        self.stat_partite_card = StatCard("Partite", "#00897B")
        self.stat_possessori_card = StatCard("Possessori", "#F57C00")
        self.stat_immobili_card = StatCard("Immobili", "#C62828")
        for card in (self.stat_comuni_card, self.stat_partite_card,
                     self.stat_possessori_card, self.stat_immobili_card):
            stats_layout.addWidget(card)
        main_layout.addLayout(stats_layout)

        # 4. Ultimi Inserimenti
        recenti_group = QGroupBox("Ultimi Inserimenti")
        recenti_layout = QVBoxLayout(recenti_group)
        self.recenti_tabs = QTabWidget()
        self.recenti_tabs.setMaximumHeight(140)

        self.tab_comuni_recenti = QTableWidget(0, 2)
        self.tab_comuni_recenti.setHorizontalHeaderLabels(["Comune", "Provincia"])
        self.tab_comuni_recenti.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tab_comuni_recenti.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tab_comuni_recenti.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tab_comuni_recenti.verticalHeader().setVisible(False)
        self.recenti_tabs.addTab(self.tab_comuni_recenti, "Comuni")

        self.tab_partite_recenti = QTableWidget(0, 2)
        self.tab_partite_recenti.setHorizontalHeaderLabels(["N. Partita", "Comune"])
        self.tab_partite_recenti.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tab_partite_recenti.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tab_partite_recenti.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tab_partite_recenti.verticalHeader().setVisible(False)
        self.recenti_tabs.addTab(self.tab_partite_recenti, "Partite")

        self.tab_possessori_recenti = QTableWidget(0, 2)
        self.tab_possessori_recenti.setHorizontalHeaderLabels(["Cognome/Nome", "Nome Completo"])
        self.tab_possessori_recenti.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tab_possessori_recenti.horizontalHeader().setStretchLastSection(True)
        self.tab_possessori_recenti.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tab_possessori_recenti.verticalHeader().setVisible(False)
        self.recenti_tabs.addTab(self.tab_possessori_recenti, "Possessori")

        recenti_layout.addWidget(self.recenti_tabs)
        main_layout.addWidget(recenti_group)

        # 5. Attività Recenti e Azioni Rapide
        bottom_layout = QHBoxLayout()

        recent_activity_group = QGroupBox("Attività Utenti Recenti")
        recent_activity_layout = QVBoxLayout(recent_activity_group)
        self.audit_table = QTableWidget()

        self.audit_table.setColumnCount(5)
        self.audit_table.setHorizontalHeaderLabels(["Data/Ora", "Utente", "Azione", "Esito", "Indirizzo IP"])

        self.audit_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.audit_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.audit_table.horizontalHeader().setStretchLastSection(True)
        self.audit_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.audit_table.customContextMenuRequested.connect(self._apri_menu_audit_dashboard)
        recent_activity_layout.addWidget(self.audit_table)
        bottom_layout.addWidget(recent_activity_group, 2)

        actions_group = QGroupBox("Azioni Rapide")
        actions_layout = QVBoxLayout(actions_group)
        btn_new_prop = QPushButton("Registra Nuova Proprietà")
        btn_new_prop.clicked.connect(lambda: self.go_to_tab_signal.emit("Inserimento", "Reg. Proprietà"))
        btn_new_partita = QPushButton("Inserisci Nuova Partita")
        btn_new_partita.clicked.connect(lambda: self.go_to_tab_signal.emit("Inserimento", "Partita"))
        btn_new_consult = QPushButton("Registra Consultazione")
        btn_new_consult.clicked.connect(lambda: self.go_to_tab_signal.emit("Inserimento", "Reg. Consultazione"))
        btn_reports = QPushButton("Vai alla Reportistica")
        btn_reports.clicked.connect(lambda: self.go_to_tab_signal.emit("Report", ""))
        if self.is_admin:
            actions_layout.addSpacing(15)
            btn_backup = QPushButton(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), " Esegui Backup")
            btn_backup.clicked.connect(lambda: self.go_to_tab_signal.emit("Sistema", "Backup/Ripristino DB"))
            actions_layout.addWidget(btn_backup)

        actions_layout.addWidget(btn_new_prop)
        actions_layout.addWidget(btn_new_partita)
        actions_layout.addWidget(btn_new_consult)
        actions_layout.addWidget(btn_reports)
        actions_layout.addStretch()

        # Mini-card stato backup — stilizzata via #backupStatusCard nel QSS
        self.backup_status_label = QLabel("Backup: nessun dato")
        self.backup_status_label.setObjectName("backupStatusCard")
        self.backup_status_label.setWordWrap(True)
        actions_layout.addWidget(self.backup_status_label)

        bottom_layout.addWidget(actions_group, 1)

        main_layout.addLayout(bottom_layout, 1)

    def load_initial_data(self):
        """Avvia il caricamento dei dati dashboard in background (non blocca la UI)."""
        self.logger.info("Avvio caricamento asincrono dati Dashboard...")
        if hasattr(self, '_dash_loader') and self._dash_loader.isRunning():
            return

        self._dash_loader = _DashboardLoaderWorker(self.db_manager, self)
        self._dash_loader.stats_ready.connect(self._on_stats_ready)
        self._dash_loader.sessions_ready.connect(self._on_sessions_ready)
        self._dash_loader.ultimi_ready.connect(self._on_ultimi_ready)
        self._dash_loader.error_occurred.connect(
            lambda msg: self.logger.warning("Errore caricamento dashboard: %s", msg)
        )
        self._dash_loader.start()

    def _on_stats_ready(self, stats: dict):
        self.stat_comuni_card.setValue(stats.get('total_comuni', 0))
        self.stat_partite_card.setValue(stats.get('total_partite', 0))
        self.stat_possessori_card.setValue(stats.get('total_possessori', 0))
        self.stat_immobili_card.setValue(stats.get('total_immobili', 0))

    def _on_sessions_ready(self, session_logs: list):
        self.audit_table.setRowCount(len(session_logs))
        for row, log in enumerate(session_logs):
            ts = log.get('data_login')
            ts_str = ts.strftime("%d/%m/%y %H:%M") if ts else "N/D"
            user_display = log.get('nome_completo') or log.get('username', 'N/D')
            action_display = log.get('azione', 'N/D').replace('_', ' ').title()
            esito_display = "Successo" if log.get('esito') else "Fallito"
            self.audit_table.setItem(row, 0, QTableWidgetItem(ts_str))
            self.audit_table.setItem(row, 1, QTableWidgetItem(user_display))
            self.audit_table.setItem(row, 2, QTableWidgetItem(action_display))
            self.audit_table.setItem(row, 3, QTableWidgetItem(esito_display))
            self.audit_table.setItem(row, 4, QTableWidgetItem(log.get('indirizzo_ip', 'N/D')))
        self.audit_table.resizeColumnsToContents()

    def _on_ultimi_ready(self, ultimi: dict):
        comuni = ultimi.get("comuni", [])
        self.tab_comuni_recenti.setRowCount(len(comuni))
        for i, c in enumerate(comuni):
            self.tab_comuni_recenti.setItem(i, 0, QTableWidgetItem(c.get("nome", "")))
            self.tab_comuni_recenti.setItem(i, 1, QTableWidgetItem(c.get("provincia", "")))
        partite = ultimi.get("partite", [])
        self.tab_partite_recenti.setRowCount(len(partite))
        for i, p in enumerate(partite):
            self.tab_partite_recenti.setItem(i, 0, QTableWidgetItem(str(p.get("numero_partita", ""))))
            self.tab_partite_recenti.setItem(i, 1, QTableWidgetItem(p.get("comune", "")))
        possessori = ultimi.get("possessori", [])
        self.tab_possessori_recenti.setRowCount(len(possessori))
        for i, pos in enumerate(possessori):
            self.tab_possessori_recenti.setItem(i, 0, QTableWidgetItem(pos.get("cognome_nome", "")))
            self.tab_possessori_recenti.setItem(i, 1, QTableWidgetItem(pos.get("nome_completo", "")))

        # Stato backup (legge da QSettings)
        try:
            from PyQt6.QtCore import QSettings
            settings = QSettings()
            last_backup = settings.value("Backup/LastBackupDate", "")
            if last_backup:
                from datetime import datetime as _dt2
                try:
                    backup_dt = _dt2.fromisoformat(last_backup)
                    days_ago = (_dt2.now() - backup_dt).days
                    if days_ago == 0:
                        status, testo = "ok", f"Backup: oggi ({backup_dt.strftime('%H:%M')})"
                    elif days_ago <= 7:
                        status, testo = "warn", f"Backup: {days_ago} giorni fa"
                    else:
                        status, testo = "alert", f"Backup: {days_ago} giorni fa — consigliato!"
                    self.backup_status_label.setText(testo)
                    self.backup_status_label.setProperty("status", status)
                    self.backup_status_label.style().unpolish(self.backup_status_label)
                    self.backup_status_label.style().polish(self.backup_status_label)
                except Exception as _e:
                    logger.debug("Impossibile aggiornare stato backup dalla data '%s': %s", last_backup, _e)
        except Exception as _e:
            logger.debug("Impossibile leggere stato backup da QSettings: %s", _e)

    def _avvia_ricerca_globale(self):
        """Emette un segnale per passare al tab di ricerca globale e inserire il testo."""
        testo_ricerca = self.search_edit.text().strip()
        if not testo_ricerca:
            return
        self.ricerca_globale_richiesta.emit(testo_ricerca)

    def _apri_menu_audit_dashboard(self, position: QPoint):
        """Context menu sulla tabella attività recenti della dashboard."""
        index = self.audit_table.indexAt(position)
        if not index.isValid():
            return
        row = index.row()
        utente_item = self.audit_table.item(row, 1)
        azione_item = self.audit_table.item(row, 2)
        ip_item = self.audit_table.item(row, 4)
        utente = utente_item.text() if utente_item else ""
        azione = azione_item.text() if azione_item else ""
        ip = ip_item.text() if ip_item else ""

        menu = QMenu(self.audit_table)
        if utente:
            menu.addAction(f"Copia utente  ({utente})").triggered.connect(
                lambda: QApplication.clipboard().setText(utente))
        if azione:
            menu.addAction(f"Copia azione  ({azione})").triggered.connect(
                lambda: QApplication.clipboard().setText(azione))
        if ip:
            menu.addAction(f"Copia IP  ({ip})").triggered.connect(
                lambda: QApplication.clipboard().setText(ip))
        menu.exec(self.audit_table.viewport().mapToGlobal(position))


__all__ = [
    "_DashboardLoaderWorker",
    "DashboardWidget",
]
