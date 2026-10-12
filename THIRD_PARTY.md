# Credits, source provenance and licenses

[Project home](README.md) · [Documentation](docs/README.md)

This file describes the Sleeping Dogs port. Component-specific copyright and
license notices remain authoritative; the root [LGPL-2.1 license](LICENSE)
does not replace the licenses of upstream code, assets or optional components.

## FEXTendo and the FEX Switch port

**AndroSwitch Project / Ibnuard** developed FEXTendo's Nintendo Switch
Horizon/Wine integration of FEX-Emu, continuing the project's `pes13-fex` work.
That includes the host adapter, JIT-memory integration, callback and exception
integration, launcher and game-specific compatibility work. The upstream CPU
translator and JIT remain **FEX-Emu** code.

The Sleeping Dogs port inherits that FEXTendo integration and reusable F1
runtime helpers. It does not take its FEX Switch integration from Autorun.
Wine-NX / Autorun remains the credited Wine/Horizon foundation, and later
adapted runtime changes are attributed separately.

- [PES13 FEX port source and commit record](https://github.com/Ibnuard/pes13_nx/blob/main/docs/FEX-PORT-PROVENANCE.md)
- [Initial adapter and guest validation](https://github.com/Ibnuard/pes13_nx/commit/88b6a2f267ae01bc8d4f8f35fb31df865800f67a)
- [Sleeping Dogs initial helper/input receipt](reports/upstream-inputs.json)

Original project code and adapted runtime files retain their own notices,
including LGPL-2.1-or-later and MIT where marked. Helper names beginning with
`f1_` are retained for traceability; they do not make F1 game data part of this
port.

The release-preparation keyboard and checker adaptation uses PES13 commit
[`38750c20`](https://github.com/Ibnuard/pes13_nx/tree/38750c20a303f9fc6c373edaada0fad3c86d5b4b).
Imported headers/tests retain LGPL-2.1-or-later notices; exact hashes are in
[vendor/pes13-launcher.json](vendor/pes13-launcher.json). The in-frame keyboard
design also credits Wine-NX / Autorun. The Sleeping Dogs host Vulkan adapter,
offline file catalog and mandatory low-window gate are documented in
[the candidate notes](docs/launcher-compact-v1.md).

## Runtime components

| Component | Origin and notices |
| --- | --- |
| Wine / Wine-NX / Autorun | Wine authors, danfromtico and contributors. The inherited baseline is [Wine-NX `1bc4e451`](https://github.com/danfromtico/wine-nx/tree/1bc4e45163f0d2328cdfd35c7f471dd9821bb879); retain LGPL-2.1-or-later notices and any later component-specific terms. |
| FEX-Emu | Ryan Houdek and FEX contributors; upstream [revision `e2f973fe`](https://github.com/FEX-Emu/FEX/tree/e2f973fe931e6dc2ce523795e51ca1ac3ca85816), MIT, with individual dependency notices. The pinned WOW64 module also credits André Zwing's Hangover work. |
| DXVK | Philip Rebohle, Joshua Ashton, Robin Kertels, Jeffrey Ellison and contributors; [3.1.1 base](https://github.com/doitsujin/dxvk/tree/b1a1c99ab52b687cf950d62c88bc2fa316b41663), zlib/libpng. The Sleeping Dogs memory and submission patches build on that work. See the retained [DXVK license](vendor/dxvk/DXVK-LICENSE). |
| DXVK-GPLAsync | DXVK authors, Ph42oN, Sporif and prior async-patch contributors; optional [2.7.1-1 release](https://gitlab.com/Ph42oN/dxvk-gplasync/-/releases/v2.7.1-1). Preserve the upstream and patch notices supplied with the renderer. |
| Mesa / mesa-switch | Mesa authors, danfromtico, NaGaa95 and contributors; inherited [revision `b297e230`](https://github.com/danfromtico/mesa-switch/tree/b297e230ef88c6c88df2561becf864f979f494a6) with later recorded backports. Mostly MIT; individual source licenses apply. |
| libnx | switchbrew and contributors, ISC. The virtual-memory adaptation retains its [libnx notice](tools/scratch_pages/libnx-LICENSE.md.txt). |
| Sphaira forwarder | ITotalJustice, NaGaa95 and contributors; [Sphaira source](https://github.com/NaGaa95/sphaira). The forwarder recipe pins loader revision `72a94b905816de24817594109fb012a8f7107d8c`; preserve its source notices. |
| DXBC-SPIRV, LLVM and libdisplay-info | Their respective authors; retained [DXBC-SPIRV](vendor/dxvk/DXBC-SPIRV-LICENSE), [LLVM](vendor/dxvk/LLVM-LICENSE.TXT) and [libdisplay-info](vendor/dxvk/libdisplay-info-LICENSE) notices accompany the vendor inputs. |

Linked libraries and packaged resources also retain their individual notices,
including SDL2/SDL2_ttf, FreeType, HarfBuzz, libdrm, libpng, zlib, bzip2, Expat,
Zstandard, Wine fonts/NLS data and the devkitPro/LLVM/Rust toolchain components.
The [inherited notice snapshot](docs/PES13-THIRD-PARTY.md) records these origins;
its PES-specific optional components and paths do not imply that every one is
active in Sleeping Dogs. Exact runtime inputs vary by experiment and are
recorded in the corresponding build/package receipts.

The [native DXVK probe v1](docs/native-dxvk-probe-v1.md) uses DXVK's existing
native implementation and headers with the retained licenses above. Its
original `src/native_dxvk/probe_*` sources, original test shaders and
`tests/native_dxvk_abi.c` carry MIT notices; see the
[probe license](src/native_dxvk/LICENSE). This experiment does not use LSFG
or game shader payloads.

The [H4 COM bridge](docs/native-dxvk-h4-v1.md) adds original MIT-marked proxy,
dispatch and fixture code in `src/native_dxvk_com/`. Its generated signatures
and GUID inventory are derived from the pinned DXVK native headers and Wine
IDL files; their respective upstream notices still apply. The ready folder
retains the inherited native renderer/driver source bundle, exact H4 overlays
and both legacy renderer origins. No game or proprietary LSFG shader bytes
are included.

## Attributed backports

The [v9 shader integration](docs/low-window-shader-optimizations.md) adapts
Autorun commits
[`5a75cfb647a0`](https://github.com/autorunhq/autorun/commit/5a75cfb647a010704a2811f535323fc4b39c9109),
[`e823a778f5cc`](https://github.com/autorunhq/autorun/commit/e823a778f5ccf40ae8392209b9ff769b42780c14), and
[`e7168c3f438a`](https://github.com/autorunhq/autorun/commit/e7168c3f438ace433c4e77da2cb4533762a77399)
for worker affinity and temporary allocation reuse. These adaptations retain
their upstream attribution; project allocator helpers retain their marked MIT
license. The [Mesa backport record](docs/low-window-mesa-backport.md) and
[GM20B shader record](docs/low-window-gm20b-shaders.md) identify later graphics work.

## Optional LSFG integration

The [v15 presentation and LSFG record](docs/native-v15-lsfg.md) identifies:

| Input | Revision / license record |
| --- | --- |
| Autorun presentation glue | [`cbb0e4e6`](https://github.com/autorunhq/autorun/tree/cbb0e4e6e7fa7f47f328d92441f51bfb507f266f), GPL-3.0-or-later |
| Switch backend adaptation | [`switch-dev` `28b2fe1b`](https://github.com/autorunhq/switch-dev/tree/28b2fe1bc39ef1f4c4fe217c430a6908e7d4c7e8/lsfg), with retained upstream notices |
| LSFG-VK archive | [Source archive repository](https://git.lsfg-vk.dev/lsfg-vk-archive.git), revision `8b0da2661c6f3473a7fccc8ba643880050e71642`, GPLv3 |
| DXBC converter | [`78ab59a8`](https://github.com/PancakeTAS/dxbc/tree/78ab59a8aaeb43cd1b0a5e91ba86722433a10b78), zlib/libpng |

The proprietary shader pack used in personal testing was derived from the
user-supplied Lossless Scaling DLL. It is separate from the GPL source and is
not provided as a public redistribution by this repository. Source-code
licenses do not grant rights to that proprietary payload.

## Artwork and distribution

The Sleeping Dogs icon is extracted from the user's game by the asset builder;
game names and artwork remain the property of their respective owners. The
neutral launcher background is generated by the project. Reused FEXTendo
launcher fonts and resources retain their existing notices and provenance.
Source licenses do not license third-party game artwork.

Game executables, game archives, saves and local keys are not release inputs.
When distributing runtime binaries, retain the applicable notices and matching
modified sources/build recipes. See [Building](docs/BUILD.md#forwarder-and-distribution)
for the current package limitations.
