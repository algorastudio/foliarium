# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

# --- Manuale in linea (Aiuto -> Manuale, F1) ---
# HelpViewerDialog legge i .md da BASE_DIR/docs e la navigazione da
# BASE_DIR/mkdocs.yml, cioe' da _internal/ nel bundle: senza queste voci il
# manuale del programma installato si apre vuoto.
# Solo i .md: il resto di docs/ (PDF di progetto, presentazioni, sorgenti del
# sito) il visualizzatore non lo usa. docs/internal/ resta fuori: sono
# documenti di progetto, non destinati ai clienti. La ricerca del manuale
# applica la stessa esclusione (help_viewer.CARTELLE_ESCLUSE_DAL_MANUALE).
# tests/unit/test_spec_manuale.py verifica il risultato.
_DOCS_ESCLUSE = {'internal'}


def _datas_manuale():
    radice = Path(SPECPATH)
    docs = radice / 'docs'
    voci = [(str(radice / 'mkdocs.yml'), '.')]
    for md in sorted(docs.rglob('*.md')):
        rel = md.relative_to(docs)
        if rel.parts[0] in _DOCS_ESCLUSE:
            continue
        voci.append((str(md), (Path('docs') / rel.parent).as_posix()))
    return voci


# --- Analisi dello script principale ---
# Qui PyInstaller analizza il codice per trovare tutte le dipendenze.
a = Analysis(
    ['gui_main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources', 'resources'), # Inclusione della cartella 'resources'
        ('styles', 'styles'),       # Inclusione della cartella 'styles'
        ('sql_scripts', 'sql_scripts'),  # Script SQL per inizializzazione DB
    ] + _datas_manuale(),               # Manuale in linea (vedi sopra)
    hiddenimports=[
        # Submodules del package foliarium/ — PyInstaller li trova via Analysis,
        # ma alcuni sono importati lazy in gui_main.py e necessitano enumerazione esplicita.
        'foliarium.core.services.license',
        'foliarium.core.services.update_checker',
        'foliarium.core.services.email',
        'foliarium.ui.widgets.custom',
        'foliarium.ui.widgets.insertion',
        'foliarium.ui.widgets.admin',
        'foliarium.ui.widgets.reporting',
        'foliarium.ui.dialogs.entity',
        'foliarium.ui.dialogs.admin',
        'foliarium.ui.dialogs.partita',
        'foliarium.ui.dialogs.import_',
        'foliarium.ui.top_bar',
        'foliarium.ui.sidebar',
        'foliarium.ui.command_palette',
        # Grafici dashboard (matplotlib + Qt backend)
        'foliarium.ui.widgets.dashboard_charts',
        'matplotlib.backends.backend_qtagg',
        # Timeline cronologica variazioni partita
        'foliarium.ui.widgets.timeline_partita',
        # Grafo genealogico interattivo
        'foliarium.ui.widgets.genealogia_graph',
        # Visualizzatore documentale (PDF/immagini)
        'foliarium.ui.widgets.document_viewer',
        'PyQt6.QtPdf',
        'PyQt6.QtPdfWidgets',
        # Wizard operazioni massive (bulk successione/trasferimento)
        'foliarium.ui.widgets.workflow.bulk_successione',
    ],
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
    icon='resources/icona_foliarium.ico', # Imposta l'icona dell'applicazione
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
