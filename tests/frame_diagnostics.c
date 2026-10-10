/* Exercise the exact production collector with an explicit fake clock/kernel. */
#include <assert.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#include <stdlib.h>
#include <stdint.h>
static uint64_t clock_tick, kernel_queries;
static __thread uint64_t cpu_tick;
static __thread unsigned handle=1;
static unsigned maps, starts, samples, complete;
static uint64_t armGetSystemTick(void) { return clock_tick; }
static uint64_t armTicksToNs(uint64_t v) { return v; }
static uint64_t armNsToTicks(uint64_t v) { return v; }
static unsigned threadGetCurHandle(void) { return handle; }
enum {InfoType_ThreadTickCount=25};
#define R_SUCCEEDED(r) ((r)==0)
static int svcGetInfo(uint64_t *p, unsigned info, unsigned h, uint64_t all)
{
    assert(info==InfoType_ThreadTickCount && h==handle && all==UINT64_MAX);
    ++kernel_queries; *p=cpu_tick; return 0;
}
void wine_nx_sd_diag_thread_map(void) { ++maps; }
static void log_line(const char *format, ...)
{
    char line[2048]; va_list args;
    va_start(args,format); vsnprintf(line,sizeof(line),format,args); va_end(args);
    if (strstr(line,"phase=start")) ++starts;
    if (strstr(line,"phase=sample")) ++samples;
    if (strstr(line,"phase=complete")) ++complete;
}
#include "sd_frame_diag_runtime.h"
#define present(q,s,v) sd_frame_diag_present(q,s,clock_tick,v)

static void *worker(void *arg)
{
    handle=10+(unsigned)(uintptr_t)arg;
    for (unsigned j=0;j<10000;j++)
        wine_nx_sd_diag_note(0,clock_tick,clock_tick+100,0,0,1);
    return NULL;
}
static void test_parallel(void)
{
    pthread_t threads[16];
    unsigned before=SD_DIAG_LOAD(&sd_frame_diag.next);
    for (unsigned i=0;i<16;i++) assert(!pthread_create(&threads[i],0,worker,(void *)(uintptr_t)i));
    /* Concurrent snapshots read only atomics; never stop a producer. */
    for (unsigned n=0;n<500;n++)
        for (unsigned i=0;i<SD_DIAG_THREADS;i++) (void)SD_DIAG_LOAD(&sd_frame_diag.rows[i].stages[0].calls);
    for (unsigned i=0;i<16;i++) assert(!pthread_join(threads[i],0));
    assert(SD_DIAG_LOAD(&sd_frame_diag.next)==before+16);
    for (unsigned i=before;i<before+16;i++) {
        struct sd_diag_stat *s=&sd_frame_diag.rows[i].stages[0];
        assert(s->calls==10000 && s->ticks==1000000 && s->peak==100 && s->direct==10000 && !s->pipe);
    }
    puts("PASS concurrent lifetime rows: 160000 calls, consistent post-join totals");
}
int main(void)
{
    clock_tick=1000000000;
    sd_frame_diag_monitor(clock_tick,0);
    wine_nx_sd_diag_note(0,clock_tick,clock_tick,0,0,1);
    present(1,2,1);
    assert(!starts && !kernel_queries && !sd_frame_diag.next);
    sd_frame_diag_enabled=1;
    sd_frame_diag_monitor(clock_tick,0);
    clock_tick+=10000000000ULL; sd_frame_diag_monitor(clock_tick,600); /* menu 60fps */
    clock_tick+=10000000000ULL; sd_frame_diag_monitor(clock_tick,800); /* slow */
    clock_tick+=10000000000ULL; sd_frame_diag_monitor(clock_tick,800); /* loading: reset */
    clock_tick+=10000000000ULL; sd_frame_diag_monitor(clock_tick,1000);
    assert(!starts);
    clock_tick+=10000000000ULL; sd_frame_diag_monitor(clock_tick,1200);
    assert(starts==1 && !complete && !kernel_queries);
    puts("PASS disabled path and slow-window gate: menu/loading do not trigger");
    uint64_t first=sd_frame_diag.begin, end=sd_frame_diag.end;
    wine_nx_sd_diag_note(0,first-1,first+1,0,0,1);
    wine_nx_sd_diag_note(0,first+3,first+2,0,0,1);
    wine_nx_sd_diag_note(0,end-1,end,0,0,1);
    assert(!sd_frame_diag.next);
    wine_nx_sd_diag_note(0,first,first+150,1,0,1);
    wine_nx_sd_diag_note(6,first,first+250,0,1,0);
    wine_nx_sd_diag_note(1,first,first+50,0,0,2);
    assert(sd_frame_diag_row->stages[0].timeouts==1 && sd_frame_diag_row->stages[6].errors==1);
    assert(sd_frame_diag_row->stages[1].pipe==1 && sd_frame_diag_row->stages[6].direct==0);
    puts("PASS stage/result/route attribution and capture boundary rejection");
    cpu_tick=10; present(1,2,1);
    clock_tick+=60000000; cpu_tick+=20000000; present(1,2,1);
    assert(sd_frame_diag_row->frames==1 && sd_frame_diag_row->cpu_ticks==20000000);
    assert(sd_frame_diag_row->over33==1 && sd_frame_diag_row->over50==1 && !sd_frame_diag_row->over100);
    clock_tick+=60000000; cpu_tick+=90000000; present(1,2,1);
    assert(sd_frame_diag_row->frames==2 && sd_frame_diag_row->cpu_frames==1); /* impossible CPU excluded */
    present(1,2,0);
    clock_tick+=60000000; present(1,2,1);
    clock_tick+=60000000; present(1,3,1);
    assert(sd_frame_diag_row->frames==2); /* invalid Present / swapchain re-prime */
    puts("PASS frame CPU validity, histogram, error and swapchain reset");
    test_parallel();
    /* Separate lifetime rows even for a recycled handle. Fixed memory limit. */
    struct sd_diag_row *a=sd_diag_register(&sd_frame_diag,99), *b=sd_diag_register(&sd_frame_diag,99);
    assert(a && b && a!=b);
    while (sd_frame_diag.next<SD_DIAG_THREADS) assert(sd_diag_register(&sd_frame_diag,777));
    assert(!sd_diag_register(&sd_frame_diag,888) && sd_frame_diag.capacity_drops==1);
    puts("PASS bounded storage and recycled-handle separation");
    clock_tick=first+10000000000ULL; sd_frame_diag_monitor(clock_tick,1400);
    clock_tick=first+20000000000ULL; sd_frame_diag_monitor(clock_tick,1600);
    clock_tick=end; sd_frame_diag_monitor(clock_tick,1800);
    assert(samples==2 && complete==1 && maps==3);
    uint64_t queries=kernel_queries, n=sd_frame_diag_row->stages[0].calls;
    present(1,3,1); wine_nx_sd_diag_note(0,end,end+100,0,0,1);
    for (unsigned i=0;i<10;i++) { clock_tick+=10000000000ULL; sd_frame_diag_monitor(clock_tick,2000+i*200); }
    assert(kernel_queries==queries && sd_frame_diag_row->stages[0].calls==n && starts==1 && complete==1);
    puts("PASS automatic stop after 30 seconds: no repeated capture or kernel tick queries");
    return 0;
}
