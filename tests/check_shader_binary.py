"""Check linked ARM64 shader paths and execute the NAK wrapper's real machine code."""
from pathlib import Path
import argparse
import io
import struct
from elftools.elf.elffile import ELFFile
from check_low_window_binary import Machine, ROOT, REG
from port_common import sha, write_json


class ShaderWrapper(Machine):
    def __init__(self, elf, enabled, result):
        super().__init__(elf_path=elf)
        self.events=[]
        self.result=result
        self.vm.mem_write(self.symbols['sd_shader_cache_enabled'],struct.pack('<I',enabled))
        for name in ('nak_compile_shader','sd_shader_cache_begin','sd_shader_cache_end'):
            self.hooks[self.symbols[name]]=name

    def hook(self,vm,pc,size,arg):
        name=self.hooks.get(pc)
        if name in ('sd_shader_cache_begin','sd_shader_cache_end'):
            self.events.append(name)
            for i in range(19):vm.reg_write(REG[i],0xface0000+i)
            self.ret(0xfeed)
        elif name=='nak_compile_shader':
            assert [self.x(i) for i in range(6)]==[1,1,2,123,3,1]
            self.events.append(name)
            self.ret(self.result)
        else:super().hook(vm,pc,size,arg)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--elf',type=Path,default=ROOT/'local/symbols/sleepingdogs-low-window-v9.elf')
    args=parser.parse_args()
    elf=ELFFile(io.BytesIO(args.elf.read_bytes()))
    symbols={s.name:s for s in elf.get_section_by_name('.symtab').iter_symbols() if s['st_size']}
    text=elf.get_section_by_name('.text');data=text.data();base=text['sh_addr']
    def branches(name):
        sym=symbols[name];start=sym['st_value'];offset=start-base
        result=[]
        for at in range(0,sym['st_size']-3,4):
            word=struct.unpack_from('<I',data,offset+at)[0]
            if word&0x7c000000==0x14000000:
                rel=word&0x3ffffff
                if rel&0x2000000:rel-=0x4000000
                result.append(start+at+4*rel)
        return result
    edges={}
    # This dedicated x86/FEXTendo runtime links the WoW64 thunks only.
    # Both generator ABIs are checked at source level by the host test.
    for arch in ('32',):
        for kind in ('Compute','Graphics'):
            name=f'thunk{arch}_vkCreate{kind}Pipelines'
            targets=branches(name)
            for dest in ('wine_nx_thread_pipeline_begin','wine_nx_thread_pipeline_end'):
                assert symbols[dest]['st_value'] in targets,(name,dest)
            edges[name]=['wine_nx_thread_pipeline_begin','wine_nx_thread_pipeline_end']
    wrap=symbols['__wrap_nak_compile_shader']['st_value']
    callers=[n for n,s in symbols.items() if s['st_info']['type']=='STT_FUNC' and
             s['st_shndx']==symbols['__wrap_nak_compile_shader']['st_shndx'] and wrap in branches(n)]
    assert callers,'Mesa never calls the wrapped NAK compiler'
    for name,dest in (('pes13_mesa_malloc','sd_shader_cache_take'),('pes13_mesa_free','sd_shader_cache_put'),
                       ('pes13_rust_alloc','sd_shader_cache_take'),('pes13_rust_dealloc','sd_shader_cache_put')):
        assert symbols[dest]['st_value'] in branches(name),(name,dest)
        edges[name]=[dest]
    cases=[]
    for enabled in (0,1):
        for result in (0,0x12345678000):
            m=ShaderWrapper(args.elf,enabled,result)
            assert m.call('__wrap_nak_compile_shader',1,1,2,123,3,1)==result
            expected=['nak_compile_shader'] if not enabled else ['sd_shader_cache_begin','nak_compile_shader','sd_shader_cache_end']
            assert m.events==expected,m.events
            cases.append(dict(enabled=enabled,result=result,events=m.events))
            m.close()
    report=dict(status='PASS',scope=__doc__,hardware_tested=False,elf_sha256=sha(args.elf),
        nak_wrapper_callers=callers,linked_edges=edges,compiled_wrapper_cases=cases,
        sources={'tests/check_shader_binary.py':sha(Path(__file__))})
    write_json(ROOT/'reports/low-window-v9-shader-binary.json',report)
    print('PASS: two linked WoW64 Vulkan thunk pairs, Mesa/Rust cache bindings, real NAK wrapper calls, and four ARM64 ABI/result cases',flush=True)


if __name__=='__main__':main()
