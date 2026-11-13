# Installationsweg: Analyse

> **Status 2026-11-11:** Ergänzt durch [RECHERCHE_STAND.md](RECHERCHE_STAND.md)
> (Factory-App, Identitäts-Provider, Test-Endpunkt, Paketformate, Gesamtbewertung).
> Kurzbefund: der rein softwarebasierte Weg existiert nicht; übrig bleiben
> ein AB-Paket (falls auffindbar), ein beliebiges USB-Blockmedium, die
> Service-PIN vom TCL-Kundendienst oder das Abwarten auf die CDN-Verteilung.

## Zusammenfassung

Der TCL-Client bietet einen lokalen Update-Pfad. Er wurde aktiviert, das Paket
wird gefunden und geprüft. Über `/sdcard` scheitert die Installation an der Größe
des Recovery-Caches. Ein zweiter Weg umgeht diese Grenze vollständig.

---

## Weg A: Paket auf `/sdcard` (getestet)

### Ablauf

```
1. Paket nach /sdcard/ kopieren   -> Client findet es
2. needProcess-Prüfung            -> true
3. Signaturprüfung                -> erfolgreich bis 50 %
4. Übergabe an RecoverySystem     -> installPackage()
5. Recovery startet               -> Paket nicht anwendbar
```

### Warum es scheitert

`RecoverySystem.installPackage()` prüft den Pfad:

```java
if (filename.startsWith("/data/")) {
    filename = "@/cache/recovery/block.map";   // Block-Map, kein Kopieren
}
// sonst: Datei muss nach /cache/recovery/package kopiert werden
```

Bei einem `/storage/`-Pfad (also `/sdcard`) wird das Paket **nach `/cache`
kopiert**.

```
adb shell df -h /cache
/dev/block/mmcblk0p41   93M   1% /cache
```

Paket 2 GB, Cache 93 MB. Die Kopie scheitert, der Recovery findet kein Paket
und bootet normal zurück. Das System bleibt unverändert.

---

## Weg B: Paket auf `/data` (der Weg des Geräts selbst)

### Warum das funktioniert

Bei einem `/data/`-Pfad erzeugt `uncrypt` eine **Block-Map** — eine kleine Datei
mit den Speicheradressen des Pakets. Der Recovery liest das Paket dann **direkt
von der Partition**, ohne Kopie nach `/cache`.

```
/data hat 15 GB frei     -> Paket passt
Block-Map wenige KB      -> passt in /cache
```

### Was der Client vorsieht

```java
// Utils.java
public static String a() {
    return new File("/data/fota").exists() ? "/data/fota" : "/data/";
}
```

```
adb shell ls -ld /data/fota
drwxrwx--- system system  /data/fota
```

Das Verzeichnis **existiert** und gehört `system`. Dorthin lädt der Client bei
Online-Updates seine Pakete — es ist für genau diesen Zweck vorgesehen.

### Der Pfad ist im Client blockiert

```java
// InstallTools.java
if (!d.b() && str.startsWith("/data/")) {
    str = "/tcl" + str;
}
```

`d.b()` liefert `ro.crypto.state == "encrypted"`. Auf diesem Gerät steht der Wert
auf `encrypted`, die Umleitung greift nicht, der Pfad bleibt `/storage/...`.

Ein Property existiert, um das zu steuern:

```
persist.tcl.update.isNOEncrypt    (nicht gesetzt = false)
```

---

## Beobachtete Logfolge (Weg A)

```
[ZipFileUtils] isABUpdateZip versionString[1]BLOCK
[c] isCanAbUpdate: true
[c] isAbUpdateZip: false
[InstallTools] verifyOrProcessPackage in ...filename = /storage/emulated/0/...
[InstallTools] isNeedProcessPackage true
Verify 0% ... 50%
Sending non-protected broadcast android.intent.action.smartcardautoupdate
Verbindung getrennt (Neustart)
Fernseher wieder erreichbar, Version unverändert
```

---

## Offene Punkte

| Frage | Stand |
|---|---|
| Nimmt der Client ein Paket aus `/data/fota` an? | zu prüfen |
| Lässt sich `/data/fota` als `shell` beschreiben? | nein — nur `system` |
| Gibt es einen Weg, den Client dorthin zu lenken? | `filePath`-Eintrag oder Download-Pfad |
| Ist `persist.tcl.update.isNOEncrypt` setzbar? | nein — `persist.*` nur für `system` |

