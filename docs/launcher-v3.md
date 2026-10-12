# Launcher v3: guest binding filter and FIFO LSFG fix

[Documentation](README.md) · [Status](STATUS.md)

The [supplied launcher-v2 capture](../reports/launcher-v2-game-2d5516526c0a.json)
requested LSFG ON at 50% motion and attached the native swapchain, but **5,034
Presents bypassed interpolation**. There were no initialization or generated-frame
markers. DXVK reported FIFO. Gameplay windows of 600 real Presents were around
18.4–23.1 FPS. These are scene-dependent windows, not a paired benchmark.
The supplied `runtime.log` is still an older H4 v3 COM test.

## Real-FPS candidate

Native State v1 caches the exact last arguments of 25 independent context
binding setters in the PE32 proxy: six shader stages' constant buffers,
samplers and shaders without class instances, input layout, topology,
rasterizer state, blend/depth-stencil state, viewports and scissors. Identical
bindings return before Wine/FEX transport. Changed bindings still execute
synchronously, with the existing native pointer/token checks.

Array **contents** and full token generations form the keys. Partial and
overlapping calls replace the last key; invalid/unsupported shapes fall back.
ClearState, ExecuteCommandList and FinishCommandList invalidate all keys,
regardless of restore flags. Reentrant mutation prevents publishing stale keys.
A second thread binding the same context permanently disables its cache.
There is no lock held across native dispatch. The cache owns no COM references
and is freed with its context proxy; allocation failure uses the ordinary path.
Only contexts allocate about 10 KiB each.

Resource hazards, SRV/UAV/render-target bindings, IA buffers, stream output,
predication, draws/dispatches and Map/Unmap are **not filtered**. Buffer contents
and the full Map copy remain unchanged. Context1 and later interfaces are not
exposed by this bridge; the generator rejects adding those interfaces without
revisiting state invalidation. The shader/constant-buffer binding and reset
semantics are described by Microsoft's
[PSSetShader](https://learn.microsoft.com/en-us/windows/win32/api/d3d11/nf-d3d11-id3d11devicecontext-pssetshader),
[PSSetConstantBuffers](https://learn.microsoft.com/en-us/windows/win32/api/d3d11/nf-d3d11-id3d11devicecontext-pssetconstantbuffers)
and [ClearState](https://learn.microsoft.com/en-us/windows/win32/api/d3d11/nf-d3d11-id3d11devicecontext-clearstate).

`[SD-NDX-STATE]` records attempts, skipped calls, disabled contexts and skipped
CB/sampler/shader/fixed-state groups every 600 real Presents. This measures
actual skipped crossings on hardware; a skipped-call count alone is not FPS.
The retained Compact COM, local reference credits, FEX x87 shortcut and native
DXVK batching are unchanged. There is **no measured v3 Switch speedup yet**.

## LSFG correction

The previous backend rejected every `VkSwapchainPresentModeInfoEXT`, even a
FIFO override. V3 accepts FIFO, tracks the mode across calls without an
override, and still bypasses non-FIFO modes. Vulkan specifies that the chosen
mode persists to subsequent operations; see
[VkSwapchainPresentModeInfoKHR/EXT](https://docs.vulkan.org/refpages/latest/refpages/source/VkSwapchainPresentModeInfoKHR.html).
Bypass logging is throttled. A generated Present copies only the mode override;
the game's present fence, ID and result storage belong to the real Present.
Terminal errors after consumed work take precedence over later mode changes.

The real host test now exercises FIFO metadata together with a present fence,
including checking that the caller's pNext chain remains unchanged. All four
generating sessions pass with zero Vulkan validation errors. This fixes the
observed rejection, but does not establish Switch generation, scanout quality
or an FPS benefit. GPU frame generation adds work; the HUD counts real frames.

## Install and compare

Close fully from HOME. Copy **only the top-level `switch/`** from
`dist/sd-launcher-v3-update/` to the SD root and replace files. No `start-game`
overlay is needed for normal installation. Mandatory Light 1280×720, cached
verification, active low-memory checks, PES13 keyboard and hidden Debug remain.
The saved LSFG setting is preserved.

Measure real FPS with LSFG **OFF**, CPU/GPU/RAM **1728/768/1600 MHz**, after
warmup, on the same route and camera. Optional `performance-off/switch/`
installs the previous Compact proxy on the same v3 NRO; `performance-on/`
restores the new filter. Both hashes are accepted by the checker. These
overlays change both the selected renderer source and active game-side proxy.
`rollback-launcher-v2/switch/` restores the prior paired NRO/proxy.

Test LSFG ON separately, initially at 12.5% motion, keeping game resolution at
720p. Confirm `first interpolated present submitted` and the subsequent
`real=... generated=...` counters in `fex-runtime.log`; ON is not proof of
generation. Send that log and `HKShip.exe_d3d11.log` separately for OFF and ON.

## Validation scope

- Actual PE32 wrappers: all 25 methods, 20,000 randomized overlapping sampler
  bindings, in-place array/viewport/scissor mutation, token generations,
  class-instance fallback, reset/restore boundaries, reentrant calls, failed
  transport, thread migration and allocation fallback. The endpoint is modeled.
- Native DXVK/lavapipe regression: 7,387,186 checks, 1,843,200 readback pixels,
  buffers/mips, 60 Presents, 2,000 concurrent reference pairs and clean resource
  teardown. This tests the native dispatcher separately from the PE cache.
- Real native/Wine LSFG routes: four generating sessions, including FIFO
  pNext plus real present fences; zero Khronos validation errors.
- ASan/UBSan launcher/cache/keyboard, acquired-image and present-mode policy
  regressions; compact codec; seven linked ARM64 heap-gate scenarios.

Build with `tools/build_native_dxvk_state.py` then `tools/build_launcher_v3.py`
in the prepared WSL environment. Run the matching state, native-host, launcher,
LSFG and binary tests before `tools/package_launcher_v3.py`. Generated sources,
source hashes and reports accompany the private folder. The personal LSFG
shader pack is excluded from GitHub; no public release or ZIP is created.
