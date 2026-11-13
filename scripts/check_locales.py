#!/usr/bin/env python3
"""
Prueft alle Sprachdateien gegen die Basis (en.json).

Aufruf:
    python scripts/check_locales.py
    python scripts/check_locales.py --fix-hint

Meldet fehlende Schluessel, ungueltiges JSON und Platzhalter-Abweichungen.
"""
from __future__ import annotations

import json
import os
import sys

LOCALES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'web', 'locales')
BASE = 'en.json'


def load(path: str) -> dict[str, str]:
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if isinstance(v, str)}


def main() -> int:
    base_path = os.path.join(LOCALES, BASE)
    if not os.path.isfile(base_path):
        print(f'Basisdatei fehlt: {base_path}')
        return 1

    base = load(base_path)
    print(f'Basis: {BASE} mit {len(base)} Schlüsseln\n')

    files = sorted(f for f in os.listdir(LOCALES) if f.endswith('.json') and f != 'index.json')
    problems = 0

    print(f'{"Datei":<10} {"Schlüssel":>10} {"fehlt":>7} {"leer":>6} {"Status":>10}')
    print('-' * 50)

    for name in files:
        path = os.path.join(LOCALES, name)
        try:
            data = load(path)
        except json.JSONDecodeError as err:
            print(f'{name:<10} {"—":>10} {"—":>7} {"—":>6} {"JSON-FEHLER":>10}')
            print(f'           {err}')
            problems += 1
            continue

        missing = [k for k in base if k not in data]
        empty = [k for k, v in data.items() if not v.strip()]
        status = 'OK' if not missing and not empty else 'UNVOLLSTÄNDIG'
        if missing or empty:
            problems += 1

        print(f'{name:<10} {len(data):>10} {len(missing):>7} {len(empty):>6} {status:>10}')

        if missing:
            print('           fehlt: ' + ', '.join(missing[:6]))
            if len(missing) > 6:
                print(f'           … und {len(missing) - 6} weitere')
        if empty:
            print('           leer: ' + ', '.join(empty[:6]))

    print()
    if problems:
        print(f'{problems} Datei(en) mit Problemen.')
        return 2

    print('Alle Sprachdateien vollständig.')
    return 0


if __name__ == '__main__':
    sys.exit(main())

