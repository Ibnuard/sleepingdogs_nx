/* Platform fixture for the actual client wrapper and server_call_unlocked. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define __SWITCH__ 1
#define FTRACE_BLOCK_START(...)
#define FTRACE_BLOCK_END()
#define TRACE_(x) trace_ignore
#define trace_ignore(...) ((void)0)
typedef uint64_t u64;
struct teb { struct { unsigned UniqueThread; } ClientId; };
static struct teb teb = {.ClientId.UniqueThread=42};
static unsigned reads, direct_calls, pipe_calls, tick_reads, fall_back, profile_ticks;
static unsigned char expected[1024];
static unsigned expected_size;
static struct teb *get_teb(void) { ++reads; return &teb; }
#define NtCurrentTeb() get_teb()
#define HandleToULong(x) (x)
enum { REQ_select, REQ_event_op, REQ_query_event, REQ_release_mutex, REQ_query_mutex,
       REQ_release_semaphore, REQ_query_semaphore, REQ_other, REQ_NB_REQUESTS };
union apc_result { uint64_t words[8]; };
struct request_header { unsigned req, request_size, reply_size; };
struct __server_request_info {
    union {
        union {
            struct request_header request_header;
            struct { struct request_header header; unsigned size; } select_request;
            unsigned char bytes[128];
        } req;
        struct { struct { unsigned error, reply_size; } reply_header; unsigned char bytes[120]; } reply;
    } u;
    struct { const void *ptr; unsigned size; } data[5];
    unsigned data_count;
    void *reply_data;
    const char *name;
};
int horizon_fast_sync_enabled, horizon_server_profile_enabled;
static uint64_t sd_sync_calls[3], wine_nx_server_calls[REQ_NB_REQUESTS], wine_nx_server_ticks[REQ_NB_REQUESTS];
static const char *wine_nx_server_names[REQ_NB_REQUESTS];
static u64 armGetSystemTick(void) { ++tick_reads; return ++profile_ticks; }
static unsigned send_request(struct __server_request_info *r) { (void)r; ++pipe_calls; return 0; }
static unsigned wait_reply(struct __server_request_info *r) { (void)r; return 0x55; }
static int horizon_server_sync_call(unsigned tid, const void *r, const void *d, unsigned size, void *reply, void *extra) {
    (void)extra; assert(tid==42); assert(((const struct request_header *)r)->request_size==size);
    ++direct_calls;
    assert(size==expected_size && !memcmp(d,expected,size));
    if (fall_back) return 0;
    memset(reply,0,128); *(unsigned *)reply=0x44; return 1;
}
#include "sd_sync_client.h"
/* ACTUAL_SERVER_CALL */
static struct __server_request_info event_req(void) {
    struct __server_request_info r={0}; r.u.req.request_header.req=REQ_event_op; r.name="event_op"; return r;
}
int main(void) {
    struct __server_request_info r=event_req();
    assert(server_call_unlocked(&r)==0x55 && pipe_calls==1 && !reads && !tick_reads);
    horizon_fast_sync_enabled=2; r=event_req();
    assert(server_call_unlocked(&r)==0x44 && direct_calls==1 && reads==1 && !tick_reads);
    fall_back=1; r=event_req(); assert(server_call_unlocked(&r)==0x55 && pipe_calls==2); fall_back=0;
    r=event_req(); r.u.req.request_header.req=REQ_other; unsigned old=reads;
    assert(server_call_unlocked(&r)==0x55 && reads==old);
    r=event_req(); r.u.req.request_header.request_size=1025; assert(!horizon_sync_call(&r));
    r=event_req(); r.data_count=6; assert(!horizon_sync_call(&r));
    r=event_req(); r.u.req.request_header.request_size=1; assert(!horizon_sync_call(&r));
    r.data_count=1; r.data[0].size=1; assert(!horizon_sync_call(&r));
    r.data[0].ptr=expected; r.data[0].size=1025; assert(!horizon_sync_call(&r));
    assert(reads==old);
    r=event_req(); r.u.req.request_header.req=REQ_select; r.u.req.select_request.size=8;
    assert(!horizon_sync_call(&r));
    r.u.req.request_header.request_size=72; r.data_count=2;
    for (unsigned i=0;i<72;++i) expected[i]=(unsigned char)i;
    r.data[0].ptr=expected; r.data[0].size=64; r.data[1].ptr=expected+64; r.data[1].size=8;
    expected_size=72; assert(horizon_sync_call(&r)); expected_size=0;
    horizon_server_profile_enabled=1; r=event_req(); assert(server_call_unlocked(&r)==0x44);
    assert(tick_reads==2 && sd_sync_calls[0]==1 && wine_nx_server_calls[REQ_event_op]==1);
    assert(!strcmp(wine_nx_server_names[REQ_event_op],"event_op"));
    horizon_fast_sync_enabled=0; r=event_req(); assert(server_call_unlocked(&r)==0x55);
    assert(sd_sync_calls[1]==1 && tick_reads==4 && wine_nx_server_calls[REQ_event_op]==2);
    puts("PASS actual client dispatch: off/direct/fallback, scatter payload, invalid bounds, reply aliasing, counters and disabled-profile clock gate");
    return 0;
}
