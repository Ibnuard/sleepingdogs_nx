"""Build the native emergency GPU reuse fix in a fresh immutable work tree."""
from pathlib import Path
import argparse, json, shutil
from port_common import ROOT, DEFAULT_GAME, GAME_EXE, sha, write_json
from build_launcher import prepare, build_nro
from build_streaming_memory import FILES as PREVIOUS_FILES, ADAPTER_FILES
from sleepingdogs_fault_trace import apply as apply_faults
from sleepingdogs_gpu_pressure import MARKER

FILES = PREVIOUS_FILES + ('wine-nx-probe/source/sd_gpu_pressure.h',)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',type=Path,default=Path('/home/blekjek/sleepingdogs-gpu-pressure-v1'))
    p.add_argument('--jobs',type=int,default=4)
    a = p.parse_args(); work = a.work.resolve(); work.mkdir(exist_ok=True,parents=True)
    out = ROOT / 'dist/gpu-pressure-fix'; out.mkdir(exist_ok=True)
    source, metadata = prepare(work, DEFAULT_GAME / GAME_EXE)
    stamp = work / 'fault-prepared.json'
    if not stamp.exists():
        apply_faults(source); write_json(stamp,{n:sha(source / n) for n in FILES})
    for n,digest in json.loads(stamp.read_text()).items(): assert sha(source / n) == digest,n
    elf,nro = build_nro(work, source, Path('/home/blekjek/pes13-build'), a.jobs)
    for marker in (MARKER.encode(),b'[SD-GPU-STREAM] v1',b'[SD-COMPILER-MEM] native=v1',b'fastest'):
        assert marker in nro.read_bytes(),marker
    shutil.copy2(nro, out / nro.name)
    shutil.copy2(elf, ROOT / 'local/symbols/sleepingdogs-gpu-pressure.elf')
    write_json(out / 'native.json',{'build':'sleepingdogs-gpu-pressure-v1', 'nro_sha256':sha(nro),
        'elf_sha256':sha(elf),'game':metadata,'gpu_preallocation_bytes':268435456,'reserve_is_soft':True,
        'source_files':{n:sha(source / n) for n in FILES},
        'adapter_files':{n:sha(work / 'fex-adapter' / n) for n in ADAPTER_FILES},
        'patch_sha256':sha(ROOT / 'tools/sleepingdogs_gpu_pressure.py'),
        'builder_sha256':sha(Path(__file__)),
        'prepared':json.loads((work / 'sleepingdogs-prepared.json').read_text()),'hardware_tested':False})
    print('GPU pressure NRO:',sha(nro),flush=True)


if __name__ == '__main__': main()
