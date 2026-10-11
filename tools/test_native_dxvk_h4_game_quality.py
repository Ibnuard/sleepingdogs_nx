"""Exercise original-game XML updates, durable file replacement and rollback."""
import json
import os
import subprocess
from build_native_dxvk_h4 import ROOT, LOCAL, WORK, sha


def main():
    work = WORK / 'game-quality-checks'
    work.mkdir(parents=True, exist_ok=True)
    LOCAL.mkdir(parents=True, exist_ok=True)
    inputs = [ROOT / 'tests/native_dxvk_game_quality_host.c',
              ROOT / 'src/native_dxvk_com/game_quality.h']
    exe = work / 'game-quality-check'
    command = ['gcc', '-std=c11', '-O1', '-g', '-Wall', '-Wextra', '-Werror', '-no-pie',
               '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
               '-I' + str(ROOT / 'src/native_dxvk_com'), str(inputs[0]), '-o', str(exe)]
    compiled = subprocess.run(command, capture_output=True, text=True)
    (LOCAL / 'game-quality.compile.log').write_text(compiled.stdout + compiled.stderr)
    if compiled.returncode:
        raise RuntimeError(compiled.stdout + compiled.stderr)
    # Interrupted writers terminate separate children; the parent retains full
    # ASan/UBSan and leak checking while recovering their filesystem state.
    env = dict(os.environ, ASAN_OPTIONS='detect_leaks=1:halt_on_error=1')
    run = subprocess.run([str(exe)], capture_output=True, text=True, env=env, timeout=60)
    (LOCAL / 'game-quality.stdout.log').write_text(run.stdout)
    (LOCAL / 'game-quality.stderr.log').write_text(run.stderr)
    if run.returncode or run.stderr:
        raise RuntimeError(run.stdout + run.stderr)
    report = json.loads(run.stdout)
    assert report['status'] == 'PASS' and report['disk_failure_cases'] > 10
    assert report['interrupted_rename_cases'] == 5
    report.update(sanitizers=['address', 'undefined'],
                  leak_detection=True, modeled_rename_cannot_overwrite=True,
                  source_files={p.relative_to(ROOT).as_posix(): sha(p) for p in inputs},
                  runner_sha256=sha(__file__), compile_argv=command,
                  executable_sha256=sha(exe), hardware_tested=False, game_fps_measured=False,
                  scope='Host filesystem fixture validates supported original XML, preservation, repeated application, restore, write/fsync/rename/unlink failures and interruption recovery; not Switch filesystem hardware, game execution or FPS.')
    (LOCAL / 'game-quality.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
