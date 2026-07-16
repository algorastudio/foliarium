# Handoff — Security & Compliance Hardening

> Documento di continuità per riprendere il lavoro in una sessione successiva.
> Punto di partenza: domanda "il software è affidabile su sicurezza e norme
> vigenti?" → security review + una serie di interventi.
> Branch di sviluppo: `claude/charming-galileo-0ixhz4`.

## 1. Stato complessivo

Tutti i finding tecnici della security review iniziale sono **risolti o in
review**. Sequenza delle PR (tutte su `main`):

| PR | Contenuto | Stato |
|---|---|---|
| #123 | Enforcement scope API granulari + rate limiting chiavi API | ✅ merged |
| #124 | TLS connessione DB (`sslmode`) + policy password rafforzata | ✅ merged |
| #125 | Cifratura at-rest dei backup (AES-256-GCM) | ✅ merged |
| #126 | Export/import chiave backup + GDPR anonimizzazione possessore | ✅ merged |
| #127 | Retention audit configurabile + modelli GDPR + firma del codice | 🟢 in review |

> Nota workflow: si sviluppa **solo** sul branch `claude/charming-galileo-0ixhz4`.
> Le PR precedenti venivano mergiate rapidamente; i commit successivi finivano a
> volte nella PR aperta successiva (da qui alcune PR "bundle"). Per la prossima
> sessione: verificare se #127 è merged prima di aprire nuove PR.

## 2. Dettaglio interventi (con riferimenti al codice)

### Sicurezza API (#123)
- `api/deps.py` — `require_scope()` ora **applicato** a tutte le route
  (`api/routes/*.py`): GET → `read:<risorsa>`, POST/PATCH/DELETE →
  `write:<risorsa>`. Le route `auth` (`/me`,`/logout`) restano su
  `get_current_session`.
- `api/rate_limit.py` — rate limiter in-memory per `api_key_id` (fixed window/
  minuto); `get_current_session` risponde `429` + `Retry-After`.
- Scope `write:comuni` aggiunto alla UI chiavi API.
- Test: `tests/unit/test_api_route_scopes.py`, `test_api_rate_limit.py`.

### TLS DB + password (#124)
- `db/base.py` — `DBConnectionBase._resolve_sslmode(sslmode, host)`: esplicito →
  `config.ENV_DB_SSLMODE` → default per host (`prefer` locale, `require` remoto).
  Salvato in `_main_db_conn_params["sslmode"]`.
- `config.py` — `ENV_DB_SSLMODE` (env `DB_SSLMODE` / `config.ini`).
- `validators.py` — `password_strength`: min 10 char + maiusc/minusc/cifra +
  denylist (`MIN_PASSWORD_LENGTH`, `COMMON_WEAK_PASSWORDS`). Helper admin ora
  delega a `FieldValidator` (fonte unica).
- Test: `test_db_sslmode.py`; aggiornati `test_validators_exceptions.py`,
  `test_new_modules.py`.

### Cifratura backup (#125) + chiave (#126)
- `foliarium/core/services/backup_crypto.py` — AES-256-GCM streaming (chunk
  1 MiB); chiave nel **keyring** (`Foliarium_BackupKey`). Funzioni: `encrypt_backup`,
  `decrypt_backup_to_temp`, `secure_delete`, `is_encrypted_file`,
  `export_key_to_file`/`import_key_from_file` (wrap passphrase scrypt+AES-GCM),
  `has_backup_key`.
- `foliarium/ui/widgets/admin/backup.py` — checkbox "Cifra il file di backup" +
  pulsanti "Esporta/Importa chiave...". Ripristino trasparente dei file `.enc`.
- `requirements.txt` — `cryptography` dichiarato.
- Test: `tests/unit/test_backup_crypto.py` (26).

### GDPR anonimizzazione (#126)
- `db/possessori.py` — `anonimizza_possessore(possessore_id, eseguito_da=None)`:
  sostituisce nome/cognome con `POSSESSORE_ANONYMIZED_LABEL`, azzera paternità,
  mantiene i legami con le partite (scelta: in-place, non hard delete).
