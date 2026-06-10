"""
foliarium/ui/widgets/workflow/bulk_successione.py — Wizard per operazioni
massive di passaggio di proprietà (es. trasferire in blocco N immobili
da una partita "padre" a una nuova partita "eredi" con quote frazionarie).

Wrappa la procedura SQL atomica ``catasto.registra_passaggio_proprieta``
(che gestisce in una transazione: creazione nuova partita + variazione +
contratto + trasferimento immobili + chiusura partita origine se vuota).

L'UI guida l'utente in 5 step con validazioni stringenti:
  1. Partita origine + tipo variazione
  2. Selezione massiva degli immobili da trasferire
  3. Eredi (possessori esistenti o nuovi) con quote frazionarie validate
  4. Dati del contratto
  5. Riepilogo + conferma (chiamata atomica)

Tutte le validazioni avvengono client-side; in caso di errore DB la
transazione SQL viene rollback dalla procedura.
"""

from __future__ import annotations

import logging
from datetime import date
from fractions import Fraction
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from PyQt6.QtCore import QDate, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QDateEdit, QDialog, QFormLayout, QFrame,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
    QPushButton, QSpinBox, QStackedWidget, QTableWidget, QTableWidgetItem,
    QTextBrowser, QVBoxLayout, QWidget,
)

from foliarium.ui.widgets.custom import (
    show_status_message as _show_status_message,
)
from dialogs import (
    ComuneSelectionDialog, CreatePossessoreDialog,
)

if TYPE_CHECKING:
    from catasto_db_manager import CatastoDBManager  # noqa: F401


logger = logging.getLogger("CatastoGUI.bulk_successione")


# Tipi di variazione supportati dalla procedura SQL
_TIPI_VARIAZIONE = ["Successione", "Vendita", "Donazione", "Permuta", "Divisione"]


def parse_quota(text: str) -> Optional[Fraction]:
    """Parse di una quota ('1/2', '1', '0.5', '3/4'). Ritorna None se non valida."""
    s = (text or "").strip()
    if not s:
        return None
    try:
        if "/" in s:
            return Fraction(s)
        # Decimale → Fraction
        return Fraction(s).limit_denominator(10000)
    except (ValueError, ZeroDivisionError):
        return None


