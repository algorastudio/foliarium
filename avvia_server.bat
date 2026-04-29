@echo off
chcp 65001 > nul

:: Legge web.ini e imposta le variabili d'ambiente
for /f "tokens=1,2 delims== eol=;" %%a in ('findstr /v "^\[" web.ini') do (
    set "_key=%%a"
    set "_val=%%b"
    :: Rimuove spazi attorno ai valori
    for /f "tokens=* delims= " %%x in ("%%a") do set "_key=%%x"
    for /f "tokens=* delims= " %%x in ("%%b") do set "_val=%%x"
    if /i "!_key!"=="host"     if not defined _srv_host set "DB_HOST=!_val!"
    if /i "!_key!"=="port"     if not defined _srv_port set "DB_PORT=!_val!"
    if /i "!_key!"=="name"     set "DB_NAME=!_val!"
    if /i "!_key!"=="user"     set "DB_USER=!_val!"
    if /i "!_key!"=="password" set "DB_PASS=!_val!"
)

:: Rileva host e porta server (sezione [server])
setlocal enabledelayedexpansion
set "_in_server=0"
for /f "tokens=1,2 delims== eol=;" %%a in (web.ini) do (
    set "_k=%%a"
    set "_v=%%b"
    for /f "tokens=* delims= " %%x in ("%%a") do set "_k=%%x"
    for /f "tokens=* delims= " %%x in ("%%b") do set "_v=%%x"
    if "!_k!"=="[server]" set "_in_server=1"
    if "!_in_server!"=="1" (
        if /i "!_k!"=="host" set "SRV_HOST=!_v!"
        if /i "!_k!"=="port" set "SRV_PORT=!_v!"
    )
)
if not defined SRV_HOST set "SRV_HOST=0.0.0.0"
if not defined SRV_PORT set "SRV_PORT=8000"

:: Verifica build frontend
if not exist "frontend\dist\index.html" (
    echo  [AVVISO] Frontend non compilato. Esegui installa_web.bat prima di continuare.
    pause & exit /b 1
)

cls
echo.
echo  ================================================
echo   Foliarium Web — Server in esecuzione
echo.
echo   Database : %DB_HOST%:%DB_PORT%/%DB_NAME%
echo   Indirizzo: http://%SRV_HOST%:%SRV_PORT%
echo.
echo   Aprire nel browser: http://localhost:%SRV_PORT%
echo   Per fermare il server: Ctrl+C
echo  ================================================
echo.

python -m uvicorn api.main:create_app --factory --host %SRV_HOST% --port %SRV_PORT%

echo.
echo  Server fermato.
pause
