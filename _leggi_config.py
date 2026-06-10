import configparser, sys

c = configparser.ConfigParser()
if not c.read('web.ini'):
    print("ERRORE: web.ini non trovato", file=sys.stderr)
    sys.exit(1)

db = c['database']
srv = c['server']
print("DB_HOST=" + db.get('host', 'localhost'))
print("DB_PORT=" + db.get('port', '5432'))
print("DB_NAME=" + db.get('name', 'catasto_storico'))
print("DB_SCHEMA=" + db.get('schema', 'catasto'))
print("DB_USER=" + db.get('user', 'postgres'))
print("DB_PASS=" + db.get('password', 'postgres'))
print("SRV_HOST=" + srv.get('host', '0.0.0.0'))
print("SRV_PORT=" + srv.get('port', '8000'))
