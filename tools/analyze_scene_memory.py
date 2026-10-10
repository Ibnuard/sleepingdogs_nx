"""Read the pinned latest logs; distinguish exhausted host backing from VRAM labels."""
from pathlib import Path
import pefile
from port_common import ROOT,sha,write_json

def main():
    folder=ROOT/'reports/scene-memory-input'
    expected={'fex-runtime.log':'d02bf54b92ed50a260316c411c84651a476e53da055d0612630e6d2ff816d423',
        'crash.log':'9236bd69fde57cb4a728ab5b07b9a01fa5a3eaa7b62f405319156128ec14f583'}
    for n,digest in expected.items():assert sha(folder/n)==digest,n
    text=(folder/'fex-runtime.log').read_text(errors='replace')
    needles=('[SD-FEX-MODE]','[FEX3-PRESET]','[SD-COMPILER-MEM]','[SD-GPU-PRESSURE] v1',
        'reserve slots=8 bytes=67371008','emergency_borrows=13 requested_bytes=24117248',
        'used=267321344 free=1114112 largest=983040','largest_examined=655352',
        'bytes=1048576 type=1','heap_used=2027413008','total=2147483648 used=2110832640',
        'Size:      1048576','1536         276         269','eip=100d147e','access=0 target=20',
        'eax=00000000 ebx=0166f548','[SD-SCRATCH-RESERVE] live=33685504 idle=33685504')
    evidence=[{'line':i,'text':line} for i,line in enumerate(text.splitlines(),1) if any(n in line for n in needles)]
    for n in needles:assert n in text,n
    dll=ROOT/'dist/streaming-memory-fix/x32/d3d11.dll'
    assert sha(dll)=='e4049ce5466c36beb8d369dd495f30016abcac0afd45311168ba8915c29b0833'
    with pefile.PE(str(dll)) as pe:
        assert pe.OPTIONAL_HEADER.ImageBase==0x10000000
        assert pe.get_data(0xd147e,3)==bytes.fromhex('8b4820')
    write_json(ROOT/'reports/scene-memory-analysis.json',{
        'input_sha256':expected,'full_log_snapshot_available':True,'previous_gpu_pressure_fix_active':True,
        'actual_fex_profile':'fastest','crash_header_profile_note':'Stable is the legacy renderer/profile label; SD-FEX-MODE and FEX3-PRESET confirm fastest.',
        'process_limit_bytes':2147483648,'process_committed_bytes':2110832640,
        'normal_heap_capacity_bytes':2070040576,'last_oom_heap_free_bytes':42607088,
        'last_oom_heap_unclaimed_bytes':20480,
        'gpu_pool':{'capacity':268435456,'used':267321344,'free':1114112,'largest':983040},
        'emergency_borrows':13,'emergency_borrow_requested_bytes':24117248,
        'failed_allocation_bytes':1048576,'vk_result':-1,'dxvk_allocated_mib':276,'dxvk_used_mib':269,
        'first_fault':{'eip':'0x100d147e','module':'d3d11.dll','function':'dxvk::DxvkBuffer constructor',
            'instruction':'mov ecx, dword ptr [eax + 0x20]','eax':0,'target':'0x20','access':'read',
            'dll_sha256':sha(dll)},
        'finding':'Previous reserve recovery works, but its pool is now almost full. Host-backed Vulkan requests fail, followed by a null allocation dereference in DXVK.',
        'memory_note':'The free heap total is fragmented; the reported GPU pool and DXVK totals overlap. They are not separate allocations to add together, and the pool is not a hard Vulkan limit.',
        'change':'Reduce simultaneous compiler leases and protected decoder/IR pairs from four to two. Keep each buffer full-size, retain both reserves permanently, and acquire the lease before compilation buffers and invalidation lock.',
        'saved_reserve_payload_bytes':33685504,'tradeoff':'Cold compilation may take longer; all guest execution cores remain available.',
        'limits':'Extra headroom does not establish that all later 3D scenes fit. Host tests do not reproduce the full hardware allocation trace.',
        'evidence':evidence,'candidate_hardware_tested':False})
    print('Pinned full latest logs; verified failing x86 instruction against DXVK sdstream1')

if __name__=='__main__':main()
