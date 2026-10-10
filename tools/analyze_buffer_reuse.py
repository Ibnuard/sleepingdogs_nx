"""Record full SS/09 logs and confirm a failed deferred Map precedes game memcpy."""
import json,pefile
from port_common import ROOT,sha,write_json
def main():
    folder=ROOT/'reports/scene2-input'
    hashes={'crash.log':'0e289085650b1b22fa9ba69367ac497b1a6fe08897dd2ba4f346ced91ba32a55',
        'fex-runtime.log':'660b2f3edca3e7d0ac5b06bfbaaaec920664c3a427f5d10d00d0f396b38b17d2'}
    for n,h in hashes.items():assert sha(folder/n)==h
    text=(folder/'fex-runtime.log').read_text(errors='replace')
    needles=('[SD-COMPILER-MEM] native=v2','[SD-COMPILER-MEM] fex=v2','[FEX3-PRESET] fastest',
        '4352 allocations of 19339 MB','used=265158656 free=3276800 largest=1114112',
        'heap_used=2022927968','bytes=5242880 type=1','[SD-DXVK-MAP] deferred buffer allocation failed',
        '1536         300         291','eip=00e5897a','access=1 target=40')
    for n in needles:assert n in text,n
    game=ROOT.parent/'Sleeping Dogs/HKShip.exe'
    assert sha(game)=='3c2eaa260ee29dfb464a0321aa9c7dc74e343894b663fac4fdd11d40fab0bacc'
    with pefile.PE(str(game)) as pe:assert pe.get_data(0xe5897a-pe.OPTIONAL_HEADER.ImageBase,2)==bytes.fromhex('f3a5')
    write_json(ROOT/'reports/buffer-reuse-analysis.json',{'input_sha256':hashes,'full_log_snapshot_available':True,
        'two_compiler_fix_active':True,'fex_profile':'fastest','failed_bytes':5242880,'vk_result':-1,
        'gpu_pool':{'used':265158656,'free':3276800,'largest':1114112},
        'last_oom_snapshot':{'heap_used':2022927968,'heap_free':45896096,'unclaimed':1216512,'heap_capacity':2070040576},
        'dxvk_allocated_mib':300,'dxvk_used_mib':291,
        'gpu_churn_last_sample':{'allocations':4352,'allocated_mib_cumulative':19339,'frees':4246,'freed_mib_cumulative':19089,'live_mib':250},
        'first_fault':{'module':'HKShip.exe','eip':'0x00e5897a','instruction':'rep movsd','access':'write','target':'0x40'},
        'finding':'Two compiler workspaces are active. Repeated large GPU allocations still end in a 5 MiB failure; deferred Map returns OOM and the game then copies to NULL+0x40.',
        'inference':'Keeping a small bounded set of fully retired large mapped buffers intact can prevent fresh contiguous backing requests during repeated Map lifetimes. The complete allocation timeline is unavailable; this does not prove the entire scene fits.',
        'change':'Cache one retired allocation per exact size/type, 2-8 MiB only, at most four entries and 16 MiB idle globally. No live references reused; drain idle entries on allocator pressure and destruction.',
        'evidence':[{'line':i,'text':s} for i,s in enumerate(text.splitlines(),1) if any(n in s for n in needles)],
        'reference_semantics':['https://learn.microsoft.com/en-us/windows-hardware/drivers/display/mapping-on-deferred-contexts',
            'https://docs.vulkan.org/refpages/latest/refpages/source/vkFreeMemory.html'],'hardware_tested':False})
    print('SS/09 full snapshots pinned; verified first-fault REP MOVSD in original game')
if __name__=='__main__':main()
