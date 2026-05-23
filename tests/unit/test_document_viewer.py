"""
tests/unit/test_document_viewer.py
==================================
Smoke test del DocumentViewerWidget: instanziazione, placeholder,
caricamento immagine, gestione file mancanti e tipi non supportati.

Marker: gui (richiede QApplication, eseguito con QT_QPA_PLATFORM=offscreen).
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault(
    "FOLIARIUM_LICENSE_KEY",
    "deadbeefcafebabe0123456789abcdef0123456789abcdef0123456789abcdef",
)

pytestmark = [pytest.mark.unit, pytest.mark.gui]


@pytest.fixture(scope="module")
def qapp():
    from PyQt6.QtWidgets import QApplication
    import sys
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def sample_png(tmp_path):
    """Crea un piccolo PNG su disco per i test."""
    from PyQt6.QtGui import QImage, QColor
    p = tmp_path / "sample.png"
    img = QImage(60, 40, QImage.Format.Format_RGB32)
    img.fill(QColor("steelblue"))
    img.save(str(p), "PNG")
    assert p.exists()
    return str(p)


def test_kind_detection():
    from foliarium.ui.widgets.document_viewer import _kind_of
    assert _kind_of("foo.pdf") == "pdf"
    assert _kind_of("foo.PDF") == "pdf"
    assert _kind_of("a/b/c.jpg") == "image"
    assert _kind_of("img.png") == "image"
    assert _kind_of("doc.tiff") == "image"
    assert _kind_of("data.csv") == "unknown"
    assert _kind_of("noext") == "unknown"


def test_widget_constructs_with_placeholder(qapp):
    from foliarium.ui.widgets.document_viewer import DocumentViewerWidget
    w = DocumentViewerWidget()
    assert w._stack.currentWidget() is w._placeholder
    assert "Nessun documento" in w._placeholder.text()
    w.deleteLater()


def test_load_missing_file_shows_placeholder(qapp):
    from foliarium.ui.widgets.document_viewer import DocumentViewerWidget
    w = DocumentViewerWidget()
    ok = w.load_document("/tmp/__nonexistent__/path.png", title="X")
    assert ok is False
    assert w._stack.currentWidget() is w._placeholder
    assert "File non trovato" in w._placeholder.text()
    w.deleteLater()


def test_load_image_switches_to_image_view(qapp, sample_png):
    from foliarium.ui.widgets.document_viewer import DocumentViewerWidget
    w = DocumentViewerWidget()
    ok = w.load_document(sample_png, title="Test image")
    assert ok is True
    assert w._stack.currentWidget() is w._image_view
    # Titolo aggiornato
    assert "Test image" in w._lbl_title.text()
    # Toolbar abilitata
    assert w._btn_zoom_in.isEnabled()
    assert w._btn_fit.isEnabled()
    assert w._btn_rotate.isEnabled()
    w.deleteLater()


def test_load_unsupported_type_falls_back(qapp, tmp_path):
    from foliarium.ui.widgets.document_viewer import DocumentViewerWidget
    p = tmp_path / "data.csv"
    p.write_text("a,b,c\n1,2,3\n")
    w = DocumentViewerWidget()
    ok = w.load_document(str(p))
    assert ok is False
    assert w._stack.currentWidget() is w._placeholder
    assert "non supportato" in w._placeholder.text()
    # "Apri esternamente" deve restare abilitato per file non supportati
    assert w._btn_open_ext.isEnabled()
    w.deleteLater()


def test_load_none_clears_viewer(qapp, sample_png):
    from foliarium.ui.widgets.document_viewer import DocumentViewerWidget
    w = DocumentViewerWidget()
    w.load_document(sample_png)
    assert w._stack.currentWidget() is w._image_view
    ok = w.load_document(None)
    assert ok is False
    assert w._stack.currentWidget() is w._placeholder
    w.deleteLater()


def test_image_view_zoom_in_out(qapp, sample_png):
    from foliarium.ui.widgets.document_viewer import DocumentViewerWidget
    w = DocumentViewerWidget()
    w.load_document(sample_png)
    initial = w._image_view._zoom_level
    w._on_zoom_in()
    assert w._image_view._zoom_level == initial + 1
    w._on_zoom_out()
    assert w._image_view._zoom_level == initial
    w.deleteLater()


def test_image_view_rotate(qapp, sample_png):
    from foliarium.ui.widgets.document_viewer import DocumentViewerWidget
    w = DocumentViewerWidget()
    w.load_document(sample_png)
    assert w._image_view._rotation == 0
    w._on_rotate()
    assert w._image_view._rotation == 90
    w._on_rotate()
    assert w._image_view._rotation == 180
    w.deleteLater()


def test_resolve_path_absolute_existing(qapp, sample_png):
    from foliarium.ui.widgets.document_viewer import DocumentViewerWidget
    w = DocumentViewerWidget()
    resolved = w._resolve_path(sample_png)
    assert resolved is not None
    assert Path(resolved).exists()
    w.deleteLater()


def test_resolve_path_missing_returns_none(qapp):
    from foliarium.ui.widgets.document_viewer import DocumentViewerWidget
    w = DocumentViewerWidget()
    assert w._resolve_path("/tmp/__definitely_does_not_exist__.png") is None
    w.deleteLater()
