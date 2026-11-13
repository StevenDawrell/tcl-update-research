# Recherchestand 2026-11-11: ohne USB-Stick installieren

Ergänzung zu [INSTALLATIONSWEG.md](INSTALLATIONSWEG.md). Diese Datei hält fest, was
zusätzlich geprüft wurde (Reverse-Engineering von `ttvs.apk` **und** der
Factory-App `FactorySettings.apk`, plus Live-Tests am Gerät), was dabei herauskam
und was realistisch übrig bleibt.

Kurzfassung vorweg: **Der bisher gesuchte rein softwarebasierte Weg existiert nicht.**
Jeder installierende Pfad des Geräts endet entweder bei einem echten Blockmedium
(USB) oder bei einer Serverantwort des Herstellers. Neu ist aber: eine vermutete
Sperre ist anders als angenommen nicht dicht, und der Werk-Update-Pfad wurde
vollständig entschlüsselt.

---

## 1. Gerätezustand (gemessen)

| Prüfung | Wert |
|---|---|
| `ro.build.type` | `user` |
| `ro.boot.flash.locked` | `1` |
| `ro.boot.verifiedbootstate` | `green` |
| `ro.crypto.state` / `ro.crypto.type` | `encrypted` / `file` (FBE) |
| `/data` | `system:system`, `0771` |
| `/data/fota` | `system:system`, `0770` |
| `/cache` | `system:cache`, `0770`, 93 MB |
| `adb shell` Gruppen | `sdcard_rw`, `sdcard_r`, **`ext_data_rw`**, `ext_obb_rw`, … (kein `media_rw`) |
| `com.tcl.ttvs` | `userId=1000`, `sharedUser android.uid.system` |
| Permissions von ttvs | `RECOVERY: granted`, `ACCESS_CACHE_FILESYSTEM: granted` |
| ttvs flags | `SYSTEM … ALLOW_CLEAR_USER_DATA UPDATED_SYSTEM_APP` — **kein `ALLOW_BACKUP`** |
| `uncrypt` / `update_engine` / `update_verifier` | vorhanden (SELinux verbirgt `ls`, Existenz via „Permission denied" statt „No such file") |

Damit ist **`adb backup/restore` endgültig tot** (kein `ALLOW_BACKUP`), und
`/data/media` ist für `shell` nicht erreichbar (kein `media_rw`).

---

## 2. Neu: unauthentifizierter Schreibzugriff auf die Geräte-Identität

`com.tcl.ttvs.deviceauthen.core.StartandroidService.MyContentProvider`
(Manifest: `android:exported="true"`, **ohne `android:permission`**)
implementiert `query()`, `insert()` **und** `update()`. Der Tabellenname wird aus
dem letzten URI-Segment gebildet:

```java
// MyContentProvider.java:133-140
public int update(Uri uri, ContentValues v, String w, String[] a) {
    String table = uri.toString().substring(uri.toString().lastIndexOf("/") + 1);
    this.a.getWritableDatabase().update(table, v, null, null);   // trifft ALLE Zeilen
    return 0;
}
```

Getestet und bestätigt (Werkzeug: `scripts/identity_db.py`):

```bash
adb shell content query  --uri content://com.tcl.xian.StartandroidService.MyContentProvider
adb shell content update --uri content://com.tcl.xian.StartandroidService.MyContentProvider/devicetoken \
                         --bind devicemodel:s:TCL-AS-RTD75P-S1
```

---

## 3. Neu: der Test-Endpunkt und seine Schalter

`j/k/p/x/q/l.java` (ProtocolAddrChanger) wählt die URL:

| Bedingung | Endpunkt |
|---|---|
| `/data/UpdatePlatformType.txt` enthält `platformType=false` | `https://testfilter-upgrade.huan.tv` |
| `persist.system.update.test.flag == true` | `https://testfilter-upgrade.huan.tv` |
| sonst, Zone aus `clientType.split("-")[1]` | `cn-` / `as-` / `na-` / `eu-filter-upgrade.huan.tv` |

