"""
Genera il manuale utente Foliarium in PDF a partire dai file Markdown della docs/.
Usa fpdf2 + markdown (già installati nel progetto).

Uso:
    python docs/genera_pdf.py
Output:
    docs/manuale_foliarium_<versione>.pdf
"""

import io
import os
import re
import sys
import markdown
from fpdf import FPDF
from fpdf.fonts import FontFace

# Forza output UTF-8 su console Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Importa la versione centralizzata
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import APP_VERSION, APP_NAME, APP_SUBTITLE

# ── Configurazione ──────────────────────────────────────────────────────────

VERSION     = APP_VERSION
APP_LABEL   = f"{APP_NAME} — {APP_SUBTITLE}"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), f"manuale_foliarium_{VERSION.replace('.','_')}.pdf")
DOCS_DIR    = os.path.dirname(__file__)

# Font TTF di sistema (Windows)
WIN_FONTS = r"C:\Windows\Fonts"
FONT_R  = os.path.join(WIN_FONTS, "arial.ttf")
FONT_B  = os.path.join(WIN_FONTS, "arialbd.ttf")
FONT_I  = os.path.join(WIN_FONTS, "ariali.ttf")
FONT_BI = os.path.join(WIN_FONTS, "arialbi.ttf")

NAV_FILES = [
    "index.md",
    "introduzione.md",
    "primo-avvio.md",
    "consultazione.md",
    "inserimento.md",
    "ricerca-avanzata.md",
    "reportistica.md",
    "statistiche.md",
    "esportazioni.md",
    "admin/index.md",
    "admin/installazione.md",
    "admin/gestione-utenti.md",
    "admin/backup.md",
    "admin/import-massivo.md",
    "riferimento/faq.md",
    "riferimento/changelog.md",
]

# ── PDF class ───────────────────────────────────────────────────────────────

class ManualePDF(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Arial", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"{APP_NAME} v{VERSION} - Manuale Utente", align="L")
        self.cell(0, 8, f"Pag. {self.page_no()}", align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(180, 180, 180)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2)
        self.set_text_color(0, 0, 0)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-15)
        self.set_font("Arial", "I", 7)
        self.set_text_color(160, 160, 160)
        self.cell(0, 10, "Archivio di Stato di Savona  |  Marco Santoro", align="C")
        self.set_text_color(0, 0, 0)


# ── Helpers ─────────────────────────────────────────────────────────────────

BOX_DRAWING = str.maketrans({
    # Box-drawing
    "\u250c": "+", "\u2514": "+", "\u251c": "+", "\u2502": "|",
    "\u2500": "-", "\u252c": "+", "\u2518": "+", "\u2510": "+",
    "\u2524": "+", "\u253c": "+", "\u2550": "=", "\u2551": "|",
    "\u2554": "+", "\u255a": "+", "\u2566": "+", "\u2569": "+",
    "\u2560": "+", "\u2563": "+", "\u256c": "+", "\u2557": "+",
    "\u255d": "+",
    # Quotes / dashes
    "\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"',
    "\u2014": "-", "\u2013": "-", "\u2026": "...",
    # Bullets / arrows
    "\u00b7": ".", "\u2022": "*", "\u25ba": ">",
    "\u2192": "->", "\u2190": "<-", "\u2191": "^", "\u2193": "v",
    "\u21d2": "=>", "\u21d0": "<=", "\u2714": "v", "\u2718": "x",
    "\u2713": "v", "\u2717": "x", "\u2611": "[x]", "\u2610": "[ ]",
    # Misc
    "\u00a0": " ", "\u200b": "", "\ufeff": "",
})


