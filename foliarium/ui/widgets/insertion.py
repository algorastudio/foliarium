"""
insertion_widgets.py — Widget di inserimento dati per Foliarium.

Estratto da gui_widgets.py per migliorare la modularità.
Contiene:
  - InserimentoComuneWidget     — Form inserimento nuovi comuni
  - InserimentoPossessoreWidget — Form inserimento nuovi possessori
  - InserimentoLocalitaWidget   — Form inserimento nuove località
  - InserimentoPartitaWidget    — Form inserimento nuove partite

Backward compatibility: gui_widgets.py re-esporta tutte le classi.
"""

from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any, TYPE_CHECKING

from PyQt6.QtCore import QDate, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDateEdit, QDialog,
    QFileDialog, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QSpinBox, QTextEdit,
    QVBoxLayout, QWidget, QCompleter,
)

from foliarium.ui.widgets.custom import (FormDraftMixin, LazyLoadedWidget,
                                         UnsavedFormMixin,
                                         imposta_nomi_accessibili)
from db.drafts import (FORM_KIND_INSERIMENTO_COMUNE,
                       FORM_KIND_INSERIMENTO_LOCALITA,
                       FORM_KIND_INSERIMENTO_PARTITA,
                       FORM_KIND_INSERIMENTO_POSSESSORE)
from catasto_exceptions import DBMError, DBUniqueConstraintError, DBDataError
from dialogs import ComuneSelectionDialog
from config import DATE_DISPLAY_FORMAT
from foliarium.ui.errors import show_user_error

if TYPE_CHECKING:
    from catasto_db_manager import CatastoDBManager

# ---------------------------------------------------------------------------
# Costanti e helper (duplicati da gui_widgets.py per evitare import circolare)
# ---------------------------------------------------------------------------

_PROVINCE_ITALIANE = [
    "AG","AL","AN","AO","AP","AQ","AR","AT","AV","BA","BG","BI","BL","BN","BO",
    "BR","BS","BT","BZ","CA","CB","CE","CH","CL","CN","CO","CR","CS","CT","CZ",
    "EN","FC","FE","FG","FI","FM","FR","GE","GO","GR","IM","IS","KR","LC","LE",
    "LI","LO","LT","LU","MB","MC","ME","MI","MN","MO","MS","MT","NA","NO","NU",
    "OG","OR","OT","PA","PC","PD","PE","PG","PI","PN","PO","PR","PT","PU","PV",
    "PZ","RA","RC","RE","RG","RI","RM","RN","RO","SA","SI","SO","SP","SR","SS",
    "SU","SV","TA","TE","TN","TO","TP","TR","TS","TV","UD","VA","VB","VC","VE",
    "VI","VR","VT","VV",
]

def _set_field_error(widget, has_error: bool) -> None:
    """Applica o rimuove il bordo rosso di errore da un widget di input.

    Usa la property [error="true"] gestita dal foglio di stile per
    mantenere coerenza visiva col tema (vs. inline CSS che soppianta
    border-radius, padding, ecc.).
    """
    widget.setProperty("error", "true" if has_error else "false")
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def _show_status_message(message: str, timeout_ms: int = 4000) -> None:
    """Mostra un messaggio nella status bar della finestra principale."""
    win = QApplication.activeWindow()
    if win and hasattr(win, "statusBar"):
        win.statusBar().showMessage(message, timeout_ms)


def _check_required(fields) -> bool:
    """Verifica i campi obbligatori di un form, segnalando cosa manca.

    ``fields`` e' una sequenza di tuple ``(widget, compilato, etichetta)``.
    Ogni widget viene marcato (o smarcato) con il bordo di errore; se
    qualcosa manca, la status bar elenca i campi da compilare e il focus
    va sul primo di essi.

    Senza questo riscontro il salvataggio fallirebbe in silenzio: l'utente
    preme "Inserisci" e, se il campo mancante e' fuori dalla porzione di
    form che sta guardando, non vede accadere nulla.

    Ritorna True se tutti i campi obbligatori sono compilati.
    """
    mancanti = [(w, etichetta) for w, compilato, etichetta in fields if not compilato]
    for widget, compilato, _ in fields:
        _set_field_error(widget, not compilato)
    if not mancanti:
        return True

    etichette = ", ".join(etichetta for _, etichetta in mancanti)
    if len(mancanti) == 1:
        _show_status_message(f"Campo obbligatorio mancante: {etichette}.", 6000)
    else:
        _show_status_message(f"Campi obbligatori mancanti: {etichette}.", 6000)
    mancanti[0][0].setFocus()
    return False


# ---------------------------------------------------------------------------