Die Test-Overrides liegen alle in `j/k/p/x/q/u.java` (`testDebug`, `testVersion`,
`testCliType`, `testDnum`, `testPid`) – sämtlich `persist.*`, also per `setprop`
nicht setzbar (bestätigt: „Failed to set property").
`/data/UpdatePlatformType.txt` existiert nicht und ist für `shell` nicht anlegbar
(`/data` = `0771 system:system`). **Die Test-Umschaltung ist verschlossen.**

---

## 4. Neu: die Factory-App (`com.tcl.factory.view`)

APK: `/product/app/FactorySettings/FactorySettings.apk`, Quelltext unter
`_archiv/werkzeuge/FactorySettings_src/`. Startbar von `shell` (exportiertes
`MainMenu`). Menüinhalt live per `uiautomator dump`:

```
Main Menu/Info Menu/USB Update
  HDCP Upgrade · HDCP2.0 Upgrade · FRC IMAGE Upgrade · MAC Upgrade
  CI Key Upgrade · WideVine Key Upgrade · Netflix MGK Key Upgrade
  ATT Upgrade · PlayReady Upgrade · Device ID Upgrade · QDA Key Upgrade
  External Device upgrade
  SW NO: V8-R75PT01-LF1V548.002110   Project Name: 55C655
```

**Ausschließlich Key-/Device-Provisioning über USB. Kein System-Update dort.**

### 4.1 `SitaUpgradeService` – Werks-Upgrade über Klartext-HTTP

Exportierter Service ohne Permission, Endpunkt (Retrofit):

```java
// HttpUrl.java
BASE_URL = "http://10.74.141.195:8080/factory-upgrade-serv/"
GET  openapi/upgrade/download?taskId=&fileType=
POST openapi/upgrade/request_upgrade_pkg
POST openapi/upgrade/report_status
```

**Klartext-HTTP, ohne jede TLS-Hürde** – der einzige Upgrade-Kanal des Geräts,
der nicht zertifikatsgebunden ist. Nach vollständiger Lektüre von
`SitaUpgradeService.java`, `InfoServiceApiImpl.java` und `DeliverInfoResponse.java`
ist der Ablauf lückenlos bekannt – und **dreifach USB-gebunden**:

```
InfoServiceApiImpl.start()
  nur wenn getPModeStatus() || getDModeStatus()          <- Tor 1: Werksmodus
  -> startForegroundService(SitaUpgradeService)
     WHAT_CHECK_USB: <USB>/AutoUpgrade/ProductBatch.txt
                     <USB>/AutoUpgrade/Equipment.txt     <- Tor 2: Konfig vom Stick
       leer -> "usb no info" -> WHAT_STOP -> stopSelf()
     POST openapi/upgrade/request_upgrade_pkg
       -> DeliverInfoResponse { pkgDownloadUrl, upgradeFileName,
                                upgradeFileSize, taskId, videoDownloadUrl, ... }
     GET  openapi/upgrade/download?taskId=&fileType=0|1
       -> Ziel: <USB>/AutoUpgrade/<upgradeFileName>      <- Tor 3: Download auf Stick
     writeDownloadBackup -> <USB>/AutoUpgrade/Backup.txt
     setAutoUpgrade(true) = doSet_FactoryUsbUpgrade(true)
     setProperty("factory.upgrade.download.flag","1")
     WHAT_REBOOT -> CommonFuns.reboot()
       -> Bootloader installiert vom USB-Medium
```

Zusätzlich: `dfmFactoryManager.setProperty()` schreibt **Factory-HAL-Properties**
(`memory.factory.*`, `factory.upgrade.*`), keine Android-Systemproperties. Die für
den Update-Client relevanten `persist.tcl.update.*` sind auch über diesen Weg
nicht setzbar.

**Bewertung: lässt nichts offen.** Ohne Medium bricht der Ablauf an Tor 2 ab
(`stopSelf`), und selbst mit Medium endet er im Bootloader-USB-Burn. Der
Klartext-Server `10.74.141.195:8080` wäre im LAN nachbaubar, ändert aber nichts
an den drei USB-Toren.

### 4.2 `setAutoUpgrade` = `doSet_FactoryUsbUpgrade(true)`

```java
// DFMFactoryManagerTromImpl.java:3507
public void setAutoUpgrade(boolean z) { this.mIFactory.doSet_FactoryUsbUpgrade(z); }
```

Aktiviert den **Bootloader-Auto-Install von USB** (Realtek-Modus, der
`install_a`/`Update.img` am Medium sucht). Nimmt einem die Menübedienung ab,
ändert aber nichts an der USB-Notwendigkeit.

### 4.3 `FactoryOsService` – Binärprotokoll auf `127.0.0.1:27856`

Die App spricht mit einer Werks-Middleware über einen lokalen TCP-Socket
(Port aus `odm.tcl.factory.socket.port`, Default **27856**), Request 144 Byte,
Response 72 Byte, Funktionen u. a. `FUN_SET_PROPERTY = 0`, `FUN_GET_PROPERTY = 1`,
`FUN_DO_FUNCTION = 4` – theoretisch ein `setprop`-Kanal mit Root-Rechten.

**Geprüft: der Port ist nicht offen** (kein Listener in `netstat`), der Server
startet erst im Werksmodus. `vendor.tcl.factory@1.0::IFactory` läuft als root,
ist aber ein Vendor-HIDL-Dienst und von `shell` nicht aufrufbar (`lshal`: nicht
im Service-Manager registriert).

---

## 5. Korrektur: der „filePath-Eintrag"

`j/k/p/x/p/a/d.java:200-203` schreibt den Installationspfad in die SharedPreferences
`ttvs_versionUpdateApp_update` (Schlüssel `filePath`, daneben `fileMd5`);
`ABUpdateManager` und `startVerify` lesen ihn von dort. Er wird aber **nur vom
Client selbst** gesetzt (Server-Download oder lokaler Scan) – es gibt keinen
externen Weg, ihn zu belegen. `run-as` (kein `debuggable`), `adb backup` (kein
`ALLOW_BACKUP`) und direkter Zugriff auf `/data/data/com.tcl.ttvs` sind versperrt.

---

## 5b. Datei-Schreiber: systematische Vollsuche (letzter Durchlauf)

Die Frage „gibt es irgendwo eine App, die eine Datei an einen system-relevanten Ort
schreibt?" wurde über **sämtliche dekompilierte APKs** geprüft — nicht zeile für
Zeile, sondern als Mustersuche nach `FileOutputStream`/`FileWriter`/`copyToFile`/
`renameTo`/`mkdirs`/`ZipInputStream` **und** nach allen Dateipfaden
(`/data`, `/cache`, `/sdcard`, `fota`, `upgrade`, `recovery`). Geprüft wurden
`ttvs.apk`, `FactorySettings.apk`, `TGuard.apk` (`com.tcl.guard`),
`RepairGuide.apk` (`com.tcl.repairguide`), plus `providers.config` und
`systemserver` (per `dumpsys`).

### 5.1 Gefundene Kandidaten und ihr tatsächliches Schicksal

| Kandidat | Datei | Ergebnis |
|---|---|---|
| `ICopyInterface.copyFile(String,String)` | `ttvs: com/tcl/guard/onlinesupport/ICopyInterface.java` | **Nur AIDL-Definition.** Keine Implementierung in irgendeiner App. `OnlineSupportService.onBind()` liefert `null`, `EventService.onBind()` liefert `IEvent.Stub` (startLog/stopLog/uploadData), nicht `ICopyInterface`. **Tot.** |
| `FileOper.copyFile(String,String)` | `TGuard: com/tcl/guard/portal/packageinstaller/FileOper.java` | Privater Helfer, `copyGeneralFile`/`cutGeneralFile`. **Wird von niemandem aufgerufen** — einziger Aufruf ist `main("D://test1.zip","E://mail")` (Entwicklungs-Test-Main). **Tot-Code.** |
| `ConfigurationProvider` (ContentProvider) | `TGuard: com/tcl/guard/portal/provider/` | Nur `tvlauncher.config`/`apprecs`/`widget`-Tabellen. Kein Dateizugriff. |
| `CheckInterfaceInner.hasUpdate()/showUpdateUI()` | `TGuard: com/tcl/update/component/check/` | AIDL nur `hasUpdate`/`showUpdateUI` — UI-Trigger, **kein Datei-Schreiben**. |
| `PackageInstallerService` | `TGuard: com/tcl/guard/portal/packageinstaller/` | `onBind()` = `null`, installiert nur **APKs** (`InstallAppProgress`), nicht OTA-Pakete. |
| `RepairGuide` (com.tcl.repairguide) | — | Nur Diagnose (Audio/Video/Picture/Network/HDMI/Remote). Eigener `FileProvider` zum Teilen von Logs. **Kein Update-Pfad.** |

**Fazit dieser Spur: Es gibt keinen erreichbaren Datei-Schreiber an einen
system-relevanten Ort.** Die beiden `copyFile`-Funktionen existieren zwar, sind
aber entweder ungebunden (ICopyInterface) oder toter Test-Code (FileOper).

### 5.2 Nebenbefund: `/data/vendor/tcl/update` — ein neuer, aber versperrter Ort

`TGuard: com/tcl/guard/portal/rubish/ScanConfig.java` definiert
`PATH_UPDATE = "/data/vendor/tcl/update"` (neben `/data/user_log`, `/data/TCL_backup`).
TGuard nutzt das nur als **Aufräum-Ziel** für den „Speicher frei machen"-Modus
(große Dateien suchen/löschen), **nicht als Update-Ziel**. Live geprüft:

```
/data/vendor          root:root   drwxrwx--x   ← shell kann hinein (x)
/data/vendor/tcl      Permission denied        ← für shell gesperrt
/data/vendor/tcl/update  Permission denied     ← für shell gesperrt
/data/upgrade         No such file             ← existiert nicht
/data/vendor/upgrade  Permission denied        ← gesperrt
```

`/data/vendor/tcl/update` ist für `shell` nicht beschreibbar (gehört einem
vendor-Prozess), und kein Code in den dekompilierten Apps schreibt eine
OTA-ZIP dorthin. Der Pfad ist also real, aber als Angriffspunkt unbrauchbar —
er macht dasselbe Problem wie `/data/fota`: nur system/vendor darf schreiben.

---

## 6. Paketformate, abschließend geprüft

| Paket | Einträge | `payload.bin` | Format |
|---|---|---|---|
| `V8-R75PT01-LF1V648.zip` | 48 | **nein** | BLOCK-Recovery-OTA (`*.new.dat.br` + `*.transfer.list`) |
| `V8-R75PT01-LF1V661.zip` | 1 | **nein** | nur `Update.img` (Realtek-TAR, Bootloader-Burn) |

### 6.1 Live-Test: selbst gebautes AB-Paket (`scripts/build_ab_probe.py`)

Eine AB-Probe-ZIP mit **selbst generiertem** `payload.bin` (CrAU-Header v2,
`REPLACE`-Operation, `payload_properties.txt`) und `ota-type=AB` in
`META-INF/com/android/metadata` wurde gebaut, auf `/sdcard` gelegt und über
*Systemupdate → USB Update* ausgelöst. Ergebnis (logcat, 2026-11-11):

```
[d]get local install path: /storage/emulated/0/V8-R75PT01-LF1V690.zip
[ZipFileUtils]isABUpdateZip line  ota-type=AB
[ZipFileUtils]isABUpdateZip versionString[0]ota-type
[ZipFileUtils]isABUpdateZip versionString[1]AB
[c]isCanAbUpdate: true
[c]isAbUpdateZip: true                                    ← AB-Pfad angenommen
[InstallTools]verifyOrProcessPackage in ... isAbUpdate:true
[InstallTools]isNeedProcessPackage false                  ← kein /cache-Kopieren!
[c]  Verify local package with progress = 0%
System.err: at android.os.RecoverySystem.verifyPackage(RecoverySystem.java:305)
[InstallTools]RecoverySystem.verifyOrProcessPackage GeneralSecurityException
```

**Was das beweist:**

1. **Der AB-Pfad lebt auf diesem Gerät.** `ota-type=AB` in der metadata schaltet
   den Client auf `UpdateParser.parse()` → `ABUpdateManager.applyPayload()`.
2. **Beim AB-Format entfällt `/cache` komplett** (`isNeedProcessPackage false`).
   Die 93-MB-Grenze, an der der BLOCK-Pfad scheitert, ist hier irrelevant.
3. **Gescheitert wird ausschließlich an `RecoverySystem.verifyPackage`** – der
   Whole-File-Signatur der ZIP gegen `/system/etc/security/otacerts.zip`.

### 6.2 Fazit „payload.bin selbst generieren": **nein**

`InstallTools` (`j/k/p/x/p/a/c.java:158`) ruft

```java
android.os.RecoverySystem.verifyPackage(file, listener, cachedFile);
```

**bedingungslos** auf – es gibt keinen Pref-Kurzschluss (`fileMd5` dient nur dem
Wiederholen/Löschen), keinen Umweg über `isAbUpdate`. Diese Prüfung ist eine
**Ganzdateisignatur** (signapk/whole-file) mit dem TCL-Release-Key; sie deckt
jede Änderung an der ZIP ab. Ein selbst erzeugtes `payload.bin` kann sie nicht
ersetzen, denn:

* die **Payload-Signatur** (die `update_engine` prüft) und die
  **ZIP-Ganzdateisignatur** (die `verifyPackage` prüft) sind zwei verschiedene
  Prüfungen – und `verifyPackage` liegt **vor** `applyPayload`;
* ohne den TCL-Privatschlüssel ist weder die eine noch die andere nachbaubar;
* die Signatur der Original-`V648` zu „übertragen" scheidet aus, weil sie genau
  die Bytes deckt, die man ändern müsste.

### 6.2a Bauen ≠ Signieren: die Werkzeuglandschaft

Alle bekannten Paketierungs-Werkzeuge lösen nur die **Hälfte** des Problems –
das Zusammenbauen, nicht das Signieren:

| Werkzeug | Kann | Braucht zum Installieren zusätzlich |
|---|---|---|
| `delta_generator` (AOSP `system/update_engine`) | Full-/Delta-Payload aus Partitions-Images erzeugen | `--private_key` = **Hersteller-OTA-Key** |
| `Payload_Repack_Tool` (snowwolf725) | Images → `payload.bin` repacken (`repackPayload.sh`) | RSA-Signierung mit Hersteller-Key |
| `payload_packer` (Rust) | Full-/Delta-Payloads aus Images (XZ/Zstd/Bzip2) | Signierung (nicht eingebaut, „experimental") |
| `payload-dumper-go` | `payload.bin` **extrahieren** (Richtung falsch) | – |
| `signapk` + Release-Key | ZIP-Ganzdateisignatur | **Hersteller-Release-Key** |

**Der Punkt:** Jedes Repack-Tool erzeugt eine *strukturell* gültige `payload.bin`.
Ohne den privaten OTA-Key bleibt der **Metadata-Signaturblock** leer
(`metadata_signature_size = 0`) – und `update_engine` verwirft sie. Dazu kommt
die Ganzdateisignatur der ZIP (`RecoverySystem.verifyPackage`), die `signapk`
mit dem TCL-Release-Key verlangt. **Zwei Tore, zwei Herstellerschlüssel.**

Das ist kein Werkzeug-, sondern ein Schlüssel-Problem: die öffentlichen
`otacerts.zip`-Zertifikate reichen zum *Prüfen*, nicht zum *Signieren*.

**Reproduzierbar:** `scripts/verify_signature_gate.py <paket>.zip` zeigt
pro Paket, ob der Payload-Signaturblock vorhanden ist, und erklärt die beiden
Tore. Die selbst gebaute AB-Probe (`scripts/build_ab_probe.py`) belegt es:
korrekt gebaut, aber `metadata signature size: 0` → vom Gerät abgelehnt.

**Damit ist der rein softwarebasierte Weg ohne fremdes Medium endgültig
ausgeschlossen.** Was bleibt, ist die Suche nach einem **offiziell signierten
AB-Paket** (siehe §7) – denn genau das würde jetzt, wie oben bewiesen, ohne USB
und ohne `/cache` installieren.

### 6.3 „AB-Paket aus den beiden ZIPs selbst bauen?"

Baumaterial wäre vorhanden:

| Quelle | Inhalt | Weiterverarbeitung |
|---|---|---|
| `V661.zip` → `Update.img` (TAR) | `package7/super.img` 2,49 GB, `boot.img` 67 MB, `vbmeta.img` 8 kB, `factory.img`, `bootloader.tar` | `super.img` mit `lpunpack` in logische Partitionen zerlegen |
| `V648.zip` | `system/product/vendor/odm/system_ext/system_dlkm/vendor_dlkm/preload/tclconfig.new.dat.br` + `.transfer.list` | `brotli -d` + `sdat2img` → Roh-Images |

Daraus ließe sich mit `delta_generator` (AOSP `system/update_engine`) oder
`brillo_update_payload` ein Payload mit `REPLACE`-Operationen erzeugen.

**`payload-dumper-go` hilft dabei nicht**: es ist ein **Extraktor**
(`payload.bin` → Partitions-Images), kein Generator. Es kann ein vorhandenes
Payload lesen und prüfen – erzeugen kann es keines. Beide vorliegenden ZIPs
enthalten gar kein `payload.bin`, also gibt es für das Werkzeug hier nichts zu tun.

**Warum der Selbstbau trotzdem scheitert** – das Bauen ist nicht das Problem,
das Signieren ist es:

1. `delta_generator` benötigt für `--private_key` den **TCL-OTA-Schlüssel**.
   Ohne ihn entsteht ein Payload ohne gültige Signatur, den `update_engine`
   ablehnt.
2. Unabhängig davon liegt **davor** `RecoverySystem.verifyPackage` – die
   Ganzdateisignatur der ZIP. In §6.1 live gemessen: `GeneralSecurityException`,
   `verify failed`, `applyPayload` wird nie erreicht.

**Das Catch-22 in einem Satz:** Das einzige Paket, das gültig signiert ist
(`V648`), ist `ota-type=BLOCK` und braucht `/cache` (93 MB) – das einzige Format,
das `/cache` umgeht, ist `ota-type=AB`, und das lässt sich nicht signieren. Die
`ota-type`-Zeile zu ändern bricht die Signatur, die genau diese Bytes abdeckt.

---

## 7. Gesamtbewertung: was bleibt

| Weg | Status |
|---|---|
| `/sdcard`-Root + lokales Update | läuft bis 50 %, scheitert an 93-MB-`/cache` (Paket 1974 MB) |
| `/data/fota` beschreiben | `system`-only |
| `filePath`/`update_info` in SharedPreferences | kein externer Schreibweg (§5) |
| Identitäts-DB überschreiben | möglich (§2), ohne Wirkung auf Update-Auswahl |
| Test-Endpunkt / `persist.tcl.update.*` | verschlossen (§3) |
| Gefälschter Update-Server | TLS-Systemtrust, ohne Root nicht zu öffnen |
| Factory-App | nur Key/Device über USB (§4) |
| `update_engine` direkt | SELinux-Deny für `shell` |
| Recovery-Sideload | kein `adbd` in der Recovery |
| Bootloader/fastboot | `flash.locked=1`, `verifiedbootstate=green` |
| **AB-Paket (`payload.bin`)** | **nicht vorhanden – Client könnte es aber installieren (§6)** |
| **USB-Blockmedium (Kartenleser/HDD/Handy/Pi-Gadget)** | **funktioniert, umgeht `/cache` vollständig** |
| **Service-PIN vom TCL-Kundendienst** | **offizieller Weg, lädt nach `/data/fota`** |
| **CDN-Verteilung abwarten** | **funktioniert, sobald der Server liefert** |

### Empfehlung in dieser Reihenfolge

1. **Nach einem AB-Paket (`payload.bin`, `ota-type=AB`) für G10 suchen.** Wird
   eines gefunden, reicht `adb push` in den `/sdcard`-Root + *Systemupdate →
   USB Update* – `update_engine` liest die Datei direkt, kein USB, kein
   `/cache`-Problem (in §6.1 live bewiesen). Suchkriterium an der ZIP erkennbar:
   `payload.bin` + `payload_properties.txt` vorhanden, in
   `META-INF/com/android/metadata` steht `ota-type=AB`, und die ZIP ist mit dem
   TCL-Release-Key signiert (`META-INF/com/android/otacert`).
   Prüfen mit `python scripts/inspect_package.py <paket>.zip`; der Ablauf ist in
   `scripts/build_ab_probe.py` als Referenz nachgebaut.
   **Ohne signiertes AB-Paket ist der Weg tot** – siehe §6.2.
2. **Jedes beliebige USB-Blockmedium** nehmen (microSD-Kartenleser mit der
   Karte aus dem Telefon, USB-SATA-Gehäuse, alte HDD/SSD, altes Telefon im
   Massenspeicher-Modus, Raspberry Pi Zero als `g_mass_storage`-Gadget). Es muss
   kein „Stick" sein – entscheidend ist ein echtes Blockgerät, das `vold` unter
   `/mnt/media_rw` einhängt. Format FAT32 (V648 mit 1,93 GiB passt; das
   3,73-GB-`Update.img` aus V661 braucht exFAT/NTFS).
3. **Service-PIN beim TCL-Kundendienst** anfordern (`persist.sys.device.dnum`
   = `REDACTED_DNUM`) – der vorgesehene Weg über *Kundendienst / Customer Service
   Update*, lädt nach `/data/fota` und installiert ohne Cache-Grenze.
4. **Abwarten**, bis TCL das Paket für dieses Gerät freischaltet; dann läuft das
   Online-Update über genau diesen `/data`-Pfad.

Alles Weitere (Root, TLS-CA einspielen, Partitionstabelle umbauen, Bootloader
entsperren) ist ausgeschlossen oder mit Brick-Risiko verbunden und kein
vernünftiger Aufwand für ein einzelnes Update.

---

## 8. Reproduzierbare Befehle

```bash
# Geräte-Identität lesen / schreiben (Befund §2)
python scripts/identity_db.py show
python scripts/identity_db.py restore

# Debug-Logging des Update-Clients (debug.* darf shell setzen)
adb shell setprop debug.tcl.ttvs.log 7

# Update-Check mit Log beobachten
adb shell logcat -c
adb shell am start -n com.tcl.ttvs/com.tcl.ttvs.versionUpdateApp.core.UI.CheckoutVersionActivity
adb shell logcat -d | findstr /i "zone getUpdateUrl isUpgradeByVerID getUpgrade checkAuthenSuccess"

# Factory-Menü / dessen Inhalt
adb shell am start -a android.intent.action.MAIN -n com.tcl.factory.view/.MainMenu
adb shell uiautomator dump /sdcard/ui.xml & adb shell cat /sdcard/ui.xml

# Paketformat prüfen
python scripts/inspect_package.py V8-R75PT01-LF1V648.zip

# Werks-Socket (läuft nur im Werksmodus)
adb shell getprop odm.tcl.factory.socket.port
adb shell netstat -anp | findstr 27856
```



Der Wert wurde tatsächlich geschrieben und ließ sich wiederherstellen.
**Wirkung auf das Update: keine** – der Request nimmt `clientType` aus
`tclx.os.TDeviceInfo` (= `ro.product.clientType`), die DB ist nur Fallback bei
leerer Property. Live-Log nach dem Test:

```
[TcastModuleConfig] clientType = TCL-EU-RTD75P-S1
[BaseNetSystemUpdater] isUpgradeByVerID: false
checkUpdatePlan updateResponseBean.getUpgrade() == null
```

Einordnung: **echter, ohne Root erreichbarer Schreibkanal in Systemdaten – aber
der Update-Client hängt nicht daran.** Nützlich für Reproduktion/Forensik, nicht
für die Installation.

