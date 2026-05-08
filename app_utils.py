import logging
import socket
import json
import csv
import os
from datetime import date, datetime
from typing import Optional, List, Dict, Any

from PyQt6.QtCore import QStandardPaths
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QDialog, QFileDialog, QMessageBox

from catasto_db_manager import CatastoDBManager
from foliarium.ui.dialogs.export_ import PDFApreviewDialog, CSVApreviewDialog  # noqa: F401


# Importa FPDF e le sue utility, che ora funzioneranno grazie a fpdf2
try:
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos # Ora possiamo re-importare e usare questi
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False
    # Definizioni fallback
    class FPDF: pass
    class PDFPartita: pass
    class PDFPossessore: pass
    class GenericTextReportPDF: pass
    class BulkReportPDF: pass

# --- Funzioni Helper ---
# All'inizio di app_utils.py
try:
    import keyring
except ImportError:
    keyring = None
    logging.warning("Libreria 'keyring' non trovata. Salvataggio sicuro password non disponibile.")


# --- Classi PDF (versione moderna con new_x e new_y) ---

if FPDF_AVAILABLE:
    # ── Palette colori istituzionale ────────────────────────────────────────
    class ModernCatastoPDF(FPDF):
        """Base class condivisa per tutti i report PDF di Foliarium."""

        APP_NAME  = "Foliarium - Archivio Catastale Storico"
        C_HEADER  = (26,  54,  93)   # navy scuro  — banda header
        C_SECTION = (41,  98, 155)   # blu medio   — titoli sezione / header tabella
        C_WHITE   = (255, 255, 255)
        C_ALT_ROW = (232, 241, 252)  # azzurro chiarissimo — righe alternate
        C_LABEL   = (105, 105, 105)  # grigio — etichette campo
        C_VALUE   = (25,  25,  25)   # quasi-nero — valori
        C_FOOTER  = (155, 155, 155)  # grigio chiaro — testo footer
        C_ACCENT  = (41,  98, 155)   # linea separatrice

        def __init__(self, report_title="Report", orientation='P', unit='mm', format='A4'):
            super().__init__(orientation, unit, format)
            self.report_title = report_title
            self._logo_path = None
            try:
                from app_paths import get_logo_path
                lp = get_logo_path()
                if lp and lp.exists():
                    self._logo_path = str(lp)
            except Exception:
                pass
            self.set_auto_page_break(auto=True, margin=18)
            self.set_left_margin(15)
            self.set_right_margin(15)

        def header(self):
            # Banda colorata
            self.set_fill_color(*self.C_HEADER)
            self.rect(0, 0, self.w, 18, 'F')
            # Logo (se disponibile)
            logo_x = 4
            if self._logo_path:
                try:
                    self.image(self._logo_path, x=logo_x, y=2, h=14)
                    logo_x = 22
                except Exception:
                    pass
            # Nome applicazione
            self.set_xy(logo_x, 3)
            self.set_font('Helvetica', 'B', 10)
            self.set_text_color(*self.C_WHITE)
            self.cell(self.w - logo_x - 30, 6, self.APP_NAME, align='L')
            # Data (destra)
            from datetime import date as _d
            self.set_xy(0, 3)
            self.set_font('Helvetica', '', 8)
            self.set_text_color(190, 210, 235)
            self.cell(self.w - self.r_margin, 6, _d.today().strftime('%d/%m/%Y'), align='R')
            # Titolo report (riga secondaria)
            self.set_xy(logo_x, 11)
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(190, 210, 235)
            self.cell(self.w - logo_x - self.r_margin, 5, self.report_title, align='L')
            # Reset
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

        # ── Blocco riepilogativo iniziale ──────────────────────────────────
        def cover_block(self, title, note=None, chips=None):
            """
            Riquadro in evidenza con barra laterale colorata.
              title : stringa principale es. "PARTITA N. 1234/A — Savona"
              note  : riga secondaria es. "Tipo: Urbano  •  Stato: Attivo"
              chips : lista di tuple (label, value) per info compatte
            """
            pw = self.w - self.l_margin - self.r_margin
            n_extra = (1 if note else 0) + (1 if chips else 0)
            block_h = 8 + n_extra * 7 + 6
            sy = self.get_y()
            # Sfondo azzurro chiaro
            self.set_fill_color(*self.C_ALT_ROW)
            self.rect(self.l_margin, sy, pw, block_h, 'F')
            # Barra sinistra blu
            self.set_fill_color(*self.C_SECTION)
            self.rect(self.l_margin, sy, 3.5, block_h, 'F')
            cx = self.l_margin + 7
            self.set_xy(cx, sy + 4)
            # Titolo principale
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

        # ── Titolo sezione ─────────────────────────────────────────────────
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

        # ── Coppie chiave-valore ───────────────────────────────────────────
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

        # ── Tabella con righe alternate ────────────────────────────────────
        def styled_table(self, headers, data_rows, col_widths_percent=None):
            pw = self.w - self.l_margin - self.r_margin
            if col_widths_percent:
                col_widths = [pw * p / 100 for p in col_widths_percent]
            else:
                n = len(headers) or 1
                col_widths = [pw / n] * len(headers)
            # Intestazione
            self.set_fill_color(*self.C_SECTION)
            self.set_text_color(*self.C_WHITE)
            self.set_font('Helvetica', 'B', 8)
            for i, h in enumerate(headers):
                is_last = i == len(headers) - 1
                self.cell(col_widths[i], 7, h, fill=True, align='C',
                          new_x=XPos.LMARGIN if is_last else XPos.RIGHT,
                          new_y=YPos.NEXT    if is_last else YPos.TOP)
            # Righe dati
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
            # Linea di chiusura
            self.set_draw_color(*self.C_ACCENT)
            self.set_line_width(0.5)
            self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
            self.set_line_width(0.2)
            self.set_draw_color(0, 0, 0)
            self.ln(4)

        # ── Alias di compatibilità con il codice chiamante ─────────────────
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
if FPDF_AVAILABLE:
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

