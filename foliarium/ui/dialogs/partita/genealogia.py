"""Dialog albero genealogico e confronto partite."""

import logging
import os
from datetime import date
from typing import Optional, Dict, Any

from PyQt6.QtCore import (QDate, Qt, QTimer)
from PyQt6.QtGui import (QBrush, QColor)
from PyQt6.QtWidgets import (QAbstractItemView, QApplication,
                             QCheckBox, QComboBox, QDateEdit,
                             QDialog, QDoubleSpinBox,
                             QFileDialog, QFormLayout, QGridLayout, QGroupBox,
                             QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                             QMessageBox, QPushButton, QSpinBox, QStyle,
                             QTabWidget, QSplitter, QTableWidget,
                             QTableWidgetItem, QTextEdit, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget, QTextBrowser,
                             QDialogButtonBox)

from catasto_db_manager import CatastoDBManager
from foliarium.ui.widgets.custom import ImmobiliTableWidget

from app_utils import (GenericTextReportPDF, FPDF_AVAILABLE, prompt_to_open_file)
from foliarium.ui.dialogs.export_ import PDFApreviewDialog

from foliarium.ui.dialogs.admin import datetime_to_qdate, qdate_to_datetime

try:
    from catasto_db_manager import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError
except ImportError:
    class DBMError(Exception): pass
    class DBUniqueConstraintError(DBMError): pass
    class DBNotFoundError(DBMError): pass
    class DBDataError(DBMError): pass


