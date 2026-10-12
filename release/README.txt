SLEEPING DOGS / FEXTENDO - PRODUCTION

Existing working installation:
Close the application fully from HOME. Copy only the main switch/ folder to
the SD root and replace matching files. No start-game folder is needed.
Keep the current game, saves and private LSFG shader pack. This package does
not contain lsfg.txt and therefore does not change the saved LSFG preference.
The default renderer is DXVK Native ARM64; Light 1280x720 is always applied.

Fresh installation:
Copy switch/ to the SD root. Supply your own original x86 Sleeping Dogs PC
game in switch/sleepingdogs-fex/drive_c/SleepingDogs/. Keep the package's
d3d9.dll, d3d11.dll, dxgi.dll, sdndx4.dll and dxvk.conf when names overlap.
The x64 Definitive Edition is unsupported. A valid original
Data/DisplaySettings.xml is required; the launcher creates its own backup.
Install the matching FEXTendo-SleepingDogs-39bit-FEXTendoMemory-v1.nsp once.
The corresponding low-memory kernel/loader patch must already be active.
The NSP alone does not install that patch. Use the HOME forwarder, not Album.

Normal Play writes no diagnostic logs. System settings, verification cache,
registry, shader caches, game saves, recovery state and last played remain
functional. Last played is recorded after the first successfully presented
frame. Old logs from earlier installations are left untouched.

For troubleshooting only: Settings > Show debug launch, then Launch Debug.
That explicit path can write runtime/crash/DXVK logs. DXVK HUD works without
enabling Debug. The complete runtime is checked once after an update; later
launches use the verification cache while checking the active memory patch.

No game executables, game archives, saves, keys, lossless.dll, LosslessScaling.dll
or proprietary LSFG shader pack are included. LSFG is optional and requires
the user's compatible personal shader pack. Source, evidence and licenses
are for reference and do not need to be copied to the SD card.

Build and host tests passed; production-v1 still needs validation on Switch.
Previous gameplay confirmation does not establish a stable FPS target.
Documentation: https://github.com/Ibnuard/sleepingdogs_nx
