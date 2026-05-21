from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame,
    QGraphicsDropShadowEffect, QSizePolicy, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

class GenealogiaNodeWidget(QFrame):
    """Rappresenta una singola operazione (nodo) nella timeline genealogica."""

    node_clicked = pyqtSignal(int)  # Emette l'ID della partita associata al nodo

    def __init__(self, data: dict, is_central: bool = False, is_predecessor: bool = False):
        super().__init__()
        self.data = data
        self.partita_id = data.get("id")
        self.numero_partita = data.get("numero_partita")
        self.suffisso = data.get("suffisso_partita") or ""
        self.comune = data.get("comune_nome") or "Sconosciuto"
        self.possessori = data.get("possessori") or "Nessun possessore"
        self.data_impianto = data.get("data_impianto")
        self.stato = data.get("stato", "attiva").upper()
        self.tipo_variazione = data.get("tipo_variazione")
        self.data_variazione = data.get("data_variazione")
        self.nominativo_rif = data.get("nominativo_riferimento")

        self.is_central = is_central
        self.is_predecessor = is_predecessor

        self.setup_ui()
        self.setup_style()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(5)

        # Intestazione (es. SUCCESSIONE -> Partita 123)
        header_layout = QHBoxLayout()
        title_text = f"Partita {self.numero_partita}"
        if self.suffisso:
            title_text += f" {self.suffisso}"

        title_label = QLabel(title_text)
        font = title_label.font()
        font.setBold(True)
        font.setPointSize(11)
        title_label.setFont(font)

        status_label = QLabel(self.stato)
        status_font = status_label.font()
        status_font.setBold(True)
        status_font.setPointSize(9)
        status_label.setFont(status_font)

        if self.stato == "ATTIVA":
            status_label.setStyleSheet("color: #27ae60;")
        else:
            status_label.setStyleSheet("color: #c0392b;")

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(status_label)
        layout.addLayout(header_layout)

        # Info variazioni (se presenti)
        if self.tipo_variazione:
            data_var = self.data_variazione.strftime("%d/%m/%Y") if self.data_variazione else "Data N/D"
            var_label = QLabel(f"🔄 <b>{self.tipo_variazione.upper()}</b> il {data_var}")
            var_label.setTextFormat(Qt.TextFormat.RichText)
            layout.addWidget(var_label)
            if self.nominativo_rif:
                rif_label = QLabel(f"👤 Rif: {self.nominativo_rif}")
                rif_label.setStyleSheet("color: #555555;")
                layout.addWidget(rif_label)

        # Comune e Possessori
        layout.addWidget(QLabel(f"<b>Comune:</b> {self.comune}"))

        poss_label = QLabel(f"<b>Possessori:</b><br>{self.possessori}")
        poss_label.setWordWrap(True)
        layout.addWidget(poss_label)

        # Pulsante di navigazione (opzionale)
        if not self.is_central and self.partita_id:
            btn_nav = QPushButton("Vedi Dettagli")
            btn_nav.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_nav.clicked.connect(self._on_btn_clicked)
            layout.addWidget(btn_nav, alignment=Qt.AlignmentFlag.AlignRight)

    def setup_style(self):
        self.setObjectName("GenealogiaNode")
        self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        self.setMinimumWidth(280)

        # Colore bordo in base al ruolo
        border_color = "#3498db" if self.is_central else ("#e67e22" if self.is_predecessor else "#9b59b6")
        bg_color = "#ffffff"
        if self.is_central:
            bg_color = "#f0f8ff"

        self.setStyleSheet(f"""
            QFrame#GenealogiaNode {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: 8px;
            }}
        """)

        # Ombra morbida
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)

    def _on_btn_clicked(self):
        self.node_clicked.emit(self.partita_id)


class GenealogiaTimelineWidget(QWidget):
    """Widget principale che visualizza la timeline genealogica di una partita."""

    navigate_to_partita = pyqtSignal(int)

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.current_partita_id = None
        self.setup_ui()

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)

        # Header / Status
        self.header_label = QLabel("Caricamento genealogia in corso...")
        font = self.header_label.font()
        font.setBold(True)
        font.setPointSize(12)
        self.header_label.setFont(font)
        self.header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.header_label)

        # Scroll area per la timeline
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("background-color: transparent;")

        self.container_widget = QWidget()
        self.container_widget.setStyleSheet("background-color: transparent;")
        self.timeline_layout = QVBoxLayout(self.container_widget)
        self.timeline_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.timeline_layout.setSpacing(20)

        self.scroll_area.setWidget(self.container_widget)
        self.main_layout.addWidget(self.scroll_area)

    def _create_arrow(self) -> QLabel:
        lbl = QLabel("⬇")
        font = lbl.font()
        font.setPointSize(24)
        lbl.setFont(font)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color: #7f8c8d; margin: -10px 0;")
        return lbl

    def _create_section_label(self, testTesto: str) -> QLabel:
        lbl = QLabel(testTesto)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color: #7f8c8d; font-weight: bold; font-size: 11px;")
        return lbl

    def load_partita(self, partita_id: int):
        self.current_partita_id = partita_id

        # Pulisci il layout corrente
        for i in reversed(range(self.timeline_layout.count())):
            widget = self.timeline_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)

        self.header_label.setText("Caricamento...")

        try:
            genealogia = self.db.get_genealogia_partita(partita_id)
            if not genealogia:
                self.header_label.setText("Nessun dato genealogico trovato.")
                return

            partita_centrale = genealogia.get("partita")
            predecessori = genealogia.get("predecessori", [])
            successori = genealogia.get("successori", [])

            self.header_label.setText(f"Genealogia della Partita {partita_centrale.get('numero_partita')}")

            # 1. PREDECESSORI (Origini)
            if predecessori:
                self.timeline_layout.addWidget(self._create_section_label("PROVENIENZE (PREDECESSORI)"))

                # Se c'è più di un predecessore (es. fusione), li mettiamo in orizzontale
                pred_container = QWidget()
                pred_layout = QHBoxLayout(pred_container)
                pred_layout.setSpacing(15)
                pred_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

                for p_data in predecessori:
                    node = GenealogiaNodeWidget(p_data, is_predecessor=True)
                    node.node_clicked.connect(self.navigate_to_partita.emit)
                    pred_layout.addWidget(node)

                self.timeline_layout.addWidget(pred_container)
                self.timeline_layout.addWidget(self._create_arrow())

            # 2. PARTITA CENTRALE
            self.timeline_layout.addWidget(self._create_section_label("PARTITA IN ESAME"))
            node_centrale = GenealogiaNodeWidget(partita_centrale, is_central=True)
            self.timeline_layout.addWidget(node_centrale, alignment=Qt.AlignmentFlag.AlignCenter)

            # 3. SUCCESSORI (Derivazioni)
            if successori:
                self.timeline_layout.addWidget(self._create_arrow())
                self.timeline_layout.addWidget(self._create_section_label("DERIVAZIONI (SUCCESSORI)"))

                # Se c'è più di un successore (es. frazionamento), li mettiamo in orizzontale
                succ_container = QWidget()
                succ_layout = QHBoxLayout(succ_container)
                succ_layout.setSpacing(15)
                succ_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

                for s_data in successori:
                    node = GenealogiaNodeWidget(s_data)
                    node.node_clicked.connect(self.navigate_to_partita.emit)
                    succ_layout.addWidget(node)

                self.timeline_layout.addWidget(succ_container)

        except Exception as e:
            self.header_label.setText("Errore durante il caricamento.")
            print(f"Errore caricamento genealogia: {e}")
