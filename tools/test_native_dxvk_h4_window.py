"""Test actual runtime handoff functions and Horizon window code with modeled libnx."""
from pathlib import Path
import hashlib
import json
import subprocess
from build_native_dxvk_h4 import ROOT,LOCAL,WORK,PIN,overlay_runtime,sha

MOCK_SWITCH=r'''#pragma once
#include <cstdint>
using u64=uint64_t;using s32=int32_t;using Result=uint32_t;using Handle=uint32_t;
enum AppletType { AppletType_Application=0,AppletType_LibraryApplet=2 };
struct NWindow { uint64_t slots_configured;uint32_t width,height;bool is_connected; };
#define R_FAILED(result) ((result)!=0)
AppletType appletGetAppletType(void);
NWindow* nwindowGetDefault(void);
bool nwindowIsValid(NWindow*);
Result nwindowSetDimensions(NWindow*,uint32_t,uint32_t);
u64 armGetSystemTick(void);u64 armTicksToNs(u64);
Handle threadGetCurHandle(void);
Result svcGetThreadCoreMask(s32*,u64*,Handle);
Result svcGetThreadPriority(s32*,Handle);
'''
CASES=['old-game-order','gui','debug','com-console','handoff-failed',
       'wrong-applet','invalid-window','other-owner-busy','dimension-failure-retry','cached-window']

def function(text,signature):
    assert text.count(signature)==1,signature
    start=text.index(signature);position=text.index('{',start);depth=1;end=position+1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[start:end]+'\n'

def main():
    pin=json.loads(PIN.read_text());source=Path(pin['runtime_source'])
    assert sha(source)==pin['runtime_sha256']
    runtime=overlay_runtime(source.read_text())
    signatures=['static int fx_owned(void) {','static int fx_handoff(void) {',
                'void wine_nx_screen_leave_console(void)\n{','static int sd_com_prepare_screen(void) {']
    fixture='\n'.join(function(runtime,signature) for signature in signatures)
    guards=['if (sd_com_enabled || fx_owned()) return -1;',
            'if (sd_com_enabled || fx_owned()) return NULL;',
            'if (sd_com_enabled || fx_owned() || !wine_nx_compositor_mode) return 0;',
            'if (sd_com_enabled || !fx_handoff()) return NULL;']
    assert all(runtime.count(guard)==1 for guard in guards)
    # Screen preparation belongs to the common native route, after optional
    # diagnostic log setup, so both HKShip and the COM test use it.
    route=runtime[runtime.index('    if(sd_com_enabled){\n        mkdir('):]
    assert route.index('mode=%s target=%s')<route.index('if(!sd_com_prepare_screen())')
    work=WORK/'window-checks';work.mkdir(parents=True,exist_ok=True);LOCAL.mkdir(parents=True,exist_ok=True)
    header=work/'switch.h';header.write_text(MOCK_SWITCH,newline='\n')
    include=work/'runtime_window.inc';include.write_text(fixture,newline='\n')
    inputs=[ROOT/'tests/native_dxvk_window_host.cpp',ROOT/'src/native_dxvk_com/com_horizon.cpp',
            ROOT/'src/native_dxvk_com/com_protocol.h',ROOT/'src/native_dxvk_com/com_interfaces.h']
    executable=work/'window-check'
    command=['g++','-std=c++17','-O1','-g','-Wall','-Wextra','-Werror','-pthread','-no-pie',
             '-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(work),
             str(inputs[0]),str(inputs[1]),'-o',str(executable)]
    with (LOCAL/'window.compile.log').open('w') as log:
        result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
    if result.returncode:raise RuntimeError((LOCAL/'window.compile.log').read_text())
    outputs={}
    for case in CASES:
        result=subprocess.run([str(executable),case],capture_output=True,text=True,timeout=10)
        assert result.returncode==0,(case,result.stdout,result.stderr)
        assert result.stdout.strip()=='PASS '+case and not result.stderr,(case,result.stdout,result.stderr)
        outputs[case]=result.stdout.strip()
    receipt=dict(status='PASS',cases=outputs,sanitizers=['address','undefined'],real_pthread_join=True,
                 runtime_source_sha256=hashlib.sha256(runtime.encode()).hexdigest(),runtime_functions=signatures,
                 source_files={str(p.relative_to(ROOT)):sha(p) for p in inputs},runner_sha256=sha(__file__),
                 compile_argv=command,fixture_sha256=sha(include),mock_header_sha256=sha(header),
                 native_wine_surface_guards_source_checked=guards,hardware_tested=False,game_fps_measured=False,
                 scope='Actual overlaid runtime handoff functions and com_horizon.cpp; real pthread stop/join with modeled UI cleanup and libnx window/console. Synthetic Result codes. No Horizon display, Wine/FEX, device or game execution.')
    (LOCAL/'window-check.json').write_text(json.dumps(receipt,indent=2)+'\n',newline='\n')
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