def get_local_ip_address():
    """
    Ottiene l'indirizzo IP locale della macchina con cui si esce sulla rete.
    """
    try:
        # Crea un socket UDP (non invia dati reali) per determinare l'IP di uscita
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        # 8.8.8.8 è il DNS di Google, un endpoint affidabile per questo scopo
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
    except Exception:
        # Se non c'è connessione di rete o si verifica un errore, usa il fallback
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except socket.gaierror:
            ip = '127.0.0.1'
    finally:
        if 's' in locals():
            s.close()
    return ip

def gui_esporta_partita_json(parent_widget, db_manager: CatastoDBManager, partita_id: int):
    # Recupera i dati usando il metodo del db_manager che restituisce il dizionario completo
    # Questo metodo è get_partita_data_for_export, NON export_partita_json
    dict_data = db_manager.get_partita_data_for_export(partita_id)

    if dict_data:
        def json_serial(obj):
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

        try:
            json_data_str = json.dumps(
                dict_data, indent=4, ensure_ascii=False, default=json_serial)
        except TypeError as te:
            logging.getLogger("CatastoGUI").error(
                f"Errore di serializzazione JSON per partita ID {partita_id}: {te} - Dati: {dict_data}")
            QMessageBox.critical(parent_widget, "Errore di Serializzazione",
                                 f"Errore durante la conversione dei dati della partita in JSON: {te}\n"
                                 "Controllare i log per i dettagli.")
            return

        default_filename_base = f"partita_{partita_id}_{date.today().isoformat()}.json"
        full_default_path = _get_default_export_path(default_filename_base)
        filename, _ = QFileDialog.getSaveFileName(
            parent_widget, "Salva JSON Partita", full_default_path, "JSON Files (*.json)")

        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(json_data_str)
                QMessageBox.information(
                    parent_widget, "Esportazione JSON", f"Partita esportata con successo in:\n{filename}")
            except Exception as e:
                logging.getLogger("CatastoGUI").error(
                    f"Errore durante il salvataggio del file JSON per partita ID {partita_id}: {e}")
                QMessageBox.critical(parent_widget, "Errore Esportazione",
                                     f"Errore durante il salvataggio del file JSON:\n{e}")
    else:
        QMessageBox.warning(parent_widget, "Errore Dati",
                            f"Partita con ID {partita_id} non trovata o errore nel recupero dei dati per l'esportazione.")


