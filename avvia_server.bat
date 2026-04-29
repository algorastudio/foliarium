@echo off
chcp 65001 > nul

:: Legge web.ini con Python (più affidabile del parsing batch)
for /f "delims=" %%i in ('python -c "
import configparser, sys
c = configparser.ConfigParser()
c.read('web.ini')
db = c['database']
srv = c['server']
print('DB_HOST=' + db.get('host','localhost'))
print('DB_PORT=' + db.get('port','5432'))
print('DB_NAME=' + db.get('name','catasto_storico'))
print('DB_USER=' + db.get('user','postgres'))
print('DB_PASS=' + db.get('password','postgres'))
print('SRV_HOST=' + srv.get('host','0.0.0.0'))
print('SRV_PORT=' + srv.get('port','8000'))
" 2^>nul') do set "%%i"

if not defined DB_NAME (
    echo  [ERRORE] web.ini non trovato o non leggibile.
    echo  Copia web.ini.example in web.ini e configura le credenziali.
    pause & exit /b 1
)

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
