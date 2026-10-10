"""Exercise the real fullscreen guard and Wine's scaling decision under ASan."""
from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from build_lsfg_backend import WORK
from prepare_lsfg_native import NATIVE
from port_common import sha,write_json

def main():
    window=(NATIVE/'dlls/win32u/window.c').read_text()
    calc=window[window.index('static BOOL calc_winpos('):window.index('static inline void get_valid_rects(')]
    assert calc.index('send_message(')<calc.index('sd_fix_fullscreen_extent(')<calc.index('new_rects->window.right')
    source=(NATIVE/'dlls/win32u/vulkan.c').read_text()
    start=source.index('static BOOL nx_scaled_host_extent(')
    end=source.index('\n}\n',start)+3
    scaling=source[start:end]
    fixture=WORK/'check-native-v15.c'
    fixture.write_text('''#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include "sd_fullscreen_extent.h"
typedef int BOOL;
#define TRUE 1
#define FALSE 0
typedef struct {uint32_t width,height;} VkExtent2D;
typedef struct {VkExtent2D currentExtent;} VkSurfaceCapabilitiesKHR;
'''+scaling+'''
int main(void) {
    unsigned cases=0; unsigned style=0x15000000u;
    #define CHECK(S,E,F,O,C,W,H,V) do{assert(sd_fullscreen_extent(S,E,F,O,C,W,H)==V);++cases;}while(0)
    CHECK(style,0,0,0,1,1292,732,1);
    CHECK(style,0,0,0,1,1296,736,1);
    CHECK(style,0,0x20,0,1,1292,732,1);
    CHECK(style,0,0,0,1,1280,720,0);
    CHECK(style,0,0,0,1,960,540,0);
    CHECK(style,0,0,0,1,972,552,0);
    CHECK(style,0,0,0,1,1920,1080,0);
    CHECK(style,0,0,0,1,1292,736,0);
    CHECK(style,0,0,0,1,1313,753,0);
    CHECK(style,0,0,0,0,1292,732,0);
    CHECK(style,0,0,1,1,1292,732,0);
    CHECK(style,0,1,0,1,1292,732,0);
    CHECK(style,0,0x80,0,1,1292,732,0);
    CHECK(style&~0x10000000u,0,0,0,1,1292,732,0);
    const unsigned excluded[]={0x40000000u,0x80000000u,0x20000000u,0x00c00000u,0x00040000u};
    for(unsigned i=0;i<sizeof(excluded)/sizeof(*excluded);++i)CHECK(style|excluded[i],0,0,0,1,1292,732,0);
    const unsigned edges[]={1,0x80,0x100,0x200,0x20000};
    for(unsigned i=0;i<sizeof(edges)/sizeof(*edges);++i)CHECK(style,edges[i],0,0,1,1292,732,0);
    VkSurfaceCapabilitiesKHR caps={{1280,720}};VkExtent2D host={0};
    VkExtent2D before={1292,732},after={1280,720},lower={960,540};
    assert(nx_scaled_host_extent(&caps,&before,&host));
    assert(!nx_scaled_host_extent(&caps,&after,&host));
    assert(nx_scaled_host_extent(&caps,&lower,&host));
    printf("PASS: %u fullscreen guard cases, original Wine scaling path removed at corrected 720p; lower modes still scale\\n",cases);
}
''')
    exe=WORK/'check-native-v15'
    subprocess.run(['cc','-O2','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all',
        '-I'+str(ROOT/'tools'),str(fixture),'-o',str(exe)],check=True)
    result=subprocess.run([str(exe)],capture_output=True,text=True,check=True)
    print(result.stdout)
    write_json(ROOT/'reports/native-v15-host-check.json',dict(status='PASS',output=result.stdout,
        helper_sha256=sha(ROOT/'tools/sd_fullscreen_extent.h'),
        window_sha256=sha(NATIVE/'dlls/win32u/window.c'),vulkan_sha256=sha(NATIVE/'dlls/win32u/vulkan.c'),
        hardware_tested=False,fps_gain_measured=False))

if __name__=='__main__':main()
