"""
foliarium/ui/widgets/document_viewer.py — Visualizzatore documenti nativo.

Mostra direttamente nella GUI le scansioni dei registri storici (PDF e
immagini) senza dover aprire programmi esterni. Supporta zoom, pan e —
per i PDF — navigazione delle pagine.

- Immagini (PNG, JPG, BMP, ...): QGraphicsView + QPixmap
- PDF: QPdfView + QPdfDocument (bundled con PyQt6 >= 6.4)
- File non supportati / mancanti: messaggio + opzione "Apri esternamente"
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import (
    QDesktopServices, QImageReader, QPainter, QPixmap,
)
from PyQt6.QtWidgets import (
    QGraphicsPixmapItem, QGraphicsScene, QGraphicsView, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)

try:
    from PyQt6.QtPdf import QPdfDocument
    from PyQt6.QtPdfWidgets import QPdfView
    _PDF_AVAILABLE = True
except Exception:
    QPdfDocument = None  # type: ignore[assignment]
    QPdfView = None  # type: ignore[assignment]
    _PDF_AVAILABLE = False


logger = logging.getLogger("CatastoGUI.document_viewer")


_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".tif", ".webp"}
_PDF_EXTS = {".pdf"}


def _kind_of(path: str) -> str:
    """Ritorna 'pdf', 'image', 'unknown' in base all'estensione."""
    ext = Path(path).suffix.lower()
    if ext in _PDF_EXTS:
        return "pdf"
    if ext in _IMAGE_EXTS:
        return "image"
    return "unknown"


# ── Image viewer ──────────────────────────────────────────────────────

