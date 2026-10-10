"""Pin the SD-card logs and separate host-memory evidence from PC requirements."""
from pathlib import Path
import argparse
from port_common import ROOT,sha,write_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--use-captured-evidence',action='store_true',
        help='Use hashes and excerpts already read during this investigation if the SD is disconnected.')
    args=parser.parse_args()
    source=Path('E:/switch/sleepingdogs-fex'); dest=ROOT/'reports/gpu-pressure-input';dest.mkdir(exist_ok=True)
    expected={'crash.log':'94391f308699a9fbd82c7994db567b397732f135ad44dcba92ffdf986c19720e',
        'fex-runtime.log':'c3d0e8ee379535300cc6652743f4b9afb8a07f055509f21314f406f235539d47'}
    snapshot=all((source/name).is_file() for name in expected)
    if snapshot:
        for name,digest in expected.items():
            assert sha(source/name)==digest
            if (dest/name).exists():assert sha(dest/name)==digest
            else:(dest/name).write_bytes((source/name).read_bytes())
        runtime=(dest/'fex-runtime.log').read_text(errors='replace')
    else:
        assert args.use_captured_evidence,'Reconnect the source or explicitly use the already observed excerpts.'
        # These exact fields and binary/log hashes were read successfully from
        # E: before it disappeared. This is not a replacement full log file.
        runtime='''[SD-GPU-STREAM] v1 total_mib=256 large_mib=64 threshold_mib=2 borrow_guard_mib=16
[SD-GPU-HEAP] bytes=65536 align=65536 recovered=0 largest_examined=61688 scanned=62 attempt=256
[SD-GPU-ARENA] capacity=268435456 used=250478592 free=17956864 largest=9437184 peak=267255808 live=174 takes=192 misses=380 returned=18 invalid=0
[SD-GPU-STREAM-STATS] general_largest=0 large_largest=9437184 heap_free=43747328 heap_unclaimed=8192
[SD-RESOURCE] reason=vulkan-allocation-failed free_threads=195 query_rc=00000000 heap_used=2026316752 arena_free=43715632 heap_arena=2070032384 heap_capacity=2070040576 heap_unclaimed=8192 heap_available=43723824
[WINE] err:   DxvkCommandList: Failed to end command buffer
[WINE] err:     Size:      196608
[SD-FIRSTFAULT] access=0 target=6c flags=00000000
[SD-FIRSTFAULT] eip=101345d0 esp=0166f398 ebp=06a063a8 eflags=00000256 context_flags=0001003f'''
    evidence=[]
    for i,line in enumerate(runtime.splitlines(),1):
        if any(x in line for x in ('[SD-GPU-STREAM]','[SD-DXVK-STREAM]',
            'reason=vulkan-allocation-failed','used=250478592','general_largest=0 large_largest=9437184',
            'largest_examined=61688','[SD-FIRSTFAULT] eip=101345d0','[SD-FIRSTFAULT] access=0 target=6c',
            'Failed to end command buffer','Size:      196608')):
            evidence.append({'line':i if snapshot else None,'text':line})
    assert 'bytes=65536 align=65536 recovered=0 largest_examined=61688' in runtime
    assert 'free=17956864 largest=9437184' in runtime
    assert 'eip=101345d0' in runtime and 'target=6c ' in runtime
    native=sha(source/'sleepingdogs-fex.nro') if snapshot else '9a5ef65f646fef4582bb0493573aaadc6c1e51c167de86bff2090f38cb0d0a8f'
    dll=sha(source/'drive_c/SleepingDogs/d3d11.dll') if snapshot else 'e4049ce5466c36beb8d369dd495f30016abcac0afd45311168ba8915c29b0833'
    assert native=='9a5ef65f646fef4582bb0493573aaadc6c1e51c167de86bff2090f38cb0d0a8f'
    assert dll=='e4049ce5466c36beb8d369dd495f30016abcac0afd45311168ba8915c29b0833'
    write_json(ROOT/'reports/gpu-pressure-analysis.json',{'input_sha256':expected,'original_log_directory':str(source),
        'full_log_snapshot_available':snapshot,'evidence_basis':'Full snapshot' if snapshot else 'Hashes and excerpts read successfully in this investigation before the SD disconnected',
        'installed_nro_sha256':native,'installed_d3d11_sha256':dll,'latest_patch_confirmed':True,'mode':'debug',
        'process_limit_bytes':2147483648,'process_committed_bytes':2110832640,'normal_heap_capacity_bytes':2070040576,
        'last_oom_heap_free_bytes':43715632,'last_oom_heap_unclaimed_bytes':8192,
        'gpu_pool':{'capacity':268435456,'used':250478592,'free':17956864,'largest':9437184},
        'normal_heap_examined_aligned_fit_bytes':61688,'guard_bytes':16777216,
        'dxvk_allocated_mib':259,'dxvk_used_mib':252,'failed_image_bytes':196608,
        'first_fault':{'eip':'0x101345d0','module':'d3d11.dll','function':'dxvk::DxvkImage::assignStorageWithUsage',
            'instruction':'mov ecx, dword ptr [ecx + 0x6c]','ecx':'0x0','access':'read','target':'0x6c'},
        'finding':'The normal heap cannot satisfy aligned GPU backing requests. The GPU reserve still has free runs but its hard 16 MiB post-allocation guard rejects all small borrowing when its largest free run is only 9 MiB.',
        'inference':'The failed image allocation leads to a null storage dereference; the CS thread also reports failure ending its command buffer. Removing avoidable reserve refusals addresses a proven allocator defect, but does not prove all later gameplay fits the process budget.',
        'pc_requirements':{'ram':'2 GB','vram':'512 MB',
            'source':'https://support.eu.square-enix.com/faqarticle.php?id=5421&kid=64273&la=2'},
        'budget_note':'The 256 MiB pool is a reservation within ordinary process heap, not a hard Vulkan limit. Overflow already uses ordinary newlib. Vulkan allocation totals are not additive to pool occupancy.',
        'change':'Keep normal allocation preferences; after guarded borrowing and both ordinary newlib paths fail, allocate best-fit from any free GPU run. Preserve live objects, resource sizes, Fastest and the existing process quota.',
        'evidence':evidence,'candidate_hardware_tested':False})
    print('Saved observed crash evidence and analysis; full log snapshot available:',snapshot)


if __name__=='__main__':main()
