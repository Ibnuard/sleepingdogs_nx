"""Compare actual v5/current dispatch cost on host; not Switch FPS or FEX cost."""
from pathlib import Path
import hashlib,json,os,select,secrets,socket,statistics,subprocess
from build_native_dxvk_h4 import ROOT,LOCAL
BASELINE='b51f1aa9f2388e43926430a2f311d05c3cff3729'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    work=LOCAL/'dispatch-benchmark';work.mkdir(parents=True,exist_ok=True)
    old=work/'v5';old.mkdir(exist_ok=True);originals={}
    native=ROOT/'src/native_dxvk_com'
    for path in sorted(native.iterdir()):
        if path.is_file():
            before=subprocess.check_output(['git','-c','safe.directory='+str(ROOT),'show',BASELINE+':'+path.relative_to(ROOT).as_posix()],cwd=ROOT)
            (old/path.name).write_bytes(before);originals[path.name]=sha(old/path.name)
    inputs=json.loads((ROOT/'local/native-dxvk-probe-v1/build-host.json').read_text());library=Path(inputs['library'])
    assert sha(library)==inputs['sha256'];source=library.parent.parent/'source';headers=library.parent.parent/'host-deps/usr/include'
    commands={};executables={}
    for label,folder in [('v5',old),('current',native)]:
        exe=work/label/'dispatch-bench';exe.parent.mkdir(exist_ok=True)
        command=['g++','-O2','-std=c++17','-DSD_COM_HOST_FAULT_TESTS','-I'+str(folder),
                 *['-I'+str(source/p) for p in ('include/native/windows','include/native/directx','include/native','include')],'-I'+str(headers),
                 str(ROOT/'tests/native_dxvk_com_host.cpp'),str(folder/'com_native.cpp'),str(library),'-ldl','-lpthread','/usr/lib/x86_64-linux-gnu/libxcb.so.1','-o',str(exe)]
        if label=='current':command.insert(1,'-DSD_COM_PROGRESS_TEST')
        compile_result=subprocess.run(command,capture_output=True,text=True);(work/(label+'.compile.log')).write_text(compile_result.stdout+compile_result.stderr)
        assert compile_result.returncode==0,compile_result.stderr
        commands[label]=command;executables[label]=exe
    display=None
    for candidate in range(191,291):
        with socket.socket() as check:
            try:check.bind(('127.0.0.1',6000+candidate))
            except OSError:continue
        display=candidate;break
    assert display is not None
    authority=work/'bench.Xauthority';authority.unlink(missing_ok=True);authority.touch(mode=0o600)
    subprocess.run(['xauth','-f',str(authority),'add','127.0.0.1:'+str(display),'MIT-MAGIC-COOKIE-1',secrets.token_hex(16)],check=True,capture_output=True)
    rd,wr=os.pipe();log=(work/'xvfb.log').open('w')
    server=subprocess.Popen(['Xvfb',':'+str(display),'-displayfd',str(wr),'-screen','0','1280x720x24','-nolisten','unix','-listen','tcp','-auth',str(authority)],pass_fds=(wr,),stdout=log,stderr=log);os.close(wr)
    runs={'v5':[],'current':[]}
    try:
        ready,_,_=select.select([rd],[],[],15);assert ready,'Xvfb timeout'
        actual=os.read(rd,100).decode().strip();assert actual.isdigit()
        for repeat in range(6):
            for label in (['v5','current'] if repeat%2==0 else ['current','v5']):
                folder=work/label;config=folder/'host.conf';config.write_text('dxvk.numCompilerThreads = 1\n')
                env=dict(os.environ,DISPLAY='127.0.0.1:'+actual,XAUTHORITY=str(authority),VK_DRIVER_FILES='/usr/share/vulkan/icd.d/lvp_icd.json',
                         DXVK_WSI_DRIVER='FEXTendoProbe',DXVK_LOG_PATH=str(folder),DXVK_SHADER_CACHE_PATH=str(folder),DXVK_CONFIG_FILE=str(config))
                run=subprocess.run([str(executables[label]),'--dispatch-bench'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=120)
                (folder/f'run-{repeat}.stdout.txt').write_text(run.stdout);(folder/f'run-{repeat}.stderr.txt').write_text(run.stderr)
                assert run.returncode==0,run.stderr[-5000:]
                result=json.loads(run.stdout);assert result['status']=='PASS' and result['iterations']==1000000
                runs[label].append(result)
    finally:
        os.close(rd);server.terminate()
        try:server.wait(timeout=5)
        except subprocess.TimeoutExpired:server.kill();server.wait()
        log.close()
    medians={label:statistics.median([r['ns_per_call'] for r in values[1:]]) for label,values in runs.items()}
    paths=[ROOT/'tests/native_dxvk_com_host.cpp',ROOT/'src/native_dxvk/probe_shaders.h',
           *sorted(native.glob('com_native*')),
           *[native/n for n in ('com_progress.h','com_protocol.h','com_interfaces.h','com_methods.h','com_guids.inc','com_inheritance.inc')]]
    report=dict(status='PASS',baseline_commit=BASELINE,baseline_sha256=originals,runs=runs,warm_median_ns_per_call=medians,
                warmup_runs_discarded_per_case=1,alternating_case_order=True,relative_dispatch_speedup=medians['v5']/medians['current'],
                sampled_snapshot_freshness_verified=True,unsampled_call_failure_snapshot_verified=True,
                executable_sha256={label:sha(p) for label,p in executables.items()},compile_argv=commands,native_dxvk_sha256=sha(library),
                runner_sha256=sha(__file__),source_files={p.relative_to(ROOT).as_posix():sha(p) for p in paths},
                hardware_tested=False,game_fps_measured=False,
                scope='Actual native dispatcher and DXVK context GetType; host CPU, modeled Wine permissions. GPU creation outside timing. No PE32/FEX, Horizon scheduling, GPU timing or gameplay benchmark.')
    (LOCAL/'dispatch-benchmark.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
    print(json.dumps({k:report[k] for k in ('status','warm_median_ns_per_call','relative_dispatch_speedup','hardware_tested','game_fps_measured')},indent=2))
if __name__=='__main__':main()
