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

[Production v1](production-v1.md) supplies a complete runtime folder locally.
The [GitHub pipeline](RELEASE.md) creates complete SD packages after merged
PRs. Use the assets on the [Releases page](https://github.com/Ibnuard/sleepingdogs_nx/releases)
when a release is published. GitHub's source download is not an installable
runtime, and the ignored `dist/` folder is not included in a clone.

| Package | Intended use |
| --- | --- |
| Complete runtime package | Fresh setup: NRO, Wine/FEX modules, renderer DLLs, assets and configuration; use its matching forwarder |
| Versioned update folder or historical ZIP | Update an already working installation; follow the package's prerequisite and install notes |
| Rollback ZIP | Restore the corresponding earlier runtime files after a test |
| Standalone NRO | Replace only the launcher/runtime binary in an otherwise compatible installation |
| GitHub source ZIP | Inspect or develop the project; see [Building](BUILD.md) |

Production packages include the runtime, forwarder, launcher assets and Wine
data. They exclude game data, saves, keys, `lossless.dll` and private LSFG
shaders. Historical update folders may be partial; do not reconstruct a fresh
installation by applying every experiment in the development history.

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
4. Keep the package's `d3d9.dll`, `d3d11.dll`, `dxgi.dll`, `sdndx4.dll` and `dxvk.conf` when
   file names overlap. The game and launcher renderer copies must match.
5. Open Sleeping Dogs from HOME. Use normal Launch / Launch GUI for play;
   enable Settings → Show debug launch and use Launch Debug when investigating
   startup or a crash. Normal production Play writes no diagnostic files.

See the [SD directory layout](../README.md#setup). The package's Wine runtime,
launcher resources and `share/wine/` files are required alongside the NRO.

For the current native-rendering baseline, select DXVK Native ARM64, FEX
Fastest and LSFG OFF. [Launcher v2](launcher-v2.md) always applies Light
1280×720 before launch and caches successful runtime verification. The x86
DXVK 3.1.1 route remains available as a comparison. Graphics profiles set
DXVK options independently of the mandatory Light game-detail profile.

## Updating an existing installation

1. Save the current log if it is needed for a comparison, and keep a backup
   of saves, preferences and the working runtime.
2. Close Sleeping Dogs **completely from HOME**.
3. Merge the update's `switch/` directory into the SD root, replacing the
   files included in that update. Do not delete the existing game installation.
4. No `start-game` folder is needed for production. Keep your game, saves and
   existing personal LSFG pack. The package does not change saved LSFG choices.
5. Relaunch. Normal Play is quiet; verify the NRO version/hash against the
   package manifest. Use explicit Launch Debug only when logs are needed.

For a production Debug launch, the build and memory markers include:

```text
[BUILD] sleepingdogs-production-v1
[SD-LOWVA] PASS: native above 4 GiB; guest low window available
[SD-SCHED-V17] mode=auto
```

The scheduler marker assumes the default automatic-affinity setting. Its A/B
override is described in [Settings](CONFIGURATION.md#developer-comparison-switches).

Use the rollback package for the exact experiment being reverted. A rollback
does not necessarily reset preferences or present-mode presets, so retain the
same settings when comparing performance.
