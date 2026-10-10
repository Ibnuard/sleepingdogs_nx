"""Convert the supplied game's embedded icon and reuse FEXTendo UI resources."""
from pathlib import Path
import io
import json
import math
import shutil
import struct

import pefile
from PIL import Image, ImageDraw, ImageFilter, ImageOps
from port_common import ROOT, BASE, DEFAULT_GAME, GAME_EXE, sha, write_json


def game_icon(exe):
    with pefile.PE(str(exe)) as pe:
        icons, groups = {}, []
        for kind in pe.DIRECTORY_ENTRY_RESOURCE.entries:
            if kind.id not in (3, 14):
                continue
            for item in kind.directory.entries:
                leaf = item.directory.entries[0].data.struct
                payload = pe.get_data(leaf.OffsetToData, leaf.Size)
                if kind.id == 3:
                    icons[item.id] = payload
                else:
                    groups.append(payload)
        if not groups:
            raise RuntimeError('The supplied HKShip.exe has no embedded icon')
        group = groups[0]
        count = struct.unpack_from('<H', group, 4)[0]
        entries, pixels = [], bytearray()
        offset = 6 + count * 16
        for i in range(count):
            item = group[6 + i * 14:20 + i * 14]
            resource_id = struct.unpack_from('<H', item, 12)[0]
            image = icons[resource_id]
            entries.append(item[:8] + struct.pack('<II', len(image), offset + len(pixels)))
            pixels.extend(image)
        ico = group[:6] + b''.join(entries) + pixels
    (ROOT / 'assets/sleepingdogs.ico').write_bytes(ico)
    image = Image.open(io.BytesIO(ico))
    best = max(image.ico.sizes(), key=lambda size: size[0] * size[1])
    return image.ico.getimage(best).convert('RGBA')


def build():
    out = ROOT / 'dist/launcher'
    out.mkdir(parents=True, exist_ok=True)
    reused = {}
    for src in (BASE / 'launcher').iterdir():
        if src.is_file() and src.suffix in ('.rgba', '.bin', '.jpg'):
            shutil.copy2(src, out / src.name)
            reused[src.name] = sha(src)
    # Original neutral dusk backdrop. UI text/cards are drawn by the native
    # launcher, not baked into an illustration or copied from the other game.
    bg = Image.new('RGBA', (1280, 720))
    draw = ImageDraw.Draw(bg)
    for y in range(720):
        t = y / 719
        draw.line((0, y, 1280, y), fill=(int(17-9*t), int(23-9*t), int(38-17*t), 255))
    for i in range(30):
        x = i * 47 - 24
        top = 150 + (i * 67 % 200)
        draw.rectangle((x, top, x + 36, 720), fill=(13, 23, 35, 255))
        for yy in range(top + 12, 700, 26):
            for xx in (x+8, x+23):
                if (i + yy // 26 + xx // 8) % 4:
                    draw.rectangle((xx, yy, xx+3, yy+6), fill=(55, 47, 50, 255))
    (out / 'background.rgba').write_bytes(bg.tobytes())
    (out / 'blur.rgba').write_bytes(bg.filter(ImageFilter.GaussianBlur(18)).tobytes())
    bg.convert('RGB').save(ROOT / 'assets/background.png')
    icon = ImageOps.fit(game_icon(DEFAULT_GAME / GAME_EXE), (256, 256), method=Image.Resampling.LANCZOS)
    icon.save(ROOT / 'assets/icon.png')
    (out / 'icon.rgba').write_bytes(icon.tobytes())
    icon.convert('RGB').save(out / 'nro-icon.jpg', quality=95, subsampling=0)
    reused = {name: digest for name, digest in reused.items()
              if name not in ('background.rgba', 'blur.rgba', 'icon.rgba', 'nro-icon.jpg')}
    write_json(out / 'assets.json', {'format': 4, 'source': 'FEXTendo UI + supplied HKShip.exe icon',
               'game_executable_sha256': sha(DEFAULT_GAME / GAME_EXE), 'reused': reused,
               'files': {p.name: sha(p) for p in sorted(out.iterdir()) if p.suffix in ('.rgba', '.bin', '.jpg')}})
    print(json.dumps({'assets': str(out), 'count': len(list(out.iterdir()))}))


if __name__ == '__main__':
    build()
