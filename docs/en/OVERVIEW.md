# Technical Overview — Installing a Signed Update Without a USB Stick

**Target device class:** TCL Google TV, Realtek RTD platform (tested: G10 / 55C655,
Android TV 12, `user` build, AVB `green`, FBE-encrypted).

## Research question

Can a *vendor-signed* system update package be installed on such a device
**without** a removable USB block device — i.e. via network or internal storage?

**Answer: no.** The design funnels every install path through exactly one of
three gates: (1) a removable block medium, (2) the vendor's OTA server, or
(3) the vendor's signing key. This repository documents *why*, with
reproducible evidence.

## System architecture (as found)

```
┌──────────────┐   HTTP/WS   ┌──────────────┐  exec  ┌─────┐  USB/NET  ┌────────┐
│ Browser / UI │ ──────────► │ local tool   │ ─────► │ adb │ ────────► │  TV    │
└──────────────┘             └──────────────┘        └─────┘           └────────┘
                                                                   ┌───────────────┐
                                                                   │ ttvs (uid 1000│
                                                                   │  = system)    │
                                                                   │  ├ versionUpd │
                                                                   │  ├ UpdatePars │
                                                                   │  └ ABUpdateMgr│
                                                                   └───────────────┘
```

Key facts:

| Component | Role | Relevance |
|---|---|---|
| `com.tcl.ttvs` (versionUpdateApp) | OTA client, runs as **system** uid | Owns all install paths; `RECOVERY` + `ACCESS_CACHE_FILESYSTEM` granted |
| `RecoverySystem.verifyPackage()` | Whole-file signature check against `otacerts.zip` | **Mandatory**, runs before any install |
| `uncrypt` | Maps package → block map | Only bypasses `/cache` copy for raw `/data` paths |
| `update_engine` | A/B payload applier | Reachable only via client (`applyPayload`); SELinux blocks direct shell calls |
| `/cache` | 93 MB recovery-readable partition | Bottleneck for non-A/B packages (1974 MB package) |

## The central constraint

```
Location            Mechanism                    Outcome
────────────────────────────────────────────────────────────────────
/sdcard/ (FUSE)     uncrypt copies → /cache      93 MB vs 1974 MB → FAIL
/data/fota (raw)    uncrypt writes block map     recovery reads direct → OK
/mnt/media_rw (USB) recovery reads medium        OK (no /cache involved)
```

FUSE (`/sdcard` → `/storage/emulated/0`) does not exist in recovery, and `/data`
is FBE-encrypted. Therefore any package staged on the emulated storage is
copied to `/cache` — which is far too small. Only **raw `/data`** (specifically
`/data/fota`, writable solely by the `system` uid) or a **block medium** avoid
the copy.

## Signatures: the second gate

Even a correctly placed file must pass two independent checks:

1. **`RecoverySystem.verifyPackage`** — whole-file signature (signapk, vendor key).
2. **Payload signature** (A/B) — checked by `update_engine` against
   `/system/etc/security/otacerts.zip`.

Self-built packages pass neither. Reproduction: `scripts/build_ab_probe.py`
shows the A/B code path is *reached* (`isAbUpdateZip: true`, no `/cache` copy)
and then stops at `verifyPackage` with `GeneralSecurityException`.

## Why network / server tricks fail

The client installs only when a server-signed `UpgradeBean` is present. The
request/response channel is TLS with the **system CA store** (no certificate
pinning, but `networkSecurityConfig` absent ⇒ `targetSdk 30` ⇒ system CAs only).
A forged server is rejected before the first byte. Region/endpoint selection is
driven by read-only properties (`ro.product.clientType`), not by settable state.

## Result

Three viable install routes remain (all vendor-controlled):

1. Any **USB block medium** (card reader + microSD, HDD/SSD, phone in mass-storage
   mode, Raspberry Pi Zero gadget) — no stick required.
2. **Service PIN** from TCL support → client downloads to `/data/fota` itself.
3. **Await CDN distribution** — the regular online path uses the same `/data` route.

See `RESEARCH_STATE.md` for the full catalogue of 20+ attempted paths and their
documented failure reasons, and `INSTALLATION_PATH.md` for the deep dive.
