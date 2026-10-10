"""Verify the pinned Mesa/Rust ABI before caching its libc-owned CPU blocks."""
from pathlib import Path
import re
import subprocess
from port_common import ROOT, sha, write_json
from native_heap.rust_patches import NAK_SHA256, PREFIX


def verify(base=Path('/home/blekjek/pes13-build')):
    library = base/'mesa-vulkan/install/opt/devkitpro/portlibs/switch/lib/libnak_rs.a'
    header = base/'mesa-switch/src/nouveau/compiler/nak.h'
    assert sha(library) == NAK_SHA256
    assert sha(header) == 'af327541a88c71080cd6032a9f04d1752bfd17bab97bbdaf7ef32d0ee534503e'
    declaration = re.search(r'nak_compile_shader\([^;]+;', header.read_text()).group()
    for arg in ('nir_shader *nir', 'bool dump_asm', 'const struct nak_compiler *nak',
                'nir_variable_mode robust2_modes', 'const struct nak_fs_key *fs_key', 'bool has_task_shader'):
        assert arg in declaration, arg
    sdk = '/opt/devkitpro/devkitA64/bin/aarch64-none-elf-'
    out = ROOT/'local/shader-v9-abi'
    out.mkdir(parents=True, exist_ok=True)
    disassembly = {}
    for name, member in {'shims':'nak_rs.c5h70ln7wzdbjp6iixzjga2ht.rcgu.o',
                         'system':'std-577dae050256c015.std.784034a803e5be6f-cgu.0.rcgu.o'}.items():
        obj = out/(name+'.o')
        obj.write_bytes(subprocess.check_output([sdk+'ar','p',str(library),member]))
        disassembly[name] = subprocess.check_output([sdk+'objdump','-dr',str(obj)], text=True)
    system = disassembly['system']
    def section(s, symbol):
        start = s.index('Disassembly of section .text.'+symbol+':')
        end = s.find('\nDisassembly of section ',start+1)
        return s[start:end if end>=0 else None]
    dealloc = section(system,PREFIX+'13___rdl_dealloc')
    instructions = re.findall(r'^\s*[0-9a-f]+:\s+[0-9a-f]{8}\s+(.+)$',dealloc,re.M)
    assert len(instructions)==1 and re.match(r'b\s+0 <free>',instructions[0]), dealloc
    assert 'R_AARCH64_JUMP26\tfree' in dealloc
    alloc = section(system,PREFIX+'11___rdl_alloc')
    assert 'R_AARCH64_JUMP26\tmalloc' in alloc and 'R_AARCH64_CALL26\tposix_memalign' in alloc
    for shim, target in (('12___rust_alloc','11___rdl_alloc'),('14___rust_dealloc','13___rdl_dealloc'),
                         ('14___rust_realloc','13___rdl_realloc'),('19___rust_alloc_zeroed','18___rdl_alloc_zeroed')):
        assert 'R_AARCH64_JUMP26\t'+PREFIX+target in section(disassembly['shims'],PREFIX+shim)
    evidence = out/'allocator-evidence.txt'
    evidence.write_text(declaration+'\n\n'+alloc+'\n'+dealloc)
    result = dict(status='PASS', library_sha256=sha(library), nak_header_sha256=sha(header),
        rust_dealloc_is_plain_free=True, rust_alloc_uses_malloc_or_posix_memalign=True,
        nak_signature=declaration, evidence_sha256=sha(evidence),
        sources={'tools/verify_shader_abi.py':sha(Path(__file__))})
    write_json(ROOT/'reports/low-window-v9-shader-abi.json', result)
    return result


if __name__ == '__main__':
    print(verify())
