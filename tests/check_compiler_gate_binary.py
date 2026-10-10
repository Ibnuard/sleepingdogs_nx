"""Deterministic five-thread interleaving through the actual DLL CompileBlock."""
import json
from check_compiler_decoder_binary import DecoderModel, DLL, L, ROOT
from fex_alloc import STUBS, reg
from unicorn import arm64_const as arm
from port_common import sha, write_json

class GateModel(DecoderModel):
    def __init__(self):
        self.gate_ready = False
        super().__init__()
        self.held = {}; self.stage = {}; self.contexts = {}; self.shared = set()
        self.slot_base = self.symbols['_ZN18SDFexCompilerLease5SlotsE']
        self.noop = STUBS + 0xb000
        handler, table = self.ctx + 0x1000, self.ctx + 0x1100
        self.writeq(self.ctx + L['syscall'], handler); self.writeq(handler, table)
        for i in range(64): self.writeq(table+i*8, self.noop)
        self.vm.mem_map(0x31000000, 0x50000)
        self.vm.mem_map(0x32000000, 0x50000)
        self.gate_ready = True

    def hook(self, vm, pc, size, user):
        if self.gate_ready:
            symbol = self.by_address.get(pc, '')
            if pc == self.noop: self.host_return(); return
            if self.hooks.get(pc) == '_vsnprintf':
                fmt = self.string(vm.reg_read(reg(2)))
                assert fmt == '[SD-COMPILER-WAIT] slots=4 waits=%llu'
                message = fmt.replace('%llu', str(self.readq(vm.reg_read(reg(3))))).encode()
                assert len(message)+1 <= vm.reg_read(reg(1))
                vm.mem_write(vm.reg_read(reg(0)), message+b'\0')
                vm.reg_write(reg(0),len(message)); self.host_return(); return
            if 'WritePriorityMutex5Mutex11lock_sharedE' in symbol:
                self.shared.add(self.current)
            if symbol == '_ZN7FEXCore11LookupCache9FindBlockEPNS_4Core19InternalThreadStateEy':
                assert self.current in self.held.values()
                self.stage[self.current] = 'lookup'
                vm.reg_write(reg(0), 0x456780); self.host_return(); vm.emu_stop(); return
            lock = vm.reg_read(reg(0))
            if self.slot_base <= lock < self.slot_base + 32:
                if symbol == '_ZNSt3__15mutex8try_lockEv':
                    ok = lock not in self.held
                    if ok: self.held[lock] = self.current
                    vm.reg_write(reg(0), int(ok)); self.host_return(); return
                if symbol == '_ZNSt3__15mutex4lockEv':
                    if lock in self.held:
                        assert self.current not in self.shared, 'Waiting compiler already holds invalidation lock'
                        self.stage[self.current] = 'waiting'; vm.emu_stop(); return
                    self.held[lock] = self.current; self.host_return(); return
                if symbol == '_ZNSt3__15mutex6unlockEv':
                    assert self.held.pop(lock) == self.current
                    self.host_return(); return
        super().hook(vm, pc, size, user)

    def start(self, n):
        self.current = n
        thread = 0x31000000+n*0x10000; frame = thread+0x4000
        self.writeq(thread+L['thread_ctx'], self.ctx); self.writeq(thread+L['thread_frame'], frame)
        self.writeq(frame+L['frame_thread'], thread)
        for i,v in enumerate((self.ctx,frame,self.code,500)): self.vm.reg_write(reg(i),v)
        self.vm.reg_write(arm.UC_ARM64_REG_SP,0x32000000+n*0x10000+0xf000)
        self.vm.reg_write(reg(30),self.stop)
        self.vm.emu_start(self.symbols[self.method('ContextImpl12CompileBlockE')],self.stop,count=200000)
        assert not self.trapped
        self.contexts[n]=self.vm.context_save()

    def resume(self,n,expected):
        self.current=n; self.vm.context_restore(self.contexts[n])
        self.vm.emu_start(self.vm.reg_read(arm.UC_ARM64_REG_PC),self.stop,count=200000)
        assert not self.trapped
        self.contexts[n]=self.vm.context_save()
        if expected=='done':
            assert self.vm.reg_read(arm.UC_ARM64_REG_PC)==self.stop
            assert self.vm.reg_read(reg(0))==0x456780
        else: assert self.stage[n]==expected

m=GateModel()
for i in range(4): m.start(i); assert m.stage[i]=='lookup'
assert len(m.held)==4
m.start(4); assert m.stage[4]=='waiting' and len(m.held)==4 and 4 not in m.shared
m.resume(0,'done'); assert len(m.held)==3
m.resume(4,'lookup'); assert len(m.held)==4 and 4 in m.shared
for i in range(1,5): m.resume(i,'done')
assert not m.held
report={'status':'PASS','dll_sha256':sha(DLL),'simultaneous_compilers':5,'permits':4,
        'fifth_waits_before_invalidation_lock':True,'released_permit_reused':True,'all_early_cache_returns_unlock':True,
        'boundaries':'NT calls, std::mutex scheduler and lookup result modeled. Actual CompileBlock, gate selection and RAII cleanup execute.',
        'hardware_tested':False}
write_json(ROOT/'reports/compiler-gate-binary-check.json',report); print(json.dumps(report))
