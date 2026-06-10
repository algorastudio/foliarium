"""
foliarium.ui.effects — Effetti grafici riutilizzabili.

QSS non supporta ombre (box-shadow). Per ottenere quel look "card"
moderno usiamo QGraphicsDropShadowEffect, applicato programmaticamente.
"""
from __future__ import annotations

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QWidget


def apply_card_shadow(
    widget: QWidget,
    blur: int = 24,
    y_offset: int = 4,
    color: str = "#1A237E",
    alpha: int = 28,
) -> QGraphicsDropShadowEffect:
    """Applica un'ombra morbida sotto un widget (look "card").

    blur: raggio di sfocatura in px.
    y_offset: spostamento verticale (px positivi = ombra sotto).
    color: colore base dell'ombra in hex.
    alpha: 0-255, opacità.
    """
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setOffset(0, y_offset)
    qcolor = QColor(color)
    qcolor.setAlpha(alpha)
    shadow.setColor(qcolor)
    widget.setGraphicsEffect(shadow)
    return shadow


def apply_soft_shadow(widget: QWidget) -> QGraphicsDropShadowEffect:
    """Ombra ancora più sottile per elementi piccoli (chip, badge)."""
    return apply_card_shadow(widget, blur=12, y_offset=2, alpha=20)


def apply_elevated_shadow(widget: QWidget) -> QGraphicsDropShadowEffect:
    """Ombra più marcata per dialog modali o popup."""
    return apply_card_shadow(widget, blur=40, y_offset=8, alpha=50)
