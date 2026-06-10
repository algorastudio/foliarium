"""
foliarium/ui/export/possessore.py — Wrapper GUI per l'export di un possessore.

Tre formati: JSON, CSV (con anteprima), PDF (con anteprima).
Estratto da app_utils.py (Sprint 3 refactor — six-hats).
"""

from __future__ import annotations

import csv
import json
import logging
from datetime import date

from PyQt6.QtWidgets import QDialog, QFileDialog, QMessageBox

from catasto_db_manager import CatastoDBManager
from foliarium.ui.dialogs.export_ import CSVApreviewDialog, PDFApreviewDialog
from foliarium.reporting.pdf import FPDF_AVAILABLE, PDFPossessore

_log = logging.getLogger("CatastoGUI")


def _default_export_path(default_filename: str) -> str:
    from app_utils import _get_default_export_path
    return _get_default_export_path(default_filename)


def _prompt_to_open(parent_widget, filename: str) -> None:
    from app_utils import prompt_to_open_file
    prompt_to_open_file(parent_widget, filename)


def gui_esporta_possessore_json(parent_widget, db_manager: CatastoDBManager,
                                possessore_id: int) -> None:
    dict_data = db_manager.get_possessore_data_for_export(possessore_id)
    if not dict_data:
        QMessageBox.warning(
            parent_widget, "Errore Dati",
            f"Possessore con ID {possessore_id} non trovato o errore recupero dati.",
        )
        return

    json_data_str = json.dumps(dict_data, indent=4, ensure_ascii=False)
    default_filename = f"possessore_{possessore_id}_{date.today()}.json"
    filename, _ = QFileDialog.getSaveFileName(
        parent_widget, "Salva JSON Possessore", default_filename,
        "JSON Files (*.json)",
    )
    if not filename:
        return

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(json_data_str)
        QMessageBox.information(
            parent_widget, "Esportazione JSON",
            f"Possessore esportato con successo in:\n{filename}",
        )
    except Exception as e:
        QMessageBox.critical(
            parent_widget, "Errore Esportazione",
            f"Errore durante il salvataggio del file JSON:\n{e}",
        )


def gui_esporta_possessore_csv(parent_widget, db_manager: CatastoDBManager,
                               possessore_id: int) -> None:
    possessore_data = db_manager.get_possessore_data_for_export(possessore_id)
    if not possessore_data or 'possessore' not in possessore_data:
        QMessageBox.warning(
            parent_widget, "Errore Dati",
            "Dati possessore non validi per l'esportazione CSV.",
        )
        return

    MAX_ROWS_PREVIEW_SECTION = 3
    preview_headers = ["Sezione", "Campo", "Valore"]
    preview_data_rows = []

    p_details = possessore_data.get('possessore', {})
    for k, v in p_details.items():
        preview_data_rows.append(["Possessore", k.replace('_', ' ').title(), v])

    if possessore_data.get('partite'):
        preview_data_rows.append(["---", "--- Partite Associate ---", "---"])
        partite_headers = list(possessore_data['partite'][0].keys()) \
            if possessore_data['partite'] else []
        preview_data_rows.append([
            "Partite", "Intestazioni",
            ", ".join([h.replace('_', ' ').title() for h in partite_headers]),
        ])
        for i, partita in enumerate(possessore_data['partite']):
            if i >= MAX_ROWS_PREVIEW_SECTION:
                preview_data_rows.append([
                    "Partite",
                    f"...e altre {len(possessore_data['partite']) - MAX_ROWS_PREVIEW_SECTION}...",
                    "",
                ])
                break
            row_summary = (
                f"N.{partita.get('numero_partita', '?')} "
                f"({partita.get('comune_nome', '?')}), "
                f"Titolo: {partita.get('titolo', 'N/D')}"
            )
            preview_data_rows.append(["Partite", f"Partita {i+1}", row_summary])

    preview_dialog = CSVApreviewDialog(
        preview_headers, preview_data_rows, parent_widget,
        title=f"Anteprima CSV - Possessore ID {possessore_id}",
    )
    if preview_dialog.exec() != QDialog.DialogCode.Accepted:
        _log.info(
            "Esportazione CSV per possessore ID %s annullata dall'utente.",
            possessore_id,
        )
        return

    default_filename = f"possessore_{possessore_id}_{date.today()}.csv"
    full_default_path = _default_export_path(default_filename)
    filename, _ = QFileDialog.getSaveFileName(
        parent_widget, "Salva CSV Possessore", full_default_path,
        "CSV Files (*.csv)",
    )
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

            for sezione, key in (('PARTITE ASSOCIATE', 'partite'),
                                  ('IMMOBILI ASSOCIATI (TRAMITE PARTITE)', 'immobili')):
                rows = possessore_data.get(key)
                if not rows:
                    continue
                writer.writerow([f'--- {sezione} ---'])
                headers = list(rows[0].keys())
                writer.writerow([h.replace('_', ' ').title() for h in headers])
                for r in rows:
                    writer.writerow([r.get(h) for h in headers])
                writer.writerow([])

        QMessageBox.information(
            parent_widget, "Esportazione CSV",
            f"Possessore esportato con successo in:\n{filename}",
        )
    except Exception as e:
        QMessageBox.critical(
            parent_widget, "Errore Esportazione",
            f"Errore durante l'esportazione CSV:\n{e}",
        )


