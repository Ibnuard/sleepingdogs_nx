# FEXTendo / Sleeping Dogs NX

FEXTendo is a Nintendo Switch launcher and compatibility **wrapper for the
original Windows PC version of Sleeping Dogs** (`HKShip.exe`, x86). It uses
Wine, FEX-Emu and DXVK to run the PC game. This repository contains the
Sleeping Dogs integration, runtime patches, build tools and test records.

The **Switch port and Horizon/Wine integration of FEX-Emu** are developed by
**AndroSwitch Project / Ibnuard**, continuing our PES13/FEXTendo work. The CPU
translation engine is upstream FEX-Emu; the Wine/Horizon runtime foundation
comes from Wine-NX / Autorun. See [credits and source provenance](THIRD_PARTY.md).

**Provide your own installed original PC game.** Game executables, game data
and saves are not supplied. The x64 **Definitive Edition is not supported**.

[Installation](docs/INSTALL.md) · [Settings](docs/CONFIGURATION.md) ·
[Troubleshooting](docs/TROUBLESHOOTING.md) · [All documentation](docs/README.md)

## Current status

This is an **experimental port** with gameplay confirmed on a Switch OLED.
Recent 720p x86-DXVK testing reports roughly **20–23 FPS**, with scene-dependent
drops and peaks around 25 FPS. Native H4 v8.1 with Light 720p is reported at
20–22 FPS, with crowded-area lows near 16 and confined-view peaks near 30.
**Stable 30 FPS has not been achieved.**

| Area | Status |
| --- | --- |
| Runtime | v18 APC test build, retaining the v17 scheduler improvement |
| Graphics | x86 DXVK 3.1.1-sdbatch2 over native ARM64 Mesa/NVK |
| Native DXVK research | [H4 v9 gameplay](docs/native-dxvk-h4-v9-memory-batching.md#subsequent-game-capture) confirms Light 720p and batching, with no meaningful improvement reported; last five Present windows pool to 20.59 FPS |
| FEX research | [Context v1](docs/fex-context-v1.md) shortens exact x87 context imports; numerical and actual ARM64-function checks pass, Switch FPS comparison pending |
| Launcher | DXVK profiles, None / FPS / Full HUD, optional experimental LSFG |
| Distribution | Source and test records; no packaged GitHub release as of 2026-10-12 |

See [current status and test evidence](docs/STATUS.md) for known issues,
hardware conditions and the difference between native FPS and frame generation.

## Setup

1. Obtain a **complete Sleeping Dogs test runtime package** and its matching
   forwarder. A GitHub source ZIP, standalone NRO or update ZIP does not contain
   everything needed for a fresh installation. See [package types](docs/INSTALL.md#packages).
2. Extract the package's `switch/` folder to the SD root. Copy your own game
   installation into `switch/sleepingdogs-fex/drive_c/SleepingDogs/`, keeping the
   package's `d3d9.dll`, `d3d11.dll`, `dxgi.dll` and `dxvk.conf`.
3. Use the matching **FEXTendo Memory v1 TEST** environment and Sleeping Dogs
   **39-bit + guest low-window** forwarder. Its target is
   `sdmc:/switch/sleepingdogs-fex/sleepingdogs-fex.nro`. Follow the
   [boot and forwarder requirements](docs/INSTALL.md#boot-and-forwarder).
4. Launch Sleeping Dogs from HOME. For a native-FPS baseline, use DXVK 3.1.1,
   FEX Fastest, LSFG OFF and 1280×720. Close the application from HOME before
   applying an update.

Expected layout at the SD root; keep the other runtime files supplied by the
complete package:

```text
switch/sleepingdogs-fex/
├── sleepingdogs-fex.nro
├── configuration.ini
├── launcher/                         # assets, renderer sets and preferences
├── drive_c/
│   ├── SleepingDogs/
│   │   ├── HKShip.exe                # your original x86 PC game
│   │   ├── Data/                     # your game data
│   │   ├── ...                       # all BIG/BIX and other installed files
│   │   ├── d3d9.dll                  # package-supplied DXVK
│   │   ├── d3d11.dll
│   │   ├── dxgi.dll
│   │   └── dxvk.conf
│   └── windows/                      # package-supplied Wine/FEX modules
└── share/wine/                       # runtime fonts and NLS data
```

The launcher graphics profiles configure DXVK. The H4 v8 candidate also adds
Game detail → Light 720p, a reversible preset for the game's own display options. The `Graphics Level: undefined` label remains unresolved.
Installation details, updates and log locations are in the
[documentation index](docs/README.md).

## Development

Start with the [build guide](docs/BUILD.md) and [contributing guide](CONTRIBUTING.md).
The current build recipes depend on prepared local Wine/FEX/Mesa inputs and
versioned build receipts; a clean clone is not yet a self-contained v18 build.

[Development history](docs/HISTORY.md) indexes the original experiments without
mixing their installation instructions into the current setup guide.

## Credits

- **FEXTendo / AndroSwitch Project / Ibnuard:** Switch FEX integration,
  native launcher and Sleeping Dogs compatibility work.
- **[FEX-Emu](https://github.com/FEX-Emu/FEX) and contributors:** the upstream
  x86 CPU translation engine.
- **[Wine-NX / Autorun](https://github.com/autorunhq/autorun), danfromtico and
  contributors:** the Wine/Horizon runtime foundation and attributed backports.
- **Wine, DXVK, Mesa/mesa-switch, libnx, Sphaira and other dependencies:**
  their original authors and licenses are retained.

See [THIRD_PARTY.md](THIRD_PARTY.md) for component origins and license notices,
including the optional LSFG integration. The repository contains the
[LGPL-2.1 license](LICENSE); component-specific licenses also apply.
Unofficial project; not affiliated with the game's publishers or Nintendo.
