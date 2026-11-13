# Security Policy

## Grundsatz

Diese Untersuchung wurde **verantwortungsvoll** durchgeführt:

- Es wurde **nichts** installiert, geflasht oder dauerhaft verändert.
- **Keine** Sicherheitsfunktion wurde umgangen – die Analyse bestätigt
  vielmehr, dass die Schutzmechanismen (Paketsignatur, SELinux,
  Dateisystemverschlüsselung) wie vorgesehen wirken.
- Es werden **keine** Exploits, Umgehungen oder funktionierenden
  Angriffsskripte veröffentlicht.

## Bekannte, öffentlich dokumentierte Schwachstelle

`disclosure/CVE-2025-55971.md` ordnet eine **bereits öffentlich** gemeldete
Schwachstelle (blindes SSRF über UPnP/DLNA) fachlich korrekt ein und zeigt,
warum sie **nicht** für Update-Manipulation ausreicht. Die Veröffentlichung
erfolgt ohne Exploit-Code, ausschließlich basierend auf der öffentlichen
CVE-Beschreibung und der Analyse des vorhandenen Firmware-Codes.

## Melden von Schwachstellen

Falls Sie in diesem Material einen Fehler oder eine unbekannte Schwachstelle
entdecken, melden Sie diese bitte über das private Meldeformular von GitHub
(*Security → Report a vulnerability*) oder per E-Mail an die Repository-Betreuer.
Bitte geben Sie an:

- betroffene Firmware-Version / Modell
- reproduzierbare Schritte
- Einschätzung der Auswirkung

Wir antworten in der Regel innerhalb von 14 Tagen und arbeiten nach den
Prinzipien der koordinierten Offenlegung.

## Scope

Im Scope: Firmware-Update-Mechanismen von TCL-Google-TVs (G10/55C655,
Realtek-RTD-Plattform), soweit sie in diesem Repository dokumentiert sind.
Nicht im Scope: aktive Angriffe auf Dritte, physische Manipulation,
Umgehung von Werksrechten.