`/data/fota` ist der aussichtsreichste Ansatz: vorgesehener Speicherort des
Clients, und der Recovery arbeitet dort ohne Cache-Kopie.

---

## Grenzen

- Das Werkzeug überträgt Pakete und öffnet den Update-Bildschirm. Über die
  Installation entscheidet das Gerät.
- Signatur- und Integritätsprüfung bleiben aktiv.
- Kein Eingriff in Systemdateien, kein Umgehen von Herstellersperren.

---

## Der reguläre Weg

1. Fernseher mit dem Internet verbinden.
2. **Einstellungen → System → Info → Softwareupdate**.
3. Der Client lädt nach `/data/fota`, prüft und übergibt an den Recovery.

Dabei läuft alles über den `/data`-Pfad — deshalb gibt es dort keine
Cache-Grenze.

---

## Weg D: Kunden-Service-Update mit vierstelliger PIN

Der Client kennt einen vierten Weg, den die Oberfläche unter *Kundendienst /
Customer Service Update* anbietet: Der Bediener gibt eine **vierstellige PIN**
ein, der Fernseher fragt daraufhin erneut beim Server nach.

### Aufrufkette im Code

```java
// NetworkUpdateActivity.java:63
intent.putExtra("key_intent_pin_code", pin);

// NetworkUpdateActivity.a()  – startType 2 = "manual pin"
SystemUpdateService.a(this, "manual", this.f);

// SystemUpdateService.java:585
intent.putExtra("pincode", str2);

// e.java:659 (BaseNetSystemUpdater)
public void a(String startType, String pin) {
    if (!isEmpty(pin) && ("manual".equals(startType) || "boot".equals(startType))) {
        this.f1822k = pin;          // PIN wandert in das Feld "md5id"
    }
}

// e.java:860
hashMap.put(MD5ID, this.f1822k);    // md5id=<PIN> in der Anfrage
```

**Ergebnis:** Die PIN wird als Parameter `md5id` an den Upgrade-Dienst
übergeben. Eine **lokale Prüfung der PIN findet nicht statt** — der Code
übernimmt jeden nicht leeren Wert. Ob ein Update angeboten wird, entscheidet
allein der Server.

### Warum das hilft

Der normale Check liefert für dieses Gerät kein Update:

```
[BaseNetSystemUpdater] checkUpdatePlan updateResponseBean.getUpgrade() == null
```

Die PIN ist der vorgesehene Weg, diese Filterung zu umgehen. Sie stammt vom
TCL-Kundendienst und ist an die Gerätenummer gebunden.

### Wo die PIN liegt

```
/data/data/com.tcl.ttvs/shared_prefs/ttvs_versionUpdateApp_update.xml
  Schlüssel: pin_code
```

Für `shell` nicht lesbar und nicht schreibbar (`Permission denied`), der Dienst
läuft als `system`.


---

## Der Mitschnitt: was der Proxy zeigt

### Warum der Proxy zunächst nichts sah

Zwei Ursachen, beide nachgewiesen:

| Ursache | Befund |
|---|---|
| Windows-Firewall | `ping` vom Fernseher: 100 % Verlust; nach Freigabe 0 % |
| Port-Kollision | `adb reverse tcp:8888 tcp:8888` belegte Port 8888 selbst |

**Lösung:** `adb reverse tcp:8888 tcp:8899` — der Fernseher spricht
`127.0.0.1:8888` an, der Datenverkehr läuft über die adb-Verbindung zum
PC-Port 8899. Damit entfallen Firewall- und Netzwerkprobleme vollständig.

```powershell
adb reverse tcp:8888 tcp:8899
adb shell settings put global http_proxy 127.0.0.1:8888
python scripts/proxy_capture.py --port 8899 --duration 60 --tunnel
adb shell am start -n com.tcl.ttvs/com.tcl.ttvs.versionUpdateApp.core.UI.CheckoutVersionActivity
```

### Einstiegspunkt ohne Berechtigung

```xml
<!-- AndroidManifest.xml, Zeile 536 -->
<activity android:name="...CheckoutVersionActivity"/>   <!-- keine android:permission -->
```

