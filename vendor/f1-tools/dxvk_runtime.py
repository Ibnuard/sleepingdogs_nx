"""Stage complete x86 DXVK sets from pinned upstream release archives."""
from pathlib import Path
import hashlib
import json
import tarfile

ROOT = Path(__file__).resolve().parents[1]
RELEASES = {
    "dxvk-3.1.1": {
        "archive": ROOT.parent / "pes13-nx/local/perf10/dxvk-3.1.1.tar.gz",
        "sha256": "40565b4a724aadc4433fa4e010b4b23916d9b1f1baeee64e17186db94f54e608",
        "prefix": "dxvk-3.1.1/x32/",
        "d3d9_sha256": "265888c31ca78dffa290c39cb7e50bfb02762590e41927906e46fb32f01497fa",
        "url": "https://github.com/doitsujin/dxvk/releases/download/v3.1.1/dxvk-3.1.1.tar.gz",
    },
    "dxvk-2.7.1-async": {
        "archive": ROOT / "vendor/dxvk/dxvk-gplasync-v2.7.1-1.tar.gz",
        "sha256": "590050b88be7b156cf641abe762e1ad47ebbe828f7f0edb2970aa4716ee3af6d",
        "prefix": "dxvk-gplasync-v2.7.1-1/x32/",
        "d3d9_sha256": "a2cd6841e102f37189527c118ec416fa5071ac4d3120762973d9a0c6c5fd067e",
        "url": "https://gitlab.com/Ph42oN/dxvk-gplasync/-/raw/main/releases/dxvk-gplasync-v2.7.1-1.tar.gz",
    },
}
DLLS = ("d3d9.dll", "d3d11.dll", "dxgi.dll")


def effective_release(renderer):
    release = dict(RELEASES[renderer])
    if renderer == 'dxvk-3.1.1':
        # The local F1 build is distinct from the original upstream archive.
        # Bind its receipt to both the pinned source and the reviewed patch.
        from dxvk_compact_chunks import COMMIT
        receipt = json.loads((ROOT/'vendor/dxvk/dxvk-3.1.1-f1mem2.json').read_text())
        assert receipt['source']['commit'] == COMMIT
        assert receipt['source']['patch_sha256'] == hashlib.sha256((ROOT/'tools/dxvk_compact_chunks.py').read_bytes()).hexdigest()
        assert receipt['source']['base_patch_sha256'] == hashlib.sha256((ROOT/'tools/dxvk_small_chunks.py').read_bytes()).hexdigest()
        assert receipt['upstream_archive_sha256'] == release['sha256']
        release.update(archive=ROOT/'vendor/dxvk/dxvk-3.1.1-f1mem2.tar.gz',
                       sha256=receipt['archive_sha256'], prefix='dxvk-3.1.1-f1mem2/x32/',
                       d3d9_sha256=receipt['files']['d3d9.dll']['sha256'],
                       url='https://github.com/doitsujin/dxvk/tree/'+COMMIT,
                       patch=receipt)
    return release


def write_lf(path, text):
    """Keep runtime text byte-identical when packaging on Windows or Linux."""
    path.write_bytes(text.replace('\r\n', '\n').encode('utf-8'))


def release_files():
    result = {}
    for renderer in RELEASES:
        release = effective_release(renderer)
        archive = release["archive"]
        if hashlib.sha256(archive.read_bytes()).hexdigest() != release["sha256"]:
            raise ValueError(f"DXVK archive hash mismatch: {archive}")
        with tarfile.open(archive, "r:gz") as tar:
            files = {name: tar.extractfile(release["prefix"] + name).read() for name in DLLS}
        if hashlib.sha256(files["d3d9.dll"]).hexdigest() != release["d3d9_sha256"]:
            raise ValueError(f"Renderer does not match its pinned D3D9 build: {renderer}")
        if 'patch' in release:
            assert all(hashlib.sha256(data).hexdigest() == release['patch']['files'][name]['sha256']
                       for name,data in files.items())
        result[renderer] = files
    return result


def stage_renderers(prefix, config):
    """Only managed DLLs/configs are written; installed user choices are retained."""
    receipt = {}
    for renderer, files in release_files().items():
        release = effective_release(renderer)
        folder = prefix / "launcher/renderers" / renderer
        folder.mkdir(parents=True, exist_ok=True)
        for name, data in files.items():
            (folder / name).write_bytes(data)
        write_lf(folder / "dxvk.conf", config("balanced", renderer.endswith("async")))
        receipt[renderer] = {
            "url": release["url"], "archive_sha256": release["sha256"],
            "dlls": {name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
        }
        if 'patch' in release:
            receipt[renderer]['patch'] = release['patch']
    (prefix / "launcher/dxvk-releases.json").write_text(json.dumps(receipt, indent=2) + "\n")
    (prefix / "launcher/DXVK-LICENSE").write_bytes((ROOT / "vendor/dxvk/DXVK-LICENSE").read_bytes())
    return receipt