def sanitize_latin1(text: str) -> str:
    """Sostituisce caratteri non-latin-1 con equivalenti ASCII."""
    text = text.translate(BOX_DRAWING)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def md_to_html(md_text: str) -> str:
    # Rimuovi admonitions/shortcodes MkDocs non supportati
    md_text = re.sub(r'^!!!.*$', '', md_text, flags=re.MULTILINE)
    md_text = re.sub(r'^===.*$', '', md_text, flags=re.MULTILINE)
    md_text = re.sub(r'^\s*\?{3}.*$', '', md_text, flags=re.MULTILINE)

    # Sostituisci box-drawing e caratteri speciali nel testo
    md_text = md_text.translate(BOX_DRAWING)

    html = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "toc", "nl2br"]
    )
    # Semplifica tag non supportati da fpdf2
    html = re.sub(r'<code class="[^"]*">', "<code>", html)
    html = re.sub(r'<table>', '<table border="1">', html)
    return html


def write_cover(pdf: ManualePDF):
    pdf.add_page()
    pdf.set_fill_color(63, 81, 181)  # Indigo 500
    pdf.rect(0, 0, pdf.w, pdf.h, "F")

    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 34)
    pdf.set_y(pdf.h * 0.33)
    pdf.cell(0, 18, APP_NAME, align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Arial", "", 16)
    pdf.cell(0, 10, APP_SUBTITLE, align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(12)
    pdf.set_font("Arial", "B", 15)
    pdf.cell(0, 10, "Manuale Utente", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"Versione {VERSION}", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(pdf.h - 42)
    pdf.set_font("Arial", "I", 9)
    pdf.set_text_color(200, 210, 230)
    pdf.cell(0, 6, "Marco Santoro", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "Archivio di Stato di Savona", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_text_color(0, 0, 0)


def write_chapter(pdf: ManualePDF, md_path: str):
    full_path = os.path.join(DOCS_DIR, md_path)
    if not os.path.exists(full_path):
        print(f"  [SKIP] {md_path} — file non trovato")
        return

    with open(full_path, encoding="utf-8") as f:
        content = f.read()

    if not content.strip():
        return

    html = md_to_html(content)
    pdf.add_page()

    # Tag styles: forza Arial (Unicode) anche per code/pre invece del default courier
    code_style = FontFace(family="Arial", size_pt=9)
    tag_styles = {"code": code_style, "pre": code_style}

    try:
        pdf.write_html(html, tag_styles=tag_styles)
    except Exception as e:
        print(f"  [WARN] fallback testo per {md_path}: {e}")
        plain = re.sub(r'<[^>]+>', ' ', html)
        plain = re.sub(r'\s+', ' ', plain).strip()
        # Sanifica caratteri residui per latin-1
        plain = plain.encode("latin-1", errors="replace").decode("latin-1")
        if pdf.page == 0 or pdf.get_y() > pdf.h - pdf.b_margin - 10:
            pdf.add_page()
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 5, plain)


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    print(f"Generazione PDF manuale {APP_NAME} v{VERSION}...")

    pdf = ManualePDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(20, 25, 20)
    pdf.set_auto_page_break(auto=True, margin=20)

    # Font Unicode con Arial di sistema
    if os.path.exists(FONT_R):
        pdf.add_font("Arial", "",  FONT_R)
        pdf.add_font("Arial", "B", FONT_B)
        pdf.add_font("Arial", "I", FONT_I)
        pdf.add_font("Arial", "BI", FONT_BI)
        print("  Font Arial Unicode caricati da sistema.")
    else:
        print("  [WARN] Font Arial non trovati — uso Helvetica (caratteri non-latin-1 potrebbero mancare)")

    pdf.set_title(f"Manuale Utente {APP_NAME} v{VERSION}")
    pdf.set_author("Marco Santoro")
    pdf.set_creator("fpdf2")

    write_cover(pdf)

    for rel_path in NAV_FILES:
        print(f"  Capitolo: {rel_path}")
        write_chapter(pdf, rel_path)

    pdf.output(OUTPUT_FILE)
    size_kb = os.path.getsize(OUTPUT_FILE) // 1024
    print(f"\nPDF generato: {OUTPUT_FILE}  ({size_kb} KB)")


if __name__ == "__main__":
    main()
