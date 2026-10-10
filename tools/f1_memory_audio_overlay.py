"""F1-only circuit memory reservation, game graphics migration and audio setup."""
from pathlib import Path
from f1_overlay import exact, replace_function

TOOLS = Path(__file__).resolve().parent


def patch_scratch(source: str) -> str:
    source = exact(source, '''static void host_log(const char *message) {
    if (host_logger) host_logger(message);
}''', '''extern void wine_nx_f1_compiler_stopped(unsigned bytes);
static void host_log(const char *message) {
    if (host_logger) host_logger(message);
    /* module_memory.cpp Stop() logs these fixed messages then traps. Route
     * that confirmed fatal condition to the independent restart worker before
     * trapping inside the PE module. Never classify recoverable OOM as fatal. */
    if (!strcmp(message, "[FEX2-HEAP] STOP compiler scratch failed bytes=0x0000000000800000"))
        wine_nx_f1_compiler_stopped(8u * 1024u * 1024u);
    else if (!strcmp(message, "[FEX2-HEAP] STOP compiler scratch failed bytes=0x0000000001000000"))
        wine_nx_f1_compiler_stopped(16u * 1024u * 1024u);
}''')
    source = exact(source, 'static void *allocate_scratch(uint64_t requested) {',
                   '#include "f1_scratch.h"\n\nstatic void *allocate_scratch(uint64_t requested) {')
    # Only the unguarded scratch callback. Code memory / private CRT heap keep
    # their original allocation and lifetime protocols.
    start = source.index('static void *allocate_scratch(uint64_t requested) {')
    end = source.index('\n}', start) + 2
    body = exact(source[start:end], 'aligned_alloc(PAGE_BYTES, size)', 'f1_scratch_alloc(size)')
    source = source[:start] + body + source[end:]
    source = exact(source, 'static void release_scratch(void *address) { free(address); }',
                   'static void release_scratch(void *address) { f1_scratch_free(address); }')
    return exact(source, 'const struct pes13_fex_host *pes13_fex_native_host(void) {',
                 'const struct pes13_fex_host *pes13_fex_native_host(void) {\n    f1_scratch_init();')


def wrap_audio(source: str, name: str, params: str, fields: str) -> str:
    signature = f'static NTSTATUS {name}(void *args)'
    start = source.index(signature)
    end = source.index('\n}', start) + 2
    original = source[start:end].replace(name+'(', 'f1_original_'+name+'(', 1)
    wrapper = signature + '''
{
    NTSTATUS status = f1_original_''' + name + '''(args);
    struct ''' + params + '''_params *p = args;
    static unsigned calls;
    if (__atomic_add_fetch(&calls, 1, __ATOMIC_RELAXED) <= 8) {
        char line[224];
        snprintf(line, sizeof(line), ''' + fields + ''');
        wine_nx_runtime_trace(line);
    }
    return status;
}'''
    return source[:start] + original + '\n' + wrapper + source[end:]


def patch_audio(source: str) -> str:
    source = exact(source, '#define NX_RATE 48000',
        '#include <stdio.h>\nextern void wine_nx_runtime_trace(const char *);\n'
        'static unsigned long long f1_audio_nonzero_frames;\n#define NX_RATE 48000')
    source = wrap_audio(source, 'nx_test_connect', 'test_connect',
        '"[F1-AUDIO] connect priority=%d initialized=%d", p->priority, initialized')
    source = wrap_audio(source, 'nx_create_stream', 'create_stream',
        '"[F1-AUDIO] create result=%08x rate=%u channels=%u bits=%u share=%u flags=%08x", '
        '(unsigned)p->result, p->fmt?p->fmt->nSamplesPerSec:0, p->fmt?p->fmt->nChannels:0, '
        'p->fmt?p->fmt->wBitsPerSample:0, (unsigned)p->share, (unsigned)p->flags')
    source = wrap_audio(source, 'nx_start', 'start',
        '"[F1-AUDIO] start result=%08x", (unsigned)p->result')
    source = exact(source, '            ((short *)dst)[1] = right * s->volume[1];',
        '            ((short *)dst)[1] = right * s->volume[1];\n'
        '            if (((short *)dst)[0] || ((short *)dst)[1]) ++f1_audio_nonzero_frames;')
    # The backend has four DMA buffers; resetting only two leaves stale frame
    # ownership when XAudio stops/restarts its stream.
    source = exact(source, '            s->read = s->held = s->submitted = s->frames[0] = s->frames[1] = 0;',
        '            s->read = s->held = s->submitted = 0;\n'
        '            memset(s->frames, 0, sizeof(s->frames));')
    return source + '''
void wine_nx_f1_audio_snapshot(void)
{
    char line[224];
    if (pthread_mutex_trylock(&audio_lock)) {
        wine_nx_runtime_trace("[F1-AUDIO] snapshot busy");
        return;
    }
    unsigned running = active ? active->running : 0, failed = active ? active->failed : 0;
    unsigned submitted = active ? active->submitted : 0, held = active ? active->held : 0;
    unsigned long long played = active ? active->played : 0, nonzero = f1_audio_nonzero_frames;
    unsigned connected = initialized, stream = active != NULL;
    pthread_mutex_unlock(&audio_lock);
    snprintf(line, sizeof(line), "[F1-AUDIO] connected=%u stream=%u running=%u failed=%u held=%u submitted=%u played=%llu nonzero=%llu",
        connected, stream, running, failed, held, submitted, played, nonzero);
    wine_nx_runtime_trace(line);
}
'''