class InserimentoComuneWidget(FormDraftMixin, UnsavedFormMixin, LazyLoadedWidget):
    _DRAFT_KIND = FORM_KIND_INSERIMENTO_COMUNE
    _DRAFT_ETICHETTA = "Comune"

    comune_appena_inserito = pyqtSignal(int)
    import_csv_requested = pyqtSignal()
    scarica_csv_requested = pyqtSignal()

    def __init__(self, db_manager: 'CatastoDBManager', utente_attuale_info: Optional[Dict[str, Any]], parent=None):
        super().__init__(parent) # Chiama il costruttore della classe base
        self.db_manager = db_manager
        self.utente_attuale_info = utente_attuale_info
        # self.logger e self._data_loaded sono gestiti dalla classe base

        self._initUI()

    def _initUI(self):
        # ... (tutta la definizione della UI rimane la stessa)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(14)

        title = QLabel("Inserimento Comune")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Aggiungi un nuovo comune all'archivio catastale.")
        subtitle.setObjectName("pageSubtitle")
        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        form_group = QGroupBox("Dati del Nuovo Comune")
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(12)
        form_layout.setHorizontalSpacing(18)
        form_layout.setVerticalSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.nome_comune_edit = QLineEdit()
        _lbl_nome = QLabel('Nome Comune <span style="color:#e74c3c;font-weight:bold;">*</span>:')
        form_layout.addRow(_lbl_nome, self.nome_comune_edit)
        self.provincia_edit = QLineEdit("SV")
        self.provincia_edit.setMaxLength(100)
        _prov_completer = QCompleter(_PROVINCE_ITALIANE, self)
        _prov_completer.setCompletionMode(QCompleter.CompletionMode.InlineCompletion)
        _prov_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.provincia_edit.setCompleter(_prov_completer)
        _lbl_prov = QLabel('Provincia <span style="color:#e74c3c;font-weight:bold;">*</span>:')
        form_layout.addRow(_lbl_prov, self.provincia_edit)
        self.regione_edit = QLineEdit()
        self.regione_edit.setMaxLength(100)
        _lbl_reg = QLabel('Regione <span style="color:#e74c3c;font-weight:bold;">*</span>:')
        form_layout.addRow(_lbl_reg, self.regione_edit)
        # Reset errore al primo carattere digitato
        self.nome_comune_edit.textChanged.connect(lambda: _set_field_error(self.nome_comune_edit, False))
        self.provincia_edit.textChanged.connect(lambda: _set_field_error(self.provincia_edit, False))
        self.regione_edit.textChanged.connect(lambda: _set_field_error(self.regione_edit, False))
        self.codice_catastale_edit = QLineEdit()
        self.codice_catastale_edit.setPlaceholderText("Es. A123 (opzionale)")
        self.codice_catastale_edit.returnPressed.connect(self.inserisci_comune)
        form_layout.addRow("Codice Catastale:", self.codice_catastale_edit)
        self.data_istituzione_check = QCheckBox("Imposta data istituzione")
        self.data_istituzione_edit = QDateEdit(calendarPopup=True)
        self.data_istituzione_edit.setDisplayFormat(DATE_DISPLAY_FORMAT)
        self.data_istituzione_edit.setEnabled(False)
        self.data_istituzione_check.toggled.connect(self.data_istituzione_edit.setEnabled)
        data_istituzione_layout = QHBoxLayout(); data_istituzione_layout.addWidget(self.data_istituzione_check); data_istituzione_layout.addWidget(self.data_istituzione_edit)
        form_layout.addRow("Data Istituzione:", data_istituzione_layout)
        self.data_soppressione_check = QCheckBox("Imposta data soppressione")
        self.data_soppressione_edit = QDateEdit(calendarPopup=True)
        self.data_soppressione_edit.setDisplayFormat(DATE_DISPLAY_FORMAT)
        self.data_soppressione_edit.setEnabled(False)
        self.data_soppressione_check.toggled.connect(self.data_soppressione_edit.setEnabled)
        data_soppressione_layout = QHBoxLayout(); data_soppressione_layout.addWidget(self.data_soppressione_check); data_soppressione_layout.addWidget(self.data_soppressione_edit)
        form_layout.addRow("Data Soppressione:", data_soppressione_layout)
        self.note_edit = QTextEdit()
        self.note_edit.setMinimumHeight(60)
        form_layout.addRow("Note:", self.note_edit)
        self.periodo_combo = QComboBox()
        form_layout.addRow("Periodo Storico:", self.periodo_combo)
        main_layout.addWidget(form_group)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        # CSV utilities a sinistra (secondari)
        btn_import = QPushButton("Impor&ta CSV")
        btn_import.setObjectName("secondaryButton")
        btn_import.clicked.connect(self.import_csv_requested.emit)
        btn_import.setToolTip("Importa più comuni da un file CSV")
        btn_scarica = QPushButton("S&carica CSV")
        btn_scarica.setObjectName("secondaryButton")
        btn_scarica.clicked.connect(self.scarica_csv_requested.emit)
        btn_scarica.setToolTip("Scarica i comuni esistenti come file CSV")
        btn_template = QPushButton("Scarica temp&late")
        btn_template.setObjectName("secondaryButton")
        btn_template.clicked.connect(self._scarica_template_csv)
        btn_template.setToolTip("Scarica un file CSV di esempio con le colonne corrette")
        btn_bozza = QPushButton("&Riprendi bozza…")
        btn_bozza.setObjectName("secondaryButton")
        btn_bozza.setToolTip(
            "Riapri un modulo lasciato a metà. Le bozze si salvano quando "
            "esci da un modulo compilato.")
        btn_bozza.clicked.connect(self._riprendi_bozza)
        button_layout.addWidget(btn_import)
        button_layout.addWidget(btn_scarica)
        button_layout.addWidget(btn_template)
        button_layout.addWidget(btn_bozza)
        button_layout.addStretch()

        # Azioni primarie a destra
        self.clear_button = QPushButton("&Pulisci Campi")
        self.clear_button.setObjectName("secondaryButton")
        self.clear_button.clicked.connect(self.pulisci_campi)
        self.clear_button.setToolTip("Azzera tutti i campi del form")
        self.submit_button = QPushButton("&Inserisci Comune")
        self.submit_button.clicked.connect(self.inserisci_comune)
        self.submit_button.setDefault(True)
        self.submit_button.setToolTip("Salva il comune nel database (Invio)")
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.submit_button)

        main_layout.addLayout(button_layout)
        main_layout.addStretch(1)

    def _load_data_on_first_show(self):
        """Metodo per il lazy loading, chiamato la prima volta."""
        imposta_nomi_accessibili(self, {
            "nome_comune_edit": "Nome del comune (obbligatorio)",
            "provincia_edit": "Sigla della provincia (obbligatorio)",
            "regione_edit": "Regione (obbligatorio)",
            "codice_catastale_edit": "Codice catastale del comune",
            "note_edit": "Note sul comune",
            "periodo_combo": "Periodo storico di riferimento",
            "data_istituzione_edit": "Data di istituzione del comune",
            "data_soppressione_edit": "Data di soppressione del comune",
        })
        self.logger.info("InserimentoComuneWidget: Esecuzione lazy loading dei periodi storici...")
        self._carica_elenco_periodi()
        # Da qui in poi il form e' pulito: e' la base per rilevare
        # le modifiche non salvate.
        self.mark_form_clean()

    def _carica_elenco_periodi(self):
        self.periodo_combo.clear()
        self.periodo_combo.addItem("--- Nessuno ---", None)
        try:
            periodi = self.db_manager.get_historical_periods()
            if periodi:
                for periodo in periodi:
                    display_text = f"{periodo.get('nome')} ({periodo.get('anno_inizio')} - {periodo.get('anno_fine', 'oggi')})"
                    self.periodo_combo.addItem(display_text, periodo.get('id'))
        except DBMError as e:
            show_user_error(self, "Caricamento periodi storici", e, logger=getattr(self, "logger", None))


    def _scarica_template_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Salva template CSV comuni", "template_comuni.csv", "File CSV (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write("nome;provincia;regione;codice_catastale;data_istituzione;data_soppressione;note\n")
                f.write("Roma;RM;Lazio;H501;1871-01-01;;\n")
            _show_status_message(f"Template CSV salvato in: {path}", 6000)
        except Exception as e:
            QMessageBox.critical(self, "Errore", str(e))

    def trigger_primary_action(self) -> None:
        """Azione primaria del modulo (Ctrl+S): salva quanto compilato."""
        self.inserisci_comune()

    def pulisci_campi(self):
        self.nome_comune_edit.clear(); self.provincia_edit.setText("SV"); self.regione_edit.clear()
        self.codice_catastale_edit.clear(); self.note_edit.clear()
        
        # --- MODIFICA QUI: Resetta anche le checkbox ---
        self.data_istituzione_check.setChecked(False)
        self.data_soppressione_check.setChecked(False)
        # Il segnale 'toggled' disabiliterà automaticamente i QDateEdit
        
        self.periodo_combo.setCurrentIndex(0)
        for w in (self.nome_comune_edit, self.provincia_edit, self.regione_edit):
            _set_field_error(w, False)
        self.nome_comune_edit.setFocus()
        self.mark_form_clean()

    def inserisci_comune(self):
        # Raccoglie i dati da tutti i campi
        nome_comune = self.nome_comune_edit.text().strip()
        provincia = self.provincia_edit.text().strip()
        regione = self.regione_edit.text().strip()
        codice_catastale = self.codice_catastale_edit.text().strip() or None
        note = self.note_edit.toPlainText().strip() or None
        periodo_id_val = self.periodo_combo.currentData()
        
        # --- MODIFICA QUI: Legge le date solo se le checkbox sono spuntate ---
        data_ist = self.data_istituzione_edit.date().toPyDate() if self.data_istituzione_check.isChecked() else None
        data_sopp = self.data_soppressione_edit.date().toPyDate() if self.data_soppressione_check.isChecked() else None

        if not _check_required([
            (self.nome_comune_edit, bool(nome_comune), "Nome Comune"),
            (self.provincia_edit, bool(provincia), "Provincia"),
            (self.regione_edit, bool(regione), "Regione"),
        ]):
            return

        username_per_log = self.utente_attuale_info.get('username', 'utente_sconosciuto') if self.utente_attuale_info else 'utente_sconosciuto'
        
        try:
            comune_id = self.db_manager.aggiungi_comune(
                nome_comune=nome_comune, provincia=provincia, regione=regione,
                periodo_id=periodo_id_val, codice_catastale=codice_catastale,
                data_istituzione=data_ist, data_soppressione=data_sopp, # Passa i valori corretti (o None)
                note=note, utente=username_per_log
            )
            _show_status_message(f"Comune '{nome_comune}' inserito con successo (ID: {comune_id}).", 5000)
            self.pulisci_campi()
            self.comune_appena_inserito.emit(comune_id)
        except (DBUniqueConstraintError, DBDataError, DBMError) as e:
            show_user_error(self, "Inserimento comune", e, logger=getattr(self, "logger", None))

class InserimentoPossessoreWidget(FormDraftMixin, UnsavedFormMixin, LazyLoadedWidget):
    _DRAFT_KIND = FORM_KIND_INSERIMENTO_POSSESSORE
    _DRAFT_ETICHETTA = "Possessore"

    import_csv_requested = pyqtSignal()
    scarica_csv_requested = pyqtSignal()

    def __init__(self, db_manager: 'CatastoDBManager', parent=None):
        super().__init__(parent)  # Chiama il costruttore della classe base
        self.db_manager = db_manager
        self.comuni_list_data: List[Dict[str, Any]] = []
        # Il logger e il flag _data_loaded sono gestiti dalla classe base

        self._initUI()

    def _initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(14)

        title = QLabel("Inserimento Possessore")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Anagrafica di un nuovo possessore di partite catastali.")
        subtitle.setObjectName("pageSubtitle")
        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        form_group = QGroupBox("Dati del Nuovo Possessore")
        form_layout = QGridLayout(form_group)
        form_layout.setHorizontalSpacing(18)
        form_layout.setVerticalSpacing(12)
        form_layout.setContentsMargins(4, 4, 4, 4)
        form_layout.setColumnStretch(1, 1)

        _lbl_cn = QLabel('Cognome e Nome <span style="color:#C62828;font-weight:600;">*</span>:')
        _lbl_cn.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form_layout.addWidget(_lbl_cn, 0, 0)
        self.cognome_nome_edit = QLineEdit()
        self.cognome_nome_edit.setPlaceholderText("Es. Rossi Mario, Bianchi Giovanni")
        form_layout.addWidget(self.cognome_nome_edit, 0, 1)

        _lbl_pat = QLabel("Paternità (es. fu Carlo):")
        _lbl_pat.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form_layout.addWidget(_lbl_pat, 1, 0)
        self.paternita_edit = QLineEdit()
        form_layout.addWidget(self.paternita_edit, 1, 1)

        self.btn_genera_nome_completo = QPushButton("&Genera Nome Completo")
        self.btn_genera_nome_completo.setObjectName("secondaryButton")
        self.btn_genera_nome_completo.clicked.connect(self._genera_e_imposta_nome_completo)
        form_layout.addWidget(self.btn_genera_nome_completo, 2, 1, Qt.AlignmentFlag.AlignLeft)

        _lbl_nc = QLabel('Nome Completo (generato) <span style="color:#C62828;font-weight:600;">*</span>:')
        _lbl_nc.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form_layout.addWidget(_lbl_nc, 3, 0)
        self.nome_completo_edit = QLineEdit()
        self.nome_completo_edit.setPlaceholderText("Verrà generato o inserire manualmente")
        self.nome_completo_edit.returnPressed.connect(self._salva_possessore)
        form_layout.addWidget(self.nome_completo_edit, 3, 1)

        _lbl_com = QLabel('Comune di Riferimento <span style="color:#C62828;font-weight:600;">*</span>:')
        _lbl_com.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form_layout.addWidget(_lbl_com, 4, 0)
        self.comune_combo = QComboBox()
        self.comune_combo.addItem("Caricamento comuni...", None)
        self.comune_combo.setEnabled(False)
        form_layout.addWidget(self.comune_combo, 4, 1)

        self.attivo_checkbox = QCheckBox("Attivo")
        self.attivo_checkbox.setChecked(True)
        form_layout.addWidget(self.attivo_checkbox, 5, 1)

        # Reset errore al primo carattere digitato
        self.cognome_nome_edit.textChanged.connect(lambda: _set_field_error(self.cognome_nome_edit, False))
        self.nome_completo_edit.textChanged.connect(lambda: _set_field_error(self.nome_completo_edit, False))
        self.comune_combo.currentIndexChanged.connect(lambda: _set_field_error(self.comune_combo, False))

        main_layout.addWidget(form_group)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        btn_import = QPushButton("Impor&ta CSV")
        btn_import.setObjectName("secondaryButton")
        btn_import.clicked.connect(self.import_csv_requested.emit)
        btn_import.setToolTip("Importa più possessori da un file CSV")
        btn_scarica = QPushButton("S&carica CSV")
        btn_scarica.setObjectName("secondaryButton")
        btn_scarica.clicked.connect(self.scarica_csv_requested.emit)
        btn_scarica.setToolTip("Scarica i possessori esistenti come file CSV")
        btn_template = QPushButton("Scarica temp&late")
        btn_template.setObjectName("secondaryButton")
        btn_template.clicked.connect(self._scarica_template_csv)
        btn_template.setToolTip("Scarica un file CSV di esempio con le colonne corrette")
        btn_bozza = QPushButton("&Riprendi bozza…")
        btn_bozza.setObjectName("secondaryButton")
        btn_bozza.setToolTip(
            "Riapri un modulo lasciato a metà. Le bozze si salvano quando "
            "esci da un modulo compilato.")
        btn_bozza.clicked.connect(self._riprendi_bozza)
        button_layout.addWidget(btn_import)
        button_layout.addWidget(btn_scarica)
        button_layout.addWidget(btn_template)
        button_layout.addWidget(btn_bozza)
        button_layout.addStretch()

        self.clear_button = QPushButton("&Pulisci Campi")
        self.clear_button.setObjectName("secondaryButton")
        self.clear_button.clicked.connect(self._pulisci_campi_possessore)
        self.clear_button.setToolTip("Azzera tutti i campi del form")
        self.save_button = QPushButton("&Salva Possessore")
        self.save_button.setDefault(True)
        self.save_button.clicked.connect(self._salva_possessore)
        self.save_button.setToolTip("Salva il possessore nel database (Invio)")
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.save_button)

        main_layout.addLayout(button_layout)
        main_layout.addStretch(1)

    def _load_data_on_first_show(self):
        """Metodo per il lazy loading: carica i comuni la prima volta che il tab viene visualizzato."""
        imposta_nomi_accessibili(self, {
            "cognome_nome_edit": "Cognome e nome del possessore (obbligatorio)",
            "paternita_edit": "Paternità, ad esempio fu Carlo",
            "nome_completo_edit": "Nome completo del possessore (obbligatorio)",
            "comune_combo": "Comune di riferimento (obbligatorio)",
            "attivo_checkbox": "Possessore attivo",
        })
        self.logger.info("InserimentoPossessoreWidget: Esecuzione lazy loading dei comuni...")
        self._load_comuni_for_combo()
        # Da qui in poi il form e' pulito: e' la base per rilevare
        # le modifiche non salvate.
        self.mark_form_clean()

    def _load_comuni_for_combo(self):
        """Carica e popola il QComboBox con l'elenco dei comuni."""
        self.comune_combo.clear()
        try:
            comuni = self.db_manager.get_elenco_comuni_semplice()
            if comuni:
                self.comune_combo.setEnabled(True)
                self.comune_combo.addItem("--- Seleziona un comune ---", None)
                for comune_id, nome in comuni:
                    self.comune_combo.addItem(nome, userData=comune_id)
            else:
                self.comune_combo.addItem("Nessun comune registrato", None)
                self.comune_combo.setEnabled(False)
        except DBMError as e:
            self.logger.error(f"Errore caricamento comuni: {e}")
            self.comune_combo.addItem("Errore caricamento", None)
            self.comune_combo.setEnabled(False)

    def _mostra_info_formato_csv(self):
        """Mostra un dialogo con le informazioni sul formato CSV per i possessori."""
        info_text = """
        <h3>Formato CSV per Importazione Possessori</h3>
        <p>Il file CSV deve rispettare le seguenti regole:</p>
        <ul>
            <li>Utilizzare il punto e virgola (<b>;</b>) come delimitatore.</li>
            <li>La prima riga deve contenere le intestazioni delle colonne.</li>
            <li>Le virgolette doppie (") sono gestite correttamente.</li>
        </ul>
        <p><b>Colonne Richieste:</b></p>
        <ul>
            <li><b>cognome_nome</b>: Il cognome e nome separati da spazio (es. Rossi Mario).</li>
            <li><b>nome_completo</b>: Il nome completo come deve apparire, includendo la paternità.</li>
        </ul>
        <p><b>Colonne Opzionali:</b></p>
        <ul>
            <li><b>paternita</b>: La paternità (es. fu Carlo).</li>
        </ul>
        <hr>
        <p><b>Esempio di contenuto del file:</b></p>
        <pre style="background-color:#f0f0f0; padding:5px;"><code>cognome_nome;paternita;nome_completo
        Rossi Mario;fu Giovanni;Rossi Mario fu Giovanni
        Bianchi Giuseppe;;Bianchi Giuseppe</code></pre>
        """
        QMessageBox.information(self, "Guida Formato CSV - Possessori", info_text)

    def _genera_e_imposta_nome_completo(self):
        """
        Genera il nome completo concatenando "Cognome Nome" e "Paternità"
        e lo imposta nel campo nome_completo_edit.
        """
        cognome_nome = self.cognome_nome_edit.text().strip()
        paternita = self.paternita_edit.text().strip()
        nome_completo_generato = cognome_nome # Inizia con cognome e nome

        if cognome_nome and paternita: # Aggiungi paternità solo se entrambi sono presenti
            nome_completo_generato += f" {paternita}" # Es. "Rossi Mario fu Giovanni"
        elif cognome_nome and not paternita: # Solo cognome e nome
            pass # nome_completo_generato è già corretto
        elif not cognome_nome and paternita: # Solo paternità (improbabile ma gestito)
            nome_completo_generato = paternita 
        else: # Entrambi vuoti
            nome_completo_generato = ""
            
        self.nome_completo_edit.setText(nome_completo_generato.strip())

    def _scarica_template_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Salva template CSV possessori", "template_possessori.csv", "File CSV (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write("cognome_nome;nome_completo;paternita\n")
                f.write("Rossi Mario;Mario Rossi;fu Giovanni\n")
            _show_status_message(f"Template CSV salvato in: {path}", 6000)
        except Exception as e:
            QMessageBox.critical(self, "Errore", str(e))

    def trigger_primary_action(self) -> None:
        """Azione primaria del modulo (Ctrl+S): salva quanto compilato."""
        self._salva_possessore()

    def _pulisci_campi_possessore(self):
        """Pulisce i campi del form possessore."""
        self.cognome_nome_edit.clear()
        self.paternita_edit.clear()
        self.nome_completo_edit.clear()
        if self.comune_combo.count() > 0:
            self.comune_combo.setCurrentIndex(0) # O -1 per nessuna selezione se preferito
        self.attivo_checkbox.setChecked(True)
        for w in (self.cognome_nome_edit, self.nome_completo_edit, self.comune_combo):
            _set_field_error(w, False)
        self.cognome_nome_edit.setFocus()
        self.mark_form_clean()

    def _salva_possessore(self):
        # Ora 'cognome_nome' è l'input primario per nome/cognome
        # 'nome_completo' è quello generato o corretto dall'utente
        cognome_nome_input = self.cognome_nome_edit.text().strip() # Usato per DB e per generare nome completo se serve
        paternita_input = self.paternita_edit.text().strip()
        nome_completo_input = self.nome_completo_edit.text().strip() # Questo è il valore da salvare

        idx_comune = self.comune_combo.currentIndex()
        comune_id_selezionato_data = self.comune_combo.itemData(idx_comune)
        comune_id_selezionato: Optional[int] = None
        if comune_id_selezionato_data is not None:
            try:
                comune_id_selezionato = int(comune_id_selezionato_data)
            except ValueError:
                QMessageBox.warning(self, "Errore Interno", "ID comune selezionato non valido.")
                return

        attivo = self.attivo_checkbox.isChecked()

        if not _check_required([
            (self.cognome_nome_edit, bool(cognome_nome_input), "Cognome e Nome"),
            (self.nome_completo_edit, bool(nome_completo_input), "Nome Completo"),
            (self.comune_combo, comune_id_selezionato is not None, "Comune di Riferimento"),
        ]):
            return

        try:
            new_possessore_id = self.db_manager.create_possessore(
                nome_completo=nome_completo_input,
                paternita=paternita_input if paternita_input else None,
                comune_riferimento_id=comune_id_selezionato,
                attivo=attivo,
                cognome_nome=cognome_nome_input # Passa il campo cognome_nome al DB manager
            )

            if new_possessore_id is not None:
                _show_status_message(f"Possessore '{nome_completo_input}' inserito con successo (ID: {new_possessore_id}).", 5000)
                self._pulisci_campi_possessore()
                # Qui potresti emettere un segnale se altri widget devono essere aggiornati
            # else: create_possessore solleva eccezioni
        # ... (stessa gestione eccezioni di prima per _salva_possessore) ...
        except DBUniqueConstraintError as uve:
            logging.getLogger("CatastoGUI").warning(f"Errore di unicità salvando possessore '{nome_completo_input}': {uve.message}")
            QMessageBox.critical(self, "Errore di Unicità", f"Impossibile creare il possessore:\n{uve.message}")
        except DBDataError as dde:
            logging.getLogger("CatastoGUI").warning(f"Errore dati per possessore '{nome_completo_input}': {dde.message}")
            QMessageBox.warning(self, "Dati Non Validi", f"Impossibile creare il possessore:\n{dde.message}")
        except DBMError as dbe:
            logging.getLogger("CatastoGUI").error(f"Errore database salvando possessore '{nome_completo_input}': {dbe.message}", exc_info=True)
            QMessageBox.critical(self, "Errore Database", f"Si è verificato un errore durante la creazione del possessore:\n{dbe.message}")
        except Exception as e:
            logging.getLogger("CatastoGUI").critical(f"Errore critico imprevisto salvando possessore '{nome_completo_input}': {e}", exc_info=True)
            show_user_error(self, "Inserimento possessore", e, logger=getattr(self, "logger", None))



# --- Scheda per Localita ---
class InserimentoLocalitaWidget(FormDraftMixin, UnsavedFormMixin, QWidget):
    _DRAFT_KIND = FORM_KIND_INSERIMENTO_LOCALITA
    _DRAFT_ETICHETTA = "Località"

    import_csv_requested = pyqtSignal()
    scarica_csv_requested = pyqtSignal()

    def __init__(self, db_manager, parent=None):
        super(InserimentoLocalitaWidget, self).__init__(parent)
        self.db_manager = db_manager
        self.comune_id = None
        self._initUI()
        # Non carichiamo i tipi qui, ma quando un comune viene selezionato

    def _initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        title = QLabel("Inserimento Località")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Aggiungi una nuova località geografica (frazione, contrada, regione).")
        subtitle.setObjectName("pageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        form_group = QGroupBox("Inserimento Nuova Località")
        form_layout = QGridLayout(form_group)
        form_layout.setHorizontalSpacing(14)
        form_layout.setVerticalSpacing(12)
        form_layout.setContentsMargins(4, 4, 4, 4)
        form_layout.setColumnStretch(1, 1)
        form_layout.setColumnStretch(2, 2)

        comune_label = QLabel('Comune <span style="color:#C62828;font-weight:600;">*</span>:')
        comune_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.comune_button = QPushButton("Selezi&ona Comune…")
        self.comune_button.setObjectName("secondaryButton")
        self.comune_button.clicked.connect(self.select_comune)
        self.comune_display = QLabel("Nessun comune selezionato")
        self.comune_display.setProperty("muted", "true")
        form_layout.addWidget(comune_label, 0, 0)
        form_layout.addWidget(self.comune_button, 0, 1)
        form_layout.addWidget(self.comune_display, 0, 2)

        nome_label = QLabel('Nome località <span style="color:#C62828;font-weight:600;">*</span>:')
        nome_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.nome_edit = QLineEdit()
        self.nome_edit.textChanged.connect(lambda: _set_field_error(self.nome_edit, False))
        self.nome_edit.returnPressed.connect(self.insert_localita)
        form_layout.addWidget(nome_label, 1, 0)
        form_layout.addWidget(self.nome_edit, 1, 1, 1, 2)

        tipo_label = QLabel('Tipo <span style="color:#C62828;font-weight:600;">*</span>:')
        tipo_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.tipo_combo = QComboBox()
        self.tipo_combo.addItem("Seleziona prima un comune...", None)
        self.tipo_combo.setEnabled(False)
        self.tipo_combo.currentIndexChanged.connect(lambda: _set_field_error(self.tipo_combo, False))
        form_layout.addWidget(tipo_label, 2, 0)
        form_layout.addWidget(self.tipo_combo, 2, 1, 1, 2)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        btn_import = QPushButton("Impor&ta CSV")
        btn_import.setObjectName("secondaryButton")
        btn_import.clicked.connect(self.import_csv_requested.emit)
        btn_import.setToolTip("Importa più località da un file CSV")
        btn_scarica = QPushButton("S&carica CSV")
        btn_scarica.setObjectName("secondaryButton")
        btn_scarica.clicked.connect(self.scarica_csv_requested.emit)
        btn_scarica.setToolTip("Scarica le località esistenti come file CSV")
        btn_template = QPushButton("Scarica temp&late")
        btn_template.setObjectName("secondaryButton")
        btn_template.clicked.connect(self._scarica_template_csv)
        btn_template.setToolTip("Scarica un file CSV di esempio con le colonne corrette")
        btn_bozza = QPushButton("&Riprendi bozza…")
        btn_bozza.setObjectName("secondaryButton")
        btn_bozza.setToolTip(
            "Riapri un modulo lasciato a metà. Le bozze si salvano quando "
            "esci da un modulo compilato.")
        btn_bozza.clicked.connect(self._riprendi_bozza)
        button_layout.addWidget(btn_import)
        button_layout.addWidget(btn_scarica)
        button_layout.addWidget(btn_template)
        button_layout.addWidget(btn_bozza)
        button_layout.addStretch()

        btn_pulisci = QPushButton("&Pulisci Campi")
        btn_pulisci.setObjectName("secondaryButton")
        btn_pulisci.clicked.connect(self._pulisci_campi)
        btn_pulisci.setToolTip("Azzera tutti i campi del form")
        btn_inserisci = QPushButton("&Inserisci Località")
        btn_inserisci.setDefault(True)
        btn_inserisci.clicked.connect(self.insert_localita)
        btn_inserisci.setToolTip("Salva la località nel database (Invio)")
        self._btn_inserisci_localita = btn_inserisci
        button_layout.addWidget(btn_pulisci)
        button_layout.addWidget(btn_inserisci)

        layout.addLayout(button_layout)
        layout.addStretch(1)

        self.setLayout(layout)
        imposta_nomi_accessibili(self, {
            "comune_button": "Comune della località (obbligatorio)",
            "nome_edit": "Nome della località (obbligatorio)",
            "tipo_combo": "Tipologia stradale, ad esempio Via o Piazza (obbligatorio)",
        })
        self.mark_form_clean()

    def trigger_primary_action(self) -> None:
        """Azione primaria del modulo (Ctrl+S): salva quanto compilato."""
        self.insert_localita()

    def _pulisci_campi(self):
        self.nome_edit.clear()
        for w in (self.nome_edit, self.tipo_combo):
            _set_field_error(w, False)
        self.nome_edit.setFocus()
        self.mark_form_clean()

    def _scarica_template_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Salva template CSV località", "template_localita.csv", "File CSV (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write("nome;tipologia_stradale\n")
                f.write("Roma;Via\n")
                f.write("Garibaldi;Piazza\n")
                f.write("Pianello;Borgata\n")
            _show_status_message(f"Template CSV salvato in: {path}", 6000)
        except Exception as e:
            QMessageBox.critical(self, "Errore", str(e))

    def _load_tipi_localita(self):
        """Carica dinamicamente le tipologie di località nel ComboBox."""
        self.tipo_combo.clear()
        try:
            tipi = self.db_manager.get_tipi_localita()
            if tipi:
                self.tipo_combo.addItem("--- Seleziona Tipo ---", None)
                for tipo in tipi:
                    self.tipo_combo.addItem(tipo['nome'], tipo['id'])
                self.tipo_combo.setEnabled(True)
            else:
                self.tipo_combo.addItem("Nessuna tipologia definita", None)
                self.tipo_combo.setEnabled(False)
        except DBMError as e:
            self.tipo_combo.addItem("Errore caricamento", None)
            self.tipo_combo.setEnabled(False)
            show_user_error(self, "Caricamento tipologie di località", e, logger=getattr(self, "logger", None))

    def select_comune(self):
        dialog = ComuneSelectionDialog(self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_comune_id:
            self.comune_id = dialog.selected_comune_id
            self.comune_display.setText(dialog.selected_comune_name)
            _set_field_error(self.comune_button, False)
            self._load_tipi_localita()
            # Scegliere il comune popola il menu delle tipologie: si riparte
            # da qui, cosi' il solo cambio di comune non risulta "da salvare".
            self.mark_form_clean()

    def insert_localita(self):
        nome = self.nome_edit.text().strip()
        tipologia_stradale = (
            self.tipo_combo.currentText() if self.tipo_combo.currentData() else None
        )

        if not _check_required([
            (self.comune_button, bool(self.comune_id), "Comune"),
            (self.tipo_combo, bool(tipologia_stradale), "Tipologia (Via, Piazza, ...)"),
            (self.nome_edit, bool(nome), "Nome della località"),
        ]):
            return

        try:
            localita_id = self.db_manager.insert_localita(self.comune_id, nome, tipologia_stradale)
            _show_status_message(
                f"Località '{tipologia_stradale} {nome}' inserita con successo (ID: {localita_id}).",
                5000,
            )
            self.nome_edit.clear()
            self.mark_form_clean()
        except (DBMError, DBDataError, DBUniqueConstraintError) as e:
            show_user_error(self, "Inserimento località", e, logger=getattr(self, "logger", None))

class InserimentoPartitaWidget(FormDraftMixin, UnsavedFormMixin, QWidget):
    _DRAFT_KIND = FORM_KIND_INSERIMENTO_PARTITA
    _DRAFT_ETICHETTA = "Partita"

    import_csv_requested = pyqtSignal()
    scarica_csv_requested = pyqtSignal()

    def __init__(self, db_manager: 'CatastoDBManager', parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")
        self._initUI()
        self.load_initial_data() # Carichiamo i dati necessari come i comuni

    def _initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(14)

        title = QLabel("Inserimento Partita")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Crea una nuova partita catastale collegata a un comune.")
        subtitle.setObjectName("pageSubtitle")
        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        form_group = QGroupBox("Dati Nuova Partita")
        form_layout = QFormLayout(form_group)
        form_layout.setHorizontalSpacing(18)
        form_layout.setVerticalSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        # --- CAMPI DEL FORM AGGIORNATI SECONDO LO SCHEMA ---
        self.comune_combo = QComboBox()
        self.comune_combo.currentIndexChanged.connect(lambda: _set_field_error(self.comune_combo, False))
        _lbl_comune_p = QLabel('Comune <span style="color:#C62828;font-weight:600;">*</span>:')
        form_layout.addRow(_lbl_comune_p, self.comune_combo)

        self.numero_partita_spin = QSpinBox()
        self.numero_partita_spin.setRange(1, 999999)
        _lbl_num = QLabel('Numero Partita <span style="color:#C62828;font-weight:600;">*</span>:')
        form_layout.addRow(_lbl_num, self.numero_partita_spin)

        self.suffisso_edit = QLineEdit()
        self.suffisso_edit.setPlaceholderText("Es. bis, A (opzionale)")
        self.suffisso_edit.setMaxLength(20)
        self.suffisso_edit.returnPressed.connect(self._salva_partita)
        form_layout.addRow("Suffisso Partita:", self.suffisso_edit)

        self.data_impianto_edit = QDateEdit(calendarPopup=True)
        self.data_impianto_edit.setDisplayFormat(DATE_DISPLAY_FORMAT)
        self.data_impianto_edit.setDate(QDate.currentDate())
        _lbl_data = QLabel('Data Impianto <span style="color:#C62828;font-weight:600;">*</span>:')
        form_layout.addRow(_lbl_data, self.data_impianto_edit)

        # NUOVO: Campo per data_chiusura (opzionale)
        self.data_chiusura_check = QCheckBox("Imposta data chiusura")
        self.data_chiusura_check.toggled.connect(self._toggle_data_chiusura)
        self.data_chiusura_edit = QDateEdit(calendarPopup=True)
        self.data_chiusura_edit.setDisplayFormat(DATE_DISPLAY_FORMAT)
        self.data_chiusura_edit.setEnabled(False) # Inizia disabilitato
        data_chiusura_layout = QHBoxLayout()
        data_chiusura_layout.addWidget(self.data_chiusura_check)
        data_chiusura_layout.addWidget(self.data_chiusura_edit)
        form_layout.addRow("Data Chiusura:", data_chiusura_layout)
        
        # CORRETTO: Campo per numero_provenienza (testuale)
        self.numero_provenienza_edit = QLineEdit()
        self.numero_provenienza_edit.setPlaceholderText("Numero o testo di riferimento (opzionale)")
        self.numero_provenienza_edit.setMaxLength(50)
        form_layout.addRow("Numero Provenienza:", self.numero_provenienza_edit)

        self.tipo_combo = QComboBox()
        self.tipo_combo.addItems(["principale", "secondaria"])
        _lbl_tipo = QLabel('Tipo <span style="color:#C62828;font-weight:600;">*</span>:')
        form_layout.addRow(_lbl_tipo, self.tipo_combo)

        self.stato_combo = QComboBox()
        self.stato_combo.addItems(["attiva", "inattiva"])
        _lbl_stato = QLabel('Stato <span style="color:#C62828;font-weight:600;">*</span>:')
        form_layout.addRow(_lbl_stato, self.stato_combo)

        main_layout.addWidget(form_group)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        btn_import = QPushButton("Impor&ta CSV")
        btn_import.setObjectName("secondaryButton")
        btn_import.clicked.connect(self.import_csv_requested.emit)
        btn_import.setToolTip("Importa più partite da un file CSV o Excel")
        btn_scarica = QPushButton("S&carica CSV")
        btn_scarica.setObjectName("secondaryButton")
        btn_scarica.clicked.connect(self.scarica_csv_requested.emit)
        btn_scarica.setToolTip("Scarica le partite esistenti come file CSV")
        btn_template = QPushButton("Scarica temp&late")
        btn_template.setObjectName("secondaryButton")
        btn_template.clicked.connect(self._scarica_template_csv)
        btn_template.setToolTip("Scarica un file CSV di esempio con le colonne corrette")
        btn_bozza = QPushButton("&Riprendi bozza…")
        btn_bozza.setObjectName("secondaryButton")
        btn_bozza.setToolTip(
            "Riapri un modulo lasciato a metà. Le bozze si salvano quando "
            "esci da un modulo compilato.")
        btn_bozza.clicked.connect(self._riprendi_bozza)
        button_layout.addWidget(btn_import)
        button_layout.addWidget(btn_scarica)
        button_layout.addWidget(btn_template)
        button_layout.addWidget(btn_bozza)
        button_layout.addStretch()

        btn_pulisci = QPushButton("&Pulisci Campi")
        btn_pulisci.setObjectName("secondaryButton")
        btn_pulisci.clicked.connect(self._pulisci_campi)
        btn_pulisci.setToolTip("Azzera tutti i campi del form")
        btn_salva = QPushButton("&Salva Partita")
        btn_salva.setDefault(True)
        btn_salva.clicked.connect(self._salva_partita)
        btn_salva.setToolTip("Salva la partita nel database (Invio)")
        self._btn_salva_partita = btn_salva
        button_layout.addWidget(btn_pulisci)
        button_layout.addWidget(btn_salva)

        main_layout.addLayout(button_layout)
        main_layout.addStretch()
        self.setLayout(main_layout)
        
    def _mostra_info_formato_csv(self):
        """Mostra un dialogo con le informazioni sul formato CSV per le partite."""
        info_text = """
        <h3>Formato CSV per Importazione Partite</h3>
        <p>Il file CSV deve rispettare le seguenti regole:</p>
        <ul>
            <li>Utilizzare il punto e virgola (<b>;</b>) come delimitatore.</li>
            <li>La prima riga deve contenere le intestazioni delle colonne.</li>
        </ul>
        <p><b>Colonne Richieste (*):</b></p>
        <ul>
            <li><b>numero_partita</b> (*): Numero intero della partita.</li>
            <li><b>data_impianto</b> (*): Data in formato YYYY-MM-DD.</li>
            <li><b>stato</b> (*): Testo, 'attiva' o 'inattiva'.</li>
            <li><b>tipo</b> (*): Testo, 'principale' o 'secondaria'.</li>
        </ul>
        <p><b>Colonne Opzionali:</b></p>
        <ul>
            <li><b>suffisso_partita</b>: Suffisso testuale (es. A, bis).</li>
            <li><b>data_chiusura</b>: Data in formato YYYY-MM-DD.</li>
            <li><b>numero_provenienza</b>: Testo o numero di riferimento.</li>
        </ul>
        <hr>
        <p><b>Esempio di contenuto del file:</b></p>
        <pre style="background-color:#f0f0f0; padding:5px;"><code>numero_partita;suffisso_partita;data_impianto;stato;tipo
        1005;A;1980-05-20;attiva;principale
        1006;;1975-11-10;inattiva;principale</code></pre>
        """
        QMessageBox.information(self, "Guida Formato CSV - Partite", info_text)

    def load_initial_data(self):
        """Metodo per caricare i dati necessari, come la lista dei comuni."""
        imposta_nomi_accessibili(self, {
            "comune_combo": "Comune della partita (obbligatorio)",
            "numero_partita_spin": "Numero della partita",
            "suffisso_edit": "Suffisso del numero di partita",
            "data_impianto_edit": "Data di impianto della partita",
            "data_chiusura_edit": "Data di chiusura della partita",
            "numero_provenienza_edit": "Numero di provenienza",
            "tipo_combo": "Tipo di partita",
            "stato_combo": "Stato della partita",
        })
        try:
            comuni = self.db_manager.get_elenco_comuni_semplice()
            self.comune_combo.clear()
            self.comune_combo.addItem("--- Seleziona un comune ---", None)
            for id_comune, nome in comuni:
                self.comune_combo.addItem(nome, id_comune)
        except DBMError as e:
            show_user_error(self, "Caricamento elenco comuni", e, logger=getattr(self, "logger", None))
        # Da qui in poi il form e' pulito: e' la base per rilevare
        # le modifiche non salvate.
        self.mark_form_clean()

    def _toggle_data_chiusura(self, checked):
        """Abilita o disabilita il QDateEdit per la data di chiusura."""
        self.data_chiusura_edit.setEnabled(checked)
        if checked:
            self.data_chiusura_edit.setDate(QDate.currentDate())
        else:
            self.data_chiusura_edit.setDate(QDate()) # Data nulla

    def trigger_primary_action(self) -> None:
        """Azione primaria del modulo (Ctrl+S): salva quanto compilato."""
        self._salva_partita()

    def _pulisci_campi(self):
        self.comune_combo.setCurrentIndex(0)
        self.numero_partita_spin.setValue(1)
        self.suffisso_edit.clear()
        self.data_impianto_edit.setDate(QDate.currentDate())
        self.data_chiusura_check.setChecked(False)
        self.numero_provenienza_edit.clear()
        self.tipo_combo.setCurrentIndex(0)
        self.stato_combo.setCurrentIndex(0)
        _set_field_error(self.comune_combo, False)
        self.mark_form_clean()

    def _scarica_template_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Salva template CSV partite", "template_partite.csv", "File CSV (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write("comune_nome;numero_partita;suffisso_partita;data_impianto;tipo_partita;numero_provenienza;stato\n")
                f.write("Roma;1;;1900-01-01;principale;;attiva\n")
            _show_status_message(f"Template CSV salvato in: {path}", 6000)
        except Exception as e:
            QMessageBox.critical(self, "Errore", str(e))

    def _salva_partita(self):
        comune_id = self.comune_combo.currentData()
        if not _check_required([
            (self.comune_combo, bool(comune_id), "Comune"),
        ]):
            return

        # Recupera i dati dai campi, inclusi i nuovi
        data_chiusura = self.data_chiusura_edit.date().toPyDate() if self.data_chiusura_check.isChecked() else None
        numero_provenienza = self.numero_provenienza_edit.text().strip() or None

        try:
            new_id = self.db_manager.create_partita(
                comune_id=comune_id,
                numero_partita=self.numero_partita_spin.value(),
                tipo=self.tipo_combo.currentText(),
                stato=self.stato_combo.currentText(),
                data_impianto=self.data_impianto_edit.date().toPyDate(),
                suffisso_partita=self.suffisso_edit.text().strip() or None,
                data_chiusura=data_chiusura, # Passa il nuovo valore
                numero_provenienza=numero_provenienza # Passa il nuovo valore
            )
            _show_status_message(f"Partita creata con successo (ID: {new_id}).", 5000)
            self._pulisci_campi()
        except (DBMError, DBUniqueConstraintError, DBDataError) as e:
            show_user_error(self, "Salvataggio partita", e, logger=getattr(self, "logger", None))


