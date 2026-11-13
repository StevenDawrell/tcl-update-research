#!/usr/bin/env python3
"""Prueft, ob alle im HTML verwendeten i18n-Schluessel vorhanden sind."""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, 'web', 'index.html')
LOCALES = os.path.join(ROOT, 'web', 'locales')

ATTR = re.compile(r'data-i18n(?:-[a-z]+)?="([a-zA-Z0-9.]+)"')


def main() -> int:
    with open(HTML, encoding='utf-8') as f:
        html = f.read()

    used = set(ATTR.findall(html))
    with open(os.path.join(LOCALES, 'en.json'), encoding='utf-8') as f:
        base = {k for k, v in json.load(f).items() if isinstance(v, str)}

    print(f'HTML-Schlüssel : {len(used)}')
    print(f'en.json        : {len(base)}')

    missing = sorted(used - base)
    unused = sorted(base - used)

    if missing:
        print('\nFehlen in en.json:')
        for k in missing:
            print('  ' + k)
    else:
        print('\nAlle HTML-Schlüssel vorhanden.')

    if unused:
        print(f'\nNicht im HTML verwendet ({len(unused)}):')
        for k in unused[:15]:
            print('  ' + k)
        if len(unused) > 15:
            print(f'  … und {len(unused) - 15} weitere')

    return 0 if not missing else 2


if __name__ == '__main__':
    sys.exit(main())

