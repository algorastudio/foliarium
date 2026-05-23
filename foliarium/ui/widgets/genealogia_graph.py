"""
foliarium/ui/widgets/genealogia_graph.py — Grafo genealogico interattivo.

Sostituisce la timeline lineare (GenealogiaTimelineWidget) con un vero
grafo a nodi su QGraphicsView/Scene:

- nodi = partite (rounded rect con numero, comune, stato)
- archi = variazioni (curve di Bézier con etichetta tipo + arrow)
- layout DAG layered: predecessori sopra, successori sotto la partita
  centrale (livelli negativi/positivi)
- interazioni: zoom (Ctrl+wheel), pan (drag), click per espandere
  predecessori/successori, double-click per navigare, fit-to-view

Espone la stessa API del vecchio widget (load_partita + segnale
navigate_to_partita) per consentire il drop-in replacement.
"""

from __future__ import annotations

import logging
import math
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Set, Tuple, TYPE_CHECKING

from PyQt6.QtCore import (
    QPointF, QRectF, Qt, pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush, QColor, QPainter, QPainterPath, QPen, QPolygonF, QFont,
)
from PyQt6.QtWidgets import (
    QFrame, QGraphicsItem, QGraphicsPathItem, QGraphicsRectItem,
    QGraphicsScene, QGraphicsSimpleTextItem, QGraphicsView, QHBoxLayout,
    QLabel, QMenu, QPushButton, QVBoxLayout, QWidget,
)

if TYPE_CHECKING:
    from catasto_db_manager import CatastoDBManager  # noqa: F401


logger = logging.getLogger("CatastoGUI.genealogia_graph")


# ── Stile ─────────────────────────────────────────────────────────────

NODE_WIDTH = 200
NODE_HEIGHT = 84
H_SPACING = 60     # spazio orizzontale tra nodi nello stesso livello
V_SPACING = 70     # spazio verticale tra livelli

# Colori per stato
_COLOR_CENTRAL_BG = QColor("#E3F2FD")
_COLOR_CENTRAL_BORDER = QColor("#1976D2")
_COLOR_DEFAULT_BG = QColor("#FFFFFF")
_COLOR_DEFAULT_BORDER = QColor("#90A4AE")
_COLOR_INATTIVA_BORDER = QColor("#C62828")

# Colori per tipo variazione (riusa la palette della timeline)
_TIPO_EDGE_COLORS: Dict[str, QColor] = {
    "frazionamento": QColor("#F57C00"),
    "vendita":       QColor("#3F51B5"),
    "successione":   QColor("#2E7D32"),
    "donazione":     QColor("#7E57C2"),
    "permuta":       QColor("#00897B"),
    "divisione":     QColor("#C62828"),
    "rettifica":     QColor("#5D4037"),
    "voltura":       QColor("#0277BD"),
}
_DEFAULT_EDGE_COLOR = QColor("#607D8B")


def _color_for_tipo(tipo: Optional[str]) -> QColor:
    if not tipo:
        return _DEFAULT_EDGE_COLOR
    return _TIPO_EDGE_COLORS.get(tipo.strip().lower(), _DEFAULT_EDGE_COLOR)


def _format_date(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (date, datetime)):
        return value.strftime("%d/%m/%Y")
    return str(value)


# ── Items ─────────────────────────────────────────────────────────────

