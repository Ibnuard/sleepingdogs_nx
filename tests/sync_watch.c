/* Host fixtures for the actual collector and Wine bridge. */
#include <assert.h>
#include <pthread.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef struct { uint32_t Eax,Ebx,Ecx,Edx,Esi,Edi,Ebp,Esp,Eip; } I386_CONTEXT;
static I386_CONTEXT cpu;
static unsigned char stack_memory[1024],queue_memory[352],object_memory[32],handle_memory[32];
static unsigned memory_reads,log_lines,invalid_logs,create_logs,close_logs,bad_signature,failed_reads;
static unsigned concurrent_mode;
static int f1_startup_watch_enabled;
typedef struct { struct { uintptr_t UniqueThread; } ClientId; void *TlsSlots[2]; } TEB;
static TEB teb;
static TEB *current_teb;
static unsigned cpu_area_calls,wrong_machine;
#define WOW64_TLS_CPURESERVED 1
#define IMAGE_FILE_MACHINE_I386 0x14c
#define HandleToULong(x) ((unsigned)(x))
static void *get_cpu_area(unsigned machine) {
    cpu_area_calls++;
    assert(machine==0x14c);
    /* Match Wine's precondition instead of hiding an early startup fault. */
    assert(current_teb && current_teb->TlsSlots[WOW64_TLS_CPURESERVED]);
    return wrong_machine ? NULL : &cpu;
}
#define NtCurrentTeb() (current_teb)
static uint64_t armGetSystemTick(void) { return 1234; }
static void NtCreateSemaphore(void) {}
static void NtOpenSemaphore(void) {}
static void NtClose(void) {}
static void NtWaitForSingleObject(void) {}
static size_t virtual_uninterrupted_read_memory(const void *,void *,size_t);
static void wine_nx_runtime_trace(const char *);
#include "sd_sync_bridge.inc"

