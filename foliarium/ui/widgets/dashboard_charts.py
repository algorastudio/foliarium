"""
foliarium/ui/widgets/dashboard_charts.py — Grafici matplotlib per la dashboard.

Mostra 4 grafici aggregati:
  - distribuzione partite per epoca storica (bar)
  - distribuzione per tipo (donut)
  - distribuzione per stato (donut)
  - top 10 comuni per numero di partite (horizontal bar)

Carica i dati in background tramite `_DashboardChartsLoader` e si
ridisegna quando arrivano. I colori dei testi sono presi dalla palette
Qt corrente per adattarsi automaticamente al tema chiaro/scuro.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# Matplotlib è opzionale: se manca, il widget si degrada con un avviso.
try:
    import matplotlib  # noqa: F401
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    _MATPLOTLIB_AVAILABLE = True
except Exception:
    FigureCanvas = None  # type: ignore[assignment]
    Figure = None  # type: ignore[assignment]
    _MATPLOTLIB_AVAILABLE = False

if TYPE_CHECKING:
    from catasto_db_manager import CatastoDBManager  # noqa: F401


logger = logging.getLogger("CatastoGUI.dashboard_charts")


# Palette colori "epoca-friendly": coordinata con i colori storici
# (Sardegna blu, Italia verde, Repubblica rosso) ma desaturata per
# non stridere con il tema dell'app.
_PALETTE = [
    "#3F51B5",  # blu indaco
    "#00897B",  # teal
    "#C62828",  # rosso
    "#F57C00",  # arancio
    "#7E57C2",  # viola
    "#5D4037",  # marrone
    "#558B2F",  # verde oliva
    "#0277BD",  # blu chiaro
    "#AD1457",  # magenta
    "#455A64",  # blu-grigio
]


class _DashboardChartsLoader(QThread):
    """Carica i dati per i grafici in background (non blocca la UI)."""
    data_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, db_manager: 'CatastoDBManager', parent=None):
        super().__init__(parent)
        self._db = db_manager

    def run(self):
        try:
            data = self._db.get_dashboard_charts_data() or {}
            self.data_ready.emit(data)
        except Exception as e:
            self.error_occurred.emit(str(e))


class DashboardChartsWidget(QGroupBox):
    """Container 2x2 di grafici per la dashboard."""

    def __init__(self, db_manager: 'CatastoDBManager', parent=None):
        super().__init__("Grafici e Statistiche", parent)
        self.db_manager = db_manager
        self._loader: Optional[_DashboardChartsLoader] = None
        self._last_data: Dict[str, Any] = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        if not _MATPLOTLIB_AVAILABLE:
            warning = QLabel(
                "matplotlib non disponibile: i grafici della dashboard non "
                "sono visualizzati. Installa la libreria con "
                "<code>pip install matplotlib</code>.")
            warning.setWordWrap(True)
            warning.setTextFormat(Qt.TextFormat.RichText)
            layout.addWidget(warning)
            self._grid = None
            return

        grid_host = QWidget()
        grid = QGridLayout(grid_host)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(12)

        self._fig_epoca = self._make_canvas()
        self._fig_tipo = self._make_canvas()
        self._fig_stato = self._make_canvas()
        self._fig_top = self._make_canvas()

        grid.addWidget(self._fig_epoca, 0, 0)
        grid.addWidget(self._fig_tipo, 0, 1)
        grid.addWidget(self._fig_top, 1, 0)
        grid.addWidget(self._fig_stato, 1, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)

        layout.addWidget(grid_host, 1)
        self._grid = grid

    def _make_canvas(self) -> 'FigureCanvas':
        fig = Figure(figsize=(4, 3), tight_layout=True)
        fig.patch.set_alpha(0.0)
        canvas = FigureCanvas(fig)
        canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        canvas.setMinimumHeight(180)
        return canvas

    # ── Public API ─────────────────────────────────────────────────────

    def load_data(self):
        """Avvia il caricamento asincrono dei dati e ridisegna i grafici."""
        if not _MATPLOTLIB_AVAILABLE:
            return
        if self._loader is not None and self._loader.isRunning():
            return
        self._loader = _DashboardChartsLoader(self.db_manager, self)
        self._loader.data_ready.connect(self._on_data_ready)
        self._loader.error_occurred.connect(
            lambda msg: logger.warning("Errore caricamento grafici: %s", msg))
        self._loader.start()

    def _on_data_ready(self, data: Dict[str, Any]):
        self._last_data = data
        self._render_all(data)

    # ── Rendering ──────────────────────────────────────────────────────

    def _text_color(self) -> str:
        """Colore testo coordinato con il tema corrente (chiaro/scuro)."""
        col = self.palette().color(QPalette.ColorRole.WindowText)
        return col.name()

    def _render_all(self, data: Dict[str, Any]):
        if not _MATPLOTLIB_AVAILABLE:
            return
        self._render_bar(
            self._fig_epoca, data.get("per_epoca") or [],
            title="Partite per epoca storica",
            color_idx_offset=0,
        )
        self._render_donut(
            self._fig_tipo, data.get("per_tipo") or [],
            title="Partite per tipo",
        )
        self._render_donut(
            self._fig_stato, data.get("per_stato") or [],
            title="Partite per stato",
        )
        self._render_hbar(
            self._fig_top, data.get("top_comuni") or [],
            title="Top 10 comuni per partite",
        )

    def _style_axes(self, ax, title: str):
        col = self._text_color()
        ax.set_title(title, fontsize=10, color=col, pad=8)
        for spine in ax.spines.values():
            spine.set_color(col)
            spine.set_alpha(0.2)
        ax.tick_params(colors=col, labelsize=8)
        ax.set_facecolor("none")

    def _render_empty(self, canvas: 'FigureCanvas', title: str):
        fig = canvas.figure
        fig.clear()
        ax = fig.add_subplot(111)
        ax.set_facecolor("none")
        col = self._text_color()
        ax.text(0.5, 0.5, "Nessun dato disponibile",
                ha="center", va="center", color=col, fontsize=9, alpha=0.6,
                transform=ax.transAxes)
        ax.set_title(title, fontsize=10, color=col, pad=8)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        canvas.draw_idle()

    def _render_bar(self, canvas: 'FigureCanvas', series: List[Dict[str, Any]],
                    title: str, color_idx_offset: int = 0):
        if not series:
            self._render_empty(canvas, title)
            return
        fig = canvas.figure
        fig.clear()
        ax = fig.add_subplot(111)
        labels = [s["label"] for s in series]
        values = [s["value"] for s in series]
        colors = [_PALETTE[(i + color_idx_offset) % len(_PALETTE)]
                  for i in range(len(values))]
        bars = ax.bar(range(len(values)), values, color=colors)
        ax.set_xticks(range(len(values)))
        ax.set_xticklabels(labels, rotation=15, ha="right", fontsize=8)
        for bar, value in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height(),
                    str(value), ha="center", va="bottom",
                    fontsize=8, color=self._text_color())
        self._style_axes(ax, title)
        canvas.draw_idle()

    def _render_hbar(self, canvas: 'FigureCanvas', series: List[Dict[str, Any]],
                     title: str):
        if not series:
            self._render_empty(canvas, title)
            return
        fig = canvas.figure
        fig.clear()
        ax = fig.add_subplot(111)
        # Ordine crescente nel grafico (i top in cima)
        series_sorted = list(reversed(series))
        labels = [s["label"] for s in series_sorted]
        values = [s["value"] for s in series_sorted]
        colors = [_PALETTE[i % len(_PALETTE)] for i in range(len(values))]
        bars = ax.barh(range(len(values)), values, color=colors)
        ax.set_yticks(range(len(values)))
        ax.set_yticklabels(labels, fontsize=8)
        for bar, value in zip(bars, values):
            ax.text(bar.get_width(), bar.get_y() + bar.get_height() / 2,
                    f" {value}", va="center", ha="left",
                    fontsize=8, color=self._text_color())
        self._style_axes(ax, title)
        canvas.draw_idle()

    def _render_donut(self, canvas: 'FigureCanvas', series: List[Dict[str, Any]],
                      title: str):
        if not series:
            self._render_empty(canvas, title)
            return
        fig = canvas.figure
        fig.clear()
        ax = fig.add_subplot(111)
        labels = [s["label"] for s in series]
        values = [s["value"] for s in series]
        total = sum(values) or 1
        colors = [_PALETTE[i % len(_PALETTE)] for i in range(len(values))]
        wedges, _texts = ax.pie(
            values, colors=colors, startangle=90,
            wedgeprops=dict(width=0.4, edgecolor="none"),
        )
        ax.set_aspect("equal")
        # Legenda con percentuali a fianco
        legend_labels = [
            f"{lbl} — {val} ({val / total * 100:.0f}%)"
            for lbl, val in zip(labels, values)
        ]
        ax.legend(wedges, legend_labels, loc="center left",
                  bbox_to_anchor=(1.0, 0.5), fontsize=8, frameon=False,
                  labelcolor=self._text_color())
        col = self._text_color()
        ax.set_title(title, fontsize=10, color=col, pad=8)
        canvas.draw_idle()


__all__ = [
    "DashboardChartsWidget",
    "_DashboardChartsLoader",
]
