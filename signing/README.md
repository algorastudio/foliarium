# Firma del codice (Authenticode) — Foliarium

Foliarium è firmato con un certificato **Certum Code Signing** intestato a
*Marco Santoro*, usando la **firma in cloud Certum SimplySign** (la chiave
privata resta nell'HSM di Certum; l'autenticazione avviene con l'**OTP
generato dall'app SimplySign sullo smartphone**).

Poiché la firma richiede l'OTP del telefono a ogni sessione, **la firma è
locale, eseguita al momento del rilascio** (non in CI). La pipeline GitHub
continua a produrre artefatti **non firmati**; la firma si applica con gli
script di questa cartella su una macchina Windows con SimplySign Desktop.

## Prerequisiti (una tantum)

1. **SimplySign Desktop** installato (Certum) — fornisce la "carta virtuale".
2. **Windows SDK – Signing Tools** (per `signtool.exe`).
3. **Inno Setup 6** (per `ISCC.exe`), già usato dalla build.
4. Il certificato attivo nel profilo SimplySign cloud.

## Procedura di rilascio firmato

1. Apri **SimplySign Desktop** e **accedi** inserendo l'OTP dell'app sul
   telefono. La sessione resta sbloccata per alcune ore: il certificato compare
   in `certmgr.msc → Personale`.
2. Genera l'eseguibile con PyInstaller:
   ```powershell
   pyinstaller foliarium.spec
   ```
3. Firma l'eseguibile e costruisci l'installer firmato in un colpo solo:
   ```powershell
   .\signing\build-signed-installer.ps1 -Version 1.0.2
   ```
   Lo script:
   - firma `dist\Foliarium\Foliarium.exe` (l'app installata è firmata);
   - compila l'installer con `iscc /DSIGN /Scertum="..."`, firmando **setup e
     uninstaller** (timestamp Certum `http://time.certum.pl`).

### Firmare singoli file

```powershell
.\signing\sign.ps1 -Files dist\Foliarium\Foliarium.exe
# selezione per impronta invece che per CN:
.\signing\sign.ps1 -Files a.exe,b.exe -Thumbprint <THUMBPRINT>
```

## Verifica

```powershell
signtool verify /pa /v .\Installer\Foliarium_1.0.2_Setup.exe
```
La firma deve risultare valida con timestamp; la catena Certum
(*Code Signing 2021 CA → Trusted Network CA 2*) viene inclusa automaticamente
da SimplySign Desktop.

## Note

- **Certificato individuale**: la firma è valida e rimuove l'avviso "editore
  sconosciuto"; la reputazione SmartScreen si costruisce nel tempo con le
  installazioni (un certificato EV l'avrebbe da subito, ma richiede hardware EV).
- **Niente segreti in CI**: la chiave non è esportabile e l'OTP è sul telefono;
  per questo la firma resta un passo locale e volontario al rilascio.
- Per firmare anche da una macchina di build automatica servirebbe un
  **self-hosted runner** Windows con SimplySign Desktop loggato — fuori dallo
  scopo di questa configurazione.
