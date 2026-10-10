"""Bind the local ready tree to the compiled game and packaged runtime receipts."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from port_common import APP_ID, GAME_DIR, GAME_EXE, DEFAULT_GAME, sha, write_json
from verify_package import verify

ready = ROOT / f'dist/{APP_ID}-ready'
prefix = ready / 'switch' / APP_ID
report = json.loads((ready / 'build-report.json').read_text())
local = json.loads((ready / 'local-game-report.json').read_text())
game = prefix / 'drive_c' / GAME_DIR
assert sha(game / GAME_EXE) == report['game']['sha256'] == sha(DEFAULT_GAME / GAME_EXE)
assert sha(prefix / f'{APP_ID}.nro') == report['nro_sha256']
checked = 0
for relative, digest in report['files'].items():
    if relative.endswith('/COPY-YOUR-GAME-HERE.txt'):
        continue
    assert sha(ready / relative) == digest, relative
    checked += 1
for relative, info in local['files'].items():
    path = game / relative
    assert path.is_file() and path.stat().st_size == info['bytes'], relative
    if 'sha256' in info:
        assert sha(path) == info['sha256'] == sha(DEFAULT_GAME / relative), relative
source_files = {str(p.relative_to(DEFAULT_GAME)) for p in DEFAULT_GAME.rglob('*') if p.is_file()}
assert source_files == set(local['files']) | set(local['skipped_conflicts'])
package = verify(prefix)
package['runtime_files_sha256_verified'] = checked
package['game_files_size_verified'] = len(local['files'])
package['game_exe_matches_compiled_reservation'] = True
package['game_source_critical_files_unchanged'] = True
package['game_bytes'] = local['total_game_bytes']
write_json(ROOT / 'reports/package-check.json', package)
print(json.dumps({k: package[k] for k in ('status','hardware_tested','runtime_files_sha256_verified',
                  'game_files_size_verified','game_exe_matches_compiled_reservation','game_bytes')}, indent=2))
