"""Verify pinned kernel/loader scope, preserved HOC settings and packed forwarder."""
from pathlib import Path
import argparse,hashlib,json,re,struct,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from port_common import sha,write_json
from build_low_window_boot import AMS_REV,HOC_RELEASE,HOC_LOADER

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',type=Path,default=Path('/home/blekjek/sleepingdogs-low-window-v1'))
    a=p.parse_args();work=a.work;out=ROOT/'dist/low-window-fix'
    build=json.loads((out/'boot/build.json').read_text());fw=json.loads((out/'forwarder/build.json').read_text())
    assert build['ams_revision']==AMS_REV and build['hoc_release']==HOC_RELEASE and build['hoc_source']==HOC_LOADER
    ams=work/'atmosphere';hoc=work/'atmosphere-hoc'
    patch=work/'sleepingdogs-low-window.patch'
    subprocess.run(['git','-C',str(ams),'apply','--reverse','--check',str(patch)],check=True)
    expected=set(re.findall(r'^diff --git a/(\S+)',patch.read_text(),re.M))
    actual=set(subprocess.check_output(['git','-C',str(ams),'diff','--name-only'],text=True).splitlines())
    assert actual==expected and len(expected)==8,(actual,expected)
    header=ams/'libraries/libvapours/include/vapours/svc/svc_memory_map.hpp'
    func=re.search(r'constexpr inline bool HasAutorunLowWindow\(u64 program_id\) \{.*?\n    \}',header.read_text(),re.S)[0]
    # Compile the exact shared whitelist used by kernel AND both loader variants.
    fixture='#include <cstdint>\nusing u64=uint64_t;\n'+func+'''
static_assert(HasAutorunLowWindow(UINT64_C(0x0548EABB35576000)));
static_assert(HasAutorunLowWindow(UINT64_C(0x059A3DB219B42000)));
static_assert(!HasAutorunLowWindow(0));
static_assert(!HasAutorunLowWindow(UINT64_MAX));
static_assert(!HasAutorunLowWindow(UINT64_C(0x0100000000000001)));
static_assert(!HasAutorunLowWindow(UINT64_C(0x059A3DB219B42001)));
int main() {}
'''
    test=work/'boot-whitelist.cpp';test.write_text(fixture)
    subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(test),'-o',str(work/'boot-whitelist')],check=True)
    subprocess.run([str(work/'boot-whitelist')],check=True)
    assert (hoc/header.relative_to(ams)).read_bytes()==header.read_bytes()
    kernel=(ams/'libraries/libmesosphere/source/kern_k_page_table_base.cpp').read_text()
    i=kernel.index('if (low_window)');assert kernel.index('if (m_address_space_width == 39)')<i
    assert 'm_code_region_start       = ams::svc::AutorunNativeAddressStart;' in kernel
    assert 'm_alias_code_region_start = ams::svc::AddressSmallMap32Start;' in kernel
    for tree in (ams,hoc):
        loader=(tree/'stratosphere/loader/source/ldr_process_creation.cpp').read_text()
        branch=loader.split('case svc::CreateProcessFlag_AddressSpace64Bit:',1)[1].split('break;',1)[0]
        assert 'if (svc::HasAutorunLowWindow(out_param->program_id))' in branch
        assert 'aslr_start = svc::AutorunNativeAddressStart;' in branch
        assert 'aslr_size  = svc::AddressMap39End - aslr_start;' in branch
    user=Path('/mnt/d/Dev/Personal/UNDANGAN/hoc.kip').read_bytes()
    patched=(out/'boot/loader-hoc-low-window.kip').read_bytes()
    uoff=build['hoc_settings_offset_original'];off=build['hoc_settings_offset_patched'];n=build['hoc_settings_bytes']
    assert patched[off:off+n]==user[uoff:uoff+n]
    assert struct.unpack_from('<II',patched,off+4)==(6,251)
    assert hashlib.sha256(patched[off:off+n]).hexdigest()==build['hoc_settings_sha256']
    for name,h in build['files'].items():assert sha(out/'boot'/name)==h
    for name in ('loader-hoc-low-window.kip','loader-stock-low-window.kip'):
        data=(out/'boot'/name).read_bytes()
        assert data[:4]==b'KIP1' and struct.unpack_from('<Q',data,16)[0]==0x0100000000000001
    npdm=(work/'forwarder-final/exefs/main.npdm').read_bytes()
    assert npdm[:4]==b'META' and npdm[12]&1 and (npdm[12]>>1)&7==3
    assert struct.unpack_from('<I',npdm,0x14)[0]==16777216
    previous=Path('/home/blekjek/sleepingdogs-gpu-forwarder-v1/exefs/main.npdm').read_bytes()
    normalized=bytearray(npdm);normalized[12]=previous[12];normalized[0x14:0x18]=previous[0x14:0x18]
    assert normalized==previous,'Unintended NPDM capability change'
    # Builder verifies packed NSP contents; independently require actual NPDM bytes in NSP.
    nsp=(out/'forwarder'/fw['nsp']).read_bytes();assert npdm in nsp
    assert hashlib.sha256(nsp).hexdigest()==fw['sha256']
    assert fw['native_nro_above_4g']
    for name,h in fw['source_files'].items():assert sha(work/'forwarder-final/source'/name)==h
    helper=(work/'forwarder-final/source/sd_forwarder_low.inc').read_text()
    fixture='''#include <cassert>
#include <cstdint>
#include <cstddef>
using VirtmemReservation=int;
static int reservation,fail_reservation,reserve_calls,find_calls;
static uintptr_t candidate=UINT64_C(0x100000000);
static VirtmemReservation *virtmemAddReservation(void *p,size_t n) {
    ++reserve_calls;assert((uintptr_t)p==0x200000 && n==0xffe00000);
    return fail_reservation?nullptr:&reservation;
}
static void *virtmemFindCodeMemory(size_t,size_t guard) {
    ++find_calls;assert(!guard && reserve_calls && !fail_reservation);return (void *)candidate;
}
'''+helper+'''
int main() {
    fail_reservation=1;assert(!sd_forwarder_find_native(4096)&&!find_calls);
    fail_reservation=0;assert(sd_forwarder_find_native(4096)==(void *)candidate);
    assert(sd_forwarder_find_native(4096)==(void *)candidate && reserve_calls==2);
    candidate=0x400000;assert(!sd_forwarder_find_native(4096));
    candidate=UINT64_C(0x8000000000)-4096;assert(!sd_forwarder_find_native(8192));
    candidate=UINT64_C(0x8000000000);assert(!sd_forwarder_find_native(4096));
    candidate=0;assert(!sd_forwarder_find_native(4096));
}
'''
    test=work/'forwarder-range.cpp';test.write_text(fixture)
    subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(test),'-o',str(work/'forwarder-range')],check=True)
    subprocess.run([str(work/'forwarder-range')],check=True)
    source_files={}
    for tree in (ams,hoc):
        paths=subprocess.check_output(['git','-C',str(tree),'diff','--name-only'],text=True).splitlines()
        source_files[tree.name]={n:sha(tree/n) for n in paths if (tree/n).is_file()}
    report={'status':'PASS','hardware_tested':False,'boot_files':build['files'],'nsp_sha256':fw['sha256'],
        'kernel_patch_files':8,'whitelist_cases':6,'hoc_configuration_preserved':True,
        'npdm_changes_only':['address space 2 -> 3','system resource 0 -> 16 MiB'],
        'compiled_source_changes':source_files,'sources':{'tests/check_low_window_boot.py':sha(Path(__file__))}}
    write_json(ROOT/'reports/low-window-boot.json',report);print('PASS kernel scope, whitelist, HOC CUST and actual NSP/NPDM')

if __name__=='__main__':main()
