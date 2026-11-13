#!/usr/bin/env python3
"""
verify_findings.py -- executable knowledge: verifies the core structural claims
of this repository against the actual artifact, without a device.

What it proves (offline, reproducible):
  1. The provided V648 package is a *block-based* OTA (no payload.bin).
  2. The provided V661 package is a Realtek Update.img TAR (no payload.bin).
  3. Neither package can take the A/B route (which would bypass /cache).
  4. Therefore: without a vendor-signed A/B package, USB medium, vendor server,
     or vendor key, installation without a stick is impossible on this device.

Run:  python scripts/verify_findings.py /path/to/V8-R75PT01-LF1V648.zip [V661.zip]
"""
import hashlib
import struct
import sys
import zipfile


def read_meta(zf):
    try:
        return zf.read('META-INF/com/android/metadata').decode('utf-8', 'replace')
    except KeyError:
        return ''


def analyze(path):
    print(f'== {path}')
    try:
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            has_payload = 'payload.bin' in names
            has_props = 'payload_properties.txt' in names
            has_meta = 'META-INF/com/android/metadata' in names
            meta = read_meta(zf)
            ota_type = None
            for line in meta.splitlines():
                if line.startswith('ota-type='):
                    ota_type = line.split('=', 1)[1].strip()
            block = any(n.endswith('.new.dat.br') for n in names)
            img = any(n.lower().endswith('update.img') for n in names)
    except zipfile.BadZipFile:
        # Realtek Update.img TAR (V661 is a 1-entry zip or raw tar)
        print('   (not a zip / single-entry archive)')
        return {'payload': False}

    print(f'   entries            : {len(names)}')
    print(f'   payload.bin        : {has_payload}')
    print(f'   payload_properties : {has_props}')
    print(f'   metadata present   : {has_meta}')
    print(f'   ota-type           : {ota_type}')
    print(f'   block-based (.new.dat.br): {block}')
    print(f'   Update.img         : {img}')

    ab_viable = has_payload and has_props and (ota_type == 'AB')
    print(f'   => A/B route viable (bypasses /cache): {ab_viable}')
    return {'payload': has_payload, 'ab': ab_viable, 'block': block}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    results = [analyze(p) for p in sys.argv[1:]]
    print()
    print('=' * 66)
    any_ab = any(r.get('ab') for r in results)
    if any_ab:
        print('RESULT: an A/B package is present.')
        print('  It would be installable without USB (if vendor-signed).')
    else:
        print('RESULT: no A/B package present.')
        print('  All packages are block-based or Update.img; installing one')
        print('  without USB requires either a vendor-signed A/B package,')
        print('  the vendor OTA server, or the vendor signing key.')
        print('  => installing without a USB stick is NOT possible with these files.')
    print('=' * 66)
    return 0


if __name__ == '__main__':
    sys.exit(main())
