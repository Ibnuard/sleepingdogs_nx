"""Bind the F1 GPU fallback to the exact Nouveau object and newlib chunk ABI.

Installed archives stay intact. Only the copied object's memalign, free and
nvMapCreate imports change; reversing objcopy must reproduce every byte.
"""
import hashlib, subprocess

LIB_SHA256 = 'ca9c82e03b04fb385004d6f7d47bd8357e107f7a35481f08e06f7b870f941315'
OBJECT = 'nouveau_horizon_memory.c.o'
OBJECT_SHA256 = '2e7dc31762b884aa5396518505fc442f4408be596f033f38d131bf3907d89dfb'
NEWLIB = {
    'libc_a-malignr.o': '05d2c3058952bad1cdadc5f86e751b7070e3fbcb211f51c4253e1beb20a93cb6',
    'libc_a-mallocr.o': '72c085e5dca9e98070c63cdc03763144b4e4dec55b3b0aa9aa8032b9d626cd9a',
    'libc_a-freer.o': '1f37d97c49866db92852720cd4242a63034d417259ba3e0198f852a7705d1388',
    'libc_a-mallinfor.o': '8524c1052d898ac7b35443b163361c8b22c9380b82b7d7e3bdd46edc566cf70c',
}

def sha(p):
    with p.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()

def apply(library, feature, cmake, sdk):
    assert sha(library) == LIB_SHA256, 'Unreviewed Nouveau build'
    feature.mkdir(exist_ok=True)
    tools = sdk/'devkitA64/bin'
    ar, objcopy = (tools/('aarch64-none-elf-'+n) for n in ('ar', 'objcopy'))
    libc = sdk/'devkitA64/aarch64-none-elf/lib/libc.a'
    pins = {}
    for name, expected in NEWLIB.items():
        data = subprocess.check_output([ar, 'p', libc, name])
        pins[name] = hashlib.sha256(data).hexdigest()
        assert pins[name] == expected, 'Unreviewed newlib allocator ABI: '+name
    original = feature/'nouveau-memory-original.o'
    original.write_bytes(subprocess.check_output([ar, 'p', library, OBJECT]))
    assert sha(original) == OBJECT_SHA256
    patched, restored = feature/'nouveau-memory-f1.o', feature/'nouveau-memory-restored.o'
    replacements = {'memalign': 'wine_nx_f1_gpu_memalign',
                    'free': 'wine_nx_f1_gpu_free',
                    'nvMapCreate': 'wine_nx_f1_gpu_nvmap_create'}
    subprocess.run([objcopy, *[f'--redefine-sym={a}={b}' for a,b in replacements.items()],
                    original, patched], check=True)
    subprocess.run([objcopy, *[f'--redefine-sym={b}={a}' for a,b in replacements.items()],
                    patched, restored], check=True)
    assert original.read_bytes() == restored.read_bytes()
    cmake.write_text(cmake.read_text()+f'\nset_source_files_properties("{patched}" PROPERTIES EXTERNAL_OBJECT TRUE GENERATED TRUE)\n'
                    +f'target_sources(wine-nx-runtime PRIVATE "{patched}" source/f1_gpu_heap.c)\n')
    return {'library_sha256': LIB_SHA256, 'object_sha256': OBJECT_SHA256,
            'bound_object_sha256': sha(patched), 'newlib_objects': pins, 'imports': replacements}
