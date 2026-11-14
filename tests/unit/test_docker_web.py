"""
tests/unit/test_docker_web.py
=============================
Immagine dello stack web (`Dockerfile` in radice) e la sua prova
(`docker/prova-web.sh`), verificate senza Docker.

Il Dockerfile copia i moduli per nome. Quando alcuni sono stati spostati nel
package `foliarium/`, il `COPY` ha continuato a citarli e la build si e'
rotta senza che nessun test se ne accorgesse. Questi controlli girano nella
pipeline principale; la prova con i container veri e' il workflow
`web_docker.yml`.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest


pytestmark = pytest.mark.unit

RADICE = Path(__file__).resolve().parents[2]
DOCKERFILE = RADICE / "Dockerfile"
WORKFLOW_AZURE = RADICE / ".github" / "workflows" / "main_foliarium.yml"
PROVA = RADICE / "docker" / "prova-web.sh"


def _sorgenti_copiate() -> list[str]:
    """Percorsi che i `COPY` prendono dal contesto di build (non da uno stage)."""
    testo = DOCKERFILE.read_text(encoding="utf-8").replace("\\\n", " ")
    sorgenti: list[str] = []
    for riga in testo.splitlines():
        parti = riga.split()
        if parti[:1] != ["COPY"]:
            continue
        argomenti = parti[1:]
        if any(a.startswith("--from=") for a in argomenti):
            continue
        argomenti = [a for a in argomenti if not a.startswith("--")]
        sorgenti.extend(argomenti[:-1])  # l'ultimo e' la destinazione
    return sorgenti


def _moduli_python(percorsi: list[str]) -> set[str]:
    """I moduli e i package Python fra i percorsi, senza barra finale."""
    return {
        p.rstrip("/") for p in percorsi
        if p.endswith(".py") or any((RADICE / p).glob("*.py"))
    }


def _moduli_artefatto_azure() -> set[str]:
    """Cio' che main_foliarium.yml copia nella radice dell'artefatto."""
    testo = WORKFLOW_AZURE.read_text(encoding="utf-8")
    moduli: set[str] = set()
    for elenco in re.findall(r"^\s*cp (?:-r )?(.+?) deploy/\s*$", testo, re.M):
        moduli.update(elenco.split())
    return moduli


def test_ogni_sorgente_copiata_esiste():
    mancanti = [s for s in _sorgenti_copiate() if not (RADICE / s).exists()]
    assert mancanti == []


def test_stessi_moduli_dell_artefatto_azure():
    # I due modi di pubblicare il backend web devono contenere lo stesso
    # codice: un modulo aggiunto a uno solo dei due elenchi funzionerebbe
    # su Azure e non nel container, o viceversa.
    azure = _moduli_artefatto_azure()
    assert azure, "elenco dell'artefatto non trovato in main_foliarium.yml"
    assert _moduli_python(_sorgenti_copiate()) == azure


def test_niente_dipendenze_dell_applicazione_desktop():
    sorgenti = _sorgenti_copiate()
    # requirements.txt porta PyQt6, pandas, matplotlib, mkdocs, pytest.
    assert "requirements-web.txt" in sorgenti
    assert "requirements.txt" not in sorgenti
    # app_utils importa PyQt6; api/main.py lo usa solo se manca DB_PASS.
    assert "app_utils.py" not in sorgenti
    assert "QT_QPA_PLATFORM" not in DOCKERFILE.read_text(encoding="utf-8")


def test_prova_sintassi_bash():
    subprocess.run(["bash", "-n", str(PROVA)], check=True)


def test_prova_senza_grep_q_in_coda_a_una_pipe():
    # Con `set -o pipefail`, `comando | grep -q testo` fallisce a caso: grep
    # esce al primo riscontro, il comando a monte riceve SIGPIPE e la pipe
    # risulta fallita anche se il testo c'era (vedi test_demo_script.py).
    testo = PROVA.read_text(encoding="utf-8")
    assert "pipefail" in testo
    colpevoli = [
        riga.strip() for riga in testo.splitlines()
        if re.search(r"\|\s*grep\s+(-\w*q\w*|--quiet)", riga)
        and not riga.lstrip().startswith("#")
    ]
    assert colpevoli == []
