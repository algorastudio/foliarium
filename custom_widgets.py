
import os,csv,sys,logging,json
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Tuple, TYPE_CHECKING

# Importazioni PyQt6
from PyQt6.QtCore import (QDate, QDateTime, QPoint, QProcess, QSettings,
                          QSize, QStandardPaths, Qt, QTimer, QUrl,
                          pyqtSignal, pyqtSlot)

from PyQt6.QtGui import (QCloseEvent, QColor, QDesktopServices, QFont,
                         QIcon, QPalette, QPixmap, QAction)

# QWebEngineView: opzionale, riservato a future funzionalità web
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    WEB_ENGINE_AVAILABLE = True
except ImportError:
    QWebEngineView = None
    WEB_ENGINE_AVAILABLE = False

from PyQt6.QtWidgets import (QAbstractItemView, QApplication,
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
# Importazione commentata (da abilitare se necessario)
# from PyQt6.QtSvgWidgets import QSvgWidget
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
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
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
        self.setEchoMode(QLineEdit.EchoMode.Password)
# In custom_widgets.py

import logging
from PyQt6.QtWidgets import QWidget

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
        

# ── StatCard ─────────────────────────────────────────────────────────────────

from PyQt6.QtWidgets import QFrame, QVBoxLayout
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QFontMetrics, QLinearGradient
from PyQt6.QtCore import Qt, QRect, QRectF

class StatCard(QFrame):
    """Stat card pittata con QPainter: bordo arrotondato, accent bar, ombra leggera."""

    def __init__(self, title: str, accent_color: str = "#3F51B5", parent=None):
        super().__init__(parent)
        self._title = title
        self._value = "—"
        self._accent = QColor(accent_color)
        self.setMinimumSize(120, 100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(108)

    def setValue(self, value):
        self._value = str(value)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()

        # Ombra leggera (offset sotto/destra)
        shadow_rect = QRectF(3, 4, w - 4, h - 4)
        painter.setBrush(QBrush(QColor(0, 0, 0, 18)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(shadow_rect, 10, 10)

        # Card background
        card_rect = QRectF(0, 0, w - 3, h - 3)
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.setPen(QPen(QColor(self._accent.red(), self._accent.green(),
                                   self._accent.blue(), 60), 1))
        painter.drawRoundedRect(card_rect, 10, 10)

        # Accent bar sinistra (4px)
        bar_rect = QRectF(0, 0, 5, h - 3)
        painter.setBrush(QBrush(self._accent))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(bar_rect, 5, 5)
        # Copertura angolo destro della bar
        painter.drawRect(QRectF(3, 0, 2, h - 3))

        # Titolo
        title_font = QFont("Segoe UI", 9)
        title_font.setWeight(QFont.Weight.Medium)
        painter.setFont(title_font)
        painter.setPen(QPen(QColor("#757575")))
        title_rect = QRect(18, 14, w - 22, 20)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         self._title.upper())

        # Valore
        value_font = QFont("Segoe UI", 22)
        value_font.setWeight(QFont.Weight.Bold)
        painter.setFont(value_font)
        painter.setPen(QPen(self._accent))
        value_rect = QRect(14, 36, w - 18, 50)
        painter.drawText(value_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         self._value)

        painter.end()
