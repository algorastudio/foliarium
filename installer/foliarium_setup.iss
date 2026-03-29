; ===================================================================
;  Script Inno Setup per Foliarium
;  Genera: Foliarium_Setup_v1.0.0.exe
;  Autore: Marco Santoro — ALGORASTUDIO
;  Requisito: Inno Setup 6+ (https://jrsoftware.org/isinfo.php)
;
;  PRIMA DI USARE QUESTO SCRIPT:
;  1. Eseguire build.bat per generare dist\Foliarium.exe
;  2. Aprire questo file in Inno Setup Compiler
;  3. Premere F9 (Build) o Compile
; ===================================================================

#define AppName         "Foliarium"
#define AppVersion      "1.0.0"
#define AppPublisher    "ALGORASTUDIO — Marco Santoro"
#define AppURL          "https://www.algorastudio.it"
#define AppExeName      "Foliarium.exe"
#define AppDescription  "Gestionale Catasto Storico per Archivi di Stato"

[Setup]
AppId={{8F3B7C2A-4D1E-4F5A-9B6C-3E2D1A0F8C7B}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes

; Licenza mostrata durante l'installazione
LicenseFile=..\LICENSE

; Output
OutputDir=..\release
OutputBaseFilename=Foliarium_Setup_v{#AppVersion}

; Icona installer — decommentare quando logo_foliarium.ico è disponibile
; SetupIconFile=..\resources\logo_foliarium.ico

; Compressione
Compression=lzma2/ultra64
SolidCompression=yes

; Richiede Windows 10 o superiore (6.2 = Windows 8, 10.0 = Windows 10)
MinVersion=10.0

; Richiede privilegi amministratore per installare in Program Files
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; Architettura
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

; Impostazioni wizard
WizardStyle=modern
WizardSizePercent=120
ShowLanguageDialog=no

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
; Opzioni mostrate all'utente durante l'installazione
Name: "desktopicon";    Description: "Crea un'icona sul Desktop"; GroupDescription: "Icone aggiuntive:"; Flags: unchecked
Name: "quicklaunchicon"; Description: "Crea un'icona nella barra di avvio rapido"; GroupDescription: "Icone aggiuntive:"; Flags: unchecked; OnlyBelowVersion: 6.1

[Files]
; Eseguibile principale (generato da build.bat)
Source: "..\dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; File di documentazione (skipifsourcedoesntexist = non blocca se mancano)
Source: "..\README.md";              DestDir: "{app}\docs"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\docs\installazione.md";  DestDir: "{app}\docs"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\docs\architettura.md";   DestDir: "{app}\docs"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\config.example.ini";     DestDir: "{app}";      Flags: ignoreversion skipifsourcedoesntexist; DestName: "config.example.ini"

; Script database (per setup manuale o aggiornamenti)
Source: "..\database\*.sql"; DestDir: "{app}\database"; Flags: ignoreversion recursesubdirs skipifsourcedoesntexist

; Nota: resources/, styles/ e i moduli Python sono già inclusi
; nell'eseguibile da PyInstaller tramite foliarium.spec

[Icons]
; Shortcut Start Menu
Name: "{group}\{#AppName}";                         Filename: "{app}\{#AppExeName}"
Name: "{group}\Documentazione";                     Filename: "{app}\docs\README.md"
Name: "{group}\{cm:UninstallProgram,{#AppName}}";   Filename: "{uninstallexe}"

; Shortcut Desktop (opzionale)
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

; Shortcut Quick Launch (opzionale, per Windows vecchi)
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: quicklaunchicon

[Run]
; Offre di avviare l'app al termine dell'installazione
Filename: "{app}\{#AppExeName}"; Description: "Avvia {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Rimuove le cartelle create durante l'installazione (se vuote)
Type: dirifempty; Name: "{app}\docs"
Type: dirifempty; Name: "{app}\database"
Type: dirifempty; Name: "{app}"

[Code]
// Controlla se PostgreSQL è raggiungibile prima di terminare l'installazione
// (solo un avviso informativo — non blocca)
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssDone then
  begin
    MsgBox(
      'Foliarium è stato installato correttamente.' + #13#10 + #13#10 +
      'IMPORTANTE: Prima di avviare Foliarium è necessario:' + #13#10 +
      '  1. Avere PostgreSQL 13+ installato e in esecuzione' + #13#10 +
      '  2. Creare il database eseguendo i file SQL in:' + #13#10 +
      '     ' + ExpandConstant('{app}\database') + #13#10 +
      '  3. Configurare la connessione in config.ini' + #13#10 + #13#10 +
      'Consultare docs\installazione.md per le istruzioni complete.',
      mbInformation, MB_OK
    );
  end;
end;
