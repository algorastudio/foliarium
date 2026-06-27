<#
.SYNOPSIS
    Costruisce l'installer Foliarium FIRMATO: firma l'eseguibile prodotto da
    PyInstaller e poi compila l'installer Inno Setup firmando anche il setup e
    l'uninstaller.

.DESCRIPTION
    Flusso (Strada 1 — firma locale al rilascio):
      1. assicurati che SimplySign Desktop sia aperto e sbloccato (OTP da app);
      2. esegui PyInstaller (foliarium.spec) per generare dist\Foliarium;
      3. lancia questo script.

    Richiede: Windows SDK (signtool), Inno Setup 6 (ISCC), SimplySign Desktop.

.EXAMPLE
    .\build-signed-installer.ps1 -Version 1.0.2
#>
[CmdletBinding()]
param(
    [string] $Version = "1.0.2",
    [string] $ExePath = "dist\Foliarium\Foliarium.exe",
    [string] $Iss = "Foliarium_Installer.iss",
    [string] $SubjectName = "MARCO SANTORO",
    [string] $TimestampUrl = "http://time.certum.pl"
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Split-Path -Parent $here

function Find-Tool([string]$name, [string[]]$candidates) {
    $c = Get-Command $name -ErrorAction SilentlyContinue
    if ($c) { return $c.Source }
    foreach ($p in $candidates) { if ($p -and (Test-Path $p)) { return $p } }
    return $null
}

# --- Individua signtool (Windows SDK) ---
$signtool = Find-Tool "signtool.exe" @()
if (-not $signtool) {
    $kits = @("${env:ProgramFiles(x86)}\Windows Kits\10\bin", "${env:ProgramFiles}\Windows Kits\10\bin")
    foreach ($r in $kits) {
        if (Test-Path $r) {
            $f = Get-ChildItem $r -Recurse -Filter signtool.exe -ErrorAction SilentlyContinue |
                 Where-Object { $_.FullName -match '\\x64\\' } |
                 Sort-Object FullName -Descending | Select-Object -First 1
            if ($f) { $signtool = $f.FullName; break }
        }
    }
}
if (-not $signtool) { throw "signtool.exe non trovato (installa il Windows SDK Signing Tools)." }

# --- Individua ISCC (Inno Setup 6) ---
$iscc = Find-Tool "iscc.exe" @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
)
if (-not $iscc) { throw "ISCC.exe (Inno Setup 6) non trovato." }

$exeFull = Join-Path $repo $ExePath
if (-not (Test-Path $exeFull)) {
    throw "Eseguibile non trovato: $exeFull. Esegui prima PyInstaller (foliarium.spec)."
}

Write-Host "signtool : $signtool"
Write-Host "iscc     : $iscc"
Write-Host "exe      : $exeFull"

# --- 1. Firma l'eseguibile interno (così l'app installata è firmata) ---
& "$here\sign.ps1" -Files $exeFull -SubjectName $SubjectName -TimestampUrl $TimestampUrl

# --- 2. Compila l'installer firmandolo (SignTool 'certum' + uninstaller) ---
# Comando SignTool per Inno: $q = virgoletta letterale, $f = file da firmare.
$signCmd = "`$q$signtool`$q sign /n `$q$SubjectName`$q /fd sha256 /tr $TimestampUrl /td sha256 `$f"

Push-Location $repo
try {
    & $iscc "/DSIGN" "/DMyAppVersion=$Version" "/Scertum=$signCmd" $Iss
    if ($LASTEXITCODE -ne 0) { throw "ISCC ha restituito exit $LASTEXITCODE." }
}
finally {
    Pop-Location
}

Write-Host "`nInstaller firmato creato in: $repo\Installer\" -ForegroundColor Green
