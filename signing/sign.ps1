<#
.SYNOPSIS
    Firma Authenticode di uno o più file con il certificato Certum SimplySign
    (firma in cloud), usando signtool.

.DESCRIPTION
    Richiede che SimplySign Desktop sia in esecuzione e che la sessione sia
    sbloccata (login con l'OTP dell'app sullo smartphone): il certificato è
    allora disponibile come "carta virtuale" nello store CurrentUser\My e
    signtool può usarlo selezionandolo per nome (CN) o impronta (thumbprint).

    La chiave privata NON lascia mai l'HSM di Certum: signtool delega la firma
    al provider cloud tramite la carta virtuale.

.EXAMPLE
    .\sign.ps1 -Files dist\Foliarium\Foliarium.exe

.EXAMPLE
    .\sign.ps1 -Files a.exe,b.exe -Thumbprint 1A2B3C...  -TimestampUrl http://time.certum.pl
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string[]] $Files,

    # Seleziona il certificato per CN (default) oppure usa -Thumbprint.
    [string] $SubjectName = "MARCO SANTORO",
    [string] $Thumbprint = "",

    # Timestamp RFC3161 di Certum (indispensabile: la firma resta valida dopo
    # la scadenza del certificato).
    [string] $TimestampUrl = "http://time.certum.pl",

    [string] $Description = "Foliarium"
)

$ErrorActionPreference = "Stop"

function Find-SignTool {
    $cmd = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $roots = @(
        "${env:ProgramFiles(x86)}\Windows Kits\10\bin",
        "${env:ProgramFiles}\Windows Kits\10\bin"
    )
    foreach ($r in $roots) {
        if (Test-Path $r) {
            $found = Get-ChildItem -Path $r -Recurse -Filter signtool.exe -ErrorAction SilentlyContinue |
                     Where-Object { $_.FullName -match '\\x64\\' } |
                     Sort-Object FullName -Descending | Select-Object -First 1
            if ($found) { return $found.FullName }
        }
    }
    throw "signtool.exe non trovato. Installa il 'Windows SDK Signing Tools'."
}

$signtool = Find-SignTool
Write-Host "signtool : $signtool"
Write-Host "timestamp: $TimestampUrl"

$selector = if ($Thumbprint) { @("/sha1", $Thumbprint) } else { @("/n", $SubjectName) }
Write-Host ("certificato: " + ($(if ($Thumbprint) { "thumbprint $Thumbprint" } else { "CN '$SubjectName'" })))

foreach ($f in $Files) {
    if (-not (Test-Path $f)) { throw "File non trovato: $f" }
    Write-Host "`n>> Firma: $f"
    & $signtool sign @selector /fd sha256 /tr $TimestampUrl /td sha256 /d $Description $f
    if ($LASTEXITCODE -ne 0) { throw "Firma fallita per '$f' (exit $LASTEXITCODE)." }
}

Write-Host "`n>> Verifica firme..."
foreach ($f in $Files) {
    & $signtool verify /pa /v $f
    if ($LASTEXITCODE -ne 0) { throw "Verifica firma fallita per '$f'." }
}

Write-Host "`nFirma completata e verificata." -ForegroundColor Green