class AlberoGeneralogicoDialog(QDialog):
    """Visualizza interattivamente la catena genealogica di una partita catastale."""

    # Colori nodi albero
    _COLOR_ROOT = QColor("#E3F2FD")
    _COLOR_SECT_PRE = QColor("#FFF3E0")
    _COLOR_NODE_PRE = QColor("#FFF8E1")
    _COLOR_SECT_SUC = QColor("#E8F5E9")
    _COLOR_NODE_SUC = QColor("#F1F8E9")

    def __init__(self, partita_id: int, db_manager, parent=None):
        super().__init__(parent)
        self.partita_id = partita_id
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")
        self.setWindowTitle("Albero Genealogico Partita")
        self.setMinimumSize(900, 600)
        self._dati = None
        self._init_ui()
        self._carica_dati()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Header
        self._header_label = QLabel()
        self._header_label.setWordWrap(True)
        layout.addWidget(self._header_label)

        # Splitter orizzontale: albero | dettaglio
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # QTreeWidget con 5 colonne
        self._tree = QTreeWidget()
        self._tree.setColumnCount(5)
        self._tree.setHeaderLabels(["Partita / Comune", "Tipo Variazione", "Data", "Possessori", "Stato"])
        self._tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.header().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._tree.header().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.itemClicked.connect(self._on_item_clicked)
        splitter.addWidget(self._tree)

        # QTextBrowser dettaglio
        self._detail = QTextBrowser()
        self._detail.setMinimumWidth(260)
        self._detail.setPlaceholderText("Seleziona un nodo per vedere i dettagli.")
        splitter.addWidget(self._detail)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

        # Barra pulsanti
        btn_layout = QHBoxLayout()
        btn_report = QPushButton("Apri Report Testo")
        btn_report.clicked.connect(self._apri_report_testo)
        btn_chiudi = QPushButton("Chiudi")
        btn_chiudi.clicked.connect(self.accept)
        btn_layout.addWidget(btn_report)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_chiudi)
        layout.addLayout(btn_layout)

    def _carica_dati(self):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self._dati = self.db_manager.get_genealogia_partita(self.partita_id)
        except Exception as e:
            self.logger.error(f"Errore caricamento genealogia: {e}", exc_info=True)
            self._dati = None
        finally:
            QApplication.restoreOverrideCursor()

        if not self._dati:
            QMessageBox.warning(self, "Partita non trovata",
                                f"Nessuna partita trovata con ID {self.partita_id}.")
            self.accept()
            return
        self._popola_albero()

    def _fmt_partita(self, p: dict) -> str:
        num = str(p.get('numero_partita', ''))
        suf = (p.get('suffisso_partita') or '').strip()
        comune = p.get('comune_nome', '')
        return f"N.{num}{(' (' + suf + ')') if suf else ''} — {comune}"

    def _fmt_data(self, val) -> str:
        if val is None:
            return ''
        return str(val)[:10]

    def _set_row_bg(self, item: QTreeWidgetItem, color: QColor):
        brush = QBrush(color)
        for col in range(5):
            item.setBackground(col, brush)

    def _popola_albero(self):
        p = self._dati['partita']
        predecessori = self._dati['predecessori']
        successori = self._dati['successori']

        # Aggiorna header
        self._header_label.setText(
            f"<b>Albero genealogico — {self._fmt_partita(p)}</b>"
            f" &nbsp;·&nbsp; Stato: <i>{p.get('stato', '')}</i>"
            f" &nbsp;·&nbsp; Impianto: {self._fmt_data(p.get('data_impianto'))}"
        )

        self._tree.clear()

        # Nodo root
        root = QTreeWidgetItem(self._tree)
        root.setText(0, self._fmt_partita(p))
        root.setText(4, p.get('stato', ''))
        root.setData(0, Qt.ItemDataRole.UserRole, {'tipo': 'root', 'dati': p})
        self._set_row_bg(root, self._COLOR_ROOT)
        font = root.font(0); font.setBold(True); root.setFont(0, font)

        # Sezione Predecessori
        sect_pre = QTreeWidgetItem(root)
        sect_pre.setText(0, f"Predecessori ({len(predecessori)})")
        self._set_row_bg(sect_pre, self._COLOR_SECT_PRE)
        font_i = sect_pre.font(0); font_i.setItalic(True); sect_pre.setFont(0, font_i)
        sect_pre.setData(0, Qt.ItemDataRole.UserRole, {'tipo': 'sezione'})
        for pre in predecessori:
            child = QTreeWidgetItem(sect_pre)
            child.setText(0, self._fmt_partita(pre))
            child.setText(1, pre.get('tipo_variazione', '') or '')
            child.setText(2, self._fmt_data(pre.get('data_variazione')))
            child.setText(3, pre.get('possessori', '') or '')
            child.setText(4, pre.get('stato', '') or '')
            child.setData(0, Qt.ItemDataRole.UserRole, {'tipo': 'predecessore', 'dati': pre})
            self._set_row_bg(child, self._COLOR_NODE_PRE)

        # Sezione Successori
        sect_suc = QTreeWidgetItem(root)
        sect_suc.setText(0, f"Successori ({len(successori)})")
        self._set_row_bg(sect_suc, self._COLOR_SECT_SUC)
        font_i2 = sect_suc.font(0); font_i2.setItalic(True); sect_suc.setFont(0, font_i2)
        sect_suc.setData(0, Qt.ItemDataRole.UserRole, {'tipo': 'sezione'})
        for suc in successori:
            child = QTreeWidgetItem(sect_suc)
            child.setText(0, self._fmt_partita(suc))
            child.setText(1, suc.get('tipo_variazione', '') or '')
            child.setText(2, self._fmt_data(suc.get('data_variazione')))
            child.setText(3, suc.get('possessori', '') or '')
            child.setText(4, suc.get('stato', '') or '')
            child.setData(0, Qt.ItemDataRole.UserRole, {'tipo': 'successore', 'dati': suc})
            self._set_row_bg(child, self._COLOR_NODE_SUC)

        self._tree.expandAll()

    def _on_item_clicked(self, item: QTreeWidgetItem, _col: int):
        payload = item.data(0, Qt.ItemDataRole.UserRole)
        if not payload or payload.get('tipo') == 'sezione':
            self._detail.clear()
            return
        d = payload.get('dati', {})
        tipo = payload.get('tipo', '')
        etichetta = {'root': 'Partita corrente', 'predecessore': 'Predecessore', 'successore': 'Successore'}.get(tipo, '')
        html = f"""
        <h3>{etichetta}</h3>
        <table cellspacing="4">
          <tr><td><b>Partita</b></td><td>{self._fmt_partita(d)}</td></tr>
          <tr><td><b>ID</b></td><td>{d.get('id', '')}</td></tr>
          <tr><td><b>Tipo</b></td><td>{d.get('tipo', '')}</td></tr>
          <tr><td><b>Stato</b></td><td>{d.get('stato', '')}</td></tr>
          <tr><td><b>Impianto</b></td><td>{self._fmt_data(d.get('data_impianto'))}</td></tr>
          <tr><td><b>Chiusura</b></td><td>{self._fmt_data(d.get('data_chiusura'))}</td></tr>
          <tr><td><b>Possessori</b></td><td>{d.get('possessori', '') or '—'}</td></tr>
        """
        if tipo in ('predecessore', 'successore'):
            html += f"""
          <tr><td><b>Variazione</b></td><td>{d.get('tipo_variazione', '') or '—'}</td></tr>
          <tr><td><b>Data variazione</b></td><td>{self._fmt_data(d.get('data_variazione'))}</td></tr>
          <tr><td><b>Nominativo rif.</b></td><td>{d.get('nominativo_riferimento', '') or '—'}</td></tr>
            """
        html += "</table>"
        self._detail.setHtml(html)

    def _apri_report_testo(self):
        if not self.db_manager:
            return
        testo = self.db_manager.genera_report_genealogico(self.partita_id)
        if not testo:
            QMessageBox.information(self, "Report", "Nessun report disponibile per questa partita.")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Report Genealogico Testuale")
        dlg.setMinimumSize(600, 450)
        v = QVBoxLayout(dlg)
        tb = QTextBrowser()
        tb.setPlainText(testo)
        v.addWidget(tb)
        btn = QPushButton("Chiudi"); btn.clicked.connect(dlg.accept)
        hl = QHBoxLayout(); hl.addStretch(); hl.addWidget(btn)
        v.addLayout(hl)
        dlg.exec()