def gui_esporta_partita_csv(parent_widget, db_manager: CatastoDBManager, partita_id: int):
    partita_data = db_manager.get_partita_data_for_export(partita_id)
    if not partita_data or 'partita' not in partita_data:
        QMessageBox.warning(parent_widget, "Errore Dati",
                            "Dati partita non validi per l'esportazione CSV.")
        return
    # --- LOGICA ANTEPRIMA CSV ---
    preview_headers = ["Sezione", "Campo", "Valore"]
    preview_data_rows = []
    MAX_ROWS_PREVIEW_SECTION = 3 # Mostra solo le prime N righe per sezione nella preview

    # Dettagli Partita
    p_details = partita_data.get('partita', {})
    for k, v in p_details.items():
        preview_data_rows.append(["Partita", k.replace('_', ' ').title(), v])

    # Possessori (prime N)
    if partita_data.get('possessori'):
        preview_data_rows.append(["---", "--- Possessori ---", "---"])
        poss_headers = list(partita_data['possessori'][0].keys()) if partita_data['possessori'] else []
        preview_data_rows.append(["Possessori", "Intestazioni", ", ".join([h.replace('_', ' ').title() for h in poss_headers])])
        for i, pos in enumerate(partita_data['possessori']):
            if i >= MAX_ROWS_PREVIEW_SECTION:
                preview_data_rows.append(["Possessori", f"...e altri {len(partita_data['possessori']) - MAX_ROWS_PREVIEW_SECTION}...", ""])
                break
            preview_data_rows.append(["Possessori", f"Possessore {i+1}", ", ".join([str(pos.get(h, '')) for h in poss_headers])])

    preview_dialog = CSVApreviewDialog(preview_headers, preview_data_rows, parent_widget,
                                       title=f"Anteprima CSV - Partita ID {partita_id}")
    if preview_dialog.exec() != QDialog.DialogCode.Accepted:
        logging.getLogger("CatastoGUI").info(f"Esportazione CSV per partita ID {partita_id} annullata dall'utente dopo anteprima.")
        return
    # --- FINE LOGICA ANTEPRIMA CSV ---
    
    default_filename = f"partita_{partita_id}_{date.today()}.csv"
    # 2. Usa la nuova funzione per ottenere il percorso completo di default
    full_default_path = _get_default_export_path(default_filename)
    filename, _ = QFileDialog.getSaveFileName(
        parent_widget, "Salva CSV Partita", full_default_path, "CSV Files (*.csv)")
    if not filename:
        return

    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            p = partita_data['partita']
            writer.writerow(['--- DETTAGLI PARTITA ---'])
            for key, value in p.items():
                writer.writerow([key.replace('_', ' ').title(), value])
            writer.writerow([])

            if partita_data.get('possessori'):
                writer.writerow(['--- POSSESSORI ---'])
                headers = list(partita_data['possessori'][0].keys(
                )) if partita_data['possessori'] else []
                if headers:
                    writer.writerow([h.replace('_', ' ').title()
                                    for h in headers])
                for pos in partita_data['possessori']:
                    writer.writerow([pos.get(h) for h in headers])
                writer.writerow([])

            if partita_data.get('immobili'):
                writer.writerow(['--- IMMOBILI ---'])
                headers = list(partita_data['immobili'][0].keys(
                )) if partita_data['immobili'] else []
                if headers:
                    writer.writerow([h.replace('_', ' ').title()
                                    for h in headers])
                for imm in partita_data['immobili']:
                    writer.writerow([imm.get(h) for h in headers])
                writer.writerow([])

            if partita_data.get('variazioni'):
                writer.writerow(['--- VARIAZIONI ---'])
                headers = list(partita_data['variazioni'][0].keys(
                )) if partita_data['variazioni'] else []
                if headers:
                    writer.writerow([h.replace('_', ' ').title()
                                    for h in headers])
                for var in partita_data['variazioni']:
                    writer.writerow([var.get(h) for h in headers])
        QMessageBox.information(parent_widget, "Esportazione CSV",
                                f"Partita esportata con successo in:\n{filename}")
    except Exception as e:
        QMessageBox.critical(parent_widget, "Errore Esportazione",
                             f"Errore durante l'esportazione CSV:\n{e}")


