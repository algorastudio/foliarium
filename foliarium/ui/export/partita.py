"""
foliarium/ui/export/partita.py — Wrapper GUI per l'export di una singola partita.

Tre formati: JSON, CSV (con anteprima), PDF (con anteprima).
Estratto da app_utils.py (Sprint 3 refactor — six-hats).
"""

from __future__ import annotations

import csv
import json
import logging
from datetime import date, datetime

from PyQt6.QtWidgets import QDialog, QFileDialog, QMessageBox

from catasto_db_manager import CatastoDBManager
from foliarium.ui.dialogs.export_ import CSVApreviewDialog, PDFApreviewDialog
from foliarium.reporting.pdf import FPDF_AVAILABLE, PDFPartita

_log = logging.getLogger("CatastoGUI")


def _default_export_path(default_filename: str) -> str:
    from app_utils import _get_default_export_path
    return _get_default_export_path(default_filename)


def _prompt_to_open(parent_widget, filename: str) -> None:
    from app_utils import prompt_to_open_file
    prompt_to_open_file(parent_widget, filename)


def gui_esporta_partita_json(parent_widget, db_manager: CatastoDBManager,
                             partita_id: int) -> None:
    dict_data = db_manager.get_partita_data_for_export(partita_id)
    if not dict_data:
        QMessageBox.warning(
            parent_widget, "Errore Dati",
            f"Partita con ID {partita_id} non trovata o errore "
            "nel recupero dei dati per l'esportazione.",
        )
        return

    def json_serial(obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError(
            f"Object of type {type(obj).__name__} is not JSON serializable"
        )

    try:
        json_data_str = json.dumps(
            dict_data, indent=4, ensure_ascii=False, default=json_serial
        )
    except TypeError as te:
        _log.error(
            "Errore di serializzazione JSON per partita ID %s: %s — Dati: %s",
            partita_id, te, dict_data,
        )
        QMessageBox.critical(
            parent_widget, "Errore di Serializzazione",
            f"Errore durante la conversione dei dati della partita in JSON: {te}\n"
            "Controllare i log per i dettagli.",
        )
        return

    default_filename = f"partita_{partita_id}_{date.today().isoformat()}.json"
    full_default_path = _default_export_path(default_filename)
    filename, _ = QFileDialog.getSaveFileName(
        parent_widget, "Salva JSON Partita", full_default_path,
        "JSON Files (*.json)",
    )
    if not filename:
        return

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(json_data_str)
        QMessageBox.information(
            parent_widget, "Esportazione JSON",
            f"Partita esportata con successo in:\n{filename}",
        )
    except Exception as e:
        _log.error(
            "Errore durante il salvataggio del file JSON per partita ID %s: %s",
            partita_id, e,
        )
        QMessageBox.critical(
            parent_widget, "Errore Esportazione",
            f"Errore durante il salvataggio del file JSON:\n{e}",
        )


def gui_esporta_partita_csv(parent_widget, db_manager: CatastoDBManager,
                            partita_id: int) -> None:
    partita_data = db_manager.get_partita_data_for_export(partita_id)
    if not partita_data or 'partita' not in partita_data:
        QMessageBox.warning(
            parent_widget, "Errore Dati",
            "Dati partita non validi per l'esportazione CSV.",
        )
        return

    MAX_ROWS_PREVIEW_SECTION = 3
    preview_headers = ["Sezione", "Campo", "Valore"]
    preview_data_rows = []

    p_details = partita_data.get('partita', {})
    for k, v in p_details.items():
        preview_data_rows.append(["Partita", k.replace('_', ' ').title(), v])

    if partita_data.get('possessori'):
        preview_data_rows.append(["---", "--- Possessori ---", "---"])
        poss_headers = list(partita_data['possessori'][0].keys()) \
            if partita_data['possessori'] else []
        preview_data_rows.append([
            "Possessori", "Intestazioni",
            ", ".join([h.replace('_', ' ').title() for h in poss_headers]),
        ])
        for i, pos in enumerate(partita_data['possessori']):
            if i >= MAX_ROWS_PREVIEW_SECTION:
                preview_data_rows.append([
                    "Possessori",
                    f"...e altri {len(partita_data['possessori']) - MAX_ROWS_PREVIEW_SECTION}...",
                    "",
                ])
                break
            preview_data_rows.append([
                "Possessori", f"Possessore {i+1}",
                ", ".join([str(pos.get(h, '')) for h in poss_headers]),
            ])

    preview_dialog = CSVApreviewDialog(
        preview_headers, preview_data_rows, parent_widget,
        title=f"Anteprima CSV - Partita ID {partita_id}",
    )
    if preview_dialog.exec() != QDialog.DialogCode.Accepted:
        _log.info(
            "Esportazione CSV per partita ID %s annullata dall'utente dopo anteprima.",
            partita_id,
        )
        return

    default_filename = f"partita_{partita_id}_{date.today()}.csv"
    full_default_path = _default_export_path(default_filename)
    filename, _ = QFileDialog.getSaveFileName(
        parent_widget, "Salva CSV Partita", full_default_path,
        "CSV Files (*.csv)",
    )
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

            for sezione, key in (('POSSESSORI', 'possessori'),
                                  ('IMMOBILI', 'immobili'),
                                  ('VARIAZIONI', 'variazioni')):
                rows = partita_data.get(key)
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
            f"Partita esportata con successo in:\n{filename}",
        )
    except Exception as e:
        QMessageBox.critical(
            parent_widget, "Errore Esportazione",
            f"Errore durante l'esportazione CSV:\n{e}",
        )


