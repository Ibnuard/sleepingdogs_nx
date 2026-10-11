# Building and validating the port

[Documentation](README.md) · [Contributing](../CONTRIBUTING.md) · [Credits](../THIRD_PARTY.md)

## Build status

The repository contains runtime overlays, pinned vendor inputs and versioned
build/packaging scripts. It does **not yet provide a self-contained build of
v18 from a clean clone**. The current recipes reuse prepared Wine/FEX/Mesa
trees, compiled dependencies and hash-checked receipts from the development
workspace. There is no automated GitHub runtime-release workflow.

There are two distinct entry points:

| Path | Purpose |
| --- | --- |
| [tools/build_launcher.py](../tools/build_launcher.py) | Original baseline preparation and full runtime staging, using the earlier 32-bit layout |
| Versioned `prepare_*`, `build_*`, `package_*` scripts | Later low-window, renderer and scheduler experiments, up to v18 |

Running the baseline builder alone does not produce the current v18 low-window
runtime. Historical scripts retain old names, version labels and dependencies
so their recorded builds can be traced.

## Workspace inputs

Native builds use WSL Ubuntu / Linux with devkitPro and devkitA64, the matched
libnx/portlibs, Wine/FEX/Mesa build inputs, and the cross-compilers used in the
recorded receipts. Python dependencies for baseline asset/package tools are
listed in [requirements.txt](../requirements.txt). Host validation additionally
uses native compilers with sanitizers; binary checks use modules such as
`pyelftools` and Unicorn according to the selected test script.

The existing scripts expect these prepared inputs:

| Input | Use |
| --- | --- |
| `../pes13-nx/local/production-input-fix/approved/` | Approved FEXTendo runtime, generated Wine source and launcher resources |
| `../pes13-nx/local/production-input-fix/wine-source.tar.gz` | Matched Wine source archive |
| `../Sleeping Dogs/HKShip.exe` | User-owned original x86 game for PE validation and icon extraction |
| `/home/blekjek/pes13-build` | Recorded dependency-build root; baseline builder accepts `--pes-build-root` |
| `/home/blekjek/sleepingdogs-*` and `local/*` | Prepared version-specific source, object files, symbols and receipts |

These local paths are not downloads or files supplied by GitHub. Inspect
[port_common.py](../tools/port_common.py), [f1_base_build.py](../tools/f1_base_build.py)
and the chosen versioned recipe before adapting them to another workspace.
[upstream-inputs.json](../reports/upstream-inputs.json) records the initial
import; it is not a complete dependency manifest for every later experiment.

Use separate Sleeping Dogs build directories. Preserve approved sibling
projects, SDK installations and baseline receipts when preparing a candidate.

## Original baseline recipe

With the inputs above already present, run from the repository root inside
WSL/Linux. The example output and work directories must be fresh:

```sh
python3 -m pip install -r requirements.txt
python3 tools/build_assets.py
python3 tools/build_launcher.py \
  --work "$HOME/sleepingdogs-baseline-doc-example" \
  --pes-build-root /home/blekjek/pes13-build \
  --game "../Sleeping Dogs/HKShip.exe" \
  --output dist/sleepingdogs-baseline-doc-example \
  --jobs 4
```

The asset builder uses the default sibling game path and approved launcher
resources. `--game` on the launcher builder does not change the asset builder's
input. `--prepare-only` prepares native source; `--build-only` stops after
ELF/NRO generation. Source changes require a fresh `--work` directory because
the preparation receipt binds the inputs.

This is the **historical baseline**, not the recommended current device build.
Do not install its older forwarder over a working low-window setup.

## Current v18 recipe

v18 builds on the already prepared v17 scheduler tree and its delivered ELF,
NRO, object files, link command and update ZIP. It first reproduces the v17
ELF byte-for-byte, then recompiles the changed native units.

