/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Bounded Debug evidence. No allocation, guest writes, or I/O on syscall paths.
 * Guest reads and log callbacks must never run while sd_sync_mutex is held.
 */
#include "sd_sync_watch.h"
#include <pthread.h>
#include <stdio.h>
#include <string.h>

#define SD_SYNC_EVENTS 256u
#define SD_SYNC_HANDLES 256u
#define SD_SYNC_FAILURES 8u
#define SD_SYNC_FRAMES 8u
struct sd_sync_frame { uint32_t address, words[12]; };
struct sd_sync_event {
    uint64_t serial, tick, handle;
    uint32_t kind, tid, status;
    int32_t initial, maximum;
    struct sd_sync_cpu cpu;
    uint32_t stack[32], stack_ok, frames;
    struct sd_sync_frame frame[SD_SYNC_FRAMES];
    uint32_t queue_address, queue_ok, queue[88], slot_index;
    uint32_t object_address, object_ok, object[8];
    uint32_t handle_memory_ok, handle_memory[8];
};
static pthread_mutex_t sd_sync_mutex = PTHREAD_MUTEX_INITIALIZER;
static struct sd_sync_event sd_sync_events[SD_SYNC_EVENTS];
static struct { uint64_t handle, generation; } sd_sync_handles[SD_SYNC_HANDLES];
static struct { uint32_t tid; uint64_t handle; } sd_sync_failures[SD_SYNC_FAILURES];
static uint64_t sd_sync_written, sd_sync_read, sd_sync_dropped;
static unsigned sd_sync_handle_overflow, sd_sync_failure_count;

static int sd_sync_read32(sd_sync_reader read_memory, uint32_t address, void *out, size_t size)
{
    if (!address || !size || size > 4096 || size > UINT32_MAX-address) return 0;
    return read_memory(address,out,size);
}

static void sd_sync_capture(struct sd_sync_event *event, sd_sync_reader read_memory)
{
    const struct sd_sync_cpu *cpu=&event->cpu;
    uint32_t frame=cpu->ebp;
    event->stack_ok=sd_sync_read32(read_memory,cpu->esp,event->stack,sizeof(event->stack));
    for (unsigned i=0;i<SD_SYNC_FRAMES;i++) {
        struct sd_sync_frame *out=&event->frame[i];
        if (frame<16 || frame<cpu->esp || (uint64_t)frame-cpu->esp>16*1024*1024) break;
        if (!sd_sync_read32(read_memory,frame-16,out->words,sizeof(out->words))) break;
        out->address=frame; event->frames++;
        if (out->words[4]<=frame) break;
        frame=out->words[4];
    }
    if (event->kind!=SD_SYNC_INVALID_WAIT) return;
    if (event->handle<=UINT32_MAX)
        event->handle_memory_ok=sd_sync_read32(read_memory,(uint32_t)event->handle,
                                              event->handle_memory,sizeof(event->handle_memory));
    /* Optional interpretation for the supplied original HKShip.exe only.
     * Check its wait wrapper and queue load instructions before following the
     * saved ESI/index. Raw registers/frames are retained if signatures differ.
     */
    const unsigned char wait_code[]={0x8b,0x01,0x6a,0xff,0x50,0xff,0x15,0xc4,0x11,0x0e,0x01,0xc3};
    const unsigned char queue_code[]={0x8b,0x4c,0xbe,0x78,0x51};
    const unsigned char wine_wait[]={0x66,0x90,0x55,0x89,0xe5,0x56};
    unsigned char code[sizeof(wait_code)];
    if (!sd_sync_read32(read_memory,0xbb6f30,code,sizeof(wait_code)) ||
        memcmp(code,wait_code,sizeof(wait_code)) ||
        !sd_sync_read32(read_memory,0xbb8730,code,sizeof(queue_code)) ||
        memcmp(code,queue_code,sizeof(queue_code)) ||
        !sd_sync_read32(read_memory,0x7b05e420,code,sizeof(wine_wait)) ||
        memcmp(code,wine_wait,sizeof(wine_wait))) return;
    for (unsigned i=0;i<event->frames;i++) {
        const struct sd_sync_frame *f=&event->frame[i];
        if (f->words[5]!=0xbb6f3b) continue;
        event->queue_address=f->words[3]; /* kernelbase!WaitForSingleObject saves ESI at EBP-4 */
        event->slot_index=cpu->edi;
        event->queue_ok=sd_sync_read32(read_memory,event->queue_address,event->queue,sizeof(event->queue));
        /* Five pointer slots precede the count at queue+0x8c. An invalid index
         * is evidence too; do not clamp it or dereference outside the header. */
        if (event->queue_ok && event->slot_index<5) {
            event->object_address=event->queue[0x78/4+event->slot_index];
            event->object_ok=sd_sync_read32(read_memory,event->object_address,event->object,sizeof(event->object));
        }
        break;
    }
}

