"""Enable the existing object-aware notification router for F1 circuit waits."""
VERSION='0.1.33-wake2'
BUILD='f1-fextendo-0.1.33-targeted-wake'
PARENT='f1-fextendo-0.1.32-circuit-profile'

def once(text,before,after):
    assert text.count(before)==1,before
    return text.replace(before,after,1)

def apply(source):
    native=source/'wine-nx-probe/source'
    p=native/'runtime.c';text=p.read_text()
    text=once(text,'#define FX_APP_VERSION "0.1.32-prof1"',f'#define FX_APP_VERSION "{VERSION}"')
    text=once(text,f'"{PARENT}"',f'"{BUILD}"')
    text=once(text,'wine_nx_fex_targeted_wake = wine_nx_config_file_bool(RUNTIME_DIR "/fex-targeted-wake.txt", 0);',
        'wine_nx_fex_targeted_wake = wine_nx_config_file_bool(RUNTIME_DIR "/f1-targeted-wake.txt", 0);')
    text=once(text,'[FEX3-SYNC] startup targeted=%d; shared start gates preserved; self-suspend isolated',
        '[FEX3-SYNC] startup targeted=%d; F1 experiment; f1-targeted-wake.txt=1 enables, absent/0 restores broad wakes; shared start gates preserved; self-suspend isolated')
    text=once(text,'[FEX3-HOT] startup_sampler=%d; circuit sampler auto-arms after two 3-25 FPS windows, 60s only; f1-no-sampler.txt=1 disables',
        '[FEX3-HOT] startup_sampler=%d; circuit sampler off by default; f1-sampler.txt=1 opts in for 60s; f1-no-sampler.txt=1 disables')
    p.write_text(text)
    p=native/'thread_profile.c';text=p.read_text()
    text=once(text,'static int f1_profile_enabled = 1;','static int f1_profile_enabled = 0;')
    text=once(text,'f1_profile_enabled=!wine_nx_config_file_bool("sdmc:/switch/f1-fex/f1-no-sampler.txt",0);',
        'f1_profile_enabled=wine_nx_config_file_bool("sdmc:/switch/f1-fex/f1-sampler.txt",0) &&\n            !wine_nx_config_file_bool("sdmc:/switch/f1-fex/f1-no-sampler.txt",0);')
    p.write_text(text)
    p=native/'f1_perf_observer.h';text=p.read_text()
    text=once(text,'sampler=bounded-diagnostic','sampler=opt-in')
    text=once(text,'    wine_nx_thread_report();','    wine_nx_thread_report();\n    fex_sync_report();')
    p.write_text(text)
    p=native/'f1_crash.c';text=once(p.read_text(),PARENT,BUILD)
    text=once(text,'/ crash.log / 0.1.32-prof1',f'/ crash.log / {VERSION}');p.write_text(text)
    return ['wine-nx-probe/source/'+n for n in ('runtime.c','f1_crash.c','thread_profile.c','f1_perf_observer.h')]