class _ImageView(QGraphicsView):
    """QGraphicsView per immagini con zoom Ctrl+wheel e pan drag."""

    def __init__(self, parent=None):
        scene = QGraphicsScene(parent)
        super().__init__(scene, parent)
        self._scene = scene
        self._pix_item: Optional[QGraphicsPixmapItem] = None
        self._zoom_level = 0
        self._rotation = 0

        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setBackgroundBrush(Qt.GlobalColor.darkGray)

    def load_image(self, path: str) -> bool:
        # Usa QImageReader per gestire più formati e ridurre memoria su
        # immagini grandi tramite setScaledSize quando necessario.
        reader = QImageReader(path)
        reader.setAutoTransform(True)
        img = reader.read()
        if img.isNull():
            return False
        pix = QPixmap.fromImage(img)
        self._scene.clear()
        self._pix_item = self._scene.addPixmap(pix)
        self._scene.setSceneRect(pix.rect().toRectF())
        self._zoom_level = 0
        self._rotation = 0
        self.resetTransform()
        self.fit_to_view()
        return True

    def fit_to_view(self):
        if self._pix_item is None:
            return
        self.fitInView(self._pix_item, Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom_level = 0

    def fit_to_width(self):
        if self._pix_item is None:
            return
        rect = self._pix_item.boundingRect()
        if rect.isEmpty():
            return
        factor = self.viewport().width() / rect.width()
        self.resetTransform()
        if self._rotation:
            self.rotate(self._rotation)
        self.scale(factor, factor)
        self._zoom_level = 0

    def zoom_in(self):
        self._apply_zoom(1.2, +1)

    def zoom_out(self):
        self._apply_zoom(1 / 1.2, -1)

    def rotate_cw(self):
        self._rotation = (self._rotation + 90) % 360
        self.rotate(90)

    def _apply_zoom(self, factor: float, cap_change: int):
        new_level = self._zoom_level + cap_change
        if not (-10 <= new_level <= 10):
            return
        self._zoom_level = new_level
        self.scale(factor, factor)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            angle = event.angleDelta().y()
            if angle != 0:
                self._apply_zoom(1.2 if angle > 0 else 1 / 1.2,
                                 +1 if angle > 0 else -1)
                event.accept()
                return
        super().wheelEvent(event)


# ── Document viewer (entry point) ─────────────────────────────────────

class DocumentViewerWidget(QWidget):
    """Visualizzatore documenti: PDF o immagine. Cambia backend in base al file."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_path: Optional[str] = None
        self._pdf_doc = None  # type: ignore[var-annotated]
        self._build_ui()
        self.show_placeholder("Nessun documento selezionato.")

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        self._lbl_title = QLabel("")
        self._lbl_title.setStyleSheet("font-weight: bold;")
        self._lbl_title.setSizePolicy(QSizePolicy.Policy.Expanding,
                                     QSizePolicy.Policy.Fixed)
        toolbar.addWidget(self._lbl_title, 1)

        self._btn_zoom_in = self._mk_btn("＋", "Zoom in (Ctrl+rotellina)",
                                         self._on_zoom_in)
        self._btn_zoom_out = self._mk_btn("－", "Zoom out", self._on_zoom_out)
        self._btn_fit = self._mk_btn("⤢", "Adatta alla vista", self._on_fit)
        self._btn_fit_w = self._mk_btn("↔", "Adatta alla larghezza", self._on_fit_width)
        self._btn_rotate = self._mk_btn("⟳", "Ruota 90°", self._on_rotate)
        self._btn_open_ext = self._mk_btn("Apri esternamente",
                                          "Apri il documento con il programma di sistema",
                                          self._on_open_external)
        for b in (self._btn_zoom_in, self._btn_zoom_out, self._btn_fit,
                  self._btn_fit_w, self._btn_rotate, self._btn_open_ext):
            toolbar.addWidget(b)

        layout.addLayout(toolbar)

        # Stack: placeholder / image / pdf
        self._stack = QStackedWidget()
        layout.addWidget(self._stack, 1)

        # 0. placeholder
        self._placeholder = QLabel()
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color: palette(mid); padding: 32px;")
        self._placeholder.setWordWrap(True)
        self._stack.addWidget(self._placeholder)

        # 1. image view
        self._image_view = _ImageView()
        self._stack.addWidget(self._image_view)

        # 2. pdf view (solo se disponibile)
        if _PDF_AVAILABLE:
            self._pdf_view = QPdfView(self)
            self._pdf_view.setPageMode(QPdfView.PageMode.MultiPage)
            self._pdf_view.setZoomMode(QPdfView.ZoomMode.FitInView)
            self._stack.addWidget(self._pdf_view)
        else:
            self._pdf_view = None

        self._set_toolbar_enabled(False)

    def _mk_btn(self, text: str, tooltip: str, slot) -> QPushButton:
        btn = QPushButton(text)
        btn.setToolTip(tooltip)
        if len(text) <= 2:
            btn.setFixedWidth(34)
        btn.clicked.connect(slot)
        return btn

    def _set_toolbar_enabled(self, enabled: bool):
        for b in (self._btn_zoom_in, self._btn_zoom_out, self._btn_fit,
                  self._btn_fit_w, self._btn_rotate):
            b.setEnabled(enabled)
        self._btn_open_ext.setEnabled(enabled)

    # ── Public API ─────────────────────────────────────────────────

    def load_document(self, path: Optional[str], title: Optional[str] = None) -> bool:
        """Carica il documento dal path. Ritorna True su successo."""
        self._current_path = path
        if not path:
            self.show_placeholder("Nessun documento selezionato.")
            return False
        # Risolvi path
        abs_path = self._resolve_path(path)
        if abs_path is None:
            self.show_placeholder(
                f"File non trovato: <code>{path}</code>")
            return False

        self._lbl_title.setText(title or os.path.basename(abs_path))

        kind = _kind_of(abs_path)
        if kind == "image":
            ok = self._image_view.load_image(abs_path)
            if not ok:
                self.show_placeholder(
                    f"Impossibile leggere l'immagine: <code>{abs_path}</code>")
                return False
            self._stack.setCurrentWidget(self._image_view)
            self._set_toolbar_enabled(True)
            self._btn_rotate.setEnabled(True)
            return True

        if kind == "pdf":
            if not _PDF_AVAILABLE or self._pdf_view is None:
                self.show_placeholder(
                    "Il visualizzatore PDF non è disponibile in questa "
                    "installazione di PyQt6. Usa 'Apri esternamente'.")
                self._btn_open_ext.setEnabled(True)
                return False
            try:
                self._pdf_doc = QPdfDocument(self)
                self._pdf_doc.load(abs_path)
                self._pdf_view.setDocument(self._pdf_doc)
                self._stack.setCurrentWidget(self._pdf_view)
                self._set_toolbar_enabled(True)
                self._btn_rotate.setEnabled(False)  # non supportato su PDF
                return True
            except Exception as e:
                logger.error(f"Errore apertura PDF: {e}", exc_info=True)
                self.show_placeholder(f"Errore apertura PDF: {e}")
                return False

        self.show_placeholder(
            f"Tipo di file non supportato: <code>{Path(abs_path).suffix}</code>.<br>"
            f"Usa 'Apri esternamente' per visualizzarlo.")
        self._btn_open_ext.setEnabled(True)
        return False

    def show_placeholder(self, html: str):
        self._placeholder.setText(html)
        self._placeholder.setTextFormat(Qt.TextFormat.RichText)
        self._stack.setCurrentWidget(self._placeholder)
        self._set_toolbar_enabled(False)
        self._lbl_title.setText("")

    # ── Helpers ────────────────────────────────────────────────────

    def _resolve_path(self, path: str) -> Optional[str]:
        """Risolve un path eventualmente relativo a varie root note."""
        p = Path(path)
        if p.is_absolute() and p.exists():
            return str(p)
        # Tenta relativo a cwd
        if p.exists():
            return str(p.resolve())
        # Tenta relativo a BASE_DIR / EXE_DIR (path resource Foliarium)
        try:
            from app_paths import BASE_DIR, EXE_DIR
            for root in (EXE_DIR, BASE_DIR):
                candidate = Path(root) / path
                if candidate.exists():
                    return str(candidate.resolve())
        except Exception:
            pass
        return None

    # ── Toolbar handlers ───────────────────────────────────────────

    def _on_zoom_in(self):
        if self._stack.currentWidget() is self._image_view:
            self._image_view.zoom_in()
        elif self._pdf_view is not None and self._stack.currentWidget() is self._pdf_view:
            self._pdf_view.setZoomFactor(self._pdf_view.zoomFactor() * 1.2)

    def _on_zoom_out(self):
        if self._stack.currentWidget() is self._image_view:
            self._image_view.zoom_out()
        elif self._pdf_view is not None and self._stack.currentWidget() is self._pdf_view:
            self._pdf_view.setZoomFactor(self._pdf_view.zoomFactor() / 1.2)

    def _on_fit(self):
        if self._stack.currentWidget() is self._image_view:
            self._image_view.fit_to_view()
        elif self._pdf_view is not None and self._stack.currentWidget() is self._pdf_view:
            self._pdf_view.setZoomMode(QPdfView.ZoomMode.FitInView)

    def _on_fit_width(self):
        if self._stack.currentWidget() is self._image_view:
            self._image_view.fit_to_width()
        elif self._pdf_view is not None and self._stack.currentWidget() is self._pdf_view:
            self._pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)

    def _on_rotate(self):
        if self._stack.currentWidget() is self._image_view:
            self._image_view.rotate_cw()

    def _on_open_external(self):
        if not self._current_path:
            return
        abs_path = self._resolve_path(self._current_path)
        if not abs_path:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(abs_path))


__all__ = [
    "DocumentViewerWidget",
]
