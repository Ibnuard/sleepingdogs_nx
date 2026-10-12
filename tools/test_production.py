"""Execute quiet logging, real native Logger and independent history maintenance."""
from pathlib import Path
import hashlib,json,subprocess,tempfile
from production_overlay import ROOT
from test_launcher_v4_runtime import function
WORK=Path('/home/blekjek/sleepingdogs-production-v1')
LOCAL=ROOT/'local/production-v1'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(args):
    p=subprocess.run([str(x) for x in args],capture_output=True,text=True,timeout=180)
    assert not p.returncode,(args,p.stdout,p.stderr)
    return p.stdout.strip()
def main():
    source=(WORK/'source/runtime.c').read_text();build=json.loads((LOCAL/'build.json').read_text())
    assert sha(WORK/'source/runtime.c')==build['generated_sources']['source/runtime.c']
    tests=WORK/'production-tests';tests.mkdir(exist_ok=True)
    environment=tests/'environment'
    run(['gcc','-std=c11','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all',
         '-I'+str(WORK/'source'),ROOT/'tests/production_environment.c','-o',environment])
    results={'environment':run([environment])}
    dxvk=Path('/home/blekjek/sleepingdogs-dxvk-arm64-v1/source')
    logger=tests/'logger'
    run(['g++','-std=c++17','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all',
         '-I'+str(dxvk/'src/util/log'),'-I'+str(dxvk/'include/native/windows'),
         '-I'+str(dxvk/'include/native'),'-I'+str(dxvk/'include'),
         WORK/'source/dxvk-log.cpp',ROOT/'tests/production_logger.cpp','-pthread','-o',logger])
    with tempfile.TemporaryDirectory() as folder:results['native_logger']=run([logger,folder])
    history=function(source,'static void fx_history_flush(void)')
    maintenance=function(source,'void __attribute__((noinline)) fx_production_maintenance_tick')
    code=r'''
#include <assert.h>
#include <stdint.h>
#include <time.h>
#include <stdio.h>
#include "diagnostics.h"
#define RUNTIME_DIR "fixture"
static uint64_t fx_history_tick,tick;static int fx_history_written,fx_debug_live;
static unsigned registry,balance,clean,streams,history_writes;static uint64_t saved_time;
static time_t now=1700000000;
static uint64_t armGetSystemTick(void){return tick;}
static uint64_t armTicksToNs(uint64_t t){return t;}
static time_t fixture_time(time_t *unused){(void)unused;return now;}
#define time fixture_time
static void log_line(const char *s){(void)s;assert(0);}
static int fx_last_played_save(const char *root,uint64_t t){(void)root;++history_writes;saved_time=t;return 1;}
int horizon_registry_flush(void){++registry;return 1;}
static void wine_nx_thread_balance(void){++balance;}
static void runtime_alternate_clean(void){++clean;}
static void runtime_tick_std_streams(void){++streams;}
'''+history+'\n'+maintenance+r'''
int main(void){
    sd_production_select_debug(0);assert(!wine_nx_sd_diagnostics_active());
    for(unsigned i=1;i<=10;++i)fx_production_maintenance_tick(i);
    assert(registry==2&&balance==1&&clean==10&&streams==0&&history_writes==0);
    fx_history_tick=1000000000;tick=6000000000;
    for(unsigned i=11;i<=30;++i)fx_production_maintenance_tick(i);
    assert(history_writes==1&&saved_time==1699999995&&streams==0);
    assert(registry==6&&balance==3&&clean==30);
    sd_production_select_debug(1);fx_debug_live=1;
    fx_production_maintenance_tick(31);assert(streams==1&&history_writes==1);
    puts("PASS actual maintenance: quiet registry/balance, first-frame last played exactly once, explicit Debug");
}
'''
    fixture=tests/'maintenance.c';fixture.write_text(code)
    run(['gcc','-std=c11','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all',
         '-I'+str(WORK/'source'),fixture,'-o',tests/'maintenance'])
    results['maintenance']=run([tests/'maintenance'])
    assert 'if(fx_ui_view.debug&&!fx_debug_file)fx_debug_file=f1_open_runtime_log' in source
    assert 'fx_ui_view.debug?wine_nx_f1_crash_init(1,renderer,selected):0' in source
    assert 'if(wine_nx_sd_diagnostics_active()) {\n    pthread_t startup_monitor;' in source
    assert 'if(!wine_nx_sd_diagnostics_active())return;' in (WORK/'source/checker_runtime.h').read_text()
    assert 'if(!wine_nx_sd_diagnostics_active()){wine_nx_sd_com_first_present();return;}' in (WORK/'source/com_horizon.cpp').read_text()
    catalog=json.loads((LOCAL/'catalog.json').read_text());assert not any(e['path'].startswith('lsfg/') for e in catalog)
    report=dict(status='PASS',results=results,generated_sources=build['generated_sources'],
                sources={p.relative_to(ROOT).as_posix():sha(p) for p in (Path(__file__),ROOT/'tests/production_environment.c',ROOT/'tests/production_logger.cpp')},
                nro_sha256=build['nro_sha256'],normal_logs=False,last_played_independent=True,
                optional_lsfg_not_required=True,hardware_tested=False)
    (LOCAL/'policy-test.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(results,indent=2))
if __name__=='__main__':main()