class ConfrontoPartiteDialog(QDialog):
    """Confronto diff visuale tra due partite catastali (possessori e immobili)."""

    _COLOR_SOLO_A  = QColor("#FFCDD2")   # rosso chiaro — rimosso / solo in A
    _COLOR_SOLO_B  = QColor("#C8E6C9")   # verde chiaro — aggiunto / solo in B
    _COLOR_COMUNE  = QColor("#FFFFFF")   # bianco       — presente in entrambe

    def __init__(self, db_manager, partita_id_a: int = 0, partita_id_b: int = 0, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Confronto tra due Partite")
        self.setMinimumSize(900, 620)
        self._init_ui(partita_id_a, partita_id_b)

    def _init_ui(self, id_a: int, id_b: int):
        layout = QVBoxLayout(self)

        # --- Selezione partite ---
        sel_group = QGroupBox("Seleziona le due partite da confrontare")
        sel_layout = QHBoxLayout(sel_group)
        sel_layout.addWidget(QLabel("Partita A (base):"))
        self._spin_a = QSpinBox(); self._spin_a.setRange(1, 9999999); self._spin_a.setValue(max(id_a, 1))
        sel_layout.addWidget(self._spin_a)
        sel_layout.addSpacing(20)
        sel_layout.addWidget(QLabel("Partita B (confronto):"))
        self._spin_b = QSpinBox(); self._spin_b.setRange(1, 9999999); self._spin_b.setValue(max(id_b, 1))
        sel_layout.addWidget(self._spin_b)
        btn_confronta = QPushButton("Confronta")
        btn_confronta.clicked.connect(self._esegui_confronto)
        sel_layout.addWidget(btn_confronta)
        sel_layout.addStretch()
        layout.addWidget(sel_group)

        # --- Header riepilogativo ---
        self._header_label = QLabel("Seleziona due partite e premi Confronta.")
        self._header_label.setWordWrap(True)
        layout.addWidget(self._header_label)

        # --- Tab Possessori / Immobili ---
        self._tabs = QTabWidget()

        # Tab Possessori
        self._tbl_poss = self._make_table(["Nome Possessore", "Titolo", "Quota", "Stato"])
        self._tabs.addTab(self._tbl_poss, "Possessori")

        # Tab Immobili
        self._tbl_imm = self._make_table(["Natura", "Classificazione", "Località", "Piani", "Vani", "Consistenza", "Stato"])
        self._tabs.addTab(self._tbl_imm, "Immobili")

        layout.addWidget(self._tabs, 1)

        # Legenda
        leg_layout = QHBoxLayout()
        for color, testo in [(self._COLOR_SOLO_A, "Solo in A (rimosso)"),
                              (self._COLOR_SOLO_B, "Solo in B (aggiunto)"),
                              (self._COLOR_COMUNE, "Presente in entrambe")]:
            lbl = QLabel(f"  {testo}  ")
            lbl.setAutoFillBackground(True)
            p = lbl.palette(); p.setColor(lbl.backgroundRole(), color); lbl.setPalette(p)
            leg_layout.addWidget(lbl)
        leg_layout.addStretch()
        btn_chiudi = QPushButton("Chiudi"); btn_chiudi.clicked.connect(self.accept)
        leg_layout.addWidget(btn_chiudi)
        layout.addLayout(leg_layout)

    def _make_table(self, headers: list) -> QTableWidget:
        tbl = QTableWidget()
        tbl.setColumnCount(len(headers))
        tbl.setHorizontalHeaderLabels(headers)
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tbl.setAlternatingRowColors(False)
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, len(headers)):
            tbl.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        return tbl

    def _esegui_confronto(self):
        id_a = self._spin_a.value()
        id_b = self._spin_b.value()
        if id_a == id_b:
            QMessageBox.warning(self, "Stessa partita", "Seleziona due ID partita diversi.")
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            dati_a = self.db_manager.get_partita_details(id_a)
            dati_b = self.db_manager.get_partita_details(id_b)
        finally:
            QApplication.restoreOverrideCursor()
        if not dati_a:
            QMessageBox.warning(self, "Non trovata", f"Partita A (ID {id_a}) non trovata."); return
        if not dati_b:
            QMessageBox.warning(self, "Non trovata", f"Partita B (ID {id_b}) non trovata."); return

        lbl_a = f"N.{dati_a['numero_partita']} — {dati_a.get('comune_nome','')}"
        lbl_b = f"N.{dati_b['numero_partita']} — {dati_b.get('comune_nome','')}"
        self._header_label.setText(
            f"<b>A:</b> {lbl_a} &nbsp;|&nbsp; <b>B:</b> {lbl_b} &nbsp;·&nbsp; "
            f"Verde = aggiunto in B &nbsp;·&nbsp; Rosso = presente solo in A"
        )
        self._popola_possessori(dati_a.get('possessori', []), dati_b.get('possessori', []))
        self._popola_immobili(dati_a.get('immobili', []), dati_b.get('immobili', []))

    def _chiave_possessore(self, p: dict) -> str:
        return p.get('nome_completo', '').strip().lower()

    def _chiave_immobile(self, i: dict) -> str:
        return f"{i.get('natura','')}{i.get('localita_nome','')}{i.get('classificazione','')}".lower()

    def _set_row_color(self, tbl: QTableWidget, row: int, color: QColor):
        brush = QBrush(color)
        for col in range(tbl.columnCount()):
            item = tbl.item(row, col)
            if item:
                item.setBackground(brush)

    def _popola_possessori(self, poss_a: list, poss_b: list):
        chiavi_a = {self._chiave_possessore(p): p for p in poss_a}
        chiavi_b = {self._chiave_possessore(p): p for p in poss_b}
        tutte = sorted(set(chiavi_a) | set(chiavi_b))
        tbl = self._tbl_poss
        tbl.setRowCount(len(tutte))
        for r, k in enumerate(tutte):
            if k in chiavi_a and k in chiavi_b:
                p = chiavi_a[k]; stato = "Entrambe"; color = self._COLOR_COMUNE
            elif k in chiavi_a:
                p = chiavi_a[k]; stato = "Solo in A"; color = self._COLOR_SOLO_A
            else:
                p = chiavi_b[k]; stato = "Solo in B"; color = self._COLOR_SOLO_B
            for c, v in enumerate([p.get('nome_completo',''), p.get('titolo',''), p.get('quota',''), stato]):
                tbl.setItem(r, c, QTableWidgetItem(str(v) if v else ''))
            self._set_row_color(tbl, r, color)

    def _popola_immobili(self, imm_a: list, imm_b: list):
        chiavi_a = {self._chiave_immobile(i): i for i in imm_a}
        chiavi_b = {self._chiave_immobile(i): i for i in imm_b}
        tutte = sorted(set(chiavi_a) | set(chiavi_b))
        tbl = self._tbl_imm
        tbl.setRowCount(len(tutte))
        for r, k in enumerate(tutte):
            if k in chiavi_a and k in chiavi_b:
                i = chiavi_a[k]; stato = "Entrambe"; color = self._COLOR_COMUNE
            elif k in chiavi_a:
                i = chiavi_a[k]; stato = "Solo in A"; color = self._COLOR_SOLO_A
            else:
                i = chiavi_b[k]; stato = "Solo in B"; color = self._COLOR_SOLO_B
            vals = [i.get('natura',''), i.get('classificazione',''), i.get('localita_nome',''),
                    str(i.get('numero_piani','') or ''), str(i.get('numero_vani','') or ''),
                    str(i.get('consistenza','') or ''), stato]
            for c, v in enumerate(vals):
                tbl.setItem(r, c, QTableWidgetItem(v))
            self._set_row_color(tbl, r, color)


# ---------------------------------------------------------------------------
# SMTPSettingsDialog — Impostazioni notifiche email
# ---------------------------------------------------------------------------