def apply(source: Path):
    runtime = source / 'wine-nx-probe/source/runtime.c'
    data = runtime.read_text()
    data = exact(data, 'static int fx_launcher_start(void) {',
        '#include "f1_game_config.h"\nstatic int fx_launcher_start(void) {')
    data = exact(data, '        if(ready){\n            unsigned crash_rc=',
        '        if(ready){\n'
        '            int graphics_migration=f1_prepare_game_graphics(RUNTIME_DIR);\n'
        '            log_line("[F1-GRAPHICS] migration=circuit-memory-v5 status=%d (2=applied,1=already applied,0=failed); target=1280x720 fullscreen + lowest scene/GPU detail; CPU/physics/input preserved; backup=.pre-0.1.27.bak",graphics_migration);\n'
        '            char graphics_summary[512];\n'
        '            f1_game_graphics_summary(RUNTIME_DIR,graphics_summary,sizeof(graphics_summary));\n'
        '            log_line("[F1-GRAPHICS] active My Games/FormulaOne2013: %s",graphics_summary);\n'
        '            unsigned crash_rc=')
    runtime.write_text(data)
    (runtime.parent / 'f1_game_config.h').write_bytes((TOOLS / 'f1_game_config.h').read_bytes())
    # The base driver enumerates only 720p. Let F1 retain the 540p selection
    # instead of treating the migrated resolution as an unavailable mode.
    display = source / 'dlls/win32u/winnx_drv.c'
    modes = exact(display.read_text(), '    dm->add_modes( &current, 1, &mode, param );',
        '    DEVMODEW modes[2] = {mode, mode};\n'
        '    modes[1].dmPelsWidth = 960; modes[1].dmPelsHeight = 540;\n'
        '    dm->add_modes( &current, 2, modes, param );\n'
        '    nxdrv_trace( "[F1-MODES] 1280x720 + 960x540; desktop remains 1280x720", 0, 0, 0, 0 );')
    display.write_text(modes)
    audio = runtime.parent / 'audio_unix.c'
    audio.write_text(patch_audio(audio.read_text()))
    registry = source / 'dlls/ntdll/unix/horizon_registry_server.h'
    data = exact(registry.read_text(), '#include "f1_crypto_registry.h"',
                 '#include "f1_crypto_registry.h"\n#include "f1_audio_registry.h"')
    data = exact(data, '    horizon_registry_hives[0] = machine;', '''    {
        unsigned status = f1_audio_registry_install(&horizon_registry, machine);
        char line[128];
        snprintf(line, sizeof(line), "[F1-AUDIO] DirectSound8/XAudio2.7 COM registration status=%08x", status);
        wine_nx_runtime_trace(line);
        if (status) {
            horizon_reg_release(&horizon_registry, horizon_registry.root);
            horizon_registry.root = NULL;
            return status;
        }
    }
    horizon_registry_hives[0] = machine;''')
    registry.write_text(data)
    (registry.parent / 'f1_audio_registry.h').write_bytes((TOOLS / 'f1_audio_registry.h').read_bytes())
