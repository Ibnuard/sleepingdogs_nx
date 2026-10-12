# FEX context v1: exact x87 import shortcut

[Documentation](README.md) · [Current status](STATUS.md)

This is a **FEX-side performance candidate for the installed native H4 v9
runtime**, at 1280×720. The subsequent capture below confirms activation. The
ready-copy directory is `dist/sd-fex-context-v1-update/`; no ZIP is produced.

The [subsequent gameplay capture](../reports/fex-context-v1-gameplay-observation.json)
contains the FEX context v1 marker and Light 720p. The user reports a slight
improvement, ordinary views at 20–23 FPS, crowded lows around 16 and narrow-view
peaks of 30. Its final five complete Present windows pool to 20.56 FPS. Scenes
and clocks are not authenticated as a matched A/B; this does not establish a
large measured gain. The next [Native Ref v1 experiment](native-dxvk-ref-v1.md)
targets avoidable COM crossings while retaining this FEX DLL.

## Why investigate outside DXVK

The [new v9 capture](../reports/native-dxvk-h4-v9-gameplay-observation.json)
confirms native DXVK, Light 720p, the memory changes and batching ON. The last
five complete Present windows pool to **20.59 FPS**, versus **20.67 FPS** for
the v8.1 reference. Scenes and clocks are not authenticated as a matched A/B,
but neither the capture nor the user's feedback shows a meaningful gain.
The supplied `runtime.log` is again the byte-identical older v3 COM file.

One later interval has about 9,182 COM calls, 1,494 draws and 9 MiB of Map
copies per Present. Zero active maps at the two endpoints does not mean no
maps occurred between them. These counts indicate recurring work; they do
not attribute frame time to FEX, Wine, DXVK, the GPU or waiting.

The source audit follows the actual installed FEX/Wine route:

- Every FEX Unix call serializes the guest context before calling native Wine
  and restores it afterward. That includes all eight x87 registers, even when
  the callee is native DXVK. The pinned adapter converts the Fastest profile's
  internal binary64 values to extended format and back. The upstream
  [WOW64 handler](https://github.com/FEX-Emu/FEX/blob/e2f973fe931e6dc2ce523795e51ca1ac3ca85816/Source/Windows/WOW64/Module.cpp)
  also preserves the context boundary; native DXVK does not remove it.
- `LockJITContext`/`UnlockJITContext` manage the simulation/suspend protocol;
  their names do not identify a contended mutex. Removing them or skipping
  context restoration would compromise callbacks and remote context changes.
- Disassembly of the retained Wine NRO shows `NtCurrentTeb` passing through
  `pthread_getspecific` to libnx `threadTlsGet`: a thread-local slot load,
  without a mutex on this path. This audit does not justify a Wine TLS rewrite.
- QPC/delay fast handling and the v17 automatic Wine scheduler are already
  active. Native DXVK workers have mask `f` and are outside the guest registry;
  that alone does not prove a placement problem. Late compile statistics do
  not show persistent heavy JIT compilation and do not measure translated game
  execution. Changing compiler presets or allocator budgets is not justified
  by those counters alone.

## Exact change

The owned [helper](../src/fex_context/exact_x87.h) recognizes normalized
extended values that are exactly representable in binary64: the exponent is
in the normal binary64 range, the explicit integer bit is set, and the low
11 significand bits are zero. Integer shifts construct the same output for
all four rounding modes. Signed zero also has a short path.

Subnormals, NaNs, infinity, unsupported extended encodings and values needing
rounding retain the pinned conversion. No host FP conversion or fast-math is
used. Full-precision mode keeps the existing serialization behavior. Guest
precision, MXCSR, register rotation, debug registers, callbacks, suspend/APC,
memory ordering and the JIT itself are unchanged.

The build reuses the pinned FEX objects after reproducing the delivered DLL
byte-for-byte with its original PE timestamp and Wine builtin marker. It
recompiles the FPU adapter and the module's startup banner in a private
directory. The existing FEX, Wine, SDK and PES13 source trees are not edited.
The NRO, DXVK, graphics settings and native COM proxies remain the installed
v9 versions, which makes the FEX comparison easier to interpret.

## Validation and limits

- **9,698,949 host checks** pass with ASan/UBSan, including all extended
  exponents/signs across selected significand boundaries, all rounding modes,
  random extended and binary64 cases, TOP rotation, both precision modes and
  output canaries. An independent host x87 oracle covers 160,000 conversions.
- The actual ARM64 PE functions from both DLLs execute in Unicorn, with
  numerical equality, stack/buffer guards, callee-preserved registers and
  Wine's x18 checked. No conversion function is replaced with a host stub.
- Representative eight-register import instruction counts are 433 → 198 for
  normal exact values, 209 → 134 for zeros and 335 → 296 for a special-value
  mixture. A general extended-value case increases from 522 → 631 because
  it needs the fallback. These are emulator instruction counts, **not cycles
  or FPS**. Host CPU timing also has slower zero/general cases; it is not an
  ARM Cortex-A57 benchmark.

The caller's Fastest export normally produces exact binary64-derived values,
which motivates the shortcut. The actual game's register-value distribution
and the share of frame time spent here are not measured. A local helper
speedup does not establish a large gameplay improvement or stable 30 FPS.
Wine scheduling and the complete callback/suspend path require hardware
testing; they are not exercised by the isolated conversion emulator.

## Install and compare

Use an existing **native H4 v9** installation. Do not copy all subfolders at
once; they are alternative states for the same FEX DLL.

1. Close the application from HOME. Copy the main `switch/` folder to the SD
   root. This installs the candidate FEX and the unchanged v9 COM client,
   then selects the COM test. Require a fresh PASS and exit `00000000`, and
   `[SD-FEX-CONTEXT] v1 exact x87 import` in its runtime log. The NRO/result
   build still says `native-dxvk-h4-v9` because that component is unchanged.
2. Save `drive_c/native-dxvk-h4-result.json`, `drive_c/native-dxvk-h4-guest.log`
   and `native-dxvk-h4/runtime.log`, relative to `switch/sleepingdogs-fex/`.
   Do not start the game if the COM test fails.
3. Close from HOME and copy `start-game-light/switch/`. Use Native ARM64,
   Performance, Light 720p, the same HUD and the same clocks as the reference
   (previously CPU 1728 / GPU 768 / RAM 1600 MHz).
4. Compare the same warmed location and camera for 30–60 seconds, then the
   same crowded route. Preserve the logs before relaunch. Check pause/resume
   and clean exit as well as FPS.
5. `fex-baseline/switch/` restores the **exact previous FEX DLL** and selects
   gameplay, keeping the other settings. `fex-fast/switch/` reapplies the
   candidate for a second run. Fully close from HOME between copies. The main
   update already installs fast; `fex-fast` is only needed after baseline.

For each game run send `fex-runtime.log` and
`native-dxvk-h4/HKShip.exe_d3d11.log`, plus a new crash log if one appears.
The `[SD-FEX-CONTEXT]` marker identifies the candidate; the baseline lacks it.
No batching overlay is needed for this experiment. Keep batching fixed for
both runs. `fex-baseline` is also the rollback if the candidate regresses.

## Rebuild

Prepared dependencies remain required; see [Building](BUILD.md).

```text
# WSL, repository root
python3 tools/build_fex_context.py
python3 tools/test_fex_context.py
# Windows Python with pefile and Unicorn, repository root
python tests/fex_context_arm64.py
# WSL after the matching reports are present
python3 tools/package_fex_context.py
```

The package requires matching source/binary/test hashes, carries the changed
sources and patches, and verifies its checksum manifest. Existing v8.1/v9
folders and all game data/saves are preserved.
