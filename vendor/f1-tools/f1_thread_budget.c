/* LGPL-2.1-or-later. Prepare the application's thread budget before starting Wine.
 * Each Wine guest thread also needs a native server connection thread. */
#include <switch.h>
#include <errno.h>
#include <stdio.h>
#include <stddef.h>
#include <stdint.h>

extern void wine_nx_runtime_trace(const char *message);

/* The failing run consumed the default 96-thread application quota before
 * reaching the first frame. Leave room for at least 64 guest/server pairs.
 * Prefer PM's reserved extras. Some kernels expose no extra PM reservation,
 * so a successful PM call can leave the application at its original limit. */
#define F1_STARTUP_FREE_THREADS 128u
#define F1_APPLICATION_THREAD_LIMIT 256u
#define F1_RESULT_NOT_CALLED ((Result)0xffffffffu)

/* Called only after PM confirms that our PID is the active application.
 * Obtain only the calling process's resource object. Never lower its limit,
 * never alter other resources, and never invoke an unadvertised SVC. */
static int f1_raise_own_thread_limit(u64 *available, Result *available_rc,
                                   char *error, size_t capacity)
{
    u64 raw_handle = 0;
    Handle resource = INVALID_HANDLE;
    s64 limit_before = -1, used_before = -1, limit_after = -1, used_after = -1;
    Result handle_rc = F1_RESULT_NOT_CALLED, limit_rc = F1_RESULT_NOT_CALLED;
    Result used_rc = F1_RESULT_NOT_CALLED, set_rc = F1_RESULT_NOT_CALLED;
    Result verify_limit_rc = F1_RESULT_NOT_CALLED, verify_used_rc = F1_RESULT_NOT_CALLED;
    Result close_rc = F1_RESULT_NOT_CALLED;
    unsigned hints = (envIsSyscallHinted(0x30) ? 1u : 0u) |
                     (envIsSyscallHinted(0x31) ? 2u : 0u) |
                     (envIsSyscallHinted(0x7e) ? 4u : 0u);
    int ready = 0;
    const char *stage = "check-svc-access";
    char line[640];

    if (hints != 7u) {
        snprintf(error, capacity, "This loader cannot raise the thread limit. See fex-runtime.log.");
        goto done;
    }
    stage = "own-resource-handle";
    /* InfoType_ResourceLimit requires INVALID_HANDLE, unlike FreeThreadCount. */
    handle_rc = svcGetInfo(&raw_handle, InfoType_ResourceLimit, INVALID_HANDLE, 0);
    if (R_FAILED(handle_rc) || !raw_handle || raw_handle > UINT32_MAX) goto failed;
    resource = (Handle)raw_handle;
    stage = "read-thread-limit";
    limit_rc = svcGetResourceLimitLimitValue(&limit_before, resource, LimitableResource_Threads);
    used_rc = svcGetResourceLimitCurrentValue(&used_before, resource, LimitableResource_Threads);
    if (R_FAILED(limit_rc) || R_FAILED(used_rc) || limit_before < 0 ||
        used_before < 0 || used_before > limit_before) goto failed;

    if (limit_before < F1_APPLICATION_THREAD_LIMIT) {
        stage = "set-thread-limit";
        set_rc = svcSetResourceLimitLimitValue(resource, LimitableResource_Threads,
                                              F1_APPLICATION_THREAD_LIMIT);
        if (R_FAILED(set_rc)) goto failed;
    }
    stage = "verify-thread-limit";
    verify_limit_rc = svcGetResourceLimitLimitValue(&limit_after, resource, LimitableResource_Threads);
    verify_used_rc = svcGetResourceLimitCurrentValue(&used_after, resource, LimitableResource_Threads);
    *available_rc = svcGetInfo(available, InfoType_FreeThreadCount, CUR_PROCESS_HANDLE, 0);
    ready = R_SUCCEEDED(verify_limit_rc) && R_SUCCEEDED(verify_used_rc) &&
            limit_after >= limit_before && used_after >= 0 && used_after <= limit_after &&
            limit_after - used_after >= F1_STARTUP_FREE_THREADS &&
            R_SUCCEEDED(*available_rc) && *available >= F1_STARTUP_FREE_THREADS;
    if (ready) goto done;
failed:
    snprintf(error, capacity, "Cannot prepare application thread quota. See fex-runtime.log.");
done:
    if (resource != INVALID_HANDLE) close_rc = svcCloseHandle(resource);
    snprintf(line, sizeof(line),
             "[F1-THREAD-LIMIT] stage=%s ready=%d svcs=%x handle_rc=%08x limit_rc=%08x used_rc=%08x "
             "set_rc=%08x verify_limit_rc=%08x verify_used_rc=%08x close_rc=%08x "
             "limit_before=%lld used_before=%lld limit_after=%lld used_after=%lld target_limit=%u",
             stage, ready, hints, handle_rc, limit_rc, used_rc, set_rc, verify_limit_rc,
             verify_used_rc, close_rc, (long long)limit_before, (long long)used_before,
             (long long)limit_after, (long long)used_after, F1_APPLICATION_THREAD_LIMIT);
    wine_nx_runtime_trace(line);
    return ready;
}

