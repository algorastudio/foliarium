<#
.SYNOPSIS
    Inizializzazione database Foliarium per Windows
.DESCRIPTION
    Crea il database catasto_storico e applica tutti gli script SQL necessari.
    Compatibile con PostgreSQL 14+.
.PARAMETER PgHost
    Host del server PostgreSQL (default: localhost)
.PARAMETER PgPort
    Porta del server PostgreSQL (default: 5432)
.PARAMETER PgUser
    Utente amministratore PostgreSQL (default: postgres)
.PARAMETER PgPass
    Password dell'utente postgres
.PARAMETER AdminEmail
    Email dell'amministratore Foliarium (default: admin@archivio.savona.it)
.PARAMETER Silent
    Modalità silenziosa per deploy automatico (SCCM/GPO)
.EXAMPLE
    .\setup-database.ps1 -PgPass "mia_password"
.EXAMPLE
    .\setup-database.ps1 -PgHost "dbserver" -PgPort "5432" -PgPass "pass" -Silent
#>
param(
    [string]$PgHost = "localhost",
    [string]$PgPort = "5432",
    [string]$PgUser = "postgres",
    [string]$PgPass = "",
    [string]$AdminEmail = "admin@archivio.savona.it",
    [switch]$Silent,
    [switch]$SaveCreds
)

# ---------------------------------------------------------------------------
# Funzioni di output colorato
# ---------------------------------------------------------------------------

function Write-OK {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Error-Msg {
    param([string]$Message)
    Write-Host "[ERRORE] $Message" -ForegroundColor Red
}

function Write-Warning-Msg {
    param([string]$Message)
    Write-Host "[AVVISO] $Message" -ForegroundColor Yellow
}

function Write-Step {
    param([string]$Message)
    Write-Host "`n>>> $Message" -ForegroundColor Cyan
}

# ---------------------------------------------------------------------------
# Avvio script
# ---------------------------------------------------------------------------

$StartTime = Get-Date

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Foliarium — Inizializzazione Database PostgreSQL" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ---------------------------------------------------------------------------
# Ricerca psql.exe
# ---------------------------------------------------------------------------

Write-Step "Ricerca di psql.exe..."

$PsqlPath = $null

# Controlla prima nel PATH
$PsqlInPath = Get-Command psql -ErrorAction SilentlyContinue
if ($PsqlInPath) {
    $PsqlPath = $PsqlInPath.Source
    Write-OK "psql trovato nel PATH: $PsqlPath"
}

# Ricerca in C:\Program Files\PostgreSQL\*\bin\psql.exe
if (-not $PsqlPath) {
    $PgInstalls = Get-Item "C:\Program Files\PostgreSQL\*\bin\psql.exe" -ErrorAction SilentlyContinue
    if ($PgInstalls) {
        # Prende la versione più recente (ordine decrescente per percorso)
        $PsqlPath = ($PgInstalls | Sort-Object FullName -Descending | Select-Object -First 1).FullName
        Write-OK "psql trovato: $PsqlPath"
    }
}

if (-not $PsqlPath) {
    Write-Error-Msg "psql.exe non trovato. Installare PostgreSQL 14+ e aggiungere il bin al PATH."
    exit 1
}

# ---------------------------------------------------------------------------
# Richiesta password se non fornita
# ---------------------------------------------------------------------------

if ([string]::IsNullOrEmpty($PgPass)) {
    if ($Silent) {
        Write-Error-Msg "Modalità silenziosa attiva ma nessuna password fornita (-PgPass)."
        exit 1
    }
    Write-Host ""
    Write-Host "Inserire la password per l'utente PostgreSQL '$PgUser':" -ForegroundColor White
    $SecurePass = Read-Host -AsSecureString
    $Bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecurePass)
    try {
        $PgPass = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($Bstr)
    } finally {
        [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Bstr)
    }
}

# ---------------------------------------------------------------------------
# Impostazione variabile d'ambiente per psql
# ---------------------------------------------------------------------------

$env:PGPASSWORD = $PgPass

# Percorso base degli script SQL
$SqlBase = Join-Path $PSScriptRoot "..\sql_scripts"
$SqlBase = [System.IO.Path]::GetFullPath($SqlBase)

