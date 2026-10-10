/* SPDX-License-Identifier: MIT.
 * The game, Wine, FEX and GPU driver share one process. Returning to hbloader
 * while any of their threads survive would unmap live code. Restart the HOME
 * application through AM instead, and show the saved result on its next boot.
 * The restart worker has its own stack and preopened private filesystem session;
 * it never waits for the Wine, renderer, audio or runtime-log locks. */
#include <switch.h>
#include <pthread.h>
#include <stdio.h>
#include "f1_relaunch.h"

#define F1_RETURN_PATH "/switch/f1-fex/launcher/last-game-return.bin"
static FsFile f1_return_owner, f1_return_file;
static unsigned f1_return_armed, f1_return_servicing, f1_return_worker_handle;
static uint64_t f1_return_pending;

int wine_nx_f1_relaunch_consume(char *message, size_t capacity)
{
    FsFileSystem *sd = fsdevGetDeviceFileSystem("sdmc");
    FsFile file;
    struct f1_return_record record;
    u64 bytes = 0;
    if (!sd || R_FAILED(fsFsOpenFile(sd, F1_RETURN_PATH, FsOpenMode_Read, &file))) return 0;
    Result rc = fsFileRead(&file, 0, &record, sizeof(record), FsReadOption_None, &bytes);
    fsFileClose(&file);
    if (R_FAILED(rc) || !f1_return_valid(&record, bytes)) return 0;
    /* Consume only a validated diagnostic. It never contains a launch command. */
    fsFsDeleteFile(sd, F1_RETURN_PATH);
    appletSetExpectedMasterVolume(1.0f, 1.0f);
    unsigned code = record.words[3];
    int normal = !code && (record.words[2] == F1_RETURN_GUEST || record.words[2] == F1_RETURN_NATIVE_EXIT);
    if (normal)
        snprintf(message, capacity, "The game has closed. The runtime was restarted. You can launch F1 again.");
    else if (record.words[2] == F1_RETURN_RESOURCE)
        snprintf(message, capacity, "Cannot start game worker (0x%08x): memory allocation failed. Runtime restarted. See fex-runtime.log.", code);
    else if (record.words[2] == F1_RETURN_COMPILER)
        snprintf(message, capacity, "FEX compiler stopped: %u MiB workspace unavailable. Runtime restarted. See fex-runtime.log.", code / (1024u * 1024u));
    else
        snprintf(message, capacity, "Game stopped (0x%08x). Runtime restarted. Logs saved: fex-runtime.log and crash.log.", code);
    return normal ? 1 : 2;
}

int wine_nx_f1_relaunch_request(unsigned kind, unsigned code)
{
    if (!__atomic_load_n(&f1_return_armed, __ATOMIC_ACQUIRE) ||
        kind < F1_RETURN_GUEST || kind > F1_RETURN_COMPILER) return 0;
    uint64_t empty = 0;
    __atomic_compare_exchange_n(&f1_return_pending, &empty, ((uint64_t)kind << 32) | code,
                                 0, __ATOMIC_RELEASE, __ATOMIC_RELAXED);
    return 1; /* A later worker exit must not replace the first failure. */
}

void wine_nx_f1_relaunch_poll(void)
{
    if (!__atomic_load_n(&f1_return_armed, __ATOMIC_ACQUIRE)) return;
    uint64_t pending = __atomic_load_n(&f1_return_pending, __ATOMIC_ACQUIRE);
    if (!pending || __atomic_exchange_n(&f1_return_servicing, 1, __ATOMIC_ACQ_REL)) return;
    struct f1_return_record record = f1_return_make(pending);
    /* Stop the surviving game's audio while AM replaces the whole process. */
    appletSetExpectedMasterVolume(0.0f, 1.0f);
    Result saved = fsFileWrite(&f1_return_file, 0, &record, sizeof(record), FsWriteOption_Flush);
    Result restart = saved;
    if (R_SUCCEEDED(saved)) restart = appletRestartProgram(NULL, 0);
    if (R_SUCCEEDED(restart)) {
        /* Successful AM dispatch normally terminates this process immediately.
         * If it does not, show a visible failure instead of waiting forever. */
        svcSleepThread(5000000000LL);
    }
    char details[320];
    snprintf(details, sizeof(details),
        "Game stopped (0x%08x). Restart did not complete.\n"
        "Save: 0x%08x  Restart: 0x%08x\n"
        "Reopen F1 from HOME. Logs: switch/f1-fex/fex-runtime.log and crash.log.",
        (unsigned)pending, saved, restart);
    ErrorApplicationConfig error;
    if (R_SUCCEEDED(errorApplicationCreate(&error, "F1 2013 stopped", details)))
        errorApplicationShow(&error);
    /* Whole-process exit only. No atexit/hbloader reload with live workers. */
    svcExitProcess();
}