class _PartitaNodeItem(QGraphicsRectItem):
    """Nodo grafico che rappresenta una partita."""

    def __init__(self, partita_data: Dict[str, Any], is_central: bool = False):
        super().__init__(0, 0, NODE_WIDTH, NODE_HEIGHT)
        self.partita_data = partita_data
        self.partita_id: Optional[int] = partita_data.get("id")
        self.is_central = is_central
        self.is_expanded = False  # se predecessori/successori già caricati

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setZValue(1)

        self._apply_style()
        self._build_text()

    def _apply_style(self):
        stato = (self.partita_data.get("stato") or "").lower()
        if self.is_central:
            bg = _COLOR_CENTRAL_BG
            border = _COLOR_CENTRAL_BORDER
            border_width = 2.5
        else:
            bg = _COLOR_DEFAULT_BG
            border = (_COLOR_INATTIVA_BORDER if stato == "inattiva"
                      else _COLOR_DEFAULT_BORDER)
            border_width = 1.5
        pen = QPen(border, border_width)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        self.setPen(pen)
        self.setBrush(QBrush(bg))

    def _build_text(self):
        numero = self.partita_data.get("numero_partita") or "?"
        suffisso = self.partita_data.get("suffisso_partita") or ""
        suf_disp = f" {suffisso}" if suffisso else ""
        title = f"Partita {numero}{suf_disp}"

        comune = self.partita_data.get("comune_nome") or ""
        stato = (self.partita_data.get("stato") or "").upper() or "—"
        data_imp = _format_date(self.partita_data.get("data_impianto"))
        possessori = (self.partita_data.get("possessori") or "—")
        # tronca possessori lunghi
        if isinstance(possessori, str) and len(possessori) > 40:
            possessori = possessori[:37] + "…"

        # Titolo
        t1 = QGraphicsSimpleTextItem(title, parent=self)
        f = QFont()
        f.setBold(True)
        f.setPointSize(10)
        t1.setFont(f)
        t1.setPos(10, 6)

        # Comune
        t2 = QGraphicsSimpleTextItem(comune, parent=self)
        f2 = QFont()
        f2.setPointSize(9)
        t2.setFont(f2)
        t2.setBrush(QBrush(QColor("#37474F")))
        t2.setPos(10, 24)

        # Possessori
        t3 = QGraphicsSimpleTextItem(possessori, parent=self)
        f3 = QFont()
        f3.setPointSize(8)
        t3.setFont(f3)
        t3.setBrush(QBrush(QColor("#546E7A")))
        t3.setPos(10, 40)

        # Footer: stato + data impianto
        footer = f"{stato}"
        if data_imp:
            footer += f"  ·  Imp. {data_imp}"
        t4 = QGraphicsSimpleTextItem(footer, parent=self)
        f4 = QFont()
        f4.setPointSize(8)
        f4.setBold(True)
        t4.setFont(f4)
        color_stato = (QColor("#C62828") if stato == "INATTIVA"
                       else QColor("#2E7D32"))
        t4.setBrush(QBrush(color_stato))
        t4.setPos(10, NODE_HEIGHT - 18)

    # ── Centro del top/bottom edge (per gli archi) ─────────────────
    def top_anchor(self) -> QPointF:
        return self.scenePos() + QPointF(NODE_WIDTH / 2, 0)

    def bottom_anchor(self) -> QPointF:
        return self.scenePos() + QPointF(NODE_WIDTH / 2, NODE_HEIGHT)

    # ── Hover effect ───────────────────────────────────────────────
    def hoverEnterEvent(self, event):
        pen = self.pen()
        pen.setWidthF(pen.widthF() + 1.0)
        self.setPen(pen)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._apply_style()
        super().hoverLeaveEvent(event)