def gui_esporta_partita_pdf(parent_widget, db_manager: CatastoDBManager, partita_id: int):
    if not FPDF_AVAILABLE:
        QMessageBox.warning(parent_widget, "Funzionalità non disponibile",
                            "La libreria FPDF è necessaria per l'esportazione in PDF, ma non è installata.")
        return

    partita_data = db_manager.get_partita_data_for_export(partita_id)
    if not partita_data or 'partita' not in partita_data:
        QMessageBox.warning(parent_widget, "Errore Dati",
                            "Dati partita non validi per l'esportazione PDF.")
        return
    # --- LOGICA ANTEPRIMA TESTUALE PDF ---
    # Genera una stringa di anteprima (puoi riutilizzare la logica dei report testuali)
    # o creare una versione semplificata della struttura PDF.
    # Qui, per esempio, potremmo usare il report testuale del report di proprietà.
    # ATTENZIONE: genera_report_proprieta è un metodo di db_manager che restituisce una stringa SQL,
    # non il testo del report. Dobbiamo simulare il contenuto testuale che andrà nel PDF.
    
    preview_text_content = f"ANTEPRIMA PDF - Partita ID: {partita_id}\n"
    preview_text_content += "======================================\n\n"
    p_details = partita_data.get('partita', {})
    preview_text_content += "Dettagli Partita:\n"
    for key, value in p_details.items():
        preview_text_content += f"  {key.replace('_', ' ').title()}: {value if value is not None else 'N/D'}\n"
    preview_text_content += "\n"

    if partita_data.get('possessori'):
        preview_text_content += "Possessori (primi 2):\n"
        for i, pos in enumerate(partita_data['possessori'][:2]):
            preview_text_content += f"  - ID: {pos.get('id')}, Nome: {pos.get('nome_completo')}, Titolo: {pos.get('titolo')}, Quota: {pos.get('quota', 'N/D')}\n"
        if len(partita_data['possessori']) > 2:
            preview_text_content += "  ...e altri.\n"
    preview_text_content += "\n"

    preview_dialog = PDFApreviewDialog(preview_text_content, parent_widget,
                                       title=f"Anteprima PDF - Partita ID {partita_id}")
    if preview_dialog.exec() != QDialog.DialogCode.Accepted:
        logging.getLogger("CatastoGUI").info(f"Esportazione PDF per partita ID {partita_id} annullata dall'utente dopo anteprima.")
        return
    # --- FINE LOGICA ANTEPRIMA TESTUALE PDF ---
    default_filename = f"partita_{partita_id}_{date.today()}.pdf"
    full_default_path = _get_default_export_path(default_filename)
    filename, _ = QFileDialog.getSaveFileName(
        parent_widget, "Salva PDF Partita", full_default_path, "PDF Files (*.pdf)")
    if not filename:
        return

    try:
        pdf = PDFPartita()
        pdf.alias_nb_pages()
        pdf.add_page()

        p = partita_data['partita']
        # ── Blocco riepilogativo in evidenza ──────────────────────────────
        num_display = f"N. {p.get('numero_partita', '')}"
        if p.get('suffisso_partita'):
            num_display += f"/{p.get('suffisso_partita')}"
        pdf.cover_block(
            title=f"PARTITA CATASTALE {num_display} - {p.get('comune_nome', '')}",
            note=f"Tipo: {p.get('tipo', 'N/D')}   •   Stato: {p.get('stato', 'N/D')}",
            chips=[
                ("Data impianto", p.get('data_impianto')),
                ("Provenienza N.", p.get('numero_provenienza')),
                ("ID", p.get('id')),
            ]
        )
        # ─────────────────────────────────────────────────────────────────

        pdf.chapter_title('Dettagli Partita')
        campi_da_visualizzare = [
            'id', 'comune_nome', 'numero_partita', 'suffisso_partita',
            'tipo', 'data_impianto', 'stato', 'data_chiusura', 'numero_provenienza'
        ]
        pdf.chapter_body({k: p.get(k) for k in campi_da_visualizzare})

        if partita_data.get('possessori'):
            pdf.chapter_title('Possessori')
            headers = ['ID', 'Nome Completo', 'Titolo', 'Quota']
            data_rows = [[pos.get('id'), pos.get('nome_completo'), pos.get(
                'titolo'), pos.get('quota')] for pos in partita_data['possessori']]
            pdf.simple_table(headers, data_rows)

        if partita_data.get('immobili'):
            pdf.chapter_title('Immobili')
            headers = ['ID', 'Natura', 'Località', 'Class.', 'Consist.']
            data_rows = [[imm.get('id'), imm.get('natura'), imm.get('localita_nome', ''),
                         imm.get('classificazione'), imm.get('consistenza')] for imm in partita_data['immobili']]
            pdf.simple_table(headers, data_rows)

        if partita_data.get('variazioni'):
            pdf.chapter_title('Variazioni')
            headers = ['ID', 'Tipo', 'Data Var.', 'Contratto', 'Notaio']
            data_rows = []
            for var in partita_data['variazioni']:
                contr_str = f"{var.get('contratto_tipo', '')} del {var.get('data_contratto', '')}" if var.get(
                    'contratto_tipo') else ''
                data_rows.append([var.get('id'), var.get('tipo'), var.get(
                    'data_variazione'), contr_str, var.get('notaio')])
            pdf.simple_table(headers, data_rows)

        pdf.output(filename)
        prompt_to_open_file(parent_widget, filename)
    except Exception as e:
        logging.getLogger("CatastoGUI").exception(
            "Errore esportazione PDF partita (GUI)")
        QMessageBox.critical(parent_widget, "Errore Esportazione",
                             f"Errore durante l'esportazione PDF:\n{e}")


