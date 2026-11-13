# Datenschutz (DSGVO / GDPR)

Diese Veröffentlichung wurde nach den Grundsätzen der Datenminimierung
(Art. 5 Abs. 1 lit. c DSGVO) aufbereitet.

## Was wurde redigiert

| Kategorie | Beispiel (echt) | Im Repo |
|---|---|---|
| Geräte-Seriennummer | 3802…CC08C | `REDACTED_SERIAL` |
| Gerätenummer (dnum) | (neunstellige Gerätenummer) | `REDACTED_DNUM` |
| Gerätetoken (didtoken) | 369c…0c5f | `REDACTED_DIDTOKEN` |
| Aktivierungsschlüssel | 13ff…fbff | `REDACTED_ACTIVEKEY` |
| Gerät-ID | baad…2707 | `REDACTED_DEVICEID` |
| Sitzungs-Token | 4999…106 | `REDACTED_TOKEN` |
| API-App-ID / App-Key | (aus Firmware-Code) | `REDACTED_APPID` / `REDACTED_APPKEY` |
| Build-Kennung / Zeitstempel | 10.60.03_10c4883_260908… | generisch maskiert |

## Was bewusst enthalten ist

- **Firmware-interne API-Schlüssel** sind *keine* personenbezogenen Daten, aber
  sie werden ebenfalls redigiert, um Missbrauch zu vermeiden. Ihre Existenz und
  Rolle wird beschrieben, nicht ihr Wert.
- **Code-Ausschnitte** (Java) aus der Firmware dienen der Nachvollziehbarkeit
  wissenschaftlicher Befunde (Zitatrecht / wissenschaftliche Analyse). Sie
  enthalten keine Geräte- oder Nutzerdaten.
- **Pfade und Eigenschaftsnamen** (`/data/fota`, `ro.software.version_id`) sind
  öffentliche Firmware-Strukturen, keine personenbezogenen Daten.

## Prinzipien

1. **Keine echten Identifikatoren** – alle Werte sind Platzhalter.
2. **Keine Nutzerdaten** – es wurde ausschließlich ein Testgerät analysiert,
   ohne Konten, ohne personenbezogene Inhalte.
3. **Reproduzierbarkeit ohne PII** – die Skripte funktionieren mit beliebigen
   Geräten; sensible Werte werden als Parameter/Platzhalter übergeben.
4. **Widerrufbarkeit** – sollte versehentlich ein echter Wert enthalten sein,
   wird er auf Anfrage umgehend entfernt (→ SECURITY.md).

## Kontakt

Datenschutzanfragen über das private Meldeformular des Repositories oder die
Kontaktmöglichkeit in SECURITY.md.
