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
    """Genera il pixmap di fallback con design moderno indigo."""
    from PyQt6.QtCore import QRect
    from PyQt6.QtGui import QLinearGradient, QBrush

    W, H = 700, 394
    pixmap = QPixmap(W, H)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    # Sfondo con gradient diagonale indigo
    gradient = QLinearGradient(0, 0, W, H)
    gradient.setColorAt(0.0, QColor("#1A237E"))
    gradient.setColorAt(0.5, QColor("#303F9F"))
    gradient.setColorAt(1.0, QColor("#3F51B5"))
    painter.setBrush(QBrush(gradient))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(0, 0, W, H, 16, 16)

    # Bordo sottile interno
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
    painter.drawRoundedRect(8, 8, W - 16, H - 16, 12, 12)

    # Linea decorativa orizzontale
    painter.setPen(QPen(QColor(197, 202, 233, 80), 1))
    painter.drawLine(W // 2 - 80, H // 2 + 36, W // 2 + 80, H // 2 + 36)

    # Titolo
    font_title = QFont("Segoe UI", 56, QFont.Weight.Bold)
    font_title.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3)
    painter.setFont(font_title)
    painter.setPen(QColor("#FFFFFF"))
    painter.drawText(QRect(0, 90, W, 100), Qt.AlignmentFlag.AlignCenter, "FOLIARIUM")

    # Subtitle 1
    font_sub = QFont("Segoe UI", 13, QFont.Weight.Medium)
    font_sub.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
    painter.setFont(font_sub)
    painter.setPen(QColor("#C5CAE9"))
    painter.drawText(QRect(0, 200, W, 30), Qt.AlignmentFlag.AlignCenter,
                     "ARCHIVIO CATASTALE STORICO")

    # Subtitle 2 (sotto la linea)
    font_sub2 = QFont("Segoe UI", 10)
    font_sub2.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.5)
    painter.setFont(font_sub2)
    painter.setPen(QColor("#9FA8DA"))
    painter.drawText(QRect(0, 250, W, 24), Qt.AlignmentFlag.AlignCenter,
                     "GESTIONE DIGITALE PER ARCHIVISTI")

    # Studio attribution + versione
    font_studio = QFont("Segoe UI", 9, QFont.Weight.DemiBold)
    painter.setFont(font_studio)
    painter.setPen(QColor("#E8EAF6"))
    painter.drawText(QRect(20, H - 38, W - 40, 20),
                     Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
                     "ALGORA STUDIO")

    font_ver = QFont("Segoe UI", 9)
    painter.setFont(font_ver)
    painter.setPen(QColor("#9FA8DA"))
    painter.drawText(QRect(20, H - 38, W - 40, 20),
                     Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
                     f"v{APP_VERSION}")

    painter.end()
    return pixmap


class FoliariumSplashScreen(QSplashScreen):
    """Splash screen mostrata all'avvio prima del login."""

    def __init__(self):
        logo_path = str(get_resource_path("Logo_foliarium1.png"))
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
