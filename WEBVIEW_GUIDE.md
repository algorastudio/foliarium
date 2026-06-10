# Foliarium WebView Integration Guide

Guida completa per sviluppatori su come usare la nuova integrazione **PyWebView + FastAPI + React**.

## 📋 Sommario

- [Architettura](#architettura)
- [Avvio in Development](#avvio-in-development)
- [Build Production](#build-production)
- [Coesistenza PyWebView ↔ PyQt6](#coesistenza-pywebview--pyqt6)
- [Comandi Utili](#comandi-utili)
- [Troubleshooting](#troubleshooting)

---

## 🏗️ Architettura

```
┌──────────────────────────────────────────────────────────────┐
│                    Foliarium.exe (single app)                │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────┐         ┌──────────────────────┐   │
│  │   PyWebView         │         │  PyQt6 (fallback)    │   │
│  │  ┌───────────────┐  │         │  ┌────────────────┐  │   │
│  │  │ Chromium-like │  │         │  │ QMainWindow +  │  │   │
│  │  │  Browser      │  │         │  │ QWidgets       │  │   │
│  │  └───────┬───────┘  │         │  └────────────────┘  │   │
│  └──────────┼──────────┘         └──────────────────────┘   │
│             │                           │                    │
│  ┌──────────▼──────────┐   ┌────────────▼──────────┐         │
│  │  http://127.0.0.1   │   │  QSqlDatabase +       │         │
│  │      :8765          │   │  CatastoDBManager     │         │
│  └──────────┬──────────┘   └────────────────────────┘         │
│             │                                                 │
│  ┌──────────▼──────────────────────────────────────────┐     │
│  │         FastAPI Server (uvicorn)                    │     │
│  │         Porta: dinamica (8765+)                     │     │
│  │                                                      │     │
│  │  ┌──────────────┐  ┌──────────┐  ┌──────────┐      │     │
│  │  │  /api routes │  │ /static  │  │ JS API   │      │     │
│  │  │  (auth, DB)  │  │ (dist/)  │  │ (expose) │      │     │
│  │  └──────────────┘  └──────────┘  └──────────┘      │     │
│  └──────────┬──────────────────────────────────────────┘     │
│             │                                                 │
│  ┌──────────▼──────────────────────────────────────────┐     │
│  │        React Frontend (dist/)                       │     │
│  │                                                      │     │
│  │  ┌─────────┐  ┌─────────┐  ┌──────────────┐        │     │
│  │  │ Login   │  │ Archivio│  │ Genealogia   │  ...   │     │
│  │  │ Page    │  │ Ricerca │  │ Partita      │        │     │
│  │  └─────────┘  └─────────┘  └──────────────┘        │     │
│  └────────────────────────────────────────────────────┘     │
│             │                                                 │
│  ┌──────────▼──────────────────────────────────────────┐     │
│  │        PostgreSQL 14+                               │     │
│  │        catasto_storico database                     │     │
│  │        (locale o remote)                            │     │
│  └──────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────┘
```

### Componenti

| Layer | Tecnologia | Descrizione |
|-------|-----------|-------------|
| **UI** | PyWebView (Chromium) | Finestra moderna con web view |
| **Fallback** | PyQt6 + QWebEngineView | UI classica se PyWebView fallisce |
| **Backend HTTP** | FastAPI + uvicorn | Server API REST, porta dinamica |
| **Frontend** | React 19 + TypeScript | SPA modern, compilata a dist/ |
| **Database** | psycopg2 → PostgreSQL | Stesso backend v1.6.1 |
| **Config** | config.py, QSettings | Credenziali DB, licenze, preferenze |

---

## 🚀 Avvio in Development

### Prerequisiti

```bash
# Python 3.12+
python --version

# Node.js 18+ (per frontend)
node --version

# PostgreSQL 14+ (database)
# O usare --demo flag per PostgreSQL embedded
```

### 1️⃣ Setup Ambiente (solo la prima volta)

```bash
# 1. Clona il repo e entra in cartella
cd foliarium

# 2. Installa dipendenze Python
pip install -r requirements.txt

# 3. Installa dipendenze React
cd frontend && npm install && cd ..

# 4. Setup database (vedi CLAUDE.md per credenziali)
# Oppure usa --demo flag per PostgreSQL embedded
```

### 2️⃣ Dev Mode (Vite HMR + FastAPI live)

**Terminal 1: FastAPI Backend**
```bash
# Avvia server FastAPI sulla porta dinamica
python -m uvicorn api.main:create_app --host 127.0.0.1 --port 8765 --reload
```

**Terminal 2: React Frontend (Vite dev server)**
```bash
cd frontend
npm run dev
# Output: http://localhost:5173
```

**Terminal 3: Launcher PyWebView (opzionale)**
```bash
# Tenta PyWebView, fallback a PyQt6
python webview_main.py --dev

# O forza PyQt6 + QWebEngineView
python webview_main.py --use-pyqt6 --dev

# Oppure apri browser manualmente: http://localhost:5173
```

**Note:**
- `--dev` flag salta build React (usa Vite dev server live con HMR)
- Vite dev server proxy `/api` a `http://127.0.0.1:8765` (vedi vite.config.ts)
- Modifche React sono hot-reload (no refresh browser)

### 3️⃣ Dev Mode Demo (PostgreSQL embedded)

```bash
# Launch con PostgreSQL embedded (porta 15432)
python webview_main.py --demo --dev --debug
```

---

## 📦 Build Production

### Step 1: Build Frontend React

```bash
cd frontend
npm run build
# Output: frontend/dist/ (index.html + assets/)
```

### Step 2: Build PyInstaller (executabile)

```bash
# Installa PyInstaller se non presente
pip install pyinstaller

# Build con spec personalizzato
pyinstaller foliarium_webview.spec

# Output: ./dist/Foliarium/
```

### Step 3: Test eseguibile

```bash
# Windows
./dist/Foliarium/Foliarium.exe

# Linux/macOS
./dist/Foliarium/Foliarium

# Tenta PyWebView, fallback a PyQt6
```

### Step 4: Pacchettizzazione (opzionale)

```bash
# Create ZIP per distribuzione
cd dist
tar -czf Foliarium_v1.7.0_Linux.tar.gz Foliarium/
zip -r Foliarium_v1.7.0_Windows.zip Foliarium/
```

---

## 🔄 Coesistenza PyWebView ↔ PyQt6

### Logica Fallback

1. **PyWebView** (primaria)
   - Richiede `pywebview` installato
   - Richiede frontend React compilato (`dist/index.html`)
   - Richiede FastAPI avvio corretto

2. **QWebEngineView** (fallback secondario)
   - Richiede `PyQt6-WebEngine` installato
   - Usa la stessa app PyQt6 ClassicaUI
   - Carica http://127.0.0.1:PORT nel QWebEngineView

3. **Browser di sistema** (fallback terziario)
   - Apre URL in browser default
   - Mostra label con link al server

### Forzare Modalità

```bash
# Tenta PyWebView, fallback a QWebEngineView → browser
python webview_main.py

# Forza subito PyQt6 (salta PyWebView)
python webview_main.py --use-pyqt6

# Dev mode: Vite dev server, no build React
python webview_main.py --dev

# Demo mode: PostgreSQL embedded
python webview_main.py --demo

# Combina flag
python webview_main.py --demo --dev --use-pyqt6
```

### Config File Opzionale

Crea `~/.foliarium/ui_mode.cfg` per ricordare la preferenza:
```ini
[ui]
# Opzioni: auto, pywebview, pyqt6
mode=pywebview
dev_mode=false
demo_mode=false
```

---

## 🛠️ Comandi Utili

### Frontend React

```bash
cd frontend

# Avvio dev server (localhost:5173)
npm run dev

# Build production (frontend/dist/)
npm run build

# Linting
npm run lint

# Preview del build
npm run preview
```

### Backend Python

```bash
# Avvia solo FastAPI (porta 8765)
python -m uvicorn api.main:create_app --reload

# Avvia solo PyQt6 (UI classica)
python gui_main.py

# Avvia launcher intelligente (tenta PyWebView)
python webview_main.py

# Launcher con logging verbose
python webview_main.py --debug

# Launcher con demo mode
python webview_main.py --demo
```

### Database

```bash
# Connessione psql
psql -h localhost -U postgres -d catasto_storico

# Esegui script SQL
psql -h localhost -U postgres -d catasto_storico -f sql_scripts/02_creazione-schema-tabelle.sql

# Dump database
pg_dump -h localhost -U postgres catasto_storico > backup.sql
```

### PyInstaller

```bash
# Build eseguibile
pyinstaller foliarium_webview.spec

# Build onefile (più lento, output singolo .exe)
pyinstaller foliarium_webview.spec --onefile

# Build con debug (riporta errori)
pyinstaller foliarium_webview.spec --debug=imports
```

---

## 🐛 Troubleshooting

### ❌ "pywebview non trovato"

```bash
pip install pywebview
```

**Oppure:** Fallback a PyQt6
```bash
python webview_main.py --use-pyqt6
```

### ❌ "frontend/dist non trovato"

Il launcher tenta auto-build. Se fallisce:

```bash
cd frontend
npm run build
# Verifica: frontend/dist/index.html deve esistere
```

### ❌ "FastAPI non avvia"

Controlla porta:
```bash
# Porta 8765 occupata? Tenta otra porta
netstat -an | grep 8765  # Windows: netstat -ano | findstr 8765

# Kill processo occupante
lsof -i :8765 | xargs kill -9
```

Oppure log dettagliato:
```bash
python webview_main.py --debug
```

### ❌ "Connessione database fallita"

```bash
# Verifica credenziali config.ini
cat config.ini | grep -A3 '\[database\]'

# Verifica DB è online
psql -h localhost -U postgres -d catasto_storico -c "SELECT 1"

# Oppure usa --demo per PostgreSQL embedded
python webview_main.py --demo
```

### ❌ "React app bianca / carica infinito"

1. Verifica browser console (`F12`)
2. Verifica FastAPI rispondesu `/api/...` (vedi DevTools Network)
3. Verifica CORS configurato in `api/main.py`:
   ```python
   allow_origins=["http://localhost:5173", "http://127.0.0.1:8765", ...]
   ```
4. Se dev mode: verifica Vite dev server avviato su 5173

### ❌ "PyInstaller build fallisce"

```bash
# Pulisci e riprova
rm -rf build/ dist/ *.egg-info

# Verifica dipendenze
pip list | grep -E "PyInstaller|PyQt6|psycopg2|fastapi"

# Build con debug
pyinstaller foliarium_webview.spec --debug=imports --log-level=DEBUG
```

### ❌ "Frontend build infinito o timeout"

```bash
# Pulisci node_modules e riprova
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

---

## 📝 Development Workflow Consigliato

### 1️⃣ Setup Una Volta

```bash
git clone https://github.com/algorastudio/foliarium
cd foliarium
pip install -r requirements.txt
cd frontend && npm install && cd ..
```

### 2️⃣ Daily Development

**Terminal 1:**
```bash
python -m uvicorn api.main:create_app --host 127.0.0.1 --port 8765 --reload
```

**Terminal 2:**
```bash
cd frontend && npm run dev
```

**Terminal 3 (opzionale):**
```bash
python webview_main.py --dev
# Oppure apri browser: http://localhost:5173
```

### 3️⃣ Testing

```bash
# Unit test backend
pytest tests/unit/

# Integration test
pytest tests/integration/

# Frontend test (future)
cd frontend && npm test
```

### 4️⃣ Before Commit

```bash
# Lint React
cd frontend && npm run lint

# Build test
npm run build

# Eseguibile test (opzionale)
pyinstaller foliarium_webview.spec --clean
./dist/Foliarium/Foliarium.exe
```

---

## 📚 Ulteriori Risorse

- **CLAUDE.md** — Documentazione completa architettura, changelog, database schema
- **api/main.py** — Entry point FastAPI, configurazione routes
- **frontend/src/App.tsx** — Entry point React, routing
- **webview_main.py** — Launcher principale con logica fallback
- **foliarium_webview.spec** — PyInstaller spec per bundle
- **.github/workflows/** — CI/CD pipeline (GitHub Actions)

---

## 🤝 Contributing

Se modifichi il frontend React o backend FastAPI:

1. Testa in dev mode (`--dev`) con live reload
2. Verifica API endpoints con `curl` o Postman
3. Build eseguibile e testa con `pyinstaller`
4. Commita con messaggi descrittivi
5. Crea PR con descrizione del cambio

---

**Last Updated:** April 2026  
**Foliarium Version:** 1.7.0 (WebView edition)