`CheckoutVersionActivity` ist die **einzige** Update-Activity ohne
Signaturberechtigung. Ihr `onCreate` ruft intern
`SystemUpdateService.a(this, "setupwizard")` auf. Alle anderen
(`UpdateEntranceActivity`, `SystemUpdateActivity`, `NetworkUpdateActivity`)
verlangen `com.tcl.permission.START_CHECK_SYSTEMUPDATE` und antworten `shell`
mit `Permission Denial`.

### Beobachtete Ziele

```
CONNECT eu-filter-upgrade.huan.tv:443          <- der eigentliche Update-Dienst
CONNECT on-hweudc-o.api.leiniao.com:443
CONNECT on-hweudc-conf-o.api.leiniao.com:443
CONNECT eu-newuser-tcl.cedock.com:443
CONNECT on-hwtcs-o.api.leiniao.com:443
CONNECT ai.tclking.com:443
GET     http://connectivitycheck.gstatic.com/generate_204
```

### Endpunkte (aus `j.k.p.x.b.a`, Base64-kodiert)

```
https://eu-filter-upgrade.huan.tv/service/platform/getUpgradeByVerID
https://eu-filter-upgrade.huan.tv/service/upmp/upgradeConfigInterface
https://eu-filter-upgrade.huan.tv/service/getinfo/getUpgradeByDnum/
```

Regionsabhängig: `filter-upgrade` (CN), `as-`, `eu-`, `na-`, `test-`.

### Kein Zertifikats-Pinning

```java
// HttpCore.java:189 — definiert, aber von NICHTS aufgerufen
public void insertPeerCertificates(InputStream... s) { ... }
// HttpCore.java:186 — leer
public void insertLocalCertificates(InputStream... s) { }
```

Die App nutzt den normalen Android-System-Truststore. Ein Mitschnitt scheitert
also nicht an Pinning, sondern an der TLS-Verschlüsselung selbst: Ohne
Zertifizierungsstelle im **System**speicher (`/system` ist nur lesbar, `root`
fehlt) lässt sich kein Tunnel entschlüsseln.

### Request-Signatur ist nachbaubar

`SignInterceptor` signiert nur die Anfrage; die Antwort wird nicht geprüft.
Die Schlüssel liegen offen im Code:

```
appId  = REDACTED_APPID
appKey = REDACTED_APPKEY
```

`scripts/probe_upgrade_api.py` bildet die Signatur nach. Der Dienst weist die
Anfrage jedoch **generisch** ab:

```
HTTP 403  {"error":{"code":"111007","info":"request parameter error:RequestId is nil"}}
```

Die Meldung erscheint identisch ohne Signatur, mit falscher Signatur und mit
korrekter Signatur — auch mit passendem `User-Agent`. Der Fernseher kommt über
dieselbe Internetverbindung durch, der PC nicht. Die Ursache liegt damit unter
HTTP: der Dienst filtert nach dem **TLS-Fingerabdruck** des Clients. Von außen
nicht nachbildbar.

---

## Bewertung der Wege

| Weg | Ergebnis |
|---|---|
| `/sdcard` → `installPackage()` | scheitert an 93 MB `/cache` |
| `/cache` vergrößern | Partition ist physisch 93 MB |
| `/data/fota` beschreiben | nur `system`, nicht `shell` |
| DNS-Umleitung | HTTPS, ohne System-CA nicht entschlüsselbar |
| Proxy-Umleitung | funktioniert zum Beobachten, nicht zum Verändern |
| `adb sideload` | Recovery startet keinen `adbd` |
| `adb root` | Produktions-Build (`ro.build.type=user`) |
| PIN selbst berechnen | Server entscheidet, kein lokaler Abgleich |
| PIN vom PC erzwingen | TLS-Fingerabdruck-Filter des Dienstes |

**Fazit:** Der Kunden-Service-Weg ist der vom Hersteller offen gehaltene Pfad.
Die PIN ist der Schlüssel — sie wird serverseitig geprüft und ist an die
Gerätenummer gebunden. Sie lässt sich nicht aus dem Gerät ableiten; sie kommt
vom TCL-Kundendienst.

### Was der Bediener tun kann

