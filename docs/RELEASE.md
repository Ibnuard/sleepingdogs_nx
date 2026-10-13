# GitHub package and release pipeline

The workflow follows the PES13-FEXTendo model: build/test the Horizon runtime
in the prepared workspace, freeze an approved runtime input, then package it
on GitHub. GitHub Actions does **not** rebuild Wine, FEX, Mesa or the NRO from a
clean checkout. The runtime is pinned by archive SHA-256, exact file inventory
and source fingerprints in [runtime-lock.json](../release/runtime-lock.json).

## Jobs

- [Validation](../.github/workflows/validate.yml) runs on relevant pushes and
  PRs with read-only permissions. It rejects tracked binaries/private payloads,
  stale runtime sources, and tests package/publication guards. Pinned existing
  FEX modules and DXVK archives remain as licensed vendor inputs; archive members
  are inspected too. No secrets are exposed to pull-request code. Pushes also
  rehearse the complete package and retain an artifact without publishing a release.
- [Release packaging](../.github/workflows/release.yml) runs only for a closed,
  **merged** PR targeting this repository's `main`. Checkout uses the exact
  `merge_commit_sha`, with credentials persistence disabled. Its token is
  read-only. It downloads the approved runtime asset, verifies its SHA-256,
  checks the inventory and assembles the SD layout.
- The dependent publication job has `contents: write`, rechecks the downloaded
  package, creates the release tag at that same merged commit, uploads to a
  draft, then publishes. Published assets are never overwritten; a rerun must
  match their hashes. GitHub generates the changelog from merged changes.

Actions are pinned to full commit SHAs. The closed-PR event alone is insufficient:
the CLI also checks merged state, base branch/repository and commit format.

## Assets

Each release contains the complete `SleepingDogs-FEXTendo-v0.1.1-sd.zip`,
standalone `sleepingdogs-fex.nro`, the matching memory forwarder NSP,
`manifest.json` and `SHA256SUMS`. Version 0.1.1 uses the same stable version
for the release tag and NRO. Earlier `-pN` runtime inputs retain the package
`-rN` naming convention. Published assets remain immutable.

The SD package includes Wine/FEX modules, renderer sets, launcher resources,
Wine fonts/NLS data, configuration, notices and matching modified source units.
The NRO embeds the small startup config defaults and restores them if absent;
they do not depend on an extracted dot folder or zero-byte archive member.
Game executables/data, saves, keys, `lossless.dll`, `LosslessScaling.dll` and
proprietary LSFG shader packs are rejected. The packager uses explicit paths;
it never mirrors a game directory or an SD card. Source and evidence directories
are also checked for disguised private binary file types.

## Updating the input

Run the [production recipe](production-v1.md) and all its tests first. Prepare a
new runtime archive and commit its lock together with source changes. Upload
that exact archive to the lock's dependency release tag. This first input uses
the **prerelease** `runtime-production-v1` dependency release, marked non-Latest.
It stores the CI input and is not the final player-facing release. Publishing
the dependency lets the packaging job use a read-only token; GitHub restricts
draft visibility to users with push access ([API reference](https://docs.github.com/en/rest/releases/releases#list-releases)).

Verify the downloadable bytes before pushing the final PR. Source changes
without a matching rebuilt runtime intentionally fail CI. Never replace the
asset under an already used immutable lock; create a new versioned input.
The 0.1.1 input is published as the `runtime-v0.1.1` prerelease dependency.

To reproduce packaging locally (Python standard library only):

```sh
python3 -m unittest discover -s tests -p 'test_release_*.py' -v
python3 tools/check_release_repository.py
python3 tools/release_package.py --runtime /path/to/pinned-runtime.zip \
  --output dist/release-check --version v0.1.0-r1 --commit FULL_40_CHAR_COMMIT
```

Add `--folder-only` for a ready-copy local folder instead of release archives.
Do not merge a PR solely to test publication. Packaging validation and the
preceding gameplay report do not replace a Switch test of the final NRO.
