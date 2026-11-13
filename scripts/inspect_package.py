#!/usr/bin/env python3
"""
OTA-Paket prüfen: Metadaten, Gerätefreigabe, Prüfsumme.

Aufruf:
    python scripts/inspect_package.py <datei.zip>
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import zipfile

META = 'META-INF/com/android/metadata'
SCRIPT = 'META-INF/com/google/android/updater-script'


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(8 << 20), b''):
            h.update(block)
    return h.hexdigest()


def read_metadata(zf: zipfile.ZipFile) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        text = zf.read(META).decode('utf-8', 'replace')
    except KeyError:
        return out
    for line in text.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            out[k.strip()] = v.strip()
    return out


def read_guards(zf: zipfile.ZipFile) -> dict[str, object]:
    try:
        script = zf.read(SCRIPT).decode('utf-8', 'replace')
    except KeyError:
        return {'device': None, 'products': [], 'brands': []}

    device = re.search(r'ro\.product\.device"\)\s*==\s*"([^"]+)"', script)
    products = re.findall(r'ro\.product\.name"\)\s*==\s*"([^"]+)"', script)
    brands = re.findall(r'ro\.product\.brand"\)\s*==\s*"([^"]+)"', script)
    return {
        'device': device.group(1) if device else None,
        'products': products,
        'brands': brands,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description='OTA-Paket prüfen')
    ap.add_argument('file', help='Pfad zur ZIP-Datei')
    args = ap.parse_args()

    if not os.path.isfile(args.file):
        print(f'Datei nicht gefunden: {args.file}')
        return 1

    size = os.path.getsize(args.file)
    print('=' * 70)
    print('Paketprüfung')
    print('=' * 70)
    print(f'  {"Datei":<30} {os.path.basename(args.file)}')
    print(f'  {"Größe":<30} {size} Bytes ({size / 1048576:.1f} MB)')

    print('  Prüfsumme wird berechnet ...')
    digest = sha256_of(args.file)
    print(f'  {"SHA-256":<30} {digest}')

    with zipfile.ZipFile(args.file) as zf:
        entries = len(zf.namelist())
        meta = read_metadata(zf)
        guards = read_guards(zf)
        has_payload = 'payload.bin' in zf.namelist()
        has_block = any(n.endswith('.new.dat.br') for n in zf.namelist())

    print(f'  {"Einträge im Archiv":<30} {entries}')
    print(f'  {"Format":<30} {"payload.bin" if has_payload else ("block-based" if has_block else "unbekannt")}')

    print('\n  Metadaten:')
    for key in ('post-build', 'post-build-incremental', 'post-software-version-id',
                'post-security-patch-level', 'post-timestamp', 'pre-device', 'ota-type'):
        print(f'    {key:<30} {meta.get(key, "—")}')

    print('\n  Gerätevorgaben:')
    print(f'    {"ro.product.device":<30} {guards["device"] or "—"}')
    products = guards['products'] or []
    print(f'    {"ro.product.name":<30} {", ".join(products) if products else "—"}')
    brands = guards['brands'] or []
    print(f'    {"ro.product.brand":<30} {", ".join(brands) if brands else "—"}')

    return 0


if __name__ == '__main__':
    sys.exit(main())