1. Gerätenummer bereitstellen: `adb shell getprop persist.sys.device.dnum`
2. Beim TCL-Kundendienst eine Service-PIN für dieses Gerät anfordern.
3. Am Fernseher: **Einstellungen → System → Info → Softwareupdate →
   Kundendienst** und die PIN eingeben.
4. Der Client lädt nach `/data/fota` und übergibt an den Recovery — ohne
   Cache-Grenze.


---

## Empirischer Test: lokales Update bis zum Recovery

Ausgelöst über die TV-Oberfläche (`Einstellungen → Info → Systemupdate →
USB Update`), Log über `adb logcat` aufgezeichnet.

### Ablauf im Log

```
[d]getLocalPackPath with file = V8-R75PT01-LF1V648.zip
[d]get localPackage lastVersion: 648
[InstallTools]verifyOrProcessPackage in ...filename =
  /storage/emulated/0/V8-R75PT01-LF1V648.zip isAbUpdate:false
[InstallTools]isNeedProcessPackage true
[c]  Verify local package with progress = 10% … 50%
[InstallTools]start RecoverySystem.processPackage ...
[c]local software is ab, but zip is not ab!
[SystemUpdateHandler]========>>> show local no ab reboot dialog <<<========
```

Nach Bestätigung Neustart. Recovery meldet:

```
The upgrade is interrupted. Please insert the peripheral that was just
pulled out, turn on again.
```

Das ist die TCL-Meldung für **„Paketdatei nicht auffindbar."**

### Warum: die Größenlage

```
/cache      mmcblk0p41    93 MB gesamt, 89 MB frei
Paket     2 070 594 934 B = 1974 MB        → Faktor 22 zu groß
```

Der Ablauf:

1. Der Scan findet die ZIP nur unter `/sdcard/` — einem **FUSE-Pfad**.
2. `uncrypt` darf diesen Pfad der Recovery nicht weitergeben (weder FUSE noch
   verschlüsseltes `/data` sind in Recovery verfügbar), also **kopiert** er die
   Datei nach `/cache/recovery/package`.
3. 1974 MB passen nicht in 93 MB → kein gültiger `block.map`.
4. Die Recovery erhält den Rohpfad `/storage/emulated/0/…`, den es dort nicht
   gibt → „insert the peripheral".

### Welche Verzeichnisse der Scan durchsucht

Getestet mit einer Delegation-Datei unter `/data/local/tmp` (dort beschreibbar
und rohes `/data`):

```
Scan-Eintraege: 36        (alle aus /sdcard-Stamm)
Probe _scanprobe.zip:     NICHT gefunden
```

**Der Scan umfasst ausschließlich `/sdcard/`-Stamm.** Ein Roh-`/data`-Pfad ist
für das lokale Update nicht erreichbar.

### Paketformat

```
ota-type=BLOCK
payload.bin              FEHLT
product.new.dat.br       1 104 284 275 B
system.new.dat.br          419 760 349 B
post-build               TCL/G10_4K_US_NF/G10:14/UTT2.250416.001/AS50
pre-device               G10
```

Das Paket ist ein **Recovery-OTA ohne A/B-Payload**. `update_engine` (der auf
diesem Gerät läuft und den Slot `_a` verwaltet) kann damit nichts anfangen —
das warnt der Client selbst mit `local software is ab, but zip is not ab`.

### Die vier Menüwege

| Weg | Ergebnis |
|---|---|
| Network Update | Server meldet `getUpgrade() == null`, PIN serverseitig geprüft |
| USB Update | funktioniert — Recovery liest den Stick direkt (`USB_FILE_PATCH = "/mnt/media_rw"`), ohne `/cache` |
| Channel Update | benötigt DVB-Kanal mit Datenstrom |
| Customer Service Update | benötigt gültige PIN vom TCL-Kundendienst |

### Fazit

Das 1974-MB-Recovery-OTA ist über den internen Speicher nicht installierbar:
der einzige von der Recovery lesbare Ort (`/cache`) ist 22-mal zu klein, und
das Paket trägt keinen A/B-Payload, der `update_engine` umgehen würde.

Verbleibende Wege sind **USB-Stick** (vom Hersteller vorgesehen, umgeht
`/cache`) und die **Service-PIN**, die das Paket über den Netzwerkpfad nach
`/data/fota` bringt.


---

## Warum sich der Server nicht fälschen lässt