void wine_nx_f1_relaunch_disarm(void)
{
    /* Explicit application close/cancel is not a crashed game. The process
     * is about to exit; do not turn that request into a relaunch loop. */
    __atomic_store_n(&f1_return_armed, 0, __ATOMIC_RELEASE);
}

static void *f1_return_worker(void *unused)
{
    (void)unused;
    __atomic_store_n(&f1_return_worker_handle, threadGetCurHandle(), __ATOMIC_RELEASE);
    for (;;) {
        svcSleepThread(250000000LL);
        wine_nx_f1_relaunch_poll();
    }
    return NULL;
}

unsigned wine_nx_f1_relaunch_arm(void)
{
    if (__atomic_load_n(&f1_return_armed, __ATOMIC_ACQUIRE)) return 0;
    FsFileSystem *sd = fsdevGetDeviceFileSystem("sdmc");
    if (!sd) return 0xf12001;
    FsDirEntryType type;
    Result rc;
    if (R_FAILED(fsFsGetEntryType(sd, F1_RETURN_PATH, &type))) {
        rc = fsFsCreateFile(sd, F1_RETURN_PATH, sizeof(struct f1_return_record), 0);
        if (R_FAILED(rc)) return rc;
    }
    rc = fsFsOpenFile(sd, F1_RETURN_PATH, FsOpenMode_Write, &f1_return_owner);
    if (R_FAILED(rc)) return rc;
    rc = fsFileSetSize(&f1_return_owner, sizeof(struct f1_return_record));
    if (R_FAILED(rc)) goto close_owner;
    rc = serviceClone(&f1_return_owner.s, &f1_return_file.s);
    if (R_FAILED(rc)) goto close_owner;
    struct f1_return_record empty = {{0}};
    rc = fsFileWrite(&f1_return_file, 0, &empty, sizeof(empty), FsWriteOption_Flush);
    if (R_FAILED(rc)) goto close_clone;
    pthread_attr_t attr;
    pthread_t worker;
    int err = pthread_attr_init(&attr);
    if (!err) {
        err = pthread_attr_setstacksize(&attr, 128 * 1024);
        if (!err) err = pthread_attr_setdetachstate(&attr, PTHREAD_CREATE_DETACHED);
        if (!err) err = pthread_create(&worker, &attr, f1_return_worker, NULL);
        pthread_attr_destroy(&attr);
    }
    if (err) { rc = 0xf12002; goto close_clone; }
    __atomic_store_n(&f1_return_armed, 1, __ATOMIC_RELEASE);
    return 0;
close_clone:
    serviceClose(&f1_return_file.s);
close_owner:
    fsFileClose(&f1_return_owner);
    return rc;
}

void wine_nx_f1_relaunch_fatal(unsigned kind, unsigned code)
{
    /* If the restart worker itself faults, retain the original OS fatal path. */
    if (threadGetCurHandle() == __atomic_load_n(&f1_return_worker_handle, __ATOMIC_ACQUIRE)) return;
    if (!wine_nx_f1_relaunch_request(kind, code)) return;
    /* Fatal record already flushed. Keep the faulted worker out of Wine/CRT
     * teardown until the independent worker replaces this application. */
    for (;;) svcSleepThread(1000000000LL);
}

void wine_nx_f1_compiler_stopped(unsigned bytes)
{
    /* Called only after FEX's explicit fatal STOP message was saved. Ordinary
     * failed allocations may recover and must never request a restart here. */
    wine_nx_f1_relaunch_fatal(F1_RETURN_COMPILER, bytes);
}
