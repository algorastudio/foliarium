; ============================================================================
; Foliarium_Installer.iss
; Installer Windows per Foliarium — Archivio Catastale Storico.
;
; Pacchettizza l'output di PyInstaller (dist\Foliarium) in un setup .exe,
; PostgreSQL incluso: l'installazione non richiede alcun intervento manuale.
;
; La pipeline (.github/workflows/pipeline_foliarium.yml) prepara dist\Foliarium
; con tre ingredienti prima di invocare iscc:
;   1. Foliarium.exe + _internal\  (PyInstaller, foliarium.spec)
;   2. setup_db.exe                (PyInstaller, setup_db.spec)
;   3. pgsql\                      (binari EnterpriseDB, ~120 MB potati)
; Compilare a mano senza quei passaggi produce un installer che non sa
; creare il database: la sezione [Code] se ne accorge e lo dice.
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
#define SetupDbExeName "setup_db.exe"
#define CredentialsFile "PRIMO-ACCESSO.txt"
#define SetupDbLog "setup_database.log"

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
; Output completo di PyInstaller (eseguibile + _internal\), piu' setup_db.exe
; e pgsql\ che la pipeline deposita nella stessa cartella. Un'unica riga:
; recursesubdirs li prende tutti.
Source: "dist\{#MyAppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Disinstalla {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; La password di 'admin' e' generata a caso e in DB resta solo l'hash: se
; l'utente non la legge ora, l'installazione e' riuscita ma non entra nessuno.
; Percio' la voce e' spuntata come quella di avvio, e viene prima: cosi' le
; credenziali sono gia' aperte quando l'applicazione chiede di accedere.
; shellexec, non "notepad.exe": su Windows 11 il Blocco note e' diventato
; un'app dello Store e invocarlo per nome non e' piu' affidabile. Cosi' il
; file si apre con l'editor di testo predefinito, qualunque sia.
Filename: "{app}\{#CredentialsFile}"; \
    Description: "Mostra le credenziali di primo accesso"; \
    Flags: postinstall skipifsilent shellexec nowait; Check: CredenzialiDisponibili

Filename: "{app}\{#MyAppExeName}"; \
    Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; \
    Flags: nowait postinstall skipifsilent

; Nessuna sezione [UninstallRun]: i suoi parametri vengono fissati durante
; l'INSTALLAZIONE, quindi un {code:...} che dipende dalla risposta dell'utente
; alla disinstallazione verrebbe valutato troppo presto — e con la variabile
; ancora a False i dati sarebbero cancellati comunque. La rimozione del
; servizio sta in CurUninstallStepChanged, vedi [Code].


[Code]
{
  Inizializzazione del database.

  Girare l'installer senza questa fase lascerebbe l'utente davanti a un
  dialogo di configurazione con un database che non esiste: e' esattamente
  il passaggio manuale che questo installer esiste per eliminare.
}

var
  DatabaseConfigurato: Boolean;

