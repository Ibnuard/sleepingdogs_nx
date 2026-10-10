"""ASan/UBSan for the exact native emergency allocator helper."""
from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from port_common import sha,write_json
WORK=Path('/home/blekjek/sleepingdogs-gpu-pressure-v1')


def main():
    native=WORK/'native-source/wine-nx-probe/source';out=WORK/'host-check';out.mkdir(exist_ok=True)
    exe=out/'pressure'
    subprocess.run(['cc','-std=gnu11','-O1','-g','-pthread','-fsanitize=address,undefined',
        '-fno-sanitize-recover=all','-fno-pie','-no-pie','-I'+str(native),
        str(ROOT/'tests/gpu_pressure.c'),'-o',str(exe)],check=True)
    result=subprocess.check_output([exe],text=True).strip();print(result,flush=True)
    write_json(ROOT/'reports/gpu-pressure-host-check.json',{'status':'PASS','result':result,
        'sanitizers':['address','undefined'],'compiled_native':{n:sha(native/n) for n in
            ('f1_gpu_arena.h','sd_gpu_stream.h','sd_gpu_pressure.h')},
        'sources':{n:sha(ROOT/n) for n in ('tests/check_gpu_pressure_host.py','tests/gpu_pressure.c')},
        'scope':'Production helper with synthetic arrangement matching the logged occupancy/free/largest values; pthread mutex models arena locking.',
        'hardware_tested':False})


if __name__=='__main__':main()