def gui_esporta_possessore_json(parent_widget, db_manager: CatastoDBManager, possessore_id: int):
    dict_data = db_manager.get_possessore_data_for_export(possessore_id)
    if dict_data:
        json_data_str = json.dumps(dict_data, indent=4, ensure_ascii=False)
        default_filename = f"possessore_{possessore_id}_{date.today()}.json"
        filename, _ = QFileDialog.getSaveFileName(
            parent_widget, "Salva JSON Possessore", default_filename, "JSON Files (*.json)")
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(json_data_str)
                QMessageBox.information(
                    parent_widget, "Esportazione JSON", f"Possessore esportato con successo in:\n{filename}")
            except Exception as e:
                QMessageBox.critical(parent_widget, "Errore Esportazione",
                                     f"Errore durante il salvataggio del file JSON:\n{e}")
    else:
        QMessageBox.warning(parent_widget, "Errore Dati",
                            f"Possessore con ID {possessore_id} non trovato o errore recupero dati.")


def gui_esporta_possessore_csv(parent_widget, db_manager: CatastoDBManager, possessore_id: int):
    possessore_data = db_manager.get_possessore_data_for_export(possessore_id)
    if not possessore_data or 'possessore' not in possessore_data:
        QMessageBox.warning(parent_widget, "Errore Dati",
                            "Dati possessore non validi per l'esportazione CSV.")
        return

    # --- NUOVA SEZIONE: Logica di Anteprima per CSV ---
    preview_headers = ["Sezione", "Campo", "Valore"]
    preview_data_rows = []
    MAX_ROWS_PREVIEW_SECTION = 3 # Mostra solo le prime N righe per sezione nell'anteprima

    # Dettagli Possessore
    p_details = possessore_data.get('possessore', {})
    for k, v in p_details.items():
        preview_data_rows.append(["Possessore", k.replace('_', ' ').title(), v])

    # Partite Associate (prime N)
    if possessore_data.get('partite'):
        preview_data_rows.append(["---", "--- Partite Associate ---", "---"])
        partite_headers = list(possessore_data['partite'][0].keys()) if possessore_data['partite'] else []
        preview_data_rows.append(["Partite", "Intestazioni", ", ".join([h.replace('_', ' ').title() for h in partite_headers])])
        
        for i, partita in enumerate(possessore_data['partite']):
            if i >= MAX_ROWS_PREVIEW_SECTION:
                preview_data_rows.append(["Partite", f"...e altre {len(possessore_data['partite']) - MAX_ROWS_PREVIEW_SECTION}...", ""])
                break
            # Crea una stringa riassuntiva per la riga di anteprima
            row_summary = f"N.{partita.get('numero_partita', '?')} ({partita.get('comune_nome', '?')}), Titolo: {partita.get('titolo', 'N/D')}"
            preview_data_rows.append(["Partite", f"Partita {i+1}", row_summary])
    

    preview_dialog = CSVApreviewDialog(preview_headers, preview_data_rows, parent_widget,
                                       title=f"Anteprima CSV - Possessore ID {possessore_id}")
    if preview_dialog.exec() != QDialog.DialogCode.Accepted:
        logging.getLogger("CatastoGUI").info(f"Esportazione CSV per possessore ID {possessore_id} annullata dall'utente.")
        return
    # --- FINE Logica di Anteprima ---

    default_filename = f"possessore_{possessore_id}_{date.today()}.csv"
    full_default_path = _get_default_export_path(default_filename)
    filename, _ = QFileDialog.getSaveFileName(
        parent_widget, "Salva CSV Possessore", full_default_path, "CSV Files (*.csv)")
    if not filename:
        return

    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            p_info = possessore_data['possessore']
            writer.writerow(['--- DETTAGLI POSSESSORE ---'])
            for key, value in p_info.items():
                writer.writerow([key.replace('_', ' ').title(), value])
            writer.writerow([])

            if possessore_data.get('partite'):
                writer.writerow(['--- PARTITE ASSOCIATE ---'])
                headers = list(possessore_data['partite'][0].keys()) if possessore_data['partite'] else []
                if headers:
                    writer.writerow([h.replace('_', ' ').title() for h in headers])
                for part in possessore_data['partite']:
                    writer.writerow([part.get(h) for h in headers])
                writer.writerow([])

            if possessore_data.get('immobili'):
                writer.writerow(['--- IMMOBILI ASSOCIATI (TRAMITE PARTITE) ---'])
                headers = list(possessore_data['immobili'][0].keys()) if possessore_data['immobili'] else []
                if headers:
                    writer.writerow([h.replace('_', ' ').title() for h in headers])
                for imm in possessore_data['immobili']:
                    writer.writerow([imm.get(h) for h in headers])

        QMessageBox.information(parent_widget, "Esportazione CSV",
                                f"Possessore esportato con successo in:\n{filename}")
    except Exception as e:
        QMessageBox.critical(parent_widget, "Errore Esportazione",
                             f"Errore durante l'esportazione CSV:\n{e}")