function CredenzialiDisponibili(): Boolean;
begin
  { La voce [Run] che apre il promemoria non deve comparire se il setup del
    database non e' arrivato a scriverlo. }
  Result := DatabaseConfigurato and FileExists(ExpandConstant('{app}\{#CredentialsFile}'));
end;

function EseguiSetupDatabase(): Boolean;
var
  SetupDbPath, Parametri: String;
  CodiceUscita: Integer;
begin
  SetupDbPath := ExpandConstant('{app}\{#SetupDbExeName}');

  if not FileExists(SetupDbPath) then
  begin
    { Build incompleta: la pipeline non ha depositato setup_db.exe in
      dist\Foliarium. Meglio dirlo che installare un guscio vuoto. }
    MsgBox('Questo pacchetto non contiene il componente di inizializzazione del '
      + 'database (' + '{#SetupDbExeName}' + ').' + #13#10#13#10
      + 'L''applicazione e'' stata installata, ma il database va configurato a mano. '
      + 'Contattare l''assistenza segnalando questo messaggio.',
      mbError, MB_OK);
    Result := False;
    Exit;
  end;

  if not DirExists(ExpandConstant('{app}\pgsql\bin')) then
  begin
    MsgBox('Questo pacchetto non contiene i binari PostgreSQL (cartella pgsql).' + #13#10#13#10
      + 'L''applicazione e'' stata installata, ma il database va configurato a mano. '
      + 'Contattare l''assistenza segnalando questo messaggio.',
      mbError, MB_OK);
    Result := False;
    Exit;
  end;

  { Le password (ruolo PostgreSQL e utente admin) le genera setup_db.exe:
    Inno Setup non ha un generatore di casualita' adatto a delle credenziali. }
  Parametri := '--credentials-out "' + ExpandConstant('{app}\{#CredentialsFile}') + '"';

  if not Exec(SetupDbPath, Parametri, ExpandConstant('{app}'),
              SW_HIDE, ewWaitUntilTerminated, CodiceUscita) then
  begin
    MsgBox('Impossibile avviare l''inizializzazione del database.' + #13#10#13#10
      + 'L''applicazione e'' installata ma non utilizzabile finche'' il database '
      + 'non viene configurato. Contattare l''assistenza.',
      mbError, MB_OK);
    Result := False;
    Exit;
  end;

  if CodiceUscita <> 0 then
  begin
    MsgBox('L''inizializzazione del database non e'' riuscita (codice '
      + IntToStr(CodiceUscita) + ').' + #13#10#13#10
      + 'Causa frequente: un PostgreSQL gia'' presente sulla macchina che occupa '
      + 'le porte 5432, 5433 e 5434.' + #13#10#13#10
      + 'Il dettaglio e'' nel file:' + #13#10
      + ExpandConstant('{app}\{#SetupDbLog}') + #13#10#13#10
      + 'L''applicazione resta installata: dopo aver risolto, rieseguire '
      + '{#SetupDbExeName} come amministratore.',
      mbError, MB_OK);
    Result := False;
    Exit;
  end;

  Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    WizardForm.StatusLabel.Caption := 'Configurazione del database in corso (30-60 secondi)...';
    WizardForm.Update();
    DatabaseConfigurato := EseguiSetupDatabase();
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  SetupDbPath, Parametri: String;
  Risposta, CodiceUscita: Integer;
begin
  if CurUninstallStep <> usUninstall then
    Exit;

  SetupDbPath := ExpandConstant('{app}\{#SetupDbExeName}');
  if not FileExists(SetupDbPath) then
    Exit;  { installazione senza database: nulla da rimuovere }

  {
    I dati sono l'archivio catastale del cliente, quindi il default e'
    conservarli: MB_DEFBUTTON2 preseleziona "No", e solo un SI' esplicito
    cancella. Chiediamo qui e non in InitializeUninstall perche' cosi' la
    risposta e' usata subito, nello stesso processo.
  }
  Risposta := MsgBox(
    'Eliminare anche i dati dell''archivio catastale?' + #13#10#13#10
    + 'Scegliendo NO il database resta in C:\ProgramData\Foliarium\pg_data '
    + 'e una futura reinstallazione lo ritrovera'' con tutti i dati.' + #13#10#13#10
    + 'Scegliendo SI l''archivio viene cancellato in modo definitivo.',
    mbConfirmation, MB_YESNO or MB_DEFBUTTON2);

  { Il servizio va rimosso in ogni caso: lasciarlo registrato dopo aver
    cancellato gli eseguibili significa un servizio Windows che fallisce a
    ogni avvio della macchina. }
  if Risposta = IDYES then
    Parametri := '--uninstall'
  else
    Parametri := '--uninstall --keep-data';

  if not Exec(SetupDbPath, Parametri, ExpandConstant('{app}'),
              SW_HIDE, ewWaitUntilTerminated, CodiceUscita) then
    MsgBox('Non e'' stato possibile rimuovere il servizio del database.' + #13#10#13#10
      + 'Rimuoverlo a mano da un prompt amministratore con:' + #13#10
      + '  sc delete FoliariumDB',
      mbInformation, MB_OK);
end;