Write-Host ""
Write-Host "  Host:         $PgHost"
Write-Host "  Porta:        $PgPort"
Write-Host "  Utente:       $PgUser"
Write-Host "  Script SQL:   $SqlBase"
Write-Host ""

# ---------------------------------------------------------------------------
# Elenco script da eseguire
# ---------------------------------------------------------------------------

$Scripts = @(
    @{ File = "01_creazione-database.sql";       Db = "postgres";         Desc = "Creazione database catasto_storico" },
    @{ File = "02_creazione-schema-tabelle.sql"; Db = "catasto_storico";  Desc = "Creazione schema e tabelle" },
    @{ File = "03_funzioni-procedure.sql";       Db = "catasto_storico";  Desc = "Funzioni e procedure" },
    @{ File = "07_user-management.sql";          Db = "catasto_storico";  Desc = "Gestione utenti" },
    @{ File = "07a_bootstrap_admin.sql";         Db = "catasto_storico";  Desc = "Bootstrap amministratore" },
    @{ File = "10_performance-optimization.sql"; Db = "catasto_storico";  Desc = "Ottimizzazione performance" }
)

$ScriptsRun = 0

# ---------------------------------------------------------------------------
# Esecuzione script
# ---------------------------------------------------------------------------

try {
    foreach ($Script in $Scripts) {
        $ScriptPath = Join-Path $SqlBase $Script.File
        Write-Step "[$($ScriptsRun + 1)/$($Scripts.Count)] $($Script.Desc)"
        Write-Host "  File: $($Script.File)" -ForegroundColor Gray
        Write-Host "  DB:   $($Script.Db)" -ForegroundColor Gray

        if (-not (Test-Path $ScriptPath)) {
            Write-Error-Msg "Script non trovato: $ScriptPath"
            exit 1
        }

        $PsqlArgs = @(
            "-h", $PgHost,
            "-p", $PgPort,
            "-U", $PgUser,
            "-d", $Script.Db,
            "-f", $ScriptPath,
            "--no-password",
            "-v", "ON_ERROR_STOP=1"
        )

        & $PsqlPath @PsqlArgs
        $ExitCode = $LASTEXITCODE

        if ($ExitCode -ne 0) {
            Write-Error-Msg "Errore durante l'esecuzione di '$($Script.File)' (codice: $ExitCode)."
            Write-Error-Msg "Inizializzazione interrotta."
            exit 1
        }

        Write-OK "Script eseguito con successo: $($Script.File)"
        $ScriptsRun++
    }

    # ---------------------------------------------------------------------------
    # Salvataggio credenziali in Windows Credential Manager
    # ---------------------------------------------------------------------------

    $SaveToCredManager = $false

    if ($Silent -and $SaveCreds) {
        $SaveToCredManager = $true
    } elseif (-not $Silent) {
        Write-Host ""
        $Answer = Read-Host "Salvare le credenziali in Windows Credential Manager? [S/N]"
        if ($Answer -match "^[Ss]$") {
            $SaveToCredManager = $true
        }
    }

    if ($SaveToCredManager) {
        Write-Step "Salvataggio credenziali in Windows Credential Manager..."
        cmdkey /generic:FOLIARIUM_DB /user:$PgUser /pass:$PgPass | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-OK "Credenziali salvate con voce 'FOLIARIUM_DB'."
        } else {
            Write-Warning-Msg "Impossibile salvare le credenziali nel Credential Manager."
        }
    }

    # ---------------------------------------------------------------------------
    # Riepilogo finale
    # ---------------------------------------------------------------------------

    $Elapsed = (Get-Date) - $StartTime
    $ElapsedStr = "{0:mm\:ss}" -f $Elapsed

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "  Inizializzazione completata con successo!" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Script eseguiti:  $ScriptsRun / $($Scripts.Count)" -ForegroundColor White
    Write-Host "  Tempo impiegato:  $ElapsedStr" -ForegroundColor White
    Write-Host ""
    Write-Host "  Per avviare Foliarium:" -ForegroundColor White
    Write-Host "    python gui_main.py" -ForegroundColor Gray
    Write-Host "    oppure eseguire Foliarium.exe dalla cartella di installazione." -ForegroundColor Gray
    Write-Host ""

} finally {
    # Pulizia variabile d'ambiente con la password
    $env:PGPASSWORD = ""
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}
