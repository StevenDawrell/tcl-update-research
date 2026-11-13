# Hintergrund: Technische Grundlagen

Diese Datei erklärt, wie das Werkzeug arbeitet und warum die einzelnen Schritte
notwendig sind. Sie richtet sich an Mitwirkende und an Anwender, die verstehen
wollen, was im Hintergrund geschieht.

---

## Update-Ablauf auf dem Gerät

TCL-Fernseher mit Android TV verwalten Systemupdates über einen herstellereigenen
Client. Dieser Client bietet drei Wege:

| Weg | Auslöser | Voraussetzung |
|---|---|---|
| Online-Update | Hersteller-Server | Internetverbindung |
| Lokales Update | Datei im internen Speicher | Update-Datei im richtigen Ordner |
| Werks-Recovery | Tastenkombination beim Einschalten | Paket auf USB-Datenträger |

Das Werkzeug nutzt den **zweiten Weg**. Der Client selbst führt Verifikation und
Installation durch; das Werkzeug bereitet die Voraussetzungen vor.

---

## Suche nach dem Paket

Beim Aufruf von „Lokales Update" durchsucht der Client das **Stammverzeichnis**
des internen Speichers (`/sdcard/`). Unterordner werden nicht betreten. Für jede
gefundene Datei gelten diese Bedingungen:

1. Die Datei endet auf `.zip`.
2. Der Name beginnt mit den ersten 15 Zeichen der Geräte-Systemversion.
3. Der Name ist länger als dieses Präfix plus vier Zeichen.
4. Der Name besteht aus drei mit Bindestrich getrennten Segmenten.
5. Die letzten drei Zeichen des ersten Segments ergeben eine Zahl.
6. Diese Zahl ist größer als die aktuell installierte Version.
7. Das dritte Segment enthält weder `S` noch `G`.

Beispiel mit der Systemversion `V8-R75PT01-LF1V548`:

```
Präfix      : V8-R75PT01-LF1V   (15 Zeichen)
Installiert : 548
Dateiname   : V8-R75PT01-LF1V648.zip
```

Der Name zerfällt in drei Segmente:

| Segment | Inhalt | Prüfung |
|---|---|---|
| 1 | `V8-R75PT01-LF1V648` | letzte drei Zeichen = `648` |
| 2 | — | (Teil des ersten Segments) |
| 3 | — | darf kein `S` oder `G` enthalten |

Entscheidend: `648 > 548`, der Name beginnt mit dem Präfix und ist lang genug.
Der Client akzeptiert die Datei.

Passt der Name nicht, wird die Datei ignoriert – ohne Fehlermeldung.

---

## Systemversion ermitteln

Die vom Client verwendete Version steht im Property `ro.software.version_id`:

```bash
adb shell getprop ro.software.version_id
```

Nicht zu verwechseln mit `ro.build.display.id` – dieses Property enthält die
interne Build-Kennung, nicht die Software-Version.

---

## Übertragung

Das Paket wird per ADB übertragen:

```bash
adb push <datei>.zip /sdcard/<name>.zip
```

Nach der Übertragung wird die Größe auf dem Gerät gegen die lokale Datei geprüft.
Bei Abweichung ist die Übertragung zu wiederholen.

---

## Verifikation durch das Gerät

Der Client prüft das Paket in mehreren Stufen:

1. **Dateiname** – siehe oben
2. **ZIP-Struktur** – Metadaten und Inhaltsverzeichnis
3. **Signatur** – gegen den im System hinterlegten Herstellerschlüssel
4. **Gerätefreigabe** – Produktname, Marke und Gerätekennung
5. **Versionsvergleich** – Paket muss neuer sein als der installierte Stand

Das Werkzeug kann Schritt 1, 4 und 5 vorab prüfen und zeigt Abweichungen an.

---

## Verbindungsarten

**USB** ist der zuverlässigste Weg. Nach dem Anschließen erscheint am Fernseher
ein Dialog zur Freigabe; ohne Bestätigung bleibt das Gerät im Zustand
`unauthorized` und nimmt keine Befehle an.

**Netzwerk** setzt voraus, dass das Gerät dies anbietet:

- Ältere Geräte: `adb tcpip 5555` bei bestehender USB-Verbindung, danach
  `adb connect <IP>:5555`.
- Android 11 und neuer: `adb pair <IP>:<PORT>` mit Pairing-Code.

Viele TCL-Geräte bieten in den Entwickleroptionen nur USB-Debugging an.

---

## Aufbau des Werkzeugs

```
Browser  ──HTTP/WebSocket──▶  Node-Server  ──execFile──▶  adb  ──USB/Netzwerk──▶  Fernseher
   │                              │
   │                              ├─ discovery.ts   SSDP-Suche
   └── Oberfläche                 ├─ ota.ts         ZIP-Analyse
       (HTML/CSS/TS)              ├─ naming.ts      Namensregeln
                                  └─ adb.ts         Gerätekommandos
```

Der Server läuft lokal und öffnet keine Ports nach außen. Die Oberfläche wird vom
selben Server ausgeliefert.

---

## Grenzen des Verfahrens

- **Keine Umgehung der Signaturprüfung.** Das Gerät akzeptiert nur Pakete, die mit
  dem Herstellerschlüssel signiert sind.
- **Keine Änderung am System.** Das Werkzeug überträgt eine Datei und öffnet einen
  Bildschirm. Alles Weitere entscheidet das Gerät.
- **Abhängig vom Client-Verhalten.** Ändert der Hersteller die Namensregeln oder
  den Suchpfad, muss das Werkzeug angepasst werden. Die Regeln stehen
  ausschließlich in `naming.ts`.

---

## Paketformate

Der Client akzeptiert zwei Formate:

| Format | Merkmal | Verbreitung |
|---|---|---|
| Block-basiert | `*.new.dat.br` + `*.patch.dat` + `*.transfer.list` | ältere Geräte |
| Payload | `payload.bin` + `payload_properties.txt` | ab Android 11 |

Beide enthalten `META-INF/com/android/metadata` mit der Paketbeschreibung und
`META-INF/com/android/otacert` mit dem Signaturzertifikat.

