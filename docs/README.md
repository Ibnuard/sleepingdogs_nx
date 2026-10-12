# Documentation

[Project home](../README.md)

These guides describe the current Sleeping Dogs FEXTendo port. Start with
installation for a first setup, or current status before comparing test builds.

| Guide | What it covers |
| --- | --- |
| [Installation](INSTALL.md) | Required game edition, complete packages, forwarder, SD layout and updates |
| [Settings](CONFIGURATION.md) | DXVK profiles, Light 720p game detail, HUD, FEX, resolution and optional LSFG |
| [Troubleshooting](TROUBLESHOOTING.md) | Startup failures, graphics labels, logs and useful performance reports |
| [Current status](STATUS.md) | Confirmed gameplay, measured results, limitations and work still under investigation |
| [Building](BUILD.md) | Local prerequisites, baseline versus v18 recipes, validation and packaging |
| [Native DXVK probe](native-dxvk-probe-v1.md) | ARM64 build, host correctness tests, standalone Horizon NRO and remaining game integration |
| [Native DXVK H2](native-dxvk-h2-v1.md) | Real PE32 guest bridge diagnostic, hardware test instructions and v18 restoration |
| [Native DXVK H3](native-dxvk-h3-v1.md) | Successful Switch guest-driven native Present capture, folder installation and production gates |
| [Native DXVK H4 v8.1](native-dxvk-h4-v8.1-transport.md) | Current candidate and subsequent Light capture: 20–22 FPS reported, crowded lows near 16; remaining bridge, Map and submission candidates |
| [Native DXVK H4 v8](native-dxvk-h4-v8-game-detail.md) | Map reuse and Light 720p introduction; later normal-settings feedback 17–20 FPS |
| [Native DXVK H4 v7](native-dxvk-h4-v7-objects.md) | Hashed proxy lookup and inline arrays; subsequent user report around 20 FPS, crowded-running lows near 13 |
| [Native DXVK H4 v6](native-dxvk-h4-v6-dispatch.md) | Reduced diagnostic cost; subsequent user report 16–17 FPS, crowded view 12–13 |
| [Native DXVK H4 v5](native-dxvk-h4-v5-com-outputs.md) | Scalar DSV and COM output fixes; user subsequently reports gameplay around 15 FPS |
| [Native DXVK H4 v4](native-dxvk-h4-v4-logging.md) | Queued native logs and compact progress; subsequently reaches Press Start then crashes |
| [Native DXVK H4 v3](native-dxvk-h4-v3-sponsor.md) | Previous FIFO/startup trace candidate and v2 observations |
| [Native DXVK H4 v2](native-dxvk-h4-v2-window.md) | Startup screen-handoff fix and original COM-first Switch validation |
| [Native DXVK H4 implementation](native-dxvk-h4-v1.md) | Original x86 COM proxies, native ARM64 launcher/game route and local validation boundaries |
| [Contributing](../CONTRIBUTING.md) | Reporting a problem, submitting changes and keeping evidence reproducible |
| [Credits and licenses](../THIRD_PARTY.md) | FEXTendo's FEX port, upstream dependencies and adapted code |
| [Development history](HISTORY.md) | Index of every version-specific investigation and build note |

## Reading the older notes

Files such as `low-window-*.md`, `native-v15-lsfg.md` and `apc-v18.md` are
records of individual experiments. Their installation steps, "latest" labels
and hardware-validation status reflect when each experiment was prepared.
Use [Current status](STATUS.md) for subsequent hardware results.

Those files keep their existing paths so source receipts, package scripts and
old links remain traceable. The previous long README is preserved separately
as [Legacy project notes](LEGACY-PROJECT-NOTES.md).

`dist/` and `local/` are generated workspace directories, excluded from Git.
An artifact named in a historical note is not necessarily available on GitHub.
The inherited [PES13 notice snapshot](PES13-THIRD-PARTY.md) is retained for
attribution; [THIRD_PARTY.md](../THIRD_PARTY.md) describes this project's scope.
