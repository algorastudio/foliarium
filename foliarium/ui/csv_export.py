"""
foliarium/ui/csv_export.py — Helper per esportazione CSV da gui_main.

Estratto da gui_main.py (Sprint 3.9 refactor — six-hats B.5).

Funzioni pure (ricevono window/db_manager/user info esplicitamente)
per separare logica IO da CatastoMainWindow. Le 5 funzioni esposte:

    - scarica_csv_generico(window, ..., data, fieldnames, default_filename)
    - seleziona_comune_per_csv(window, db_manager, entita)
    - scarica_csv_comuni(window, db_manager, user_id, session_id)
    - scarica_csv_localita(window, db_manager, user_id, session_id)
    - scarica_csv_possessori(window, db_manager, user_id, session_id)
    - scarica_csv_partite(window, db_manager, user_id, session_id)

Tutte mostrano QMessageBox in caso di successo / errore e loggano
l'evento `export_csv` sul DB.
"""

from __future__ import annotations

import csv as _csv
import logging
import os
from typing import List, Optional, Tuple

from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMessageBox


logger = logging.getLogger("CatastoGUI.csv_export")


def scarica_csv_generico(
    window,
    db_manager,
    user_id: Optional[int],
    session_id: Optional[int],
    data: List[dict],
    fieldnames: List[str],
    default_filename: str,
) -> None:
    """Salva una lista di dict come CSV (delimiter ';') tramite QFileDialog.

    Mostra messaggi di successo/errore via QMessageBox. Logga
    `export_csv` sul DB con entity = nome file senza estensione.
    """
    if not data:
        QMessageBox.information(window, "Nessun dato", "Nessun record da scaricare.")
        return
    filename, _ = QFileDialog.getSaveFileName(
        window, "Salva CSV", default_filename, "File CSV (*.csv)"
    )
    if not filename:
        return
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = _csv.DictWriter(
                f, fieldnames=fieldnames, delimiter=';', extrasaction='ignore',
            )
            writer.writeheader()
            writer.writerows(data)
        QMessageBox.information(
            window, "Scaricato",
            f"{len(data)} record salvati in:\n{filename}",
        )
        # Audit log export
        if db_manager:
            db_manager.log_app_event(
                user_id, session_id,
                "export_csv",
                {
                    "filename": os.path.basename(filename),
                    "n_record": len(data),
                    "entity": default_filename.replace(".csv", ""),
                },
            )
    except OSError as e:
        QMessageBox.critical(window, "Errore salvataggio", str(e))


def seleziona_comune_per_csv(
    window, db_manager, entita: str,
) -> Tuple[Optional[int], str]:
    """Mostra QInputDialog per selezionare un comune.

    Ritorna (comune_id, slug_per_filename) oppure (None, '') se annullato.
    """
    try:
        comuni = db_manager.get_elenco_comuni_semplice()
    except Exception:
        comuni = []
    if not comuni:
        QMessageBox.warning(window, "Nessun Comune",
                            "Nessun comune trovato nel database.")
        return None, ""
    nomi = [c[1] for c in comuni]
    nome, ok = QInputDialog.getItem(
        window, "Selezione Comune",
        f"Comune di riferimento per '{entita}':", nomi, 0, False,
    )
    if not ok or not nome:
        return None, ""
    for cid, cnome in comuni:
        if cnome == nome:
            return cid, cnome.replace(' ', '_')
    return None, ""


def scarica_csv_comuni(window, db_manager, user_id, session_id) -> None:
    """Scarica tutti i comuni in un CSV compatibile con 'Importa Comuni da CSV'."""
    try:
        data = db_manager.get_comuni_export_csv()
    except Exception as e:
        QMessageBox.critical(window, "Errore Database", str(e))
        return
    scarica_csv_generico(
        window, db_manager, user_id, session_id, data,
        ['nome', 'provincia', 'regione', 'codice_catastale',
         'data_istituzione', 'data_soppressione', 'note'],
        'comuni_export.csv',
    )


def scarica_csv_localita(window, db_manager, user_id, session_id) -> None:
    """Scarica le località di un comune in CSV compatibile con 'Importa Località da CSV'."""
    comune_id, slug = seleziona_comune_per_csv(window, db_manager, "località")
    if not comune_id:
        return
    try:
        data = db_manager.get_localita_export_csv(comune_id)
    except Exception as e:
        QMessageBox.critical(window, "Errore Database", str(e))
        return
    scarica_csv_generico(
        window, db_manager, user_id, session_id, data,
        ['nome', 'tipo', 'civico'],
        f'localita_{slug}.csv',
    )


def scarica_csv_possessori(window, db_manager, user_id, session_id) -> None:
    """Scarica i possessori di un comune in CSV compatibile con 'Importa Possessori da CSV'."""
    comune_id, slug = seleziona_comune_per_csv(window, db_manager, "possessori")
    if not comune_id:
        return
    try:
        data = db_manager.get_possessori_export_csv(comune_id)
    except Exception as e:
        QMessageBox.critical(window, "Errore Database", str(e))
        return
    scarica_csv_generico(
        window, db_manager, user_id, session_id, data,
        ['cognome_nome', 'nome_completo', 'paternita'],
        f'possessori_{slug}.csv',
    )


def scarica_csv_partite(window, db_manager, user_id, session_id) -> None:
    """Scarica le partite di un comune in CSV compatibile con 'Importa Partite da CSV'."""
    comune_id, slug = seleziona_comune_per_csv(window, db_manager, "partite")
    if not comune_id:
        return
    try:
        data = db_manager.get_partite_export_csv(comune_id)
    except Exception as e:
        QMessageBox.critical(window, "Errore Database", str(e))
        return
    scarica_csv_generico(
        window, db_manager, user_id, session_id, data,
        ['numero_partita', 'data_impianto', 'stato', 'tipo'],
        f'partite_{slug}.csv',
    )


__all__ = [
    "scarica_csv_generico",
    "seleziona_comune_per_csv",
    "scarica_csv_comuni",
    "scarica_csv_localita",
    "scarica_csv_possessori",
    "scarica_csv_partite",
]