static void outside_mutex(void) {
    if (concurrent_mode) return;
    assert(pthread_mutex_trylock(&sd_sync_mutex)==0);
    pthread_mutex_unlock(&sd_sync_mutex);
}
static size_t virtual_uninterrupted_read_memory(const void *input,void *out,size_t size) {
    uint64_t address=(uintptr_t)input;outside_mutex();
    __atomic_add_fetch(&memory_reads,1,__ATOMIC_RELAXED);
    if (failed_reads) return 0;
    const unsigned char wait_code[]={0x8b,0x01,0x6a,0xff,0x50,0xff,0x15,0xc4,0x11,0x0e,0x01,0xc3};
    const unsigned char queue_code[]={0x8b,0x4c,0xbe,0x78,0x51};
    const unsigned char wine_code[]={0x66,0x90,0x55,0x89,0xe5,0x56};
    const struct { uint64_t address; const void *data; size_t size; } regions[]={
        {0x10000,stack_memory,sizeof(stack_memory)}, {0x30001000,queue_memory,sizeof(queue_memory)},
        {0x30002000,object_memory,sizeof(object_memory)}, {0x6d4ffff0,handle_memory,sizeof(handle_memory)},
        {0xbb6f30,wait_code,sizeof(wait_code)}, {0xbb8730,queue_code,sizeof(queue_code)},
        {0x7b05e420,wine_code,sizeof(wine_code)} };
    for (unsigned i=0;i<sizeof(regions)/sizeof(regions[0]);i++) {
        if(address>=regions[i].address && address-regions[i].address<=regions[i].size &&
           size<=regions[i].size-(address-regions[i].address)) {
            memcpy(out,(const char *)regions[i].data+(address-regions[i].address),size);
            if(bad_signature && address==0x7b05e420) memset(out,0,size);
            return size;
        }
    }
    return 0;
}
static void wine_nx_runtime_trace(const char *line) {
    outside_mutex();log_lines++;
    if(strstr(line,"kind=invalid-wait")) invalid_logs++;
    if(strstr(line,"kind=create")) create_logs++;
    if(strstr(line,"kind=close")) close_logs++;
}
static void put(unsigned char *memory,unsigned offset,uint32_t value) { memcpy(memory+offset,&value,4); }
static void reset(void) {
    memset(sd_sync_events,0,sizeof(sd_sync_events));memset(sd_sync_handles,0,sizeof(sd_sync_handles));
    memset(sd_sync_failures,0,sizeof(sd_sync_failures));
    sd_sync_written=sd_sync_read=sd_sync_dropped=0;sd_sync_handle_overflow=sd_sync_failure_count=0;
    sd_sync_last_created=sd_sync_create_serial=sd_sync_last_invalid=sd_sync_invalid_taken=0;
    memory_reads=log_lines=invalid_logs=create_logs=close_logs=bad_signature=failed_reads=concurrent_mode=0;
    memset(stack_memory,0,sizeof(stack_memory));memset(queue_memory,0,sizeof(queue_memory));
    memset(object_memory,0,sizeof(object_memory));memset(handle_memory,0,sizeof(handle_memory));
    cpu=(I386_CONTEXT){.Edi=2,.Esp=0x10100,.Ebp=0x10180,.Eip=0x7bc4d4ac};
    put(stack_memory,0x17c,0x30001000);put(stack_memory,0x184,0xbb6f3b);
    put(queue_memory,0x80,0x30002000);put(object_memory,0,0x6d4ffff0);
    f1_startup_watch_enabled=1;
    teb=(TEB){.ClientId={4},.TlsSlots={[WOW64_TLS_CPURESERVED]=&cpu}};
    current_teb=&teb;cpu_area_calls=wrong_machine=0;
}
static void after(unsigned kind,uint64_t handle,uint32_t status) {
    uint64_t serial=sd_sync_create_serial;
    void *handler=kind==SD_SYNC_CREATE?(void *)NtCreateSemaphore:kind==SD_SYNC_CLOSE?(void *)NtClose:(void *)NtWaitForSingleObject;
    if(kind==SD_SYNC_CREATE && !(status&0x80000000u)) wine_nx_sd_sync_created_handle(handle);
    sd_sync_after_syscall(handler,(uintptr_t)handle,0,1000,status,serial);
}
static void *stress(void *arg) {
    unsigned n=(unsigned)(uintptr_t)arg;
    struct sd_sync_cpu snapshot={.esp=0x10100,.ebp=0x10180};
    for(unsigned i=0;i<1000;i++) {
        uint64_t handle=0x400+n*4;
        sd_sync_note(SD_SYNC_CREATE,n+1,handle,0,0,1000,i,&snapshot,sd_sync_guest_read);
        sd_sync_note(SD_SYNC_CLOSE,n+1,handle,0,0,0,i,&snapshot,sd_sync_guest_read);
    }
    return NULL;
}
int main(void) {
    reset();current_teb=NULL;
    after(SD_SYNC_CLOSE,0x804,0);after(SD_SYNC_CREATE,0x800,0);
    after(SD_SYNC_INVALID_WAIT,0x6d4ffff0,0xc0000008);
    assert(!cpu_area_calls&&!sd_sync_written&&!memory_reads&&!sd_sync_invalid_taken);
    puts("PASS missing native TEB skips capture");
    reset();teb.TlsSlots[WOW64_TLS_CPURESERVED]=NULL;
    after(SD_SYNC_CLOSE,0x804,0);after(SD_SYNC_CREATE,0x800,0);
    sd_sync_after_syscall((void *)NtOpenSemaphore,0x800,0,0,0,0);
    after(SD_SYNC_INVALID_WAIT,0x6d4ffff0,0xc0000008);
    assert(!cpu_area_calls&&!sd_sync_written&&!memory_reads&&!sd_sync_invalid_taken);
    teb.TlsSlots[WOW64_TLS_CPURESERVED]=&cpu;
    after(SD_SYNC_CREATE,0x800,0);after(SD_SYNC_CLOSE,0x800,0);
    after(SD_SYNC_INVALID_WAIT,0x6d4ffff0,0xc0000008);
    assert(cpu_area_calls==3&&sd_sync_written==3&&sd_sync_invalid_taken==1);
    puts("PASS loader before WoW64 CPU setup skips capture, then records normally");
    reset();wrong_machine=1;
    after(SD_SYNC_INVALID_WAIT,0x6d4ffff0,0xc0000008);
    assert(cpu_area_calls==1&&!sd_sync_written&&!memory_reads&&!sd_sync_invalid_taken);
    wrong_machine=0;after(SD_SYNC_INVALID_WAIT,0x6d4ffff0,0xc0000008);
    assert(sd_sync_written==1&&sd_sync_invalid_taken==1);
    puts("PASS absent x86 context does not consume first-invalid evidence");
    reset();f1_startup_watch_enabled=0;
    after(SD_SYNC_CREATE,0x800,0);after(SD_SYNC_INVALID_WAIT,0x6d4ffff0,0xc0000008);
    assert(!sd_sync_written&&!memory_reads);puts("PASS GUI/expired observation does no capture");
    reset();after(SD_SYNC_CLOSE,0x804,0);assert(!sd_sync_written&&!memory_reads);
    after(SD_SYNC_CREATE,0x800,0);after(SD_SYNC_CLOSE,0x800,0xc0000008);after(SD_SYNC_CLOSE,0x800,0);
    after(SD_SYNC_CLOSE,0x800,0);after(SD_SYNC_CREATE,0x800,0);after(SD_SYNC_CLOSE,0x800,0);
    assert(sd_sync_written==5);wine_nx_sd_sync_report();assert(create_logs==2&&close_logs==3);
    assert(!sd_sync_handles[0].handle);puts("PASS lifecycle, failed close, untracked close, handle reuse");
    reset();after(SD_SYNC_CREATE,0x800,0);after(SD_SYNC_CREATE,0x804,0);
    after(SD_SYNC_CLOSE,0x800,0);after(SD_SYNC_CREATE,0x804,0);
    unsigned live=0;for(unsigned i=0;i<SD_SYNC_HANDLES;i++)live+=sd_sync_handles[i].handle==0x804;
    assert(live==1);puts("PASS duplicate handle does not consume a second registry slot");
    reset();after(SD_SYNC_CREATE,0x800,0xc0000017);assert(sd_sync_events[0].handle==0&&!sd_sync_handles[0].handle);
    puts("PASS failed create cannot reuse stale output handle");
    reset();I386_CONTEXT before=cpu;
    after(SD_SYNC_INVALID_WAIT,0x6d4ffff0,0xc0000008);
    struct sd_sync_event *e=&sd_sync_events[0];
    assert(e->queue_ok&&e->queue_address==0x30001000&&e->object_ok&&e->object[0]==0x6d4ffff0);
    assert(e->slot_index==2&&e->handle_memory_ok&&!memcmp(&before,&cpu,sizeof(cpu)));
    unsigned reads=memory_reads;for(unsigned i=0;i<100000;i++)after(SD_SYNC_INVALID_WAIT,0x6d4ffff0,0xc0000008);
    assert(sd_sync_written==1&&memory_reads==reads);wine_nx_sd_sync_report();assert(invalid_logs==1);
    puts("PASS invalid-wait object capture, no mutation, retry flood deduplicated");
    reset();bad_signature=1;after(SD_SYNC_INVALID_WAIT,0x6d4ffff0,0xc0000008);
    assert(sd_sync_events[0].frames&&!sd_sync_events[0].queue_ok);
    reset();failed_reads=1;after(SD_SYNC_INVALID_WAIT,0x6d4ffff0,0xc0000008);
    assert(!sd_sync_events[0].frames&&!sd_sync_events[0].stack_ok&&!sd_sync_events[0].queue_ok);
    reset();cpu.Edi=99;after(SD_SYNC_INVALID_WAIT,0x6d4ffff0,0xc0000008);
    assert(sd_sync_events[0].queue_ok&&!sd_sync_events[0].object_ok);
    assert(!sd_sync_read32(sd_sync_guest_read,UINT32_MAX-1,stack_memory,4));
    puts("PASS inaccessible memory, mismatched code, bad index and address overflow");
    reset();for(unsigned i=0;i<300;i++)after(SD_SYNC_CREATE,0x1000+i*4,0);
    wine_nx_sd_sync_report();assert(create_logs==SD_SYNC_EVENTS&&sd_sync_dropped==44&&sd_sync_handle_overflow==44);
    unsigned logs=log_lines;wine_nx_sd_sync_report();assert(log_lines==logs);
    puts("PASS bounded ring, explicit dropped/registry counters, drain once");
    reset();struct sd_sync_cpu snapshot={.esp=0x10100,.ebp=0x10180};
    for(unsigned i=0;i<30;i++)sd_sync_note(SD_SYNC_INVALID_WAIT,i+1,0x6d4ffff0,0xc0000008,0,0,0,&snapshot,sd_sync_guest_read);
    assert(sd_sync_written==SD_SYNC_FAILURES);puts("PASS global invalid snapshot cap");
    reset();concurrent_mode=1;pthread_t threads[4];
    for(unsigned i=0;i<4;i++)assert(!pthread_create(&threads[i],NULL,stress,(void *)(uintptr_t)i));
    for(unsigned i=0;i<4;i++)assert(!pthread_join(threads[i],NULL));
    assert(sd_sync_written==8000&&!sd_sync_handle_overflow);
    for(unsigned i=0;i<SD_SYNC_HANDLES;i++)assert(!sd_sync_handles[i].handle);
    wine_nx_sd_sync_report();assert(sd_sync_read==8000&&sd_sync_dropped==8000-SD_SYNC_EVENTS);
    puts("PASS concurrent producers and bounded history");
    return 0;
}
