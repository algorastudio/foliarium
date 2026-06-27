; ============================================================================
; Foliarium_Installer.iss
; Installer Windows per Foliarium — Archivio Catastale Storico.
;
; Pacchettizza l'output di PyInstaller (dist\Foliarium) in un setup .exe.
; Non include PostgreSQL: il database va configurato separatamente
; (vedi setup_database.py / documentazione).
;
; La versione puo' essere sovrascritta da riga di comando:
;   iscc /DMyAppVersion=1.2.3 Foliarium_Installer.iss
; ============================================================================

#ifndef MyAppVersion
  #define MyAppVersion "1.0.2"
#endif
#define MyAppName "Foliarium"
#define MyAppPublisher "Marco Santoro / Algora Studio"
#define MyAppURL "https://github.com/algorastudio/foliarium"
#define MyAppExeName "Foliarium.exe"
#define MyCopyright "Copyright (C) Marco Santoro / Algora Studio"

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
OutputBaseFilename=Foliarium_{#MyAppVersion}_Setup
SetupIconFile=resources\icona_foliarium.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible

; --- Firma del codice (opt-in) ---
; Attiva solo se si compila con  /DSIGN  e si definisce il SignTool 'certum'
; via  /Scertum="..."  (vedi signing/build-signed-installer.ps1).
; Senza /DSIGN l'installer si compila normalmente, non firmato.
#ifdef SIGN
SignTool=certum
SignedUninstaller=yes
#endif

VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Installazione di {#MyAppName}
VersionInfoCopyright={#MyCopyright}

LicenseFile=resources\EULA.txt

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Output completo di PyInstaller (eseguibile + _internal/)
Source: "dist\{#MyAppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Disinstalla {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; \
    Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; \
    Flags: nowait postinstall skipifsilent
