"""Compile and exercise native COM inline pointer storage under ASan/UBSan."""
import json
import subprocess
from build_native_dxvk_h4 import ROOT, LOCAL, WORK, sha


def main():
    work = WORK / 'array-checks'
    work.mkdir(parents=True, exist_ok=True)
    LOCAL.mkdir(parents=True, exist_ok=True)
    inputs = [ROOT / 'tests/native_dxvk_array_host.cpp',
              ROOT / 'src/native_dxvk_com/com_native_array.h',
              ROOT / 'src/native_dxvk_com/com_protocol.h']
    exe = work / 'array-check'
    command = ['g++', '-std=c++17', '-O1', '-g', '-Wall', '-Wextra', '-Werror', '-no-pie',
               '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
               '-I' + str(ROOT / 'src/native_dxvk_com'), str(inputs[0]), '-o', str(exe)]
    result = subprocess.run(command, capture_output=True, text=True)
    (LOCAL / 'arrays.compile.log').write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    result = subprocess.run([str(exe)], capture_output=True, text=True, timeout=30)
    (LOCAL / 'arrays.stdout.log').write_text(result.stdout)
    (LOCAL / 'arrays.stderr.log').write_text(result.stderr)
    if result.returncode or result.stderr:
        raise RuntimeError(result.stdout + result.stderr)
    receipt = json.loads(result.stdout)
    assert receipt['status'] == 'PASS' and receipt['vector_allocations'] == 10000
    assert receipt['inline_allocations'] == receipt['live_allocations'] == 0
    receipt.update(sanitizers=['address', 'undefined'], inline_capacity=128,
                   counts_tested=[0, 1, 12, 128, 129, 16384],
                   source_files={p.relative_to(ROOT).as_posix(): sha(p) for p in inputs},
                   runner_sha256=sha(__file__), compile_argv=command, executable_sha256=sha(exe),
                   hardware_tested=False, game_fps_measured=False,
                   scope='Native temporary pointer-array allocation, initialization, failure and lifetime only; no COM proxy, FEX, GPU or game FPS measurement.')
    (LOCAL / 'array-check.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
