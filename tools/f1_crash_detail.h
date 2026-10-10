/* Bounded supplementary evidence after the primary fatal record is flushed.
 * No heap, stdio, Wine calls or waiting locks on these paths. */
#ifndef F1_CRASH_DETAIL_H
#define F1_CRASH_DETAIL_H
#include <unistd.h>
#define F1_NATIVE_BASE (F1_FATAL_BASE + F1_FATAL_BYTES)
#define F1_NATIVE_BYTES 4096
#define F1_RUST_BASE (F1_NATIVE_BASE + F1_NATIVE_BYTES)
static unsigned f1_native_text_busy, f1_native_text_size;
static char f1_native_text[512];
extern void wine_nx_f1_native_heap_counters(uint64_t out[7]);

static int f1_native_readable(uintptr_t p,size_t n,MemoryInfo *info)
{
    u32 page;
    return p && n && R_SUCCEEDED(svcQueryMemory(info,&page,p)) &&
        (info->perm & Perm_R) && p>=info->addr && info->size>=n &&
        p-info->addr<=info->size-n;
}
static void f1_native_capture(const void *data,size_t n)
{
    uintptr_t p=(uintptr_t)data;MemoryInfo info;
    if(!p || !n || n>UINTPTR_MAX-p) return;
    if(n>sizeof(f1_native_text)){p+=n-sizeof(f1_native_text);n=sizeof(f1_native_text);}
    if(__atomic_exchange_n(&f1_native_text_busy,1,__ATOMIC_ACQUIRE)) return;
    if(f1_native_readable(p,n,&info)) {
        unsigned keep=f1_native_text_size;
        if(keep>sizeof(f1_native_text)-n) keep=sizeof(f1_native_text)-n;
        for(unsigned i=0;i<keep;i++) f1_native_text[i]=f1_native_text[f1_native_text_size-keep+i];
        const volatile char *src=(const volatile char *)p;
        for(size_t i=0;i<n;i++) f1_native_text[keep+i]=src[i];
        f1_native_text_size=keep+n;
    }
    __atomic_store_n(&f1_native_text_busy,0,__ATOMIC_RELEASE);
}
extern ssize_t __real_write(int,const void *,size_t);
ssize_t __wrap_write(int fd,const void *data,size_t n)
{
    ssize_t result=__real_write(fd,data,n);
    if(fd==1 || fd==2) {
        int saved_errno=errno;
        /* Rust's final stderr is useful even if the native console is closed.
         * Checked reads also preserve EFAULT behavior for an invalid buffer. */
        f1_native_capture(data,result>0?(size_t)result:n);
        errno=saved_errno;
    }
    return result;
}

static void f1_native_frames(struct f1_text *b,uintptr_t fp)
{
    MemoryInfo info;uintptr_t start=fp;
    if((fp&15) || !f1_native_readable(fp,16,&info)) return;
    for(unsigned i=0;i<12;i++) {
        if(!fp || (fp&15) || fp<start || fp-start>1024*1024 ||
           fp<info.addr || fp-info.addr>info.size-16) break;
        const volatile uintptr_t *frame=(const volatile uintptr_t *)fp;
        uintptr_t next=frame[0],ret=frame[1];
        f1_text_add(b,"\nreturn_pc_");f1_text_number(b,i,10);f1_text_value(b,"=",ret);
        if(next<=fp) break;
        fp=next;
    }
}
static void f1_crash_native_detail(uintptr_t fp)
{
    static char record[F1_NATIVE_BYTES];
    struct f1_text b={record,0,sizeof(record)};uint64_t counters[7];
    f1_text_add(&b,"NATIVE_CONTEXT");
    f1_text_value(&b," thread=",threadGetCurHandle());
    f1_text_add(&b,"\nReturn PCs need minus 4 for AArch64 call-site lookup; bounded frame chain only.");
    f1_native_frames(&b,fp);
    wine_nx_f1_native_heap_counters(counters);
    static const char *names[]={"\nrust_attempts="," rust_recovered="," rust_failed=",
        " rust_returned="," rust_realloc="," rust_last_bytes="," rust_last_align="};
    for(unsigned i=0;i<7;i++) f1_text_value(&b,names[i],counters[i]);
    if(!__atomic_exchange_n(&f1_native_text_busy,1,__ATOMIC_ACQUIRE)) {
        f1_text_add(&b,"\nnative_text_tail=");
        for(unsigned i=0;i<f1_native_text_size;i++) {
            unsigned char c=f1_native_text[i];char one[2]={(char)(c>=32&&c<127?c:'?'),0};
            f1_text_add(&b,one);
        }
        __atomic_store_n(&f1_native_text_busy,0,__ATOMIC_RELEASE);
    } else f1_text_add(&b,"\nnative_text_busy=1");
    f1_text_add(&b,"\nEnd of supplementary record.\n");f1_text_finish(&b);
    fsFileWrite(&f1_crash_fatal,F1_NATIVE_BASE,record,sizeof(record),FsWriteOption_Flush);
}
void wine_nx_crash_rust_allocation(unsigned kind,size_t n,size_t align,size_t old,uintptr_t caller)
{
    int saved_errno=errno;
    if(!__atomic_load_n(&f1_crash_ready,__ATOMIC_ACQUIRE)) return;
    if(__atomic_exchange_n(&f1_crash_busy,1,__ATOMIC_ACQUIRE)) {
        __atomic_add_fetch(&f1_crash_dropped,1,__ATOMIC_RELAXED);return;
    }
    char record[512];struct f1_text b={record,0,sizeof(record)};
    f1_text_add(&b,"RUST_ALLOCATION_FAILED");
    f1_text_value(&b," kind=",kind);f1_text_value(&b," bytes=",n);
    f1_text_value(&b," alignment=",align);f1_text_value(&b," old_bytes=",old);
    f1_text_value(&b," caller=",caller);f1_text_value(&b," thread=",threadGetCurHandle());
    f1_text_value(&b," tick=",armGetSystemTick());
    f1_text_add(&b,"\nAllocation failed; this record alone does not mean the process terminated.\n");
    f1_text_finish(&b);
    Result rc=fsFileWrite(&f1_crash_events,F1_RUST_BASE,record,sizeof(record),FsWriteOption_Flush);
    if(R_FAILED(rc)) __atomic_store_n(&f1_crash_write_error,rc,__ATOMIC_RELAXED);
    __atomic_store_n(&f1_crash_busy,0,__ATOMIC_RELEASE);errno=saved_errno;
}
#endif