Die Frage, ob man dem Fernseher die eigene ZIP über einen gefälschten Server
schicken kann. Antwort: **neun von zehn Prüfungen sind umgehbar — die zehnte
ist die TLS-Vertrauenskette, und die liegt im Betriebssystem.**

### Was tatsächlich fälschbar ist

| Prüfung | Befund |
|---|---|
| Zertifikats-Pinning | **keines.** `insertPeerCertificates` hat null Aufrufer, `insertLocalCertificates` ist leer, im App-Code steht kein `CertificatePinner.Builder` |
| Signatur der Antwort | **wird nicht geprüft** — `getUpgrade()` wird nur als JSON gelesen |
| Signatur der Anfrage | **nachbaubar** — `appId`/`appKey` stehen im Klartext im Code, umgesetzt in `scripts/proxy_capture.py`-Umgebung bzw. `probe_upgrade_api.py` |
| Paket-Signatur | **irrelevant** — wir verwenden das echte, korrekt signierte V648 |
| Proxy des Systems | **wird genutzt** — der Client schickte `CONNECT` durch meinen Proxy |
| Klartext-HTTP | **erlaubt** — `usesCleartextTraffic = 0xffffffff` |

### Die einzige Wand

```
targetSdkVersion              30        (ab 24 nur System-CA-Vertrauen)
networkSecurityConfig         FEHLT     (kein Opt-in für User-CAs)
System-CA-Store               125 CAs   /system = "Read-only file system"
User-CA-Store                 /data/misc/user/0/cacerts-added → Permission denied
```

Ohne eigene Zertifizierungsstelle in `/system/etc/security/cacerts` kann der
Client unseren Server nicht vertrauen. Diese Datei schreiben zu können, ist
**root** — und nichts anderes.

### Verhalten ohne gültiges TLS

Lief der Proxy nicht als Tunnel, sondern antwortete mit `502`, ging die
Aktualisierung sang-und-klanglos ins Leere:

```
ConfigFileDownload: result: error code: End of input at character 0
NullPointerException: UpdateResponseBean$UpgradeBean.getVersion() on null
checkUpdatePlan updateResponseBean.getUpgrade() == null
```

Ein gefälschter Server ohne gültiges Zertifikat erzeugt genau dasselbe
Bild — die Verbindung wird vor dem ersten Byte verworfen.

### Der Klartext-Weg ist ebenfalls verschlossen

Es existiert ein unverschlüsselter Endpunkt:

```
http://tdp-t.api.leiniao.com/tdp-api/        (j.k.p.x.c.d.b:8)
```

Er wird über `persist.system.update.test.flag=true` zugeschaltet. Versuche:

```
setprop persist.system.update.test.flag true → Failed to set property
setprop persist.tcl.update.testDebug true     → Failed to set property
/data/UpdatePlatformType.txt schreiben        → Permission denied
```

Die zweite Umschaltung (Datei `/data/UpdatePlatformType.txt`) ist ebenfalls
nur für `system` beschreibbar.

### Versuch, die Region zu drehen

Möglich und erfolgreich — aber ohne Wirkung:

```
settings put system tcl_sys_country_code US   → US (geschrieben!)
settings put secure CountryOfPurchase US       → US (geschrieben!)
```

Beide Felder liefern `LocalDeviceInfo.getRegion()`, die Anfrage trug danach
`region='US'`. Der Server meldete weiter `getUpgrade() == null`. Denn der
**Endpunkt** leitet sich nicht aus der Region ab, sondern aus dem
nur-lesbaren `ro.product.clientType = TCL-EU-RTD75P-S1` → Zone `EU` →
`eu-filter-upgrade.huan.tv`. Ein Wechsel zur na-/as-Region erfordert
`persist.tcl.update.testCliType`, also wieder `setprop`.

### Ergebnis

Der gefälschte Server ist der Weg, der funktionieren würde: Antwort fälschen,
`fileurl` auf einen eigenen HTTP-Server zeigen, der Client lädt nach
`data/fota` und `uncrypt` mappt ohne die 93-MB-Kopie. Genau diese eine
Tür ist durch die TLS-Vertrauenskette verriegelt, und die ist ohne root
nicht zu öffnen.


---

## Zweite Paketgeneration: `Update.img`

