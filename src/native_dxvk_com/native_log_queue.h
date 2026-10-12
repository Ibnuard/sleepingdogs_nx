/* SPDX-License-Identifier: MIT; bounded native-runtime logging, one consumer. */
#ifndef SD_NATIVE_LOG_QUEUE_H
#define SD_NATIVE_LOG_QUEUE_H
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define SD_NATIVE_LOG_SLOTS 512u
#define SD_NATIVE_LOG_LINE 1024u
#define SD_NATIVE_LOG_BATCH 32u
static pthread_mutex_t sd_native_log_lock=PTHREAD_MUTEX_INITIALIZER;
static char sd_native_log_lines[SD_NATIVE_LOG_SLOTS][SD_NATIVE_LOG_LINE];
static unsigned sd_native_log_head,sd_native_log_count;
static uint64_t sd_native_log_dropped;

/* Called under renderer/guest locks: never wait for another logger or do I/O. */
static void sd_native_log_enqueue(const char *line)
{
    if (pthread_mutex_trylock(&sd_native_log_lock)) {
        __atomic_fetch_add(&sd_native_log_dropped,1,__ATOMIC_RELAXED);return;
    }
    if (sd_native_log_count==SD_NATIVE_LOG_SLOTS) {
        pthread_mutex_unlock(&sd_native_log_lock);
        __atomic_fetch_add(&sd_native_log_dropped,1,__ATOMIC_RELAXED);return;
    }
    unsigned slot=(sd_native_log_head+sd_native_log_count)%SD_NATIVE_LOG_SLOTS;
    snprintf(sd_native_log_lines[slot],SD_NATIVE_LOG_LINE,"%.*s\n",(int)SD_NATIVE_LOG_LINE-2,line);
    ++sd_native_log_count;
    pthread_mutex_unlock(&sd_native_log_lock);
}

/* Only the runtime maintenance thread drains. Release the queue before I/O. */
static unsigned sd_native_log_drain(void (*write_batch)(const char*,size_t,void*),void *context)
{
    static char batch[SD_NATIVE_LOG_BATCH*SD_NATIVE_LOG_LINE+128];
    size_t bytes=0;unsigned lines=0;
    uint64_t dropped=__atomic_exchange_n(&sd_native_log_dropped,0,__ATOMIC_RELAXED);
    if(dropped)bytes=(size_t)snprintf(batch,sizeof(batch),"[SD-NDX-LOG] dropped=%llu; queue full or busy, capture may omit events\n",(unsigned long long)dropped);
    pthread_mutex_lock(&sd_native_log_lock);
    while(sd_native_log_count&&lines<SD_NATIVE_LOG_BATCH) {
        const char *line=sd_native_log_lines[sd_native_log_head];size_t length=strlen(line);
        memcpy(batch+bytes,line,length);bytes+=length;
        sd_native_log_head=(sd_native_log_head+1)%SD_NATIVE_LOG_SLOTS;
        --sd_native_log_count;++lines;
    }
    pthread_mutex_unlock(&sd_native_log_lock);
    if(bytes)write_batch(batch,bytes,context);
    return lines;
}
#endif
