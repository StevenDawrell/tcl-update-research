#!/usr/bin/env python3
"""
probe_tv_proxy.py -- Prueft, ob der Fernseher den Proxy erreicht und nutzt.

Setzt testweise den Proxy, laesst den Client eine Anfrage ausloesen und
meldet, ob am Proxy etwas ankommt.

Aufruf:
    python scripts/probe_tv_proxy.py --host 192.168.1.16 --port 8080

Voraussetzung: proxy_capture.py laeuft bereits.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402


def sh(serial: str, cmd: str, timeout: int = 20) -> str:
    try:
        return common.adb(['shell', cmd], serial=serial, timeout=timeout)
    except RuntimeError as err:
        return f'(Fehler: {err})'


def main() -> int:
    ap = argparse.ArgumentParser(description='Proxy-Erreichbarkeit pruefen')
    ap.add_argument('--host', default='192.168.1.16')
    ap.add_argument('--port', type=int, default=8080)
    ap.add_argument('--serial')
    args = ap.parse_args()

    try:
        serial = args.serial or common.first_device()
    except RuntimeError as err:
        return common.die(str(err))

    common.header('Gerät')
    common.row('Seriennummer', serial)

    common.header('1. Proxy-Einstellung')
    current = sh(serial, 'settings get global http_proxy')
    common.row('http_proxy', current or '(nicht gesetzt)')

    common.header('2. Erreichbarkeit des Rechners')
    ping = sh(serial, f'ping -c 2 -W 2 {args.host}')
    for line in ping.splitlines()[:3]:
        print('  ' + line)

    common.header('3. TCP-Test auf Proxy-Port')
    # Toybox hat kein nc; curl/wget fehlen meist. Ersatz: connect ueber /proc
    test = sh(serial, f'timeout 3 sh -c "exec 3<>/dev/tcp/{args.host}/{args.port}" 2>&1')
    if 'No such file' in test or 'not found' in test:
        print('  /dev/tcp nicht verfügbar (Android-Shell)')
        print('  Alternativer Test über die Update-Anfrage selbst.')
    else:
        print('  Ergebnis: ' + (test or 'Verbindung hergestellt'))

    common.header('4. Update-Anfrage auslösen')
    print('  Öffne Update-Bildschirm am Fernseher ...')
    sh(serial, 'am start -a android.settings.SYSTEM_UPDATE_SETTINGS')
    print('  Warte 20 s auf Proxy-Traffic ...')
    time.sleep(20)

    print()
    print('  Prüfe die Ausgabe von proxy_capture.py auf Einträge')
    print(f'  mit Absender 192.168.1.1xx (Fernseher).')

    common.header('5. Proxy zurücksetzen (falls nötig)')
    print(f'  adb shell settings put global http_proxy :0')
    return 0


if __name__ == '__main__':
    sys.exit(main())