void sd_sync_note(unsigned kind, uint32_t tid, uint64_t handle, uint32_t status,
                  int32_t initial, int32_t maximum, uint64_t tick,
                  const struct sd_sync_cpu *cpu, sd_sync_reader read_memory)
{
    unsigned slot=SD_SYNC_HANDLES;
    uint64_t generation=0;
    if (!cpu || !read_memory || kind>SD_SYNC_INVALID_WAIT || !tid) return;
    if (kind==SD_SYNC_INVALID_WAIT && (status!=0xc0000008u || handle<0x10000 || handle>UINT32_MAX)) return;
    pthread_mutex_lock(&sd_sync_mutex);
    if (kind==SD_SYNC_CLOSE) {
        for (unsigned i=0;i<SD_SYNC_HANDLES;i++)
            if (sd_sync_handles[i].handle==handle && handle) { slot=i;generation=sd_sync_handles[i].generation;break; }
        if (slot==SD_SYNC_HANDLES) { pthread_mutex_unlock(&sd_sync_mutex);return; }
    } else if (kind==SD_SYNC_INVALID_WAIT) {
        for (unsigned i=0;i<sd_sync_failure_count;i++)
            if (sd_sync_failures[i].tid==tid && sd_sync_failures[i].handle==handle) {
                pthread_mutex_unlock(&sd_sync_mutex);return;
            }
        if (sd_sync_failure_count==SD_SYNC_FAILURES) { pthread_mutex_unlock(&sd_sync_mutex);return; }
        sd_sync_failures[sd_sync_failure_count].tid=tid;
        sd_sync_failures[sd_sync_failure_count++].handle=handle;
    }
    pthread_mutex_unlock(&sd_sync_mutex);
    struct sd_sync_event event={0};
    event.kind=kind;event.tid=tid;event.handle=handle;event.status=status;
    event.initial=initial;event.maximum=maximum;event.tick=tick;event.cpu=*cpu;
    sd_sync_capture(&event,read_memory);
    pthread_mutex_lock(&sd_sync_mutex);
    event.serial=++sd_sync_written;
    if ((kind==SD_SYNC_CREATE || kind==SD_SYNC_OPEN) && !(status&0x80000000u) && handle) {
        for (unsigned i=0;i<SD_SYNC_HANDLES;i++) {
            if (sd_sync_handles[i].handle==handle) { slot=i;break; }
            if (!sd_sync_handles[i].handle && slot==SD_SYNC_HANDLES) slot=i;
        }
        if (slot==SD_SYNC_HANDLES) sd_sync_handle_overflow++;
        else { sd_sync_handles[slot].handle=handle;sd_sync_handles[slot].generation=event.serial; }
    } else if (kind==SD_SYNC_CLOSE && !status && sd_sync_handles[slot].generation==generation) {
        sd_sync_handles[slot].handle=0;
    }
    sd_sync_events[(event.serial-1)%SD_SYNC_EVENTS]=event;
    pthread_mutex_unlock(&sd_sync_mutex);
}

