# -*- mode: python ; coding: utf-8 -*-
#
# foliarium_demo.spec — Build spec per la versione DEMO portabile di Foliarium
#
# Il bundle include:
#   - Foliarium_Demo.exe  (l'applicazione)
#   - pgsql/              (PostgreSQL 14 portabile Windows, ~50 MB binari)
#   - demo_data/          (cluster PostgreSQL pre-inizializzato con dati demo)
#   - resources/, styles/ (risorse grafiche e temi)
#
# PRE-REQUISITI (eseguiti dal job CI build-demo):
#   1. Scaricare PostgreSQL portabile in pgsql/
#   2. Eseguire: python prepare_demo_db.py --pgsql-dir pgsql
#      → crea demo_data/ con schema + dati Savona 1870-1985
#
# Build:
#   pyinstaller foliarium_demo.spec
#
# ZIP portabile (nessuna installazione richiesta):
#   Compress-Archive -Path dist\Foliarium_Demo\* -DestinationPath Foliarium_Demo_Portabile.zip
# ---------------------------------------------------------------------------

import os
import tempfile
from pathlib import Path

# Runtime hook: imposta FOLIARIUM_DEMO=1 prima di qualsiasi import
_rthook_content = "import os\nos.environ['FOLIARIUM_DEMO'] = '1'\n"
_rthook_path = os.path.join(tempfile.gettempdir(), 'rthook_foliarium_demo.py')
with open(_rthook_path, 'w') as _f:
    _f.write(_rthook_content)

# ---------------------------------------------------------------------------
# Calcola i datas aggiuntivi in base a ciò che esiste nella directory di build
# ---------------------------------------------------------------------------
_extra_datas = []

# NOTA: pgsql/ e demo_data/ NON vengono inclusi come PyInstaller datas perché
# in PyInstaller 6+ i datas finiscono in _internal/ (non nella root del bundle).
# Vengono copiati direttamente nella root del bundle dal pipeline CI dopo
# l'esecuzione di pyinstaller (vedi step "Copia pgsql e demo_data nel bundle").

if not Path('pgsql').exists():
    print("[spec] ATTENZIONE: cartella pgsql/ non trovata. "
          "Ricorda di copiarla nel bundle dopo la build.")

if not Path('demo_data').exists():
    print("[spec] ATTENZIONE: cartella demo_data/ non trovata. "
          "Eseguire prima prepare_demo_db.py, poi copiare nel bundle.")

# ---------------------------------------------------------------------------
a = Analysis(
    ['gui_main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources', 'resources'),
        ('styles',    'styles'),
        *_extra_datas,
    ],
    hiddenimports=[
        'demo_launcher',   # import esplicito — usato solo in modalità demo
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[_rthook_path],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Foliarium_Demo',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icona_foliarium.ico',
    version='version.txt',
    copyright="Copyright © Marco Santoro — Versione Demo",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Foliarium_Demo',
)
