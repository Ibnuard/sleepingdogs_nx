# Production v1: quiet Play and public packaging

This build retains launcher v4's native COM/Present work and Light 720p. The
user accepted the preceding gameplay candidate and supplied six README
screenshots. No new FPS measurement or Switch test of production v1 is claimed.

## Behavior

Normal Play does not open runtime, crash, system-check or DXVK diagnostic
files. Native DXVK logging is gated before its mutex/file code, including
loggers initialized before `main`. Guest environment construction removes
duplicate logging keys before selecting the quiet policy. Existing diagnostic
marker files cannot turn normal Play into a trace session.

The ordinary maintenance thread still flushes the registry, performs scheduler
maintenance and saves last played after the first successfully presented frame.
This no longer depends on a diagnostic frame report. Settings, verification
cache, game saves, functional shader caches and recovery state remain enabled.
Old log files are left untouched, so their presence alone does not identify a
new production session.

**Settings → Show debug launch → Launch Debug** explicitly enables diagnostics.
DXVK HUD needs no Debug launch. This preserves a troubleshooting route without
writing diagnostic files during ordinary play.

The required low-memory checks, cached full verification and keyboard behavior
are retained. The public checker catalog excludes the optional private LSFG
pack. The release contains no `lsfg.txt`, so existing LSFG settings are preserved.
Without a compatible personal shader pack, LSFG cannot generate frames.

## Deliverable

`dist/sleepingdogs-fex-production-v1/` is a ready-copy folder. Existing users
copy only its main `switch/` folder to the SD root after closing from HOME.
The root forwarder is included for a fresh compatible setup; no reinstall is
needed for users already on that matching forwarder. Source/evidence folders
are reference material and need not go on the SD.

Game files, saves, keys, `lossless.dll`, `LosslessScaling.dll` and proprietary
LSFG shader packs are excluded. Wine fonts/NLS, runtime modules, launcher assets,
renderer sets and presets are included. The memory boot patch is a separate
prerequisite; the forwarder does not install it.

## Build and evidence

NACP version: `0.1.0-p1`.

NRO SHA-256:
`e6169af1a3ead1aeaf53c0ee9c70f8e322cc70a4d6f9a26bc765ea24ddc734b3`.

The recipe uses pinned launcher-v4 objects and recompiles the production
runtime, native Present shim and native logger. It does not modify the renderer,
FEX translator, saved LSFG preference or sibling-project build inputs.

```sh
python3 tools/build_production.py
python3 tools/test_production.py
python3 tools/test_production_launcher.py
python3 tools/prepare_production_runtime.py \
  --output local/production-v1/sleepingdogs-production-v1-public-runtime.zip
```

These commands require the prepared WSL workspace described in [Building](BUILD.md).
The archive path must be new; published inputs are immutable.
Before preparing the archive, also run `python tools/test_production_binary.py`
with the Windows Python environment containing pyelftools and Unicorn. It
reads the exact linked WSL ELF through the shared workspace.

Validation covers the actual environment builder under sanitizers (240 boundary
cases), the actual native logger initialized before `main` (2,000 quiet calls,
Debug and quiet again), actual maintenance/first-frame history functions,
launcher/checker/keyboard/LSFG regression checks, and ARM64 heap and symbol
checks. The public package is re-read and every file hash, DLL architecture,
NRO version and forwarder NCA inventory is checked.

See [production validation](../reports/production-v1-validation.json) and
[release pipeline](RELEASE.md). Host PASS does not establish hardware FPS or
exclude device-only failures.