def gui_esporta_partita_pdf(parent_widget, db_manager: CatastoDBManager,
                            partita_id: int) -> None:
    if not FPDF_AVAILABLE:
        QMessageBox.warning(
            parent_widget, "Funzionalità non disponibile",
            "La libreria FPDF è necessaria per l'esportazione in PDF, "
            "ma non è installata.",
        )
        return

    partita_data = db_manager.get_partita_data_for_export(partita_id)
    if not partita_data or 'partita' not in partita_data:
        QMessageBox.warning(
            parent_widget, "Errore Dati",
            "Dati partita non validi per l'esportazione PDF.",
        )
        return

    preview_text_content = f"ANTEPRIMA PDF - Partita ID: {partita_id}\n"
    preview_text_content += "======================================\n\n"
    p_details = partita_data.get('partita', {})
    preview_text_content += "Dettagli Partita:\n"
    for key, value in p_details.items():
        preview_text_content += (
            f"  {key.replace('_', ' ').title()}: "
            f"{value if value is not None else 'N/D'}\n"
        )
    preview_text_content += "\n"

    if partita_data.get('possessori'):
        preview_text_content += "Possessori (primi 2):\n"
        for pos in partita_data['possessori'][:2]:
            preview_text_content += (
                f"  - ID: {pos.get('id')}, Nome: {pos.get('nome_completo')}, "
                f"Titolo: {pos.get('titolo')}, Quota: {pos.get('quota', 'N/D')}\n"
            )
        if len(partita_data['possessori']) > 2:
            preview_text_content += "  ...e altri.\n"
    preview_text_content += "\n"

    preview_dialog = PDFApreviewDialog(
        preview_text_content, parent_widget,
        title=f"Anteprima PDF - Partita ID {partita_id}",
    )
    if preview_dialog.exec() != QDialog.DialogCode.Accepted:
        _log.info(
            "Esportazione PDF per partita ID %s annullata dall'utente dopo anteprima.",
            partita_id,
        )
        return

    default_filename = f"partita_{partita_id}_{date.today()}.pdf"
    full_default_path = _default_export_path(default_filename)
    filename, _ = QFileDialog.getSaveFileName(
        parent_widget, "Salva PDF Partita", full_default_path,
        "PDF Files (*.pdf)",
    )
    if not filename:
        return

    try:
        pdf = PDFPartita()
        pdf.alias_nb_pages()
        pdf.add_page()

        p = partita_data['partita']
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
            ],
        )

        pdf.chapter_title('Dettagli Partita')
        campi_da_visualizzare = [
            'id', 'comune_nome', 'numero_partita', 'suffisso_partita',
            'tipo', 'data_impianto', 'stato', 'data_chiusura', 'numero_provenienza',
        ]
        pdf.chapter_body({k: p.get(k) for k in campi_da_visualizzare})

        if partita_data.get('possessori'):
            pdf.chapter_title('Possessori')
            headers = ['ID', 'Nome Completo', 'Titolo', 'Quota']
            data_rows = [
                [pos.get('id'), pos.get('nome_completo'),
                 pos.get('titolo'), pos.get('quota')]
                for pos in partita_data['possessori']
            ]
            pdf.simple_table(headers, data_rows)

        if partita_data.get('immobili'):
            pdf.chapter_title('Immobili')
            headers = ['ID', 'Natura', 'Località', 'Class.', 'Consist.']
            data_rows = [
                [imm.get('id'), imm.get('natura'), imm.get('localita_nome', ''),
                 imm.get('classificazione'), imm.get('consistenza')]
                for imm in partita_data['immobili']
            ]
            pdf.simple_table(headers, data_rows)

        if partita_data.get('variazioni'):
            pdf.chapter_title('Variazioni')
            headers = ['ID', 'Tipo', 'Data Var.', 'Contratto', 'Notaio']
            data_rows = []
            for var in partita_data['variazioni']:
                contr_str = (
                    f"{var.get('contratto_tipo', '')} del {var.get('data_contratto', '')}"
                    if var.get('contratto_tipo') else ''
                )
                data_rows.append([
                    var.get('id'), var.get('tipo'),
                    var.get('data_variazione'), contr_str, var.get('notaio'),
                ])
            pdf.simple_table(headers, data_rows)

        pdf.output(filename)
        _prompt_to_open(parent_widget, filename)
    except Exception as e:
        _log.exception("Errore esportazione PDF partita (GUI)")
        QMessageBox.critical(
            parent_widget, "Errore Esportazione",
            f"Errore durante l'esportazione PDF:\n{e}",
        )


__all__ = [
    "gui_esporta_partita_json",
    "gui_esporta_partita_csv",
    "gui_esporta_partita_pdf",
]
