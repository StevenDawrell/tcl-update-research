#!/usr/bin/env python3
"""
proxy_capture.py -- Kleiner HTTP/HTTPS-Proxy zum Mitschnitt der OTA-Anfragen.

Zweck: Feststellen, welche Hosts und Pfade der TCL-Client beim Update aufruft.
Der Fernseher wird per `settings put global http_proxy <PC-IP>:<PORT>` auf
diesen Proxy gelenkt.

Aufruf:
    python scripts/proxy_capture.py --port 8080 --duration 120

Rueckgaengig machen:
    adb shell settings put global http_proxy :0
"""
from __future__ import annotations

import argparse
import socket
import socketserver
import sys
import threading
import time
from datetime import datetime

PORT = 8080
DURATION = 120
TUNNEL = False


def pipe(src: socket.socket, dst: socket.socket) -> None:
    """Kopiert Bytes von src nach dst, bis eine Seite schliesst."""
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except OSError:
        pass
    finally:
        try:
            dst.shutdown(socket.SHUT_WR)
        except OSError:
            pass


class Proxy(socketserver.StreamRequestHandler):
    timeout = 60

    def handle(self) -> None:
        try:
            line = self.rfile.readline(65536).decode('latin-1').strip()
            if not line:
                return

            headers: list[str] = []
            while True:
                h = self.rfile.readline(65536).decode('latin-1').strip()
                if not h:
                    break
                headers.append(h)

            stamp = datetime.now().strftime('%H:%M:%S')
            print(f'[{stamp}] {self.client_address[0]}  {line}', flush=True)

            for h in headers:
                low = h.lower()
                if low.startswith(('host:', 'user-agent:', 'content-type:',
                                   'content-length:', 'accept:')):
                    print(f'          {h}', flush=True)

            method, target, _ = (line.split(' ', 2) + ['', ''])[:3]

            if method.upper() == 'CONNECT':
                host, _, port = target.partition(':')
                port = int(port) if port.isdigit() else 443
                if TUNNEL and self.open_tunnel(host, port):
                    return
                print(f'          -> CONNECT {host}:{port} (Tunnel abgelehnt)', flush=True)
                self.send_response_text('HTTP/1.1 502 Tunnel nicht eingerichtet\r\n\r\n')
                return

            host = next((h.split(':', 1)[1].strip() for h in headers
                         if h.lower().startswith('host:')), '')
            print(f'          -> HTTP  http://{host}{target}', flush=True)
            if TUNNEL and self.forward_http(line, headers, host):
                return
            self.send_response_text('HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n')

        except Exception as err:
            print(f'          Fehler: {err}', flush=True)

    def open_tunnel(self, host: str, port: int) -> bool:
        """HTTPS-Tunnel aufbauen und Bytes in beide Richtungen durchreichen."""
        try:
            upstream = socket.create_connection((host, port), timeout=10)
        except OSError as err:
            print(f'          !! Tunnel zu {host}:{port} fehlgeschlagen: {err}', flush=True)
            return False
        print(f'          -> Tunnel offen zu {host}:{port}', flush=True)
        self.send_response_text('HTTP/1.1 200 Connection Established\r\n\r\n')
        worker = threading.Thread(target=pipe, args=(upstream, self.connection), daemon=True)
        worker.start()
        pipe(self.connection, upstream)
        worker.join(timeout=5)
        try:
            upstream.close()
        except OSError:
            pass
        return True

    def forward_http(self, line: str, headers: list[str], host: str) -> bool:
        """Einfache HTTP-Anfrage weiterleiten und Antwort durchreichen."""
        port = 80
        if host.count(':') == 1:
            h, _, p = host.partition(':')
            if p.isdigit():
                host, port = h, int(p)
        try:
            upstream = socket.create_connection((host, port), timeout=10)
        except OSError as err:
            print(f'          !! HTTP-Weiterleitung fehlgeschlagen: {err}', flush=True)
            return False
        raw = (line + '\r\n' + '\r\n'.join(headers) + '\r\n\r\n').encode('latin-1')
        try:
            upstream.sendall(raw)
        except OSError:
            upstream.close()
            return False
        worker = threading.Thread(target=pipe, args=(upstream, self.connection), daemon=True)
        worker.start()
        pipe(self.connection, upstream)
        worker.join(timeout=5)
        try:
            upstream.close()
        except OSError:
            pass
        return True

    def send_response_text(self, text: str) -> None:
        try:
            self.wfile.write(text.encode('latin-1'))
            self.wfile.flush()
        except Exception:
            pass


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'
    finally:
        s.close()


def main() -> int:
    ap = argparse.ArgumentParser(description='OTA-Anfragen mitschneiden')
    ap.add_argument('--port', type=int, default=PORT)
    ap.add_argument('--duration', type=int, default=DURATION)
    ap.add_argument('--tunnel', action='store_true',
                    help='CONNECT-Tunnel wirklich weiterleiten (Fernseher behaelt Internet)')
    args = ap.parse_args()

    global TUNNEL
    TUNNEL = args.tunnel

    ip = local_ip()
    server = Server(('0.0.0.0', args.port), Proxy)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    print('=' * 70)
    print('Mitschnitt laeuft')
    print('=' * 70)
    print(f'  Adresse : {ip}:{args.port}')
    print()
    print('  Am Fernseher setzen:')
    print(f'    adb shell settings put global http_proxy {ip}:{args.port}')
    print()
    print('  Danach am Fernseher: Softwareupdate starten')
    print(f'  Dauer: {args.duration} s')
    print('=' * 70)
    print()

    try:
        time.sleep(args.duration)
    except KeyboardInterrupt:
        print('\n(abgebrochen)')
    finally:
        server.shutdown()
        print()
        print('Mitschnitt beendet.')
        print('Proxy zuruecksetzen:')
        print('  adb shell settings put global http_proxy :0')
    return 0


if __name__ == '__main__':
    sys.exit(main())

