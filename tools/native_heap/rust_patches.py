"""Bind CPU-only fallback to the four verified Rust allocation shims.

Do not guess a new Rust ABI or rewrite the installed Mesa library. The exact
archive has four separate allocation shim functions; ld wraps references to
them and the wrappers call the original functions through __real_.
"""
import hashlib
NAK_SHA256='f56fc46711c90330a9d68ff78cf00fd31a2525f922b6a90b77366d044542381f'
PREFIX='_RNvCsdBezzDwma51_7___rustc'
SHIMS={
    'alloc':('12___rust_alloc','void *','size_t,size_t'),
    'dealloc':('14___rust_dealloc','void','void *,size_t,size_t'),
    'realloc':('14___rust_realloc','void *','void *,size_t,size_t,size_t'),
    'alloc_zeroed':('19___rust_alloc_zeroed','void *','size_t,size_t'),
}
def apply(library,feature,cmake):
    assert hashlib.sha256(library.read_bytes()).hexdigest()==NAK_SHA256,'Unreviewed Rust archive/ABI'
    declarations=['/* Generated from hash-verified Rust 1.93.1 allocation shims. */','#include <stddef.h>']
    options=[]
    for name,(suffix,result,args) in SHIMS.items():
        symbol=PREFIX+suffix
        declarations.append(f'extern {result} fx_rust_real_{name}({args}) __asm__("__real_{symbol}");')
        options += [f'-Wl,--wrap={symbol}',f'-Wl,--defsym=__wrap_{symbol}=pes13_rust_{name}']
    header=feature/'fextendo_rust_symbols.h'
    header.write_text('\n'.join(declarations)+'\n')
    cmake.write_text(cmake.read_text()+'\ntarget_link_options(wine-nx-runtime PRIVATE '+' '.join(options)+')\n')
    return {'libnak_rs_sha256':NAK_SHA256,'header_sha256':hashlib.sha256(header.read_bytes()).hexdigest(),
            'symbols':{name:PREFIX+item[0] for name,item in SHIMS.items()}}
