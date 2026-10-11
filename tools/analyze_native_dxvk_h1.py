"""Validate and preserve a user-supplied standalone Horizon H1 capture.

The result covers native rendering on Switch, not real guest transport or
Sleeping Dogs FPS. Raw log bytes are copied without interpreting instructions.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def find(pattern, text):
    match = re.search(pattern, text, re.M)
    if not match:
        raise ValueError('Required H1 evidence missing: ' + pattern)
    return match


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log-dir', type=Path, required=True)
    args = parser.parse_args()
    names = ('result.json', 'probe.log', 'stderr.log', 'sd-dxvk-native-probe_d3d11.log')
    raw = {name: (args.log_dir / name).read_bytes() for name in names}
    result = json.loads(raw['result.json'])
    probe = raw['probe.log'].decode('utf-8')
    dxvk = raw[names[3]].decode('utf-8')
    stderr = raw['stderr.log'].decode('utf-8')
    assert result['status'] == 'PASS' and result['build'] == 'native-dxvk-horizon-v1'
    assert result['checks'] == 644 and result['present_calls'] == 300
    assert not any(result[key] for key in ('game_integration', 'guest_execution', 'game_fps_measured'))
    applet, mode = map(int, find(r'applet_type=(\d+) operation_mode=(\d+)', probe).groups())
    assert applet == 0, 'Full application mode not established'
    arena = find(r'arena native=(0x[0-9a-f]+) guest=(0x[0-9a-f]+) bytes=(\d+)', probe)
    native, guest, size = int(arena[1], 16), int(arena[2], 16), int(arena[3])
    assert native > 0xffffffff and guest == 0x10000000 and size == 8 * 1024 * 1024
    find(r'PASS device FL11_0', probe)
    find(r'PASS buffer shadow Map/Unmap/copy/readback bytes=1024', probe)
    draw = find(r'draw readback pixels=(\d+) bad=(\d+) row_pitch=(\d+)', probe)
    pixels, bad, pitch = map(int, draw.groups())
    assert pixels == 1280 * 720 and bad == 0 and pitch == 1280 * 4
    present = find(r'PASS present calls=(\d+) seconds=([\d.]+); synthetic triangle, no game FPS measurement', probe)
    calls, seconds = int(present[1]), float(present[2])
    assert calls == 300 and seconds > 0
    find(r'PASS all checks=644 presents=300', probe)
    find(r'END; exiting diagnostic', probe)
    assert 'FAIL' not in probe
    find(r'DXVK: 3\.1\.1-sdbatch2-native-probe-v1', dxvk)
    find(r'Build: horizon', dxvk)
    find(r'Found device: NVIDIA Tegra X1 \(GM20B\)', dxvk)
    find(r'VK_NN_vi_surface', dxvk)
    find(r'Present mode: VK_PRESENT_MODE_FIFO_KHR', dxvk)
    find(r'Buffer size:\s+1280x720', dxvk)
    find(r'Image count:\s+3', dxvk)
    assert not re.search(r'VK_ERROR_DEVICE_LOST|Segmentation fault|fatal error', dxvk + stderr, re.I)

    capture = 'native-dxvk-h1-' + sha(raw['probe.log'])[:12]
    archive = ROOT / 'reports' / capture
    archive.mkdir(exist_ok=True)
    (archive / '.gitattributes').write_text('* -text\n', newline='\n')
    inputs = {}
    for name, data in raw.items():
        target_name = name if name.endswith('.json') else name.removesuffix('.log') + '.txt'
        target = archive / target_name
        if target.exists():
            assert target.read_bytes() == data, ('Existing capture differs', target)
        else:
            target.write_bytes(data)
        inputs[name] = dict(source=str((args.log_dir / name).resolve()), sha256=sha(data),
                           archived_path=target.relative_to(ROOT).as_posix(), bytes=len(data))
    warnings = [line for line in dxvk.splitlines() if line.startswith(('warn:', 'err:'))]
    report = dict(status='PASS', capture=capture, evidence='user-supplied Switch logs',
                  build=result['build'], checks=result['checks'], inputs=inputs,
                  hardware_rendering_tested=True, transport='modeled-guest32-arena',
                  real_x86_guest_execution=False, game_integration=False, game_fps_measured=False,
                  applet_type=applet, operation_mode=mode,
                  clocks_recorded=False, clocks_mhz=None, visible_scanout_confirmed_by_user=False,
                  native_arena_address=hex(native), native_arena_above_4g=True,
                  modeled_guest_base=hex(guest), arena_bytes=size,
                  renderer='DXVK 3.1.1-sdbatch2-native-probe-v1 / Horizon ARM64',
                  gpu='NVIDIA Tegra X1 (GM20B)', driver='NVK 26.2.2 / v14.1 cache identity',
                  device_feature_level='11_0', buffer_bytes_verified=1024,
                  draw_resolution=[1280, 720], draw_pixels_verified=pixels,
                  draw_bad_pixels=bad, readback_row_pitch=pitch,
                  present_mode='FIFO', swapchain_images=3,
                  present_calls=calls, present_seconds=seconds,
                  synthetic_present_rate_hz=round(calls / seconds, 4),
                  synthetic_workload=True, normal_main_exit_marker=True,
                  binary_sha256_in_runtime_log=False,
                  warnings=warnings,
                  driver_conformance_warning='NVK is not a conformant Vulkan implementation' in stderr,
                  limits=[
                      'No real PE32/FEX guest or x86 COM proxy exercised.',
                      'Map uses an explicit bounded shadow copy, not zero-copy.',
                      'Present timing is a tiny FIFO synthetic workload, not game FPS.',
                      'Clock telemetry, visible scanout and final return to hbmenu are not recorded.',
                      'The marker identifies H1; logs do not authenticate a running NRO hash.',
                      'Display metadata fallback and native CloseHandle stub still require production review.'
                  ], analyzer_sha256=sha(Path(__file__).read_bytes()))
    output = ROOT / 'reports' / (capture + '.json')
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