def gui_esporta_possessore_pdf(parent_widget, db_manager: CatastoDBManager,
                               possessore_id: int) -> None:
    if not FPDF_AVAILABLE:
        QMessageBox.warning(
            parent_widget, "Funzionalità non disponibile",
            "La libreria FPDF è necessaria per l'esportazione in PDF, "
            "ma non è installata.",
        )
        return

    possessore_data = db_manager.get_possessore_data_for_export(possessore_id)
    if not possessore_data or 'possessore' not in possessore_data:
        QMessageBox.warning(
            parent_widget, "Errore Dati",
            "Dati possessore non validi per l'esportazione PDF.",
        )
        return

    preview_text_content = f"ANTEPRIMA PDF - Possessore ID: {possessore_id}\n"
    preview_text_content += "========================================\n\n"
    p_details = possessore_data.get('possessore', {})
    preview_text_content += "Dettagli Possessore:\n"
    for key, value in p_details.items():
        preview_text_content += (
            f"  {key.replace('_', ' ').title()}: "
            f"{value if value is not None else 'N/D'}\n"
        )
    preview_text_content += "\n"

    if possessore_data.get('partite'):
        preview_text_content += "Partite Associate (prime 3):\n"
        for partita in possessore_data['partite'][:3]:
            preview_text_content += (
                f"  - Partita N.{partita.get('numero_partita', '?')} "
                f"({partita.get('comune_nome', '?')}) - "
                f"Titolo: {partita.get('titolo', 'N/D')}, "
                f"Quota: {partita.get('quota', 'N/D')}\n"
            )
        if len(possessore_data['partite']) > 3:
            preview_text_content += "  ...e altre.\n"
    preview_text_content += "\n"

    preview_dialog = PDFApreviewDialog(
        preview_text_content, parent_widget,
        title=f"Anteprima PDF - Possessore ID {possessore_id}",
    )
    if preview_dialog.exec() != QDialog.DialogCode.Accepted:
        _log.info(
            "Esportazione PDF per possessore ID %s annullata dall'utente.",
            possessore_id,
        )
        return

    default_filename = f"possessore_{possessore_id}_{date.today()}.pdf"
    full_default_path = _default_export_path(default_filename)
    filename, _ = QFileDialog.getSaveFileName(
        parent_widget, "Salva PDF Possessore", full_default_path,
        "PDF Files (*.pdf)",
    )
    if not filename:
        return

    try:
        pdf = PDFPossessore()
        pdf.alias_nb_pages()
        pdf.add_page()

        p_info = possessore_data['possessore']
        nome = p_info.get('nome_completo') or p_info.get('cognome_nome', 'N/D')
        stato_str = "Attivo" if p_info.get('attivo') else "Non attivo"
        pdf.cover_block(
            title=f"POSSESSORE - {nome}",
            note=f"Stato: {stato_str}   •   Comune: {p_info.get('comune_nome', 'N/D')}",
            chips=[
                ("Paternità", p_info.get('paternita')),
                ("ID", p_info.get('id')),
            ],
        )

        pdf.chapter_title('Dettagli Possessore')
        details_poss = {
            'ID Possessore': p_info.get('id'),
            'Nome Completo': p_info.get('nome_completo'),
            'Comune Riferimento': p_info.get('comune_nome'),
            'Paternità': p_info.get('paternita'),
            'Stato': "Attivo" if p_info.get('attivo') else "Non Attivo",
        }
        pdf.chapter_body(details_poss)

        if possessore_data.get('partite'):
            pdf.chapter_title('Partite Associate')
            headers = ['ID Part.', 'Num. Partita', 'Suffisso', 'Comune',
                       'Tipo', 'Quota', 'Titolo']
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
                    part.get('titolo'),
                ])
            pdf.simple_table(headers, data_rows,
                             col_widths_percent=col_widths_percent)

        if possessore_data.get('immobili'):
            pdf.chapter_title('Immobili Associati (tramite Partite)')
            headers = ['ID Imm.', 'Natura', 'Località', 'Part. N.', 'Comune Part.']
            col_widths_percent_imm = [10, 30, 25, 15, 20]
            data_rows_imm = []
            for imm in possessore_data['immobili']:
                data_rows_imm.append([
                    imm.get('id'), imm.get('natura'), imm.get('localita_nome'),
                    imm.get('numero_partita'), imm.get('comune_nome'),
                ])
            pdf.simple_table(headers, data_rows_imm, col_widths_percent_imm)

        pdf.output(filename)
        _prompt_to_open(parent_widget, filename)
    except Exception as e:
        _log.exception("Errore esportazione PDF possessore (GUI)")
        QMessageBox.critical(
            parent_widget, "Errore Esportazione",
            f"Errore durante l'esportazione PDF:\n{e}",
        )


__all__ = [
    "gui_esporta_possessore_json",
    "gui_esporta_possessore_csv",
    "gui_esporta_possessore_pdf",
]
