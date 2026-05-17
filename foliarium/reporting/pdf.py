"""
foliarium/reporting/pdf.py — Classi PDF per i report di Foliarium.

Estratto da app_utils.py (Sprint 3 refactor — six-hats).

Espone:
    FPDF_AVAILABLE   — True se fpdf2 e' installato
    ModernCatastoPDF — classe base con palette, header, footer, layout
    PDFPartita       — report dettaglio singola partita catastale
    PDFPossessore    — report dettaglio singolo possessore
    GenericTextReportPDF — report testuale generico (Courier, sfondo grigio)
    BulkReportPDF    — report tabellare landscape con header ripetuto

In ambienti senza fpdf2 (CI minimale, build privi della dipendenza opzionale)
vengono esportati stub vuoti per preservare gli import dei chiamanti, in
modo simmetrico a quanto faceva storicamente app_utils.py.
"""

from __future__ import annotations

import logging

_log = logging.getLogger("CatastoGUI.reporting.pdf")


try:
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False
    class FPDF:  # type: ignore[no-redef]
        pass
    XPos = YPos = None  # type: ignore[assignment]


if FPDF_AVAILABLE:

    class ModernCatastoPDF(FPDF):
        """Base class condivisa per tutti i report PDF di Foliarium."""

        APP_NAME  = "Foliarium - Archivio Catastale Storico"
        C_HEADER  = (26,  54,  93)
        C_SECTION = (41,  98, 155)
        C_WHITE   = (255, 255, 255)
        C_ALT_ROW = (232, 241, 252)
        C_LABEL   = (105, 105, 105)
        C_VALUE   = (25,  25,  25)
        C_FOOTER  = (155, 155, 155)
        C_ACCENT  = (41,  98, 155)

        def __init__(self, report_title="Report", orientation='P', unit='mm', format='A4'):
            super().__init__(orientation, unit, format)
            self.report_title = report_title
            self._logo_path = None
            try:
                from app_paths import get_logo_path
                lp = get_logo_path()
                if lp and lp.exists():
                    self._logo_path = str(lp)
            except Exception as _e:
                _log.debug("Logo PDF non caricato: %s", _e)
            self.set_auto_page_break(auto=True, margin=18)
            self.set_left_margin(15)
            self.set_right_margin(15)

        def header(self):
            self.set_fill_color(*self.C_HEADER)
            self.rect(0, 0, self.w, 18, 'F')
            logo_x = 4
            if self._logo_path:
                try:
                    self.image(self._logo_path, x=logo_x, y=2, h=14)
                    logo_x = 22
                except Exception as _e:
                    _log.debug("Impossibile incorporare logo nell'header PDF: %s", _e)
            self.set_xy(logo_x, 3)
            self.set_font('Helvetica', 'B', 10)
            self.set_text_color(*self.C_WHITE)
            self.cell(self.w - logo_x - 30, 6, self.APP_NAME, align='L')
            from datetime import date as _d
            self.set_xy(0, 3)
            self.set_font('Helvetica', '', 8)
            self.set_text_color(190, 210, 235)
            self.cell(self.w - self.r_margin, 6, _d.today().strftime('%d/%m/%Y'), align='R')
            self.set_xy(logo_x, 11)
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(190, 210, 235)
            self.cell(self.w - logo_x - self.r_margin, 5, self.report_title, align='L')
            self.set_text_color(*self.C_VALUE)
            self.set_y(23)

        def footer(self):
            self.set_y(-13)
            y = self.get_y()
            self.set_draw_color(*self.C_ACCENT)
            self.set_line_width(0.3)
            self.line(self.l_margin, y, self.w - self.r_margin, y)
            self.set_line_width(0.2)
            self.ln(1)
            pw = self.w - self.l_margin - self.r_margin
            self.set_font('Helvetica', 'I', 7)
            self.set_text_color(*self.C_FOOTER)
            self.cell(pw * 0.78, 5,
                      "Il presente report ha valore puramente storico e documentale.",
                      align='L')
            self.set_font('Helvetica', '', 7)
            self.cell(0, 5, f'Pag. {self.page_no()}/{{nb}}', align='R')
            self.set_draw_color(0, 0, 0)
            self.set_text_color(*self.C_VALUE)

        def cover_block(self, title, note=None, chips=None):
            pw = self.w - self.l_margin - self.r_margin
            n_extra = (1 if note else 0) + (1 if chips else 0)
            block_h = 8 + n_extra * 7 + 6
            sy = self.get_y()
            self.set_fill_color(*self.C_ALT_ROW)
            self.rect(self.l_margin, sy, pw, block_h, 'F')
            self.set_fill_color(*self.C_SECTION)
            self.rect(self.l_margin, sy, 3.5, block_h, 'F')
            cx = self.l_margin + 7
            self.set_xy(cx, sy + 4)
            self.set_font('Helvetica', 'B', 13)
            self.set_text_color(*self.C_SECTION)
            self.cell(pw - 7, 8, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_x(cx)
            if note:
                self.set_font('Helvetica', '', 9)
                self.set_text_color(*self.C_LABEL)
                self.cell(pw - 7, 6, note, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self.set_x(cx)
            if chips:
                self.set_font('Helvetica', '', 9)
                self.set_text_color(*self.C_LABEL)
                chips_text = '    |    '.join(
                    f"{lbl}: {val}"
                    for lbl, val in chips
                    if val is not None and val != ''
                )
                self.cell(pw - 7, 6, chips_text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_text_color(*self.C_VALUE)
            self.set_y(sy + block_h + 5)

        def section_title(self, title):
            self.ln(3)
            pw = self.w - self.l_margin - self.r_margin
            self.set_fill_color(*self.C_SECTION)
            self.set_text_color(*self.C_WHITE)
            self.set_font('Helvetica', 'B', 10)
            self.cell(pw, 7, f'  {title}', fill=True,
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_text_color(*self.C_VALUE)
            self.ln(2)

        def info_block(self, data_dict):
            pw  = self.w - self.l_margin - self.r_margin
            lw  = pw * 0.36
            vw  = pw - lw
            self.set_draw_color(210, 220, 230)
            self.set_line_width(0.1)
            for key, value in data_dict.items():
                label   = key.replace('_', ' ').title()
                val_str = str(value) if value is not None else 'N/D'
                self.set_font('Helvetica', 'B', 9)
                self.set_text_color(*self.C_LABEL)
                self.cell(lw, 6, label, border='B',
                          new_x=XPos.RIGHT, new_y=YPos.TOP)
                self.set_font('Helvetica', '', 9)
                self.set_text_color(*self.C_VALUE)
                try:
                    self.multi_cell(vw, 6, val_str, border='B',
                                    new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                except Exception:
                    self.multi_cell(vw, 6, '[valore non visualizzabile]', border='B',
                                    new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_draw_color(0, 0, 0)
            self.set_line_width(0.2)
            self.ln(3)

        def styled_table(self, headers, data_rows, col_widths_percent=None):
            pw = self.w - self.l_margin - self.r_margin
            if col_widths_percent:
                col_widths = [pw * p / 100 for p in col_widths_percent]
            else:
                n = len(headers) or 1
                col_widths = [pw / n] * len(headers)
            self.set_fill_color(*self.C_SECTION)
            self.set_text_color(*self.C_WHITE)
            self.set_font('Helvetica', 'B', 8)
            for i, h in enumerate(headers):
                is_last = i == len(headers) - 1
                self.cell(col_widths[i], 7, h, fill=True, align='C',
                          new_x=XPos.LMARGIN if is_last else XPos.RIGHT,
                          new_y=YPos.NEXT    if is_last else YPos.TOP)
            self.set_font('Helvetica', '', 8)
            for row_i, row in enumerate(data_rows):
                self.set_fill_color(*(self.C_ALT_ROW if row_i % 2 else self.C_WHITE))
                self.set_text_color(*self.C_VALUE)
                for i, item in enumerate(row):
                    is_last = i == len(row) - 1
                    text = str(item) if item is not None else ''
                    self.cell(col_widths[i], 6, text, fill=True, align='L',
                              new_x=XPos.LMARGIN if is_last else XPos.RIGHT,
                              new_y=YPos.NEXT    if is_last else YPos.TOP)
            self.set_draw_color(*self.C_ACCENT)
            self.set_line_width(0.5)
            self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
            self.set_line_width(0.2)
            self.set_draw_color(0, 0, 0)
            self.ln(4)

        def chapter_title(self, title):
            self.section_title(title)

        def chapter_body(self, data_dict):
            self.info_block(data_dict)

        def simple_table(self, headers, data_rows, col_widths_percent=None):
            self.styled_table(headers, data_rows, col_widths_percent)


    class PDFPartita(ModernCatastoPDF):
        def __init__(self):
            super().__init__(report_title="Dettaglio Partita Catastale")


    class PDFPossessore(ModernCatastoPDF):
        def __init__(self):
            super().__init__(report_title="Dettaglio Possessore Catastale")


    class GenericTextReportPDF(ModernCatastoPDF):
        def __init__(self, orientation='P', unit='mm', format='A4', report_title="Report"):
            super().__init__(report_title=report_title, orientation=orientation,
                             unit=unit, format=format)

        def add_report_text(self, text_content: str):
            """Aggiunge testo preformattato con sfondo grigio chiaro."""
            text_content = text_content.replace('\t', '    ')
            pw = self.w - self.l_margin - self.r_margin
            self.set_fill_color(248, 249, 250)
            self.set_font('Courier', '', 8)
            self.set_text_color(*self.C_VALUE)
            self.multi_cell(pw, 5, text_content, fill=True,
                            new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln()


    class BulkReportPDF(ModernCatastoPDF):
        """Report tabellare bulk in formato landscape con intestazioni ripetute."""

        def __init__(self, orientation='L', unit='mm', format='A4', report_title="Report Dati"):
            super().__init__(report_title=report_title, orientation=orientation,
                             unit=unit, format=format)
            self.headers    = []
            self.col_widths = []

        def header(self):
            self.set_fill_color(*self.C_HEADER)
            self.rect(0, 0, self.w, 16, 'F')
            self.set_xy(8, 4)
            self.set_font('Helvetica', 'B', 10)
            self.set_text_color(*self.C_WHITE)
            self.cell(self.w - 50, 6, f'{self.APP_NAME}  |  {self.report_title}', align='L')
            from datetime import date as _d
            self.set_xy(0, 4)
            self.set_font('Helvetica', '', 8)
            self.set_text_color(190, 210, 235)
            self.cell(self.w - self.r_margin, 6, _d.today().strftime('%d/%m/%Y'), align='R')
            self.set_text_color(*self.C_VALUE)
            if self.headers and self.col_widths:
                self.set_y(20)
                self.set_fill_color(*self.C_SECTION)
                self.set_text_color(*self.C_WHITE)
                self.set_font('Helvetica', 'B', 8)
                for i, h in enumerate(self.headers):
                    is_last = i == len(self.headers) - 1
                    self.cell(self.col_widths[i], 7, h, fill=True, align='C',
                              new_x=XPos.LMARGIN if is_last else XPos.RIGHT,
                              new_y=YPos.NEXT    if is_last else YPos.TOP)
                self.set_text_color(*self.C_VALUE)
            else:
                self.set_y(21)

        def print_table(self, headers, data):
            if not data:
                return
            self.headers = headers
            ew = self.w - self.l_margin - self.r_margin
            self.col_widths = [ew / len(headers)] * len(headers)
            self.set_font('Helvetica', '', 8)
            self.add_page()
            for row_i, row in enumerate(data):
                if self.get_y() + 6 > self.page_break_trigger:
                    self.add_page()
                self.set_fill_color(*(self.C_ALT_ROW if row_i % 2 else self.C_WHITE))
                self.set_text_color(*self.C_VALUE)
                for i, header in enumerate(headers):
                    cell_value = (str(row.get(header, '')) if isinstance(row, dict)
                                  else (str(row[i]) if i < len(row) else ''))
                    is_last = i == len(headers) - 1
                    self.cell(self.col_widths[i], 6, cell_value, fill=True, align='L',
                              new_x=XPos.LMARGIN if is_last else XPos.RIGHT,
                              new_y=YPos.NEXT    if is_last else YPos.TOP)

else:
    # Stub di fallback se fpdf2 non e' installato. Mantengono gli import dei
    # chiamanti funzionanti (controlleranno FPDF_AVAILABLE prima di istanziare).
    class ModernCatastoPDF:  # type: ignore[no-redef]
        pass

    class PDFPartita:  # type: ignore[no-redef]
        pass

    class PDFPossessore:  # type: ignore[no-redef]
        pass

    class GenericTextReportPDF:  # type: ignore[no-redef]
        pass

    class BulkReportPDF:  # type: ignore[no-redef]
        pass


__all__ = [
    "FPDF_AVAILABLE",
    "ModernCatastoPDF",
    "PDFPartita",
    "PDFPossessore",
    "GenericTextReportPDF",
    "BulkReportPDF",
]
