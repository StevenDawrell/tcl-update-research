# Reverse-Engineering Notes (Dekompilat-Bezuege)

Diese Datei haelt fest, aus welchen Firmware-Komponenten die Befunde stammen,
und dient der wissenschaftlichen Nachvollziehbarkeit. Alle Angaben beziehen sich
auf die Firmware der Geraeteklasse G10/55C655 (Realtek RTD, Android TV).

## Dekompilierte Komponenten

| APK | Prozess/UID | Rolle |
|---|---|---|
| `ttvs.apk` (`com.tcl.ttvs`) | uid 1000 (`android.uid.system`) | OTA-Client, DLNA/AirPlay, Identitaets-DB, Factory-Proxy |
| `FactorySettings.apk` (`com.tcl.factory.view`) | Priv-App | Werksmenue, Key-Provisioning, Werks-Upgrade |
| `TGuard.apk` (`com.tcl.guard`) | Priv-App | Berechtigungs-Shield, Speicheraufräumen, Paket-Installer |
| `RepairGuide.apk` (`com.tcl.repairguide`) | Priv-App | Diagnose (Audio/Video/Netz/HDMI) |

## Zentrale Code-Stellen (Klassen / Methoden)

| Stelle | Fund |
|---|---|
| `j/k/p/x/p/a/c.java` (`InstallTools`) | `RecoverySystem.verifyPackage()` wird **bedingungslos** aufgerufen (Ganzdateisignatur) |
| `j/k/p/x/k/c.java` | `isABUpdateZip()` liest `ota-type` aus `META-INF/com/android/metadata` **vor** der Signaturpruefung |
| `com/tcl/ttvs/versionUpdateApp/AB/UpdateParser.java` | `USB_FILE_PATCH = /mnt/media_rw`, `payload.bin`/`payload_properties.txt`, `file://`-URL |
| `com/tcl/ttvs/versionUpdateApp/AB/ABUpdateManager.java` | `applyPayload(url, offset, size, props)` auf `android.os.UpdateEngine` |
| `j/k/p/x/q/l.java` (`ProtocolAddrChanger`) | Endpunkt-Auswahl: Test-Filter vs. Zonen-Filter (`cn/as/na/eu`) |
| `j/k/p/x/q/v.java` (`UtilsTools`) | Schalter: `/data/UpdatePlatformType.txt` (`platformType=false`) |
| `j/k/p/x/q/u.java` (`UtilsTest`) | `persist.tcl.update.{testDebug,testVersion,testCliType,testDnum,testPid}` |
| `j/k/p/x/q/t.java` (`Utils`) | `a()` liefert `/data/fota` als Download-Ziel; `c()` extrahiert Zone aus `clientType` |
| `com/tcl/ttvs/deviceauthen/.../MyContentProvider.java` | `exported=true` ohne Permission; `insert()`/`update()` mit Tabellenname aus URI |
| `com/tcl/factory/view/infoservice/.../SitaUpgradeService.java` | Werks-Upgrade ueber Klartext-HTTP, USB-Zielverzeichnis `<USB>/AutoUpgrade/` |
| `com/tcl/factory/view/factoryos/socket/FactoryOsService.java` | Binärprotokoll `127.0.0.1:27856`, `FUN_SET_PROPERTY` (Werksmodus) |
| `com/tcl/allcast/sdk/utils/ToolUtil.java` | `checkUriValidity()` validiert nur Schema, nicht Ziel (bestaetigt CVE-2025-55971) |
| `com/tcl/guard/portal/packageinstaller/FileOper.java` | `copyFile()` = toter Code (nur `main()`-Test) |
| `com/tcl/guard/onlinesupport/ICopyInterface.java` | AIDL `copyFile(String,String)` ohne Implementierung |

## Methodik

- **Statisches RE:** JADX 1.5.0 auf den APKs (`.jar` unter `work/jadx`),
  Mustersuche ueber `FileOutputStream`/`FileWriter`/Pfad-Literale.
- **Live-Tests:** `adb shell` (read-only bis auf dokumentierte, rueckgaengige
  Tests), `content query/update`, `am start`, `uiautomator dump`, `logcat`.
- **Paket-Analyse:** ZIP-Tail-Parser, SHA-256, CrAU-Header-Parser.

## Reproduzierbarkeit

Jeder Befund ist an eine Stelle im Code oder einen Log-Auszug gekoppelt;
`../scripts/` enthaelt die Werkzeuge fuer die Live-Tests. Sensible Werte sind
redigiert (siehe `../docs/DATENSCHUTZ.md`).
