"""Differential range/probe faults using actual bridge and pinned Wine bodies.

Wine SEH is replaced only by a POSIX signal recovery adapter. This tests real
page protections, not Horizon exception dispatch or gameplay performance.
"""
from pathlib import Path
import hashlib,json,re,subprocess
from build_native_dxvk_h4 import ROOT,LOCAL,PIN
BASELINE='f2d16f243e2feb5bca8f7320673445edd15c972f'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    work=LOCAL/'memory-probe-check';work.mkdir(parents=True,exist_ok=True)
    pin=json.loads(PIN.read_text());wine=Path(pin['virtual_source'])
    assert sha(wine)==pin['virtual_sha256']
    source=wine.read_text();bodies=[]
    for kind in ('read','write'):
        start=source.index('BOOL virtual_check_buffer_for_'+kind+'(')
        end=source.index('\n}\n',start)+3
        body=source[start:end].replace('virtual_check_buffer_for_'+kind,'pinned_'+kind)
        # Wine's C bodies need explicit void-pointer casts in this C++ fixture.
        body=body.replace('volatile const char *p = ptr;', 'volatile const char *p = (const char *)ptr;')
        body=body.replace('volatile char *p = ptr;', 'volatile char *p = (char *)ptr;')
        bodies.append(body)
    (work/'wine_probe_bodies.inc').write_text('\n'.join(bodies),newline='\n')
    old=subprocess.check_output(['git','-c','safe.directory='+str(ROOT),'show',BASELINE+':src/native_dxvk_com/com_native.cpp'],cwd=ROOT,text=True)
    native=ROOT/'src/native_dxvk_com/com_native.cpp';ranges=[]
    for label,text in [('OldRanges',old),('NewRanges',native.read_text())]:
        start=text.index('    template<typename T> T* read(');end=text.index('    uint32_t array_count(',start)
        ranges.append('struct '+label+' {\n'+text[start:end]+'};\n')
    (work/'bridge_ranges.inc').write_text('\n'.join(ranges),newline='\n')
    exe=work/'memory-probes';fixture=ROOT/'tests/native_dxvk_memory_probes.cpp'
    command=['g++','-std=c++17','-O2','-g','-fsanitize=undefined','-fno-sanitize-recover=all','-I'+str(work),str(fixture),'-lpthread','-o',str(exe)]
    result=subprocess.run(command,capture_output=True,text=True);(work/'compile.log').write_text(result.stdout+result.stderr)
    assert result.returncode==0,result.stderr
    result=subprocess.run([str(exe)],capture_output=True,text=True,timeout=60)
    (work/'stdout.log').write_text(result.stdout);(work/'stderr.log').write_text(result.stderr)
    assert result.returncode==0,result.stderr
    report=json.loads(result.stdout);assert report['status']=='PASS'
    report.update(baseline_commit=BASELINE,runner_sha256=sha(__file__),compile_argv=command,
        source_files={p.relative_to(ROOT).as_posix():sha(p) for p in (native,fixture,PIN)},
        pinned_wine_source=dict(path=str(wine),sha256=sha(wine)),
        extracted_body_sha256={p.name:sha(p) for p in (work/'wine_probe_bodies.inc',work/'bridge_ranges.inc')},
        executable_sha256=sha(exe),sanitizers=['undefined'],hardware_tested=False,game_fps_measured=False,
        scope='Actual bridge range methods and pinned Wine volatile probe bodies (names and explicit C-to-C++ void-pointer casts adapted); real mmap/mprotect faults with modeled POSIX recovery replacing Wine SEH. Timings are host check cost, not FEX/Horizon or game FPS.')
    (LOCAL/'memory-probes.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
    print(result.stdout.strip())
if __name__=='__main__':main()
