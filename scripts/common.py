#!/usr/bin/env python3
"""
Gemeinsame Helfer fuer alle Skripte dieses Projekts.
Nur Standardbibliothek, kein externes Paket.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys


def find_adb() -> str | None:
    """Sucht adb im Projekt, im Nachbarordner, in bekannten Ordnern und im PATH."""
    name = 'adb.exe' if os.name == 'nt' else 'adb'
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for folder in (root, os.path.dirname(root)):
        candidate = os.path.join(folder, 'platform-tools', name)
        if os.path.isfile(candidate):
            return candidate

    found = shutil.which('adb')
    if found:
        return found

    for base in ('/usr/local/bin', '/usr/bin', os.path.expanduser('~/platform-tools')):
        p = os.path.join(base, name)
        if os.path.isfile(p):
            return p
    return None


def adb(args: list[str], serial: str | None = None, timeout: int = 120) -> str:
    """Fuehrt adb aus und liefert stdout als Text."""
    exe = find_adb()
    if not exe:
        raise RuntimeError('adb nicht gefunden. Android Platform Tools installieren '
                           'oder Verzeichnis in den PATH aufnehmen.')

    cmd = [exe]
    if serial:
        cmd += ['-s', serial]
    cmd += args

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           encoding='utf-8', errors='replace')
    except subprocess.TimeoutExpired:
        raise RuntimeError(f'adb Zeitueberschreitung: {" ".join(args)}') from None

    out = (r.stdout or '').strip()
    err = (r.stderr or '').strip()
    if r.returncode != 0 and err:
        raise RuntimeError(err)
    return out


def first_device() -> str:
    """Liefert die Seriennummer des ersten verbundenen Geraets."""
    out = adb(['devices'])
    for line in out.splitlines():
        if '\tdevice' in line:
            return line.split('\t')[0].strip()
    raise RuntimeError('Kein Geraet verbunden. USB-Kabel pruefen und Dialog am '
                       'Fernseher bestaetigen.')


def getprop(serial: str, key: str) -> str:
    return adb(['shell', 'getprop', key], serial=serial)


def header(text: str) -> None:
    print('\n' + '=' * 70)
    print(text)
    print('=' * 70)


def row(key: str, value: str) -> None:
    print(f'  {key:<34} {value}')


def die(message: str, code: int = 1) -> int:
    print(f'  Fehler: {message}')
    return code


if __name__ == '__main__':
    print('Dieses Modul wird von den Skripten importiert.')
    sys.exit(0)

