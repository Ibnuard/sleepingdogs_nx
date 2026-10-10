"""Route only the pinned Mesa ralloc object's CPU allocation imports.

Keep every installed library intact. The explicit object supplies the same
public Mesa functions, so the archive's old member is not extracted by ld.
Instructions and all other imports are byte-identical after objcopy.
"""
import hashlib,subprocess

LIB_SHA256='f4cb6feafd6ccc203c90debe720d660fd4007f1f5fb833a65d061da579c16d0a'
OBJ_SHA256='f64b6d5b68aa217316bd68d8e259d6e1cc6be218d263aa5ae7e1f9b6d63ef6d6'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def apply(library,feature,cmake,sdk):
    assert sha(library)==LIB_SHA256,'Unreviewed Mesa allocator library'
    tools=sdk/'devkitA64/bin';ar=tools/'aarch64-none-elf-ar';objcopy=tools/'aarch64-none-elf-objcopy'
    members=subprocess.check_output([str(ar),'t',str(library)],text=True).splitlines()
    assert members.count('ralloc.c.o')==1,members
    original=feature/'mesa-ralloc-original.o'
    original.write_bytes(subprocess.check_output([str(ar),'p',str(library),'ralloc.c.o']))
    assert sha(original)==OBJ_SHA256,'Unreviewed Mesa allocator object'
    patched=feature/'mesa-ralloc-recovery.o'
    replacements={n:'pes13_mesa_'+n for n in ('malloc','realloc','free')}
    command=[str(objcopy)]+[f'--redefine-sym={a}={b}' for a,b in replacements.items()]+[str(original),str(patched)]
    subprocess.run(command,check=True)
    restored=feature/'mesa-ralloc-restored.o'
    subprocess.run([str(objcopy)]+[f'--redefine-sym={b}={a}' for a,b in replacements.items()]+[str(patched),str(restored)],check=True)
    assert original.read_bytes()==restored.read_bytes(),'Changes outside the approved symbol bindings'
    cmake.write_text(cmake.read_text()+f'\nset_source_files_properties("{patched}" PROPERTIES EXTERNAL_OBJECT TRUE GENERATED TRUE)\n'
                    +f'target_sources(wine-nx-runtime PRIVATE "{patched}")\n')
    return {'library_sha256':LIB_SHA256,'object_sha256':OBJ_SHA256,'bound_object_sha256':sha(patched),'imports':replacements}
