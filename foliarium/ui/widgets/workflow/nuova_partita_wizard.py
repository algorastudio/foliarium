"""
nuova_partita_wizard.py — Wizard a 4 step per la creazione guidata di una nuova partita.

Estratto da partita_workflow_widgets.py (Sprint 3 refactor — six-hats).
La classe e' anche re-esportata da partita_workflow_widgets per
preservare la backward compatibility con i consumer esistenti.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from PyQt6.QtCore import (
    QDate, Qt,
)
from PyQt6.QtWidgets import (
    QComboBox, QDateEdit, QDialog, QFormLayout, QFrame,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QSpinBox, QStackedWidget, QTableWidget,
    QTableWidgetItem, QTextBrowser, QVBoxLayout, QWidget,
)

from foliarium.ui.widgets.custom import (
    show_status_message as _show_status_message,
)
from dialogs import (
    ComuneSelectionDialog, CreateLocalitaDialog, CreatePossessoreDialog,
)

try:
    from catasto_db_manager import (
        DBMError,
    )
except ImportError:
    class DBMError(Exception):
        pass


logger = logging.getLogger("CatastoGUI.nuova_partita_wizard")


class NuovaPartitaWizardWidget(QWidget):
    """Wizard a 4 step per la creazione guidata di una nuova partita."""

    def __init__(self, db_manager, utente_info=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.utente_info = utente_info or {}
        self._step = 0
        self._comune_id: Optional[int] = None
        self._comune_nome: str = ""
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Step indicator
        step_bar = QFrame()
        step_bar.setObjectName("wizardStepBar")
        step_bar.setFixedHeight(56)
        step_layout = QHBoxLayout(step_bar)
        step_layout.setContentsMargins(32, 0, 32, 0)
        step_layout.setSpacing(12)

        self._step_widgets: list[QWidget] = []
        for i, label in enumerate(["Dati Partita", "Possessori", "Immobili", "Riepilogo"]):
            w = QLabel(f"{i+1}. {label}")
            w.setAlignment(Qt.AlignmentFlag.AlignCenter)
            step_layout.addWidget(w)

        step_layout.addStretch()
        main_layout.addWidget(step_bar)

        # Content area
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_step1())
        self._stack.addWidget(self._build_step2())
        self._stack.addWidget(self._build_step3())
        self._stack.addWidget(self._build_step4())
        main_layout.addWidget(self._stack, 1)

        # Navigation
        nav_bar = QFrame()
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(20, 12, 20, 12)
        nav_layout.setSpacing(8)

        self._btn_back = QPushButton("← Indietro")
        self._btn_back.setObjectName("secondaryButton")
        self._btn_back.setEnabled(False)
        self._btn_back.clicked.connect(self._go_back)
        nav_layout.addWidget(self._btn_back)

        nav_layout.addStretch()

        self._btn_reset = QPushButton("Ricomincia")
        self._btn_reset.setObjectName("secondaryButton")
        self._btn_reset.clicked.connect(self._reset_wizard)
        nav_layout.addWidget(self._btn_reset)

        self._btn_next = QPushButton("Avanti →")
        self._btn_next.clicked.connect(self._go_next)
        nav_layout.addWidget(self._btn_next)

        main_layout.addWidget(nav_bar)

    def _build_step1(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)

        title = QLabel("Dati della Partita")
        title.setObjectName("wizardStepTitle")
        layout.addWidget(title)

        form_group = QGroupBox("Informazioni Generali")
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(10)

        self._s1_comune_label = QLabel("Nessun comune selezionato")
        self._s1_comune_label.setProperty("muted", "true"); self._s1_comune_label.style().unpolish(self._s1_comune_label); self._s1_comune_label.style().polish(self._s1_comune_label)
        comune_btn = QPushButton("Seleziona...")
        comune_btn.setObjectName("secondaryButton")
        comune_btn.clicked.connect(self._s1_select_comune)
        comune_row = QHBoxLayout()
        comune_row.addWidget(self._s1_comune_label, 1)
        comune_row.addWidget(comune_btn)
        form_layout.addRow("Comune: *", comune_row)

        self._s1_numero = QSpinBox()
        self._s1_numero.setMinimum(1)
        self._s1_numero.setMaximum(99999)
        self._s1_numero.setValue(1)
        form_layout.addRow("Numero Partita: *", self._s1_numero)

        self._s1_suffisso = QLineEdit()
        self._s1_suffisso.setPlaceholderText("Es. A, B, bis (opzionale)")
        form_layout.addRow("Suffisso:", self._s1_suffisso)

        self._s1_data_imp = QDateEdit()
        self._s1_data_imp.setCalendarPopup(True)
        self._s1_data_imp.setDate(QDate.currentDate())
        self._s1_data_imp.setDisplayFormat("dd/MM/yyyy")
        form_layout.addRow("Data Impianto: *", self._s1_data_imp)

        self._s1_tipo = QComboBox()
        self._s1_tipo.addItems(["Principale", "Secondaria", "Enfiteusi", "Usufrutto"])
        form_layout.addRow("Tipo:", self._s1_tipo)

        self._s1_stato = QComboBox()
        self._s1_stato.addItems(["Attiva", "Inattiva"])
        form_layout.addRow("Stato:", self._s1_stato)

        layout.addWidget(form_group)
        layout.addStretch()

        return w

    def _s1_select_comune(self):
        dialog = ComuneSelectionDialog(self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_comune_id:
            self._comune_id = dialog.selected_comune_id
            self._comune_nome = dialog.selected_comune_name
            self._s1_comune_label.setText(self._comune_nome)
            self._s1_comune_label.setProperty("muted", "false"); self._s1_comune_label.style().unpolish(self._s1_comune_label); self._s1_comune_label.style().polish(self._s1_comune_label)

    def _build_step2(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)

        title = QLabel("Aggiungi Possessori (Opzionale)")
        title.setObjectName("wizardStepTitle")
        layout.addWidget(title)

        search_row = QHBoxLayout()
        self._s2_search = QLineEdit()
        self._s2_search.setPlaceholderText("Cerca possessore...")
        search_row.addWidget(self._s2_search, 1)

        search_btn = QPushButton("Cerca")
        search_btn.clicked.connect(self._s2_search_possessore)
        search_row.addWidget(search_btn)

        create_btn = QPushButton("Crea Nuovo...")
        create_btn.setObjectName("secondaryButton")
        create_btn.setToolTip("Crea un nuovo possessore e aggiungilo alla partita")
        create_btn.clicked.connect(self._s2_create_possessore)
        search_row.addWidget(create_btn)

        layout.addLayout(search_row)

        layout.addWidget(QLabel("Risultati:"))
        self._s2_results = QListWidget()
        self._s2_results.setMaximumHeight(140)
        self._s2_results.itemDoubleClicked.connect(self._s2_add_from_list)
        layout.addWidget(self._s2_results)

        layout.addWidget(QLabel("Selezionati:"))
        self._s2_table = QTableWidget()
        self._s2_table.setColumnCount(3)
        self._s2_table.setHorizontalHeaderLabels(["Nome", "Titolo", ""])
        self._s2_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self._s2_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._s2_table, 1)

        return w

    def _s2_search_possessore(self):
        testo = self._s2_search.text().strip()
        if not testo:
            return
        try:
            results = self.db_manager.search_possessori_by_term_globally(testo, limit=20)
            self._s2_results.clear()
            for p in (results or []):
                item = QListWidgetItem(f"{p.get('nome_completo','')} — {p.get('paternita','')}")
                item.setData(Qt.ItemDataRole.UserRole, p.get('id'))
                self._s2_results.addItem(item)
        except Exception as e:
            logging.getLogger("CatastoGUI").error(f"Errore ricerca possessori: {e}")

    def _s2_add_from_list(self, item: QListWidgetItem):
        poss_id = item.data(Qt.ItemDataRole.UserRole)
        if not poss_id:
            return
        self._s2_append_possessore(poss_id, item.text().split(" — ")[0])

    def _s2_append_possessore(self, poss_id: int, nome: str):
        """Aggiunge un possessore alla tabella dei selezionati (se non già presente)."""
        for r in range(self._s2_table.rowCount()):
            it = self._s2_table.item(r, 0)
            if it and it.data(Qt.ItemDataRole.UserRole) == poss_id:
                QMessageBox.information(self, "Già presente",
                                        "Questo possessore è già nella lista.")
                return

        row = self._s2_table.rowCount()
        self._s2_table.insertRow(row)
        nome_item = QTableWidgetItem(nome)
        nome_item.setData(Qt.ItemDataRole.UserRole, poss_id)
        self._s2_table.setItem(row, 0, nome_item)
        self._s2_table.setItem(row, 1, QTableWidgetItem("Proprietario"))

        del_btn = QPushButton("✕")
        del_btn.clicked.connect(
            lambda: self._remove_row(self._s2_table, del_btn))
        self._s2_table.setCellWidget(row, 2, del_btn)

    @staticmethod
    def _remove_row(table: QTableWidget, btn: QPushButton):
        """Rimuove la riga che contiene il pulsante dato (indice sempre corretto
        anche dopo rimozioni precedenti)."""
        for r in range(table.rowCount()):
            if table.cellWidget(r, table.columnCount() - 1) is btn:
                table.removeRow(r)
                return

    def _s2_create_possessore(self):
        """Apre il dialog di creazione possessore e lo aggiunge alla partita."""
        dialog = CreatePossessoreDialog(self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.nuovo_possessore_dati:
            info = dialog.nuovo_possessore_dati
            self._s2_append_possessore(info["id"], info.get("nome_completo", ""))

    def _build_step3(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)

        title = QLabel("Aggiungi Immobili (Opzionale)")
        title.setObjectName("wizardStepTitle")
        layout.addWidget(title)

        add_group = QGroupBox("Nuovo Immobile")
        add_layout = QFormLayout(add_group)

        self._s3_natura = QLineEdit()
        self._s3_natura.setPlaceholderText("Es. Casa, Terreno")
        add_layout.addRow("Natura: *", self._s3_natura)

        # La località è obbligatoria: immobile.localita_id è NOT NULL nel DB.
        self._s3_localita = QComboBox()
        self._s3_localita.setPlaceholderText("Seleziona prima un comune...")
        self._s3_new_localita_btn = QPushButton("+ Nuova...")
        self._s3_new_localita_btn.setObjectName("secondaryButton")
        self._s3_new_localita_btn.setToolTip("Crea una nuova località per il comune selezionato")
        self._s3_new_localita_btn.clicked.connect(self._s3_create_localita)
        loc_row = QHBoxLayout()
        loc_row.setContentsMargins(0, 0, 0, 0)
        loc_row.addWidget(self._s3_localita, 1)
        loc_row.addWidget(self._s3_new_localita_btn)
        add_layout.addRow("Località: *", loc_row)

        self._s3_classif = QLineEdit()
        self._s3_classif.setPlaceholderText("Es. A/1, A/2")
        add_layout.addRow("Classificazione:", self._s3_classif)

        add_btn = QPushButton("+ Aggiungi")
        add_btn.clicked.connect(self._s3_add_immobile)
        add_layout.addRow("", add_btn)

        layout.addWidget(add_group)

        layout.addWidget(QLabel("Immobili:"))
        self._s3_table = QTableWidget()
        self._s3_table.setColumnCount(4)
        self._s3_table.setHorizontalHeaderLabels(["Natura", "Località", "Classificazione", ""])
        self._s3_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self._s3_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._s3_table, 1)

        return w

    def _load_localita(self):
        """Popola la combo delle località per il comune selezionato."""
        self._s3_localita.clear()
        if not self._comune_id:
            self._s3_localita.setEnabled(False)
            self._s3_new_localita_btn.setEnabled(False)
            return
        self._s3_new_localita_btn.setEnabled(True)
        try:
            localita = self.db_manager.get_localita_by_comune(self._comune_id) or []
        except Exception as e:
            logging.getLogger("CatastoGUI").error(f"Errore caricamento località: {e}")
            localita = []
        if localita:
            self._s3_localita.addItem("--- Seleziona Località ---", None)
            for loc in localita:
                tipo = loc.get("tipologia_stradale") or "N/D"
                self._s3_localita.addItem(f"{loc['nome']} ({tipo})", loc["id"])
            self._s3_localita.setEnabled(True)
        else:
            self._s3_localita.addItem("Nessuna località — usa '+ Nuova...'", None)
            self._s3_localita.setEnabled(False)

    def _s3_create_localita(self):
        if not self._comune_id:
            QMessageBox.warning(self, "Comune mancante",
                                "Seleziona prima un comune al Passo 1.")
            return
        dlg = CreateLocalitaDialog(
            self.db_manager, self._comune_id, self._comune_nome, self)
        if dlg.exec() != QDialog.DialogCode.Accepted or not dlg.nuova_localita_id:
            return
        self._load_localita()
        idx = self._s3_localita.findData(dlg.nuova_localita_id)
        if idx >= 0:
            self._s3_localita.setCurrentIndex(idx)

    def _s3_add_immobile(self):
        natura = self._s3_natura.text().strip()
        if not natura:
            QMessageBox.warning(self, "Attenzione", "Natura obbligatoria.")
            return
        localita_id = self._s3_localita.currentData()
        if not localita_id:
            QMessageBox.warning(self, "Attenzione",
                                "Località obbligatoria. Selezionane una o creane una nuova.")
            return

        row = self._s3_table.rowCount()
        self._s3_table.insertRow(row)
        natura_item = QTableWidgetItem(natura)
        natura_item.setData(Qt.ItemDataRole.UserRole, localita_id)
        self._s3_table.setItem(row, 0, natura_item)
        self._s3_table.setItem(row, 1, QTableWidgetItem(self._s3_localita.currentText()))
        self._s3_table.setItem(row, 2, QTableWidgetItem(self._s3_classif.text().strip()))

        del_btn = QPushButton("✕")
        del_btn.clicked.connect(
            lambda: self._remove_row(self._s3_table, del_btn))
        self._s3_table.setCellWidget(row, 3, del_btn)

        self._s3_natura.clear()
        self._s3_classif.clear()

    def _build_step4(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)

        title = QLabel("Riepilogo e Conferma")
        title.setObjectName("wizardStepTitle")
        layout.addWidget(title)

        self._s4_browser = QTextBrowser()
        self._s4_browser.setMinimumHeight(300)
        layout.addWidget(self._s4_browser, 1)

        self._s4_register_btn = QPushButton("✓ Registra Partita")
        self._s4_register_btn.setMinimumHeight(40)
        self._s4_register_btn.clicked.connect(self._registra_tutto)
        layout.addWidget(self._s4_register_btn)

        return w

    def _render_riepilogo(self):
        numero = self._s1_numero.value()
        suffisso = self._s1_suffisso.text().strip()
        suf_disp = f"/{suffisso}" if suffisso else ""
        data_imp = self._s1_data_imp.date().toString("dd/MM/yyyy")
        tipo = self._s1_tipo.currentText()
        stato = self._s1_stato.currentText()
        comune = self._comune_nome or "Non selezionato"

        n_poss = self._s2_table.rowCount()
        n_imm = self._s3_table.rowCount()

        html = f"""
