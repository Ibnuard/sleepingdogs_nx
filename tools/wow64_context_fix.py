"""Build the isolated Wine WoW64 context-query fix (LGPL-2.1-or-later)."""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess

from port_common import ROOT, PES, APPROVED, BASE, sha, write_json
from f1_overlay import replace_function
from wow64_dep_fix import apply as apply_dep

SIGNATURE = 'NTSTATUS WINAPI wow64_NtGetContextThread( UINT *args )'
ORIGINAL = '''NTSTATUS WINAPI wow64_NtGetContextThread( UINT *args )
{
    HANDLE handle = get_handle( &args );
    WOW64_CONTEXT *context = get_ptr( &args );
    NTSTATUS status;
    ULONG count;

    if (wow64info->CpuFlags & WOW64_CPUFLAGS_SOFTWARE) RtlWow64SuspendThread( handle, &count );
    status = RtlWow64GetThreadContext( handle, context );
    if (wow64info->CpuFlags & WOW64_CPUFLAGS_SOFTWARE) NtResumeThread( handle, &count );
    return status;
}'''
FIXED = '''NTSTATUS WINAPI wow64_NtGetContextThread( UINT *args )
{
    HANDLE handle = get_handle( &args );
    WOW64_CONTEXT *context = get_ptr( &args );
    NTSTATUS status;
    ULONG count;
    BOOL suspended = FALSE;

    if (wow64info->CpuFlags & WOW64_CPUFLAGS_SOFTWARE)
    {
        /* The calling guest is already stopped at its WoW64 syscall boundary.
         * Suspending it here prevents this call from ever reaching the resume.
         * Resolve real handles to self too, and use the native self-context path. */
        if (handle != GetCurrentThread())
        {
            THREAD_BASIC_INFORMATION info;
            status = NtQueryInformationThread( handle, ThreadBasicInformation,
                                               &info, sizeof(info), NULL );
            if (status) return status;
            if (info.ClientId.UniqueThread == NtCurrentTeb()->ClientId.UniqueThread &&
                info.ClientId.UniqueProcess == NtCurrentTeb()->ClientId.UniqueProcess)
                handle = GetCurrentThread();
        }
        if (handle != GetCurrentThread())
        {
            status = RtlWow64SuspendThread( handle, &count );
            if (status) return status;
            suspended = TRUE;
        }
    }
    status = RtlWow64GetThreadContext( handle, context );
    /* Do not consume another caller's suspend count after a failed suspend. */
    if (suspended) NtResumeThread( handle, &count );
    return status;
}'''


def patched(source):
    if source.count(ORIGINAL) != 1:
        raise ValueError('Unexpected WoW64 context implementation; inspect before patching')
    return replace_function(source, SIGNATURE, FIXED)


def build(work, dependencies, jobs=4):
    work = Path(work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    archive = PES / 'local/production-input-fix/wine-source.tar.gz'
    overlay = APPROVED / 'source/generated/wine/pe-source'
    toolchain = Path(dependencies) / 'toolchains/llvm-mingw-20260505-ucrt-ubuntu-22.04-x86_64'
    compiler = toolchain / 'bin/aarch64-w64-mingw32-clang'
    if not compiler.is_file():
        raise ValueError(f'Missing compiler: {compiler}')
    identity = {'archive_sha256': sha(archive), 'patch_sha256': sha(Path(__file__)),
                'dep_bridge': {n: sha(ROOT / n) for n in ('tools/wow64_dep_fix.py', 'src/sd_wow64_dep.inc')},
                'overlay': {p.relative_to(overlay).as_posix(): sha(p)
                            for p in sorted(overlay.rglob('*')) if p.is_file()},
                'toolchain': str(toolchain.resolve())}
    manifest = json.loads((APPROVED / 'runtime-manifest.json').read_text())
    # Pin every reused PE overlay to the approved release, including callback fixes.
    manifest_files = manifest.get('files', manifest)
    for relative, digest in identity['overlay'].items():
        expected = manifest_files['source/generated/wine/pe-source/' + relative]
        if isinstance(expected, dict):
            expected = expected['sha256']
        if digest != expected:
            raise ValueError(f'Approved PE source changed: {relative}')
    source = work / 'source'
    stamp = work / 'prepared.json'
    if stamp.exists():
        if json.loads(stamp.read_text()) != identity:
            raise ValueError('WoW64 build inputs changed; use a new work directory')
    else:
        if source.exists():
            raise ValueError(f'Untracked source directory: {source}')
        source.mkdir()
        subprocess.run(['tar', '-xzf', str(archive), '--strip-components=1', '-C', str(source)], check=True)
        shutil.copytree(overlay, source, dirs_exist_ok=True)
        syscall = source / 'dlls/wow64/syscall.c'
        syscall.write_text(patched(syscall.read_text()), encoding='utf-8', newline='\n')
        apply_dep(source)
        write_json(stamp, identity)
    pe = work / 'build'
    pe.mkdir(exist_ok=True)
    temp = work / 'tmp'
    temp.mkdir(exist_ok=True)
    env = dict(os.environ, PATH=str(toolchain / 'bin') + os.pathsep + os.environ['PATH'], TMPDIR=str(temp))
    target = 'dlls/wow64/aarch64-windows/wow64.dll'
    print(f'Building WoW64 context fix; log: {work / "build.log"}', flush=True)
    with (work / 'build.log').open('a') as log:
        if not (pe / 'Makefile').exists():
            subprocess.run([str(source / 'configure'), '-C', '--enable-archs=aarch64,i386',
                            '--enable-winebox64=aarch64', '--without-x', '--without-freetype'],
                           cwd=pe, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        subprocess.run(['make', '-C', str(pe), '-j', str(jobs), target],
                       env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    dll = pe / target
    receipt = {'fix': 'sleepingdogs-wow64-self-context-v1', 'inputs': identity,
               'original_dll_sha256': sha(BASE / 'drive_c/windows/system32/wow64.dll'),
               'dll_sha256': sha(dll), 'syscall_source_sha256': sha(source / 'dlls/wow64/syscall.c'),
               'dep_notification': 'initial policy and successful self-process changes',
               'compiler': subprocess.check_output([str(compiler), '--version'], text=True).splitlines()[0],
               'hardware_tested': False}
    write_json(work / 'build.json', receipt)
    return dll, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=Path.home() / 'sleepingdogs-wow64-context-v1')
    parser.add_argument('--dependencies', type=Path, default=Path('/home/blekjek/pes13-build'))
    parser.add_argument('--jobs', type=int, default=4)
    args = parser.parse_args()
    dll, receipt = build(args.work, args.dependencies, args.jobs)
    output = ROOT / 'dist/wow64-context-fix'
    output.mkdir(parents=True, exist_ok=True)
    shutil.copy2(dll, output / 'wow64.dll')
    shutil.copy2(Path(args.work) / 'source/dlls/wow64/syscall.c', output / 'syscall.c')
    write_json(output / 'build.json', receipt)
    print(json.dumps({'dll': str(output / 'wow64.dll'), 'sha256': receipt['dll_sha256']}))


if __name__ == '__main__':
    main()
