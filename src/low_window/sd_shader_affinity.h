/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Adapted from Autorun/Wine-NX 5a75cfb647a0 and e823a778f5cc.
 * FEXTendo integration: independent slot metadata, stable-balancer exclusion,
 * existing core-3 helper coexistence, and retried affinity restoration.
 * Included after registry and fex_dxvk_slots; all *_locked calls hold registry_mutex.
 */
enum { SD_SHADER_NONE, SD_SHADER_WORKER, SD_SHADER_PIPELINE, SD_SHADER_RESTORE };
struct sd_shader_slot {
    unsigned mode;
    s32 core;
    u64 mask;
};
static struct sd_shader_slot sd_shader_slots[NX_PROF_MAX_THREADS];
static unsigned sd_shader_enabled;
static u64 sd_shader_mask;

int wine_nx_sd_shader_configure(int requested)
{
    u64 mask = 0;
    sd_shader_enabled = requested &&
        R_SUCCEEDED(svcGetInfo(&mask, InfoType_CoreMask, CUR_PROCESS_HANDLE, 0)) && (mask & 7);
    sd_shader_mask = mask & 7;
    return sd_shader_enabled;
}

static int sd_shader_worker(const char *name)
{
    return !strcmp(name, "dxvk-shader") || !strcmp(name, "dxvk-shader-h") ||
           !strcmp(name, "dxvk-shader-n") || !strcmp(name, "dxvk-shader-l");
}

static void sd_shader_follow_locked(unsigned i, u64 mask)
{
    if (registry[i].teb && horizon_follow_thread_cores)
        horizon_follow_thread_cores((void *)(uintptr_t)registry[i].teb, (unsigned)mask);
}

static int sd_shader_retry_locked(unsigned i)
{
    struct sd_shader_slot *s = &sd_shader_slots[i];
    if (s->mode != SD_SHADER_RESTORE) return 1;
    if (R_FAILED(svcSetThreadCoreMask(registry[i].handle, s->core, s->mask))) return 0;
    sd_shader_follow_locked(i, s->mask);
    s->mode = SD_SHADER_NONE;
    return 1;
}

static int sd_shader_restore_locked(unsigned i)
{
    if (!sd_shader_slots[i].mode) return 1;
    sd_shader_slots[i].mode = SD_SHADER_RESTORE;
    return sd_shader_retry_locked(i);
}

static int sd_shader_migrate_locked(unsigned i, unsigned mode)
{
    struct sd_shader_slot *s = &sd_shader_slots[i];
    s32 core;
    u64 mask;
    if (!sd_shader_enabled || registry[i].fixed || fex_dxvk_slots[i].active) return 0;
    if (!sd_shader_retry_locked(i) || s->mode) return 0;
    if (R_FAILED(svcGetThreadCoreMask(&core, &mask, registry[i].handle)) ||
        R_FAILED(svcSetThreadCoreMask(registry[i].handle, -1, sd_shader_mask))) return 0;
    s->core = core;
    s->mask = mask;
    s->mode = mode;
    sd_shader_follow_locked(i, sd_shader_mask);
    return 1;
}

/* Restore a renamed shader worker before the existing dxvk-cs helper policy runs. */
static int sd_shader_before_name_locked(unsigned i, const char *name)
{
    if (!sd_shader_worker(name)) return sd_shader_restore_locked(i);
    return sd_shader_retry_locked(i);
}

static void sd_shader_after_name_locked(unsigned i, const char *name)
{
    if (!sd_shader_worker(name)) return;
    if (sd_shader_slots[i].mode == SD_SHADER_PIPELINE)
        sd_shader_slots[i].mode = SD_SHADER_WORKER;
    sd_shader_migrate_locked(i, SD_SHADER_WORKER);
}

/* The Windows affinity request was accepted. It supersedes any saved scope.
 * On a native failure, retry this requested placement, never the old one. */
static int sd_shader_explicit_locked(unsigned i, u64 mask)
{
    struct sd_shader_slot *s = &sd_shader_slots[i];
    if (!mask || (!s->mode && (!sd_shader_enabled || fex_dxvk_slots[i].active))) return 0;
    registry[i].fixed = 1;
    s->core = __builtin_ctzll(mask);
    s->mask = mask;
    s->mode = SD_SHADER_RESTORE;
    sd_shader_retry_locked(i);
    return 1;
}

unsigned wine_nx_thread_pipeline_begin(void)
{
    if (!sd_shader_enabled) return 0;
    Handle handle = threadGetCurHandle();
    unsigned token = 0;
    pthread_mutex_lock(&registry_mutex);
    for (unsigned i = 0; i < NX_PROF_MAX_THREADS; ++i) {
        if (registry[i].handle != handle || registry[i].kind != 'w') continue;
        if (sd_shader_migrate_locked(i, SD_SHADER_PIPELINE)) token = i + 1;
        break;
    }
    pthread_mutex_unlock(&registry_mutex);
    return token;
}

void wine_nx_thread_pipeline_end(unsigned token)
{
    if (!token || token > NX_PROF_MAX_THREADS) return;
    unsigned i = token - 1;
    int restored = 1;
    pthread_mutex_lock(&registry_mutex);
    if (registry[i].handle == threadGetCurHandle() && sd_shader_slots[i].mode == SD_SHADER_PIPELINE)
        restored = sd_shader_restore_locked(i);
    pthread_mutex_unlock(&registry_mutex);
    if (!restored) wine_nx_runtime_trace("[SD-SHADER-AFFINITY] pipeline restoration pending retry");
}