static void sd_sync_words(sd_sync_logger log, uint64_t serial, const char *label,
                          uint32_t address, const uint32_t *words, unsigned count)
{
    char line[256];
    for (unsigned i=0;i<count;i+=8) {
        int n=snprintf(line,sizeof(line),"[SD-SYNC-MEM] seq=%llu %s address=%08x words=",
                       (unsigned long long)serial,label,address+i*4);
        for (unsigned j=i;j<count && j<i+8;j++)
            n+=snprintf(line+n,sizeof(line)-(size_t)n," %08x",words[j]);
        log(line);
    }
}

void sd_sync_report(sd_sync_logger log)
{
    static const char *names[]={"create","open","close","invalid-wait"};
    char line[512];
    uint64_t stop;
    if (!log || pthread_mutex_trylock(&sd_sync_mutex)) return;
    stop=sd_sync_written;
    pthread_mutex_unlock(&sd_sync_mutex);
    unsigned reported=0;
    for (unsigned i=0;i<SD_SYNC_EVENTS;i++) {
        struct sd_sync_event event;
        if (pthread_mutex_trylock(&sd_sync_mutex)) break;
        if (sd_sync_written-sd_sync_read>SD_SYNC_EVENTS) {
            uint64_t skipped=sd_sync_written-sd_sync_read-SD_SYNC_EVENTS;
            sd_sync_dropped+=skipped;sd_sync_read+=skipped;
        }
        if (sd_sync_read>=stop) { pthread_mutex_unlock(&sd_sync_mutex);break; }
        event=sd_sync_events[sd_sync_read%SD_SYNC_EVENTS];sd_sync_read++;
        pthread_mutex_unlock(&sd_sync_mutex);
        reported++;
        const struct sd_sync_cpu *c=&event.cpu;
        snprintf(line,sizeof(line),"[SD-SYNC] v1 seq=%llu kind=%s tid=%u handle=%llx status=%08x initial=%d max=%d tick=%llu frames=%u stack_read=%u",
                 (unsigned long long)event.serial,names[event.kind],event.tid,(unsigned long long)event.handle,
                 event.status,event.initial,event.maximum,(unsigned long long)event.tick,event.frames,event.stack_ok);
        log(line);
        snprintf(line,sizeof(line),"[SD-SYNC-REG] seq=%llu eax=%08x ebx=%08x ecx=%08x edx=%08x esi=%08x edi=%08x ebp=%08x esp=%08x eip=%08x",
                 (unsigned long long)event.serial,c->eax,c->ebx,c->ecx,c->edx,c->esi,c->edi,c->ebp,c->esp,c->eip);
        log(line);
        if (event.stack_ok) sd_sync_words(log,event.serial,"stack",c->esp,event.stack,32);
        for (unsigned j=0;j<event.frames;j++)
            sd_sync_words(log,event.serial,"frame",event.frame[j].address-16,event.frame[j].words,12);
        if (event.kind==SD_SYNC_INVALID_WAIT) {
            snprintf(line,sizeof(line),"[SD-SYNC-OBJECT] seq=%llu queue=%08x queue_read=%u index=%u object=%08x object_read=%u handle_read=%u; signature-gated candidate, non-atomic observation",
                     (unsigned long long)event.serial,event.queue_address,event.queue_ok,event.slot_index,
                     event.object_address,event.object_ok,event.handle_memory_ok);
            log(line);
            if (event.queue_ok) sd_sync_words(log,event.serial,"queue",event.queue_address,event.queue,88);
            if (event.object_ok) sd_sync_words(log,event.serial,"object",event.object_address,event.object,8);
            if (event.handle_memory_ok) sd_sync_words(log,event.serial,"handle-data",(uint32_t)event.handle,event.handle_memory,8);
        }
    }
    if (reported && !pthread_mutex_trylock(&sd_sync_mutex)) {
        uint64_t dropped=sd_sync_dropped;unsigned full=sd_sync_handle_overflow,failed=sd_sync_failure_count;
        pthread_mutex_unlock(&sd_sync_mutex);
        snprintf(line,sizeof(line),"[SD-SYNC-SUMMARY] delivered=%u overwritten=%llu registry_overflow=%u invalid_captures=%u; PE syscall observations only",
                 reported,(unsigned long long)dropped,full,failed);
        log(line);
    }
}