- `foliarium/ui/dialogs/entity/possessore.py` — pulsante "Anonimizza (GDPR)"
  con doppia conferma. Export possessore già esistente (`export_possessore_json`).
- Test: `tests/unit/test_db_anonimizza_possessore.py` (9).

### Retention audit (#127)
- `db/audit.py` — `cleanup_audit_logs` **parametrizzata** (`make_interval(days => %s)`).
- `foliarium/core/services/audit_retention.py` — policy in giorni in `QSettings`
  (`0` = off); `get/set/apply/run_startup`.
- `config.py` — `SETTINGS_AUDIT_RETENTION_DAYS`.
- `foliarium/ui/widgets/admin/audit.py` — checkbox "Applica all'avvio".
- `gui_main.py` — `run_startup_retention` best-effort post-login.
- Test: `tests/unit/test_audit_retention.py` (12).

### Documenti GDPR (bozze) (#127)
- `docs/compliance/`: `README.md`, `informativa-privacy.md`,
  `registro-trattamenti.md`, `dpia.md`, `misure-sicurezza.md` (+ nav mkdocs,
  link da `docs/admin/privacy-gdpr.md`). **Template con segnaposto**, da validare
  da consulente/DPO.

### Firma del codice (#127)
- Certificato: **Certum Code Signing** (individuale, "Marco Santoro"),
  firma **cloud SimplySign**, OTP da app smartphone → **firma locale al rilascio**
  (non automatizzabile su runner GitHub-hosted).
- `signing/sign.ps1`, `signing/build-signed-installer.ps1`, `signing/README.md`.
- `Foliarium_Installer.iss` — `SignTool`/`SignedUninstaller` opt-in con `/DSIGN`.
- File `.cer`/`.p7b` forniti dall'utente = solo parte pubblica (chiave in HSM).

## 3. Cose ancora aperte / prossimi passi

- [ ] **Merge PR #127** (o verifica CI e review).
- [ ] **Adozione formale dei documenti GDPR** — compila i segnaposto `[…]` e fai
      validare (compete al Titolare, non è codice).
- [ ] **Firma release**: al prossimo rilascio, su Windows con SimplySign Desktop
      loggato: `pyinstaller foliarium.spec` → `.\signing\build-signed-installer.ps1 -Version X.Y.Z`.
- [ ] (Opz.) Retention audit: valutare una **pianificazione periodica** oltre
      all'applicazione all'avvio.
- [ ] (Opz.) Verificare che l'export dei log di supporto (`app_utils.create_logs_archive`)
      non includa dati personali prima della consegna.

## 4. Note ambientali per riprendere velocemente

- **Test rapidi (headless)**: `python -m pytest <file> -o addopts="" -p no:cacheprovider -q`
  (il `-o addopts=""` bypassa i flag `--cov` di `pytest.ini`).
- Dipendenze utili in locale: `pytest fastapi httpx psycopg2-binary bcrypt cryptography keyring cffi`.
- **PyQt6 non è installato** nell'ambiente di dev headless: i moduli che importano
  `config`/PyQt6 falliscono in import → i test che li toccano vanno resi tolleranti
  (vedi `test_db_sslmode.py` skip, `audit_retention` usa un `RETENTION_DAYS_KEY`
  locale per non importare `config`). In CI PyQt6 c'è.
- **cryptography** localmente era rotta (`_cffi_backend` mancante) finché non si
  installa `cffi`.
- Convenzione PyQt6: **enum sempre namespacizzati** (vedi CLAUDE.md).

## 5. Riferimenti

- CLAUDE.md (istruzioni progetto, aggiornato con sslmode e backup_crypto).
- `docs/admin/privacy-gdpr.md`, `docs/admin/backup.md`, `docs/admin/installazione.md`.
- Repo GitHub scope sessione: `algorastudio/foliarium`.
