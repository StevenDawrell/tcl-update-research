#!/usr/bin/env python3
"""
Prueft die Sprachdateien und die Auslieferung durch den Server.

Aufruf:
    python scripts/check_i18n.py
    python scripts/check_i18n.py --server http://localhost:8787
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCALES = os.path.join(ROOT, 'web', 'locales')
BASE = 'en.json'


def load(path: str) -> dict[str, str]:
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if isinstance(v, str)}


def fetch(url: str, timeout: int = 5) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b''
    except Exception:
        return 0, b''


def main() -> int:
    server = None
    if '--server' in sys.argv:
        i = sys.argv.index('--server')
        if i + 1 < len(sys.argv):
            server = sys.argv[i + 1].rstrip('/')

    base = load(os.path.join(LOCALES, BASE))
    files = sorted(f for f in os.listdir(LOCALES) if f.endswith('.json') and f != 'index.json')

    print('=' * 62)
    print('Sprachdateien')
    print('=' * 62)
    print(f'  Basis        : {BASE} mit {len(base)} Schlüsseln')
    print(f'  Dateien      : {len(files)}')

    faulty = 0
    for name in files:
        try:
            data = load(os.path.join(LOCALES, name))
        except json.JSONDecodeError as err:
            print(f'  {name:<10} JSON-FEHLER: {err}')
            faulty += 1
            continue
        missing = set(base) - set(data)
        empty = [k for k, v in data.items() if not v.strip()]
        if missing or empty:
            print(f'  {name:<10} unvollständig (fehlt {len(missing)}, leer {len(empty)})')
            faulty += 1
        else:
            print(f'  {name:<10} {len(data):>3} Schlüssel · OK')

    # Index
    try:
        with open(os.path.join(LOCALES, 'index.json'), encoding='utf-8') as f:
            index = json.load(f)
        codes = {e['code'] for e in index}
        present = {f[:-5] for f in files}
        print(f'\n  index.json   : {len(index)} Einträge')
        if codes != present:
            print(f'  Abweichung   : {sorted(codes ^ present)}')
            faulty += 1
    except Exception as err:
        print(f'\n  index.json fehlerhaft: {err}')
        faulty += 1

    if server:
        print()
        print('=' * 62)
        print(f'Auslieferung über {server}')
        print('=' * 62)
        for path in ('locales/index.json', 'locales/en.json', 'locales/de.json', 'app.js', 'index.html'):
            status, body = fetch(f'{server}/{path}')
            mark = 'OK  ' if status == 200 else 'FEHLT'
            print(f'  {mark} /{path:<24} {status} {len(body):>7} Bytes')
            if status != 200:
                faulty += 1

    print()
    if faulty:
        print(f'{faulty} Problem(e) gefunden.')
        return 2
    print('Alles in Ordnung.')
    return 0


if __name__ == '__main__':
    sys.exit(main())

