; Script per Inno Setup per l'applicazione Foliarium
; Creato da Supporto Definitivo per il Tirocinio per Marco Santoro

; --- DEFINIZIONE COSTANTI ---
; Usare le costanti rende lo script più pulito e facile da manutenere per versioni future.
#define MyAppName "Foliarium"
#define MyAppVersion "1.6.0"
#define MyAppPublisher "Marco Santoro"
#define MyAppURL "https://github.com/saintgold74/catasto"
#define MyAppExeName "Foliarium.exe"
#define MyCopyright "Copyright © Marco Santoro. In gentile concessione gratuita all'Archivio di Stato di Savona."

[Setup]
; --- INFORMAZIONI PRINCIPALI SULL'APP E SULL'INSTALLER ---
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; Specifica dove salvare l'installer finale e come chiamarlo.
OutputDir=Installer
OutputBaseFilename=Foliarium_{#MyAppVersion}_Setup
SetupIconFile=resources\icona_foliarium.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

; --- INFORMAZIONI DI VERSIONE INCLUSE NELL'ESEGUIBILE DELL'INSTALLER ---
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Installazione di Foliarium - Archivio Catastale Storico
VersionInfoCopyright={#MyCopyright}

; --- LICENZA D'USO (EULA) ---
; Mostra il file di licenza prima dell'installazione.
; Assicurarsi che il file si trovi nel percorso specificato.
LicenseFile=resources\EULA.rtf

[Languages]
; Imposta la lingua dell'installer.
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
; Aggiunge una casella di controllo per creare un'icona sul desktop.
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; --- COPIA DEI FILE DELL'APPLICAZIONE ---
; Questa è la sezione più importante. Copia TUTTO il contenuto della cartella
; generata da PyInstaller nella directory di installazione dell'utente.
Source: "dist\{#MyAppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; --- CREAZIONE DEI COLLEGAMENTI (ICONE) ---
; Crea l'icona nel Menu Start.
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
; Crea l'icona sul Desktop se l'utente ha spuntato la casella nel wizard.
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; --- ESECUZIONE POST-INSTALLAZIONE ---
; Offre all'utente la possibilità di avviare il programma subito dopo l'installazione.
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent