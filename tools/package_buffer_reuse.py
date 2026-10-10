"""Cumulative retired-buffer update; preserve the proven native/FEX pair."""
from pathlib import Path
import argparse, hashlib, json, shutil, tempfile, zipfile
from port_common import ROOT, sha, write_json
from package_named_pipe import PREFIX, archive, encode
from package_dxvk_memory import interfaces
from package_streaming_memory import executable_sections
from build_dxvk_memory import manifest
from sleepingdogs_dxvk_recycle import apply, FILES
from dxvk_runtime import effective_release, release_files

PRIOR_SHA = '95d31c4440fea782f3798b4fd14bb26e5e0b34df96e84c8c57c02a02bf6fb277'
NRO_SHA = 'de0a9ea83adcdf8e68a1b0cd3d8383af50e911ec99e7e43149ddadb98367b0f7'
FEX_SHA = '48b169a80966676100c7b361343072766973809a80727cb2fcfe8bb33a300024'
FW_SHA = '222269d0bc876b970a1a82a82890223909dd6811776232041e7b8966c4756781'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-buffer-reuse-v2'))
    work = parser.parse_args().work
    out = ROOT / 'dist/buffer-reuse-fix'
    build = json.loads((out / 'build.json').read_text())
    staged = json.loads((out / 'staged.json').read_text())
    previous_source = Path('/home/blekjek/sleepingdogs-streaming-memory-v1/dxvk/source')
    assert manifest(previous_source) == build['inputs']['base']
    assert manifest(work / 'source') == build['source_files']
    for key, filename in (('builder_sha256', 'tools/build_dxvk_recycle.py'),
                          ('patch_sha256', 'tools/sleepingdogs_dxvk_recycle.py'),
                          ('helper_sha256', 'src/sd_dxvk_recycle.inc')):
        assert build['inputs'][key] == sha(ROOT / filename), filename
    changed_source = {n:h for n,h in build['source_files'].items() if build['inputs']['base'].get(n) != h}
    assert changed_source == build['changed'] and set(changed_source) == set(FILES)
    with tempfile.TemporaryDirectory() as temp:
        source = Path(temp)
        for name in FILES:
            if name not in build['inputs']['base']: continue
            target = source / name; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(previous_source / name, target)
        apply(source)
        for name in FILES: assert sha(source / name) == changed_source[name], name
    checks = {}
    for name in ('recycle-host-check', 'recycle-binary-check'):
        check = json.loads((ROOT / 'reports' / (name + '.json')).read_text())
        assert check['status'] == 'PASS'
        for filename,digest in check['sources'].items(): assert sha(ROOT / filename) == digest, filename
        checks[name] = check
    host = checks['recycle-host-check']; binary = checks['recycle-binary-check']
    assert host['helper_sha256'] == build['inputs']['helper_sha256']
    for name,digest in host['results']['candidate']['compiled_sources'].items():
        assert build['source_files'][name] == digest
    for name,digest in host['results']['baseline']['compiled_sources'].items():
        assert build['inputs']['base'][name] == digest
    assert binary['dll_sha256'] == staged['files']['d3d11.dll']['sha256']
    prior = ROOT / 'dist/sleepingdogs-fex-scene-memory-fix.zip'
    assert sha(prior) == PRIOR_SHA
    with zipfile.ZipFile(prior) as z:
        assert z.testzip() is None
        old = {n:z.read(n) for n in z.namelist() if n not in ('README.txt', 'SHA256SUMS.txt')}
    entries = dict(old); changed = set(); managed = set(); interface_report = {}
    current = release_files()['dxvk-3.1.1']
    for name,data in current.items():
        digest = hashlib.sha256(data).hexdigest()
        assert digest == staged['files'][name]['sha256'] == build['files'][name]['sha256']
        raw = (out / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == build['files'][name]['raw_sha256']
        assert executable_sections(raw) == executable_sections(data), name
        assert interfaces(data) == interfaces(old[PREFIX + 'drive_c/SleepingDogs/' + name]), name
        interface_report[name] = {'sha256':digest, 'imports_exports_unchanged':True,
                                  'stripped_executable_sections_identical':True}
        targets = ['launcher/renderers/dxvk-3.1.1/' + name, 'drive_c/SleepingDogs/' + name]
        if name == 'd3d9.dll': targets.append('drive_c/dxvk/d3d9.dll')
        for relative in targets:
            key = PREFIX + relative; assert key in old
            entries[key] = data; changed.add(key); managed.add(key)
    assert len(managed) == 7
    key = PREFIX + 'launcher/dxvk-releases.json'; receipts = json.loads(old[key])
    release = effective_release('dxvk-3.1.1')
    dlls = {n:m['sha256'] for n,m in staged['files'].items()}
    receipts['dxvk-3.1.1'] = {'url':release['url'], 'archive_sha256':release['sha256'],
                             'dlls':dlls, 'patch':staged}
    entries[key] = encode(receipts); changed.add(key)
    key = PREFIX + 'launcher/dxvk-memory-fix.json'; entries[key] = encode(staged); changed.add(key)
    for name in ('streaming-memory-fix', 'gpu-pressure-fix'):
        key = PREFIX + 'launcher/' + name + '.json'; receipt = json.loads(old[key])
        assert receipt['nro_sha256'] == NRO_SHA
        receipt['dxvk_dlls'] = dlls; entries[key] = encode(receipt); changed.add(key)
    entries[PREFIX + 'launcher/buffer-reuse-fix.json'] = encode({
        'build':'sleepingdogs-buffer-reuse-v1', 'dxvk_dlls':dlls, 'max_idle_bytes':16777216,
        'max_idle_count':4, 'retired_only':True, 'hardware_tested':False})
    for relative,digest in (('sleepingdogs-fex.nro', NRO_SHA),
                            ('drive_c/windows/system32/libwow64fex.dll', FEX_SHA)):
        assert entries[PREFIX + relative] == old[PREFIX + relative]
        assert hashlib.sha256(entries[PREFIX + relative]).hexdigest() == digest
    fw = json.loads(old['forwarder/build.json']); assert fw['sha256'] == FW_SHA
    assert hashlib.sha256(entries['forwarder/' + fw['nsp']]).hexdigest() == FW_SHA
    entries['README.txt'] = '''Sleeping Dogs FEXTendo - retired buffer reuse v1

1. Tutup game/FEXTendo sepenuhnya dari HOME.
2. Salin SELURUH folder switch dari ZIP ini ke root SD PALING AKHIR, timpa file
   yang diminta. DLL di drive_c dan launcher harus ikut diperbarui bersama.
3. NSP GPU-budget yang sekarang tetap dipakai: TIDAK perlu install ulang.
   Untuk instalasi dari basis lama, tersedia NSP yang sama di folder forwarder.
4. Pilih DXVK 3.1.1 > Launch Debug, lalu New Game sampai adegan 3D.

Penanda versi: [SD-DXVK-RECYCLE] v1 retired-only exact-size-type max_idle_mib=16
Penanda saat buffer benar-benar terpakai ulang: [SD-DXVK-RECYCLE] event=reuse

Log SS/09 masih gagal mengalokasikan buffer mapped 5 MiB, kemudian game
menulis ke pointer kosong. Patch menyimpan sementara buffer besar yang sudah
selesai dipakai untuk ukuran/tipe sama: maksimal 16 MiB, empat buffer idle.
Cache dilepas saat jalur pemulihan alokasi membutuhkan memori. Buffer yang
masih aktif tidak dipakai ulang dan ukuran resource game tidak dipotong.

NRO/FEX tetap pasangan scene-memory dua compiler. FEX Fastest tetap aktif.
Paket mencakup patch terdahulu. Data game, save, dan pilihan pengguna tidak
disertakan atau ditimpa. Batas memori proses tetap berlaku.

Uji host dan instruksi DLL lulus. Gameplay di Switch belum diverifikasi.
Jika masih crash, kirim fex-runtime.log dan crash.log dari percobaan terbaru.
Rollback: sleepingdogs-fex-buffer-reuse-rollback.zip. Tutup dari HOME lalu
salin seluruh switch; mengembalikan set DXVK sdstream1, dengan NRO/FEX sama.
'''.encode()
    folder = 'source/buffer-reuse-fix/'
    sources = ('src/sd_dxvk_recycle.inc', 'tools/sleepingdogs_dxvk_recycle.py',
        'tools/build_dxvk_recycle.py', 'tools/stage_dxvk_recycle.py', 'tools/package_buffer_reuse.py',
        'tools/analyze_buffer_reuse.py', 'tools/build_dxvk_memory.py', 'tools/dxvk_runtime.py',
        'tools/build_launcher.py', 'tools/verify_package.py', 'tools/port_common.py',
        'tests/recycle_dxvk.cpp', 'tests/check_recycle_host.py', 'tests/recycle_layout.cpp',
        'tests/build_recycle_layout.py', 'tests/check_recycle_binary.py',
        'tests/check_dxvk_map_binary.py', 'tests/check_wow64_context_binary.py',
        'tests/check_buffer_reuse_package.py', 'tests/check_buffer_reuse_launcher.py',
        'tests/check_streaming_launcher.py', 'tests/check_renderer_package.py',
        'vendor/f1-tools/check_renderer_package.py', 'docs/buffer-reuse-fix.md',
        'reports/buffer-reuse-analysis.json', 'vendor/dxvk/dxvk-3.1.1-sdrecycle1.json',
        'vendor/dxvk/DXVK-LICENSE', 'LICENSE')
    for name in sources: entries[folder + name] = (ROOT / name).read_bytes()
    for name,check in checks.items(): entries[folder + 'reports/' + name + '.json'] = encode(check)
    for name in ('build.json','staged.json'): entries[folder + name] = (out / name).read_bytes()
    entries[folder + 'local/recycle-layout.json'] = (ROOT / 'local/recycle-layout.json').read_bytes()
    for name in FILES:
        entries[folder + 'dxvk/' + name] = (work / 'source' / name).read_bytes()
        if name in build['inputs']['base']:
            entries[folder + 'dxvk-base/' + name] = (previous_source / name).read_bytes()
    for name,data in old.items():
        if name not in changed: assert entries[name] == data, name
    for name in entries:
        if '/drive_c/SleepingDogs/' in name: assert name in managed, name
        if name.lower().endswith('.nsp'): assert name == 'forwarder/' + fw['nsp'] and entries[name] == old[name]
        assert not name.lower().endswith(('.log','.keys','.exe','.big','.bix'))
        assert Path(name).name not in {'configuration.ini','fex-mode.txt','UserOptions.dat','selected.txt','renderer-choice.txt'}
    rollback = {name:old[name] for name in changed}
    rollback[PREFIX + 'launcher/buffer-reuse-fix.json'] = encode({'rolled_back':True})
    rollback['README.txt'] = b'Close FEXTendo from HOME and copy the entire switch folder. Restores the previous sdstream1 DXVK set and receipts. The two-compiler NRO/FEX pair, Fastest and current forwarder remain unchanged.\n'
    report = archive(ROOT / 'dist/sleepingdogs-fex-buffer-reuse-fix.zip', entries)
    report['rollback'] = archive(ROOT / 'dist/sleepingdogs-fex-buffer-reuse-rollback.zip', rollback)
    report.update(status='PASS', source_reconstruction='PASS', prior_payloads_preserved=True,
        managed_dll_copies=len(managed), interfaces=interface_report, nro_sha256=NRO_SHA,
        fex_sha256=FEX_SHA, forwarder_unchanged=FW_SHA, original_game_excluded=True, hardware_tested=False)
    write_json(ROOT / 'reports/buffer-reuse-package.json', report)
    print(json.dumps({k:report[k] for k in ('path','sha256','bytes','files')}))


if __name__ == '__main__': main()
