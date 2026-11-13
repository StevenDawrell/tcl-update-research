#!/usr/bin/env python3
"""Kurzer Funktionstest der lokalen API. Nur Standardbibliothek."""
from __future__ import annotations

import json
import sys
import urllib.request

BASE = 'http://localhost:8787'


def call(path: str, body: dict | None = None) -> tuple[int, object]:
    data = None if body is None else json.dumps(body).encode('utf-8')
    req = urllib.request.Request(
        BASE + path,
        data=data,
        headers={'content-type': 'application/json'} if data else {},
        method='POST' if data else 'GET',
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8') or '{}')


def main() -> int:
    failures = 0

    def check(name: str, ok: bool, detail: str = '') -> None:
        nonlocal failures
        mark = 'OK  ' if ok else 'FEHLT'
        print(f'  {mark} {name:<26} {detail}')
        if not ok:
            failures += 1

    print('=' * 66)
    print('Funktionstest')
    print('=' * 66)

    code, env = call('/api/env')
    adb = (env or {}).get('adb') if isinstance(env, dict) else None
    check('/api/env', code == 200 and bool(adb), f'adb={bool(adb)}')

    code, devs = call('/api/devices')
    count = len((devs or {}).get('devices', [])) if isinstance(devs, dict) else 0
    check('/api/devices', code == 200, f'{count} Gerät(e)')

    if count:
        serial = devs['devices'][0]['serial']
        code, info = call('/api/device-info', {'serial': serial})
        props = (info or {}).get('props', {}) if isinstance(info, dict) else {}
        check('/api/device-info', code == 200 and bool(props),
              props.get('ro.product.name', '—'))

        sysver = props.get('ro.software.version_id', '')
        if sysver:
            code, naming = call('/api/naming', {
                'systemVersion': sysver,
                'filename': 'V8-XXXXXXXX-LF1V999.zip',
            })
            accepted = isinstance(naming, dict)
            check('/api/naming', code == 200 and accepted,
                  (naming or {}).get('target', '—'))
    else:
        print('  --   /api/device-info       übersprungen (kein Gerät)')
        print('  --   /api/naming            übersprungen (kein Gerät)')

    pkg = sys.argv[1] if len(sys.argv) > 1 else ''
    if pkg:
        code, insp = call('/api/inspect', {'file': pkg})
        version = (insp or {}).get('postVersion') if isinstance(insp, dict) else None
        check('/api/inspect', code == 200 and bool(version), version or '—')

    print()
    print(f'Ergebnis: {"alle Prüfungen bestanden" if failures == 0 else f"{failures} Fehler"}')
    return 0 if failures == 0 else 1


if __name__ == '__main__':
    sys.exit(main())

