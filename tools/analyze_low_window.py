"""Audit the latest OOM and Autorun's pinned 39-bit low-window implementation.

Read-only with respect to installed runtimes, game files and boot configuration.
Downloaded upstream sources are kept under local/autorun-memory-audit.
"""
from pathlib import Path
import hashlib, json, re, subprocess
import pefile
from port_common import ROOT, sha, write_json


def main():
    research = ROOT / 'local/autorun-memory-audit'
    upstream = json.loads((research / 'upstream.json').read_text(encoding='utf-8-sig'))
    assert upstream['commit'] == 'cbb0e4e6e7fa7f47f328d92441f51bfb507f266f'
    tree = json.loads((research / 'tree.json').read_text(encoding='utf-8-sig'))
    by_path = {item['path']:item for item in tree['tree'] if item['type'] == 'blob'}
    manifest = {}
    for path in research.rglob('*'):
        if not path.is_file(): continue
        relative = path.relative_to(research).as_posix()
        if relative not in by_path: continue
        data = path.read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        assert blob == by_path[relative]['sha'], relative
        manifest[relative] = {'git_blob':blob, 'sha256':sha(path)}
    write_json(research / 'fetched-source-manifest.json', manifest)
    origin = Path('D:/Dev/Personal/UNDANGAN/fex-runtime.log')
    snapshot = ROOT / 'reports/autorun-memory-input/fex-runtime.log'
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    data = origin.read_bytes()
    if snapshot.exists(): assert snapshot.read_bytes() == data, 'Preserve the existing input snapshot'
    else: snapshot.write_bytes(data)
    log = data.decode(errors='replace')
    budget = re.findall(r'\[SD-MEMBUDGET\].*total=(\d+) used=(\d+) free=(\d+)', log)
    resources = re.findall(r'\[SD-RESOURCE\].*heap_used=(\d+) arena_free=(\d+) heap_arena=(\d+) heap_capacity=(\d+) heap_unclaimed=(\d+) heap_available=(\d+)', log)
    recycle = re.findall(r'\[SD-DXVK-RECYCLE\] event=reuse bytes=(\d+) idle_bytes=(\d+) hits=(\d+)', log)
    failures = re.findall(r'\[SD-DXVK-MAP\] deferred buffer allocation failed: bytes=(\d+)', log)
    assert budget and resources and recycle and failures
    assert {int(row[0]) for row in budget} == {2147483648}
    assert {int(n) for n in failures} == {4194304, 5242880}
    assert '[SD-FIRSTFAULT] access=1 target=40' in log
    assert '[SD-FEX-MODE] source=launcher/fex-mode.txt: fastest' in log
    patch = (research / 'horizon-wine/mesosphere/low-window.patch').read_text()
    assert 'program_id == UINT64_C(0x0548EABB35576000)' in patch
    assert 'AutorunNativeAddressStart = UINT64_C(0x100000000)' in patch
    assert 'm_alias_code_region_start = ams::svc::AddressSmallMap32Start' in patch
    assert 'aslr_start = svc::AutorunNativeAddressStart' in patch
    config = (research / 'horizon-wine/build-low-window.sh').read_text()
    assert 'revision=5388824be146a89619e8d641acd64599cf1c5f62' in config
    forwarder = (ROOT / 'forwarder/build_forwarder.py').read_text()
    assert 'address_space_type=2' in forwarder
    target = '/switch/sleepingdogs-fex/sleepingdogs-fex.nro'
    title_id = 0x0500000000000000 | (int.from_bytes(hashlib.sha256((target * 2).encode()).digest()[:8], 'little') & 0x00FFFFFFFFFFF000)
    assert title_id == 0x059a3db219b42000
    assert 'sd_host_size>0x100000000ULL' in (ROOT / 'tools/sleepingdogs_overlay.py').read_text()
    assert '(uintptr_t)base >= UINT64_C(0x100000000)' in (ROOT / 'src/sd_guest_arena.c').read_text()
    exe = ROOT.parent / 'Sleeping Dogs/HKShip.exe'
    with pefile.PE(str(exe), fast_load=True) as pe:
        game = {'image_base':hex(pe.OPTIONAL_HEADER.ImageBase),
                'large_address_aware':bool(pe.FILE_HEADER.Characteristics & 0x20),
                'relocations_stripped':bool(pe.FILE_HEADER.Characteristics & 1), 'sha256':sha(exe)}
    assert game['image_base'] == '0x400000' and not game['large_address_aware']
    # Run the unmodified upstream host suite. Its AArch64 execution branch is
    # excluded on x86_64; its SVC boundaries are mocks, not a Switch kernel.
    run = subprocess.run(['wsl', '-d', 'Ubuntu', '--cd',
        '/mnt/d/Dev/Switch/SwitchHub/sleepingdogs-fex/local/autorun-memory-audit',
        '--', 'env', 'CC=gcc', 'sh', 'horizon-wine/check-low-window.sh'],
        capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stdout + run.stderr
    assert run.stdout.count('passed') == 4
    report = {
        'audit_complete':True, 'runtime_changed':False, 'boot_files_installed':False,
        'new_switch_build_produced':False, 'hardware_tested':False,
        'input':{'origin':str(origin), 'snapshot':str(snapshot), 'sha256':sha(snapshot)},
        'upstream':upstream, 'upstream_verified_files':manifest,
        'user_environment':{'hos_reported':'22.5', 'atmosphere':'1.11.2', 'boot':'Hekate', 'hoc_or_custom_kernel':'not specified'},
        'latest_log':{'process_budget_bytes':int(budget[-1][0]),
            'last_logged_reuse_hits':int(recycle[-1][2]), 'map_failures_bytes':[int(n) for n in failures],
            'native_heap':dict(zip(('used','free_fragments','arena','capacity','unclaimed','available'), map(int,resources[-1]))),
            'fault_target':'0x40', 'fex_profile':'fastest'},
        'game':game,
        'finding':'The 32-bit no-alias layout imposes a real 2 GiB process ceiling. Retired-buffer reuse is active but does not prevent this scene OOM.',
        'upstream_solution':{'host_bits':39, 'native_address_floor':'0x100000000',
            'guest_window':['0x00200000','0x100000000'], 'base_atmosphere_commit':'5388824be146a89619e8d641acd64599cf1c5f62',
            'base_application_pool_mib_4gb_console':3285, 'full_4gib_physical_heap_promised':False,
            'guest_non_laa_limit_bytes':2147483648, 'guest_laa_limit_bytes':4294967296,
            'note':'Physical memory remains limited by the application pool and overhead. Low guest aliases do not duplicate backing RAM.'},
        'port_requirements':[
            {'component':'kernel and loader', 'reason':'Whitelist the Sleeping Dogs title as well as Autorun; the stock upstream whitelist cannot enable this launcher.',
             'sleepingdogs_title':f'{title_id:016x}', 'autorun_title':'0548eabb35576000'},
            {'component':'forwarder and runtime preflight', 'reason':'Select 39-bit NPDM; reserve the guest window before native mappings; require executable 0x00400000 and writable high-edge alias probes.'},
            {'component':'guest data arena', 'reason':'Current 1000 MiB arena rejects high backing addresses. Replace or bypass the direct-heap path with high backing mapped into the low guest window, preserving ownership and protection semantics.'},
            {'component':'native/guest allocation routing', 'reason':'Keep stacks, JIT/native views and backing high; audit FEX and Vulkan mappings returned to x86 for valid low pointers.'}
        ],
        'upstream_host_checks':{'status':'PASS','output':run.stdout.strip(),
            'scope':'Unmodified upstream x86_64 host checks; mocked SVCs. AArch64 low-address execution and actual Horizon boot were not run.'},
        'remaining_uncertainty':'More native RAM is plausible and removes this address-mode ceiling; it does not yet demonstrate successful Sleeping Dogs 3D gameplay.',
        'references':[
            'https://github.com/autorunhq/autorun/blob/'+upstream['commit']+'/horizon-wine/mesosphere/README.txt',
            'https://github.com/autorunhq/autorun/blob/'+upstream['commit']+'/horizon-wine/mesosphere/low-window.patch',
            'https://github.com/autorunhq/autorun/blob/'+upstream['commit']+'/horizon-wine/source/low_window.c',
            'https://github.com/Atmosphere-NX/Atmosphere/blob/5388824be146a89619e8d641acd64599cf1c5f62/libraries/libmesosphere/source/kern_k_address_space_info.cpp',
            'https://github.com/Atmosphere-NX/Atmosphere/blob/5388824be146a89619e8d641acd64599cf1c5f62/libraries/libmesosphere/source/board/nintendo/nx/kern_k_system_control.cpp',
            'https://github.com/Atmosphere-NX/Atmosphere/releases/tag/1.11.2'
        ],
        'local_sources':{n:sha(ROOT/n) for n in ('tools/analyze_low_window.py','tools/sleepingdogs_overlay.py','src/sd_guest_arena.c','src/sd_guest_view.inc','forwarder/build_forwarder.py')}
    }
    write_json(ROOT / 'reports/autorun-low-window-audit.json', report)
    print(json.dumps({'audit_complete':True, 'process_budget_bytes':report['latest_log']['process_budget_bytes'],
        'reuse_hits':report['latest_log']['last_logged_reuse_hits'], 'verified_upstream_files':len(manifest),
        'upstream_host_checks':'PASS', 'new_switch_build_produced':False}))


if __name__ == '__main__': main()
