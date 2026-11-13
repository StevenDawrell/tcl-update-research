#!/usr/bin/env python3
"""
identity_db.py -- Lesen/Schreiben der Geräte-Identitäts-DB über einen
exportierten, NICHT berechtigungsgeschützten ContentProvider.

Befund (2026-11-11, Reverse-Engineering von ttvs.apk + live am Gerät):
  com.tcl.ttvs.deviceauthen.core.StartandroidService.MyContentProvider
    android:exported="true"    (kein android:permission!)
    Authority: com.tcl.xian.StartandroidService.MyContentProvider
    SQLite-DB: ttvs_DeviceAuthen_MyUsers.db, Tabelle "devicetoken"
    insert()/update() implementiert, Tabellenname = letztes URI-Segment

  => adb shell kann die Zeile beschreiben. GETTER (ohne Berechtigung):
       adb shell content query --uri content://com.tcl.xian.StartandroidService.MyContentProvider

  Spalten: huanid, didtoken, license_type, activekey, boottimes, loginflag,
           deviceid, dum, activeflag, license_data, devicemodel, token

WICHTIG: Diese Werte identifizieren das Gerät gegenüber dem TCL-Update-Dienst.
         Vor jeder Änderung "show" ausführen und notieren, danach "restore".

Gespeichert am Gerät (Originalwerte 2026-11-11):
  huanid=100000000
  didtoken=REDACTED_DIDTOKEN
  license_type=000
  activekey=REDACTED_ACTIVEKEY
  boottimes=1259          (laeuft mit, nicht zuruecksetzen)
  loginflag=1
  deviceid=REDACTED_DEVICEID
  dum=REDACTED_DNUM
  activeflag=1
  license_data=000
  devicemodel=TCL-EU-RTD75P-S1
  token=REDACTED_TOKEN

Beobachtete Wirkung (getestet): devicemodel zu "TCL-AS-..." geaendert und
zurueckgesetzt. Der Update-Request nutzt clientType aus
tclx.os.TDeviceInfo (Property ro.product.clientType), NICHT aus dieser DB --
die DB ist nur Fallback bei leerer Property. Damit ist der Schreibzugriff
real, aber ohne direkte Wirkung auf die Update-Auswahl.

Aufruf:
    python scripts/identity_db.py show
    python scripts/identity_db.py set devicemodel TCL-AS-RTD75P-S1
    python scripts/identity_db.py restore
"""
import subprocess
import sys

ADB = r'C:\Users\jacqu\Downloads\TCL\platform-tools\adb.exe'
URI = 'content://com.tcl.xian.StartandroidService.MyContentProvider'
TABLE_URI = URI + '/devicetoken'

ORIGINAL = {
    'huanid': '100000000',
    'didtoken': 'REDACTED_DIDTOKEN',
    'license_type': '000',
    'activekey': 'REDACTED_ACTIVEKEY',
    'loginflag': '1',
    'deviceid': 'REDACTED_DEVICEID',
    'dum': 'REDACTED_DNUM',
    'activeflag': '1',
    'license_data': '000',
    'devicemodel': 'TCL-EU-RTD75P-S1',
    'token': 'REDACTED_TOKEN',
}


def sh(args):
    r = subprocess.run([ADB, 'shell'] + args, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    return ((r.stdout or '') + (r.stderr or '')).strip()


def show():
    out = sh(['content', 'query', '--uri', TABLE_URI])
    print('== devicetoken ==')
    print(out)
    return out


def set_value(key, value):
    if key not in ORIGINAL:
        print(f'WARN: {key} ist keine bekannte Spalte ({", ".join(ORIGINAL)})')
    print(f'setze {key} = {value}')
    print(sh(['content', 'update', '--uri', TABLE_URI,
              '--bind', f'{key}:s:{value}']))
    show()


def restore():
    for k, v in ORIGINAL.items():
        sh(['content', 'update', '--uri', TABLE_URI, '--bind', f'{k}:s:{v}'])
    print('restore ausgefuehrt (boottimes bleibt unberuehrt):')
    show()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd = sys.argv[1]
    if cmd == 'show':
        show()
    elif cmd == 'set' and len(sys.argv) == 4:
        set_value(sys.argv[2], sys.argv[3])
    elif cmd == 'restore':
        restore()
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
