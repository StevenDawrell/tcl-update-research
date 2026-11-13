#!/usr/bin/env python3
"""
build_ab_probe.py -- Erzeugt eine A/B-OTA-PROBE-ZIP mit selbst generiertem payload.bin.

Zweck: den AB-Pfad des TCL-Clients gezielt ansprechen und sehen, wo update_engine
stoppt. Der Pfad ist (aus c.java rekonstruiert):

    isABUpdateZip(path, "META-INF/com/android/metadata")   liest "ota-type"
      -> true  =>  UpdateParser.parse(zip)  =>  ABUpdateManager.updateEngineApplyPayload
                   UpdateEngine.applyPayload("file://<zip>", offset, size, props)
      -> false =>  RecoverySystem.processPackage  (BLOCK-Pfad, /cache-Grenze)

WICHTIG: Der Payload ist NICHT signiert. update_engine prueft die Payload-Signatur
gegen /system/etc/security/otacerts.zip. Ohne den TCL-Privat-Schluessel ist ein
installierbares payload.bin NICHT erzeugbar. Diese Probe zeigt deshalb nur:
   a) nimmt der Client den AB-Zweig an?   (isAbUpdateZip == true, Log)
   b) ruft er applyPayload auf?           (Log: "updateEngineApplyPayload url:")
   c) was meldet update_engine?           (Fehlercode = Signatur vs. Struktur)

Wird (a)+(b) bestaetigt, ist bewiesen: ein korrekt signiertes AB-Paket wuerde
auf diesem Geraet OHNE USB und OHNE /cache installierbar sein. Dann nur noch
nach einem echten Hersteller-AB-Paket suchen.

Aufruf:
    python scripts/build_ab_probe.py            # erzeugt V8-R75PT01-LF1V690.zip
"""
import hashlib
import io
import os
import struct
import sys
import zipfile

BLOCK = 4096
PARTITION = 'boot'
ZIP_NAME = 'V8-R75PT01-LF1V690.zip'          # 690 > 548, 3 Segmente, kein S/G


# ---- minimaler Protobuf-Encoder (nur varint + length-delimited) -------------

def _varint(n):
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out)


def _key(field, wire):
    return _varint((field << 3) | wire)


def _len_delim(field, payload):
    return _key(field, 2) + _varint(len(payload)) + payload


def _uint64(field, value):
    return _key(field, 0) + _varint(value)


def _string(field, value):
    return _len_delim(field, value.encode())


# ---- update_metadata.Manifest ----------------------------------------------

def make_extent(start_block, num_blocks):
    # Extent { start_block = 1; num_blocks = 2; }
    return _uint64(1, start_block) + _uint64(2, num_blocks)


def make_replace_op(dst_start_block, dst_blocks, data):
    """InstallOperation { type=REPLACE(0); dst_extents=4; dst_length=5; data_sha256_hash=6 }"""
    op = b''
    op += _uint64(1, 0)                                   # type = REPLACE
    op += _len_delim(4, make_extent(dst_start_block, dst_blocks))
    op += _uint64(5, len(data))
    op += _len_delim(6, hashlib.sha256(data).digest())
    return op


def make_manifest(op_bytes):
    """Manifest { block_size=3; partitions_update=13 }"""
    pu = _string(1, PARTITION) + _len_delim(2, op_bytes)   # PartitionsUpdate
    m = b''
    m += _uint64(3, BLOCK)                                 # block_size
    m += _len_delim(13, pu)                                # partitions_update
    return m


def make_payload(manifest, data):
    """CrAU-Header: magic(4) version(u64be) manifest_size(u64be) meta_sig_size(u32be)"""
    hdr = b'CrAU'
    hdr += struct.pack('>Q', 2)          # Version 2
    hdr += struct.pack('>Q', len(manifest))
    hdr += struct.pack('>I', 0)          # metadata_signature_size = 0 (UNGESIGNIERT)
    return hdr + manifest + data


def make_props(payload):
    # Datenbereich = hinter Header+Manifest
    manifest_size = struct.unpack('>Q', payload[12:20])[0]
    body = payload[24 + manifest_size:]
    return '\n'.join([
        'FILE_HASH=' + hashlib.sha256(body).hexdigest(),
        'FILE_SIZE=%d' % len(body),
        'METADATA_HASH=' + hashlib.sha256(payload[:24 + manifest_size]).hexdigest(),
        'METADATA_SIZE=%d' % (24 + manifest_size),
        'SWITCH_SLOT_ON_REBOOT=1',
    ]) + '\n'


def make_metadata():
    # isABUpdateZip liest "ota-type" und splittet an "="
    return '\n'.join([
        'ota-type=AB',
        'ota-type=AB',
        'pre-device=G10',
        'post-build=TCL/G10_4K_US_NF/G10:14/UTT2.250416.001/AS50:user/release-keys',
        'post-timestamp=1791561166',
        'post-security-patch-level=2026-06-05',
    ]) + '\n'


def main():
    data = os.urandom(BLOCK)                    # eine Block-Dummy-Daten für "boot"
    op = make_replace_op(0, 1, data)
    manifest = make_manifest(op)
    payload = make_payload(manifest, data)
    props = make_props(payload)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', ZIP_NAME)
    out = os.path.normpath(out)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_STORED) as zf:
        zf.writestr('payload.bin', payload)
        zf.writestr('payload_properties.txt', props)
        zf.writestr('META-INF/com/android/metadata', make_metadata())
        zf.writestr('META-INF/com/android/metadata.pb', b'')
    with open(out, 'wb') as f:
        f.write(buf.getvalue())

    print('Payload-Kopf :', payload[:4], 'Version 2, Manifest', len(manifest), 'Bytes')
    print('payload.bin  :', len(payload), 'Bytes')
    print('props        :')
    print(props)
    print('ZIP geschrieben:', out, os.path.getsize(out), 'Bytes')
    print()
    print('Nächste Schritte:')
    print('  adb push %s /sdcard/%s' % (out, ZIP_NAME))
    print('  adb shell logcat -c')
    print('  adb shell am start -n com.tcl.ttvs/com.tcl.ttvs.versionUpdateApp.core.UI.CheckoutVersionActivity')
    print('  adb shell logcat -d | findstr /i "isAbUpdateZip updateEngineApplyPayload applyPayload update_engine errorCode"')
    return 0


if __name__ == '__main__':
    sys.exit(main())