def gui_esporta_possessore_pdf(parent_widget, db_manager: CatastoDBManager, possessore_id: int):
    if not FPDF_AVAILABLE:
        QMessageBox.warning(parent_widget, "Funzionalità non disponibile",
                            "La libreria FPDF è necessaria per l'esportazione in PDF, ma non è installata.")
        return

    possessore_data = db_manager.get_possessore_data_for_export(possessore_id)
    if not possessore_data or 'possessore' not in possessore_data:
        QMessageBox.warning(parent_widget, "Errore Dati",
                            "Dati possessore non validi per l'esportazione PDF.")
        return

    # --- NUOVA SEZIONE: Logica di Anteprima per PDF ---
    preview_text_content = f"ANTEPRIMA PDF - Possessore ID: {possessore_id}\n"
    preview_text_content += "========================================\n\n"
    
    p_details = possessore_data.get('possessore', {})
    preview_text_content += "Dettagli Possessore:\n"
    for key, value in p_details.items():
        preview_text_content += f"  {key.replace('_', ' ').title()}: {value if value is not None else 'N/D'}\n"
    preview_text_content += "\n"

    if possessore_data.get('partite'):
        preview_text_content += "Partite Associate (prime 3):\n"
        for i, partita in enumerate(possessore_data['partite'][:3]):
            preview_text_content += (f"  - Partita N.{partita.get('numero_partita', '?')} "
                                     f"({partita.get('comune_nome', '?')}) - "
                                     f"Titolo: {partita.get('titolo', 'N/D')}, Quota: {partita.get('quota', 'N/D')}\n")
        if len(possessore_data['partite']) > 3:
            preview_text_content += "  ...e altre.\n"
    preview_text_content += "\n"

    
    preview_dialog = PDFApreviewDialog(preview_text_content, parent_widget,
                                       title=f"Anteprima PDF - Possessore ID {possessore_id}")
    if preview_dialog.exec() != QDialog.DialogCode.Accepted:
        logging.getLogger("CatastoGUI").info(f"Esportazione PDF per possessore ID {possessore_id} annullata dall'utente.")
        return
    # --- FINE Logica di Anteprima ---

    default_filename = f"possessore_{possessore_id}_{date.today()}.pdf"
    full_default_path = _get_default_export_path(default_filename)
    filename, _ = QFileDialog.getSaveFileName(
        parent_widget, "Salva PDF Possessore", full_default_path, "PDF Files (*.pdf)")
    if not filename:
        return

    try:
        pdf = PDFPossessore()
        pdf.alias_nb_pages()
        pdf.add_page()

        p_info = possessore_data['possessore']
        # ── Blocco riepilogativo in evidenza ──────────────────────────────
        nome = p_info.get('nome_completo') or p_info.get('cognome_nome', 'N/D')
        stato_str = "Attivo" if p_info.get('attivo') else "Non attivo"
        pdf.cover_block(
            title=f"POSSESSORE - {nome}",
            note=f"Stato: {stato_str}   •   Comune: {p_info.get('comune_nome', 'N/D')}",
            chips=[
                ("Paternità", p_info.get('paternita')),
                ("ID", p_info.get('id')),
            ]
        )
        # ─────────────────────────────────────────────────────────────────

        pdf.chapter_title('Dettagli Possessore')
        details_poss = {
            'ID Possessore': p_info.get('id'), 'Nome Completo': p_info.get('nome_completo'),
            'Comune Riferimento': p_info.get('comune_nome'),
            'Paternità': p_info.get('paternita'),
            'Stato': "Attivo" if p_info.get('attivo') else "Non Attivo",
        }
        pdf.chapter_body(details_poss)

        if possessore_data.get('partite'):
            pdf.chapter_title('Partite Associate')
            headers = ['ID Part.', 'Num. Partita', 'Suffisso', 'Comune', 'Tipo', 'Quota', 'Titolo']
            col_widths_percent = [8, 12, 10, 20, 10, 15, 25]
            data_rows = []
            for part in possessore_data['partite']:
                data_rows.append([
                    part.get('id'),
                    part.get('numero_partita'),
                    part.get('suffisso_partita', '') or '',
                    part.get('comune_nome'),
                    part.get('tipo'), 
                    part.get('quota'), 
                    part.get('titolo')
                ])
            pdf.simple_table(headers, data_rows, col_widths_percent=col_widths_percent)

        if possessore_data.get('immobili'):
            pdf.chapter_title('Immobili Associati (tramite Partite)')
            headers = ['ID Imm.', 'Natura', 'Località', 'Part. N.', 'Comune Part.']
            col_widths_percent_imm = [10, 30, 25, 15, 20]
            data_rows_imm = []
            for imm in possessore_data['immobili']:
                data_rows_imm.append([
                    imm.get('id'), imm.get('natura'), imm.get('localita_nome'),
                    imm.get('numero_partita'), imm.get('comune_nome')
                ])
            pdf.simple_table(headers, data_rows_imm, col_widths_percent_imm)

        pdf.output(filename)
        prompt_to_open_file(parent_widget, filename)
    except Exception as e:
        logging.getLogger("CatastoGUI").exception(
            "Errore esportazione PDF possessore (GUI)")
        QMessageBox.critical(parent_widget, "Errore Esportazione",
                             f"Errore durante l'esportazione PDF:\n{e}")


