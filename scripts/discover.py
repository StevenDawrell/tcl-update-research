#!/usr/bin/env python3
"""
Geräte im lokalen Netzwerk finden (SSDP).

Aufruf:
    python scripts/discover.py
    python scripts/discover.py --timeout 8
"""
from __future__ import annotations

import argparse
import socket
import time

SEARCH = (
    'M-SEARCH * HTTP/1.1\r\n'
    'HOST:239.255.255.250:1900\r\n'
    'MAN:"ssdp:discover"\r\n'
    'MX:3\r\n'
    'ST:upnp:rootdevice\r\n\r\n'
)

TV_HINTS = ('chromecast', 'android', 'dlna')


def score(server: str) -> int:
    s = server.lower()
    points = 0
    if 'chromecast' in s:
        points += 10
    if 'android' in s:
        points += 4
    if 'linux' in s:
        points += 2
    if 'dlna' in s:
        points += 1
    return points


def field(raw: str, key: str) -> str:
    for line in raw.splitlines():
        if line.upper().startswith(key.upper() + ':'):
            return line.split(':', 1)[1].strip()
    return ''


def main() -> int:
    ap = argparse.ArgumentParser(description='Geräte im Netzwerk finden')
    ap.add_argument('--timeout', type=float, default=5.0, help='Suchdauer in Sekunden')
    args = ap.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(1.0)

    try:
        sock.sendto(SEARCH.encode(), ('239.255.255.250', 1900))
    except OSError as err:
        print(f'Suche nicht möglich: {err}')
        return 1

    seen: dict[str, str] = {}
    end = time.time() + args.timeout
    while time.time() < end:
        try:
            data, addr = sock.recvfrom(4096)
        except socket.timeout:
            continue
        server = field(data.decode('utf-8', 'replace'), 'SERVER')
        ip = addr[0]
        if ip not in seen or len(server) > len(seen[ip]):
            seen[ip] = server
    sock.close()

    if not seen:
        print('Keine Geräte gefunden.')
        print('Hinweis: Rechner und Fernseher müssen im selben Netzwerk sein.')
        return 0

    print(f'{len(seen)} Gerät(e):\n')
    ranked = sorted(seen.items(), key=lambda kv: score(kv[1]), reverse=True)
    for ip, server in ranked:
        mark = 'Fernseher' if score(server) >= 10 else '—'
        print(f'  {ip:<16} {mark:<10} {server}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

