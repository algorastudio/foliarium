"""
foliarium/ui/widgets/timeline_partita.py — Timeline cronologica delle
variazioni di una partita.

Sostituisce la tabella variazioni con una UI a "nastro del tempo" in
cui ogni evento è una card espandibile con la cronologia degli atti
(Frazionamento, Vendita, Successione, ecc.) e i dettagli del contratto
collegato.

Reso fully Qt-native: nessuna dipendenza aggiuntiva oltre a PyQt6.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger("CatastoGUI.timeline_partita")


# Palette colori per i tipi di variazione storici più comuni.
# Le voci sono case-insensitive: la chiave è confrontata in lowercase.
_TIPO_COLORS: Dict[str, str] = {
    "frazionamento": "#F57C00",   # arancio
    "vendita":       "#3F51B5",   # blu indaco
    "successione":   "#2E7D32",   # verde
    "donazione":     "#7E57C2",   # viola
    "permuta":       "#00897B",   # teal
    "divisione":     "#C62828",   # rosso
    "rettifica":     "#5D4037",   # marrone
    "voltura":       "#0277BD",   # blu chiaro
}
_DEFAULT_COLOR = "#607D8B"  # blu-grigio per tipi non mappati


def _color_for_tipo(tipo: Optional[str]) -> str:
    if not tipo:
        return _DEFAULT_COLOR
    return _TIPO_COLORS.get(tipo.strip().lower(), _DEFAULT_COLOR)


def _format_date(value: Any) -> str:
    """Formatta una data in dd/mm/yyyy. Accetta date/datetime/str/None."""
    if value is None or value == "":
        return ""
    if isinstance(value, (date, datetime)):
        return value.strftime("%d/%m/%Y")
    s = str(value)
    # ISO yyyy-mm-dd → dd/mm/yyyy
    try:
        return datetime.fromisoformat(s.split(" ")[0]).strftime("%d/%m/%Y")
    except Exception:
        return s


def _year_of(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return str(value.year)
    s = str(value or "")
    if len(s) >= 4 and s[:4].isdigit():
        return s[:4]
    return ""


class _TimelineEntry(QFrame):
    """Singola voce della timeline. Card espandibile."""

    def __init__(self, variazione: Dict[str, Any],
                 current_partita_id: Optional[int] = None,
                 is_first: bool = False, is_last: bool = False,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.variazione = variazione
        self.current_partita_id = current_partita_id
        self.is_first = is_first
        self.is_last = is_last
        self._expanded = False
        self._build_ui()

    def _build_ui(self):
        self.setObjectName("timelineEntry")
        self.setFrameShape(QFrame.Shape.NoFrame)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # ── Colonna sinistra: data ────────────────────────────────────
        date_col = QWidget()
        date_col.setFixedWidth(72)
        date_layout = QVBoxLayout(date_col)
        date_layout.setContentsMargins(0, 4, 0, 0)
        date_layout.setSpacing(0)

        anno = _year_of(self.variazione.get("data_variazione"))
        giorno = _format_date(self.variazione.get("data_variazione"))
        # Visualizza "15/03" sopra e l'anno sotto, in grande
        giorno_mese = giorno[:5] if len(giorno) >= 5 else giorno

        anno_label = QLabel(anno or "—")
        anno_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        anno_label.setStyleSheet("font-size: 18px; font-weight: 600;")
        date_layout.addWidget(anno_label)

        giorno_label = QLabel(giorno_mese)
        giorno_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        giorno_label.setStyleSheet("font-size: 11px; color: palette(mid);")
        date_layout.addWidget(giorno_label)
        date_layout.addStretch()

        layout.addWidget(date_col)

        # ── Colonna centrale: linea verticale + pallino colorato ──────
        rail_col = QWidget()
        rail_col.setFixedWidth(20)
        rail_layout = QVBoxLayout(rail_col)
        rail_layout.setContentsMargins(0, 0, 0, 0)
        rail_layout.setSpacing(0)

        color = _color_for_tipo(self.variazione.get("tipo"))

        # Segmento di linea sopra il pallino (nascosto sulla prima entry)
        top_line = QFrame()
        top_line.setFrameShape(QFrame.Shape.VLine)
        top_line.setStyleSheet("color: palette(mid); background: palette(mid);")
        top_line.setFixedWidth(2)
        top_line.setFixedHeight(8)
        top_line_wrap = QWidget()
        top_line_wrap_l = QHBoxLayout(top_line_wrap)
        top_line_wrap_l.setContentsMargins(0, 0, 0, 0)
        top_line_wrap_l.addStretch()
        top_line_wrap_l.addWidget(top_line)
        top_line_wrap_l.addStretch()
        if self.is_first:
            top_line_wrap.setVisible(False)
        rail_layout.addWidget(top_line_wrap)

        # Pallino colorato
        dot = QLabel()
        dot.setFixedSize(14, 14)
        dot.setStyleSheet(
            f"background:{color}; border-radius:7px; border:2px solid palette(window);"
        )
        dot_wrap = QWidget()
        dot_wrap_l = QHBoxLayout(dot_wrap)
        dot_wrap_l.setContentsMargins(0, 0, 0, 0)
        dot_wrap_l.addStretch()
        dot_wrap_l.addWidget(dot)
        dot_wrap_l.addStretch()
        rail_layout.addWidget(dot_wrap)

        # Linea sotto il pallino (nascosta sull'ultima entry)
        bottom_line = QFrame()
        bottom_line.setFrameShape(QFrame.Shape.VLine)
        bottom_line.setStyleSheet("color: palette(mid); background: palette(mid);")
        bottom_line.setFixedWidth(2)
        bottom_line_wrap = QWidget()
        bottom_line_wrap_l = QHBoxLayout(bottom_line_wrap)
        bottom_line_wrap_l.setContentsMargins(0, 0, 0, 0)
        bottom_line_wrap_l.addStretch()
        bottom_line_wrap_l.addWidget(bottom_line)
        bottom_line_wrap_l.addStretch()
        rail_layout.addWidget(bottom_line_wrap, 1)
        if self.is_last:
            bottom_line_wrap.setVisible(False)

        layout.addWidget(rail_col)

        # ── Colonna destra: card contenuto ────────────────────────────
        card = QFrame()
        card.setObjectName("timelineCard")
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setStyleSheet(
            f"#timelineCard {{ "
            f"  background: palette(base); "
            f"  border: 1px solid palette(mid); "
            f"  border-left: 4px solid {color}; "
            f"  border-radius: 6px; "
            f"  padding: 0px; "
            f"}}"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(6)

        # Header: tipo + bottone espandi
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        tipo_text = (self.variazione.get("tipo") or "Variazione").upper()
        tipo_label = QLabel(tipo_text)
        tipo_label.setStyleSheet(
            f"font-size: 12px; font-weight: 700; color: {color};")
        header_row.addWidget(tipo_label)
        header_row.addStretch()

        var_id = self.variazione.get("id")
        if var_id is not None:
            id_label = QLabel(f"ID Var. {var_id}")
            id_label.setStyleSheet("color: palette(mid); font-size: 10px;")
            header_row.addWidget(id_label)

        card_layout.addLayout(header_row)

        # Origine → Destinazione
        flow_text = self._flow_description()
        if flow_text:
            flow_label = QLabel(flow_text)
            flow_label.setTextFormat(Qt.TextFormat.RichText)
            flow_label.setWordWrap(True)
            card_layout.addWidget(flow_label)

        # Pulsante espandi dettagli contratto
        self._has_contract = bool(self.variazione.get("tipo_contratto"))
        self._has_notes = bool(self.variazione.get("contratto_note"))
        self._has_repertorio = bool(self.variazione.get("repertorio"))

        if self._has_contract or self._has_notes or self._has_repertorio:
            self._toggle_btn = QToolButton()
            self._toggle_btn.setText("▶ Dettagli contratto")
            self._toggle_btn.setCheckable(True)
            self._toggle_btn.setAutoRaise(True)
            self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._toggle_btn.setStyleSheet(
                "QToolButton { color: palette(link); font-size: 11px; "
                "  padding: 2px 4px; }"
                "QToolButton:checked { color: palette(text); }"
            )
            self._toggle_btn.toggled.connect(self._on_toggle)
            card_layout.addWidget(self._toggle_btn,
                                  alignment=Qt.AlignmentFlag.AlignLeft)

            self._detail_frame = self._build_detail_frame(color)
            self._detail_frame.setVisible(False)
            card_layout.addWidget(self._detail_frame)

        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(card, 1)

    def _flow_description(self) -> str:
        """Descrizione 'Origine → Destinazione' in HTML, evidenziando la partita corrente."""
        origine = self._format_partita_link(
            self.variazione.get("partita_origine_id"),
            self.variazione.get("origine_numero_partita"),
            self.variazione.get("origine_comune_nome"),
        )
        destinazione = self._format_partita_link(
            self.variazione.get("partita_destinazione_id"),
            self.variazione.get("destinazione_numero_partita"),
            self.variazione.get("destinazione_comune_nome"),
        )
        if not origine and not destinazione:
            return ""
        arrow = "&nbsp;→&nbsp;"
        parts: List[str] = []
        if origine:
            parts.append(f"<span>Da {origine}</span>")
        if destinazione:
            parts.append(f"<span>A {destinazione}</span>")
        return arrow.join(parts) if origine and destinazione else " ".join(parts)

    def _format_partita_link(self, pid: Any, numero: Any, comune: Any) -> str:
        if not pid and not numero:
            return ""
        num = str(numero) if numero is not None else "?"
        com = str(comune) if comune else ""
        text = f"Partita N.{num}"
        if com:
            text += f" ({com})"
        # Evidenzia la partita corrente in grassetto
        if self.current_partita_id is not None and pid == self.current_partita_id:
            return f"<b>{text}</b>"
        return text

    def _build_detail_frame(self, color: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame {{ background: palette(alternate-base); "
            f"  border-left: 2px solid {color}; "
            f"  border-radius: 3px; padding: 4px 8px; }}"
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(3)

        rows: List[str] = []
        tipo_contratto = self.variazione.get("tipo_contratto")
        if tipo_contratto:
            rows.append(f"<b>Tipo contratto:</b> {tipo_contratto}")
        data_contratto = self.variazione.get("data_contratto")
        if data_contratto:
            rows.append(f"<b>Data:</b> {_format_date(data_contratto)}")
        notaio = self.variazione.get("notaio")
        if notaio:
            rows.append(f"<b>Notaio:</b> {notaio}")
        repertorio = self.variazione.get("repertorio")
        if repertorio:
            rows.append(f"<b>Repertorio:</b> {repertorio}")
        contratto_note = self.variazione.get("contratto_note")
        if contratto_note:
            rows.append(f"<b>Note:</b> {contratto_note}")

        if not rows:
            rows.append("<i>Nessun dettaglio contratto disponibile.</i>")

        for r in rows:
            lbl = QLabel(r)
            lbl.setTextFormat(Qt.TextFormat.RichText)
            lbl.setWordWrap(True)
            lbl.setStyleSheet("font-size: 11px;")
            layout.addWidget(lbl)

        return frame

    def _on_toggle(self, checked: bool):
        self._expanded = checked
        self._toggle_btn.setText(
            "▼ Dettagli contratto" if checked else "▶ Dettagli contratto")
        self._detail_frame.setVisible(checked)


class TimelinePartitaWidget(QWidget):
    """Timeline cronologica delle variazioni di una partita."""

    def __init__(self, variazioni: Optional[List[Dict[str, Any]]] = None,
                 current_partita_id: Optional[int] = None,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._variazioni = variazioni or []
        self._current_partita_id = current_partita_id
        self._chronological = True  # True = vecchio→nuovo (top→bottom)
        self._build_ui()
        self._populate()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)

        # Toolbar minimale: conteggio + bottoni ordine/espandi tutto
        toolbar = QHBoxLayout()
        self._count_label = QLabel("")
        self._count_label.setStyleSheet("color: palette(mid);")
        toolbar.addWidget(self._count_label)
        toolbar.addStretch()

        self._btn_order = QPushButton("⇅ Ordine cronologico")
        self._btn_order.setFlat(True)
        self._btn_order.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_order.clicked.connect(self._toggle_order)
        toolbar.addWidget(self._btn_order)

        self._btn_expand_all = QPushButton("Espandi tutto")
        self._btn_expand_all.setFlat(True)
        self._btn_expand_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_expand_all.clicked.connect(self._expand_all)
        toolbar.addWidget(self._btn_expand_all)

        outer.addLayout(toolbar)

        # Area scrollabile con la timeline
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(8, 8, 8, 8)
        self._container_layout.setSpacing(0)
        self._container_layout.addStretch(1)

        self._scroll.setWidget(self._container)
        outer.addWidget(self._scroll, 1)

    def set_variazioni(self, variazioni: List[Dict[str, Any]],
                       current_partita_id: Optional[int] = None):
        self._variazioni = variazioni or []
        if current_partita_id is not None:
            self._current_partita_id = current_partita_id
        self._populate()

    def _toggle_order(self):
        self._chronological = not self._chronological
        self._btn_order.setText(
            "⇅ Ordine cronologico" if self._chronological
            else "⇅ Più recenti prima")
        self._populate()

    def _expand_all(self):
        for i in range(self._container_layout.count()):
            item = self._container_layout.itemAt(i)
            w = item.widget()
            if isinstance(w, _TimelineEntry) and hasattr(w, "_toggle_btn"):
                w._toggle_btn.setChecked(True)

    def _clear(self):
        # Rimuovi tutto tranne lo stretch finale
        while self._container_layout.count() > 1:
            item = self._container_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

    def _populate(self):
        self._clear()

        if not self._variazioni:
            self._count_label.setText("Nessuna variazione registrata.")
            empty = QLabel(
                "Nessuna variazione registrata per questa partita.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("color: palette(mid); padding: 24px;")
            self._container_layout.insertWidget(0, empty)
            return

        # Ordina per data_variazione
        def _sort_key(v):
            d = v.get("data_variazione")
            if d is None:
                return date.min
            if isinstance(d, (date, datetime)):
                return d if isinstance(d, date) else d.date()
            try:
                return datetime.fromisoformat(str(d).split(" ")[0]).date()
            except Exception:
                return date.min

        ordered = sorted(self._variazioni, key=_sort_key,
                         reverse=not self._chronological)

        self._count_label.setText(
            f"{len(ordered)} variazion{'i' if len(ordered) != 1 else 'e'} "
            f"in ordine {'cronologico' if self._chronological else 'inverso'}")

        for i, var in enumerate(ordered):
            entry = _TimelineEntry(
                var,
                current_partita_id=self._current_partita_id,
                is_first=(i == 0),
                is_last=(i == len(ordered) - 1),
            )
            self._container_layout.insertWidget(
                self._container_layout.count() - 1, entry)


__all__ = [
    "TimelinePartitaWidget",
]