def _get_default_export_path(default_filename: str) -> str:
    """
    Crea la sottocartella 'Esportazioni Foliarium' in Documenti se non esiste e restituisce
    il percorso completo per il file di default.
    """
    # 1. Trova la cartella "Documenti" ufficiale dell'utente di Windows
    cartella_documenti = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
    
    # Fallback di sicurezza se per caso QStandardPaths fallisce
    if not cartella_documenti:
        cartella_documenti = os.path.expanduser("~")
        
    # 2. Definisce il percorso per la sottocartella dedicata
    full_dir_path = os.path.join(cartella_documenti, "Esportazioni Foliarium")
    
    # 3. Crea la directory in Documenti (qui abbiamo sempre i permessi!)
    os.makedirs(full_dir_path, exist_ok=True)
    
    # 4. Restituisce il percorso completo al file
    return os.path.join(full_dir_path, default_filename)
def get_password_from_keyring(service_name: str, username: str) -> Optional[str]:
    """
    Recupera una password dal keyring di sistema in modo sicuro.
    Restituisce None se keyring non è disponibile o la password non è trovata.
    """
    if not keyring:
        return None # La libreria non è installata

    try:
        password = keyring.get_password(service_name, username)
        if password:
            logging.getLogger("CatastoGUI").info(f"Password recuperata dal keyring per il servizio '{service_name}' e utente '{username}'.")
        else:
            logging.getLogger("CatastoGUI").info(f"Nessuna password trovata nel keyring per il servizio '{service_name}' e utente '{username}'.")
        return password
    except Exception as e:
        logging.getLogger("CatastoGUI").error(f"Errore durante il recupero della password dal keyring: {e}", exc_info=True)
        return None

