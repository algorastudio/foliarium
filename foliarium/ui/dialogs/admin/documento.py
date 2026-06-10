"""Dialog visualizzatore documenti PDF."""
from __future__ import annotations

import logging
import os

from PyQt6.QtCore import (Qt)
from PyQt6.QtGui import (QPixmap)
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtWidgets import (QDialog,
                             QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout,
                             QWidget, QGraphicsScene, QGraphicsView)
from PyQt6.QtGui import QPainter
from app_paths import get_resource_path, get_resource_path as resource_path, get_doc_path  # noqa: F401
from catasto_exceptions import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError  # noqa: F401

try:
    import keyring
except ImportError:
    keyring = None

try:
    import markdown
except ImportError:
    markdown = None

try:
    import yaml
except ImportError:
    yaml = None


class DocumentViewerDialog(QDialog):
    def __init__(self, parent=None, file_path: str = None):
        super().__init__(parent)
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")
        self.file_path = file_path
        self.setWindowTitle("Visualizzatore Documento")
        self.setMinimumSize(800, 600)

        self._init_ui()
        self._load_document()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # Toolbar zoom PDF (visibile solo quando si carica un PDF)
        self.pdf_toolbar = QWidget()
        toolbar_layout = QHBoxLayout(self.pdf_toolbar)
        toolbar_layout.setContentsMargins(4, 4, 4, 4)
        self.btn_zoom_out = QPushButton("−")
        self.btn_zoom_out.setToolTip("Riduci zoom")
        self.zoom_label = QLabel("100%")
        self.zoom_label.setMinimumWidth(50)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setToolTip("Aumenta zoom")
        self.btn_fit = QPushButton("Adatta")
        self.btn_fit.setToolTip("Adatta alla larghezza della finestra")
        toolbar_layout.addWidget(self.btn_zoom_out)
        toolbar_layout.addWidget(self.zoom_label)
        toolbar_layout.addWidget(self.btn_zoom_in)
        toolbar_layout.addWidget(self.btn_fit)
        toolbar_layout.addStretch()
        self.pdf_toolbar.setVisible(False)

        self.viewer_widget = QWidget()
        self.viewer_layout = QVBoxLayout(self.viewer_widget)
        self.viewer_layout.setContentsMargins(0, 0, 0, 0)

        button_layout = QHBoxLayout()
        self.close_button = QPushButton("Chiudi")
        self.close_button.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        button_layout.addStretch()

        main_layout.addWidget(self.pdf_toolbar)
        main_layout.addWidget(self.viewer_widget)
        main_layout.addLayout(button_layout)

    def _load_document(self):
        if not self.file_path or not os.path.exists(self.file_path):
            QMessageBox.critical(self, "Errore", "File non trovato o percorso non valido.")
            self.logger.error(f"Tentativo di caricare documento non trovato o non valido: {self.file_path}")
            self.viewer_layout.addWidget(QLabel("Errore: File non trovato."))
            return

        file_extension = os.path.splitext(self.file_path)[1].lower()

        if file_extension == '.pdf':
            self._load_pdf()
        elif file_extension in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
            self._load_image()
        else:
            QMessageBox.warning(self, "Formato non supportato", f"Il formato '{file_extension}' non è supportato per la visualizzazione interna.")
            self.logger.warning(f"Formato documento non supportato per la visualizzazione interna: {self.file_path}")
            self.viewer_layout.addWidget(QLabel(f"Formato '{file_extension}' non supportato."))
            
    def _load_pdf(self):
        try:
            self.pdf_document = QPdfDocument(self)
            status = self.pdf_document.load(self.file_path)
            if status != QPdfDocument.Status.Ready:
                raise RuntimeError(f"Errore caricamento documento: {status.name}")

            self.pdf_view = QPdfView(self)
            self.pdf_view.setDocument(self.pdf_document)
            self.pdf_view.setPageMode(QPdfView.PageMode.MultiPage)
            self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitInView)
            self._pdf_zoom = 1.0
            self.viewer_layout.addWidget(self.pdf_view)

            # Attiva toolbar zoom
            self.pdf_toolbar.setVisible(True)
            self.btn_zoom_in.clicked.connect(self._pdf_zoom_in)
            self.btn_zoom_out.clicked.connect(self._pdf_zoom_out)
            self.btn_fit.clicked.connect(self._pdf_zoom_fit)
            self._update_zoom_label()

            self.logger.info(f"PDF caricato con QPdfDocument ({self.pdf_document.pageCount()} pagine): {self.file_path}")
        except Exception as e:
            self.logger.error(f"Errore durante il caricamento del PDF: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore PDF", f"Impossibile visualizzare il PDF.\n{e}")
            self.viewer_layout.addWidget(QLabel("Errore nel caricamento del PDF."))

    def _pdf_zoom_in(self):
        self._pdf_zoom = min(self._pdf_zoom * 1.25, 5.0)
        self.pdf_view.setZoomMode(QPdfView.ZoomMode.Custom)
        self.pdf_view.setZoomFactor(self._pdf_zoom)
        self._update_zoom_label()

    def _pdf_zoom_out(self):
        self._pdf_zoom = max(self._pdf_zoom / 1.25, 0.1)
        self.pdf_view.setZoomMode(QPdfView.ZoomMode.Custom)
        self.pdf_view.setZoomFactor(self._pdf_zoom)
        self._update_zoom_label()

    def _pdf_zoom_fit(self):
        self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitInView)
        self._pdf_zoom = self.pdf_view.zoomFactor()
        self._update_zoom_label()

    def _update_zoom_label(self):
        self.zoom_label.setText(f"{int(self._pdf_zoom * 100)}%")
            
    def _load_image(self):
        try:
            self.graphics_scene = QGraphicsScene(self)
            self.graphics_view = QGraphicsView(self.graphics_scene, self)
            self.graphics_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            self.graphics_view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            self.graphics_view.setCacheMode(QGraphicsView.CacheModeFlag.CacheBackground)
            self.graphics_view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate)
            self.graphics_view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

            pixmap = QPixmap(str(self.file_path))
            if pixmap.isNull():
                raise ValueError(f"Impossibile caricare immagine da: {self.file_path}")

            self.pixmap_item = self.graphics_scene.addPixmap(pixmap)
            self.graphics_view.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
            self.graphics_view.setAlignment(Qt.AlignmentFlag.AlignCenter)

            self.zoom_factor = 1.0
            self.graphics_view.wheelEvent = self._image_wheel_event

            self.viewer_layout.addWidget(self.graphics_view)
            self.logger.info(f"Immagine caricata in QGraphicsView: {self.file_path}")

        except Exception as e:
            self.logger.error(f"Errore durante il caricamento dell'immagine in QGraphicsView: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Immagine", f"Impossibile visualizzare l'immagine. Errore: {e}")
            self.viewer_layout.addWidget(QLabel("Errore nel caricamento dell'immagine."))

    def _image_wheel_event(self, event):
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        
        if event.angleDelta().y() > 0:
            self.zoom_factor *= zoom_in_factor
        else:
            self.zoom_factor *= zoom_out_factor

        self.zoom_factor = max(0.1, min(self.zoom_factor, 10.0))

        transform = self.graphics_view.transform()
        transform.reset()
        transform.scale(self.zoom_factor, self.zoom_factor)
        self.graphics_view.setTransform(transform)

        event.accept()

# *** FINE: Classe DocumentViewerDialog ***

# --- Dialog per la Selezione dei Possessori ---




