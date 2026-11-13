# TCL-Update-Forschung: Update ohne USB-Stick (G10 / 55C655)

[![Status](https://img.shields.io/badge/status-research-complete-blue)](#)
[![Reproduzierbar](https://img.shields.io/badge/reproducible-yes-brightgreen)](#reproduzierbarkeit)
[![DSGVO](https://img.shields.io/badge/DPR-redacted-orange)](docs/DATENSCHUTZ.md)
[![Lizenz](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)

**Wissenschaftliche Reverse-Engineering-Untersuchung:** Kann man ein signiertes
System-Update auf einem TCL-Google-TV (Modell G10 / 55C655) installieren, *ohne*
einen USB-Stick zu verwenden – also rein über Netzwerk oder internen Speicher?

Ergebnis: ein **negatives, aber fundiert belegtes**. Der Weg existiert nicht ohne
ein physisches Blockmedium, den Herstellerschlüssel oder den Hersteller-Server.
Dieses Repository hält fest, *warum* – und *was* stattdessen funktioniert.

---

## Für die Presse / Kurzüberblick

| Frage | Antwort |
|---|---|
| **Was wurde untersucht?** | Alle Wege, eine Firmware-Datei ohne USB-Stick auf einem TCL-Google-TV zu installieren. |
| **Ist der Fernseher „geknackt"?** | **Nein.** Nichts installiert, nichts verändert, keine Sicherheitsfunktion umgangen. Gerät unverändert. |
| **Ist es ein Sicherheitsproblem?** | Nein. Die Schutzmechanismen (Signatur, SELinux, verschlüsselter Speicher) funktionieren wie vorgesehen – die Analyse bestätigt sie. |
| **Praktischer Ratschlag?** | Beliebiges USB-Kartenleser-Medium (SD aus dem Handy) verwenden – **kein „Stick" nötig** – oder Service-PIN des TCL-Kundendienstes. |
| **Verwundbare Stellen?** | Eine bereits offengelegte Schwachstelle (CVE-2025-55971, blindes SSRF über UPnP) wurde bestätigt, ist aber für Update-Manipulation **nicht ausnutzbar** → [disclosure/](disclosure/). |
| **Bedeutung** | „Update ohne Medium" ist bewusst verriegelt – Hersteller-Server, nicht lokale Dateien, sind die Kontrollinstanz. |

> **Datenschutz:** Keine echten Geräte-IDs, Seriennummern, Tokens oder
> API-Schlüssel – alle durch `REDACTED_*` ersetzt → [docs/DATENSCHUTZ.md](docs/DATENSCHUTZ.md).

---

## Für Hobby-ITler / Praktische Zusammenfassung

**Das Problem:** Du hast die Update-Datei, sie ist auf dem Fernseher – das
Update-Programm findet sie, kann sie aber nicht installieren.

**Warum?** Am *Ablageort*, nicht an der Datei:

```
Wo du ablegst              →  Was passiert
─────────────────────────────────────────────────────────────────
/sdcard/… (FUSE)           → findet sie, muss nach /cache kopieren
                             /cache = 93 MB, Datei = 1974 MB → Abbruch ❌
/data/fota/… (rohes /data) → Recovery liest direkt, kein /cache ✅
                             aber: nur der Hersteller-Server darf schreiben
USB-Stick /mnt/media_rw    → Recovery liest direkt vom Medium ✅
```

**Die Klammer:** Die Datei muss **signiert** sein (Herstellerschlüssel). Ohne
ihn lehnt das Gerät jede Änderung ab – korrekt so.

**Was du tun kannst (einfach → aufwändig):**
1. **Beliebiges USB-Blockmedium** – Kartenleser + microSD aus dem Handy, alte
   HDD/SSD, altes Handy im Massenspeicher-Modus, Raspberry Pi Zero als
   USB-Gadget. FAT32. Am einfachsten.
2. **Service-PIN vom TCL-Kundendienst** (mit der Gerätenummer).
3. **Abwarten**, bis TCL das Update regulär verteilt.
4. Für Technik-Interessierte: Ein *AB-Paket* (`payload.bin`) würde auch ohne USB
   funktionieren – aber nur, wenn der Hersteller es signiert hat.

**Was *nicht* funktioniert (und warum):** selbstgebaute Pakete, veränderte Apps,
Test-Menüs, Netzwerk-Tricks – jeweils durch eine dokumentierte Schutzmaßnahme
blockiert → [docs/](docs/).

---

## Für Informatiker / Technische Dokumentation

| Dokument | Inhalt |
|---|---|
| [docs/en/OVERVIEW.md](docs/en/OVERVIEW.md) | Übersicht, Systemarchitektur, Angriffsoberflächen |
| [docs/en/INSTALLATION_PATH.md](docs/en/INSTALLATION_PATH.md) | `uncrypt`, `/cache`-Bottleneck, A/B vs. Block |
| [docs/en/RESEARCH_STATE.md](docs/en/RESEARCH_STATE.md) | Befundkatalog: 20+ Wege, Code-Stellen, Live-Tests |
| [docs/](docs/) | Deutsche Originale + DATENSCHUTZ |

**Kernbefunde (mit Beweis):**
- **A/B-Pfad lebt, aber Signatur fehlt.** Selbst gebautes `payload.bin` mit
  `ota-type=AB` wird angenommen (`isAbUpdateZip: true`), umgeht `/cache`
  (`isNeedProcessPackage false`) – scheitert an `RecoverySystem.verifyPackage`.
  *Reproduzierbar: `scripts/build_ab_probe.py`.*
- **`/sdcard` ist der falsche Ort.** FUSE erzwingt `/cache`-Kopie
  (93 MB vs. 1974 MB); nur `/data/fota` oder Blockmedium vermeiden das.
- **Server-Antwort ist die Kontrollinstanz.** Nur eine signierte `UpgradeBean`
  befähigt den Client, selbst nach `/data/fota` zu laden. TLS-Systemtrust
  verhindert Fälschung (kein Pinning, aber System-CA-Store).
- **Kein externer Datei-Schreiber.** Vollständige Suche über alle dekompilierten
  Apps: die einzigen `copyFile`-Funktionen sind ungebundene AIDL bzw. toter Code.

**Methodik:** Statisches RE (JADX), Mustersuche über Datei-I/O und Pfade,
reproduzierbare Live-Tests (Android 12, Build `user`, AVB `green`, FBE). Alles
read-only bzw. rückgängig; nichts geflasht.

### Reproduzierbarkeit

Jeder zentrale Befund hat ein Skript unter [scripts/](scripts/).
Gerätezustand: [docs/en/RESEARCH_STATE.md](docs/en/RESEARCH_STATE.md) §1.

---

## Struktur

```
README.md · LICENSE · SECURITY.md · CITATION.cff · CODE_OF_CONDUCT.md
disclosure/   CVE-2025-55971 (korrekt eingeordnet)
docs/         Deutsche Originale + DATENSCHUTZ ·  docs/en/ Englische Fassung
scripts/      Reproduzierbare Werkzeuge (PII-frei) · src/ RE-Notizen
```

## Ethik & Verantwortung

- **Nichts** installiert, geflasht oder dauerhaft verändert.
- **Keine** Sicherheitsfunktion umgangen; die Analyse bestätigt ihre Wirksamkeit.
- Geräte-Identifikatoren redigiert (DSGVO).
- CVE-2025-55971 ist öffentlich; dieses Repo zeigt, warum sie für
  Update-Manipulation **nicht ausreicht** – ohne sie ausnutzbar zu machen.

## Lizenz

MIT – siehe [LICENSE](LICENSE).
