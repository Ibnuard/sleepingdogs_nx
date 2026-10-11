# Documentation

[Project home](../README.md)

These guides describe the current Sleeping Dogs FEXTendo port. Start with
installation for a first setup, or current status before comparing test builds.

| Guide | What it covers |
| --- | --- |
| [Installation](INSTALL.md) | Required game edition, complete packages, forwarder, SD layout and updates |
| [Settings](CONFIGURATION.md) | DXVK profiles, HUD, FEX, resolution and optional LSFG |
| [Troubleshooting](TROUBLESHOOTING.md) | Startup failures, graphics labels, logs and useful performance reports |
| [Current status](STATUS.md) | Confirmed gameplay, measured results, limitations and work still under investigation |
| [Building](BUILD.md) | Local prerequisites, baseline versus v18 recipes, validation and packaging |
| [Native DXVK probe](native-dxvk-probe-v1.md) | ARM64 build, host correctness tests, standalone Horizon NRO and remaining game integration |
| [Native DXVK H2](native-dxvk-h2-v1.md) | Real PE32 guest bridge diagnostic, hardware test instructions and v18 restoration |
| [Native DXVK H3](native-dxvk-h3-v1.md) | Guest-driven native swapchain/Present diagnostic, folder installation and timing limits |
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
