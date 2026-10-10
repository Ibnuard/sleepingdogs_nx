"""Execute the shipped ARM64 cache identity paths, including a failing v14 control.

nvk_CreateInstance runs as a complete function with modeled allocation, Vulkan
initialization and environment/DRI services. The inlined physical-device cache
initializer runs from its verified instruction boundary with a fixture pdev.
Actual build-ID conversion, BLAKE3 hashing and hex formatting execute unmodified.
Disk I/O is intercepted at disk_cache_create to inspect the namespace arguments.
This is an identity regression test, not a Vulkan/GPU or gameplay test.
"""
from pathlib import Path
import io
import json
import struct
from elftools.elf.elffile import ELFFile
from unicorn import arm64_const as arm
from check_low_window_binary import Machine, ROOT, REG
from port_common import sha, write_json

OLD_ID='e1ebad7dfe18474eca84a5f7f4251d1a0d028b8c'
V14_ID='8b8d3ff1c7937a1f55443fdadf6c739048110e18'
OLD_ELF='1b919a9c90291ec3054a716b1400bd080259e29451c60539217d36e27d916f5d'


class CacheIdentity(Machine):
    def __init__(self, elf, layout):
        super().__init__(elf_path=elf)
        self.layout=layout
        self.area=0x630000000
        self.vm.mem_map(self.area,0x100000)
        self.instance=self.area+0x1000
        self.pdev=self.area+0x10000
        self.allocator=self.area+0x100
        self.callback=self.stop+0x100
        self.q(self.allocator+8,self.callback)
        self.hooks[self.callback]='fixture_allocate'
        self.updates=[]
        self.disk=None
        self.end=None
        self.allocations=[]
        self.compiler_flags=0x1234
        for name in ('vk_instance_dispatch_table_from_entrypoints','vk_instance_init',
                     'os_get_option','nvk_parse_dri_options',
                     'nvk_physical_device_compiler_flags','blake3_hasher_update',
                     'disk_cache_create'):
            self.hooks[self.symbols[name]]=name
        e=ELFFile(io.BytesIO(elf.read_bytes()))
        symbols={s.name:s for s in e.get_section_by_name('.symtab').iter_symbols()}
        sym=symbols['nvk_create_physical_device_from_nvkmd']
        section=e.get_section(sym['st_shndx'])
        off=sym['st_value']-section['sh_addr']
        data=section.data()[off:off+sym['st_size']]
        calls={}
        for i in range(0,len(data)-3,4):
            w=struct.unpack_from('<I',data,i)[0]
            if w&0xfc000000!=0x94000000:continue
            rel=w&0x3ffffff
            if rel&0x2000000:rel-=0x4000000
            at=self.bias+sym['st_value']+i
            calls.setdefault(at+4*rel,[]).append((at,i))
        init_calls=calls[self.symbols['blake3_hasher_init']]
        disk_calls=calls[self.symbols['disk_cache_create']]
        assert len(init_calls)==len(disk_calls)==1
        at,i=init_calls[0]
        # GCC inlines the cache initializer here. Verify the exact two setup
        # instructions before entering; never infer registers on a new compiler.
        assert struct.unpack_from('<II',data,i-8)==(0x911f63e0,0xf9402ab4)
        # add x0, sp, #0x7d8; ldr x20, [x21, #80]. x21 is the fixture pdev.
        assert layout['pdev_instance_offset']==80
        self.entry=at-8
        self.cache_end=disk_calls[0][0]+4
        assert 0<self.cache_end-self.entry<1024

    def hook(self,vm,pc,size,arg):
        name=self.hooks.get(pc)
        if self.end is not None and pc==self.end:
            self.returned=True;vm.emu_stop();return
        if name=='fixture_allocate':
            assert self.x(1)==self.layout['instance_size'] and self.x(2)==8
            self.allocations.append(self.x(1))
            vm.mem_write(self.instance,bytes(self.layout['instance_size']))
            self.ret(self.instance)
        elif name in ('vk_instance_dispatch_table_from_entrypoints','vk_instance_init',
                      'os_get_option','nvk_parse_dri_options'):
            self.ret(0)
        elif name=='nvk_physical_device_compiler_flags':
            assert self.x(0)==self.pdev
            self.ret(self.compiler_flags)
        elif name=='blake3_hasher_update':
            self.updates.append(bytes(vm.mem_read(self.x(1),self.x(2))).hex())
            # Execute the real hash function after observing its input.
        elif name=='snprintf':
            assert self.text(self.x(2))=='nvk_%04x' and self.x(1)==10
            value=('nvk_%04x'%self.x(3)).encode()
            vm.mem_write(self.x(0),value+b'\0');self.ret(len(value))
        elif name=='disk_cache_create':
            assert self.disk is None
            self.disk=dict(renderer=self.text(self.x(0)),timestamp=self.text(self.x(1)),
                           flags=self.x(2))
            self.ret(0)
        else:super().hook(vm,pc,size,arg)

    def run(self):
        output=self.area+0x300
        assert self.call('nvk_CreateInstance',self.area+0x400,self.allocator,output)==0
        assert self.uq(output)==self.instance and self.allocations==[self.layout['instance_size']]
        instance_id=bytes(self.vm.mem_read(self.instance+self.layout['build_sha_offset'],32)).hex()
        self.q(self.pdev+self.layout['pdev_instance_offset'],self.instance)
        self.vm.mem_write(self.pdev+self.layout['chipset_offset'],struct.pack('<H',0x12b))
        self.vm.reg_write(REG[21],self.pdev)
        self.vm.reg_write(arm.UC_ARM64_REG_SP,self.stack+0xe000)
        self.vm.reg_write(REG[30],self.stop)
        self.end=self.cache_end;self.returned=False
        self.vm.emu_start(self.entry,0,count=2000000)
        assert self.returned and self.disk
        assert self.disk['renderer']=='nvk_012b' and self.disk['flags']==self.compiler_flags
        assert self.disk['timestamp']==instance_id
        assert len(self.updates)==3 and self.updates[1]=='2b01'
        assert self.updates[2]==struct.pack('<Q',self.compiler_flags).hex()
        assert len(instance_id)==64 and len(self.updates[0])==40
        uuid=bytes(self.vm.mem_read(self.pdev+self.layout['pipeline_uuid_offset'],16)).hex()
        assert uuid!='00'*16
        return dict(instance_build_sha=instance_id,pipeline_build_id=self.updates[0],
                    pipeline_uuid=uuid,disk_cache=self.disk,
                    identities_match=instance_id==self.updates[0].ljust(64,'0'),
                    logs=self.logs,cache_block_entry=hex(self.entry-self.bias),
                    cache_block_end=hex(self.cache_end-self.bias))


