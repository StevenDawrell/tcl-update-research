#!/usr/bin/env python3
"""
Dateinamen gegen die Regeln des Update-Clients prüfen.

Aufruf:
    python scripts/check_filename.py <dateiname.zip>
    python scripts/check_filename.py --system-version V8-R75PT01-LF1V548 <dateiname.zip>
    python scripts/check_filename.py --device <dateiname.zip>

Ohne --system-version wird die Version vom verbundenen Gerät gelesen.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402


def rules(system_version: str) -> tuple[str, int, int]:
    prefix = system_version[:15]
    tail = system_version[15:]
    current = int(tail) if tail.isdigit() else 0
    return prefix, current, len(prefix) + 4


def version_from_name(name: str) -> int:
    dot = name.find('.')
    if dot < 0:
        return 0
    base = name[:dot]
    if len(base.split('-')) != 3:
        return 0
    digits = base[-3:]
    return int(digits) if digits.isdigit() else 0


def check(name: str, system_version: str) -> tuple[bool, list[str]]:
    prefix, current, min_len = rules(system_version)
    reasons: list[str] = []

    if not name.lower().endswith('.zip'):
        reasons.append('Endung muss .zip sein')
    if not name.startswith(prefix):
        reasons.append(f'muss mit "{prefix}" beginnen')
    if len(name) <= min_len:
        reasons.append(f'muss länger als {min_len} Zeichen sein')
    if len(name.split('-')) != 3:
        reasons.append('genau drei mit Bindestrich getrennte Segmente')

    version = version_from_name(name)
    if version == 0:
        reasons.append('Versionsnummer nicht lesbar')
    elif version <= current:
        reasons.append(f'Version {version} ist nicht neuer als {current}')

    third = name.split('-')[2] if len(name.split('-')) >= 3 else ''
    if 'S' in third or 'G' in third:
        reasons.append('Sonderversion (S/G im dritten Segment)')

    return (not reasons), reasons


def main() -> int:
    ap = argparse.ArgumentParser(description='Dateinamen prüfen')
    ap.add_argument('filename', help='Name der ZIP-Datei')
    ap.add_argument('--system-version', help='Systemversion, z. B. V8-R75PT01-LF1V548')
    ap.add_argument('--device', action='store_true', help='Version vom Gerät lesen')
    args = ap.parse_args()

    if args.system_version:
        system_version = args.system_version
    elif args.device:
        try:
            serial = common.first_device()
            system_version = common.getprop(serial, 'ro.software.version_id')
            if not system_version:
                system_version = common.getprop(serial, 'ro.build.display.id')
        except RuntimeError as err:
            return common.die(str(err))
    else:
        return common.die('Bitte --system-version angeben oder --device verwenden.')

    prefix, current, min_len = rules(system_version)
    ok, reasons = check(args.filename, system_version)

    print('=' * 70)
    print('Dateinamen-Prüfung')
    print('=' * 70)
    print(f'  {"Systemversion":<26} {system_version}')
    print(f'  {"Erwartetes Präfix":<26} {prefix}')
    print(f'  {"Installierte Version":<26} {current}')
    print(f'  {"Mindestlänge":<26} {min_len}')
    print(f'  {"Geprüfter Name":<26} {args.filename}')
    print(f'  {"Ergebnis":<26} {"akzeptiert" if ok else "abgelehnt"}')

    if reasons:
        print('\n  Gründe:')
        for r in reasons:
            print(f'    - {r}')
        suggestion = f'{prefix}{str(current + 1).zfill(3)}.zip'
        print(f'\n  Vorschlag: {suggestion}')
        print(f'  Zielpfad : /sdcard/{suggestion}')
    else:
        print(f'\n  Zielpfad: /sdcard/{args.filename}')

    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())

