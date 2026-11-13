"""
tests/unit/test_demo_esempi_import.py
=====================================
File d'esempio per provare l'import di massa nella demo in Docker.

Il cliente della demo non puo' caricare file dal proprio PC: per provare
«File -> Importa Comuni da CSV» gli serve un file gia' presente nella
postazione. Deve essere nel formato che il dialogo accetta e contenere
comuni che l'archivio dimostrativo non ha, altrimenti l'import li salta
tutti come duplicati e sembra non funzionare.
"""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path

import pytest


pytestmark = pytest.mark.unit

RADICE = Path(__file__).resolve().parents[2]
ESEMPI = RADICE / "docker" / "demo" / "esempi-import"
COMUNI = ESEMPI / "comuni.csv"
INTESTAZIONE = "nome;provincia;regione;codice_catastale;data_istituzione;data_soppressione;note"


def _righe() -> list[str]:
    return COMUNI.read_text(encoding="utf-8-sig").splitlines()


def test_comuni_csv_ha_intestazione_documentata():
    righe = _righe()
    assert righe[0] == INTESTAZIONE
    assert len(righe) == 9, "intestazione + otto comuni"
    assert all(len(r.split(";")) == 7 for r in righe)


def test_intestazione_coincide_con_il_modello_del_dialogo():
    # Il dialogo di import offre «Scarica Template CSV»: se il modello
    # cambia, l'esempio deve seguirlo.
    sorgente = (RADICE / "foliarium" / "ui" / "dialogs" / "import_.py").read_text(encoding="utf-8")
    assert f'TEMPLATE_HEADERS = "{INTESTAZIONE}"' in sorgente


def test_colonne_obbligatorie_compilate():
    for riga in csv.DictReader(io.StringIO("\n".join(_righe())), delimiter=";"):
        assert riga["nome"].strip()
        assert riga["regione"].strip() == "Liguria"
        assert len(riga["provincia"]) == 2 and riga["provincia"].isupper()


def _comuni_del_dataset_demo() -> set[str]:
    """Nomi dei comuni che demo_data.sql inserisce (array v_comuni_nomi)."""
    demo = (RADICE / "sql_scripts" / "demo" / "demo_data.sql").read_text(encoding="utf-8")
    corpo = re.search(r"v_comuni_nomi TEXT\[\] := ARRAY\[(.*?)\];", demo, re.S).group(1)
    return set(re.findall(r"'([^']+)'", corpo))


def test_comuni_csv_non_duplica_il_dataset_demo():
    gia_presenti = _comuni_del_dataset_demo()
    assert "Savona" in gia_presenti, "lettura dell'elenco dei comuni demo fallita"
    nomi = [riga.split(";")[0] for riga in _righe()[1:]]
    assert len(set(nomi)) == len(nomi), "nomi ripetuti nell'esempio"
    assert not (set(nomi) & gia_presenti), "comuni gia' nell'archivio dimostrativo"


def test_le_date_sono_lasciate_vuote():
    # Il manuale indica AAAA-MM-GG, il dialogo GG/MM/AAAA: finche' le due
    # indicazioni divergono, l'esempio non deve dipendere da nessuna.
    for riga in csv.DictReader(io.StringIO("\n".join(_righe())), delimiter=";"):
        assert riga["data_istituzione"] == ""
        assert riga["data_soppressione"] == ""


def test_la_cartella_ha_le_istruzioni():
    testo = (ESEMPI / "LEGGIMI.txt").read_text(encoding="utf-8")
    assert "comuni.csv" in testo
    assert "Importa Comuni" in testo