class BulkSuccessioneWizard(QWidget):
    """Wizard per operazioni massive di passaggio proprietà.

    Tipico caso d'uso: una partita "padre" (defunto) viene chiusa
    trasferendo in blocco tutti gli immobili agli eredi su una nuova
    partita, con quote frazionarie validate (la somma deve essere = 1).
    """

    operazione_completata = pyqtSignal(int)  # comune_id_della_partita_origine

    def __init__(self, db_manager: 'CatastoDBManager', parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db_manager = db_manager
        self._step = 0

        # Stato wizard
        self._origine_partita: Optional[Dict[str, Any]] = None
        self._immobili_origine: List[Dict[str, Any]] = []
        self._immobili_selezionati_ids: List[int] = []
        self._eredi: List[Dict[str, Any]] = []  # [{possessore_id, nome_completo, titolo, quota}, ...]
        self._tipo_variazione: str = "Successione"

        self._build_ui()

    # ── UI BUILD ───────────────────────────────────────────────────

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # Step bar
        step_bar = QFrame()
        step_bar.setObjectName("wizardStepBar")
        step_bar.setFixedHeight(56)
        step_bar_layout = QHBoxLayout(step_bar)
        step_bar_layout.setContentsMargins(32, 0, 32, 0)
        step_bar_layout.setSpacing(12)
        self._step_labels: list[QLabel] = []
        for i, name in enumerate(
                ["Origine", "Immobili", "Eredi", "Contratto", "Conferma"]):
            lbl = QLabel(f"{i+1}. {name}")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._step_labels.append(lbl)
            step_bar_layout.addWidget(lbl)
        step_bar_layout.addStretch()
        main.addWidget(step_bar)

        # Stack di step
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_step1())
        self._stack.addWidget(self._build_step2())
        self._stack.addWidget(self._build_step3())
        self._stack.addWidget(self._build_step4())
        self._stack.addWidget(self._build_step5())
        main.addWidget(self._stack, 1)

        # Navigation
        nav = QFrame()
        nav_l = QHBoxLayout(nav)
        nav_l.setContentsMargins(20, 12, 20, 12)
        nav_l.setSpacing(8)

        self._btn_back = QPushButton("← Indietro")
        self._btn_back.setObjectName("secondaryButton")
        self._btn_back.setEnabled(False)
        self._btn_back.clicked.connect(self._go_back)
        nav_l.addWidget(self._btn_back)

        nav_l.addStretch()

        self._btn_reset = QPushButton("Ricomincia")
        self._btn_reset.setObjectName("secondaryButton")
        self._btn_reset.clicked.connect(self._reset_wizard)
        nav_l.addWidget(self._btn_reset)

        self._btn_next = QPushButton("Avanti →")
        self._btn_next.clicked.connect(self._go_next)
        nav_l.addWidget(self._btn_next)

        main.addWidget(nav)

    # ── Step 1: origine + tipo variazione ─────────────────────────

    def _build_step1(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)

        title = QLabel("Partita di Origine")
        title.setObjectName("wizardStepTitle")
        layout.addWidget(title)

        warning = QLabel(
            "⚠ <b>Operazione massiva</b>: questo wizard trasferisce in "
            "blocco gli immobili selezionati a una nuova partita destinata "
            "agli eredi (o ai nuovi possessori), in <b>un'unica transazione</b>. "
            "Se tutti gli immobili vengono trasferiti, la partita origine "
            "viene chiusa automaticamente (stato 'inattiva')."
        )
        warning.setWordWrap(True)
        warning.setTextFormat(Qt.TextFormat.RichText)
        warning.setStyleSheet(
            "background: palette(alternate-base); padding: 10px; "
            "border-left: 4px solid #F57C00; border-radius: 4px;"
        )
        layout.addWidget(warning)

        group = QGroupBox("Origine")
        form = QFormLayout(group)

        # Selezione partita: comune + numero
        self._s1_comune_label = QLabel("Nessun comune selezionato")
        self._s1_comune_id: Optional[int] = None
        self._s1_comune_nome: str = ""
        comune_btn = QPushButton("Seleziona comune...")
        comune_btn.setObjectName("secondaryButton")
        comune_btn.clicked.connect(self._s1_select_comune)
        comune_row = QHBoxLayout()
        comune_row.addWidget(self._s1_comune_label, 1)
        comune_row.addWidget(comune_btn)
        form.addRow("Comune origine: *", comune_row)

        self._s1_numero = QSpinBox()
        self._s1_numero.setMinimum(1)
        self._s1_numero.setMaximum(99999)
        form.addRow("Numero Partita: *", self._s1_numero)

        self._s1_suffisso = QLineEdit()
        self._s1_suffisso.setPlaceholderText("Es. A, bis (opzionale)")
        form.addRow("Suffisso:", self._s1_suffisso)

        load_btn = QPushButton("Carica partita")
        load_btn.clicked.connect(self._s1_load_partita)
        form.addRow("", load_btn)

        self._s1_origine_info = QLabel("Nessuna partita caricata.")
        self._s1_origine_info.setStyleSheet(
            "padding: 8px; background: palette(base); "
            "border: 1px solid palette(mid); border-radius: 4px;")
        self._s1_origine_info.setWordWrap(True)
        form.addRow("Stato:", self._s1_origine_info)

        self._s1_tipo = QComboBox()
        self._s1_tipo.addItems(_TIPI_VARIAZIONE)
        form.addRow("Tipo Variazione: *", self._s1_tipo)

        layout.addWidget(group)
        layout.addStretch()
        return w

    def _s1_select_comune(self):
        dlg = ComuneSelectionDialog(self.db_manager, self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.selected_comune_id:
            self._s1_comune_id = dlg.selected_comune_id
            self._s1_comune_nome = dlg.selected_comune_name
            self._s1_comune_label.setText(self._s1_comune_nome)

    def _s1_load_partita(self):
        if not self._s1_comune_id:
            QMessageBox.warning(self, "Comune mancante",
                                "Seleziona prima un comune.")
            return
        numero = self._s1_numero.value()
        suffisso = self._s1_suffisso.text().strip() or None
        partita = self._find_partita(self._s1_comune_id, numero, suffisso)
        if not partita:
            self._origine_partita = None
            self._immobili_origine = []
            self._s1_origine_info.setText(
                "<span style='color:#C62828;'>Partita non trovata. "
                "Verifica comune, numero e suffisso.</span>")
            return
        self._origine_partita = partita
        # Carica immobili
        try:
            details = self.db_manager.get_partita_details(int(partita["id"]))
        except Exception as e:
            logger.error(f"Errore caricamento dettagli partita: {e}", exc_info=True)
            self._s1_origine_info.setText(
                f"<span style='color:#C62828;'>Errore: {e}</span>")
            return
        self._immobili_origine = (details or {}).get("immobili") or []
        n = len(self._immobili_origine)
        stato = partita.get("stato", "?")
        possessori = partita.get("possessori", "")
        if isinstance(possessori, list):
            possessori = ", ".join(
                str(p.get("nome_completo", "")) for p in possessori)
        self._s1_origine_info.setText(
            f"<b>Partita ID {partita['id']}</b> · Stato: <b>{stato}</b> · "
            f"{n} immobil{'i' if n != 1 else 'e'} · "
            f"Possessori attuali: {possessori or '—'}")

    def _find_partita(self, comune_id: int, numero: int,
                      suffisso: Optional[str]) -> Optional[Dict[str, Any]]:
        try:
            results = self.db_manager.search_partite(
                comune_id=comune_id, numero_partita=numero, limit=20) or []
        except Exception as e:
            logger.error(f"Ricerca partita fallita: {e}", exc_info=True)
            return None
        # Filtra per suffisso (None == None match)
        for p in results:
            ps = p.get("suffisso_partita") or None
            if (ps or None) == (suffisso or None):
                return p
        # Fallback: match solo per numero se l'unica trovata corrisponde
        if len(results) == 1 and not suffisso:
            return results[0]
        return None

    # ── Step 2: selezione immobili ────────────────────────────────

    def _build_step2(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)

        title = QLabel("Selezione Immobili da Trasferire")
        title.setObjectName("wizardStepTitle")
        layout.addWidget(title)

        helper = QLabel(
            "Seleziona con il checkbox gli immobili da trasferire alla "
            "nuova partita. Se non selezioni nessun immobile, la partita "
            "origine rimarrà invariata (operazione bloccata).")
        helper.setWordWrap(True)
        layout.addWidget(helper)

        # Toolbar
        bar = QHBoxLayout()
        self._btn_sel_all = QPushButton("Seleziona tutti")
        self._btn_sel_all.setObjectName("secondaryButton")
        self._btn_sel_all.clicked.connect(lambda: self._s2_set_all(True))
        bar.addWidget(self._btn_sel_all)
        self._btn_sel_none = QPushButton("Nessuno")
        self._btn_sel_none.setObjectName("secondaryButton")
        self._btn_sel_none.clicked.connect(lambda: self._s2_set_all(False))
        bar.addWidget(self._btn_sel_none)
        bar.addStretch()
        self._s2_count_label = QLabel("0 immobili selezionati")
        self._s2_count_label.setStyleSheet("color: palette(mid);")
        bar.addWidget(self._s2_count_label)
        layout.addLayout(bar)

        self._s2_table = QTableWidget()
        self._s2_table.setColumnCount(5)
        self._s2_table.setHorizontalHeaderLabels(
            ["✓", "ID", "Natura", "Località", "Classificazione"])
        self._s2_table.horizontalHeader().setStretchLastSection(True)
        self._s2_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._s2_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._s2_table.itemChanged.connect(self._s2_update_count)
        layout.addWidget(self._s2_table, 1)
        return w

    def _s2_populate(self):
        # Disconnetti temporaneamente per evitare itemChanged spam
        try:
            self._s2_table.itemChanged.disconnect(self._s2_update_count)
        except TypeError:
            pass
        self._s2_table.setRowCount(0)
        for imm in self._immobili_origine:
            row = self._s2_table.rowCount()
            self._s2_table.insertRow(row)
            check = QTableWidgetItem()
            check.setFlags(check.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            check.setCheckState(Qt.CheckState.Checked)
            check.setData(Qt.ItemDataRole.UserRole, imm.get("id"))
            self._s2_table.setItem(row, 0, check)
            self._s2_table.setItem(row, 1, QTableWidgetItem(str(imm.get("id", ""))))
            self._s2_table.setItem(row, 2, QTableWidgetItem(imm.get("natura", "")))
            loc_nome = imm.get("localita_nome") or imm.get("localita") or ""
            self._s2_table.setItem(row, 3, QTableWidgetItem(str(loc_nome)))
            self._s2_table.setItem(row, 4, QTableWidgetItem(imm.get("classificazione", "") or ""))
        self._s2_table.itemChanged.connect(self._s2_update_count)
        self._s2_update_count()

    def _s2_set_all(self, checked: bool):
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for r in range(self._s2_table.rowCount()):
            it = self._s2_table.item(r, 0)
            if it:
                it.setCheckState(state)

    def _s2_update_count(self, *args):
        count = 0
        for r in range(self._s2_table.rowCount()):
            it = self._s2_table.item(r, 0)
            if it and it.checkState() == Qt.CheckState.Checked:
                count += 1
        total = self._s2_table.rowCount()
        self._s2_count_label.setText(
            f"{count} di {total} immobili selezionati")

    def _s2_get_selected_ids(self) -> List[int]:
        ids: List[int] = []
        for r in range(self._s2_table.rowCount()):
            it = self._s2_table.item(r, 0)
            if it and it.checkState() == Qt.CheckState.Checked:
                imm_id = it.data(Qt.ItemDataRole.UserRole)
                if imm_id is not None:
                    ids.append(int(imm_id))
        return ids

    # ── Step 3: eredi ─────────────────────────────────────────────

    def _build_step3(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)

        title = QLabel("Eredi / Nuovi Possessori")
        title.setObjectName("wizardStepTitle")
        layout.addWidget(title)

        helper = QLabel(
            "Aggiungi i possessori della nuova partita con la rispettiva "
            "quota frazionaria. <b>La somma delle quote deve essere = 1</b> "
            "(es. due eredi con 1/2 ciascuno; tre eredi con 1/3 ciascuno).")
        helper.setWordWrap(True)
        helper.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(helper)

        # Toolbar
        bar = QHBoxLayout()
        self._s3_search = QLineEdit()
        self._s3_search.setPlaceholderText("Cerca possessore esistente...")
        bar.addWidget(self._s3_search, 1)
        btn_search = QPushButton("Cerca e aggiungi")
        btn_search.clicked.connect(self._s3_search_and_add)
        bar.addWidget(btn_search)
        btn_create = QPushButton("Crea nuovo possessore...")
        btn_create.setObjectName("secondaryButton")
        btn_create.clicked.connect(self._s3_create_new)
        bar.addWidget(btn_create)
        layout.addLayout(bar)

        # Tabella eredi
        self._s3_table = QTableWidget()
        self._s3_table.setColumnCount(5)
        self._s3_table.setHorizontalHeaderLabels(
            ["ID", "Nome Completo", "Titolo", "Quota", ""])
        self._s3_table.horizontalHeader().setStretchLastSection(False)
        self._s3_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._s3_table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.SelectedClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed)
        self._s3_table.itemChanged.connect(self._s3_update_quota_status)
        layout.addWidget(self._s3_table, 1)

        # Riga numero nuova partita
        dest_group = QGroupBox("Nuova Partita Destinazione")
        dest_form = QFormLayout(dest_group)
        self._s3_dest_comune_label = QLabel("(stesso comune dell'origine)")
        dest_form.addRow("Comune destinazione:", self._s3_dest_comune_label)

        self._s3_dest_numero = QSpinBox()
        self._s3_dest_numero.setMinimum(1)
        self._s3_dest_numero.setMaximum(99999)
        dest_form.addRow("Numero nuova partita: *", self._s3_dest_numero)
        self._s3_dest_suffisso = QLineEdit()
        self._s3_dest_suffisso.setPlaceholderText("Opzionale (es. A, bis)")
        dest_form.addRow("Suffisso:", self._s3_dest_suffisso)

        layout.addWidget(dest_group)

        # Stato quote
        self._s3_quota_status = QLabel("")
        self._s3_quota_status.setStyleSheet("font-weight: bold;")
        layout.addWidget(self._s3_quota_status)

        return w

    def _s3_search_and_add(self):
        text = self._s3_search.text().strip()
        if not text:
            return
        try:
            results = self.db_manager.search_possessori_by_term_globally(
                text, limit=10) or []
        except Exception as e:
            logger.error(f"Errore ricerca possessori: {e}", exc_info=True)
            return
        if not results:
            QMessageBox.information(self, "Nessun risultato",
                                    f"Nessun possessore trovato per '{text}'.")
            return
        if len(results) == 1:
            p = results[0]
            self._s3_add_erede(p["id"], p.get("nome_completo", ""))
            return
        # Multipli: mostra un picker rapido
        from PyQt6.QtWidgets import QInputDialog
        items = [f"{p.get('nome_completo','')}  (id {p.get('id')})"
                 for p in results]
        sel, ok = QInputDialog.getItem(
            self, "Seleziona possessore",
            f"Risultati per '{text}':", items, 0, False)
        if not ok:
            return
        idx = items.index(sel)
        p = results[idx]
        self._s3_add_erede(p["id"], p.get("nome_completo", ""))

    def _s3_create_new(self):
        dlg = CreatePossessoreDialog(self.db_manager, self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.nuovo_possessore_dati:
            info = dlg.nuovo_possessore_dati
            self._s3_add_erede(info["id"], info.get("nome_completo", ""))

    def _s3_add_erede(self, pid: int, nome: str,
                      titolo: str = "proprietà", quota: str = ""):
        # Evita duplicati
        for r in range(self._s3_table.rowCount()):
            it = self._s3_table.item(r, 0)
            if it and str(it.text()) == str(pid):
                QMessageBox.information(self, "Già presente",
                                        "Questo possessore è già nella lista.")
                return
        row = self._s3_table.rowCount()
        self._s3_table.insertRow(row)
        id_item = QTableWidgetItem(str(pid))
        id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._s3_table.setItem(row, 0, id_item)
        nome_item = QTableWidgetItem(nome)
        nome_item.setFlags(nome_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._s3_table.setItem(row, 1, nome_item)
        self._s3_table.setItem(row, 2, QTableWidgetItem(titolo))
        self._s3_table.setItem(row, 3, QTableWidgetItem(quota))

        del_btn = QPushButton("✕")
        del_btn.setMaximumWidth(40)
        del_btn.clicked.connect(
            lambda: (self._s3_remove_row(del_btn), self._s3_update_quota_status()))
        self._s3_table.setCellWidget(row, 4, del_btn)
        self._s3_update_quota_status()

    def _s3_remove_row(self, btn: QPushButton):
        for r in range(self._s3_table.rowCount()):
            if self._s3_table.cellWidget(r, 4) is btn:
                self._s3_table.removeRow(r)
                return

    def _s3_update_quota_status(self, *args):
        total = Fraction(0)
        invalid = False
        n = self._s3_table.rowCount()
        for r in range(n):
            it = self._s3_table.item(r, 3)
            if not it:
                continue
            q = parse_quota(it.text())
            if q is None:
                invalid = True
                continue
            total += q
        if n == 0:
            self._s3_quota_status.setText("Nessun erede inserito.")
            self._s3_quota_status.setStyleSheet("color: palette(mid);")
            return
        if invalid:
            self._s3_quota_status.setText(
                f"⚠ Alcune quote non sono valide. Somma parziale: {total}")
            self._s3_quota_status.setStyleSheet("color: #C62828;")
            return
        if total == Fraction(1):
            self._s3_quota_status.setText(
                f"✓ Somma quote = 1 ({n} erede{'i' if n != 1 else ''}).")
            self._s3_quota_status.setStyleSheet("color: #2E7D32;")
        else:
            self._s3_quota_status.setText(
                f"⚠ Somma quote = {total} (deve essere = 1).")
            self._s3_quota_status.setStyleSheet("color: #C62828;")

    def _s3_collect_eredi(self) -> Optional[List[Dict[str, Any]]]:
        """Raccoglie gli eredi dalla tabella. None se invalidi."""
        out: List[Dict[str, Any]] = []
        total = Fraction(0)
        for r in range(self._s3_table.rowCount()):
            id_item = self._s3_table.item(r, 0)
            nome_item = self._s3_table.item(r, 1)
            tit_item = self._s3_table.item(r, 2)
            quo_item = self._s3_table.item(r, 3)
            if not id_item or not nome_item:
                return None
            try:
                pid = int(id_item.text())
            except ValueError:
                return None
            titolo = (tit_item.text() if tit_item else "").strip() or "proprietà"
            quota_text = (quo_item.text() if quo_item else "").strip()
            quota = parse_quota(quota_text)
            if quota is None:
                return None
            total += quota
            out.append({
                "possessore_id": pid,
                "nome_completo": nome_item.text(),
                "titolo": titolo,
                "quota": quota_text,
            })
        if total != Fraction(1):
            return None
        return out

    # ── Step 4: contratto ─────────────────────────────────────────

    def _build_step4(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)

        title = QLabel("Dati dell'Atto / Contratto")
        title.setObjectName("wizardStepTitle")
        layout.addWidget(title)

        group = QGroupBox("Contratto")
        form = QFormLayout(group)

        self._s4_tipo_contratto = QLineEdit()
        self._s4_tipo_contratto.setPlaceholderText(
            "Es. Atto pubblico, Dichiarazione di successione, ...")
        form.addRow("Tipo Contratto: *", self._s4_tipo_contratto)

        self._s4_data_variazione = QDateEdit()
        self._s4_data_variazione.setCalendarPopup(True)
        self._s4_data_variazione.setDate(QDate.currentDate())
        self._s4_data_variazione.setDisplayFormat("dd/MM/yyyy")
        form.addRow("Data Variazione: *", self._s4_data_variazione)

        self._s4_data_contratto = QDateEdit()
        self._s4_data_contratto.setCalendarPopup(True)
        self._s4_data_contratto.setDate(QDate.currentDate())
        self._s4_data_contratto.setDisplayFormat("dd/MM/yyyy")
        form.addRow("Data Contratto: *", self._s4_data_contratto)

        self._s4_notaio = QLineEdit()
        self._s4_notaio.setPlaceholderText("Es. Mario Rossi (opzionale)")
        form.addRow("Notaio:", self._s4_notaio)

        self._s4_repertorio = QLineEdit()
        self._s4_repertorio.setPlaceholderText("Numero repertorio (opzionale)")
        form.addRow("Repertorio:", self._s4_repertorio)

        self._s4_note = QLineEdit()
        self._s4_note.setPlaceholderText("Annotazioni libere (opzionale)")
        form.addRow("Note:", self._s4_note)

        layout.addWidget(group)
        layout.addStretch()
        return w

    # ── Step 5: preview + conferma ────────────────────────────────

    def _build_step5(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)

        title = QLabel("Riepilogo e Conferma")
        title.setObjectName("wizardStepTitle")
        layout.addWidget(title)

        self._s5_preview = QTextBrowser()
        layout.addWidget(self._s5_preview, 1)

        warn = QLabel(
            "⚠ Premendo <b>Esegui operazione</b> verrà chiamata la "
            "procedura atomica <code>registra_passaggio_proprieta</code>: "
            "creazione nuova partita + trasferimento immobili + chiusura "
            "origine (se vuota), tutto in <b>una transazione</b>. "
            "L'operazione è registrata nell'audit log.")
        warn.setWordWrap(True)
        warn.setTextFormat(Qt.TextFormat.RichText)
        warn.setStyleSheet(
            "background: palette(alternate-base); padding: 10px; "
            "border-left: 4px solid #C62828; border-radius: 4px;")
        layout.addWidget(warn)

        self._s5_btn_execute = QPushButton("✓ Esegui Operazione")
        self._s5_btn_execute.setMinimumHeight(40)
        self._s5_btn_execute.clicked.connect(self._eseguire_operazione)
        layout.addWidget(self._s5_btn_execute)
        return w

    def _render_preview(self):
        eredi_html = "".join(
            f"<tr><td>{e['nome_completo']}</td>"
            f"<td>{e.get('titolo','')}</td>"
            f"<td>{e['quota']}</td></tr>"
            for e in (self._eredi or [])
        )
        imm_html = "".join(
            f"<tr><td>{imm.get('id','')}</td>"
            f"<td>{imm.get('natura','')}</td>"
            f"<td>{imm.get('localita_nome', imm.get('localita',''))}</td></tr>"
            for imm in self._immobili_origine
            if imm.get("id") in self._immobili_selezionati_ids
        )
        n_imm = len(self._immobili_selezionati_ids)
        n_tot = len(self._immobili_origine)
        close_orig = "<span style='color:#C62828;'>SÌ (tutti gli immobili trasferiti)</span>" \
            if n_imm == n_tot else \
            "<span style='color:#2E7D32;'>NO (alcuni immobili restano sull'origine)</span>"
        data_v = self._s4_data_variazione.date().toString("dd/MM/yyyy")
        data_c = self._s4_data_contratto.date().toString("dd/MM/yyyy")
        comune = self._s1_comune_nome
        orig_num = self._origine_partita.get("numero_partita") if self._origine_partita else "?"
        dest_num = self._s3_dest_numero.value()
        dest_suf = self._s3_dest_suffisso.text().strip()
        dest_suf_disp = f"/{dest_suf}" if dest_suf else ""

        html = f"""
<style>
h3 {{ color:#3F51B5; margin-top:14px; margin-bottom:4px; }}
table {{ border-collapse:collapse; width:100%; margin-top:4px; }}
th, td {{ padding:4px 8px; border-bottom:1px solid #ddd; text-align:left; }}
th {{ background:#E8EAF6; color:#3F51B5; }}
</style>
<h3>Origine</h3>
<table>
  <tr><th>Comune</th><td>{comune}</td></tr>
  <tr><th>Partita</th><td>N.{orig_num}</td></tr>
  <tr><th>Chiusura automatica</th><td>{close_orig}</td></tr>
</table>

<h3>Destinazione</h3>
<table>
  <tr><th>Comune</th><td>{comune}</td></tr>
  <tr><th>Nuova Partita</th><td>N.{dest_num}{dest_suf_disp}</td></tr>
  <tr><th>Tipo Variazione</th><td>{self._tipo_variazione}</td></tr>
</table>

<h3>Contratto</h3>
<table>
  <tr><th>Tipo</th><td>{self._s4_tipo_contratto.text()}</td></tr>
  <tr><th>Data Variazione</th><td>{data_v}</td></tr>
  <tr><th>Data Contratto</th><td>{data_c}</td></tr>
  <tr><th>Notaio</th><td>{self._s4_notaio.text() or '—'}</td></tr>
  <tr><th>Repertorio</th><td>{self._s4_repertorio.text() or '—'}</td></tr>
</table>

<h3>Eredi / Nuovi Possessori ({len(self._eredi)})</h3>
<table><tr><th>Nome</th><th>Titolo</th><th>Quota</th></tr>{eredi_html}</table>

<h3>Immobili da trasferire ({n_imm} di {n_tot})</h3>
<table><tr><th>ID</th><th>Natura</th><th>Località</th></tr>{imm_html}</table>
"""
        self._s5_preview.setHtml(html)

    # ── Navigazione ───────────────────────────────────────────────

    def _go_next(self):
        if not self._validate_current_step():
            return
        if self._step == self._stack.count() - 1:
            return
        self._step += 1
        self._stack.setCurrentIndex(self._step)
        self._btn_back.setEnabled(self._step > 0)
        self._on_step_entered(self._step)
        self._update_step_bar()

    def _go_back(self):
        if self._step == 0:
            return
        self._step -= 1
        self._stack.setCurrentIndex(self._step)
        self._btn_back.setEnabled(self._step > 0)
        self._update_step_bar()

    def _update_step_bar(self):
        for i, lbl in enumerate(self._step_labels):
            if i == self._step:
                lbl.setStyleSheet("font-weight: bold; color: #3F51B5;")
            elif i < self._step:
                lbl.setStyleSheet("color: #2E7D32;")
            else:
                lbl.setStyleSheet("color: palette(mid);")

    def _on_step_entered(self, step: int):
        if step == 1:
            self._s2_populate()
        if step == 2 and self._origine_partita:
            self._s3_dest_comune_label.setText(self._s1_comune_nome)
        if step == 4:
            self._render_preview()

    def _validate_current_step(self) -> bool:
        if self._step == 0:
            if not self._origine_partita:
                QMessageBox.warning(self, "Origine mancante",
                                    "Carica la partita di origine prima di proseguire.")
                return False
            self._tipo_variazione = self._s1_tipo.currentText()
            return True
        if self._step == 1:
            self._immobili_selezionati_ids = self._s2_get_selected_ids()
            if not self._immobili_selezionati_ids:
                QMessageBox.warning(self, "Nessun immobile",
                                    "Seleziona almeno un immobile da trasferire.")
                return False
            return True
        if self._step == 2:
            eredi = self._s3_collect_eredi()
            if eredi is None:
                QMessageBox.warning(
                    self, "Eredi non validi",
                    "Verifica gli eredi: ogni riga deve avere un possessore "
                    "ed una quota valida (es. 1/2). La somma delle quote "
                    "deve essere esattamente 1.")
                return False
            if not eredi:
                QMessageBox.warning(
                    self, "Nessun erede",
                    "Aggiungi almeno un erede / nuovo possessore.")
                return False
            self._eredi = eredi
            return True
        if self._step == 3:
            if not self._s4_tipo_contratto.text().strip():
                QMessageBox.warning(self, "Dati mancanti",
                                    "Indica il tipo di contratto.")
                return False
            return True
        return True

    def _reset_wizard(self):
        reply = QMessageBox.question(
            self, "Ricomincia", "Ricominciare il wizard?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._step = 0
        self._origine_partita = None
        self._immobili_origine = []
        self._immobili_selezionati_ids = []
        self._eredi = []
        self._s1_comune_id = None
        self._s1_comune_nome = ""
        self._s1_comune_label.setText("Nessun comune selezionato")
        self._s1_numero.setValue(1)
        self._s1_suffisso.clear()
        self._s1_origine_info.setText("Nessuna partita caricata.")
        self._s2_table.setRowCount(0)
        self._s3_table.setRowCount(0)
        self._s3_dest_numero.setValue(1)
        self._s3_dest_suffisso.clear()
        self._s3_quota_status.setText("")
        self._s4_tipo_contratto.clear()
        self._s4_data_variazione.setDate(QDate.currentDate())
        self._s4_data_contratto.setDate(QDate.currentDate())
        self._s4_notaio.clear()
        self._s4_repertorio.clear()
        self._s4_note.clear()
        self._s5_preview.clear()
        self._stack.setCurrentIndex(0)
        self._btn_back.setEnabled(False)
        self._update_step_bar()

    # ── Esecuzione finale ─────────────────────────────────────────

    def _eseguire_operazione(self):
        reply = QMessageBox.question(
            self, "Conferma operazione massiva",
            f"Eseguire il trasferimento di {len(self._immobili_selezionati_ids)} "
            f"immobil{'i' if len(self._immobili_selezionati_ids) != 1 else 'e'} "
            f"dalla partita N.{self._origine_partita.get('numero_partita')} "
            f"alla nuova partita N.{self._s3_dest_numero.value()}?\n\n"
            f"L'operazione è atomica e tracciata in audit.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return

        # Costruisce parametri per registra_passaggio_proprieta
        data_v = self._s4_data_variazione.date()
        data_c = self._s4_data_contratto.date()
        nuovi_possessori = [
            {"possessore_id": e["possessore_id"],
             "titolo": e["titolo"],
             "quota": e["quota"]}
            for e in self._eredi
        ]

        try:
            self.db_manager.registra_passaggio_proprieta(
                partita_origine_id=int(self._origine_partita["id"]),
                comune_id_nuova_partita=int(self._s1_comune_id),
                numero_nuova_partita=self._s3_dest_numero.value(),
                suffisso_nuova_partita=(self._s3_dest_suffisso.text().strip()
                                        or None),
                tipo_variazione=self._tipo_variazione,
                data_variazione=date(data_v.year(), data_v.month(), data_v.day()),
                tipo_contratto=self._s4_tipo_contratto.text().strip(),
                data_contratto=date(data_c.year(), data_c.month(), data_c.day()),
                notaio=self._s4_notaio.text().strip() or None,
                repertorio=self._s4_repertorio.text().strip() or None,
                nuovi_possessori_list=nuovi_possessori,
                immobili_da_trasferire_ids=self._immobili_selezionati_ids,
                note_variazione=self._s4_note.text().strip() or None,
            )
        except Exception as e:
            logger.error(f"Errore operazione massiva: {e}", exc_info=True)
            QMessageBox.critical(
                self, "Errore",
                f"L'operazione è fallita.\n\n{e}\n\n"
                f"La transazione SQL è stata annullata (rollback).")
            return

        _show_status_message(
            f"Operazione massiva completata: nuova partita "
            f"N.{self._s3_dest_numero.value()} creata, "
            f"{len(self._immobili_selezionati_ids)} immobili trasferiti.",
            6000)
        if self._origine_partita and self._s1_comune_id:
            self.operazione_completata.emit(int(self._s1_comune_id))
        self._reset_wizard()


__all__ = [
    "BulkSuccessioneWizard",
    "parse_quota",
]
