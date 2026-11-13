# Research State — Complete Findings Catalogue

*English synthesis. Full German record: [../RECHERCHE_STAND.md](../RECHERCHE_STAND.md).*

## 1. Device baseline (measured)

| Check | Value |
|---|---|
| `ro.build.type` | `user` |
| `ro.boot.flash.locked` / `verifiedbootstate` | `1` / `green` |
| `ro.crypto.state` / `type` | `encrypted` / `file` (FBE) |
| `/data`, `/data/fota`, `/cache` | `system:system` 0771 / `system:system` 0770 / `system:cache` 0770 (93 MB) |
| `com.tcl.ttvs` | uid 1000 (`sharedUser android.uid.system`), `RECOVERY` + `ACCESS_CACHE_FILESYSTEM` |
| ttvs flags | `SYSTEM … ALLOW_CLEAR_USER_DATA UPDATED_SYSTEM_APP` — **no `ALLOW_BACKUP`** |
| `uncrypt` / `update_engine` / `update_verifier` | present (SELinux hides `ls`) |

Consequences: `adb backup/restore` dead (no `ALLOW_BACKUP`); `/data/media`
unreachable for `shell` (not in `media_rw` group).

## 2. Positive finding: unauthenticated write to device-identity DB

`MyContentProvider` (`com.tcl.ttvs.deviceauthen…`) is `exported="true"` **without
permission** and implements `insert()`/`update()` with table name from the URI
path. Live-verified: `content update` modifies `devicetoken` rows.

**Effect on updates: none.** Request uses `clientType` from `TDeviceInfo`
(read-only property); DB is only a fallback. Kept as forensic tool
(`scripts/identity_db.py`), not an install vector.

## 3. Test-endpoint switches: closed

Endpoint selection driven by `/data/UpdatePlatformType.txt` (`platformType=false`)
or `persist.system.update.test.flag`. All `persist.tcl.update.*` are `persist.*`
⇒ `setprop` denied; file in `/data` (0771 `system:system`) ⇒ not writable.

## 4. Factory app (`com.tcl.factory.view`) — fully mapped

Menu (live `uiautomator`): HDCP / MAC / WideVine / PlayReady / Device ID key
provisioning over USB only — **no system update**.

- `SitaUpgradeService`: plain-HTTP factory-line updater, **three USB gates**
  (P/D-mode, `ProductBatch.txt`/`Equipment.txt` from `<USB>/AutoUpgrade/`,
  download target on `<USB>`), ends in `doSet_FactoryUsbUpgrade(true)` + reboot.
- `setProperty()` writes **factory-HAL** properties (`memory.factory.*`), not
  Android system properties.
- `FactoryOsService`: binary protocol on `127.0.0.1:27856` with
  `FUN_SET_PROPERTY` — **port not listening** outside factory middleware;
  `vendor.tcl.factory@1.0::IFactory` is a vendor HIDL, unreachable from `shell`.

## 5. File-writer search: exhaustive negative result

All decompiled apps searched for file I/O and every path literal:

| Candidate | Verdict |
|---|---|
| `ICopyInterface.copyFile(String,String)` | AIDL only; no implementation; `onBind()` → `null`/`IEvent.Stub` |
| `FileOper.copyFile` (TGuard) | dead code (dev-test `main`) |
| `ConfigurationProvider` (TGuard) | widget tables only |
| `CheckInterfaceInner.hasUpdate()/showUpdateUI()` | UI triggers only |
| `PackageInstallerService` | installs APKs only |
| `RepairGuide` | diagnostics only |
| `/data/vendor/tcl/update` | real path, **not writable** by `shell` |

**No reachable file writer to any system-relevant install location exists.**

## 6. A/B self-build: key evidence

Self-built `payload.bin` (CrAU v2) with `ota-type=AB`, staged to `/sdcard`,
triggered via *System update → USB Update* (live logcat):

```
[c]isAbUpdateZip: true                      ← A/B path accepted
[InstallTools]isNeedProcessPackage false    ← NO /cache copy
RecoverySystem.verifyPackage → GeneralSecurityException
```

The A/B route works and avoids `/cache`; it stops **only** at the whole-file
signature. Valid payload generation requires the vendor OTA key
(`delta_generator --private_key`); `payload-dumper-go` is an extractor, not a
generator; both provided packages are non-A/B (`V648` = block OTA,
`V661` = Realtek `Update.img` TAR).

## 7. Consolidated verdict

| Path | Status |
|---|---|
| `/sdcard` + local update | reaches 50 %, fails at 93 MB `/cache` copy |
| write `/data/fota` | `system`-only, no external channel |
| `filePath` / `update_info` prefs | client-written only |
| identity-DB overwrite | possible, no effect |
| test-endpoint / `persist.tcl.update.*` | closed |
| forged update server | TLS system trust, needs root |
| factory app | USB-only provisioning |
| `update_engine` direct | SELinux deny for `shell` |
| recovery sideload | no `adbd` in recovery |
| fastboot | `flash.locked=1`, `verifiedbootstate=green` |
| **A/B package (`payload.bin`)** | **not available — client would install it (§6)** |
| **USB block medium** | **works, bypasses `/cache`** |
| **service PIN** | **vendor route, downloads to `/data/fota`** |
| **await CDN** | **works once the server serves the device** |

## 8. Reproducible commands

```bash
# device-identity DB (forensic tool)
python scripts/identity_db.py show      # read
python scripts/identity_db.py restore   # reset to captured originals

# client debug logging (debug.* is shell-settable)
adb shell setprop debug.tcl.ttvs.log 7

# observe an update check
adb shell logcat -c
adb shell am start -n com.tcl.ttvs/com.tcl.ttvs.versionUpdateApp.core.UI.CheckoutVersionActivity
adb shell logcat -d | findstr /i "zone getUpdateUrl isUpgradeByVerID getUpgrade checkAuthenSuccess"

# factory menu content
adb shell am start -a android.intent.action.MAIN -n com.tcl.factory.view/.MainMenu
adb shell uiautomator dump /sdcard/ui.xml & adb shell cat /sdcard/ui.xml

# package format check
python scripts/inspect_package.py <package>.zip

# A/B probe (generates unsigned AB zip, demonstrates §6)
python scripts/build_ab_probe.py
```

