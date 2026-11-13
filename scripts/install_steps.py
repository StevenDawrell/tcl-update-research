#!/usr/bin/env python3
"""
Paket übertragen und Update-Bildschirm öffnen.

Aufruf:
    python scripts/install_steps.py <datei.zip>
    python scripts/install_steps.py <datei.zip> --open
    python scripts/install_steps.py <datei.zip> --serial <SERIENNUMMER> --open

Ablauf:
    1. Systemversion lesen
    2. Dateinamen prüfen und ggf. korrigieren
    3. Paket nach /sdcard/ übertragen
    4. Übertragung verifizieren
    5. Optional: Update-Bildschirm öffnen

Die Installation selbst führt das Gerät aus (Menüpunkt "Lokales Update").
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402
import check_filename  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description='Paket übertragen')
    ap.add_argument('file', help='Pfad zur ZIP-Datei')
    ap.add_argument('--serial', help='Seriennummer (sonst erstes Gerät)')
    ap.add_argument('--open', action='store_true', help='Update-Bildschirm öffnen')
    ap.add_argument('--force', action='store_true', help='Namensprüfung überspringen')
    args = ap.parse_args()

    if not os.path.isfile(args.file):
        return common.die(f'Datei nicht gefunden: {args.file}')

    try:
        serial = args.serial or common.first_device()
    except RuntimeError as err:
        return common.die(str(err))

    common.header('1. Gerät')
    common.row('Seriennummer', serial)
    try:
        system_version = common.getprop(serial, 'ro.software.version_id')
        if not system_version:
            system_version = common.getprop(serial, 'ro.build.display.id')
        product = common.getprop(serial, 'ro.product.name')
    except RuntimeError as err:
        return common.die(str(err))
    common.row('Systemversion', system_version or '—')
    common.row('Produkt', product or '—')

    common.header('2. Dateiname')
    name = os.path.basename(args.file)
    if args.force:
        common.row('Prüfung', 'übersprungen')
        target_name = name
    else:
        ok, reasons = check_filename.check(name, system_version)
        prefix, current, _ = check_filename.rules(system_version)
        if ok:
            common.row('Ergebnis', 'akzeptiert')
            target_name = name
        else:
            target_name = f'{prefix}{str(current + 1).zfill(3)}.zip'
            common.row('Ergebnis', 'abgelehnt')
            for r in reasons:
                common.row('', r)
            common.row('Verwendet', target_name)
    remote = f'/sdcard/{target_name}'

    common.header('3. Übertragung')
    size_mb = os.path.getsize(args.file) / 1048576
    common.row('Quelle', args.file)
    common.row('Ziel', remote)
    common.row('Größe', f'{size_mb:.1f} MB')
    print('  Überträgt ...')
    try:
        common.adb(['push', args.file, remote], serial=serial, timeout=1800)
    except RuntimeError as err:
        return common.die(str(err))
    common.row('Status', 'übertragen')

    common.header('4. Kontrolle')
    try:
        remote_size = common.adb(['shell', 'stat', '-c', '%s', remote], serial=serial)
        expected = os.path.getsize(args.file)
        match = remote_size.strip() == str(expected)
        common.row('Größe auf Gerät', remote_size.strip())
        common.row('Übereinstimmung', 'ja' if match else 'nein')
        if not match:
            return common.die('Übertragung unvollständig, bitte wiederholen.')
    except RuntimeError as err:
        return common.die(str(err))

    common.header('5. Installation')
    if args.open:
        try:
            common.adb(['shell', 'am', 'start', '-a',
                        'android.settings.SYSTEM_UPDATE_SETTINGS'], serial=serial)
            common.row('Update-Bildschirm', 'geöffnet')
        except RuntimeError as err:
            common.row('Update-Bildschirm', f'nicht geöffnet ({err})')
    else:
        common.row('Nächster Schritt', 'am Fernseher: Softwareupdate > Lokales Update')
    print()
    print('  Am Fernseher: Einstellungen > System > Info > Softwareupdate > Lokales Update')
    print('  Während der Installation nicht ausschalten.')
    return 0


if __name__ == '__main__':
    sys.exit(main())

