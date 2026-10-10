"""Prepare a reversible automatic-affinity overlay on the delivered v16 inputs."""
from pathlib import Path
import difflib
import os
import shutil
from port_common import ROOT, sha, write_json
from prepare_lsfg_native import replace
from sleepingdogs_direct_sync import change_function, function

LINUX_WORK = '/home/blekjek/sleepingdogs-scheduler-v17'
def host_path(path):
    return Path('//wsl.localhost/Ubuntu' + path) if os.name == 'nt' else Path(path)
WORK = host_path(LINUX_WORK)
NATIVE = WORK / 'native-source'
BASE = host_path('/home/blekjek/sleepingdogs-sync-v16/native-source')
HORIZON = 'dlls/ntdll/unix/'
RUNTIME = 'wine-nx-probe/source/'
CHANGED = (HORIZON+'horizon.c', HORIZON+'thread.c', RUNTIME+'thread_profile.c',
           RUNTIME+'runtime.c', RUNTIME+'sd_shader_affinity.h')

POLICY = r'''
/* The OS may schedule ordinary runnable Wine threads on any application core.
 * Registry ownership excludes accepted explicit masks and shader/core-3 work.
 * No syscall or server-follow state is changed after a failed query/set. */
static uint64_t sd_scheduler_counts[6]; /* applied, correct, query failure, set failure, process failure, no cores */
static uint64_t sd_scheduler_pin_counts[2];

void wine_nx_sd_scheduler_pin_result(int failed)
{
    __atomic_add_fetch(&sd_scheduler_pin_counts[!!failed], 1, __ATOMIC_RELAXED);
}

static void sd_scheduler_update(u64 process_mask)
{
    const u64 allowed = sd_auto_allowed_mask(process_mask);
    pthread_mutex_lock(&registry_mutex);
    if (!allowed) {
        ++sd_scheduler_counts[5];
        pthread_mutex_unlock(&registry_mutex);
        return;
    }
    for (unsigned i = 0; i < NX_PROF_MAX_THREADS; ++i) {
        struct nx_prof_thread *thread = &registry[i];
        s32 preferred;
        u64 actual;
        /* Pending explicit/helper restores must run before eligibility. */
        if (thread->handle) sd_shader_retry_locked(i);
        if (!thread->handle || thread->kind != 'w' || thread->fixed ||
            fex_dxvk_slots[i].active || sd_shader_slots[i].mode) continue;
        if (R_FAILED(svcGetThreadCoreMask(&preferred, &actual, thread->handle))) {
            ++sd_scheduler_counts[2];
            continue;
        }
        if (actual == allowed) {
            ++sd_scheduler_counts[1];
            /* A successful query confirms this mask without another Set SVC.
             * The main thread may already have it before a pipe is created. */
            if (thread->teb && horizon_follow_thread_cores)
                horizon_follow_thread_cores((void *)(uintptr_t)thread->teb, (unsigned)allowed);
            continue;
        }
        preferred = sd_auto_preferred(allowed, preferred, thread->core);
        if (R_FAILED(svcSetThreadCoreMask(thread->handle, preferred, allowed))) {
            ++sd_scheduler_counts[3];
            continue;
        }
        ++sd_scheduler_counts[0];
        if (thread->teb && horizon_follow_thread_cores)
            horizon_follow_thread_cores((void *)(uintptr_t)thread->teb, (unsigned)allowed);
    }
    pthread_mutex_unlock(&registry_mutex);
}

static void sd_scheduler_report(void)
{
    uint64_t c[6];
    char line[320];
    if (!wine_nx_sd_auto_affinity) return;
    pthread_mutex_lock(&registry_mutex);
    memcpy(c, sd_scheduler_counts, sizeof(c));
    pthread_mutex_unlock(&registry_mutex);
    snprintf(line, sizeof(line), "[SD-SCHED-V17] applied=%llu already_correct=%llu query_failed=%llu set_failed=%llu process_query_failed=%llu no_app_cores=%llu initial_ok=%llu initial_failed=%llu; cumulative, no FPS inference",
        (unsigned long long)c[0], (unsigned long long)c[1], (unsigned long long)c[2],
        (unsigned long long)c[3], (unsigned long long)c[4], (unsigned long long)c[5],
        (unsigned long long)__atomic_load_n(&sd_scheduler_pin_counts[0], __ATOMIC_RELAXED),
        (unsigned long long)__atomic_load_n(&sd_scheduler_pin_counts[1], __ATOMIC_RELAXED));
    wine_nx_runtime_trace(line);
}
'''

