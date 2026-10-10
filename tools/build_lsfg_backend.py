"""Build the pinned GPL Horizon backend and host-only DXBC converter locally."""
from pathlib import Path
import shutil, subprocess, json
from port_common import ROOT, sha, write_json

WORK = Path('/home/blekjek/sleepingdogs-lsfg-v15')
MESA_HEADERS = Path('/home/blekjek/pes13-build/mesa-switch/include')

def run(args):
    subprocess.run(list(map(str,args)),check=True)

def main():
    recipe=WORK/'recipe'
    shutil.copytree(ROOT/'local/research-lsfg/switch-dev/lsfg',recipe,dirs_exist_ok=True)
    cmake=recipe/'CMakeLists.txt'
    cmake.write_text(cmake.read_text()+f'\ntarget_include_directories(lsfg-vk PRIVATE "{MESA_HEADERS}")\n')
    # Remove the previous diagnostic override; restore every x18/TLS/PIE flag.
    run(['cmake','-S',recipe,'-B',WORK/'backend-cross','-G','Ninja',
        '-DCMAKE_TOOLCHAIN_FILE='+str(ROOT/'local/research-lsfg/switch-dev/cmake/switch.cmake'),
        '-DCMAKE_BUILD_TYPE=Release','-DCMAKE_EXPORT_COMPILE_COMMANDS=ON',
        '-DCMAKE_INSTALL_PREFIX='+str(WORK/'portlibs'),'-DLSFG_SOURCE='+str(WORK/'backend'),
        '-DGLSLANG_VALIDATOR='+str(WORK/'host-tools/usr/bin/glslangValidator')])
    run(['ninja','-C',WORK/'backend-cross','-j6','install'])
    run(['cmake','-S',WORK/'dxbc','-B',WORK/'dxbc-build','-G','Ninja',
         '-DCMAKE_BUILD_TYPE=Release','-DCMAKE_CXX_FLAGS=-I'+str(MESA_HEADERS)])
    run(['ninja','-C',WORK/'dxbc-build','-j6'])
    run(['c++','-std=c++17','-O2','-I'+str(MESA_HEADERS),
         *['-I'+str(WORK/'dxbc/include'/p) for p in ('dxbc','spirv','util','dxvk')],
         ROOT/'tools/lsfg_translate.cpp',WORK/'dxbc-build/libdxbc.a','-o',WORK/'lsfg_translate'])
    commands=json.loads((WORK/'backend-cross/compile_commands.json').read_text())
    assert all('-ffixed-x18' in x['command'] and '-mtp=soft' in x['command'] and '-D__SWITCH__' in x['command'] for x in commands)
    write_json(ROOT/'reports/lsfg-backend-build.json',dict(status='BUILT',
        backend_revision='8b0da2661c6f3473a7fccc8ba643880050e71642',
        horizon_revision='28b2fe1bc39ef1f4c4fe217c430a6908e7d4c7e8',
        dxbc_revision='78ab59a8aaeb43cd1b0a5e91ba86722433a10b78',
        library_sha256=sha(WORK/'portlibs/lib/liblsfg-vk.a'),
        converter_sha256=sha(WORK/'lsfg_translate'),fixed_x18=True,soft_tls=True))

if __name__=='__main__': main()
