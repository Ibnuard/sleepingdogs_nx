# Contributing

Start with the [project README](README.md), [current status](docs/STATUS.md)
and [build guide](docs/BUILD.md). This port currently targets the original
x86 Sleeping Dogs PC game.

## Report a problem

Use a [GitHub issue](https://github.com/Ibnuard/sleepingdogs_nx/issues/new/choose)
and describe the expected result, actual result and steps to reproduce it.
Include the exact build/package, device model, boot/forwarder setup, clocks,
renderer, resolution, graphics profile and LSFG setting.

Save the runtime log before another launch replaces it. For a performance
report, compare the same warmed scene and camera with LSFG OFF and record any
clock changes during the session. See [log locations and comparison guidance](docs/TROUBLESHOOTING.md).
Attach diagnostic logs and relevant screenshots rather than game files or keys.

## Submit a change

Keep a change focused on one behavior so its effect can be compared. Preserve
upstream attribution, approved build inputs, rollback artifacts and existing
user settings. Prepared source trees belong in isolated build directories;
do not silently replace dependencies used by a recorded baseline.

Explain the problem and resulting behavior in the pull request. State which
host, ARM64, package and hardware checks were actually run, including source
or binary identities where needed. A passing host test is not a Switch FPS
result. Performance claims should identify native versus generated frames,
scene, resolution and clocks.

For documentation, update the relevant current guide and its index. Keep
historical experiment paths stable because packaging scripts and receipts
refer to them. Add later outcomes to [Current status](docs/STATUS.md) rather
than rewriting an old test result as if it had been known at build time.

For a new dependency or backport, update [THIRD_PARTY.md](THIRD_PARTY.md) and
the matching source/build records. Generated `dist/` and `local/` content,
game data, proprietary personal-test shader payloads and keys stay outside
ordinary source commits.
