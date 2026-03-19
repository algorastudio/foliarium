# -*- mode: python ; coding: utf-8 -*-

# ===================================================================
#  File di Specifiche PyInstaller per Foliarium DEMO 1.0
#  Genera FoliariumDemo.exe con modalita demo attivata.
#  Autore: Marco Santoro — ALGORASTUDIO
#  Licenza: AGPL-3.0-or-later
# ===================================================================

import os

ROOT = SPECPATH

a = Analysis(
    [os.path.join(ROOT, 'main.py')],
    pathex=[os.path.join(ROOT, 'src')],
    binaries=[],
    datas=[
        (os.path.join(ROOT, 'resources'), 'resources'),
        (os.path.join(ROOT, 'styles'),    'styles'),
        (os.path.join(ROOT, 'database'),  'database'),
    ],
    hiddenimports=[
        'psycopg2._psycopg',
        'PyQt5.sip',
        'PyQt5.QtSvg',
        'PyQt5.QtWebEngine',
        'PyQt5.QtWebEngineWidgets',
        'pandas',
        'fpdf',
        'bcrypt',
        'keyring',
        'keyring.backends',
        'keyring.backends.Windows',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[os.path.join(ROOT, 'demo', 'hook_demo_mode.py')],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

_icon_path = os.path.join(ROOT, 'resources', 'logo_foliarium.ico')
_icon = _icon_path if os.path.isfile(_icon_path) else None

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FoliariumDemo',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_icon,
)
