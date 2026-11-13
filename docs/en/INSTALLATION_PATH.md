# Installation Path — Deep Dive

## Summary

The TCL update client offers a *local* update path that finds and verifies the
package, then hands it to `RecoverySystem` / `update_engine`. Where the package
is stored determines whether installation succeeds.

## Path A: `/sdcard` root (tested, fails)

```
1. copy package to /sdcard/            → client finds it (root scan only)
2. isNeedProcessPackage               → true
3. signature verification             → OK up to 50 %
4. RecoverySystem.installPackage()    → must copy to /cache/recovery/package
5. /cache = 93 MB, package = 1974 MB  → copy fails, recovery finds nothing
```

`RecoverySystem.installPackage()` logic (simplified):

```java
if (filename.startsWith("/data/")) {
    filename = "@/cache/recovery/block.map";   // block map, no copy
}
// otherwise the file must be copied to /cache/recovery/package
```

A `/storage/…` (i.e. `/sdcard`) path therefore triggers the copy — and the
cache partition is simply too small.

## Path B: `/data/fota` (the device's own route)

When the path is under raw `/data`, `uncrypt` writes a **block map** — a tiny
file listing the package's storage locations. The recovery then reads the
package **directly from the partition**, with no copy.

```
/data has ~15 GB free       → package fits
block map = few KB          → fits into /cache
```

`/data/fota` is exactly where the client downloads its own online updates
(`Utils.java`): `new File("/data/fota").exists() ? "/data/fota" : "/data/"`.
It exists and is owned by `system`.

**Why it is still unusable:** the client rewrites `/data/…` paths for the
recovery in a way that only helps when `ro.crypto.state != "encrypted"`
(`InstallTools.java`); on this device the value is `encrypted`, so the
redirection is a no-op. And crucially, only the `system` uid may write to
`/data/fota` — `shell` (uid 2000) cannot place a file there.

## Path C: A/B payload (`payload.bin`) — works, but unsigned

If the package carries `ota-type=AB` in
`META-INF/com/android/metadata`, the client takes the A/B route:

```
isAbUpdateZip: true              (metadata parsed before signature check)
isNeedProcessPackage false       → no /cache copy at all
UpdateParser.parse() → ABUpdateManager.applyPayload("file://…")
```

This path reads the package **in place** and applies it via `update_engine`,
completely avoiding `/cache`. Reproduction with a self-built payload
(`scripts/build_ab_probe.py`) shows the route is reached and then fails at
`RecoverySystem.verifyPackage` (`GeneralSecurityException`) — the whole-file
signature, which only the vendor key can satisfy.

## Path D: USB block medium (works)

Vold mounts the medium under `/mnt/media_rw/<uuid>`. The recovery reads it
directly (`USB_FILE_PATCH = "/mnt/media_rw"` in `UpdateParser`), no `/cache`
and no `uncrypt` involved. Any block device works — card reader, HDD/SSD,
phone in mass-storage mode, Raspberry Pi Zero gadget. FAT32 suffices for the
~2 GB package.

## Path E: server-driven install (works only with the vendor)

The network path (`SystemUpdateService` → `BaseNetSystemUpdater`) installs
only after receiving a server-signed `UpgradeBean`; the client then downloads
to `/data/fota` itself. The request is TLS-protected with the **system CA
store** (no pinning, but user CAs are not trusted for `targetSdk 30` without a
`networkSecurityConfig`). Forging the server is therefore not possible without
root.

## Conclusion

| Path | Blocked by | Bypassable? |
|---|---|---|
| `/sdcard` | 93 MB `/cache` copy | no (physical size) |
| `/data/fota` write | uid `system` only | no (no external write channel) |
| A/B self-build | vendor signature | no (key unknown) |
| Server-driven | TLS + server response | no (no root) |
| USB medium | nothing | **yes — recommended** |