| Step | Entry point / required context |
| --- | --- |
| Prepare v18 overlay | [prepare_apc_v18.py](../tools/prepare_apc_v18.py), based on `/home/blekjek/sleepingdogs-scheduler-v17/native-source` |
| Build and reproduce baseline | [build_apc_v18.py](../tools/build_apc_v18.py), using `local/scheduler-v17/native.json` and its exact link inputs |
| Check host behavior | [check_apc_v18.py](../tests/check_apc_v18.py), with the prepared protocol/source trees |
| Extract the compiled ABI | [extract_apc_v18_layout.py](../tests/extract_apc_v18_layout.py) |
| Check ARM64 code | [check_apc_v18_binary.py](../tests/check_apc_v18_binary.py), against the candidate ELF |
| Check inherited behavior | Native, diagnostic, direct-sync, low-window and shader checks required by the packager |
| Package update and rollback | [package_apc_v18.py](../tools/package_apc_v18.py), after all required reports pass |

Preparation and build scripts currently contain fixed workspace paths. They
are not portable command-line installers. Read the recipe and receipt before
running it; missing predecessor inputs cannot be replaced by a similarly named
NRO or a newer upstream dependency.

The packager enumerates the required reports in its `REPORTS` tuple and verifies
their source/ELF identities, baseline archive hash, payload CRCs and rollback.
The [v18 package record](../reports/apc-v18-package.json) identifies the existing
artifacts and hashes. Local artifact names are:

```text
dist/sleepingdogs-fex-v18-apc-update.zip
dist/sleepingdogs-fex-v18-rollback-v17.zip
```

These are update/rollback artifacts for an existing installation. The
[v18 experiment note](apc-v18.md) describes the code change; [Current status](STATUS.md)
records subsequent hardware results.

## Native DXVK H4 candidate

The [H4 v5 recipe](native-dxvk-h4-v5-com-outputs.md#rebuild-and-capture-analysis) overlays the pinned
v18 link inputs and native H1 DXVK archive, first reproducing the baseline ELF.
It builds PE32 COM DLLs, a real COM self-test client and the ARM64 runtime with
three renderer choices. Separate host, compiled-ABI, window-handoff,
logging/progress, PE32 output, launcher-transaction and static-game-import checks feed its
folder packager.

Run the listed checks before `tools/package_native_dxvk_h4.py`. The output is
`dist/sd-dxvk-native-h4-v5-update/` with two-phase COM/game activation and the
exact v18 rollback; no ZIP is created. Prepared sources/objects/SDK and pinned
legacy DLLs remain necessary. Run the PE32 output check with Windows Python;
other build/package steps run in WSL. Local PASS receipts do not establish H4 Switch guest
execution, game API coverage, gameplay or a Switch FPS improvement.

## Forwarder and distribution

[forwarder/build_forwarder.py](../forwarder/build_forwarder.py) builds the
pinned Sphaira-based forwarder using a local keyset and supplied NRO. Its
`--fextendo-memory-v1` option implies `--low-window` and adds the memory-layout
descriptor. See [forwarder technical notes](forwarder-memory-v1.md) and the
current [boot requirements](INSTALL.md#boot-and-forwarder).

The original [package_sd.py](../forwarder/package_sd.py) and
[verify_package.py](../tools/verify_package.py) belong to the baseline package
path. Later versioned packagers have their own matching validation; a baseline
check is not a substitute for those checks.

Keep game files, keys and personal test data out of distributable artifacts.
[stage_game.py](../tools/stage_game.py) makes a local testing copy with the
user's game; that output is not a release bundle. Optional LSFG shader payloads
derived from a proprietary input also remain personal test inputs.

Preserve component notices and the matching modified sources/build recipes in
any distributed runtime package. [THIRD_PARTY.md](../THIRD_PARTY.md) is the
current project overview; the original baseline packager still copies the
inherited PES13 notice snapshot. A future consolidated release must account
for the later renderer, Mesa and optional LSFG components as well.

## Validation boundaries

Host sanitizer tests, ARM64 execution with modeled platform calls, and package
hash checks establish different parts of correctness. None measures actual
multicore scheduling, shader execution or gameplay performance on Switch.
Report the exact checks run and their candidate identities, then perform a
separate hardware test. A build receipt's original `hardware_tested: false`
field describes that build-time record; later feedback belongs in the status
and experiment documentation.

For documentation-only changes, check relative links and anchors, referenced
files, Markdown formatting and consistency with the scripts. A native rebuild
is unnecessary unless runtime or packaging behavior changes.
