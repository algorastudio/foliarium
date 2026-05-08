"""
foliarium/ui/splash.py — Splash screen mostrata all'avvio.
"""
from __future__ import annotations

import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPainter, QPixmap, QPen, QColor
from PyQt6.QtWidgets import QSplashScreen

from app_paths import get_resource_path
from config import APP_VERSION


def _build_foliarium_splash_pixmap() -> QPixmap:
    """Genera il pixmap di fallback se il PNG non esiste."""
    from PyQt6.QtCore import QRect

    W, H = 700, 394
    pixmap = QPixmap(W, H)
    pixmap.fill(QColor("#f5f0e8"))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    pen = QPen(QColor("#b8960c"), 4)
    painter.setPen(pen)
    painter.drawRect(8, 8, W - 16, H - 16)
    painter.drawLine(40, H // 2 + 30, W - 40, H // 2 + 30)

    font_title = QFont("Georgia", 64, QFont.Weight.Bold)
    painter.setFont(font_title)
    painter.setPen(QColor("#1a3c2b"))
    painter.drawText(QRect(0, 50, W, 140), Qt.AlignmentFlag.AlignCenter, "FOLIARIUM")

    font_sub = QFont("Georgia", 16)
    painter.setFont(font_sub)
    painter.drawText(QRect(0, 210, W, 40), Qt.AlignmentFlag.AlignCenter, "GESTIONE DIGITALE")
    painter.drawText(QRect(0, 245, W, 40), Qt.AlignmentFlag.AlignCenter, "ARCHIVI CATASTALI STORICI")

    font_ver = QFont("Georgia", 10)
    painter.setFont(font_ver)
    painter.setPen(QColor("#7a6a50"))
    painter.drawText(
        QRect(0, H - 45, W - 20, 30),
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
        f"v{APP_VERSION}",
    )

    painter.end()
    return pixmap


class FoliariumSplashScreen(QSplashScreen):
    """Splash screen mostrata all'avvio prima del login."""

    def __init__(self):
        logo_path = str(get_resource_path("Logo_foliarium.png"))
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path).scaled(
                700, 394,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        else:
            pixmap = _build_foliarium_splash_pixmap()
        super().__init__(pixmap)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
