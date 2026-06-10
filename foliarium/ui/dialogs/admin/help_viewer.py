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

_HELP_CSS = """
<style>
body {
    font-family: Segoe UI, Arial, sans-serif;
    font-size: 13px;
    line-height: 1.65;
    color: #212121;
    max-width: 860px;
    margin: 0 auto;
    padding: 16px 24px;
}
h1 { font-size: 1.7em; color: #1a237e; border-bottom: 2px solid #3949ab; padding-bottom: 6px; margin-top: 0; }
h2 { font-size: 1.35em; color: #283593; border-bottom: 1px solid #c5cae9; padding-bottom: 4px; margin-top: 1.4em; }
h3 { font-size: 1.1em; color: #303f9f; margin-top: 1.2em; }
h4 { font-size: 1em; color: #3949ab; }
a  { color: #1565c0; text-decoration: none; }
a:hover { text-decoration: underline; }
code {
    background: #f0f0f0;
    border-radius: 3px;
    padding: 1px 5px;
    font-family: Consolas, monospace;
    font-size: 0.88em;
    color: #c62828;
}
pre {
    background: #f5f5f5;
    border-left: 4px solid #3949ab;
    border-radius: 3px;
    padding: 10px 14px;
    overflow-x: auto;
    font-family: Consolas, monospace;
    font-size: 0.85em;
    line-height: 1.5;
}
pre code { background: none; padding: 0; color: inherit; }
blockquote {
    background: #e8eaf6;
    border-left: 4px solid #3949ab;
    margin: 10px 0;
    padding: 8px 14px;
    border-radius: 0 4px 4px 0;
    color: #37474f;
}
table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 0.92em; }
th { background: #3949ab; color: #fff; padding: 7px 12px; text-align: left; }
td { padding: 6px 12px; border-bottom: 1px solid #e0e0e0; }
tr:nth-child(even) td { background: #f5f5f5; }
ul, ol { padding-left: 1.5em; margin: 6px 0; }
li { margin: 3px 0; }
hr { border: none; border-top: 1px solid #e0e0e0; margin: 16px 0; }
</style>
"""

_MKDOCS_YML = "mkdocs.yml"


# ---------------------------------------------------------------------------
# HelpViewerDialog — Manuale utente integrato (Markdown → QTextBrowser)
# ---------------------------------------------------------------------------

_HELP_CSS = """
<style>
body {
    font-family: Segoe UI, Arial, sans-serif;
    font-size: 13px;
    line-height: 1.65;
    color: #212121;
    max-width: 860px;
    margin: 0 auto;
    padding: 16px 24px;
}
h1 { font-size: 1.7em; color: #1a237e; border-bottom: 2px solid #3949ab; padding-bottom: 6px; margin-top: 0; }
h2 { font-size: 1.35em; color: #283593; border-bottom: 1px solid #c5cae9; padding-bottom: 4px; margin-top: 1.4em; }
h3 { font-size: 1.1em; color: #303f9f; margin-top: 1.2em; }
h4 { font-size: 1em; color: #3949ab; }
a  { color: #1565c0; text-decoration: none; }
a:hover { text-decoration: underline; }
code {
    background: #f0f0f0;
    border-radius: 3px;
    padding: 1px 5px;
    font-family: Consolas, monospace;
    font-size: 0.88em;
    color: #c62828;
}
pre {
    background: #f5f5f5;
    border-left: 4px solid #3949ab;
    border-radius: 3px;
    padding: 10px 14px;
    overflow-x: auto;
    font-family: Consolas, monospace;
    font-size: 0.85em;
    line-height: 1.5;
}
pre code { background: none; padding: 0; color: inherit; }
blockquote {
    background: #e8eaf6;
    border-left: 4px solid #3949ab;
    margin: 10px 0;
    padding: 8px 14px;
    border-radius: 0 4px 4px 0;
    color: #37474f;
}
table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 0.92em; }
th { background: #3949ab; color: #fff; padding: 7px 12px; text-align: left; }
td { padding: 6px 12px; border-bottom: 1px solid #e0e0e0; }
tr:nth-child(even) td { background: #f5f5f5; }
ul, ol { padding-left: 1.5em; margin: 6px 0; }
li { margin: 3px 0; }
hr { border: none; border-top: 1px solid #e0e0e0; margin: 16px 0; }
</style>
"""

_MKDOCS_YML = "mkdocs.yml"


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
                + _HELP_CSS
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




