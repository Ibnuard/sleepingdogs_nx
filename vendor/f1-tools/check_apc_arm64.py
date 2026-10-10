"""Execute the APC entry machine code plus the packaged Wine PE dispatcher.

Run with Windows Python (Unicorn/pefile) and the WSL devkitA64 assembler.
The callback and NtContinue kernel boundary are mocked; this is not FEX or
Switch gameplay testing. Checks ABI, stack reuse, arguments and continuation.
"""
from pathlib import Path
import argparse
import ast
import re
import struct
import subprocess
import pefile
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
import unicorn.arm64_const as regs

ROOT = Path(__file__).resolve().parents[1]
X = [getattr(regs, f'UC_ARM64_REG_X{i}') for i in range(31)]
Q = [getattr(regs, f'UC_ARM64_REG_Q{i}') for i in range(32)]
SP, PC = regs.UC_ARM64_REG_SP, regs.UC_ARM64_REG_PC
ENTRY, RESUME, CALLBACK = 0x10000000, 0x10001000, 0x10002000
STACK, TOP, SOURCE, TEB = 0x20000000, 0x201f0000, 0x30001000, 0x987654320
SIZE, CTX = 0x3c0, 0x30


def wsl_path(path):
    return '/mnt/' + path.drive[0].lower() + path.as_posix()[2:]


def p64(data, offset, value):
    struct.pack_into('<Q', data, offset, value & ((1 << 64)-1))


def elf_function(path, name):
    data=path.read_bytes()
    assert data[:6]==b'\x7fELF\x02\x01'
    off=struct.unpack_from('<Q',data,40)[0]
    size,count=struct.unpack_from('<HH',data,58)
    sections=[struct.unpack_from('<IIQQQQIIQQ',data,off+i*size) for i in range(count)]
    for section in sections:
        if section[1]!=2:continue
        strings=sections[section[6]]
        names=data[strings[4]:strings[4]+strings[5]]
        for i in range(section[4],section[4]+section[5],section[9]):
            n,info,other,index,value,length=struct.unpack_from('<IBBHQQ',data,i)
            if names[n:names.find(b'\0',n)]!=name.encode():continue
            target=sections[index]
            start=target[4]+value-target[3]
            return data[start:start+length]
    raise AssertionError('ELF function missing: '+name)


def config(context=None):
    out = bytearray(SIZE)
    p64(out, 0, CALLBACK)
    for i, v in enumerate((0x7b7b60abcdef00, 0x12345678016eabcd, 0)):
        p64(out, 8+i*8, v)
    p64(out, 0x20, 1)
    if context is not None:
        out[CTX:] = context
    else:
        struct.pack_into('<I', out, CTX, 0x400017)  # ARM64 FULL | X18
    return bytes(out)


