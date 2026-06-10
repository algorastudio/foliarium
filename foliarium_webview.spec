# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec per Foliarium WebView + FastAPI + PyQt6 fallback.

Crea un bundle 'onedir' (cartella con EXE + librerie) che include:
- FastAPI server (uvicorn)
- Frontend React compilato (dist/)
- Backend Foliarium (api/, db/, catasto_db_manager.py, etc.)
- PyQt6 come fallback
- PostgreSQL embedded (demo mode, opzionale)

Entry point: webview_main.py

Uso:
    pyinstaller foliarium_webview.spec
    pyinstaller foliarium_webview.spec --onefile   # Crea single .exe (più lento)

Output:
    ./dist/Foliarium/Foliarium.exe (Windows)
    ./dist/Foliarium/Foliarium (Linux/macOS)
"""
import os
from pathlib import Path

# Percorsi base
PROJ_ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIST = os.path.join(PROJ_ROOT, 'frontend', 'dist')
API_DIR = os.path.join(PROJ_ROOT, 'api')
DB_DIR = os.path.join(PROJ_ROOT, 'db')

# --- ENTRY POINT ---
entrypoint = os.path.join(PROJ_ROOT, 'webview_main.py')

# --- DATI BINDLATI ---
# Frontend React compilato (dist/ → assets/)
datas = [
    (os.path.join(FRONTEND_DIST, 'index.html'), 'frontend/dist'),
    (os.path.join(FRONTEND_DIST, 'assets'), 'frontend/dist/assets'),
    (os.path.join(FRONTEND_DIST, 'favicon.svg'), 'frontend/dist'),
    (os.path.join(FRONTEND_DIST, 'icons.svg'), 'frontend/dist'),
    # SQL scripts
    (os.path.join(PROJ_ROOT, 'sql_scripts'), 'sql_scripts'),
    # Stili QSS (fallback PyQt6)
    (os.path.join(PROJ_ROOT, 'styles'), 'styles'),
    # Risorse (icone, loghi, etc.)
    (os.path.join(PROJ_ROOT, 'resources'), 'resources'),
    # Documentazione (per manuale integrato F1)
    (os.path.join(PROJ_ROOT, 'docs'), 'docs'),
    # mkdocs.yml per navigazione manuale
    (os.path.join(PROJ_ROOT, 'mkdocs.yml'), '.'),
]

# Config demo (rimossa da main — inclusa solo se presente)
if os.path.exists(os.path.join(PROJ_ROOT, 'demo_config.ini')):
    datas.append((os.path.join(PROJ_ROOT, 'demo_config.ini'), '.'))

# --- MODULI INCLUDERE ---
# Alcuni moduli potrebbero non essere rilevati automaticamente
hiddenimports = [
    'fastapi',
    'uvicorn',
    'uvicorn.lifespan.on',
    'uvicorn.loops.auto',
    'uvicorn.protocols.http.auto',
    'uvicorn.logging',
    'uvicorn.server',
    'webview',
    'psycopg2',
    'psycopg2.extensions',
    'pandas',
    'matplotlib',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.QtSvg',
    'PyQt6.QtWebEngineWidgets',
    'api.main',
    'api.routes',
    'api.routes.auth',
    'api.routes.comuni',
    'api.routes.partite',
    'api.routes.possessori',
    'api.routes.dashboard',
    'api.routes.audit',
    'api.routes.genealogia',
    'api.routes.timeline',
    'api.server_thread',
    'api.webview_launcher',
    'catasto_db_manager',
    'config',
    'app_utils',
    'app_paths',
]

# --- ANALISI STATIC TREE ---
# Aggiungi moduli di database
db_modules = []
if os.path.isdir(DB_DIR):
    for fname in os.listdir(DB_DIR):
        if fname.endswith('.py') and not fname.startswith('__'):
            module_name = f'db.{fname[:-3]}'
            db_modules.append(module_name)
            hiddenimports.append(module_name)

# --- CONFIGURAZIONE PYINSTALLER ---
a = Analysis(
    [entrypoint],
    pathex=[PROJ_ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[
        # Escludi WebEngine (opzionale, non sempre richiesto)
        'PyQt6.QtWebEngine',
        'PyQt6.QtWebEngineCore',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# --- PYZ (bytecode zippato) ---
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# --- BUILD (onedir) ---
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Foliarium',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Senza finestra console (GUI app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(PROJ_ROOT, 'resources', 'foliarium.ico') if os.path.exists(os.path.join(PROJ_ROOT, 'resources', 'foliarium.ico')) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Foliarium',
)

# --- NOTA DI POST-BUILD ---
print("""
╔════════════════════════════════════════════════════════════════╗
║  PyInstaller build: Foliarium WebView + FastAPI + PyQt6       ║
╚════════════════════════════════════════════════════════════════╝

Output: ./dist/Foliarium/

Struttura:
  Foliarium/
  ├── Foliarium.exe          (Windows entry point)
  ├── Foliarium              (Linux/macOS entry point)
  ├── frontend/dist/         (React app compilata)
  ├── api/                   (FastAPI backend)
  ├── db/                    (Database layer)
  ├── sql_scripts/           (SQL init scripts)
  ├── styles/                (PyQt6 fallback themes)
  ├── resources/             (Icons, etc.)
  ├── docs/                  (Manuale utente)
  └── [librerie PyQt6, psycopg2, fastapi, webview, etc.]

Lancio:
  ./dist/Foliarium/Foliarium.exe              (tenta PyWebView → fallback PyQt6)
  ./dist/Foliarium/Foliarium.exe --use-pyqt6  (forza PyQt6)
  ./dist/Foliarium/Foliarium.exe --dev        (Vite dev server + HMR)

Primi launch richiederanno build frontend (npm run build) se src/ è stato
modificato. Successivi lanciamenti usano dist/ cached.

PostgreSQL embedded non è bundled per impostazione predefinita.
Per demo version, usare foliarium_demo.spec che include pgsql/ portabile.
""")
