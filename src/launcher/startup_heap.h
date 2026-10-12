/* LGPL-2.1-or-later. Pre-main libnx heap policy for the memory-mode gate.
 * No malloc, stdio, filesystem, applet services or TLS-dependent errno here.
 * Compatible launches retain the original loader heap / 256-MiB default.
 */
#ifndef FEXTENDO_STARTUP_HEAP_H
#define FEXTENDO_STARTUP_HEAP_H
extern size_t __nx_heap_size;
extern char *fake_heap_start,*fake_heap_end;
extern void NX_NORETURN __nx_exit(Result,LoaderReturnFn);

void __libnx_initheap(void){
    /* libnx calls this before __appInit and C/C++ constructors, not at main. */
    int compatible=sd_boot_memory_compatible();
    void *base=NULL;size_t size=0;
    if(envHasHeapOverride()){
        base=envGetHeapOverrideAddr();size=envGetHeapOverrideSize();
    }else{
        size=compatible?__nx_heap_size:128u*1024u*1024u;
        if(!size)size=256u*1024u*1024u;
        Result rc=svcSetHeapSize(&base,size);
        /* The checker/GUI needs artwork but no Wine allocations. Do not abort for a
         * 256-MiB request in an applet with a smaller memory allowance. */
        while(R_FAILED(rc)&&!compatible&&size>2u*1024u*1024u){
            size=(size/2)&~(size_t)(2u*1024u*1024u-1);
            rc=svcSetHeapSize(&base,size);
        }
        if(R_FAILED(rc))__nx_exit(rc,envGetExitFuncPtr());
    }
    /* Respect ownership of a heap supplied by hbloader. Never resize it. */
    if(!base||!size||(uintptr_t)base>UINTPTR_MAX-size)
        __nx_exit(MAKERESULT(Module_Libnx,LibnxError_HeapAllocFailed),envGetExitFuncPtr());
    fake_heap_start=base;fake_heap_end=(char *)base+size;
}
#endif
