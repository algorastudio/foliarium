@echo off
echo ==============================================================
echo   CREAZIONE E FIRMA DIGITALE FOLIARIUM (CERTUM CLOUD)
echo ==============================================================
echo.
echo ATTENZIONE: Prima di continuare, assicurati di:
echo 1. Aver aperto l'app SimplySign Desktop sul PC.
echo 2. Aver effettuato l'accesso con il token OTP dal telefono.
echo.
pause

echo.
echo [1/4] Compilazione dell'eseguibile con PyInstaller in corso...
call pyinstaller foliarium.spec --clean --noconfirm
if %errorlevel% neq 0 (
    echo [ERRORE] Compilazione PyInstaller fallita!
    pause
    exit /b %errorlevel%
)

echo.
echo [2/4] Firma digitale di Foliarium.exe in corso...
:: Cerca automaticamente signtool.exe nelle cartelle di Windows SDK
set SIGNTOOL_PATH=
for /f "delims=" %%i in ('dir /b /s "C:\Program Files (x86)\Windows Kits\10\bin\*\x64\signtool.exe" 2^>nul') do set "SIGNTOOL_PATH=%%i"

if "%SIGNTOOL_PATH%"=="" (
    echo [ERRORE] signtool.exe non trovato! Devi installare Windows 10/11 SDK.
    pause
    exit /b 1
)

"%SIGNTOOL_PATH%" sign /tr http://time.certum.pl/ /td sha256 /fd sha256 /a "dist\Foliarium\Foliarium.exe"
if %errorlevel% neq 0 (
    echo [ERRORE] Firma dell'eseguibile fallita! Controlla SimplySign.
    pause
    exit /b %errorlevel%
)

echo.
echo [3/4] Creazione del pacchetto di installazione (Inno Setup)...
call "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" Foliarium_Installer.iss
if %errorlevel% neq 0 (
    echo [ERRORE] Creazione dell'Installer fallita!
    pause
    exit /b %errorlevel%
)

echo.
echo [4/4] Firma digitale dell'Installer in corso...
"%SIGNTOOL_PATH%" sign /tr http://time.certum.pl/ /td sha256 /fd sha256 /a "Installer\Foliarium_1.5_Setup.exe"
if %errorlevel% neq 0 (
    echo [ERRORE] Firma dell'Installer fallita! Controlla SimplySign.
    pause
    exit /b %errorlevel%
)

echo.
echo ==============================================================
echo   SUCCESSO! FOLIARIUM E' COMPILATA E FIRMATA DIGITALMENTE.
echo ==============================================================
echo Trovi il file pronto da consegnare all'Archivio nella cartella "Installer".
echo.
pause
