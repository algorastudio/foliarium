# -*- mode: python ; coding: utf-8 -*-

# ===================================================================
#  File di Specifiche PyInstaller per Meridiana 1.3
#  Autore: Marco Santoro
#  Data: 16/06/2025
# ===================================================================

# 'a' è l'analisi dello script principale e delle sue dipendenze.
a = Analysis(
    ['gui_main.py'],  # Lo script Python principale da cui partire
    pathex=[],
    binaries=[],
    datas=[
        # Sezione FONDAMENTALE per includere cartelle e file non Python.
        # La sintassi è ('percorso/sorgente', 'nome/cartella/nel/pacchetto')
        ('resources', 'resources'),
        ('styles', 'styles'),
        ('sql_scripts', 'sql_scripts')
    ],
    hiddenimports=[
        # Moduli che PyInstaller potrebbe non trovare automaticamente.
        # Includerli qui previene errori nell'eseguibile finale.
        'psycopg2._psycopg',
        'PyQt5.sip',
        'PyQt5.QtSvg',
        'pandas',
        'openpyxl',
        'fpdf'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

# 'pyz' è il bundle di tutti i file Python.
pyz = PYZ(a.pure)

# 'exe' definisce le proprietà del file .exe finale.
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas, # Includiamo le risorse definite sopra
    [],
    name='Meridiana',          # Nome del file .exe finale
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,             # IMPORTANTISSIMO: Nasconde la finestra di console nera
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/logo_meridiana.ico' # Percorso del file icona (.ico)
)