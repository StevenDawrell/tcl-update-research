# Sprachen

Die Oberfläche ist in 26 Sprachen verfügbar. Englisch ist die Basissprache.

## Erkannte Sprachen

Die Auswahl erfolgt automatisch über die Browsersprache (`navigator.languages`).
Reihenfolge:

1. gespeicherte Wahl des Nutzers
2. Browsersprache (exakte Übereinstimmung, dann Grundsprache)
3. Englisch als Rückfallebene

Beispiel: Browser meldet `de-AT`, vorhanden ist `de` → Deutsch wird verwendet.
Browser meldet `ja` (nicht vorhanden) → Englisch wird verwendet.

Die Auswahl lässt sich jederzeit über das Menü oben rechts ändern und bleibt
gespeichert.

## Verfügbare Sprachen

| Code | Sprache | Nativ |
|---|---|---|
| `en` | English | English |
| `bg` | Bulgarian | Български |
| `cs` | Czech | Čeština |
| `da` | Danish | Dansk |
| `de` | German | Deutsch |
| `el` | Greek | Ελληνικά |
| `es` | Spanish | Español |
| `et` | Estonian | Eesti |
| `fi` | Finnish | Suomi |
| `fr` | French | Français |
| `ga` | Irish | Gaeilge |
| `hr` | Croatian | Hrvatski |
| `hu` | Hungarian | Magyar |
| `it` | Italian | Italiano |
| `lt` | Lithuanian | Lietuvių |
| `lv` | Latvian | Latviešu |
| `mt` | Maltese | Malti |
| `nl` | Dutch | Nederlands |
| `pl` | Polish | Polski |
| `pt` | Portuguese | Português |
| `ro` | Romanian | Română |
| `ru` | Russian | Русский |
| `sk` | Slovak | Slovenčina |
| `sv` | Swedish | Svenska |
| `uk` | Ukrainian | Українська |
| `zh` | Chinese | 中文 |

Damit sind alle 24 EU-Amtssprachen abgedeckt sowie Russisch, Ukrainisch und Chinesisch.

## Aufbau

```
web/locales/
  index.json      Liste der Sprachen (Code, Name, Nativname)
  en.json         Basis
  de.json         …
  zh.json         …
```

Jede Sprachdatei enthält dieselben Schlüssel. Fehlt ein Schlüssel, wird der
englische Text angezeigt; fehlt auch der, erscheint der Schlüssel selbst.

## Neue Sprache hinzufügen

1. `web/locales/en.json` kopieren und als `<code>.json` speichern.
2. Werte übersetzen, Schlüssel unverändert lassen.
3. Eintrag in `web/locales/index.json` ergänzen.
4. Prüfen:

```bash
python scripts/check_i18n.py
```

## Text ändern

1. In `en.json` den Schlüssel anpassen.
2. Dieselbe Änderung in allen anderen Sprachdateien vornehmen.
3. Prüfen, dass keine Schlüssel fehlen:

```bash
python scripts/check_locales.py
```

## Verwendung im Code

Statische Texte im HTML:

```html
<h2 data-i18n="step1.title">Select update package</h2>
<input data-i18n-ph="settings.adbPlaceholder">
```

Der englische Text steht als Inhalt im HTML, damit vor dem Laden der Sprache
kein leerer Bildschirm erscheint.

Dynamische Texte im TypeScript:

```ts
import * as i18n from './i18n.js';

const text = i18n.t('step1.name');
```

## Prüfwerkzeuge

| Skript | Zweck |
|---|---|
| `scripts/check_locales.py` | Vollständigkeit aller Sprachdateien |
| `scripts/check_html_keys.py` | Schlüssel im HTML gegen `en.json` |
| `scripts/check_i18n.py` | Gesamtprüfung, optional mit Server |

```bash
python scripts/check_i18n.py --server http://localhost:8787
```

