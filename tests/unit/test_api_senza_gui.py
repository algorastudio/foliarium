"""
tests/unit/test_api_senza_gui.py
================================
Il backend web non deve dipendere dalla GUI.

`api/main.py` gira su Azure Web App, dove Qt non ha ragione di esistere e le
sue librerie di sistema non ci sono. La catena di import dell'API passa per
`config.py`, che fino alla revisione del workflow di deploy importava
`PyQt6.QtCore` a livello di modulo: bastava quello a rendere PyQt6 un
requisito del server.

Questi test guardano il sorgente invece di provare l'import, perche'
nell'ambiente di test PyQt6 c'e' e un import riuscito non direbbe nulla.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


pytestmark = pytest.mark.unit

RADICE = Path(__file__).resolve().parents[2]

# Moduli nella catena di import di api.main che devono restare privi di Qt.
# api/server_thread.py e api/webview_launcher.py non sono in elenco: servono
# a integrare l'API dentro l'applicazione desktop e Qt lo importano per forza.
MODULI_SENZA_GUI = [
    "config.py",
    "app_paths.py",
    "catasto_db_manager.py",
    "api/main.py",
    "api/deps.py",
    "api/auth.py",
]

VIETATI = {"PyQt6", "matplotlib", "fpdf", "pandas"}


def _import_di_modulo(percorso: Path) -> set[str]:
    """Package importati a livello di modulo (non dentro funzioni o classi)."""
    albero = ast.parse(percorso.read_text(encoding="utf-8"), filename=str(percorso))
    trovati: set[str] = set()

    for nodo in albero.body:  # solo il corpo: gli import lazy sono ammessi
        if isinstance(nodo, ast.Import):
            trovati.update(alias.name.split(".")[0] for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0:
            trovati.add(nodo.module.split(".")[0])
        elif isinstance(nodo, ast.Try):
            # try/except ImportError attorno a un import resta un import
            # di primo livello: se fallisce senza fallback, il modulo non si carica.
            for interno in nodo.body:
                if isinstance(interno, ast.Import):
                    trovati.update(a.name.split(".")[0] for a in interno.names)
                elif isinstance(interno, ast.ImportFrom) and interno.module and interno.level == 0:
                    trovati.add(interno.module.split(".")[0])

    return trovati


@pytest.mark.parametrize("modulo", MODULI_SENZA_GUI)
def test_nessuna_dipendenza_grafica_a_livello_di_modulo(modulo):
    percorso = RADICE / modulo
    if not percorso.exists():
        pytest.skip(f"{modulo} non presente")

    vietati_trovati = _import_di_modulo(percorso) & VIETATI
    assert not vietati_trovati, (
        f"{modulo} importa {sorted(vietati_trovati)} a livello di modulo. "
        "La catena dell'API REST deve restare importabile su un server senza "
        "Qt: spostare l'import dentro la funzione che lo usa, con un fallback."
    )


def test_le_dipendenze_web_non_includono_la_gui():
    """requirements-web.txt e' la lista installata sul Web App."""
    percorso = RADICE / "requirements-web.txt"
    assert percorso.exists(), "requirements-web.txt mancante: lo usa il deploy Azure"

    righe = [
        r.strip().lower()
        for r in percorso.read_text(encoding="utf-8").splitlines()
        if r.strip() and not r.strip().startswith("#")
    ]

    for pacchetto in ("pyqt6", "matplotlib", "pillow", "mkdocs", "pytest"):
        assert not any(r.startswith(pacchetto) for r in righe), (
            f"requirements-web.txt contiene {pacchetto}: e' una dipendenza "
            "desktop o di sviluppo, e pillow in particolare e' cio' che faceva "
            "fallire il deploy quando pip doveva compilarla da sorgente."
        )

    # Il minimo con cui create_app() si avvia, verificato in venv pulito.
    for atteso in ("fastapi", "uvicorn", "psycopg2-binary", "bcrypt"):
        assert any(r.startswith(atteso) for r in righe), f"manca {atteso}"


def test_setup_global_logging_funziona_senza_qt(tmp_path, monkeypatch):
    """
    Il fallback che si attiva quando PyQt6 non c'e'. Simula l'assenza
    facendo fallire l'import di PyQt6.QtCore.
    """
    import builtins
    import logging

    import config

    reale = builtins.__import__

    def import_senza_qt(name, *args, **kwargs):
        if name.startswith("PyQt6"):
            raise ImportError("PyQt6 non disponibile (simulato)")
        return reale(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_senza_qt)
    monkeypatch.setenv("HOME", str(tmp_path))

    config.setup_global_logging(logging.INFO)  # non deve sollevare

    atteso = tmp_path / "FoliariumAppData" / "logs"
    assert atteso.exists(), "il fallback non ha creato la cartella di log"
