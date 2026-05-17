
import os, csv, sys, logging, json  # noqa: F401, E401  — alcuni nomi sono re-export storici
from datetime import date, datetime  # noqa: F401  — re-export per consumer storici
from typing import Optional, List, Dict, Any, Tuple, TYPE_CHECKING  # noqa: F401
from app_utils import (  # noqa: F401  — re-export storici da gui_widgets
    BulkReportPDF, FPDF_AVAILABLE, _get_default_export_path, prompt_to_open_file,
)
from app_paths import get_icon_path  # noqa: F401  — re-export
import pandas as pd  # noqa: F401  — re-export per chiamanti storici

# Importazioni PyQt6
from PyQt6.QtCore import (  # noqa: F401  — alcuni Qt sono re-export storici
    QDate, QDateTime, QPoint, QProcess, QSize, QStandardPaths, QTimer, QUrl,
    QAbstractTableModel, QModelIndex, QProcessEnvironment, Qt, QSettings,
    QSortFilterProxyModel, pyqtSlot, pyqtSignal, QThread,
)

from PyQt6.QtGui import (  # noqa: F401  — re-export
    QCloseEvent, QColor, QDesktopServices, QFont, QIcon, QPalette, QPixmap, QAction,
)

# QWebEngineView: opzionale, riservato a future funzionalità web
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    WEB_ENGINE_AVAILABLE = True
except ImportError:
    QWebEngineView = None
    WEB_ENGINE_AVAILABLE = False

from PyQt6.QtWidgets import (  # noqa: F401  — re-export storici
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QDateEdit, QDateTimeEdit,
    QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFormLayout, QFrame,
    QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QInputDialog, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox,
    QProgressBar, QPushButton, QScrollArea, QSizePolicy, QSpacerItem, QSpinBox,
    QStyle, QStyleFactory, QTabWidget, QTableView, QTableWidget, QTableWidgetItem,
    QTextEdit, QVBoxLayout, QWidget, QProgressDialog, QTextBrowser, QSlider,
    QCompleter, QSplitter, QStackedWidget,
)

from config import (  # noqa: F401  — re-export di costanti storiche
    APP_VERSION,
    SETTINGS_DB_TYPE, SETTINGS_DB_HOST, SETTINGS_DB_PORT,
    SETTINGS_DB_NAME, SETTINGS_DB_USER, SETTINGS_DB_SCHEMA,
    COLONNE_POSSESSORI_DETTAGLI_NUM, COLONNE_POSSESSORI_DETTAGLI_LABELS,
    COLONNE_VISUALIZZAZIONE_POSSESSORI_NUM, COLONNE_VISUALIZZAZIONE_POSSESSORI_LABELS,
    COLONNE_INSERIMENTO_POSSESSORI_NUM, COLONNE_INSERIMENTO_POSSESSORI_LABELS,
    NUOVE_ETICHETTE_POSSESSORI,
)
from dialogs import (  # noqa: F401  — re-export
    ModificaPossessoreDialog, PartiteComuneDialog, ModificaImmobileDialog,
    PossessoriComuneDialog, LocalitaSelectionDialog, ModificaComuneDialog,
    PartitaDetailsDialog, CreateUserDialog, ModificaLocalitaDialog,
    PeriodoStoricoEditDialog, CreatePossessoreDialog, AlberoGeneralogicoDialog,
    ConfrontoPartiteDialog,
)
from foliarium.ui.widgets.custom import LazyLoadedWidget

# Ottieni un logger specifico per questo modulo.
logger = logging.getLogger("CatastoGUI.gui_widgets")
# In gui_main.py, dopo le importazioni PyQt e standard:
# E le sue eccezioni se servono qui
if TYPE_CHECKING:
    # Questa importazione avviene solo per i type checker (es. MyPy),
    # non a runtime, quindi non crea il ciclo.
    from gui_main import CatastoMainWindow  # noqa: F401
    from catasto_db_manager import CatastoDBManager  # noqa: F401