def prompt_to_open_file(parent_widget, filename: str):
    """
    Mostra un dialogo che chiede all'utente se vuole aprire il file appena creato.
    Se l'utente accetta, apre il file con l'applicazione di sistema predefinita.
    """
    if not filename:
        return
        
    reply = QMessageBox.question(
        parent_widget,
        "Esportazione Completata",
        f"File salvato con successo.\n\nVuoi aprirlo ora?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.Yes  # Il pulsante 'Sì' è preselezionato
    )

    if reply == QMessageBox.StandardButton.Yes:
        try:
            from PyQt6.QtCore import QUrl
            from PyQt6.QtGui import QDesktopServices
            
            QDesktopServices.openUrl(QUrl.fromLocalFile(filename))
        except Exception as e:
            logging.getLogger("CatastoGUI").error(f"Impossibile aprire il file {filename}: {e}", exc_info=True)
            QMessageBox.critical(parent_widget, "Errore Apertura File", f"Impossibile aprire il file:\n{e}")
            
def is_file_locked(filepath):
    """
    Verifica se un file è bloccato/in uso da un altro processo.
    """
    if not os.path.exists(filepath):
        return False
    
    try:
        # Prova ad aprire il file in modalità esclusiva
        with open(filepath, 'a'):
            pass
        return False
    except (IOError, PermissionError):
        return True

def get_alternative_filename(original_path):
    """
    Genera un nome file alternativo aggiungendo un timestamp.
    """
    base, ext = os.path.splitext(original_path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base}_{timestamp}{ext}"


if FPDF_AVAILABLE:
    class BulkReportPDF(ModernCatastoPDF):
        """Report tabellare bulk in formato landscape con intestazioni ripetute."""

        def __init__(self, orientation='L', unit='mm', format='A4', report_title="Report Dati"):
            super().__init__(report_title=report_title, orientation=orientation,
                             unit=unit, format=format)
            self.headers    = []
            self.col_widths = []

        def header(self):
            # Banda header
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
            # Intestazione tabella ripetuta su ogni pagina
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
