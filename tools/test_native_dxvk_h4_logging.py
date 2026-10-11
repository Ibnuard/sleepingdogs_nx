"""Check actual native logging overlay and bounded progress under ASan/UBSan."""
from pathlib import Path
import hashlib
import json
import subprocess
from build_native_dxvk_h4 import ROOT,LOCAL,WORK,PIN,overlay_runtime,sha
from test_native_dxvk_h4_window import function

def main():
    pin=json.loads(PIN.read_text());before=Path(pin['runtime_source']).read_text()
    assert sha(pin['runtime_source'])==pin['runtime_sha256']
    runtime=overlay_runtime(before);work=WORK/'logging-checks';work.mkdir(parents=True,exist_ok=True);LOCAL.mkdir(parents=True,exist_ok=True)
    fixture=work/'runtime_logging.inc'
    fixture.write_text(function(runtime,'static void sd_native_log_write(')+function(runtime,'static void log_line( const char *fmt, ... )\n{'),newline='\n')
    assert 'if(__atomic_load_n(&sd_com_enabled,__ATOMIC_ACQUIRE)){sd_com_progress_report();continue;}' in runtime
    assert 'sd_native_log_drain(sd_native_log_write,NULL);' in function(runtime,'static void *log_flusher( void *arg )')
    inputs=[ROOT/'tests/native_dxvk_logging_host.cpp',ROOT/'src/native_dxvk_com/native_log_queue.h',ROOT/'src/native_dxvk_com/com_progress.h']
    exe=work/'logging-check'
    command=['g++','-std=c++17','-O1','-g','-Wall','-Wextra','-Werror','-pthread','-no-pie','-fsanitize=address,undefined','-fno-sanitize-recover=all',
             '-I'+str(work),'-I'+str(ROOT/'src/native_dxvk_com'),str(inputs[0]),'-o',str(exe)]
    with (LOCAL/'logging.compile.log').open('w') as log:result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
    if result.returncode:raise RuntimeError((LOCAL/'logging.compile.log').read_text())
    result=subprocess.run([str(exe)],capture_output=True,text=True,timeout=30)
    (LOCAL/'logging.stdout.log').write_text(result.stdout);(LOCAL/'logging.stderr.log').write_text(result.stderr)
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    assert result.stdout.startswith('PASS:') and not result.stderr
    receipt=dict(status='PASS',sanitizers=['address','undefined'],queue_slots=512,batch_lines=32,
                 actual_overlay_log_functions_tested=True,blocked_sink_does_not_block_producer=True,legacy_logging_preserved=True,
                 overflow_and_contention_reported=True,truncation_keeps_newline=True,concurrent_producers=4,snapshot_publications=20000,
                 runtime_source_sha256=hashlib.sha256(runtime.encode()).hexdigest(),source_files={p.relative_to(ROOT).as_posix():sha(p) for p in inputs},
                 runner_sha256=sha(__file__),fixture_sha256=sha(fixture),compile_argv=command,hardware_tested=False,game_fps_measured=False,
                 scope='Actual overlaid log functions and queue; blocked output callback and concurrent writers. Atomic snapshot consistency. No Horizon SD latency or Switch scheduling measurement.')
    (LOCAL/'logging-check.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