<style>
body {{ font-family: Segoe UI, Arial; font-size:10pt; }}
h3 {{ color:#3F51B5; margin:12px 0 4px 0; }}
table {{ width:100%; border-collapse:collapse; }}
th {{ background:#E8EAF6; color:#3F51B5; padding:5px 8px; text-align:left; }}
td {{ padding:4px 8px; border-bottom:1px solid #EEE; }}
.ok {{ color:#2E7D32; }}
.warn {{ color:#E65100; }}
</style>
<h3>Partita</h3>
<table>
  <tr><td>Comune</td><td>{comune}</td></tr>
  <tr><td>Numero</td><td>{numero}{suf_disp}</td></tr>
  <tr><td>Data Impianto</td><td>{data_imp}</td></tr>
  <tr><td>Tipo</td><td>{tipo}</td></tr>
  <tr><td>Stato</td><td>{stato}</td></tr>
</table>

<h3>Possessori <span class="{'ok' if n_poss > 0 else 'warn'}">[{n_poss}]</span></h3>
"""
        if n_poss > 0:
            html += '<table><tr><th>Nome</th><th>Titolo</th></tr>'
            for row in range(n_poss):
                nome = self._s2_table.item(row, 0).text() if self._s2_table.item(row, 0) else ""
                titolo = self._s2_table.item(row, 1).text() if self._s2_table.item(row, 1) else ""
                html += f'<tr><td>{nome}</td><td>{titolo}</td></tr>'
            html += '</table>'

        css_class = 'ok' if n_imm > 0 else 'warn'
        html += f'<h3>Immobili <span class="{css_class}">[{n_imm}]</span></h3>'
        if n_imm > 0:
            html += '<table><tr><th>Natura</th><th>Località</th><th>Classificazione</th></tr>'
            for row in range(n_imm):
                natura = self._s3_table.item(row, 0).text() if self._s3_table.item(row, 0) else ""
                localita = self._s3_table.item(row, 1).text() if self._s3_table.item(row, 1) else ""
                classif = self._s3_table.item(row, 2).text() if self._s3_table.item(row, 2) else ""
                html += f'<tr><td>{natura}</td><td>{localita}</td><td>{classif}</td></tr>'
            html += '</table>'

        self._s4_browser.setHtml(html)

    def _go_next(self):
        if self._step == 0:
            if not self._comune_id:
                QMessageBox.warning(self, "Attenzione", "Seleziona un comune.")
                return

        self._step = min(self._step + 1, 3)
        self._stack.setCurrentIndex(self._step)
        if self._step == 2:
            self._load_localita()
        if self._step == 3:
            self._render_riepilogo()
        self._btn_back.setEnabled(self._step > 0)

    def _go_back(self):
        self._step = max(self._step - 1, 0)
        self._stack.setCurrentIndex(self._step)
        self._btn_back.setEnabled(self._step > 0)

    def _reset_wizard(self):
        reply = QMessageBox.question(
            self, "Ricomincia", "Ricominciare il wizard?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self._step = 0
            self._comune_id = None
            self._s1_numero.setValue(1)
            self._s1_suffisso.clear()
            self._s1_data_imp.setDate(QDate.currentDate())
            self._s2_search.clear()
            self._s2_results.clear()
            self._s2_table.setRowCount(0)
            self._s3_natura.clear()
            self._s3_classif.clear()
            self._s3_localita.clear()
            self._s3_table.setRowCount(0)
            self._stack.setCurrentIndex(0)
            self._btn_back.setEnabled(False)

    def _registra_tutto(self):
        if not self._comune_id:
            QMessageBox.warning(self, "Errore", "Comune non selezionato.")
            return

        try:
            numero = self._s1_numero.value()
            suffisso = self._s1_suffisso.text().strip() or None
            data_date = self._s1_data_imp.date()
            data_imp = date(data_date.year(), data_date.month(), data_date.day())
            tipo = self._s1_tipo.currentText().lower()
            stato = self._s1_stato.currentText().lower()

            partita_id = self.db_manager.create_partita(
                comune_id=self._comune_id,
                numero_partita=numero,
                suffisso_partita=suffisso,
                data_impianto=data_imp,
                tipo=tipo,
                stato=stato,
                numero_provenienza=None
            )
        except Exception as e:
            logging.getLogger("CatastoGUI").error(f"Errore registrazione partita: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore", str(e))
            return

        # Possessori e immobili: la partita esiste già; eventuali errori qui
        # vengono raccolti e mostrati, non silenziati.
        errori: list[str] = []

        for row in range(self._s2_table.rowCount()):
            cell = self._s2_table.item(row, 0)
            poss_id = cell.data(Qt.ItemDataRole.UserRole) if cell else None
            titolo = self._s2_table.item(row, 1).text() if self._s2_table.item(row, 1) else ""
            if not poss_id:
                continue
            try:
                self.db_manager.aggiungi_possessore_a_partita(
                    partita_id=partita_id,
                    possessore_id=poss_id,
                    # 'tipo_partita' ammette solo 'principale'/'secondaria'
                    tipo_partita_rel="principale",
                    titolo=titolo or "proprietà esclusiva",
                    quota="1/1",
                )
            except Exception as e:
                nome = cell.text() if cell else str(poss_id)
                logging.getLogger("CatastoGUI").error(
                    f"Errore aggiunta possessore '{nome}': {e}", exc_info=True)
                errori.append(f"Possessore '{nome}': {e}")

        for row in range(self._s3_table.rowCount()):
            cell = self._s3_table.item(row, 0)
            natura = cell.text() if cell else ""
            localita_id = cell.data(Qt.ItemDataRole.UserRole) if cell else None
            classif = self._s3_table.item(row, 2).text() if self._s3_table.item(row, 2) else ""
            if not natura or not localita_id:
                continue
            try:
                self.db_manager.inserisci_immobile(
                    partita_id=partita_id,
                    natura=natura,
                    localita_id=localita_id,
                    classificazione=classif or None,
                )
            except Exception as e:
                logging.getLogger("CatastoGUI").error(
                    f"Errore inserimento immobile '{natura}': {e}", exc_info=True)
                errori.append(f"Immobile '{natura}': {e}")

        if errori:
            QMessageBox.warning(
                self, "Registrazione parziale",
                f"Partita N.{numero} creata (ID: {partita_id}), ma alcuni "
                f"elementi non sono stati salvati:\n\n- " + "\n- ".join(errori))
        else:
            _show_status_message(
                f"Partita N.{numero} registrata con successo (ID: {partita_id}).", 5000)
        self._reset_wizard()


