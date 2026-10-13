"""GitHub release transport. Uses only the job-scoped GH_TOKEN via gh."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def gh(*args, data=None):
    command = ['gh', *args]
    if data is not None:
        command += ['--input', '-']
    result = subprocess.run(command, input=json.dumps(data) if data is not None else None,
                            text=True, capture_output=True, check=True)
    return json.loads(result.stdout) if result.stdout.strip() else None


def repository():
    repo = os.environ['GITHUB_REPOSITORY']
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        raise ValueError('Invalid GitHub repository')
    return repo


def merged_commit():
    """Use the immutable merged revision, never a later main HEAD or PR head."""
    if os.environ.get('GITHUB_EVENT_NAME') != 'pull_request_target':
        raise ValueError('Release requires a merged pull request to main')
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    pr = event.get('pull_request') or {}
    base = pr.get('base') or {}
    if (event.get('action') != 'closed' or pr.get('merged') is not True
            or base.get('ref') != 'main'
            or (base.get('repo') or {}).get('full_name') != repository()):
        raise ValueError('Release requires a merged pull request to main')
    commit = pr.get('merge_commit_sha', '')
    if not isinstance(commit, str) or not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('Missing or invalid merge commit')
    return commit


def version():
    commit = merged_commit()
    # Keep the runtime version visible; the revision distinguishes package runs.
    runtime = json.loads((ROOT / 'release/runtime-lock.json').read_text())['runtime_version']
    match = re.fullmatch(r'(\d+\.\d+\.\d+)(?:-p\d+)?', runtime)
    if not match:
        raise ValueError('Invalid runtime version')
    run = os.environ['GITHUB_RUN_NUMBER']
    if not run.isdecimal():
        raise ValueError('Invalid workflow run number')
    value = 'v' + match[1] + ('-r' + run if '-p' in runtime else '')
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        output.write('version=' + value + '\ncommit=' + commit + '\n')
    print(value)


def release_title(tag):
    match = re.fullmatch(r'v(\d+\.\d+\.\d+)(?:-r(\d+))?', tag)
    if not match:
        raise ValueError('Invalid production release identity')
    title = 'Sleeping Dogs FEXTendo ' + match[1]
    return title + (' (r' + match[2] + ')' if match[2] else '')


def fetch(output):
    lock = json.loads((ROOT / 'release/runtime-lock.json').read_text())
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*\.zip', lock['asset']):
        raise ValueError('Invalid runtime asset filename')
    if '\n' in str(output) or '\r' in str(output):
        raise ValueError('Invalid runtime output path')
    output.mkdir(parents=True, exist_ok=True)
    subprocess.run(['gh', 'release', 'download', lock['tag'], '--repo', repository(),
                    '--pattern', lock['asset'], '--dir', str(output)], check=True)
    if hashlib.sha256((output / lock['asset']).read_bytes()).hexdigest() != lock['sha256']:
        raise ValueError('Downloaded runtime differs from committed SHA256')
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as result:
            result.write('runtime_path=' + str(output / lock['asset']) + '\n')


def validate_assets(folder, tag, commit):
    from release_package import NSP, NRO, ROOT, validate_payload, sha
    import zipfile
    expected = {f'SleepingDogs-FEXTendo-{tag}-sd.zip', 'sleepingdogs-fex.nro', NSP, 'manifest.json'}
    sums = {}
    for line in (folder / 'SHA256SUMS').read_text().splitlines():
        digest, name = line.split('  ', 1)
        if name in sums or name not in expected or not re.fullmatch('[0-9a-f]{64}', digest):
            raise ValueError('Invalid release checksum entry')
        sums[name] = digest
    if set(sums) != expected or {p.name for p in folder.iterdir()} != expected | {'SHA256SUMS'}:
        raise ValueError('Release asset set differs from expected output')
    for name, digest in sums.items():
        if hashlib.sha256((folder / name).read_bytes()).hexdigest() != digest:
            raise ValueError('Release asset checksum mismatch: ' + name)
    manifest = json.loads((folder / 'manifest.json').read_text())
    if manifest['source_commit'] != commit or manifest['package_version'] != tag:
        raise ValueError('Artifact belongs to a different commit or release')
    # Recheck archive contents in the privileged publish job; a checksum list
    # alone would not establish that its payload passed the package allowlist.
    lock = json.loads((ROOT/'release/runtime-lock.json').read_text())
    with zipfile.ZipFile(folder/f'SleepingDogs-FEXTendo-{tag}-sd.zip') as archive:
        if len(archive.namelist()) != len(set(archive.namelist())):
            raise ValueError('Duplicate final archive member')
        contents = {n: archive.read(n) for n in archive.namelist()}
    if contents.pop('manifest.json') != (folder/'manifest.json').read_bytes():
        raise ValueError('Final embedded manifest differs')
    if {n: sha(d) for n,d in contents.items()} != manifest['files']:
        raise ValueError('Final payload differs from manifest')
    contents.pop('README.txt')
    validate_payload(contents,lock)
    if contents[NRO] != (folder/'sleepingdogs-fex.nro').read_bytes() or contents[NSP] != (folder/NSP).read_bytes():
        raise ValueError('Standalone binaries differ from SD package')
    return manifest


def publish(folder, tag, commit):
    title = release_title(tag)
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('Invalid production release identity')
    repo = repository()
    prefix = 'repos/' + repo
    manifest = validate_assets(folder, tag, commit)
    # A tag must always refer to the exact commit whose package was validated.
    refs = gh('api', prefix + '/git/matching-refs/tags/' + tag)
    refs = [r for r in refs if r['ref'] == 'refs/tags/' + tag]
    if refs:
        if refs[0]['object']['sha'] != commit or refs[0]['object']['type'] != 'commit':
            raise ValueError('Existing release tag targets a different commit')
    else:
        gh('api', prefix + '/git/refs', '--method', 'POST', data={'ref': 'refs/tags/' + tag, 'sha': commit})
    # Listing with pagination also distinguishes API/auth failures from a missing release.
    releases = gh('api', prefix + '/releases?per_page=100', '--paginate', '--slurp')
    release = next((r for page in releases for r in page if r['tag_name'] == tag), None)
    if release and not release['draft']:
        existing = {a['name']: a for a in release['assets']}
        if set(existing) != {p.name for p in folder.iterdir()}:
            raise ValueError('Published release has an unexpected asset set; refusing to overwrite')
        # Published assets are never replaced, even by a workflow rerun.
        for p in folder.iterdir():
            if existing[p.name].get('digest') != 'sha256:' + hashlib.sha256(p.read_bytes()).hexdigest():
                raise ValueError('Published asset differs from rerun: ' + p.name)
        print('Already published: ' + release['html_url'])
        return
    if not release:
        notes = gh('api', prefix + '/releases/generate-notes', '--method', 'POST',
                   data={'tag_name': tag, 'target_commitish': commit})
        notes_path=ROOT/'release/NOTES.md'
        changes=notes_path.read_text().strip()+'\n\n' if notes_path.is_file() else ''
        body = (changes+'Download **SleepingDogs-FEXTendo-' + tag + '-sd.zip** for the complete runtime. '
                'It includes the NRO, NSP forwarder, Wine/FEX/DXVK runtime, launcher assets, '
                'presets, matching modified source units and notices.\n\n'
                'Copy your own original x86 Sleeping Dogs game into '
                '`switch/sleepingdogs-fex/drive_c/SleepingDogs/`. '
                'Game data, saves, lossless.dll and proprietary LSFG shaders are excluded. '
                'The matching low-memory boot patch is required separately.\n\n'
                'Runtime: native DXVK, Light 720p, cached System Check, live keyboard, '
                'normal Play without diagnostic files, independent last played and optional Debug; NRO version '
                + manifest['runtime_version'] + '. Package validation is not a Switch hardware test. '
                'Saved LSFG preferences are retained. Standalone NRO/NSP assets are for existing installations.\n\n' + notes['body'])
        release = gh('api', prefix + '/releases', '--method', 'POST', data={
            'tag_name': tag, 'target_commitish': commit, 'name': title,
            'body': body, 'draft': True, 'prerelease': False})
    # Upload to a draft; a partial network failure can safely be resumed.
    subprocess.run(['gh', 'release', 'upload', tag, '--repo', repo, '--clobber',
                    *[str(p) for p in sorted(folder.iterdir())]], check=True)
    result = gh('api', prefix + '/releases/' + str(release['id']), '--method', 'PATCH',
                data={'draft': False, 'make_latest': 'true'})
    print('Published: ' + result['html_url'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('version')
    download = sub.add_parser('fetch')
    download.add_argument('--output', type=Path, required=True)
    release = sub.add_parser('publish')
    release.add_argument('--input', type=Path, required=True)
    release.add_argument('--tag', required=True)
    release.add_argument('--commit', required=True)
    args = parser.parse_args()
    if args.command == 'version':
        version()
    elif args.command == 'fetch':
        fetch(args.output)
    else:
        if merged_commit() != args.commit:
            raise ValueError('Publish commit differs from the merged pull request')
        publish(args.input, args.tag, args.commit)
