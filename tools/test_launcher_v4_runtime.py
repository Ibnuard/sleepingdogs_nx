"""Execute the generated native counter policy and monitor with host stubs."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess

from launcher_v4_runtime import runtime_overlay

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / "local/launcher-v4-runtime"


def digest(data):
    return hashlib.sha256(data.encode()).hexdigest()


def function(source, signature):
    start = source.index(signature)
    opening = source.index("{", start)
    # Skip prototypes: a declaration's next brace belongs to another function.
    while 0 <= source.find(";", start, opening) < opening:
        start = source.index(signature, start + len(signature))
        opening = source.index("{", start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


def main():
    parser = argparse.ArgumentParser()
    default = "/home/blekjek/sleepingdogs-launcher-v3/source/runtime.c"
    if os.name == "nt":
        default = "//wsl.localhost/Ubuntu" + default
    parser.add_argument("--source", default=default)
    parser.add_argument("--cc", default="gcc")
    args = parser.parse_args()
    original = Path(args.source).read_text(encoding="utf-8")
    candidate = runtime_overlay(original)
    # Dependency/maintenance and input/LSFG paths must remain byte-identical.
    unchanged = ["void __attribute__((noinline)) fx_production_maintenance_tick",
                 "static void *log_flusher", "static void log_line("]
    for signature in unchanged:
        assert function(original, signature) == function(candidate, signature), signature
    assert "horizon_server_profile_enabled = sd_perf_counters || runtime_profile || fx_ui_view.debug || sd_frame_diag_enabled;" in candidate
    assert [x for x in original.splitlines() if "lsfg" in x.lower()] == [x for x in candidate.splitlines() if "lsfg" in x.lower()]
    try:
        runtime_overlay(candidate)
    except ValueError:
        pass
    else:
        raise AssertionError("double application accepted")
    policy = function(candidate, "static int sd_perf_counter_policy")
    monitor_start = candidate.index("        if(__atomic_load_n(&sd_com_enabled,__ATOMIC_ACQUIRE)) {")
    monitor_end = candidate.index("        unsigned presented", monitor_start)
    monitor = candidate[monitor_start:monitor_end]
    begin = candidate.index("    const int sd_perf_generic_requested =")
    end = candidate.index('    runtime_profile = wine_nx_config_file_bool(RUNTIME_DIR "/profile.txt", 0);', begin)
    configure = candidate[begin:end]
    diag_begin = candidate.index("    const int sd_frame_diag_requested =")
    diag_end = candidate.index('    log_line("[SD-DIAG] v4', diag_begin)
    configure_diag = candidate[diag_begin:diag_end]
    code = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define RUNTIME_DIR "runtime"
static int sd_com_enabled,sd_perf_counters,generic_request,native_request;
static int sd_frame_diag_enabled,frame_request,runtime_profile,horizon_server_profile_enabled;
static struct { int debug; } fx_ui_view;
static unsigned reports,progress,remainder,config_reads;
static int wine_nx_config_file_bool(const char *path,int fallback) {
    (void)fallback;
    if(strstr(path,"/native-performance-counters.txt")) {++config_reads;return native_request;}
    assert(strstr(path,"/performance-counters.txt"));return generic_request;
}
static void log_line(const char *fmt,...) {(void)fmt;}
static int sd_sync_load_mode(const char *path) {assert(strstr(path,"/frame-diagnostics.txt"));return frame_request;}
static void sd_com_progress_report(void) {++progress;}
static void sd_perf_summary(uint64_t now,int debug) {assert(now==10000);assert(!debug);++reports;}
'''+policy+"\nstatic void configure(int guest_tests) {\n"+configure+r'''
}
'''+"\nstatic void configure_diagnostics(int guest_tests) {\n"+configure_diag+r'''
}
static void monitor_once(void) {
    uint64_t now=10000;
    for(int once=0;once<1;++once) {
'''+monitor+r'''
        ++remainder;
    }
}
int main(void) {
    unsigned checks=0;
    for(int native=0;native<2;++native)
    for(int guest=0;guest<2;++guest)
    for(int generic=0;generic<2;++generic)
    for(int requested=0;requested<2;++requested)
    for(int debug=0;debug<2;++debug) {
        sd_com_enabled=native;generic_request=generic;native_request=requested;
        fx_ui_view.debug=debug;reports=progress=remainder=config_reads=0;
        configure(guest);
        int expected=native ? (!guest && requested) : generic;
        assert(sd_perf_counters==expected);
        assert(config_reads==(unsigned)native);
        monitor_once();
        assert(progress==(unsigned)native);
        assert(reports==(unsigned)(native && expected));
        assert(remainder==(unsigned)!native);
        /* Legacy Wine frame diagnostics have no native producer or consumer.
         * Debug/profile and the new native summary remain explicit opt-ins. */
        for(int profile=0;profile<2;++profile)
        for(int frame=0;frame<2;++frame) {
            runtime_profile=profile;frame_request=frame;
            configure_diagnostics(guest);
            int expected_frame=!native && !guest && frame;
            assert(sd_frame_diag_enabled==expected_frame);
            assert(horizon_server_profile_enabled==(expected || profile || debug || expected_frame));
            ++checks;
        }
        ++checks;
    }
    assert(checks==160);
    printf("PASS %u policy/monitor cases; generic native default has no consumer or collection\n",checks);
    return 0;
}
'''
    LOCAL.mkdir(parents=True, exist_ok=True)
    fixture = LOCAL / "counter_policy.c"
    fixture.write_text(code, encoding="utf-8", newline="\n")
    executable = LOCAL / ("counter_policy.exe" if os.name == "nt" else "counter_policy")
    command = [args.cc,"-std=c11","-Wall","-Wextra","-Werror","-O2",str(fixture),"-o",str(executable)]
    compiled = subprocess.run(command,capture_output=True,text=True)
    assert compiled.returncode == 0, compiled.stdout+compiled.stderr
    run = subprocess.run([str(executable)],capture_output=True,text=True)
    assert run.returncode == 0, run.stdout+run.stderr
    report = dict(status="PASS", input_sha256=digest(original), generated_sha256=digest(candidate),
                  overlay_sha256=digest((ROOT/"tools/launcher_v4_runtime.py").read_text()),
                  tests_sha256=digest(Path(__file__).read_text()), fixture_sha256=digest(code),
                  compiler=command[0], output=run.stdout.strip(), checks=160,
                  maintenance_unchanged=True, lsfg_lines_unchanged=True,
                  independent_debug_profile_flags_preserved=True,
                  inactive_native_frame_diagnostics_disabled=True,
                  wine_frame_diagnostics_preserved=True,
                  hardware_tested=False, fps_gain_measured=False)
    (LOCAL/"test.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))


if __name__ == "__main__":
    main()
