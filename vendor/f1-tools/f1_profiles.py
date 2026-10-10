"""DXVK profiles for the F1 build with the verified 39-bit bootstrap.

Keep the original profile indices stable; append Performance at index 4.
The memory advertisements match the successful 0.1.28-as39t1 device log.
They describe the adapter to the game, not a physical allocation limit.
"""
PROFILES = ("balanced", "low-latency", "stable", "quality", "performance")


def profile_config(profile: str, async_mode: bool) -> str:
    if profile not in PROFILES:
        raise ValueError(f"Unknown F1 profile: {profile}")
    vsync, latency, anisotropy = {
        "balanced": (1, 2, -1),
        "low-latency": (0, 1, -1),
        "stable": (1, 2, 0),
        "quality": (1, 2, 4),
        "performance": (0, 3, 0),
    }[profile]
    lines = [f"# F1 2013 / 39-bit / {profile}",
             "# Adapter hints from the successful circuit test; not RAM caps.",
             "dxgi.maxDeviceMemory = 256", "dxgi.maxSharedMemory = 64",
             "dxvk.numCompilerThreads = 1",
             "dxvk.enableDescriptorBuffer = False",
             "dxvk.enableDescriptorHeap = False",
             "# The launcher appends the separately saved HUD choice on Play.",
             "dxvk.hud =",
             f"d3d9.presentInterval = {vsync}", f"dxgi.syncInterval = {vsync}",
             f"d3d9.maxFrameLatency = {latency}", f"dxgi.maxFrameLatency = {latency}",
             "d3d9.maxFrameRate = -1", "dxgi.maxFrameRate = -1",
             f"d3d9.samplerAnisotropy = {anisotropy}",
             f"d3d11.samplerAnisotropy = {anisotropy}"]
    if async_mode:
        lines.append("dxvk.enableAsync = True")
    return "\n".join(lines) + "\n"