def main():
    layout_path=ROOT/'dist/low-window-gm20b-cache-fix/layout.json'
    layout=json.loads(layout_path.read_text())
    native_path=ROOT/'dist/low-window-gm20b-cache-fix/native.json'
    native=json.loads(native_path.read_text())
    cases={}
    for version,digest in (('v14',OLD_ELF),('v141',native['elf_sha256'])):
        elf=ROOT/f'local/symbols/sleepingdogs-low-window-{version}.elf'
        assert sha(elf)==digest
        m=CacheIdentity(elf,layout)
        try:cases[version]=dict(elf_sha256=digest,**m.run())
        finally:m.close()
    old,new=cases['v14'],cases['v141']
    assert old['instance_build_sha']==OLD_ID.ljust(64,'0')
    assert old['pipeline_build_id']==V14_ID and not old['identities_match']
    new_id=native['cache_id']
    assert new_id not in (OLD_ID,V14_ID)
    assert new['instance_build_sha']==new_id.ljust(64,'0') and new['identities_match']
    assert new['pipeline_build_id']==new_id and old['pipeline_uuid']!=new['pipeline_uuid']
    assert old['disk_cache']['timestamp']!=new['disk_cache']['timestamp']
    assert any('[SD-NVK-V14.1] instance/disk cache_id='+new_id in s for s in new['logs'])
    sources={p.relative_to(ROOT).as_posix():sha(p) for p in (
        Path(__file__),ROOT/'tests/check_low_window_binary.py',layout_path)}
    write_json(ROOT/'reports/low-window-v141-cache-binary.json',dict(status='PASS',
        scope=__doc__,cases=cases,negative_control_detected=True,cache_fix_verified=True,
        native_receipt_sha256=sha(native_path),sources=sources,hardware_tested=False))
    print('PASS: actual ARM64 v14 mismatched IDs reproduced; v14.1 disk/pipeline identities agree',flush=True)


if __name__=='__main__':main()
