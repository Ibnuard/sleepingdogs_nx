"""Exercise the shipped low alias implementation with actual shared Linux pages."""
from pathlib import Path
import argparse,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from port_common import sha,write_json

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',type=Path,default=Path('/home/blekjek/sleepingdogs-low-window-v1'))
    p.add_argument('--production-size',action='store_true');a=p.parse_args()
    source=a.work/'native-source';native=source/'wine-nx-probe/source';out=a.work/('alias-check-full' if a.production_size else 'alias-check')
    out.mkdir(exist_ok=True)
    test=(ROOT/'tests/direct_arena.c').read_text()
    start=test.index('typedef unsigned Result;');end=test.index('#define memalign test_memalign')
    test=test[:start]+(ROOT/'tests/low_window_arena_boundary.inc').read_text()+test[end:]
    # The boundary supplies only low_window_ready; profile constants remain real.
    test=test.replace('static int sd_low_window_ready(void)', 'int sd_low_window_ready(void)')
    test=test.replace('    if(mapping){assert(!munmap(mapping,mapping_size));mapping=NULL;}',
        '''    if(alias){assert(!munmap(alias,mapping_size));alias=NULL;}
    if(mapping){assert(!munmap(mapping,mapping_size));mapping=NULL;}
    if(backing_fd>=0){close(backing_fd);backing_fd=-1;}
    sd_arena_backing=NULL;map_fail=process_fail=unmap_fail=low_busy=0;ready=1;''')
    test=test.replace('pass("reject backing above 4 GiB")','pass("reject backing below 4 GiB")')
    test=test.replace('nviews==3&&views[0].protect==VPROT_SYSTEM&&views[2].protect==VPROT_SYSTEM',
                      'nviews==2&&views[1].protect==VPROT_SYSTEM')
    old='    assert(sd_register_kernel_range(p-65536,size+131072));'
    start=test.index('    assert(!sd_register_kernel_range(p-65536');end=test.index('\n    assert(sd_map_direct_view',start)
    test=test[:start]+'''    assert(!sd_register_low_arena());assert(nviews==1&&sd_direct_view==&views[0]);
    assert(!sd_register_low_arena()&&nviews==1);pass("high kernel heap does not hide the low Wine arena guard");
    /* Also exercise the untouched fallback for unrelated kernel ranges. */
    assert(!sd_register_kernel_range((void *)0x70000000,65536));
''' + test[end:]
    pos=test.index('    reset_fixture();sd_guest_arena_init();unsigned char *p=')
    test=test[:pos]+'''    reset_fixture();ready=0;sd_guest_arena_init();assert(!sd_arena_base&&!mapping);pass("failed preflight prevents physical allocation");
    reset_fixture();low_busy=1;sd_guest_arena_init();assert(!sd_arena_base&&frees==1&&!alias);pass("occupied low range is never replaced");
    reset_fixture();map_fail=1;sd_guest_arena_init();assert(!sd_arena_base&&frees==1&&!alias);pass("map failure frees unowned backing");
    reset_fixture();process_fail=1;sd_guest_arena_init();assert(!sd_arena_base&&frees==1&&!alias);pass("permission failure unmaps before freeing");
    reset_fixture();process_fail=unmap_fail=1;sd_guest_arena_init();assert(!sd_arena_base&&!frees&&alias&&sd_arena_backing==mapping);pass("failed unmap retains owned backing and disables arena");
''' + test[pos:]
    testfile=out/'alias.c';testfile.write_text(test)
    binary=out/'alias-check'
    command=['gcc','-std=c11','-g','-O1','-Wall','-Wextra','-Werror','-Wno-misleading-indentation',
        '-fsanitize=undefined','-fno-sanitize-recover=all','-I',str(native),'-I',str(source/'dlls/ntdll/unix'),str(testfile),'-o',str(binary)]
    if a.production_size:command.insert(1,'-DSD_GUEST_ARENA_BYTES=1048576000UL')
    subprocess.run(command,check=True)
    result=subprocess.run([binary],text=True,capture_output=True)
    (out/'output.txt').write_text(result.stdout+result.stderr);print(result.stdout+result.stderr);result.check_returncode()
    cases=[l[5:] for l in result.stdout.splitlines() if l.startswith('PASS ')];assert len(cases)==20,cases
    write_json(ROOT/'reports'/('low-window-arena-full.json' if a.production_size else 'low-window-arena.json'),{
        'status':'PASS','hardware_tested':False,'sanitizers':['undefined'],'cases':cases,
        'arena_bytes':1048576000 if a.production_size else 1048576,
        'source_files':{p.relative_to(source).as_posix():sha(p) for p in [native/'sd_guest_arena.c',native/'sd_guest_arena.h',
            native/'sd_alias_arena_init.inc',native/'sd_low_window.h',source/'dlls/ntdll/unix/sd_guest_view.inc']},
        'tests':{p.relative_to(ROOT).as_posix():sha(p) for p in [Path(__file__),ROOT/'tests/direct_arena.c',ROOT/'tests/low_window_arena_boundary.inc']}})

if __name__=='__main__':main()
