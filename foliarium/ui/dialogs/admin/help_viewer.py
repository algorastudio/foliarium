"""Visualizzatore del manuale utente integrato."""
from __future__ import annotations


from PyQt6.QtCore import (Qt)
from PyQt6.QtGui import (QDesktopServices, QFont)
from PyQt6.QtWidgets import (QDialog,
                             QHBoxLayout, QLabel, QPushButton, QSplitter, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                             QTextBrowser)
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


# ---------------------------------------------------------------------------
# HelpViewerDialog — Manuale utente integrato (Markdown → QTextBrowser)
# ---------------------------------------------------------------------------

#: Palette del manuale per tema chiaro e scuro. Il QSS di Qt non raggiunge
#: l'HTML renderizzato dentro il QTextBrowser, quindi i colori del documento
#: vanno dichiarati qui, altrimenti in tema scuro il manuale si aprirebbe
#: come una pagina bianca accecante.
_HELP_PALETTES = {
    "light": {
        "bg":          "#ffffff",
        "fg":          "#212121",
        "h1":          "#1a237e",
        "h2":          "#283593",
        "h3":          "#303f9f",
        "h4":          "#3949ab",
        "rule":        "#3949ab",
        "rule_soft":   "#c5cae9",
        "link":        "#1565c0",
        "code_bg":     "#f0f0f0",
        "code_fg":     "#c62828",
        "pre_bg":      "#f5f5f5",
        "quote_bg":    "#e8eaf6",
        "quote_fg":    "#37474f",
        "th_bg":       "#3949ab",
        "th_fg":       "#ffffff",
        "border":      "#e0e0e0",
        "row_alt":     "#f5f5f5",
    },
    "dark": {
        "bg":          "#1e1f26",
        "fg":          "#e4e6eb",
        "h1":          "#9fa8da",
        "h2":          "#9fa8da",
        "h3":          "#b39ddb",
        "h4":          "#b0bec5",
        "rule":        "#5c6bc0",
        "rule_soft":   "#3a3f55",
        "link":        "#82b1ff",
        "code_bg":     "#2a2c36",
        "code_fg":     "#ff8a80",
        "pre_bg":      "#24262f",
        "quote_bg":    "#262a3d",
        "quote_fg":    "#cfd8dc",
        "th_bg":       "#3a416b",
        "th_fg":       "#ffffff",
        "border":      "#3a3f55",
        "row_alt":     "#24262f",
    },
}


def _build_help_css(dark: bool) -> str:
    """Compone il foglio di stile del manuale per il tema attivo."""
    c = _HELP_PALETTES["dark" if dark else "light"]
    return """
<style>
body {{
    font-family: Segoe UI, Arial, sans-serif;
    font-size: 13px;
    line-height: 1.65;
    color: {fg};
    background-color: {bg};
    max-width: 860px;
    margin: 0 auto;
    padding: 16px 24px;
}}
h1 {{ font-size: 1.7em; color: {h1}; border-bottom: 2px solid {rule}; padding-bottom: 6px; margin-top: 0; }}
h2 {{ font-size: 1.35em; color: {h2}; border-bottom: 1px solid {rule_soft}; padding-bottom: 4px; margin-top: 1.4em; }}
h3 {{ font-size: 1.1em; color: {h3}; margin-top: 1.2em; }}
h4 {{ font-size: 1em; color: {h4}; }}
a  {{ color: {link}; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
code {{
    background: {code_bg};
    border-radius: 3px;
    padding: 1px 5px;
    font-family: Consolas, monospace;
    font-size: 0.88em;
    color: {code_fg};
}}
pre {{
    background: {pre_bg};
    border-left: 4px solid {rule};
    border-radius: 3px;
    padding: 10px 14px;
    overflow-x: auto;
    font-family: Consolas, monospace;
    font-size: 0.85em;
    line-height: 1.5;
}}
pre code {{ background: none; padding: 0; color: inherit; }}
blockquote {{
    background: {quote_bg};
    border-left: 4px solid {rule};
    margin: 10px 0;
    padding: 8px 14px;
    border-radius: 0 4px 4px 0;
    color: {quote_fg};
}}
table {{ border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 0.92em; }}
th {{ background: {th_bg}; color: {th_fg}; padding: 7px 12px; text-align: left; }}
td {{ padding: 6px 12px; border-bottom: 1px solid {border}; }}
tr:nth-child(even) td {{ background: {row_alt}; }}
ul, ol {{ padding-left: 1.5em; margin: 6px 0; }}
li {{ margin: 3px 0; }}
hr {{ border: none; border-top: 1px solid {border}; margin: 16px 0; }}
</style>
""".format(**c)


