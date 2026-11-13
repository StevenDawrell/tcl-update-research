#!/usr/bin/env python3
"""
Ergaenzt fehlende Schluessel in allen Sprachdateien aus dem englischen Basiswert.

Aufruf:
    python scripts/sync_locales.py            # Vorschau
    python scripts/sync_locales.py --write    # schreiben
"""
from __future__ import annotations

import json
import os
import sys

LOCALES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'web', 'locales')

# Uebersetzungen fuer neue Schluessel je Sprache
EXTRA: dict[str, dict[str, str]] = {
    'env.fileMode': {
        'bg': 'Отворено като файл — първо стартирайте сървъра',
        'cs': 'Otevřeno jako soubor — nejprve spusťte server',
        'da': 'Åbnet som fil — start serveren først',
        'de': 'Als Datei geöffnet — bitte zuerst den Server starten',
        'el': 'Άνοιγμα ως αρχείο — ξεκινήστε πρώτα τον διακομιστή',
        'es': 'Abierto como archivo — inicie primero el servidor',
        'et': 'Avatud failina — käivitage esmalt server',
        'fi': 'Avattu tiedostona — käynnistä ensin palvelin',
        'fr': 'Ouvert comme fichier — démarrez d\'abord le serveur',
        'ga': 'Oscailte mar chomhad — tosaigh an freastalaí ar dtús',
        'hr': 'Otvoreno kao datoteka — prvo pokrenite poslužitelj',
        'hu': 'Fájlként megnyitva — először indítsa el a kiszolgálót',
        'it': 'Aperto come file — avviare prima il server',
        'lt': 'Atidaryta kaip failas — pirmiausia paleiskite serverį',
        'lv': 'Atvērts kā fails — vispirms palaidiet serveri',
        'mt': 'Miftuħ bħala fajl — ibda s-server l-ewwel',
        'nl': 'Geopend als bestand — start eerst de server',
        'pl': 'Otwarto jako plik — najpierw uruchom serwer',
        'pt': 'Aberto como ficheiro — inicie primeiro o servidor',
        'ro': 'Deschis ca fișier — porniți mai întâi serverul',
        'ru': 'Открыто как файл — сначала запустите сервер',
        'sk': 'Otvorené ako súbor — najprv spustite server',
        'sv': 'Öppnad som fil — starta servern först',
        'uk': 'Відкрито як файл — спочатку запустіть сервер',
        'zh': '已作为文件打开 — 请先启动服务器',
    },
    'env.fileModeHint': {
        'bg': 'Изпълнете: npm start — след това отворете http://localhost:8787',
        'cs': 'Spusťte: npm start — poté otevřete http://localhost:8787',
        'da': 'Kør: npm start — åbn derefter http://localhost:8787',
        'de': 'Ausführen: npm start — dann http://localhost:8787 öffnen',
        'el': 'Εκτελέστε: npm start — μετά ανοίξτε http://localhost:8787',
        'es': 'Ejecute: npm start — luego abra http://localhost:8787',
        'et': 'Käivitage: npm start — seejärel avage http://localhost:8787',
        'fi': 'Suorita: npm start — avaa sitten http://localhost:8787',
        'fr': 'Exécutez : npm start — puis ouvrez http://localhost:8787',
        'ga': 'Rith: npm start — ansin oscail http://localhost:8787',
        'hr': 'Pokrenite: npm start — zatim otvorite http://localhost:8787',
        'hu': 'Futtassa: npm start — majd nyissa meg a http://localhost:8787 címet',
        'it': 'Eseguire: npm start — poi aprire http://localhost:8787',
        'lt': 'Paleiskite: npm start — tada atidarykite http://localhost:8787',
        'lv': 'Palaidiet: npm start — pēc tam atveriet http://localhost:8787',
        'mt': 'Mexxi: npm start — imbagħad iftaħ http://localhost:8787',
        'nl': 'Voer uit: npm start — open dan http://localhost:8787',
        'pl': 'Uruchom: npm start — następnie otwórz http://localhost:8787',
        'pt': 'Execute: npm start — depois abra http://localhost:8787',
        'ro': 'Rulați: npm start — apoi deschideți http://localhost:8787',
        'ru': 'Выполните: npm start — затем откройте http://localhost:8787',
        'sk': 'Spustite: npm start — potom otvorte http://localhost:8787',
        'sv': 'Kör: npm start — öppna sedan http://localhost:8787',
        'uk': 'Виконайте: npm start — потім відкрийте http://localhost:8787',
        'zh': '运行：npm start — 然后打开 http://localhost:8787',
    },
}


def main() -> int:
    write = '--write' in sys.argv
    base_path = os.path.join(LOCALES, 'en.json')
    with open(base_path, encoding='utf-8') as f:
        base = json.load(f)

    added = 0
    for name in sorted(f for f in os.listdir(LOCALES) if f.endswith('.json') and f != 'index.json'):
        code = name[:-5]
        path = os.path.join(LOCALES, name)
        with open(path, encoding='utf-8') as f:
            data = json.load(f)

        missing = [k for k in base if k not in data]
        if not missing:
            continue

        for key in missing:
            fallback = base[key]
            data[key] = EXTRA.get(key, {}).get(code, fallback)
            added += 1

        if write:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.write('\n')

        print(f'  {name:<10} +{len(missing)} ({", ".join(missing[:3])})')

    print()
    print(f'{added} Einträge {"geschrieben" if write else "fehlend (Vorschau)"}.')
    if not write and added:
        print('Zum Schreiben: python scripts/sync_locales.py --write')
    return 0


if __name__ == '__main__':
    sys.exit(main())

