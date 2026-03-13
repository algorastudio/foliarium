
import os,csv,sys,logging,json
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Tuple, TYPE_CHECKING

# Importazioni PyQt5
# Importazioni necessarie (QSvgWidget già dovrebbe esserci dalla risposta precedente)
#from PyQt5.QtSvgWidgets import QSvgWidget
# QByteArray non è più necessario se carichi da file
# from PyQt5.QtCore import QByteArray
# Importazioni PyQt5
from PyQt5.QtCore import (QDate, QDateTime, QPoint, QProcess, QSettings, 
                          QSize, QStandardPaths, Qt, QTimer, QUrl, 
                          pyqtSignal)

from PyQt5.QtGui import (QCloseEvent, QColor, QDesktopServices, QFont, 
                         QIcon, QPalette, QPixmap)

from PyQt5.QtWebEngineWidgets import QWebEngineView

from PyQt5.QtWidgets import (QAbstractItemView, QAction, QApplication, 
                             QCheckBox, QComboBox, QDateEdit, QDateTimeEdit,
                             QDialog, QDialogButtonBox, QDoubleSpinBox,
                             QFileDialog, QFormLayout, QFrame, QGridLayout,
                             QGroupBox, QHBoxLayout, QHeaderView, QInputDialog,
                             QLabel, QLineEdit, QListWidget, QListWidgetItem,
                             QMainWindow, QMenu, QMessageBox, QProgressBar,
                             QPushButton, QScrollArea, QSizePolicy, QSpacerItem,
                             QSpinBox, QStyle, QStyleFactory, QTabWidget,
                             QTableWidget, QTableWidgetItem, QTextEdit,
                             QVBoxLayout, QWidget)
from PyQt5.QtCore import Qt, QSettings, pyqtSlot
# Importazione commentata (da abilitare se necessario)
# from PyQt5.QtSvgWidgets import QSvgWidget
class ImmobiliTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super(ImmobiliTableWidget, self).__init__(parent)

        # Impostazione colonne
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(
            ["ID", "Natura", "Classificazione", "Consistenza", "Località"])

        # Altre impostazioni
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setStretchLastSection(True)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSortingEnabled(True)

    def populate_data(self, immobili: List[Dict]):
        """Popola la tabella con i dati degli immobili."""
        self.setRowCount(0)  # Resetta la tabella

        for immobile in immobili:
            row_position = self.rowCount()
            self.insertRow(row_position)

            # Imposta i dati per ogni cella
            self.setItem(row_position, 0, QTableWidgetItem(
                str(immobile.get('id', ''))))
            self.setItem(row_position, 1, QTableWidgetItem(
                immobile.get('natura', '')))
            self.setItem(row_position, 2, QTableWidgetItem(
                immobile.get('classificazione', '')))
            self.setItem(row_position, 3, QTableWidgetItem(
                immobile.get('consistenza', '')))

            # Informazioni sulla località
            localita_text = ""
            if 'localita_nome' in immobile:
                localita_text = immobile['localita_nome']
                if 'civico' in immobile and immobile['civico'] is not None:
                    localita_text += f", {immobile['civico']}"
                if 'localita_tipo' in immobile:
                    localita_text += f" ({immobile['localita_tipo']})"

            self.setItem(row_position, 4, QTableWidgetItem(localita_text))

        # Adatta le dimensioni delle colonne al contenuto
        self.resizeColumnsToContents()
class QPasswordLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEchoMode(QLineEdit.Password)
# In custom_widgets.py

import logging
from PyQt5.QtWidgets import QWidget

class LazyLoadedWidget(QWidget):
    """
    Una classe base per tutti i widget che necessitano di caricare dati
    solo la prima volta che vengono visualizzati (lazy loading).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data_loaded = False
        # Ogni sottoclasse dovrebbe avere il proprio logger
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")

    def load_initial_data(self):
        """
        Metodo universale chiamato dalla finestra principale.
        Controlla se i dati sono già stati caricati e, in caso negativo,
        chiama il metodo di caricamento specifico della sottoclasse.
        """
        if self._data_loaded:
            return  # Non fare nulla se già caricato

        self.logger.info(f"Esecuzione lazy loading per {self.__class__.__name__}...")
        self._load_data_on_first_show() # Chiama il metodo che le sottoclassi implementeranno
        self._data_loaded = True

    def _load_data_on_first_show(self):
        """
        Metodo astratto. Le sottoclassi DEVONO sovrascrivere questo metodo
        per implementare la loro logica di caricamento dati.
        """
        # self.logger.warning(f"Metodo _load_data_on_first_show non implementato per {self.__class__.__name__}")
        # Usiamo pass per non mostrare avvisi per widget che potrebbero non averne bisogno
        pass
        