class _EdgeItem(QGraphicsPathItem):
    """Arco direzionale tra due nodi con etichetta tipo variazione."""

    def __init__(self, source: _PartitaNodeItem, target: _PartitaNodeItem,
                 variazione: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.source = source
        self.target = target
        self.variazione = variazione or {}
        self.setZValue(0)

        tipo = self.variazione.get("tipo_variazione") or self.variazione.get("tipo")
        color = _color_for_tipo(tipo)
        pen = QPen(color, 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        self.setPen(pen)
        self.setBrush(Qt.GlobalColor.transparent)

        self._label: Optional[QGraphicsSimpleTextItem] = None
        self._arrow: Optional[QGraphicsPathItem] = None
        self._build_label_and_arrow(color, tipo)
        self.update_path()

    def _build_label_and_arrow(self, color: QColor, tipo: Optional[str]):
        if tipo:
            label_text = tipo.upper()
            data_v = _format_date(self.variazione.get("data_variazione"))
            if data_v:
                label_text += f" · {data_v}"
            self._label = QGraphicsSimpleTextItem(label_text)
            f = QFont()
            f.setPointSize(8)
            f.setBold(True)
            self._label.setFont(f)
            self._label.setBrush(QBrush(color))
            self._label.setZValue(2)
        self._arrow = QGraphicsPathItem()
        self._arrow.setBrush(QBrush(color))
        self._arrow.setPen(QPen(color, 0))
        self._arrow.setZValue(0.5)

    def items_to_add(self) -> List[QGraphicsItem]:
        out: List[QGraphicsItem] = []
        if self._arrow is not None:
            out.append(self._arrow)
        if self._label is not None:
            out.append(self._label)
        return out

    def update_path(self):
        """Ricalcola il percorso Bézier source.bottom → target.top."""
        p_src = self.source.bottom_anchor()
        p_dst = self.target.top_anchor()

        path = QPainterPath(p_src)
        # Curva morbida con due control points sull'asse y
        dy = p_dst.y() - p_src.y()
        c1 = QPointF(p_src.x(), p_src.y() + dy * 0.45)
        c2 = QPointF(p_dst.x(), p_dst.y() - dy * 0.45)
        path.cubicTo(c1, c2, p_dst)
        self.setPath(path)

        # Arrowhead alla fine
        if self._arrow is not None:
            arrow_path = QPainterPath()
            # Direzione tangente: approssima con (p_dst - c2)
            dx = p_dst.x() - c2.x()
            dyv = p_dst.y() - c2.y()
            ang = math.atan2(dyv, dx)
            tip = p_dst
            size = 8
            left = QPointF(
                tip.x() - size * math.cos(ang - math.pi / 7),
                tip.y() - size * math.sin(ang - math.pi / 7),
            )
            right = QPointF(
                tip.x() - size * math.cos(ang + math.pi / 7),
                tip.y() - size * math.sin(ang + math.pi / 7),
            )
            poly = QPolygonF([tip, left, right])
            arrow_path.addPolygon(poly)
            arrow_path.closeSubpath()
            self._arrow.setPath(arrow_path)

        # Etichetta vicino al midpoint
        if self._label is not None:
            t = 0.5
            mid_x = (
                (1 - t) ** 3 * p_src.x()
                + 3 * (1 - t) ** 2 * t * c1.x()
                + 3 * (1 - t) * t ** 2 * c2.x()
                + t ** 3 * p_dst.x()
            )
            mid_y = (
                (1 - t) ** 3 * p_src.y()
                + 3 * (1 - t) ** 2 * t * c1.y()
                + 3 * (1 - t) * t ** 2 * c2.y()
                + t ** 3 * p_dst.y()
            )
            br = self._label.boundingRect()
            self._label.setPos(mid_x - br.width() / 2,
                               mid_y - br.height() / 2)


# ── GraphicsView con zoom/pan ─────────────────────────────────────────

class _GraphView(QGraphicsView):
    """QGraphicsView con zoom Ctrl+wheel e pan con drag/scroll."""

    def __init__(self, scene: QGraphicsScene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
            | QPainter.RenderHint.TextAntialiasing
        )
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._zoom_level = 0
        self._zoom_min = -10
        self._zoom_max = 10

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            angle = event.angleDelta().y()
            if angle == 0:
                return
            self._apply_zoom(1.15 if angle > 0 else 1 / 1.15,
                             cap_change=1 if angle > 0 else -1)
            event.accept()
            return
        super().wheelEvent(event)

    def _apply_zoom(self, factor: float, cap_change: int = 0):
        new_level = self._zoom_level + cap_change
        if not (self._zoom_min <= new_level <= self._zoom_max):
            return
        self._zoom_level = new_level
        self.scale(factor, factor)

    def reset_zoom(self):
        self.resetTransform()
        self._zoom_level = 0


# ── Widget principale ─────────────────────────────────────────────────

class GenealogiaGraphWidget(QWidget):
    """Grafo genealogico interattivo.

    Drop-in replacement (stessa API) di GenealogiaTimelineWidget:
      - ``load_partita(partita_id)`` per impostare la partita centrale
      - ``navigate_to_partita = pyqtSignal(int)`` quando l'utente fa
        double-click su un nodo non centrale
    """

    navigate_to_partita = pyqtSignal(int)

    def __init__(self, db_manager: 'CatastoDBManager', parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db_manager
        self.current_partita_id: Optional[int] = None

        # Stato grafo
        self._nodes: Dict[int, _PartitaNodeItem] = {}
        self._edges: List[_EdgeItem] = []
        self._layers: Dict[int, int] = {}  # partita_id → layer

        self._build_ui()

    # ── UI ─────────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Header / toolbar
        header_row = QHBoxLayout()
        self.header_label = QLabel("Nessuna partita selezionata.")
        self.header_label.setStyleSheet("font-weight: bold;")
        header_row.addWidget(self.header_label, 1)

        self._btn_zoom_in = QPushButton("＋")
        self._btn_zoom_in.setFixedWidth(34)
        self._btn_zoom_in.setToolTip("Zoom in (Ctrl+rotellina)")
        self._btn_zoom_in.clicked.connect(lambda: self._view._apply_zoom(1.2, +1))
        header_row.addWidget(self._btn_zoom_in)

        self._btn_zoom_out = QPushButton("－")
        self._btn_zoom_out.setFixedWidth(34)
        self._btn_zoom_out.setToolTip("Zoom out")
        self._btn_zoom_out.clicked.connect(lambda: self._view._apply_zoom(1 / 1.2, -1))
        header_row.addWidget(self._btn_zoom_out)

        self._btn_fit = QPushButton("Adatta")
        self._btn_fit.setToolTip("Adatta tutto il grafo nella vista")
        self._btn_fit.clicked.connect(self.fit_to_view)
        header_row.addWidget(self._btn_fit)

        self._btn_expand_all = QPushButton("Espandi tutto")
        self._btn_expand_all.setToolTip(
            "Carica tutti i predecessori e successori transitivi (max 5 livelli)")
        self._btn_expand_all.clicked.connect(self.expand_all)
        header_row.addWidget(self._btn_expand_all)

        layout.addLayout(header_row)

        # Scene + View
        self._scene = QGraphicsScene(self)
        self._scene.setBackgroundBrush(QBrush(QColor("#FAFAFA")))
        self._view = _GraphView(self._scene, self)
        self._view.setFrameShape(QFrame.Shape.NoFrame)
        layout.addWidget(self._view, 1)

        # Doppio click → naviga; click destro → menu
        self._view.viewport().installEventFilter(self)

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.MouseButtonDblClick:
            scene_pos = self._view.mapToScene(event.pos())
            item = self._scene.itemAt(scene_pos, self._view.transform())
            node = self._resolve_node(item)
            if node and node.partita_id and not node.is_central:
                self.navigate_to_partita.emit(node.partita_id)
                return True
        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.RightButton:
                scene_pos = self._view.mapToScene(event.pos())
                item = self._scene.itemAt(scene_pos, self._view.transform())
                node = self._resolve_node(item)
                if node is not None:
                    self._show_node_menu(node, event.globalPosition().toPoint())
                    return True
            elif event.button() == Qt.MouseButton.LeftButton:
                scene_pos = self._view.mapToScene(event.pos())
                item = self._scene.itemAt(scene_pos, self._view.transform())
                node = self._resolve_node(item)
                if node is not None and not node.is_expanded:
                    self._expand_node(node)
                    # non return True: lascia anche il pan funzionare se l'utente trascina
        return super().eventFilter(obj, event)

    def _resolve_node(self, item) -> Optional[_PartitaNodeItem]:
        """Risale dalla gerarchia di sotto-text-items al _PartitaNodeItem."""
        while item is not None:
            if isinstance(item, _PartitaNodeItem):
                return item
            item = item.parentItem()
        return None

    def _show_node_menu(self, node: _PartitaNodeItem, global_pos):
        menu = QMenu(self)
        if not node.is_expanded:
            menu.addAction("Espandi nodo").triggered.connect(
                lambda: self._expand_node(node))
        if node.partita_id and not node.is_central:
            menu.addAction("Vai alla partita").triggered.connect(
                lambda: self.navigate_to_partita.emit(node.partita_id))
        menu.addAction("Centra nella vista").triggered.connect(
            lambda: self._view.centerOn(node))
        menu.exec(global_pos)

    # ── Public API ─────────────────────────────────────────────────

    def load_partita(self, partita_id: int):
        """Resetta il grafo e inizia da `partita_id` come nodo centrale."""
        self.current_partita_id = partita_id
        self._reset_graph()

        if partita_id is None:
            self.header_label.setText("Nessuna partita selezionata.")
            return

        try:
            genealogia = self.db.get_genealogia_partita(partita_id)
        except Exception as e:
            logger.error(f"Errore caricamento genealogia: {e}", exc_info=True)
            self.header_label.setText("Errore caricamento genealogia.")
            return

        if not genealogia or not genealogia.get("partita"):
            self.header_label.setText("Nessun dato genealogico trovato.")
            return

        central = genealogia["partita"]
        self._add_node(central, layer=0, is_central=True)
        self._integrate_genealogia(partita_id, genealogia, mark_expanded=True)

        n = central.get("numero_partita")
        self.header_label.setText(f"Genealogia della Partita {n}")
        self._relayout()
        self.fit_to_view()

    def fit_to_view(self):
        rect = self._scene.itemsBoundingRect()
        if rect.isEmpty():
            return
        # Padding intorno al rect
        rect.adjust(-40, -40, 40, 40)
        self._view.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
        self._view._zoom_level = 0

    def expand_all(self, max_depth: int = 5):
        """Espande BFS il grafo fino a profondità massima dalla partita corrente."""
        if self.current_partita_id is None:
            return
        # Frontier = nodi non ancora espansi
        for _ in range(max_depth):
            frontier = [n for n in self._nodes.values() if not n.is_expanded]
            if not frontier:
                break
            for node in frontier:
                if node.partita_id is None:
                    node.is_expanded = True
                    continue
                self._fetch_and_integrate(node)
        self._relayout()
        self.fit_to_view()

    # ── Internals ──────────────────────────────────────────────────

    def _reset_graph(self):
        self._scene.clear()
        self._nodes.clear()
        self._edges.clear()
        self._layers.clear()

    def _expand_node(self, node: _PartitaNodeItem):
        if node.is_expanded or node.partita_id is None:
            return
        self._fetch_and_integrate(node)
        self._relayout()

    def _fetch_and_integrate(self, node: _PartitaNodeItem):
        """Carica predecessori/successori del nodo e li integra nel grafo."""
        try:
            genealogia = self.db.get_genealogia_partita(node.partita_id)
        except Exception as e:
            logger.warning(f"Espansione nodo {node.partita_id} fallita: {e}")
            node.is_expanded = True
            return
        if not genealogia:
            node.is_expanded = True
            return
        self._integrate_genealogia(node.partita_id, genealogia,
                                   mark_expanded=True)

    def _integrate_genealogia(self, source_partita_id: int,
                              genealogia: Dict[str, Any],
                              mark_expanded: bool = False):
        source_node = self._nodes.get(source_partita_id)
        if source_node is None:
            # Caso anomalo: aggiungilo come centrale di fatto
            central = genealogia.get("partita") or {}
            source_node = self._add_node(central, layer=0, is_central=False)

        src_layer = self._layers.get(source_partita_id, 0)

        # Predecessori → layer = src_layer - 1
        for p in genealogia.get("predecessori") or []:
            pid = p.get("id")
            if pid is None:
                continue
            target_layer = src_layer - 1
            if pid not in self._nodes:
                self._add_node(p, layer=target_layer, is_central=False)
            else:
                # Aggiorna layer se trovata posizione più vicina al centro
                self._layers[pid] = min(self._layers[pid], target_layer)
            # Edge: predecessore → source
            self._add_edge(self._nodes[pid], source_node, variazione=p)

        # Successori → layer = src_layer + 1
        for s in genealogia.get("successori") or []:
            sid = s.get("id")
            if sid is None:
                continue
            target_layer = src_layer + 1
            if sid not in self._nodes:
                self._add_node(s, layer=target_layer, is_central=False)
            else:
                self._layers[sid] = max(self._layers[sid], target_layer)
            # Edge: source → successore
            self._add_edge(source_node, self._nodes[sid], variazione=s)

        if mark_expanded:
            source_node.is_expanded = True

    def _add_node(self, partita_data: Dict[str, Any], layer: int,
                  is_central: bool) -> _PartitaNodeItem:
        pid = partita_data.get("id")
        if pid is not None and pid in self._nodes:
            return self._nodes[pid]
        node = _PartitaNodeItem(partita_data, is_central=is_central)
        self._scene.addItem(node)
        if pid is not None:
            self._nodes[pid] = node
            self._layers[pid] = layer
        return node

    def _add_edge(self, source: _PartitaNodeItem,
                  target: _PartitaNodeItem,
                  variazione: Optional[Dict[str, Any]] = None):
        # Evita duplicati esatti (source, target) — sostituisci variazione
        key: Tuple[int, int] = (id(source), id(target))
        for e in self._edges:
            if (id(e.source), id(e.target)) == key:
                return
        edge = _EdgeItem(source, target, variazione=variazione)
        self._scene.addItem(edge)
        for sub in edge.items_to_add():
            self._scene.addItem(sub)
        self._edges.append(edge)

    def _relayout(self):
        """Layout layered semplice: ordina per layer, distribuisci x uniformi."""
        # Raggruppa nodi per layer
        by_layer: Dict[int, List[_PartitaNodeItem]] = {}
        for pid, layer in self._layers.items():
            by_layer.setdefault(layer, []).append(self._nodes[pid])

        if not by_layer:
            return

        min_layer = min(by_layer.keys())
        # Mappa: layer 0 = central → y0; -1 = sopra; +1 = sotto
        for layer, nodes in by_layer.items():
            # Ordina nodi per partita_id per stabilità
            nodes.sort(key=lambda n: n.partita_data.get("numero_partita") or 0)
            n = len(nodes)
            total_width = n * NODE_WIDTH + max(0, n - 1) * H_SPACING
            x0 = -total_width / 2
            y = (layer - min_layer) * (NODE_HEIGHT + V_SPACING)
            for i, node in enumerate(nodes):
                node.setPos(x0 + i * (NODE_WIDTH + H_SPACING), y)

        # Ricalcola tutti gli archi
        for edge in self._edges:
            edge.update_path()

        # Aggiorna bounding rect della scena
        self._scene.setSceneRect(self._scene.itemsBoundingRect().adjusted(-40, -40, 40, 40))


__all__ = [
    "GenealogiaGraphWidget",
]
