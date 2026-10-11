# Third-party components

> Inherited notice snapshot. PES13-specific paths and optional components below
> refer to the source project, not the current Sleeping Dogs installation.
> See [Sleeping Dogs credits](../THIRD_PARTY.md) and the
> [documentation index](README.md) for the current scope. PES13 source links
> have been repaired against revision `65f6962f`; attribution text is retained.

FEXTendo / PES13-NX is a wrapper built on existing open-source projects.
Its FEX backend uses the upstream FEX-Emu engine. The older Box64 backend remains
in the repository's history and build tools. Original copyright headers and
component licenses are preserved; the project name does not replace them.

The [FEX port provenance record](https://github.com/Ibnuard/pes13_nx/blob/65f6962f49381e08ab71a1b87c9f2efcff8e49d5/docs/FEX-PORT-PROVENANCE.md) maps AndroSwitch
Project / Ibnuard's Switch integration work to source files, commit history
and recorded validation. A `fex_` filename identifies its integration target;
it does not by itself establish original authorship.

## Provenance: reused, adapted and original

| Part | How this project uses it |
| --- | --- |
| Autorun / Wine-NX and Wine | The runtime is built from the pinned Wine-NX source, with project patches. The native Horizon runtime, Wine loader, Windows API implementation and underlying platform support are inherited code, not a runtime written from scratch here. [Autorun](https://github.com/autorunhq/autorun) is the project's current name. The base is Wine-NX commit `1bc4e45163f0d2328cdfd35c7f471dd9821bb879`, recorded in [dependencies.json](https://github.com/Ibnuard/pes13_nx/blob/65f6962f49381e08ab71a1b87c9f2efcff8e49d5/dependencies.json). |
| Direct Autorun backport | The waitable-timer changes in [tools/fex_runtime_fixes.py](https://github.com/Ibnuard/pes13_nx/blob/65f6962f49381e08ab71a1b87c9f2efcff8e49d5/tools/fex_runtime_fixes.py) contain before/after code from Autorun commit [51f94949](https://github.com/autorunhq/autorun/commit/51f94949d738c978bfb80a5118d7ffa4cf6b98ae), then add project changes for cancellation semantics, bounded catch-up, overflow and rearm handling. This later backport entered this repository in [c4ec5cb](https://github.com/Ibnuard/pes13_nx/commit/c4ec5cb2d0262841c36c6cbb5472c8a2f3ea26e3), after the initial FEX guest PASS; it was not part of the initial port. This is adapted upstream code, not wholly original code. |
| Autorun graphics-worker offload (opt-in trial) | [src/runtime/fex_dxvk_core3.h](https://github.com/Ibnuard/pes13_nx/blob/65f6962f49381e08ab71a1b87c9f2efcff8e49d5/src/runtime/fex_dxvk_core3.h) and its name/affinity wiring adapt Autorun commit [c2268252](https://github.com/autorunhq/autorun/tree/c2268252a28abb5977fec8ea385b43f0e9519a5f) (`horizon-wine/source/thread_profile.c/h`, `dlls/ntdll/unix/thread.c`). The project narrows eligibility to `dxvk-cs`, retains its stable balancer, and adds readback logs, separate role metadata and failure recovery. This is adapted upstream design/code under LGPL-2.1-or-later, not wholly original work. |
| Autorun references | Thread placement, synchronization and configuration were studied against pinned Autorun source. The [thread/CPU audit](https://github.com/Ibnuard/pes13_nx/blob/65f6962f49381e08ab71a1b87c9f2efcff8e49d5/docs/AUTORUN-THREAD-CPU-AUDIT-2026-09-28.md) distinguishes implemented behavior from unimplemented proposals. Referencing those designs does not mean their entire implementation was copied. |
| Upstream FEX-Emu | The CPU translator, JIT and upstream WOW64 implementation come from FEX-Emu and are built with Horizon-specific patches. FEX-Emu itself was not created by this project. Its [pinned WOW64 module](https://github.com/FEX-Emu/FEX/blob/e2f973fe931e6dc2ce523795e51ca1ac3ca85816/Source/Windows/WOW64/Module.cpp) also acknowledges André Zwing's Hangover work; that acknowledgement remains with the upstream source. |
| FEXTendo's FEX-Emu port to Nintendo Switch | AndroSwitch Project / Ibnuard developed the Switch host adapter, Horizon JIT-memory interface, PE-to-native callback wrapper, Wine exception integration, project profiles and guest test programs, with integration/build patchers. The initial adapter and guest validation are recorded in [commit 88b6a2f](https://github.com/Ibnuard/pes13_nx/commit/88b6a2f267ae01bc8d4f8f35fb31df865800f67a). The build uses pinned upstream FEX source and applies this repository's adapter and patches. This work extends FEX and the inherited Wine-NX runtime, including its existing native-to-PE callback machinery. The [source map](https://github.com/Ibnuard/pes13_nx/blob/65f6962f49381e08ab71a1b87c9f2efcff8e49d5/docs/FEX-PORT-PROVENANCE.md) identifies those boundaries. Project adapter code is MIT where marked; patched upstream files retain their notices. |
| FEX diagnostic sampler adaptation | The optional FEX-aware context sampler adapts the inherited Wine-NX profiling machinery to FEX register/frame metadata. The profiler foundation remains Wine-NX code; the FEX-specific mapping is an integration change, under LGPL-2.1-or-later. |
| Original FEXTendo launcher | [src/runtime/fextendo_*.h](https://github.com/Ibnuard/pes13_nx/tree/65f6962f49381e08ab71a1b87c9f2efcff8e49d5/src/runtime) implements the native menu, renderer, focus/scroll animation, preset handling, generated audio cues, Last played history and timestamp overlay. It does not enter or copy Wine-NX's SDL launcher. The overlay uses libnx's VI protocol; [libnx VI](https://github.com/switchbrew/libnx/blob/master/nx/source/services/vi.c) and [libtesla's layer-stack setup](https://github.com/WerWolv/libtesla/blob/master/include/tesla.hpp) were engineering references. |
| Direct runtime dependencies | The package retains matched Wine modules, fonts/NLS data and DXVK DLLs from the pinned Wine-NX release payload where recorded by packaging manifests. Mesa, libnx and portlibs are linked dependencies. Building or packaging these does not make them original project code. |

PES-specific runtime changes use LGPL-2.1-or-later unless marked otherwise;
the new FEX adapter uses MIT. The complete project licenses are [LICENSE](https://github.com/Ibnuard/pes13_nx/blob/65f6962f49381e08ab71a1b87c9f2efcff8e49d5/LICENSE)
and [src/fex/LICENSE](https://github.com/Ibnuard/pes13_nx/blob/65f6962f49381e08ab71a1b87c9f2efcff8e49d5/src/fex/LICENSE). Dependency revisions are recorded in
[dependencies.json](https://github.com/Ibnuard/pes13_nx/blob/65f6962f49381e08ab71a1b87c9f2efcff8e49d5/dependencies.json), the FEX build recipes and package receipts.

## Upstream components

Sleeping Dogs v9 additionally adapts Autorun commits
[`5a75cfb647a0`](https://github.com/autorunhq/autorun/commit/5a75cfb647a010704a2811f535323fc4b39c9109),
[`e823a778f5cc`](https://github.com/autorunhq/autorun/commit/e823a778f5ccf40ae8392209b9ff769b42780c14), and
[`e7168c3f438a`](https://github.com/autorunhq/autorun/commit/e7168c3f438ace433c4e77da2cb4533762a77399)
for shader affinity and temporary allocation reuse. The adaptation uses
FEXTendo's existing stable balancer and Mesa/Rust allocation recovery shims.
Adapted sources are marked LGPL-2.1-or-later; the project's allocator helpers
retain MIT. This does not import or replace FEXTendo's independently developed
Switch FEX integration inherited from `pes13-fex`; that integration's engine
is upstream FEX-Emu. See [the Sleeping Dogs v9 record](low-window-shader-optimizations.md).

| Component | Attribution | License / source |
| --- | --- | --- |
| Wine / Wine-NX / Autorun | Wine authors; danfromtico and Autorun contributors | LGPL-2.1-or-later; [pinned source](https://github.com/danfromtico/wine-nx/tree/1bc4e45163f0d2328cdfd35c7f471dd9821bb879) |
| Box64 | ptitSeb and contributors | MIT; [pinned source](https://github.com/ptitSeb/box64/tree/dae0917c47b4edd8956f314210417a20fd225c4b) |
| FEX-Emu | Ryan Houdek and FEX contributors | MIT; [pinned source](https://github.com/FEX-Emu/FEX/tree/e2f973fe931e6dc2ce523795e51ca1ac3ca85816); upstream dependencies retain their individual licenses |
| DXVK | Philip Rebohle, Joshua Ashton, Robin Kertels, Jeffrey Ellison and contributors | zlib/libpng; legacy Wine-NX payload at `878473ba`; FEX3 trial baseline uses the official [v3.1.1 release](https://github.com/doitsujin/dxvk/releases/tag/v3.1.1). Exact DLL hashes are recorded in package manifests. |
| DXVK-Sarek (opt-in renderer trial) | DXVK authors; pythonlover02 and Sarek contributors | zlib/libpng; unmodified PE32 D3D9 from [v1.13.0](https://github.com/pythonlover02/dxvk-sarek/releases/tag/v1.13.0), commit `37f397e142b977a343e920dbc4c7bf7ed2c63a81`. The project supplies configuration and packaging, not the Sarek renderer or dyasync implementation. |
| DXVK-GPLAsync (opt-in renderer trial) | DXVK authors; Ph42oN; Sporif and prior async-patch contributors | DXVK zlib/libpng notices retained; unmodified PE32 D3D9 from [v2.7.1-1](https://gitlab.com/Ph42oN/dxvk-gplasync/-/releases/v2.7.1-1). Release recipe/patch commit `209a3069a19d13efb019e111f27114c185e86092` applies to upstream DXVK `c3dd74be6baec53786d4e064a572185b70347a17`. This project supplies configuration, validation and packaging, not DXVK or its async implementation. |
| Mesa / mesa-switch | Mesa authors; danfromtico, NaGaa95 and contributors | Mostly MIT, individual source licenses apply; [pinned source](https://github.com/danfromtico/mesa-switch/tree/b297e230ef88c6c88df2561becf864f979f494a6) |
| libnx | switchbrew and contributors | ISC; [source](https://github.com/switchbrew/libnx) |
| SDL2 / SDL2_ttf | Sam Lantinga and contributors | zlib; [source](https://github.com/libsdl-org) |
| FreeType | The FreeType Project | FTL or GPL-2.0; [source](https://freetype.org) |
| HarfBuzz | HarfBuzz authors | MIT; [source](https://github.com/harfbuzz/harfbuzz) |
| libdrm_nouveau | Mesa/libdrm authors and Switch port contributors | MIT, per source; devkitPro portlib |
| libpng / zlib / bzip2 | Their respective authors | libpng / zlib / BSD-style, respectively |
| Expat / Zstandard | Their respective authors | MIT / BSD-or-GPL dual license, respectively |
| devkitA64 / llvm-mingw / Rust | devkitPro, GCC, LLVM, mingw-w64 and Rust contributors | Toolchain components retain their respective licenses |

Wine fonts and NLS files are retained from the matched release dependency
package. Their source and notices are in the Wine tree. The upstream source
also contains Wine-NX's launcher implementation; PES13-NX starts PES directly
and does not enter that launcher. The Wine-NX launcher design acknowledges
[dolphin-nx](https://github.com/NaGaa95/dolphin-nx); its implementation is Wine-NX code.

[Sphaira](https://github.com/NaGaa95/sphaira), by ITotalJustice, NaGaa95 and
contributors, supplies the forwarder configuration used for the hardware run.
No Sphaira binary is included in the public PES13-NX package.

The new adapter under `src/fex/` and its JIT probe test are MIT-licensed; see
`src/fex/LICENSE`. The standalone FEX1 probe package includes the FEX MIT and
libnx ISC notices. Its retained libnx notice comes from the
[upstream license](https://github.com/switchbrew/libnx/blob/master/LICENSE.md).
The full experimental FEX DLL is not included in the FEX1 probe. The FEX2
integration test includes that DLL, matched Wine modules and their license
notices, plus notices from FEX's retained dependencies. Its x86 smoke program
is original MIT-licensed test code, not a game executable.

The earlier Fextendo v1 launcher uses Barlow Regular and SemiBold, copyright
2017 The Barlow Project Authors, under SIL Open Font License 1.1. Source:
[Google Fonts / Barlow](https://github.com/google/fonts/tree/main/ofl/barlow).
The full notice is in `assets/fonts/OFL.txt` and `licenses/Barlow-OFL.txt` in
the Fextendo package. The native launcher does not enter Wine-NX's SDL menu.

The Fextendo experimental package includes the launcher artwork supplied by
the user (`PES13WP.jpg`, `logo.png`, and `icon.png`); rights remain with their
respective owners. Game executables, match data and saved games are not
included. The font and source-code licenses do not license the PES artwork.

FEXTendo v2 and later use Inter (The Inter Project Authors) under SIL OFL 1.1:
`assets/fonts/Inter/OFL.txt`, packaged as `licenses/Inter-OFL.txt`.
The user-supplied Solid Duo controller sprites retain their original rights;
they are not covered by the source-code or font licenses. V2's generated
stadium, flat gamepad and FEXTendo wordmark have provenance and prompts in
`assets/fextendo-v2/GENERATION.md`.

FEXTendo v3.2 adds independently synthesized mallet-style cues and an original
16-second ambient loop, with no third-party audio samples or tracks. Its flat
Settings/Credits images were generated for this project; the exact prompts and
method are in [assets/fextendo-v3.2/GENERATION.md](https://github.com/Ibnuard/pes13_nx/blob/65f6962f49381e08ab71a1b87c9f2efcff8e49d5/assets/fextendo-v3.2/GENERATION.md).
The new default-display capture uses libnx as a linked dependency and the
[libnx default-window lifecycle](https://github.com/switchbrew/libnx/blob/master/nx/source/display/default_window.c)
as a reference. It borrows the application display and preserves libnx ownership.

FEXTendo 0.3.8-r6 includes an adapted libnx virtual-address manager in
`src/runtime/fextendo_virtmem.c`, retaining switchbrew/libnx authors' ISC notice
in that source and `licenses/libnx-LICENSE.md.txt`. It adds an exhaustive search
after random placement fails; source provenance/digest are recorded in the file.

Runtime Fixer links devkitPro's Switch libcurl (7.69.1, libnx TLS backend) and
MiniZip for manual HTTPS download and ZIP extraction in the launcher. Notices
are retained in `licenses/curl-COPYING.txt` and `licenses/minizip-NOTICE.txt`.
The compressed data uses the existing zlib dependency. The build report pins
the exact linked libcurl/MiniZip archives independently of the Wine/FEX runtime.
