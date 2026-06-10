@echo off
chcp 65001 > nul
echo.
echo  ================================================
echo   Foliarium Web — Installazione dipendenze
echo  ================================================
echo.

:: Verifica Python
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERRORE] Python non trovato. Installare Python 3.10+ da python.org
    pause & exit /b 1
)

:: Verifica Node.js
node --version > nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERRORE] Node.js non trovato. Installare Node.js 18+ da nodejs.org
    pause & exit /b 1
)

echo  [1/3] Installazione dipendenze Python...
pip install fastapi "uvicorn[standard]" psycopg2-binary bcrypt pydantic
if %errorlevel% neq 0 (
    echo  [ERRORE] Installazione Python fallita.
    pause & exit /b 1
)

echo.
echo  [2/3] Installazione dipendenze frontend...
cd frontend
call npm install
if %errorlevel% neq 0 (
    echo  [ERRORE] npm install fallita.
    cd ..
    pause & exit /b 1
)

echo.
echo  [3/3] Build interfaccia web...
call npm run build
cd ..
if %errorlevel% neq 0 (
    echo  [ERRORE] Build frontend fallita.
    pause & exit /b 1
)

echo.
echo  ================================================
echo   Installazione completata!
echo.
echo   Modifica web.ini con le credenziali del
echo   database, poi avvia con: avvia_server.bat
echo  ================================================
echo.
pause