def run_case(code, pe, count=1, supplied=False, overlap=0, result=0xc0):
    uc = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    uc.mem_map(ENTRY, 0x10000);uc.mem_write(ENTRY, code)
    uc.mem_map(STACK, 0x200000)
    uc.mem_map(0x30000000, 0x10000)
    base = pe.OPTIONAL_HEADER.ImageBase
    uc.mem_map(base, (pe.OPTIONAL_HEADER.SizeOfImage+4095)&~4095)
    uc.mem_write(base, pe.get_memory_mapped_image())
    exports = {s.name.decode():base+s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name}
    dispatcher, ntcontinue = exports['KiUserApcDispatcher'], exports['NtContinue']
    initial = {r:0x55550000+i*0x100 for i,r in enumerate(X)}
    initial[X[30]] = RESUME
    for r,v in initial.items():uc.reg_write(r,v)
    vectors = {r:(0x123456789abcdef0+i)*((1 << 64)+1) for i,r in enumerate(Q)}
    for r,v in vectors.items():uc.reg_write(r,v)
    uc.reg_write(regs.UC_ARM64_REG_NZCV,0xa0000000)
    uc.reg_write(regs.UC_ARM64_REG_FPCR,0x400000)
    uc.reg_write(regs.UC_ARM64_REG_FPSR,0x10)
    uc.mem_write(TOP,b'\x6b'*4096)  # native caller frame must survive
    desired = None
    if supplied:
        desired=bytearray(0x390)
        struct.pack_into('<II',desired,0,0x400017,0xa0000000)
        for i,r in enumerate(X):p64(desired,8+i*8,initial[r])
        p64(desired,8,result)
        p64(desired,0x100,TOP);p64(desired,0x108,RESUME)
        for i,r in enumerate(Q):desired[0x110+i*16:0x120+i*16]=vectors[r].to_bytes(16,'little')
        struct.pack_into('<II',desired,0x310,0x400000,0x10)
    source = TOP-SIZE+overlap if overlap else SOURCE
    uc.mem_write(source,config(desired))
    caller_bytes=bytes(uc.mem_read(TOP,4096))
    uc.reg_write(SP,TOP-0x3000 if supplied else TOP)
    for r,v in zip(X[:5],(source,dispatcher,TEB,result if not supplied else 0xc0,not supplied)):
        uc.reg_write(r,int(v))
    delivered, saved, frame_addresses = 0, None, []
    done = False

    def hook(u, address, size, user):
        nonlocal delivered, saved, done
        if address == CALLBACK:
            delivered+=1
            frame=u.reg_read(SP);frame_addresses.append(frame)
            assert frame==TOP-SIZE, (hex(frame),delivered)
            assert u.reg_read(X[18])==TEB
            assert tuple(u.reg_read(r) for r in X[:3])==(0x7b7b60abcdef00,0x12345678016eabcd,0)
            assert u.reg_read(X[3])==frame+CTX
            context=bytes(u.mem_read(frame+CTX,0x390))
            if saved is None:saved=context
            else:assert context==saved, 'nested dispatch changed original continuation'
            if desired is not None:assert context==bytes(desired)
            else:
                assert struct.unpack_from('<I',context,0)[0]==0x400017
                assert struct.unpack_from('<Q',context,8)[0]==result
                for i in range(18,31):assert struct.unpack_from('<Q',context,8+i*8)[0]==initial[X[i]]
                assert struct.unpack_from('<QQ',context,0x100)==(TOP,RESUME)
                for i,r in enumerate(Q):assert int.from_bytes(context[0x110+i*16:0x120+i*16],'little')==vectors[r]
            # Simulate callback return; the actual PE dispatcher calls NtContinue.
            for r in X[:18]:u.reg_write(r,0xdeadbeef)
            u.reg_write(PC,u.reg_read(X[30]))
        elif address == ntcontinue:
            assert u.reg_read(X[1])==1
            context=bytes(u.mem_read(u.reg_read(X[0]),0x390))
            assert context==saved
            if delivered < count:
                # Like the actual NtContinueEx: drain the next APC with the
                # supplied original context, from a deeper native call frame.
                local=u.reg_read(SP)-0x1000
                u.mem_write(local,config(context));u.reg_write(SP,local-0x100)
                for r,v in zip(X[:5],(local,dispatcher,TEB,0xc0,0)):u.reg_write(r,v)
                u.reg_write(PC,ENTRY)
            else:
                # Kernel restore is outside Unicorn. Consume the exact full
                # context passed to the existing Horizon NtContinue path.
                for i,r in enumerate(X):u.reg_write(r,struct.unpack_from('<Q',context,8+i*8)[0])
                for i,r in enumerate(Q):u.reg_write(r,int.from_bytes(context[0x110+i*16:0x120+i*16],'little'))
                u.reg_write(SP,struct.unpack_from('<Q',context,0x100)[0])
                u.reg_write(PC,struct.unpack_from('<Q',context,0x108)[0])
        elif address == RESUME:
            done=True;u.emu_stop()

    uc.hook_add(UC_HOOK_CODE,hook)
    uc.emu_start(ENTRY,RESUME+4,count=1000000)
    assert done and delivered==count
    assert uc.reg_read(SP)==TOP and uc.reg_read(X[0])==result
    for i in range(18,31):assert uc.reg_read(X[i])==initial[X[i]]
    assert bytes(uc.mem_read(TOP,4096))==caller_bytes
    assert len(set(frame_addresses))==1


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--elf',type=Path)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    text=(ROOT/'tools/f1_apc_dispatch.inc').read_text()
    asm=text.split('__asm__(',1)[1].split('\n);',1)[0]
    asm=''.join(ast.literal_eval(s) for s in re.findall(r'^\s*("(?:[^"\\]|\\.)*")',asm,re.M))
    path=args.output/'apc-entry.S';path.write_text('.text\n'+asm)
    obj=args.output/'apc-entry.o';binary=args.output/'apc-entry.bin'
    tc='/opt/devkitpro/devkitA64/bin/aarch64-none-elf-'
    for cmd in ([tc+'as','-o',wsl_path(obj),wsl_path(path)],
                [tc+'objcopy','-O','binary','-j','.text',wsl_path(obj),wsl_path(binary)]):
        subprocess.run(['wsl','-d','Ubuntu','-u','blekjek','--',*cmd],check=True)
    pe=pefile.PE(str(ROOT/'dist/f1-fex-ready/switch/f1-fex/drive_c/windows/system32/ntdll.dll'))
    code=binary.read_bytes()
    if args.elf:
        assert elf_function(args.elf,'f1_enter_apc')==code, 'tested ARM64 bytes differ from built ELF'
    run_case(code,pe)
    run_case(code,pe,result=0)  # NtTestAlert's success return
    run_case(code,pe,count=2048)  # queued completions must not grow the stack
    run_case(code,pe,supplied=True,result=0x42)
    run_case(code,pe,supplied=True,overlap=-16,result=0x42)
    run_case(code,pe,supplied=True,overlap=16,result=0x42)
    print('PASS: actual ARM64 entry and packaged PE KiUserApcDispatcher; 64-bit arguments, TEB, saved registers/SIMD, callback return, explicit context, overlapping copy and 2048 APCs with constant stack use.')


if __name__=='__main__':main()
