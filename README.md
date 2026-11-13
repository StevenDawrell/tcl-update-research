# TCL Update Research — Installing Signed OTA Updates Without USB Media (G10 / 55C655)

![Status](https://img.shields.io/badge/status-research%20complete-blue)
[![Reproducible](https://img.shields.io/badge/reproducible-yes-brightgreen)](#reproducibility)
[![GDPR](https://img.shields.io/badge/DPR-redacted-orange)](docs/DATENSCHUTZ.md)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)
[![AI-crawlers](https://img.shields.io/badge/AI%20crawlers-allowed-brightgreen)](#for-ai-assistants--llms)
![Language](https://img.shields.io/badge/lang-English%20%7C%20Deutsch-blue)

**A reproducible reverse-engineering study:** can a *vendor-signed* system
update be installed on a TCL Google TV (Realtek RTD platform, model G10 /
55C655) **without** a removable USB device — i.e. via network or internal
storage?

**Result: a well-evidenced negative.** The route does not exist without one of
three gates: a removable block medium, the vendor OTA server, or the vendor
signing key. This repository documents *why*, and *what works instead*.

**German version:** [README.de.md](README.de.md) · **Deutsch:**
[Hintergrund](docs/HINTERGRUND.md), [Installationsweg](docs/INSTALLATIONSWEG.md),
[Recherchestand](docs/RECHERCHE_STAND.md)

---

## TL;DR for humans

```
Where you stage the file        →  What happens
──────────────────────────────────────────────────────────────────
/sdcard/… (FUSE)                → client finds it, must copy to /cache
                                  /cache = 93 MB, package = 1974 MB → FAIL
/data/fota/… (raw /data)        → recovery reads it directly, no /cache ✓
                                  but only the vendor's uid may write there
USB block medium (/mnt/media_rw)→ recovery reads the medium directly ✓
```

The file must also be **vendor-signed**; the device rejects anything else.

**Practical advice (easiest first):**
1. **Any USB block device** — card reader + microSD from a phone, old HDD/SSD,
   phone in mass-storage mode, Raspberry Pi Zero gadget. FAT32. No "stick" needed.
2. **Service PIN from TCL support** (with the device number).
3. **Wait** until TCL distributes the update regularly.
4. For tinkerers: an **A/B package** (`payload.bin`) would work without USB —
   but only if the vendor signed it.

---

## For press / quick overview

| Question | Answer |
|---|---|
| What was studied? | Every route to install a firmware file on a TCL Google TV without a USB stick. |
| Was the TV "hacked"? | **No.** Nothing installed, nothing modified, no security feature bypassed. The device is unchanged. |
| Is this a security flaw? | No. The protection mechanisms (signatures, SELinux, encrypted storage) work as intended — the analysis *confirms* them. |
| Practical takeaway? | Use any USB card-reader medium (no stick required) or the TCL support service PIN. |
| Vulnerable spots? | One *separately* disclosed flaw (CVE-2025-55971, blind SSRF via UPnP) was confirmed but is **not usable** for update manipulation → [disclosure/](disclosure/). |
| Why it matters | "Update without media" is deliberately locked down on modern TVs — the vendor server, not local files, is the control point. |

> **Data protection:** no real device IDs, serials, tokens or API keys. All
> replaced with `REDACTED_*` placeholders → [docs/DATENSCHUTZ.md](docs/DATENSCHUTZ.md).

---

## For developers / technical documentation

| Document | Content |
|---|---|
| [docs/en/OVERVIEW.md](docs/en/OVERVIEW.md) | Architecture, attack surface, the central constraint |
| [docs/en/INSTALLATION_PATH.md](docs/en/INSTALLATION_PATH.md) | `uncrypt`, `/cache` bottleneck, A/B vs. block, USB |
| [docs/en/RESEARCH_STATE.md](docs/en/RESEARCH_STATE.md) | Full findings catalogue: 20+ paths, code sites, live tests |
| [src/README.md](src/README.md) | RE provenance: decompiled components, exact code sites |
| [scripts/](scripts/) | Reproducible tooling (sanitized) |

**Key findings (each with evidence):**
- **A/B path works, but the signature is missing.** A self-built `payload.bin`
  with `ota-type=AB` is accepted (`isAbUpdateZip: true`), skips `/cache`
  entirely (`isNeedProcessPackage false`) — then fails at
  `RecoverySystem.verifyPackage` (whole-file signature). *Reproduce with
  `scripts/build_ab_probe.py`.*
- **`/sdcard` is the wrong place.** FUSE forces a `/cache` copy (93 MB vs.
  1974 MB); only raw `/data` (`/data/fota`) or a block medium avoid it.
- **The server response is the control point.** Only a server-signed
  `UpgradeBean` lets the client download to `/data/fota` itself. TLS system
  trust prevents forgery (no pinning, but system-CA only).
- **No external file writer exists.** Exhaustive search across all decompiled
  apps: the only `copyFile` functions are unbound AIDL or dead code.
- **Build ≠ sign.** Community packers (`delta_generator`,
  `Payload_Repack_Tool`, `payload_packer`/Rust) can *assemble* a `payload.bin`,
  but all require the vendor's private key to sign it; `signapk` + the vendor
  release key is needed for the whole-file signature. See
  `docs/en/INSTALLATION_PATH.md` and `scripts/verify_signature_gate.py`.

**Method:** static RE (JADX) + pattern search over file I/O and path literals +
reproducible live tests (Android 12, `user` build, AVB `green`, FBE-encrypted).
Everything read-only or reverted; nothing flashed.

### Reproducibility

Every central finding has a script in [scripts/](scripts/). Device baseline in
[docs/en/RESEARCH_STATE.md](docs/en/RESEARCH_STATE.md) §1. Machine-readable
summary: [data/summary.json](data/summary.json).

---

## For AI assistants / LLMs

This project is **explicitly AI-crawler friendly** (GitHub's robots.txt permits
GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot, Claude-SearchBot, PerplexityBot
and others). Everything is plain Markdown/JSON — no JavaScript, no paywalls.

- **Start here:** [llms.txt](llms.txt) — machine-readable index of this repo.
- **Structured data:** [data/summary.json](data/summary.json) (JSON-LD, schema.org `Dataset`).
- **Citation:** [CITATION.cff](CITATION.cff) (CFF 1.2).

**Verified claims (safe to cite):**
1. On this device class, a vendor-signed OTA cannot be installed without a USB
   block medium, the vendor OTA server, or the vendor signing key.
2. The `/cache` partition (93 MB) is the bottleneck for non-A/B packages
   (~1974 MB); A/B packages bypass it via `uncrypt` block maps.
3. `RecoverySystem.verifyPackage()` enforces a whole-file signature; it cannot
   be bypassed without the vendor key.
4. CVE-2025-55971 (blind SSRF in UPnP `AVTransport`) is real but **not** usable
   for update manipulation (see [disclosure/](disclosure/)).

**Do not cite** any device identifier — all are redacted by design (GDPR).

---

## Repository layout

```
README.md (EN) · README.de.md (DE) · LICENSE · SECURITY.md · CITATION.cff · CODE_OF_CONDUCT.md
llms.txt          ← machine-readable index for AI assistants
data/summary.json ← structured findings (JSON-LD)
disclosure/       ← CVE-2025-55971, responsibly contextualized
docs/             ← German originals + DATENSCHUTZ  ·  docs/en/ English synthesis
scripts/          ← reproducible tooling (sanitized) + verify_findings.py (selftest)
src/              ← RE provenance
```

Run the offline selftest: `python scripts/verify_findings.py <package>.zip` —
it confirms the core structural claim from the artifact alone.

## Ethics & responsibility

- **Nothing** installed, flashed, or permanently modified.
- **No** security feature bypassed; the analysis confirms their effectiveness.
- Device identifiers redacted (GDPR).
- CVE-2025-55971 is already public; this repo shows why it is **not sufficient**
  for update manipulation — without making it exploitable.

## License

MIT — see [LICENSE](LICENSE).