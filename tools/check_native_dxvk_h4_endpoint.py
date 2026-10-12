"""Inspect the built PE32 endpoint and pinned FEX atomic implementation.

Static code generation/source checks only; Windows races are tested separately.
Prepared FEX sources used to build the retained guest runtime are required.
"""
from pathlib import Path
import hashlib,json,re,subprocess
from build_native_dxvk_h4 import ROOT,LOCAL,MINGW

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    objdump=MINGW/'llvm-objdump';dll=LOCAL/'sdndx4.dll'
    output=subprocess.check_output([str(objdump),'-d','--disassemble-symbols=_proxy_call',str(dll)],text=True)
    (LOCAL/'endpoint-disassembly.txt').write_text(output)
    instructions={int(m[1],16):m[2].strip() for m in re.finditer(r'(?m)^([0-9a-f]+):[^\t]+\t([^\n]+)$',output)}
    load=re.search(r'movl\s+(0x[0-9a-f]+), (%e\w+)',output);assert load,output
    address,register=load.groups()
    branch=re.search(r'jne\s+(0x[0-9a-f]+)',output);assert branch
    hot=[]
    for at,insn in instructions.items():
        if at<int(branch[1],16):continue
        hot.append(insn)
        if insn=='retl':break
    assert hot and hot[-1]=='retl'
    expected_call='calll\t*0x8('+register+')'
    assert [insn for insn in hot if insn.startswith('calll')]==[expected_call],hot
    assert 'pushl\t0x4('+register+')' in hot and 'pushl\t('+register+')' in hot
    assert not any('xchg' in insn for insn in hot)
    exchanges=[insn for insn in instructions.values() if re.search(r'xchgl\s+%e\w+, '+re.escape(address)+r'\b',insn)]
    assert len(exchanges)==1
    vendor=json.loads((ROOT/'vendor/fex/libwow64fex-sd-scene.json').read_text())
    source=Path('/home/blekjek/sleepingdogs-scene-memory-v1/fex/source');files={}
    for name,begin,end in [('FEXCore/Source/Interface/Core/OpcodeDispatcher.cpp','std::optional<Ref> OpDispatchBuilder::XCHGOpImpl','void OpDispatchBuilder::XCHGOp'),('FEXCore/Source/Interface/Core/JIT/AtomicOps.cpp','DEF_OP(AtomicSwap)','DEF_OP(AtomicFetchAdd)')]:
        path=source/name;text=path.read_text();part=text[text.index(begin):text.index(end)]
        files[name]=dict(path=str(path),sha256=sha(path),reviewed_fragment_sha256=hashlib.sha256(part.encode()).hexdigest())
        assert sha(path)==vendor['debug_register_build']['inputs']['source'][name],name
        if 'OpcodeDispatcher.cpp' in name:assert '_AtomicSwap(OpSizeFromSrc(Op), Src, Dest)' in part
        else:assert 'ldswpal(' in part and 'ldaxr(' in part and 'stlxr(' in part and 'TSO' not in part
    report=dict(status='STATIC_CODEGEN_AND_PINNED_FEX_AUDIT',guest_sha256=sha(ROOT/'src/native_dxvk_com/com_guest.c'),proxy_sha256=sha(dll),
        checker_sha256=sha(__file__),disassembly_sha256=sha(LOCAL/'endpoint-disassembly.txt'),compiler_objdump_sha256=sha(objdump),
        published_pointer_address=address,hot_path_instructions=hot,cold_publication_instruction=exchanges[0],
        observed_hot_path='Nonzero descriptor pointer bypasses discovery, critical-section calls and XCHG; both handle halves and the indirect function load depend on that pointer.',
        observed_publication='One XCHG instruction publishes the pointer on the cold initialization path.',
        fex_source_files=files,fex_vendor_receipt_sha256=sha(ROOT/'vendor/fex/libwow64fex-sd-scene.json'),
        fex_interpretation='Pinned normal memory XCHG path emits AtomicSwap, using SWPAL or LDAXR/STLXR independently of optional ordinary-load/store TSO. Existing MonoBackpatcher special path is not modeled or executed in this audit.',
        log_preset='fastest x87=64 scalar_tso=0 vector_tso=0 memcpy_tso=0 multiblock=1 smc=mtrack',
        reference='https://developer.arm.com/-/media/Arm%20Developer%20Community/PDF/Learn%20the%20Architecture/Armv8-A%20memory%20model%20guide.pdf?revision=58b1dd0a-3800-4218-b21a-f95a0332034c',
        limits='Static checks of pinned compiler output and FEX source, not FEX execution or hardware concurrency proof. Switch COM/game validation remains required.',hardware_tested=False,game_fps_measured=False)
    (ROOT/'reports/native-dxvk-h4-v9-endpoint-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],proxy_sha256=report['proxy_sha256'],hot_address_dependency=True,cold_xchg=True,fex_source_hashes_match_vendor=True)))

if __name__=='__main__':main()
