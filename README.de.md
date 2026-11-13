# TCL-Update-Forschung — Update ohne USB-Stick (G10 / 55C655)

![Status](https://img.shields.io/badge/status-research%20complete-blue)
[![DSGVO](https://img.shields.io/badge/DPR-redacted-orange)](docs/DATENSCHUTZ.md)
[![Lizenz](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)

**Englische Hauptfassung:** [README.md](README.md) — diese Datei ist die deutsche
Kurzfassung.

**Frage:** Kann man ein signiertes System-Update auf einem TCL-Google-TV
(Realtek RTD, Modell G10/55C655) **ohne** USB-Stick installieren — über
Netzwerk oder internen Speicher?

**Ergebnis: ein fundiert belegtes Nein.** Der Weg existiert nicht ohne eines von
drei Toren: physisches Blockmedium, Hersteller-OTA-Server oder Herstellerschlüssel.

---

## Kurz für Menschen

```
Wo du ablegst                →  Was passiert
──────────────────────────────────────────────────────────────────
/sdcard/… (FUSE)             → findet sie, muss nach /cache kopieren
                               /cache = 93 MB, Datei = 1974 MB → Abbruch ❌
/data/fota/… (rohes /data)   → Recovery liest direkt, kein /cache ✅
                               aber: nur der Hersteller-Server darf schreiben
USB-Blockmedium (media_rw)   → Recovery liest direkt vom Medium ✅
```

Die Datei muss zudem **signiert** sein (Herstellerschlüssel).

**Ratschlag (einfach → aufwändig):**
1. **Beliebiges USB-Blockmedium** — Kartenleser + microSD aus dem Handy, alte
   HDD/SSD, Handy im Massenspeicher-Modus, Raspberry-Pi-Zero-Gadget. FAT32.
2. **Service-PIN vom TCL-Kundendienst** (mit der Gerätenummer).
3. **Abwarten**, bis TCL regulär verteilt.
4. Für Bastler: ein **AB-Paket** (`payload.bin`) würde ohne USB gehen — aber
   nur, wenn der Hersteller es signiert hat.

---

## Für die Presse

| Frage | Antwort |
|---|---|
| Ist der Fernseher „geknackt"? | **Nein.** Nichts installiert, nichts verändert, keine Sicherheitsfunktion umgangen. |
| Ein Sicherheitsproblem? | Nein. Die Schutzmechanismen wirken wie vorgesehen — die Analyse bestätigt sie. |
| Praktische Folge? | Beliebiges USB-Kartenleser-Medium (kein „Stick" nötig) oder Service-PIN. |
| Schwachstellen? | Eine bereits offengelegte (CVE-2025-55971, blindes SSRF über UPnP) wurde bestätigt, ist für Update-Manipulation **nicht ausnutzbar** → [disclosure/](disclosure/). |

> **Datenschutz:** Keine echten Geräte-IDs, Seriennummern, Tokens oder
> API-Schlüssel — alle `REDACTED_*` → [docs/DATENSCHUTZ.md](docs/DATENSCHUTZ.md).

---

## Technische Doku & Reproduzierbarkeit

- Englisch: [docs/en/OVERVIEW.md](docs/en/OVERVIEW.md),
  [INSTALLATION_PATH.md](docs/en/INSTALLATION_PATH.md),
  [RESEARCH_STATE.md](docs/en/RESEARCH_STATE.md)
- Deutsch: [docs/HINTERGRUND.md](docs/HINTERGRUND.md),
  [docs/INSTALLATIONSWEG.md](docs/INSTALLATIONSWEG.md),
  [docs/RECHERCHE_STAND.md](docs/RECHERCHE_STAND.md)
- RE-Herkunft: [src/README.md](src/README.md) · Werkzeuge: [scripts/](scripts/)

## Ethik

Nichts installiert/geflasht, keine Sicherheitsfunktion umgangen, Geräte-ID
redigiert (DSGVO), keine Exploits veröffentlicht. Lizenz MIT.
