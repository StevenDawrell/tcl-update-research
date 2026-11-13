#!/usr/bin/env python3
"""
Gerätezustand erfassen: Version, Slot, Update-Dienst.

Aufruf:
    python scripts/diagnose.py
    python scripts/diagnose.py --serial <SERIENNUMMER>
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

PROPS = [
    'ro.product.device', 'ro.product.name', 'ro.product.brand', 'ro.product.model',
    'ro.software.version_id', 'ro.build.version.release', 'ro.build.version.sdk',
    'ro.build.display.id', 'ro.build.version.incremental', 'ro.build.date.utc',
    'ro.build.version.security_patch', 'ro.build.fingerprint',
    'ro.boot.slot_suffix', 'ro.boot.hardware',
    'ro.serialno', 'persist.sys.device.dnum',
]


def main() -> int:
    ap = argparse.ArgumentParser(description='Gerätezustand erfassen')
    ap.add_argument('--serial', help='Seriennummer (sonst erstes Gerät)')
    args = ap.parse_args()

    try:
        serial = args.serial or common.first_device()
    except RuntimeError as err:
        return common.die(str(err))

    common.header('Gerät')
    common.row('Seriennummer', serial)
    for key in PROPS:
        try:
            common.row(key, common.getprop(serial, key) or '—')
        except RuntimeError:
            common.row(key, '—')

    common.header('Update-Dienst')
    try:
        engine = common.adb(['shell', 'getprop', 'init.svc.update_engine'], serial=serial)
        common.row('init.svc.update_engine', engine or '—')
        binder = common.adb(['shell', 'service check android.os.UpdateEngineService'], serial=serial)
        common.row('UpdateEngine-Binder', binder or '—')
        slot = common.getprop(serial, 'ro.boot.slot_suffix')
        common.row('Aktiver Slot', slot or '—')
    except RuntimeError as err:
        common.row('Abfrage', f'nicht möglich ({err})')

    common.header('Speicher')
    try:
        df = common.adb(['shell', 'df', '-h', '/data'], serial=serial)
        for line in df.splitlines():
            print('  ' + line)
    except RuntimeError as err:
        common.row('Abfrage', f'nicht möglich ({err})')

    common.header('Installationsdateien im Zielordner')
    try:
        listing = common.adb(['shell', 'ls', '-l', '/sdcard/'], serial=serial)
        zips = [l for l in listing.splitlines() if l.strip().endswith('.zip')]
        if zips:
            for line in zips:
                print('  ' + line.strip())
        else:
            print('  Keine ZIP-Datei im Stammverzeichnis.')
            print('  Das Paket muss unter /sdcard/<name>.zip liegen.')
    except RuntimeError as err:
        common.row('Abfrage', f'nicht möglich ({err})')

    return 0


if __name__ == '__main__':
    sys.exit(main())

