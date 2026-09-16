# -*- mode: python ; coding: utf-8 -*-
"""
setup_db.spec — Eseguibile di inizializzazione del database.

L'installer Inno Setup non puo' assumere che Python sia installato sulla
macchina di destinazione, quindi `setup_database.py` viene impacchettato a
parte e invocato come `setup_db.exe`.

Gli script SQL NON sono impacchettati qui: restano una risorsa del bundle
principale (`_internal/sql_scripts`), e `setup_database.resolve_sql_dir()`
li cerca anche li'. Duplicarli significherebbe poterli far divergere.

Output: dist/setup_db/setup_db.exe (onefile, console).
"""

a = Analysis(
    ['setup_database.py'],
    pathex=[],
    binaries=[],
    datas=[],
    # setup_database.py usa solo la libreria standard: nessun hidden import.
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Escludiamo esplicitamente le dipendenze pesanti dell'applicazione:
        # PyInstaller non dovrebbe trovarle (non sono importate), ma se un
        # domani setup_database.py importasse config.py se le tirerebbe
        # dietro, e l'eseguibile passerebbe da pochi MB a oltre cento.
        'PyQt6', 'matplotlib', 'numpy', 'pandas', 'psycopg2', 'fpdf',
        'openpyxl', 'keyring', 'bcrypt',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='setup_db',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # come foliarium.spec: UPX aumenta i falsi positivi antivirus
    runtime_tmpdir=None,
    # Console: l'installer mostra l'avanzamento delle 8 fasi, e in caso di
    # errore il messaggio deve restare leggibile.
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icona_foliarium.ico',
)
