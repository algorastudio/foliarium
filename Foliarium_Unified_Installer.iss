; ============================================================================
; Foliarium_Unified_Installer.iss
; Installer unificato: Foliarium + PostgreSQL + Database
;
; Sequenza:
;   1. Copia app (PyInstaller) + pgsql/ binaries + sql_scripts/
;   2. Genera password casuale per il DB
;   3. Esegue setup_database.bat (initdb, servizio, schema, admin)
;   4. Scrive config.ini con le credenziali locali
;   5. Crea collegamenti nel Menu Start e Desktop
;
; Disinstallazione:
;   1. Ferma e rimuove il servizio Windows FoliariumDB
;   2. Rimuove pg_data/ (dati del database)
;   3. Rimuove tutti i file dell'applicazione
; ============================================================================

#define MyAppName "Foliarium"
#define MyAppVersion "1.6.0"
#define MyAppPublisher "Marco Santoro"
#define MyAppURL "https://github.com/saintgold74/catasto"
#define MyAppExeName "Foliarium.exe"
#define MyCopyright "Copyright (C) Marco Santoro. In gentile concessione gratuita all'Archivio di Stato di Savona."

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=Installer
OutputBaseFilename=Foliarium_{#MyAppVersion}_Unified_Setup
SetupIconFile=resources\icona_foliarium.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Richiede admin per registrare il servizio Windows
PrivilegesRequired=admin
; Dimensione minima approssimativa (app ~150MB + pgsql ~120MB)
ExtraDiskSpaceRequired=300000000

; Informazioni versione
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Installazione di Foliarium con PostgreSQL integrato
VersionInfoCopyright={#MyCopyright}

; EULA
LicenseFile=resources\EULA.rtf

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[CustomMessages]
italian.InstallingDB=Configurazione database in corso...
italian.DBSuccess=Database inizializzato con successo
italian.DBError=Errore durante la configurazione del database. Consultare il file setup_database.log nella cartella di installazione.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; --- Applicazione Foliarium (output PyInstaller) ---
Source: "dist\{#MyAppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; --- PostgreSQL binaries (bin + lib + share — necessari per il server) ---
Source: "pgsql\bin\*"; DestDir: "{app}\pgsql\bin"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "pgsql\lib\*"; DestDir: "{app}\pgsql\lib"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "pgsql\share\*"; DestDir: "{app}\pgsql\share"; Flags: ignoreversion recursesubdirs createallsubdirs

; --- Script SQL per inizializzazione schema ---
Source: "sql_scripts\02_creazione-schema-tabelle.sql"; DestDir: "{app}\sql_scripts"; Flags: ignoreversion
Source: "sql_scripts\03_funzioni-procedure.sql"; DestDir: "{app}\sql_scripts"; Flags: ignoreversion
Source: "sql_scripts\07_user-management.sql"; DestDir: "{app}\sql_scripts"; Flags: ignoreversion
Source: "sql_scripts\07a_bootstrap_admin.sql"; DestDir: "{app}\sql_scripts"; Flags: ignoreversion

; --- Script di setup e uninstall database ---
Source: "setup_database.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "uninstall_database.bat"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Disinstalla {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Esegue il setup del database dopo la copia dei file
; La password viene generata dal codice Pascal (vedi sotto)
Filename: "{app}\setup_database.bat"; \
    Parameters: """{app}"" ""{code:GetDBPassword}"" ""{code:GetAdminPassword}"""; \
    StatusMsg: "{cm:InstallingDB}"; \
    Flags: runhidden waituntilterminated; \
    BeforeInstall: GeneratePasswords

; Avvia l'applicazione (opzionale)
Filename: "{app}\{#MyAppExeName}"; \
    Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; \
    Flags: nowait postinstall skipifsilent

[UninstallRun]
; Ferma e rimuove il servizio PostgreSQL prima della disinstallazione
Filename: "{app}\uninstall_database.bat"; \
    Parameters: """{app}"""; \
    Flags: runhidden waituntilterminated

[Code]
// ============================================================================
// Codice Pascal per Inno Setup
// Genera password casuali per PostgreSQL e l'utente admin
// ============================================================================

var
  DBPassword: String;
  AdminPassword: String;

// Genera una password casuale alfanumerica di lunghezza N
function GenerateRandomPassword(Len: Integer): String;
var
  I: Integer;
  Chars: String;
begin
  Chars := 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  Result := '';
  for I := 1 to Len do
  begin
    Result := Result + Chars[Random(Length(Chars)) + 1];
  end;
end;

// Chiamata da BeforeInstall del [Run] — genera le password
procedure GeneratePasswords;
begin
  if DBPassword = '' then
    DBPassword := GenerateRandomPassword(16);
  if AdminPassword = '' then
    AdminPassword := GenerateRandomPassword(12);
end;

// Funzioni accessor per usare {code:...} nei parametri
function GetDBPassword(Param: String): String;
begin
  if DBPassword = '' then
    GeneratePasswords;
  Result := DBPassword;
end;

function GetAdminPassword(Param: String): String;
begin
  if AdminPassword = '' then
    GeneratePasswords;
  Result := AdminPassword;
end;

// Mostra un messaggio post-installazione con le credenziali admin
procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigFile: String;
begin
  if CurStep = ssPostInstall then
  begin
    ConfigFile := ExpandConstant('{app}\config.ini');
    if FileExists(ConfigFile) then
    begin
      MsgBox(
        'Foliarium è stato installato con successo!' + #13#10 + #13#10 +
        'Il database PostgreSQL è stato configurato automaticamente.' + #13#10 + #13#10 +
        'Credenziali amministratore:' + #13#10 +
        '  Utente: admin' + #13#10 +
        '  Password: admin123' + #13#10 + #13#10 +
        'IMPORTANTE: Cambiare la password al primo accesso!' + #13#10 + #13#10 +
        'Il servizio database (FoliariumDB) si avvia automaticamente con Windows.',
        mbInformation, MB_OK);
    end
    else
    begin
      MsgBox(
        'Attenzione: il file config.ini non è stato creato.' + #13#10 +
        'Consultare il file setup_database.log per i dettagli.' + #13#10 +
        'Potrebbe essere necessario configurare il database manualmente.',
        mbError, MB_OK);
    end;
  end;
end;

// Prima della disinstallazione: avvisa l'utente
function InitializeUninstall(): Boolean;
begin
  Result := MsgBox(
    'La disinstallazione rimuoverà anche il database PostgreSQL e tutti i dati.' + #13#10 +
    'Si consiglia di effettuare un backup prima di procedere.' + #13#10 + #13#10 +
    'Continuare con la disinstallazione?',
    mbConfirmation, MB_YESNO) = IDYES;
end;
