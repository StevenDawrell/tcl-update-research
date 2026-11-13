#!/usr/bin/env python3
"""
trace_full_install.py -- Vollstaendiger Mitschnitt des Installationsablaufs.

Achtet auf die aus dem Client rekonstruierten Schluesselstellen:
    InstallTools   : verifyOrProcessPackage, isNeedProcessPackage
    BaseNetSystemUpdater : startVerify, isAbUpdateZip, verifyOk
    RecoverySystem : verifyPackage / processPackage / installPackage
    update_engine  : applyPayload
    Progress       : Verify package with progress
    Zustand        : getState state is

Nutzung:
    python trace_full_install.py 420
Am TV: Softwareupdate > Lokales Update
"""
import os
import re
import subprocess
import sys
import time

ADB = os.environ.get('ADB_PATH') or 'adb'
SERIAL = os.environ.get('ADB_SERIAL') or ''
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')

WATCH = [
    ('NEEDPROCESS', re.compile(r'isNeedProcessPackage|verifyOrProcessPackage', re.I)),
    ('INSTALLTOOLS', re.compile(r'InstallTools', re.I)),
    ('VERIFY', re.compile(r'Verify (local )?package with progress = (\d+)%', re.I)),
    ('ISAB', re.compile(r'isCanAbUpdate|isAbUpdateZip', re.I)),
    ('PROCESS', re.compile(r'processPackage|installPackage|smartcardautoupdate', re.I)),
    ('APPLYPAYLOAD', re.compile(r'applyPayload', re.I)),
    ('DECRYPT', re.compile(r'decrypt finished|VerifySuccess', re.I)),
    ('STATE', re.compile(r'getState state is (\w+)')),
    ('ERROR', re.compile(r'(EX=|Exception|fail|abort|interrupt|error)', re.I)),
]


def adb_shell(cmd: str, timeout: int = 20) -> str:
    args = [ADB] + (['-s', SERIAL] if SERIAL else []) + ['shell', cmd]
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                           encoding='utf-8', errors='replace')
        return ((r.stdout or '') + (r.stderr or '')).strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ''


def main() -> int:
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 420
    os.makedirs(OUT, exist_ok=True)
    stamp = time.strftime('%Y%m%d_%H%M%S')
    report = os.path.join(OUT, f'install_{stamp}.txt')

    print('=' * 74)
    print('Umgebung')
    print('=' * 74)
    print('  ro.crypto.state    :', adb_shell('getprop ro.crypto.state'))
    print('  External Storage   :', adb_shell('echo $EXTERNAL_STORAGE'))
    print('  ZIP kanonisch      :', adb_shell('readlink -f /sdcard/V8-R75PT01-LF1V648.zip'))
    print('  ZIP Groesse        :', adb_shell('stat -c %s /sdcard/V8-R75PT01-LF1V648.zip'))

    adb_shell('logcat -c')
    print()
    print('=' * 74)
    print(f'MITSCHNITT {duration}s')
    print('>>> TV: Einstellungen > System > Info > Softwareupdate > Lokales Update <<<')
    print('=' * 74, flush=True)

    cmd = [ADB] + (['-s', SERIAL] if SERIAL else []) + ['logcat', '-v', 'time']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding='utf-8', errors='replace', bufsize=1)

    start = time.time()
    events = []
    last_pct = -1
    disconnected = False

    while time.time() - start < duration:
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None:
                disconnected = True
                print('\n  !! Verbindung getrennt (Neustart?) !!', flush=True)
                events.append((time.time() - start, 'DISCONNECT', ''))
                break
            continue

        matched = False
        for key, pattern in WATCH:
            m = pattern.search(line)
            if not m:
                continue

            if key == 'VERIFY':
                pct = int(m.group(2))
                if pct == last_pct:
                    matched = True
                    break
                last_pct = pct
                text = f'{pct}%'
            else:
                text = line.strip()
                for tag in ('versionUpdate:', 'InstallTools:', 'BaseNetSystemUpdater:',
                            'update_engine:', 'RecoverySystem:'):
                    if tag in text:
                        text = text.split(tag, 1)[-1].strip()
                        break

            elapsed = time.time() - start
            safe = text.encode('ascii', 'replace').decode('ascii')
            print(f'  [{elapsed:7.1f}s] {key:12s} {safe[:120]}', flush=True)
            events.append((elapsed, key, safe[:300]))
            matched = True
            break

    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        proc.kill()

    print()
    print('=' * 74)
    print('AUSWERTUNG')
    print('=' * 74)
    counts: dict[str, int] = {}
    for _, key, _ in events:
        counts[key] = counts.get(key, 0) + 1
    for key, n in sorted(counts.items()):
        print(f'  {key:14s} {n:4d}')

    text_all = ' '.join(v for _, _, v in events)
    checks = {
        'needProcess erkannt': 'isNeedProcessPackage' in text_all,
        'processPackage': 'processPackage' in text_all,
        'installPackage': 'installPackage' in text_all,
        'applyPayload': 'applyPayload' in text_all,
        'verify erfolgreich': ('decrypt finished' in text_all) or ('VerifySuccess' in text_all),
    }
    print('\n  Schritte:')
    for name, ok in checks.items():
        print(f'    {name:22s} {"JA" if ok else "nein"}')

    with open(report, 'w', encoding='utf-8') as f:
        f.write(f'Mitschnitt {stamp}, {duration}s\n')
        f.write(f'crypto={adb_shell("getprop ro.crypto.state")}\n')
        f.write(f'zip={adb_shell("stat -c %s /sdcard/V8-R75PT01-LF1V648.zip")}\n')
        f.write(f'getrennt={disconnected}\n\n')
        for elapsed, key, value in events:
            f.write(f'{elapsed:8.1f}s {key:14s} {value}\n')
    print(f'\n  Bericht: {report}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

