#!/usr/bin/env python3
"""
probe_upgrade_api.py -- Fragt die TCL-Upgrade-Schnittstelle direkt ab.

Zweck: Nachvollziehen, welche Antwort der Upgrade-Server fuer dieses Geraet
liefert, ohne den Fernseher neu zu starten. Der Aufruf bildet die Signatur aus
`SignInterceptor` der App `com.tcl.ttvs` nach (XTCL-HMAC-SHA256).

Der Parameter `md5id` entspricht der vierstelligen Service-PIN. Bleibt er leer,
verhaelt sich die Abfrage wie ein normaler Update-Check.

Aufruf:
    python scripts/probe_upgrade_api.py --dnum REDACTED_DNUM --model G10_4K_GB \
        --version V8-R75PT01-LF1V548 --pin 0648

Hinweis: Es handelt sich um eine reine Leseabfrage an den oeffentlichen
Upgrade-Dienst. Bitte nur mit eigenen Geraetedaten verwenden.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

# Aus com.tcl.ff.component.core.http.core.HttpCore: setAppInfo(...)
APP_ID = 'REDACTED_APPID'
APP_KEY = 'REDACTED_APPKEY'

# Aus j.k.p.x.b.a: EU-Endpunkt fuer getUpgradeByVerID
BASE = 'https://eu-filter-upgrade.huan.tv/service/platform/getUpgradeByVerID'

# SHA-256 ueber einen leeren Body (Konstante aus SignInterceptor)
EMPTY_BODY_SHA256 = 'E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855'


def _b64_sha256(data: bytes) -> str:
    return base64.b64encode(hashlib.sha256(data).digest()).decode()


def _sorted_header_string(headers: dict[str, str], with_values: bool) -> str:
    parts = []
    for key in sorted(headers):
        parts.append(f'{key}:{headers[key]};' if with_values else f'{key};')
    return ''.join(parts)


def build_signature(method: str, path: str, query: str,
                    headers: dict[str, str], app_id: str, app_key: str) -> dict[str, str]:
    """Bildet die Kopfzeilen aus SignInterceptor nach."""
    nonce = uuid.uuid4().hex
    sign_headers: dict[str, str] = {'xtcl-nonce': nonce}
    for name, value in headers.items():
        low = name.lower()
        if low in ('host', 'content-type') or low.startswith('xtcl-'):
            sign_headers[low] = value.lower()

    with_values = _sorted_header_string(sign_headers, True)
    names_only = _sorted_header_string(sign_headers, False)
    timestamp = str(int(time.time()))

    body_hash = base64.b64encode(bytes.fromhex(EMPTY_BODY_SHA256)).decode()
    to_sign = f'{method}\n{path}\n{query}\n{with_values}\n{body_hash}'
    digest = _b64_sha256(to_sign.encode())

    string_to_sign = f'TCL1-HMAC-SHA256\n{timestamp}\n{digest}'
    signature = base64.b64encode(
        hmac.new(app_key.encode(), string_to_sign.encode(), hashlib.sha256).digest()
    ).decode()

    return {
        'XTCL-Authorization': (f'TCL1-HMAC-SHA256 Credential={app_id},'
                               f'SignedHeaders={names_only},Signature={signature}'),
        'XTCL-Timestamp': timestamp,
        'XTCL-nonce': nonce,
    }


def query_for(args: argparse.Namespace) -> dict[str, str]:
    return {
        'md5id': args.pin,
        'devmodel': args.model,
        'dnum': args.dnum,
        'projectid': str(args.projectid),
        'packagever': 'com.tcl.ttvs',
        'systemver': args.android,
        'appver': args.version,
        'https': 'true',
        'language': args.language,
        'area': args.area,
        'appkey': ''.join(args.version.split('-')[:-1]),
        'upmptype': '4',
        'request_id': args.request_id,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description='TCL-Upgrade-API abfragen')
    ap.add_argument('--dnum', required=True, help='Geraetenummer, z. B. REDACTED_DNUM')
    ap.add_argument('--model', default='G10_4K_GB', help='clientType / devmodel')
    ap.add_argument('--version', default='V8-R75PT01-LF1V548', help='appver (Systemversion)')
    ap.add_argument('--android', default='12', help='systemver (Android-Version)')
    ap.add_argument('--projectid', type=int, default=1)
    ap.add_argument('--pin', default='', help='vierstellige Service-PIN (md5id)')
    ap.add_argument('--language', default='en-US')
    ap.add_argument('--area', default='EU')
    ap.add_argument('--request-id', default=uuid.uuid4().hex,
                    help='RequestId der Abfrage (Default: zufaellig)')
    ap.add_argument('--raw', action='store_true', help='Rohantwort ungekuerzt ausgeben')
    args = ap.parse_args()

    params = query_for(args)
    query = urllib.parse.urlencode(params)
    parsed = urllib.parse.urlsplit(BASE)
    extra = {
        'host': parsed.netloc,
        'xtcl-app': 'com.tcl.ttvs',
        'xtcl-traceid': args.request_id,
    }
    headers = build_signature('GET', parsed.path, query, extra, APP_ID, APP_KEY)
    headers['XTCL-App'] = 'com.tcl.ttvs'

    url = f'{BASE}?{query}'
    print(f'Abfrage : {parsed.netloc}{parsed.path}')
    print(f'md5id   : {args.pin or "(leer)"}')
    print(f'dnum    : {args.dnum}   Modell: {args.model}   Version: {args.version}')
    print('-' * 70)

    req = urllib.request.Request(url, headers=headers, method='GET')
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
            body = resp.read().decode('utf-8', 'replace')
            print(f'HTTP {resp.status}')
            if args.raw:
                print(body)
            else:
                try:
                    data = json.loads(body)
                    print(json.dumps(data, indent=2, ensure_ascii=False)[:1500])
                except json.JSONDecodeError:
                    print(body[:1500])
            return 0
    except urllib.error.HTTPError as err:
        body = err.read().decode('utf-8', 'replace')
        print(f'HTTP {err.code} {err.reason}')
        print(body[:800])
        return 1
    except Exception as err:  # noqa: BLE001
        print(f'Fehler: {err}')
        return 1


if __name__ == '__main__':
    sys.exit(main())

