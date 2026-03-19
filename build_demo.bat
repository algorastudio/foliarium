@echo off
REM ===================================================================
REM  Script di Build per Foliarium DEMO
REM  Genera dist\FoliariumDemo.exe tramite PyInstaller
REM  La versione demo imposta FOLIARIUM_DEMO=1 all'avvio.
REM  Autore: Marco Santoro — ALGORASTUDIO
REM ===================================================================

echo.
echo  =========================================
echo   Foliarium DEMO — Build Script
echo   ALGORASTUDIO
echo  =========================================
echo.

REM Controlla che Python sia disponibile
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRORE] Python non trovato nel PATH. Installare Python 3.8+ e riprovare.
    pause
    exit /b 1
)

REM Controlla che siamo nella cartella giusta
if not exist "main.py" (
    echo [ERRORE] Eseguire questo script dalla root del progetto Foliarium.
    pause
    exit /b 1
)

REM Installa/aggiorna PyInstaller
echo [1/4] Installazione PyInstaller...
python -m pip install --quiet --upgrade pyinstaller
if errorlevel 1 (
    echo [ERRORE] Impossibile installare PyInstaller.
    pause
    exit /b 1
)

REM Installa dipendenze del progetto
echo [2/4] Installazione dipendenze progetto...
python -m pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo [ERRORE] Impossibile installare le dipendenze.
    pause
    exit /b 1
)

REM Pulisce la build precedente
echo [3/4] Pulizia build precedente...
if exist "dist\FoliariumDemo.exe" del /f /q "dist\FoliariumDemo.exe"
if exist "build\FoliariumDemo" rmdir /s /q "build\FoliariumDemo"

REM Avviso icona mancante
if not exist "resources\logo_foliarium.ico" (
    echo.
    echo  [AVVISO] resources\logo_foliarium.ico non trovato.
    echo.
)

REM Esegue PyInstaller con spec demo
echo [4/4] Compilazione FoliariumDemo.exe...
python -m PyInstaller --clean foliarium_demo.spec
if errorlevel 1 (
    echo.
    echo [ERRORE] Build fallita. Controlla i messaggi di errore sopra.
    pause
    exit /b 1
)

if not exist "dist\FoliariumDemo.exe" (
    echo [ERRORE] dist\FoliariumDemo.exe non trovato dopo la build.
    pause
    exit /b 1
)

echo.
echo  =========================================
echo   Build DEMO completata con successo!
echo   Output: dist\FoliariumDemo.exe
echo  =========================================
echo.
echo  Copia dist\FoliariumDemo.exe nella cartella demo\
echo  e distribuiscila insieme agli script in demo\
echo.
pause
