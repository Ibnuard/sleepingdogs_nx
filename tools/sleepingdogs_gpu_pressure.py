"""Make the GPU reserve a preference, not a reason to fail a fitting allocation."""
from pathlib import Path
from port_common import ROOT
from f1_overlay import exact

MARKER = '[SD-GPU-PRESSURE] v1 soft_reserve=1; reuse idle GPU space before OOM'


def apply(source):
    folder = Path(source) / 'wine-nx-probe/source'
    (folder / 'sd_gpu_pressure.h').write_bytes((ROOT / 'src/sd_gpu_pressure.h').read_bytes())
    p = folder / 'f1_gpu_heap.c'; s = p.read_text()
    s = exact(s, '#include "sd_gpu_stream.h"', '#include "sd_gpu_stream.h"\n#include "sd_gpu_pressure.h"\n'
        'static uint64_t sd_gpu_emergency_takes, sd_gpu_emergency_bytes;')
    s = exact(s, '        p=sd_gpu_stream_take(&f1_gpu_pool,alignment,bytes,1);',
        '''        int emergency=0;
        p=sd_gpu_pressure_take(&f1_gpu_pool,alignment,bytes,&emergency);
        if(emergency) { ++sd_gpu_emergency_takes; sd_gpu_emergency_bytes+=bytes; }''')
    s = exact(s, '    wine_nx_runtime_trace(line);errno=saved_errno;',
        '    wine_nx_runtime_trace(line);\n    wine_nx_runtime_trace("'+MARKER+'");errno=saved_errno;')
    s = exact(s, '    uint64_t live=f1_gpu_pool.live, invalid=f1_gpu_pool.bad_frees;',
        '    uint64_t live=f1_gpu_pool.live, invalid=f1_gpu_pool.bad_frees;\n'
        '    uint64_t emergency_takes=sd_gpu_emergency_takes, emergency_bytes=sd_gpu_emergency_bytes;')
    anchor = '    wine_nx_runtime_trace(line);\n}\n\nvoid wine_nx_f1_gpu_heap_snapshot(void)'
    s = exact(s, anchor, '''    wine_nx_runtime_trace(line);
    snprintf(line,sizeof(line),"[SD-GPU-PRESSURE-STATS] emergency_borrows=%llu requested_bytes=%llu",
        (unsigned long long)emergency_takes,(unsigned long long)emergency_bytes);
    wine_nx_runtime_trace(line);
}

void wine_nx_f1_gpu_heap_snapshot(void)''')
    p.write_text(s, newline='\n')
