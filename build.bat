@echo off
REM ===================================================================
REM  Script di Build per Foliarium
REM  Genera dist\Foliarium.exe tramite PyInstaller
REM  Autore: Marco Santoro — ALGORASTUDIO
REM ===================================================================

echo.
echo  =========================================
echo   Foliarium — Build Script
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

REM Controlla che siamo nella cartella giusta (deve esserci main.py)
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
if exist "dist\Foliarium.exe" del /f /q "dist\Foliarium.exe"
if exist "build\Foliarium" rmdir /s /q "build\Foliarium"

REM Avviso icona mancante (non bloccante)
if not exist "resources\logo_foliarium.ico" (
    echo.
    echo  [AVVISO] resources\logo_foliarium.ico non trovato.
    echo           L'eseguibile verra' creato senza icona personalizzata.
    echo           Per aggiungere l'icona: metti logo_foliarium.ico in resources\
    echo.
)

REM Esegue PyInstaller
echo [4/4] Compilazione Foliarium.exe...
python -m PyInstaller --clean foliarium.spec
if errorlevel 1 (
    echo.
    echo [ERRORE] Build fallita. Controlla i messaggi di errore sopra.
    pause
    exit /b 1
)

REM Verifica output
if not exist "dist\Foliarium.exe" (
    echo [ERRORE] dist\Foliarium.exe non trovato dopo la build.
    pause
    exit /b 1
)

echo.
echo  =========================================
echo   Build completata con successo!
echo   Output: dist\Foliarium.exe
echo  =========================================
echo.
echo  Passo successivo: eseguire installer\foliarium_setup.iss
echo  con Inno Setup per creare il pacchetto di installazione.
echo.
pause
