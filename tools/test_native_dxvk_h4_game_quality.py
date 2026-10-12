"""Exercise original-game XML updates, durable file replacement and rollback."""
import json
import os
import shutil
import subprocess
from build_native_dxvk_h4 import ROOT, LOCAL, WORK, sha


def main():
    work = WORK / 'game-quality-checks'
    work.mkdir(parents=True, exist_ok=True)
    LOCAL.mkdir(parents=True, exist_ok=True)
    inputs = [ROOT / 'tests/native_dxvk_game_quality_host.c',
              ROOT / 'src/native_dxvk_com/game_quality.h',
              ROOT / 'tests/native_dxvk_game_quality_capture.c',
              ROOT / 'reports/native-dxvk-h4-game-7d1ee877d066/DisplaySettings.xml']
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
    assert sha(inputs[3])=='27bdc2ab3d16dfad4ee0078349a855fef43985351c89c73f72cdc25d5e350c89'
    baseline='951ffdc4192b01a88a8fc51224ea02804f5776ab'
    capture_cases={}
    for name in ('v8','current'):
        case=work/name;case.mkdir(exist_ok=True)
        header=case/'game_quality.h'
        if name=='v8':header.write_bytes(subprocess.check_output(['git','-c','safe.directory='+str(ROOT),'show',baseline+':src/native_dxvk_com/game_quality.h'],cwd=ROOT))
        else:shutil.copyfile(inputs[1],header)
        binary=case/'capture-check'
        argv=command[:command.index('-I'+str(ROOT/'src/native_dxvk_com'))]+['-I'+str(case),str(inputs[2]),'-o',str(binary)]
        compile_capture=subprocess.run(argv,capture_output=True,text=True)
        assert compile_capture.returncode==0,compile_capture.stderr
        captured=subprocess.run([str(binary),str(inputs[3])],capture_output=True,text=True,env=env,timeout=20)
        expected=42 if name=='v8' else 0
        assert captured.returncode==expected and not captured.stderr,(name,captured.stdout,captured.stderr)
        assert ('REJECTED_PRESERVED: unsupported Version' if name=='v8' else 'PASS: exact supplied XML') in captured.stdout
        capture_cases[name]=dict(exit_code=captured.returncode,output=captured.stdout.strip(),
                                header_sha256=sha(header),executable_sha256=sha(binary),compile_argv=argv)
    report.update(sanitizers=['address', 'undefined'],
                  leak_detection=True, modeled_rename_cannot_overwrite=True,
                  source_files={p.relative_to(ROOT).as_posix(): sha(p) for p in inputs},
                  runner_sha256=sha(__file__), compile_argv=command,
                  executable_sha256=sha(exe), supplied_xml_replay=capture_cases,baseline_commit=baseline,
                  only_global_setting_changes_in_supplied_xml=True,negative_values_in_other_fields_still_rejected=True,
                  precise_field_errors_verified=True,hardware_tested=False, game_fps_measured=False,
                  scope='Host filesystem fixture validates supported original XML, preservation, repeated application, restore, write/fsync/rename/unlink failures and interruption recovery; not Switch filesystem hardware, game execution or FPS.')
    (LOCAL / 'game-quality.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
