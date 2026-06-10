"""
import_dialogs.py — Dialog e worker per l'importazione dati in Foliarium.

Estratto da dialogs.py per migliorare la modularità.
Contiene:
  - CSVImportResultDialog    — Riepilogo risultati import CSV
  - ISTATDownloadWorker      — Thread download dati ISTAT comuni
  - _mostra_risultati_import — Helper: dialog riepilogo import batch
  - _popola_preview_tabella  — Helper: anteprima 20 righe in QTableWidget
  - ImportComuniDialog       — Import comuni da CSV o ISTAT
  - OSMLocalitaWorker        — Thread download dati OpenStreetMap
  - ImportLocalitaDialog     — Import località da CSV o OpenStreetMap

Backward compatibility: dialogs.py re-esporta tutte le classi.
"""

import csv
import logging
import urllib.request
from typing import Optional, List, Dict, Tuple, TYPE_CHECKING

from PyQt6.QtCore import (
    QThread, Qt, pyqtSignal,
)
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication,
    QCheckBox, QComboBox,
    QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox,
    QProgressBar, QPushButton, QTabWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)


if TYPE_CHECKING:
    from catasto_db_manager import CatastoDBManager

logger = logging.getLogger("CatastoGUI.import_dialogs")

class CSVImportResultDialog(QDialog):
    """
    Un dialogo per visualizzare i risultati di un'importazione da CSV,
    separando i record importati con successo da quelli con errori.
    """
    def __init__(self, success_data: List[Dict], error_data: List[Tuple[int, Dict, str]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Riepilogo Importazione CSV")
        self.setMinimumSize(700, 500)

        main_layout = QVBoxLayout(self)

        # Messaggio di riepilogo
        summary_text = f"<b>Importazione completata.</b><br>" \
                       f"Record importati con successo: <b>{len(success_data)}</b><br>" \
                       f"Record con errori: <b>{len(error_data)}</b>"
        summary_label = QLabel(summary_text)
        main_layout.addWidget(summary_label)

        # Tab per separare successi ed errori
        tabs = QTabWidget()
        
        # Tab dei successi
        success_table = self._create_table(["ID Assegnato", "Nome Completo", "Comune"], success_data)
        tabs.addTab(success_table, f"✅ Successi ({len(success_data)})")

        # Tab degli errori
        error_table = self._create_error_table(["Riga N.", "Dati Riga", "Errore"], error_data)
        tabs.addTab(error_table, f"❌ Errori ({len(error_data)})")
        
        if not error_data:
            tabs.setTabEnabled(1, False) # Disabilita il tab errori se non ci sono errori

        main_layout.addWidget(tabs)

        # Pulsante OK
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)
        main_layout.addWidget(button_box)

    def _create_table(self, headers: List[str], data: List[Dict]) -> QTableWidget:
        table = QTableWidget(len(data), len(headers))
        table.setHorizontalHeaderLabels(headers)
        for row_idx, row_data in enumerate(data):
            table.setItem(row_idx, 0, QTableWidgetItem(str(row_data.get('id', 'N/A'))))
            table.setItem(row_idx, 1, QTableWidgetItem(row_data.get('nome_completo', '')))
            table.setItem(row_idx, 2, QTableWidgetItem(row_data.get('comune_nome', '')))
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(True)
        return table

    def _create_error_table(self, headers: List[str], data: List[Tuple[int, Dict, str]]) -> QTableWidget:
        table = QTableWidget(len(data), len(headers))
        table.setHorizontalHeaderLabels(headers)
        for row_idx, error_tuple in enumerate(data):
            line_num, row_data, error_msg = error_tuple
            table.setItem(row_idx, 0, QTableWidgetItem(str(line_num)))
            table.setItem(row_idx, 1, QTableWidgetItem(str(row_data)))
            table.setItem(row_idx, 2, QTableWidgetItem(error_msg))
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(True)
        return table


class ISTATDownloadWorker(QThread):
    """QThread che scarica e analizza il file comuni ISTAT in background."""
    progress = pyqtSignal(str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    ISTAT_URL = "https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.csv"
    COL_NOME = "Denominazione in italiano"
    COL_PROVINCIA = "Sigla automobilistica"
    COL_REGIONE = "Denominazione Regione"
    COL_CODICE_CATASTALE = "Codice Catastale del comune"
    COL_SIGLA = "Sigla automobilistica"

    def __init__(self, provincia_filter: str = "", parent=None):
        super().__init__(parent)
        self.provincia_filter = provincia_filter.strip().upper()

    def run(self):
        import io as _io
        try:
            self.progress.emit("Connessione al server ISTAT...")
            req = urllib.request.Request(self.ISTAT_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as response:
                raw = response.read()
            self.progress.emit("Download completato. Analisi dati...")
            text = raw.decode("latin-1")
            reader = csv.DictReader(_io.StringIO(text), delimiter=";")
            required = {self.COL_NOME, self.COL_PROVINCIA, self.COL_REGIONE, self.COL_CODICE_CATASTALE}
            fieldnames = set(reader.fieldnames or [])
            if not required.issubset(fieldnames):
                missing = required - fieldnames
                self.error.emit(
                    f"Il file ISTAT non contiene le colonne attese.\n"
                    f"Mancanti: {', '.join(missing)}\n\n"
                    f"Colonne trovate: {', '.join(sorted(fieldnames))}"
                )
                return
            rows = []
            for row in reader:
                if self.provincia_filter and self.COL_SIGLA in row:
                    sigla = (row.get(self.COL_SIGLA) or "").strip().upper()
                    if sigla != self.provincia_filter:
                        continue
                nome = (row.get(self.COL_NOME) or "").strip()
                if not nome:
                    continue
                rows.append({
                    "nome": nome,
                    "provincia": (row.get(self.COL_PROVINCIA) or "").strip(),
                    "regione": (row.get(self.COL_REGIONE) or "").strip(),
                    "codice_catastale": (row.get(self.COL_CODICE_CATASTALE) or "").strip(),
                })
            self.progress.emit(f"Trovati {len(rows)} comuni. Pronto per l'import.")
            self.finished.emit(rows)
        except Exception as e:
            self.error.emit(f"Errore durante il download: {e}")


def _mostra_risultati_import(parent, entity_label: str, success_rows: list, error_rows: list):
    """Mostra un dialog di riepilogo dopo un import batch."""
    if not error_rows:
        QMessageBox.information(
            parent, "Import completato",
            f"Importazione completata con successo.\n\n"
            f"{entity_label} importati: {len(success_rows)}"
        )
        return

    dlg = QDialog(parent)
    dlg.setWindowTitle("Riepilogo importazione")
    dlg.setMinimumSize(650, 400)
    layout = QVBoxLayout(dlg)

    layout.addWidget(QLabel(
        f"<b>Import completato.</b> "
        f"Successi: <b>{len(success_rows)}</b> &nbsp;|&nbsp; "
        f"Errori: <b>{len(error_rows)}</b>"
    ))

    table = QTableWidget(len(error_rows), 3)
    table.setHorizontalHeaderLabels(["Riga", "Dato", "Errore"])
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    for i, (line_num, row_data, msg) in enumerate(error_rows):
        table.setItem(i, 0, QTableWidgetItem(str(line_num)))
        table.setItem(i, 1, QTableWidgetItem(str(row_data)))
        table.setItem(i, 2, QTableWidgetItem(msg))
    table.resizeColumnsToContents()
    table.horizontalHeader().setStretchLastSection(True)
    layout.addWidget(table)

    bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
    bb.accepted.connect(dlg.accept)
    layout.addWidget(bb)
    dlg.exec()


def _popola_preview_tabella(table: QTableWidget, rows: list, columns: list):
    """Popola una QTableWidget con le prime 20 righe per l'anteprima."""
    preview = rows[:20]
    table.setRowCount(len(preview))
    table.setColumnCount(len(columns))
    table.setHorizontalHeaderLabels([c[0] for c in columns])
    for r_idx, row in enumerate(preview):
        for c_idx, (_, key) in enumerate(columns):
            table.setItem(r_idx, c_idx, QTableWidgetItem(str(row.get(key, ""))))
    table.resizeColumnsToContents()
    table.horizontalHeader().setStretchLastSection(True)


class ImportComuniDialog(QDialog):
    """Dialog per importare comuni da file CSV o da ISTAT."""

    TEMPLATE_HEADERS = "nome;provincia;regione;codice_catastale;data_istituzione;data_soppressione;note"
    TEMPLATE_EXAMPLE = "Firenze;FI;Toscana;D612;01/01/1871;;"
    PREVIEW_COLUMNS = [
        ("Nome", "nome"), ("Provincia", "provincia"), ("Regione", "regione"),
        ("Cod. catastale", "codice_catastale"), ("Data ist.", "data_istituzione"),
        ("Data sopp.", "data_soppressione"), ("Note", "note"),
    ]

    def __init__(self, db_manager: 'CatastoDBManager', parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Importa Comuni")
        self.setMinimumSize(780, 520)
        self._csv_rows: list = []
        self._istat_rows: list = []
        self._istat_worker: Optional[ISTATDownloadWorker] = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_csv_tab(), "Da file CSV")
        self._tabs.addTab(self._build_istat_tab(), "Da ISTAT")
        layout.addWidget(self._tabs)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)

    # --- Tab CSV ---

    def _build_csv_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        info = QLabel(
            "Seleziona un file CSV con separatore <b>;</b>.<br>"
            "Colonne obbligatorie: <b>nome, provincia, regione</b>.<br>"
            "Opzionali: codice_catastale, data_istituzione (GG/MM/AAAA), data_soppressione, note."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        btn_layout = QHBoxLayout()
        btn_template = QPushButton("Scarica template CSV")
        btn_template.clicked.connect(self._scarica_template_csv)
        btn_layout.addWidget(btn_template)

        btn_apri = QPushButton("Seleziona file CSV...")
        btn_apri.clicked.connect(self._seleziona_csv)
        btn_layout.addWidget(btn_apri)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self._csv_path_label = QLabel("Nessun file selezionato.")
        layout.addWidget(self._csv_path_label)

        self._csv_preview = QTableWidget(0, len(self.PREVIEW_COLUMNS))
        self._csv_preview.setHorizontalHeaderLabels([c[0] for c in self.PREVIEW_COLUMNS])
        self._csv_preview.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._csv_preview.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._csv_preview)

        self._csv_import_btn = QPushButton("Importa nel DB")
        self._csv_import_btn.setEnabled(False)
        self._csv_import_btn.clicked.connect(self._importa_csv)
        layout.addWidget(self._csv_import_btn)
        return w

    def _scarica_template_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Salva template CSV", "template_comuni.csv", "File CSV (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write(self.TEMPLATE_HEADERS + "\n")
                f.write(self.TEMPLATE_EXAMPLE + "\n")
            QMessageBox.information(self, "Template salvato", f"Template salvato in:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile salvare il template:\n{e}")

    def _seleziona_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleziona file CSV comuni", "", "File CSV (*.csv);;Tutti i file (*)"
        )
        if not path:
            return
        try:
            with open(path, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter=";")
                required = {"nome", "provincia", "regione"}
                if not required.issubset(set(reader.fieldnames or [])):
                    QMessageBox.warning(
                        self, "Intestazioni mancanti",
                        f"Il file CSV deve contenere almeno: {', '.join(required)}"
                    )
                    return
                self._csv_rows = list(reader)

            self._csv_path_label.setText(f"File: {path}  ({len(self._csv_rows)} righe)")
            _popola_preview_tabella(self._csv_preview, self._csv_rows, self.PREVIEW_COLUMNS)
            self._csv_import_btn.setEnabled(bool(self._csv_rows))
        except Exception as e:
            QMessageBox.critical(self, "Errore lettura CSV", str(e))

    def _importa_csv(self):
        if not self._csv_rows:
            return
        risposta = QMessageBox.question(
            self, "Conferma importazione",
            f"Stai per importare <b>{len(self._csv_rows)}</b> comuni nel database.<br><br>"
            "I record con lo stesso nome potrebbero essere ignorati o aggiornati.<br>"
            "I dati associati (partite, possessori) ai comuni già presenti rimarranno invariati.<br><br>"
            "Procedere con l'importazione?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if risposta != QMessageBox.StandardButton.Yes:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            result = self.db_manager.import_comuni_from_rows(self._csv_rows)
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Errore DB", str(e))
            return
        QApplication.restoreOverrideCursor()
        _mostra_risultati_import(self, "Comuni", result.get("success", []), result.get("errors", []))
        self._csv_rows = []
        self._csv_preview.setRowCount(0)
        self._csv_import_btn.setEnabled(False)
        self._csv_path_label.setText("Nessun file selezionato.")

    # --- Tab ISTAT ---

    ISTAT_PREVIEW_COLUMNS = [
        ("Nome", "nome"), ("Provincia", "provincia"),
        ("Regione", "regione"), ("Cod. catastale", "codice_catastale"),
    ]

    def _build_istat_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        info = QLabel(
            "Scarica l'elenco ufficiale dei comuni italiani dall'ISTAT e importali nel DB.<br>"
            "Filtra per <b>sigla provincia</b> (es. <i>FI</i> per Firenze) oppure lascia vuoto per tutti."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filtro provincia (sigla):"))
        self._istat_sigla_edit = QLineEdit()
        self._istat_sigla_edit.setPlaceholderText("es. SV  (lascia vuoto per tutti)")
        self._istat_sigla_edit.setMaximumWidth(180)
        filter_layout.addWidget(self._istat_sigla_edit)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        btn_layout = QHBoxLayout()
        self._istat_download_btn = QPushButton("Scarica da ISTAT")
        self._istat_download_btn.clicked.connect(self._avvia_download_istat)
        btn_layout.addWidget(self._istat_download_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self._istat_status_label = QLabel("In attesa.")
        layout.addWidget(self._istat_status_label)

        self._istat_progress = QProgressBar()
        self._istat_progress.setRange(0, 0)  # indeterminate
        self._istat_progress.setVisible(False)
        layout.addWidget(self._istat_progress)

        self._istat_preview = QTableWidget(0, len(self.ISTAT_PREVIEW_COLUMNS))
        self._istat_preview.setHorizontalHeaderLabels([c[0] for c in self.ISTAT_PREVIEW_COLUMNS])
        self._istat_preview.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._istat_preview.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._istat_preview)

        self._istat_import_btn = QPushButton("Importa nel DB")
        self._istat_import_btn.setEnabled(False)
        self._istat_import_btn.clicked.connect(self._importa_istat)
        layout.addWidget(self._istat_import_btn)
        return w

    def _avvia_download_istat(self):
        self._istat_rows = []
        self._istat_preview.setRowCount(0)
        self._istat_import_btn.setEnabled(False)
        self._istat_download_btn.setEnabled(False)
        self._istat_progress.setVisible(True)
        self._istat_status_label.setText("Download in corso...")

        sigla = self._istat_sigla_edit.text().strip()
        self._istat_worker = ISTATDownloadWorker(provincia_filter=sigla, parent=self)
        self._istat_worker.progress.connect(self._istat_status_label.setText)
        self._istat_worker.finished.connect(self._on_istat_finished)
        self._istat_worker.error.connect(self._on_istat_error)
        self._istat_worker.start()

    def _on_istat_finished(self, rows: list):
        self._istat_rows = rows
        self._istat_progress.setVisible(False)
        self._istat_download_btn.setEnabled(True)
        _popola_preview_tabella(self._istat_preview, rows, self.ISTAT_PREVIEW_COLUMNS)
        self._istat_import_btn.setEnabled(bool(rows))

    def _on_istat_error(self, msg: str):
        self._istat_progress.setVisible(False)
        self._istat_download_btn.setEnabled(True)
        self._istat_status_label.setText("Errore durante il download.")
        QMessageBox.critical(self, "Errore ISTAT", msg)

    def _importa_istat(self):
        if not self._istat_rows:
            return
        risposta = QMessageBox.question(
            self, "Conferma importazione",
            f"Stai per importare <b>{len(self._istat_rows)}</b> comuni da ISTAT nel database.<br><br>"
            "I record con lo stesso nome potrebbero essere ignorati o aggiornati.<br>"
            "I dati associati ai comuni già presenti rimarranno invariati.<br><br>"
            "Procedere con l'importazione?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if risposta != QMessageBox.StandardButton.Yes:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            result = self.db_manager.import_comuni_from_rows(self._istat_rows)
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Errore DB", str(e))
            return
        QApplication.restoreOverrideCursor()
        _mostra_risultati_import(self, "Comuni", result.get("success", []), result.get("errors", []))
        self._istat_rows = []
        self._istat_preview.setRowCount(0)
        self._istat_import_btn.setEnabled(False)
        self._istat_status_label.setText("Import completato. Scarica di nuovo per un nuovo import.")

    def closeEvent(self, event):
        if self._istat_worker and self._istat_worker.isRunning():
            self._istat_worker.quit()
            self._istat_worker.wait(2000)
        super().closeEvent(event)


class OSMLocalitaWorker(QThread):
    """QThread che scarica strade e luoghi da OpenStreetMap (Overpass API) per un comune."""

    OVERPASS_URL = "https://overpass-api.de/api/interpreter"
    PREFIXES_IT = {
        'Via', 'Viale', 'Corso', 'Piazza', 'Vicolo', 'Largo',
        'Salita', 'Calata', 'Contrada', 'Borgata', 'Regione',
        'Frazione', 'Strada', 'Traversa', 'Passaggio', 'Località',
    }
    PLACE_TAGS = {'hamlet', 'village', 'suburb', 'neighbourhood', 'locality', 'quarter'}

    progress = pyqtSignal(str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, comune_nome: str, include_strade: bool = True,
                 include_luoghi: bool = True, parent=None):
        super().__init__(parent)
        self.comune_nome = comune_nome
        self.include_strade = include_strade
        self.include_luoghi = include_luoghi

    def run(self):
        import urllib.parse
        import json as _json
        try:
            self.progress.emit("Connessione a OpenStreetMap...")
            parts = []
            if self.include_strade:
                parts.append('way["highway"]["name"](area.a);')
            if self.include_luoghi:
                parts.append('node["place"]["name"](area.a);')
            if not parts:
                self.error.emit("Seleziona almeno un tipo di dati (strade o luoghi).")
                return
            query = (
                '[out:json][timeout:90];'
                f'area["boundary"="administrative"]["admin_level"="8"]'
                f'["name"="{self.comune_nome}"]->.a;'
                f'({" ".join(parts)});out tags;'
            )
            data = urllib.parse.urlencode({'data': query}).encode()
            req = urllib.request.Request(
                self.OVERPASS_URL, data=data,
                headers={'User-Agent': 'Foliarium/1.5 (archivio catastale storico)'}
            )
            self.progress.emit("Download dati in corso...")
            with urllib.request.urlopen(req, timeout=90) as resp:
                result = _json.loads(resp.read())

            rows, seen = [], set()
            for el in result.get('elements', []):
                tags = el.get('tags', {})
                nome = tags.get('name', '').strip()
                if not nome:
                    continue
                tipo = self._parse_tipo(nome, tags.get('highway', ''), tags.get('place', ''))
                key = (nome, tipo)
                if key not in seen:
                    seen.add(key)
                    rows.append({'nome': nome, 'tipo': tipo, 'civico': ''})

            self.progress.emit(f"Trovati {len(rows)} elementi. Pronto per l'import.")
            self.finished.emit(rows)
        except Exception as e:
            self.error.emit(f"Errore durante il download: {e}")

    def _parse_tipo(self, nome: str, highway: str, place: str) -> str:
        first = nome.split()[0] if nome else ''
        if first in self.PREFIXES_IT:
            return first
        if place in self.PLACE_TAGS:
            return 'Località'
        return ''


class ImportLocalitaDialog(QDialog):
    """Dialog per importare località da file CSV o da OpenStreetMap per un comune selezionato."""

    TEMPLATE_HEADERS = "nome;tipo;civico"
    TEMPLATE_EXAMPLE = (
        "Via Roma;Via;10\n"
        "Borgata Pianello;Borgata;\n"
        "Regione Valleggia;Regione;\n"
    )
    PREVIEW_COLUMNS = [("Nome", "nome"), ("Tipo", "tipo"), ("Civico", "civico")]
    OSM_PREVIEW_COLUMNS = [("Nome", "nome"), ("Tipo", "tipo")]

    def __init__(self, db_manager: 'CatastoDBManager', parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Importa Località")
        self.setMinimumSize(720, 520)
        self._csv_rows: list = []
        self._osm_rows: list = []
        self._osm_worker: Optional[OSMLocalitaWorker] = None
        self._comuni_map: Dict[str, int] = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Selezione comune (condivisa tra entrambi i tab)
        comune_layout = QHBoxLayout()
        comune_layout.addWidget(QLabel("Comune di riferimento:"))
        self._comune_combo = QComboBox()
        self._comune_combo.setMinimumWidth(280)
        self._comune_combo.currentTextChanged.connect(self._on_comune_changed)
        comune_layout.addWidget(self._comune_combo)
        comune_layout.addStretch()
        layout.addLayout(comune_layout)

        self._carica_comuni()

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_csv_tab(), "Da file CSV")
        self._tabs.addTab(self._build_osm_tab(), "Da OpenStreetMap")
        layout.addWidget(self._tabs)

        # Sincronizza il campo OSM con la selezione iniziale del combo
        self._on_comune_changed(self._comune_combo.currentText())

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)

    def _build_csv_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        info = QLabel(
            "File CSV con separatore <b>;</b>.<br>"
            "Colonna obbligatoria: <b>nome</b>.<br>"
            "Opzionali: <b>tipo</b> (Via, Borgata, Regione, Altro), <b>civico</b> (numero intero)."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        btn_layout = QHBoxLayout()
        btn_template = QPushButton("Scarica template CSV")
        btn_template.clicked.connect(self._scarica_template)
        btn_layout.addWidget(btn_template)
        btn_apri = QPushButton("Seleziona file CSV...")
        btn_apri.clicked.connect(self._seleziona_csv)
        btn_layout.addWidget(btn_apri)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self._path_label = QLabel("Nessun file selezionato.")
        layout.addWidget(self._path_label)

        self._csv_preview = QTableWidget(0, len(self.PREVIEW_COLUMNS))
        self._csv_preview.setHorizontalHeaderLabels([c[0] for c in self.PREVIEW_COLUMNS])
        self._csv_preview.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._csv_preview.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._csv_preview)

        self._csv_import_btn = QPushButton("Importa nel DB")
        self._csv_import_btn.setEnabled(False)
        self._csv_import_btn.clicked.connect(self._importa_csv)
        layout.addWidget(self._csv_import_btn)

        return w

    def _build_osm_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        info = QLabel(
            "Scarica strade e luoghi da <b>OpenStreetMap</b> per il comune selezionato.<br>"
            "I dati sono open source e vengono recuperati tramite l'API Overpass."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        # Nome comune (auto-popolato dal combo, modificabile)
        nome_layout = QHBoxLayout()
        nome_layout.addWidget(QLabel("Nome comune (per OSM):"))
        self._osm_comune_edit = QLineEdit()
        self._osm_comune_edit.setPlaceholderText("es. Firenze")
        nome_layout.addWidget(self._osm_comune_edit)
        layout.addLayout(nome_layout)

        # Checkboxes tipo dati
        check_layout = QHBoxLayout()
        self._osm_chk_strade = QCheckBox("Includi strade (Via, Corso, Piazza...)")
        self._osm_chk_strade.setChecked(True)
        self._osm_chk_luoghi = QCheckBox("Includi luoghi (frazioni, borghi...)")
        self._osm_chk_luoghi.setChecked(True)
        check_layout.addWidget(self._osm_chk_strade)
        check_layout.addWidget(self._osm_chk_luoghi)
        check_layout.addStretch()
        layout.addLayout(check_layout)

        # Download button + status
        dl_layout = QHBoxLayout()
        self._osm_download_btn = QPushButton("Scarica da OpenStreetMap")
        self._osm_download_btn.clicked.connect(self._avvia_download_osm)
        dl_layout.addWidget(self._osm_download_btn)
        dl_layout.addStretch()
        layout.addLayout(dl_layout)

        self._osm_status_label = QLabel("In attesa.")
        layout.addWidget(self._osm_status_label)

        self._osm_progress = QProgressBar()
        self._osm_progress.setRange(0, 0)
        self._osm_progress.setVisible(False)
        layout.addWidget(self._osm_progress)

        self._osm_preview = QTableWidget(0, len(self.OSM_PREVIEW_COLUMNS))
        self._osm_preview.setHorizontalHeaderLabels([c[0] for c in self.OSM_PREVIEW_COLUMNS])
        self._osm_preview.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._osm_preview.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._osm_preview)

        self._osm_import_btn = QPushButton("Importa nel DB")
        self._osm_import_btn.setEnabled(False)
        self._osm_import_btn.clicked.connect(self._importa_osm)
        layout.addWidget(self._osm_import_btn)

        return w

    def _on_comune_changed(self, text: str):
        """Sincronizza il nome del comune nell'edit OSM con la selezione del combo."""
        nome = text.split("(")[0].strip() if text else ""
        if hasattr(self, '_osm_comune_edit'):
            self._osm_comune_edit.setText(nome)

    def _carica_comuni(self):
        self._comune_combo.clear()
        self._comuni_map = {}
        try:
            comuni = self.db_manager.get_comuni()
            for c in comuni:
                label = f"{c['nome']} ({c['provincia']})"
                self._comune_combo.addItem(label)
                self._comuni_map[label] = c['id']
        except Exception as e:
            QMessageBox.warning(self, "Avviso", f"Impossibile caricare i comuni: {e}")

    def _get_selected_comune_id(self) -> Optional[int]:
        label = self._comune_combo.currentText()
        return self._comuni_map.get(label)

    # --- Tab CSV ---

    def _scarica_template(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Salva template CSV", "template_localita.csv", "File CSV (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write(self.TEMPLATE_HEADERS + "\n")
                f.write(self.TEMPLATE_EXAMPLE)
            QMessageBox.information(self, "Template salvato", f"Template salvato in:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile salvare il template:\n{e}")

    def _seleziona_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleziona file CSV località", "", "File CSV (*.csv);;Tutti i file (*)"
        )
        if not path:
            return
        try:
            with open(path, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter=";")
                if "nome" not in (reader.fieldnames or []):
                    QMessageBox.warning(self, "Intestazioni mancanti",
                                        "Il file CSV deve contenere almeno la colonna 'nome'.")
                    return
                self._csv_rows = list(reader)
            self._path_label.setText(f"File: {path}  ({len(self._csv_rows)} righe)")
            _popola_preview_tabella(self._csv_preview, self._csv_rows, self.PREVIEW_COLUMNS)
            self._csv_import_btn.setEnabled(bool(self._csv_rows))
        except Exception as e:
            QMessageBox.critical(self, "Errore lettura CSV", str(e))

    def _importa_csv(self):
        comune_id = self._get_selected_comune_id()
        if not comune_id:
            QMessageBox.warning(self, "Nessun comune", "Seleziona un comune prima di importare.")
            return
        if not self._csv_rows:
            return
        comune_nome = self._comune_combo.currentText()
        risposta = QMessageBox.question(
            self, "Conferma importazione",
            f"Stai per importare <b>{len(self._csv_rows)}</b> località per il comune "
            f"<b>{comune_nome}</b>.<br><br>"
            "Le località con lo stesso nome già presenti nel database potrebbero essere sovrascritte.<br><br>"
            "Procedere con l'importazione?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if risposta != QMessageBox.StandardButton.Yes:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            result = self.db_manager.import_localita_from_rows(comune_id, self._csv_rows)
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Errore DB", str(e))
            return
        QApplication.restoreOverrideCursor()
        _mostra_risultati_import(self, "Località", result.get("success", []), result.get("errors", []))
        self._csv_rows = []
        self._csv_preview.setRowCount(0)
        self._csv_import_btn.setEnabled(False)
        self._path_label.setText("Nessun file selezionato.")

    # --- Tab OSM ---

    def _avvia_download_osm(self):
        comune_nome = self._osm_comune_edit.text().strip()
        if not comune_nome:
            QMessageBox.warning(self, "Nome mancante", "Inserisci il nome del comune.")
            return
        self._osm_rows = []
        self._osm_preview.setRowCount(0)
        self._osm_import_btn.setEnabled(False)
        self._osm_download_btn.setEnabled(False)
        self._osm_progress.setVisible(True)
        self._osm_status_label.setText("Download in corso...")

        self._osm_worker = OSMLocalitaWorker(
            comune_nome=comune_nome,
            include_strade=self._osm_chk_strade.isChecked(),
            include_luoghi=self._osm_chk_luoghi.isChecked(),
            parent=self
        )
        self._osm_worker.progress.connect(self._osm_status_label.setText)
        self._osm_worker.finished.connect(self._on_osm_finished)
        self._osm_worker.error.connect(self._on_osm_error)
        self._osm_worker.start()

    def _on_osm_finished(self, rows: list):
        self._osm_rows = rows
        self._osm_progress.setVisible(False)
        self._osm_download_btn.setEnabled(True)
        _popola_preview_tabella(self._osm_preview, rows, self.OSM_PREVIEW_COLUMNS)
        self._osm_import_btn.setEnabled(bool(rows))

    def _on_osm_error(self, msg: str):
        self._osm_progress.setVisible(False)
        self._osm_download_btn.setEnabled(True)
        self._osm_status_label.setText("Errore durante il download.")
        QMessageBox.critical(self, "Errore OpenStreetMap", msg)

    def _importa_osm(self):
        comune_id = self._get_selected_comune_id()
        if not comune_id:
            QMessageBox.warning(self, "Nessun comune",
                                "Seleziona il comune nel menu a tendina in alto prima di importare.")
            return
        if not self._osm_rows:
            return
        comune_nome = self._comune_combo.currentText()
        risposta = QMessageBox.question(
            self, "Conferma importazione",
            f"Stai per importare <b>{len(self._osm_rows)}</b> località da OpenStreetMap per il comune "
            f"<b>{comune_nome}</b>.<br><br>"
            "Le località con lo stesso nome già presenti nel database potrebbero essere sovrascritte.<br><br>"
            "Procedere con l'importazione?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if risposta != QMessageBox.StandardButton.Yes:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            result = self.db_manager.import_localita_from_rows(comune_id, self._osm_rows)
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Errore DB", str(e))
            return
        QApplication.restoreOverrideCursor()
        _mostra_risultati_import(self, "Località", result.get("success", []), result.get("errors", []))
        self._osm_rows = []
        self._osm_preview.setRowCount(0)
        self._osm_import_btn.setEnabled(False)
        self._osm_status_label.setText("Import completato. Scarica di nuovo per un nuovo import.")

    def closeEvent(self, event):
        if self._osm_worker and self._osm_worker.isRunning():
            self._osm_worker.quit()
            self._osm_worker.wait(2000)
        super().closeEvent(event)
