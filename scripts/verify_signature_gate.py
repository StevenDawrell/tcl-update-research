#!/usr/bin/env python3
"""
verify_signature_gate.py -- explains and checks the *build vs. sign* distinction.

There are TWO independent signatures on an Android/Android-TV OTA package.
Both must pass before anything is installed:

  (1) PAYLOAD signature  -- inside payload.bin (CrAU: metadata_signature block),
                            verified by update_engine against the keys in
                            /system/etc/security/otacerts.zip
  (2) WHOLE-FILE signature -- signapk over the whole .zip, verified by
                            RecoverySystem.verifyPackage() BEFORE (1) even runs

Community packers (delta_generator, Payload_Repack_Tool, payload_packer/rust)
can ASSEMBLE a payload.bin from partition images -- but every one of them needs
the VENDOR'S PRIVATE OTA KEY to sign it. Without that key you can produce a
structurally valid payload.bin that the device will reject at gate (2) or (1).

This script makes that concrete:
  * parse a payload.bin (or an OTA zip containing one) and report whether the
    metadata_signature block is present and non-empty;
  * report which signing material is required to make it acceptable.

Run:
  python scripts/verify_signature_gate.py V8-...-LF1V648.zip
  python scripts/verify_signature_gate.py payload.bin
"""
import hashlib
import struct
import sys
import zipfile

CR_AU = b'CrAU'


def parse_payload(data, label):
    print(f'== {label}')
    if data[:4] != CR_AU:
        print('   not a CrAU payload (magic mismatch)')
        return {'is_payload': False}
    version = struct.unpack('>Q', data[4:12])[0]
    manifest_size = struct.unpack('>Q', data[12:20])[0]
    metadata_sig_size = struct.unpack('>I', data[20:24])[0]
    print(f'   payload format version : {version}')
    print(f'   manifest size          : {manifest_size} bytes')
    print(f'   metadata signature size: {metadata_sig_size} bytes')

    has_payload_sig = metadata_sig_size > 0
    print(f'   payload signature block present: {has_payload_sig}')
    if has_payload_sig:
        sig_region = data[24 + manifest_size: 24 + manifest_size + metadata_sig_size]
        print(f'   signature sha256 (first 8 bytes): {hashlib.sha256(sig_region).hexdigest()[:16]}…')
    else:
        print('   -> unsigned payload: update_engine will reject it')
    return {
        'is_payload': True,
        'has_payload_sig': has_payload_sig,
        'metadata_sig_size': metadata_sig_size,
    }


def inspect(path):
    print(f'### {path}')
    try:
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            has_otacert = any(n.lower().endswith('otacert') for n in names)
            meta_sig = [n for n in names if 'META-INF' in n and (n.endswith('.SF') or n.endswith('.RSA') or n.endswith('.EC') or n.endswith('.DSA'))]
            print(f'   zip entries               : {len(names)}')
            print(f'   META-INF/com/android/otacert: {has_otacert}')
            print(f'   signapk signature files   : {meta_sig if meta_sig else "NONE"}')
            if 'payload.bin' in names:
                return parse_payload(zf.read('payload.bin'), 'payload.bin inside zip')
            print('   no payload.bin in this package (block-based or Update.img)')
            return {'is_payload': False, 'has_whole_file_sig': bool(meta_sig)}
    except zipfile.BadZipFile:
        with open(path, 'rb') as f:
            head = f.read(24)
        return parse_payload(head + open(path, 'rb').read()[24:24 + 4096], 'raw file (partial)')


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    print('=' * 68)
    print('Bauen != Signieren: ein payload.bin zu ERZEUGEN ist machbar,')
    print('es beim GERAET ANGENOMMEN zu bekommen braucht den Hersteller-Key.')
    print('=' * 68)
    for p in sys.argv[1:]:
        inspect(p)
        print()
    print('-' * 68)
    print('Um ein installierbares OTA zu erhalten, muessen BEIDE Tore passiert')
    print('werden:')
    print('  (1) payload.bin mit dem privaten OTA-Key signieren (delta_generator')
    print('      --private_key, sign_target_files_apks / Payload_Repack_Tool,')
    print('      payload_packer --key)  -> Key liegt beim Hersteller')
    print('  (2) die gesamte ZIP mit signapk + dem Release-Key signieren')
    print('      (RecoverySystem.verifyPackage)                  -> ebenfalls Hersteller')
    print('Ohne diese beiden Schluessel produziert jedes Repack-Tool ein Paket,')
    print('das das Geraet verwirft - unabhaengig davon, wie korrekt es gebaut ist.')
    print('-' * 68)
    return 0


if __name__ == '__main__':
    sys.exit(main())
