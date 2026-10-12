# Installation and updates

[Documentation](README.md) · [Settings](CONFIGURATION.md) · [Troubleshooting](TROUBLESHOOTING.md)

## Requirements

- Your own installed **original Sleeping Dogs PC game**, with the x86
  `HKShip.exe`. The x64 Definitive Edition is not supported.
- A complete Sleeping Dogs FEXTendo runtime package.
- A Switch environment providing the project's **39-bit host + guest
  low-window** memory layout and its matching Sleeping Dogs HOME forwarder.

Gameplay has been confirmed on an OLED handheld. The reference test clocks
are CPU 1728 / GPU 768 / RAM 1600 MHz; these describe a reported test, not
minimum requirements or a guarantee of performance. See [Current status](STATUS.md).

## Packages

As of **2026-10-11**, this repository has no packaged GitHub release. Existing
test builds were distributed from the development workspace. GitHub's source
download is not an installable runtime, and the ignored `dist/` folder is not
included in a clone.

| Package | Intended use |
| --- | --- |
| Complete runtime package | Fresh setup: NRO, Wine/FEX modules, renderer DLLs, assets and configuration; use its matching forwarder |
| Versioned update folder or historical ZIP | Update an already working installation; follow the package's prerequisite and install notes |
| Rollback ZIP | Restore the corresponding earlier runtime files after a test |
| Standalone NRO | Replace only the launcher/runtime binary in an otherwise compatible installation |
| GitHub source ZIP | Inspect or develop the project; see [Building](BUILD.md) |

The v18 APC update is an update to the existing low-window installation, not
a complete first-install bundle. Do not reconstruct a fresh installation by
applying every ZIP listed in the development history.

## Boot and forwarder

The current path uses **FEXTendo Memory v1 TEST** with:

```text
Forwarder: FEXTendo-SleepingDogs-39bit-FEXTendoMemory-v1.nsp
Title ID:  059a3db219b42000
Target:    sdmc:/switch/sleepingdogs-fex/sleepingdogs-fex.nro
Layout:    39-bit native host with a low address window for the x86 guest
```

The forwarder requests the memory layout through its `fxtmem` descriptor.
Installing the NSP alone does not add that support to the active kernel/loader.
The test environment must already be set up with the matching memory support;
this repository does not provide a general-purpose firmware setup guide.

Install the matching forwarder once and launch its HOME tile. The original
32-bit Sleeping Dogs forwarder, an unrelated F1/PES13 forwarder, and Album
applet mode are not substitutes for this setup. The earlier title-specific
low-window boot route is documented in the [historical startup record](low-window-startup-fix.md).

A runtime-only update does not require reinstalling the matching forwarder
or rebooting while the compatible boot environment remains active.

## Copy the runtime and game

1. Extract the complete package's `switch/` directory to the SD root.
2. Copy the **contents** of your installed game into
   `switch/sleepingdogs-fex/drive_c/SleepingDogs/`.
3. Include `HKShip.exe`, all BIG/BIX archives, `Data/`, original game DLLs and
   other supporting files. Avoid an extra nested `Sleeping Dogs/` directory.
4. Keep the package's `d3d9.dll`, `d3d11.dll`, `dxgi.dll` and `dxvk.conf` when
   file names overlap. The game and launcher renderer copies must match.
5. Open Sleeping Dogs from HOME. Use normal Launch / Launch GUI for play;
   use Launch Debug when investigating startup or a crash.

See the [SD directory layout](../README.md#setup). The package's Wine runtime,
launcher resources and `share/wine/` files are required alongside the NRO.

For the initial native-rendering baseline, select DXVK 3.1.1, FEX Fastest,
LSFG OFF and 1280×720. Choose game quality through its own menus; launcher
profiles do not set the game's world-detail preset.

## Updating an existing installation

1. Save the current log if it is needed for a comparison, and keep a backup
   of saves, preferences and the working runtime.
2. Close Sleeping Dogs **completely from HOME**.
3. Merge the update's `switch/` directory into the SD root, replacing the
   files included in that update. Do not delete the existing game installation.
4. Read the update's notes for any required renderer or forwarder replacement.
   In particular, the v18 APC update retains existing presets and preferences.
5. Relaunch and verify the build in `switch/sleepingdogs-fex/fex-runtime.log`.

For v18, the build and memory markers include:

```text
[BUILD] sleepingdogs-fextendo-0.1.0-v18-apc
[SD-LOWVA] PASS: native above 4 GiB; guest low window available
[SD-SCHED-V17] mode=auto
```

The scheduler marker assumes the default automatic-affinity setting. Its A/B
override is described in [Settings](CONFIGURATION.md#developer-comparison-switches).

Use the rollback package for the exact experiment being reverted. A rollback
does not necessarily reset preferences or present-mode presets, so retain the
same settings when comparing performance.
