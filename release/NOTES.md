## 0.1.1 — Fix failed launch caused by missing startup configuration

- Fix launch returning to the launcher when `.pandora` startup configuration was omitted during copying or extraction.
- Embed the three startup defaults in the NRO and restore missing files automatically during System Check and before Play, including the intentional zero-byte `local` file.
- Preserve existing user configuration. Show a clear error if the SD card cannot read or restore a required file.
- Existing installations can update `sleepingdogs-fex.nro`; the current memory forwarder remains compatible.

Validated with host recovery tests, production regressions, linked ARM64 checks and full package verification. The missing-config cause was confirmed on an affected user's installation; the rebuilt NRO still needs a Switch launch test.