# In gui_widgets.py, dopo le importazioni PyQt e standard:
from foliarium.ui.widgets.custom import QPasswordLineEdit, StatCard  # noqa: F401
from dialogs import (  # noqa: F401  — re-export
    DBConfigDialog, DocumentViewerDialog, PeriodoStoricoDetailsDialog,
)
from dialogs import (  # noqa: F401  — re-export
    ComuneSelectionDialog, PartitaSearchDialog, PossessoreSelectionDialog,
    ImmobileDialog, DettagliLegamePossessoreDialog, UserSelectionDialog,
    qdate_to_datetime, datetime_to_qdate, _hash_password, _verify_password,
)

from app_utils import (  # noqa: F401  — re-export storici
    gui_esporta_partita_pdf, gui_esporta_partita_json, gui_esporta_partita_csv,
    gui_esporta_possessore_pdf, gui_esporta_possessore_json,
    gui_esporta_possessore_csv, GenericTextReportPDF, is_file_locked,
    get_alternative_filename,
)
# È possibile che alcune utility (es. hashing) siano usate da dialoghi che ora sono in gui_main.py
# In tal caso, gui_main.py importerà _hash_password da app_utils.py.


# Importazione del gestore DB e eccezioni
try:
    from catasto_db_manager import (  # noqa: F401  — re-export di eccezioni storiche
        CatastoDBManager, DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError,
    )
except ImportError:
    # Fallback o gestione errore
    class DBMError(Exception):
        pass  # ... definizioni fallback come nel file originale
    logger.warning("ATTENZIONE: catasto_db_manager non trovato, usando eccezioni DB fallback in gui_widgets.py")
# ---------------------------------------------------------------------------
# Costanti e helper globali UI/UX
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
    """Applica o rimuove il bordo rosso di errore via property [error="true"]."""
    widget.setProperty("error", "true" if has_error else "false")
    widget.style().unpolish(widget)
    widget.style().polish(widget)


from foliarium.ui.widgets.custom import show_status_message as _show_status_message


# ---------------------------------------------------------------------------

# Estratto in foliarium/ui/widgets/comuni.py — backward compat re-export
from foliarium.ui.widgets.comuni import (  # noqa: F401
    _ComuniLoaderWorker,
    ComuniTableModel,
    ElencoComuniWidget,
)


# Estratto in search_widgets.py — backward compat re-export
from search_widgets import (  # noqa: F401
    _PartiteSearchWorker, PartitaResultCard,
    RicercaPartiteWidget, RicercaAvanzataImmobiliWidget,
    UnifiedFuzzySearchThread, UnifiedFuzzySearchWidget,
)

# Estratto in insertion_widgets.py — backward compat re-export
from foliarium.ui.widgets.insertion import (  # noqa: F401
    InserimentoComuneWidget, InserimentoPossessoreWidget,
    InserimentoLocalitaWidget, InserimentoPartitaWidget,
)
from foliarium.ui.widgets.admin import (  # noqa: F401
    GestioneTipiLocalitaWidget, GestionePeriodiStoriciWidget,
)


# Estratto in partita_workflow_widgets.py — backward compat re-export
from partita_workflow_widgets import (  # noqa: F401
    RegistrazioneProprietaWidget,
    NuovaPartitaWizardWidget,
    OperazioniPartitaWidget,
)

# Estratto in admin_widgets.py — backward compat re-export
# Estratto in reporting_widgets.py — backward compat re-export
from foliarium.ui.widgets.reporting import (  # noqa: F401
    RicercaDocumentiWidget, EsportazioniWidget, ReportisticaWidget,
    StatisticheWidget, RegistraConsultazioneWidget,
)

from foliarium.ui.widgets.admin import (  # noqa: F401
    GestioneUtentiWidget, AuditLogViewerWidget, BackupWidget,
    ArchivioWidget, TipiPossessoWidget,
)

# Estratto in foliarium/ui/widgets/dashboard.py — backward compat re-export
from foliarium.ui.widgets.dashboard import (  # noqa: F401
    _DashboardLoaderWorker,
    DashboardWidget,
)


# Estratto in foliarium/ui/widgets/welcome.py — backward compat re-export
from foliarium.ui.widgets.welcome import WelcomeScreen  # noqa: F401
