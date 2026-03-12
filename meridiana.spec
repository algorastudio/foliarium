# -*- mode: python ; coding: utf-8 -*-

# Importa le utility di PyInstaller
from PyInstaller.utils.hooks import collect_data_files

# --- Analisi dello script principale ---
# Qui PyInstaller analizza il codice per trovare tutte le dipendenze.
a = Analysis(
    ['gui_main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources', 'resources'), # Inclusione della cartella 'resources'
        ('styles', 'styles')       # Inclusione della cartella 'styles'
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# --- Creazione dell'archivio Python ---
# Raggruppa tutti i moduli Python compilati.
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# --- Creazione dell'Eseguibile (.exe) ---
# Configura l'eseguibile con metadati specifici e icona.
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Foliarium',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # FONDAMENTALE: disabilita UPX per ridurre i falsi positivi
    console=False, # True per debug, False per un'applicazione GUI
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icona_meridiana.ico', # Imposta l'icona dell'applicazione
    # --- Metadati del File Eseguibile ---
    version='version.txt', # File di versione per informazioni dettagliate
    copyright='Copyright © Marco Santoro. In gentile concessione gratuita all\'Archivio di Stato di Savona.'
)

# --- Creazione della Cartella di Distribuzione ---
# Raccoglie l'eseguibile e tutte le sue dipendenze in una singola cartella.
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False, # Disabilita UPX anche per le librerie DLL
    upx_exclude=[],
    name='Foliarium' # Nome della cartella finale che verrà creata in 'dist'
)