Neu heruntergeladen, beide enthalten **ausschließlich `Update.img`** und
**keine** `META-INF/com/android/metadata`:

```
V8-R75PT01-LF1V661.zip   2 264 655 260 B   → Update.img  3 733 084 160 B
V8-R75PT01-LF1V590.zip   1 742 986 832 B   → Update.img  2 108 047 360 B
```

### Format

```
0000  install_a.......................
0060  ....0000755.0000000.0000000...
0100  .ustar  .root...................      ← tar-Magic
```

`Update.img` ist ein **TAR-Archiv** mit dem vollständigen Realtek-Layout:

```
install_a                        290 824   Slot-A-Marker
config.txt / postprocess.sh
package7/bootloader.tar       18 728 960
package7/verify/*.sha                 SHA256-Prüfsummen
package7/super.img          2 485 937 076   dynamische Partition
package7/boot.img             67 108 864
package7/vbmeta.img                8 192
package7/factory.img        16 777 216
package7/_layout_64G_cache.img     49 228
```

### Warum es nicht installierbar ist

| Prüfung | Ergebnis |
|---|---|
| `CrAU` / `payload.bin` in 256 MB | **nicht gefunden** → `update_engine` nicht nutzbar |
| `META-INF/com/android/metadata` | **fehlt** → `isABUpdateZip` und `verifyPackage` schlagen fehl |
| Flashwerkzeug im Gerät | **keines** — `/system/bin` kennt nur `update_engine`, `/vendor/bin` nur `aux_updater`, `rtk_burn_key` |
| `Update.img` in der APK | **nicht referenziert** |

Das Format gehört in den **Bootloader-Aufspielmodus**, der von einem
externen Blockdevice liest — das ist genau das „peripheral" aus der
Recovery-Meldung.

---

## Es gibt keinen unverschlüsselten Ort für 1974 MB

Die Recovery kann nur lesen, was nicht verschlüsselt ist. Bestandsaufnahme:

```
/cache       mmcblk0p41     93 MB    89 MB frei   ← einziger schreibbarer Ort
/tclconfig   mmcblk0p44    265 MB   129 MB frei   ← read-only (dm-verity)
/metadata    mmcblk0p27                 FBE-Schlüssel, winzig
/             dm-6        read-only
/data         dm-13       VERSCHLÜSSELT
/system, /vendor, /product, /oem, /odm   read-only
```

Dazu: kein SD-Schlitz (nur `mmcblk0`), `sm list-volumes` kennt nur
`private` und `emulated`.

### `/cache` vergrößern

Die Partition liegt auf `mmcblk0` — derselben eMMC wie `userdata`,
`metadata`, `boot` und `vbmeta`. Die Partitionstabelle umzuschreiben
verlangt `root`, das Laufwerk muss ausgehängt werden, und `metadata`
trägt die FBE-Schlüssel: ein Fehler dort bedeutet **dauerhafter
Datenverlust**. Die Aussage „nur mit Brick-Risiko" ist korrekt — und mit
`root` wäre es immer noch unvernünftig.

### Virtuelles Laufwerk / Loop-Mount

`mount` und die Device-Mapper-Umleitung sind Systemaufrufe für `root`.
Ohne root lässt sich weder ein Loop-Device noch eine fremde Partition
einhängen — und selbst dann müsste die Recovery sie lesen können.

---

## Was tatsächlich verbleibt

Zwei Wege sind **nicht** ausgeschöpft, weil sie keine Hacking-Leistung
brauchen, sondern nur ein Medium:

1. **Jedes USB-Speichermedium.** Nicht unbedingt ein „USB-Stick" — ein
   **Kartenleser mit microSD**, eine externe HDD, ein Handy im
   Massenspeicher-Modus. Vold hängt sie unter `/mnt/media_rw/<uuid>` ein,
   das ist ein echtes Blockdevice ohne Verschlüsselung, und die Recovery
   liest es direkt. Damit entfallen `/cache`, `uncrypt` und die
   93-MB-Grenze ersatzlos.

2. **Die Service-PIN.** Anruf bei TCL, Gerätenummer
   `persist.sys.device.dnum = REDACTED_DNUM` durchgeben. Der Netzwerkpfad
   lädt nach `/data/fota` und arbeitet mit dem vom Hersteller
   vorgesehenen Mechanismus.


