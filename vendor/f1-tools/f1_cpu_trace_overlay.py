"""Passive circuit diagnostics over the shipped 0.1.29-perf1 source."""
from pathlib import Path

VERSION = '0.1.30-cpu1'
BUILD = 'f1-fextendo-0.1.30-cpu-trace'
PARENT = 'f1-fextendo-0.1.29-performance-hud'


def replace_once(text, before, after):
    assert text.count(before) == 1, before
    return text.replace(before, after, 1)


def apply(source: Path):
    native = source / 'wine-nx-probe/source'
    p = native / 'runtime.c'
    text = replace_once(p.read_text(), '#define FX_APP_VERSION "0.1.29-perf1"',
                        f'#define FX_APP_VERSION "{VERSION}"')
    text = replace_once(text, f'"{PARENT}"', f'"{BUILD}"')
    text = replace_once(text, '#include "f1_frame_summary.h"',
                        '#include "f1_frame_summary.h"\n#include "f1_perf_observer.h"')
    text = replace_once(text, '        if (presented) f1_frame_summary(now);',
                        '        if (presented) { f1_frame_summary(now); f1_perf_observer(now); }')
    p.write_text(text)
    (native / 'f1_perf_observer.h').write_bytes(
        Path(__file__).with_name('f1_perf_observer.h').read_bytes())
    p = native / 'f1_crash.c'
    text = replace_once(p.read_text(), PARENT, BUILD)
    text = replace_once(text, '/ crash.log / 0.1.29-perf1', f'/ crash.log / {VERSION}')
    p.write_text(text)
    return ['wine-nx-probe/source/' + name for name in
            ('runtime.c', 'f1_crash.c', 'f1_perf_observer.h')]