_MKDOCS_YML = "mkdocs.yml"


# ---------------------------------------------------------------------------
# HelpViewerDialog — Manuale utente integrato (Markdown → QTextBrowser)
# ---------------------------------------------------------------------------



class HelpViewerDialog(QDialog):
    """Visualizzatore del manuale utente integrato.
    Legge i file .md dalla cartella docs/, li converte in HTML e li mostra
    in un QTextBrowser con navigazione ad albero sul lato sinistro.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manuale Utente \u2014 Foliarium")
        self.setMinimumSize(900, 620)
        self.resize(1100, 720)
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)

        self._docs_dir = get_doc_path()
        self._history = []
        self._history_pos = -1

        # Il manuale viene renderizzato come HTML dentro un QTextBrowser:
        # i colori vanno scelti ora, in base al tema attivo, perche' il QSS
        # dell'applicazione non raggiunge il contenuto del documento.
        try:
            from foliarium.ui.theme import is_dark_theme
            self._dark = is_dark_theme()
        except Exception:
            self._dark = False
        self._help_css = _build_help_css(self._dark)

        self._build_ui()
        self._populate_nav()

        # Apri la prima pagina disponibile
        root = self.nav_tree.invisibleRootItem()
        if root.childCount():
            first = root.child(0)
            if first.childCount():
                first = first.child(0)
            self.nav_tree.setCurrentItem(first)

    # ------------------------------------------------------------------
    # Costruzione UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Toolbar navigazione
        toolbar = QHBoxLayout()
        self.btn_back = QPushButton("\u25c4 Indietro")
        self.btn_back.setEnabled(False)
        self.btn_back.clicked.connect(self._go_back)
        self.btn_forward = QPushButton("Avanti \u25ba")
        self.btn_forward.setEnabled(False)
        self.btn_forward.clicked.connect(self._go_forward)
        self.lbl_title = QLabel()
        title_font = self.lbl_title.font()
        title_font.setBold(True)
        self.lbl_title.setFont(title_font)
        toolbar.addWidget(self.btn_back)
        toolbar.addWidget(self.btn_forward)
        toolbar.addSpacing(12)
        toolbar.addWidget(self.lbl_title)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Splitter: albero a sinistra, contenuto a destra
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.nav_tree = QTreeWidget()
        self.nav_tree.setHeaderHidden(True)
        self.nav_tree.setMinimumWidth(180)
        self.nav_tree.setMaximumWidth(280)
        self.nav_tree.setAnimated(True)
        self.nav_tree.currentItemChanged.connect(self._on_nav_changed)

        self.content = QTextBrowser()
        self.content.setOpenLinks(False)
        # Evita il lampo di sfondo chiaro tra un caricamento e l'altro:
        # il viewport usa lo stesso colore dichiarato nel CSS del documento.
        _bg = _HELP_PALETTES["dark" if self._dark else "light"]["bg"]
        self.content.setStyleSheet(f"QTextBrowser {{ background-color: {_bg}; }}")
        self.content.anchorClicked.connect(self._on_link_clicked)
        self.content.setFont(QFont("Segoe UI", 10))

        splitter.addWidget(self.nav_tree)
        splitter.addWidget(self.content)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        layout.addWidget(splitter, stretch=1)

        # Pulsante chiudi
        btn_bar = QHBoxLayout()
        btn_bar.addStretch()
        btn_close = QPushButton("Chiudi")
        btn_close.setDefault(True)
        btn_close.clicked.connect(self.accept)
        btn_bar.addWidget(btn_close)
        layout.addLayout(btn_bar)

    # ------------------------------------------------------------------
    # Navigazione ad albero da mkdocs.yml
    # ------------------------------------------------------------------

    def _populate_nav(self):
        """Legge mkdocs.yml e costruisce il QTreeWidget di navigazione."""
        nav = self._parse_mkdocs_nav()
        self.nav_tree.clear()
        if nav:
            self._add_nav_items(self.nav_tree.invisibleRootItem(), nav)
        else:
            self._add_nav_fallback()
        self.nav_tree.expandAll()

    def _parse_mkdocs_nav(self):
        """Tenta di leggere la sezione nav da mkdocs.yml."""
        yml_path = self._docs_dir.parent / _MKDOCS_YML
        if not yml_path.exists():
            return []
        try:
            import yaml
            with open(yml_path, encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            return cfg.get("nav", []) or []
        except Exception:
            return []

    def _add_nav_items(self, parent, nav_list):
        """Ricorsivo: costruisce QTreeWidgetItem dalla struttura nav di mkdocs."""
        for entry in nav_list:
            if isinstance(entry, dict):
                for label, value in entry.items():
                    if isinstance(value, str):
                        item = QTreeWidgetItem(parent, [label])
                        item.setData(0, Qt.ItemDataRole.UserRole, value)
                        item.setToolTip(0, label)
                    elif isinstance(value, list):
                        cat = QTreeWidgetItem(parent, [label])
                        cat.setData(0, Qt.ItemDataRole.UserRole, None)
                        cat_font = cat.font(0)
                        cat_font.setBold(True)
                        cat.setFont(0, cat_font)
                        self._add_nav_items(cat, value)
            elif isinstance(entry, str):
                item = QTreeWidgetItem(parent, [entry])
                item.setData(0, Qt.ItemDataRole.UserRole, entry)

    def _add_nav_fallback(self):
        """Fallback: scansiona docs/ e aggiunge tutti i .md trovati."""
        for md_file in sorted(self._docs_dir.rglob("*.md")):
            rel = md_file.relative_to(self._docs_dir).as_posix()
            label = md_file.stem.replace("-", " ").replace("_", " ").title()
            item = QTreeWidgetItem(self.nav_tree, [label])
            item.setData(0, Qt.ItemDataRole.UserRole, rel)

    # ------------------------------------------------------------------
    # Caricamento e rendering pagina
    # ------------------------------------------------------------------

    def _load_page(self, rel_path, push_history=True):
        """Carica un file .md, lo converte in HTML e lo visualizza."""
        anchor = ""
        if "#" in rel_path:
            rel_path, anchor = rel_path.split("#", 1)
        rel_path = rel_path.replace("\\", "/")

        md_file = self._docs_dir / rel_path
        if not md_file.exists():
            self.content.setHtml(
                f"<p><i>Pagina non trovata: <code>{rel_path}</code></i></p>")
            return

        try:
            import markdown as _md
            text = md_file.read_text(encoding="utf-8")
            body = _md.markdown(
                text,
                extensions=["tables", "fenced_code", "toc", "admonition", "nl2br"],
            )
            html = (
                "<!DOCTYPE html><html><head>"
                + self._help_css
                + "</head><body>"
                + body
                + "</body></html>"
            )
            self.content.setHtml(html)
        except Exception as e:
            self.content.setPlainText(f"Errore rendering: {e}")
            return

        title = md_file.stem.replace("-", " ").replace("_", " ").title()
        self.lbl_title.setText(title)

        if anchor:
            self.content.scrollToAnchor(anchor)

        if push_history:
            self._history = self._history[:self._history_pos + 1]
            self._history.append(rel_path)
            self._history_pos = len(self._history) - 1

        self._update_nav_buttons()
        self._sync_tree(rel_path)

    def _sync_tree(self, rel_path):
        """Seleziona nel tree il nodo corrispondente alla pagina corrente."""
        def _find(item):
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.replace("\\", "/") == rel_path:
                self.nav_tree.blockSignals(True)
                self.nav_tree.setCurrentItem(item)
                self.nav_tree.blockSignals(False)
                return True
            for i in range(item.childCount()):
                if _find(item.child(i)):
                    return True
            return False

        root = self.nav_tree.invisibleRootItem()
        for i in range(root.childCount()):
            if _find(root.child(i)):
                break

    # ------------------------------------------------------------------
    # Slot
    # ------------------------------------------------------------------

    def _on_nav_changed(self, current, _previous):
        if current is None:
            return
        path = current.data(0, Qt.ItemDataRole.UserRole)
        if path:
            self._load_page(path)

    def _on_link_clicked(self, url):
        href = url.toString()
        if href.startswith("http://") or href.startswith("https://"):
            QDesktopServices.openUrl(url)
            return
        if self._history_pos >= 0:
            from pathlib import PurePosixPath
            current_rel = self._history[self._history_pos]
            base = PurePosixPath(current_rel).parent
            resolved = str(base / href).lstrip("/")
        else:
            resolved = href
        self._load_page(resolved)

    def _go_back(self):
        if self._history_pos > 0:
            self._history_pos -= 1
            self._load_page(self._history[self._history_pos], push_history=False)

    def _go_forward(self):
        if self._history_pos < len(self._history) - 1:
            self._history_pos += 1
            self._load_page(self._history[self._history_pos], push_history=False)

    def _update_nav_buttons(self):
        self.btn_back.setEnabled(self._history_pos > 0)
        self.btn_forward.setEnabled(self._history_pos < len(self._history) - 1)


# ===========================================================================
# LicenseDialog — gestione e visualizzazione della licenza
# ===========================================================================