def main():
    NATIVE.mkdir(parents=True, exist_ok=True)
    shutil.copytree(BASE, NATIVE, dirs_exist_ok=True)
    before = {n: (BASE/n).read_text() for n in CHANGED}
    header = 'sd_auto_affinity_v17.h'
    for rel in (HORIZON, RUNTIME):
        shutil.copy2(ROOT/'src/low_window'/header, NATIVE/rel/header)
    source = before[HORIZON+'horizon.c']
    anchor = 'void horizon_pin_current_thread( ULONG_PTR requested_mask )'
    source = replace(source, anchor, '#include "sd_auto_affinity_v17.h"\n\n'+anchor)
    def pin(f):
        f = replace(f, '    Result rc;\n', '    Result rc;\n    int automatic_v17 = 0;\n')
        old = '''        const ULONG_PTR automatic = fex_auto_worker_mask(system_mask, wine_nx_fex_auto_core3);
        unsigned int count = count_mask_bits( automatic );

        index = InterlockedIncrement( &next_core_index ) - 1;
        mask = nth_core_mask( automatic, index % count );'''
        new = '''        ULONG_PTR automatic;
        unsigned int count;
        if (wine_nx_sd_auto_affinity) {
            u64 granted = 0;
            /* Unlike the historical cached mask, a failed query grants nothing. */
            rc = svcGetInfo(&granted, InfoType_CoreMask, CUR_PROCESS_HANDLE, 0);
            automatic = sd_auto_allowed_mask(granted);
            if (R_FAILED(rc) || !automatic) {
                wine_nx_sd_scheduler_pin_result(1);
                return;
            }
            automatic_v17 = 1;
        } else automatic = fex_auto_worker_mask(system_mask, wine_nx_fex_auto_core3);
        count = count_mask_bits(automatic);
        index = InterlockedIncrement(&next_core_index) - 1;
        mask = nth_core_mask(automatic, index % count);
        preferred = lowest_set_core(mask);
        if (automatic_v17) mask = automatic;'''
        f = replace(f, old, new)
        f = replace(f, '    preferred = lowest_set_core( mask );',
                    '    if (!automatic_v17) preferred = lowest_set_core( mask );')
        f = replace(f, '    if (R_FAILED(rc))\n',
                    '    if (automatic_v17) wine_nx_sd_scheduler_pin_result(R_FAILED(rc));\n    if (R_FAILED(rc))\n')
        return f
    source = change_function(source, 'horizon_pin_current_thread', pin)
    (NATIVE/HORIZON/'horizon.c').write_text(source, newline='\n')

    thread = before[HORIZON+'thread.c']
    thread = replace(thread, 'static int fex_dxvk_explicit_affinity(HANDLE handle, ULONG_PTR mask)',
        'extern int wine_nx_sd_auto_affinity;\nstatic int fex_dxvk_explicit_affinity(HANDLE handle, ULONG_PTR mask)')
    thread = replace(thread,
        'if (!status && is_current_thread_handle( handle )) horizon_pin_current_thread( req_aff->Mask );',
        'if (!status && !(wine_nx_sd_auto_affinity && fex_dxvk_explicit_affinity(handle, req_aff->Mask)) &&\n'
        '            is_current_thread_handle(handle)) horizon_pin_current_thread(req_aff->Mask);')
    (NATIVE/HORIZON/'thread.c').write_text(thread, newline='\n')

    profile = before[RUNTIME+'thread_profile.c']
    profile = replace(profile, '#include "thread_profile.h"',
                      '#include "thread_profile.h"\n#include "sd_auto_affinity_v17.h"')
    profile = replace(profile, 'void wine_nx_thread_report( void )', POLICY+'\nvoid wine_nx_thread_report( void )')
    profile = change_function(profile, 'wine_nx_thread_report', lambda f: replace(f,
        '    server_report();', '    sd_scheduler_report();\n    server_report();'))
    old = '''    if (!wine_nx_balance_enabled || R_FAILED( svcGetInfo( &process_mask, InfoType_CoreMask, CUR_PROCESS_HANDLE, 0 ) ))
        return;'''
    new = '''    if (!wine_nx_balance_enabled) return; /* no-balance.txt also disables registry updates */
    if (R_FAILED(svcGetInfo(&process_mask, InfoType_CoreMask, CUR_PROCESS_HANDLE, 0))) {
        if (wine_nx_sd_auto_affinity) {
            pthread_mutex_lock(&registry_mutex);
            ++sd_scheduler_counts[4];
            pthread_mutex_unlock(&registry_mutex);
        }
        return;
    }
    if (wine_nx_sd_auto_affinity) {
        sd_scheduler_update(process_mask);
        return; /* Never feed automatic broad masks back into the pinning balancer. */
    }'''
    profile = change_function(profile, 'wine_nx_thread_balance', lambda f: replace(f, old, new))
    (NATIVE/RUNTIME/'thread_profile.c').write_text(profile, newline='\n')
    shader = replace(before[RUNTIME+'sd_shader_affinity.h'],
        'if (!mask || (!s->mode && (!sd_shader_enabled || fex_dxvk_slots[i].active))) return 0;',
        'if (!mask || (!s->mode && ((!sd_shader_enabled && !wine_nx_sd_auto_affinity) || fex_dxvk_slots[i].active))) return 0;')
    (NATIVE/RUNTIME/'sd_shader_affinity.h').write_text(shader, newline='\n')
    runtime = before[RUNTIME+'runtime.c']
    runtime = replace(runtime, 'int wine_nx_fex_auto_core3;',
                      'int wine_nx_fex_auto_core3;\nint wine_nx_sd_auto_affinity;')
    runtime = replace(runtime, 'sleepingdogs-fextendo-0.1.0-v16-sync-notify',
                      'sleepingdogs-fextendo-0.1.0-v17-scheduler')
    runtime = replace(runtime, '#define FX_APP_VERSION "0.1.0-v16-sync"',
                      '#define FX_APP_VERSION "0.1.0-v17-sched"')
    anchor = '    log_line( "[INIT] core balancing %s (no-balance.txt)", wine_nx_balance_enabled ? "on" : "off" );'
    runtime = replace(runtime, anchor, anchor+'''
    wine_nx_sd_auto_affinity = !guest_tests && wine_nx_config_file_bool(RUNTIME_DIR "/auto-affinity.txt", 1);
    log_line("[SD-SCHED-V17] mode=%s coremask=%s periodic=%d; explicit affinity, shader and core3 helpers preserved; no-balance.txt disables periodic updates",
        wine_nx_sd_auto_affinity ? "auto" : "v16-pinned",
        wine_nx_sd_auto_affinity ? "process&7" : "v16-policy", wine_nx_balance_enabled);''')
    (NATIVE/RUNTIME/'runtime.c').write_text(runtime, newline='\n')
    patch = ''.join(''.join(difflib.unified_diff(before[n].splitlines(True),
        (NATIVE/n).read_text().splitlines(True), fromfile='a/'+n, tofile='b/'+n)) for n in CHANGED)
    (WORK/'v17.patch').write_text(patch, newline='\n')
    write_json(WORK/'prepared.json', dict(source=LINUX_WORK+'/native-source',
        base='/home/blekjek/sleepingdogs-sync-v16/native-source', changed_files=list(CHANGED)+
        [HORIZON+header, RUNTIME+header], input_sha256={n:sha(BASE/n) for n in CHANGED},
        files={p.relative_to(NATIVE).as_posix():sha(p) for p in NATIVE.rglob('*') if p.is_file()},
        hardware_tested=False, fps_gain_measured=False, mode='automatic process&7; OFF v16 scheduler'))
    print('Prepared v17 scheduler source overlay; no build, SDK or baseline changes', flush=True)

if __name__ == '__main__':
    main()
