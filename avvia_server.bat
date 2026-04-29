@echo off
chcp 65001 > nul

for /f "delims=" %%i in ('python _leggi_config.py') do set "%%i"

if not defined DB_NAME (
    echo [ERRORE] web.ini non trovato o non leggibile.
    echo Copia web.ini.example in web.ini e configura le credenziali.
    pause & exit /b 1
)

if not exist "frontend\dist\index.html" (
    echo [AVVISO] Frontend non compilato. Esegui prima installa_web.bat
    pause & exit /b 1
)

cls
echo.
echo  ================================================
echo   Foliarium Web - Server in esecuzione
echo.
echo   Database : %DB_HOST%:%DB_PORT%/%DB_NAME%
echo   Indirizzo: http://localhost:%SRV_PORT%
echo.
echo   Per fermare il server: Ctrl+C
echo  ================================================
echo.

python -m uvicorn api.main:create_app --factory --host %SRV_HOST% --port %SRV_PORT%

echo.
echo  Server fermato.
pause