int wine_nx_f1_prepare_threads(char *error, size_t capacity)
{
    int saved_errno = errno, ready = 0;
    u64 before = 0, after = 0, self_pid = 0, app_pid = 0;
    Result before_rc = svcGetInfo(&before, InfoType_FreeThreadCount, CUR_PROCESS_HANDLE, 0);
    Result after_rc = before_rc, init_rc = 0, self_rc = 0, app_rc = 0, boost_rc = 0;
    const char *stage = "already-available";
    char line[384];

    if (capacity) error[0] = 0;
    after = before;
    if (R_SUCCEEDED(before_rc) && before >= F1_STARTUP_FREE_THREADS) {
        ready = 1;
        goto done;
    }

    stage = "pm-initialize";
    init_rc = pmshellInitialize();
    if (R_FAILED(init_rc)) {
        snprintf(error, capacity, "Cannot request application threads (PM %08x). See fex-runtime.log.", init_rc);
        goto done;
    }

    /* The PM command affects the active application group. Verify it is us,
     * so launching from Album cannot boost an unrelated suspended title. */
    stage = "verify-application";
    self_rc = svcGetProcessId(&self_pid, CUR_PROCESS_HANDLE);
    app_rc = pmshellGetApplicationProcessIdForShell(&app_pid);
    if (R_FAILED(self_rc) || R_FAILED(app_rc) || !self_pid || self_pid != app_pid) {
        snprintf(error, capacity, "Open hbmenu by holding R while launching a game, then start F1 again.");
        goto close_service;
    }

    stage = "request-application-threads";
    boost_rc = pmshellBoostApplicationThreadResourceLimit();
    after_rc = svcGetInfo(&after, InfoType_FreeThreadCount, CUR_PROCESS_HANDLE, 0);
    /* A successful PM call may be a no-op if the kernel has no extra quota.
     * Use the measured capacity when available. On older kernels, only PM's
     * explicit success can allow startup without the newer free-count query. */
    ready = R_SUCCEEDED(after_rc) ? after >= F1_STARTUP_FREE_THREADS : R_SUCCEEDED(boost_rc);
    if (!ready) {
        stage = "own-resource-limit";
        ready = f1_raise_own_thread_limit(&after, &after_rc, error, capacity);
    }
close_service:
    pmshellExit();
done:
    snprintf(line, sizeof(line),
             "[F1-THREAD-BUDGET] stage=%s ready=%d before=%llu before_rc=%08x after=%llu after_rc=%08x "
             "pm_rc=%08x self_rc=%08x app_rc=%08x self_pid=%llu app_pid=%llu boost_rc=%08x required_free=%u",
             stage, ready, (unsigned long long)before, before_rc, (unsigned long long)after, after_rc,
             init_rc, self_rc, app_rc, (unsigned long long)self_pid, (unsigned long long)app_pid,
             boost_rc, F1_STARTUP_FREE_THREADS);
    wine_nx_runtime_trace(line);
    errno = saved_errno;
    return ready;
}
