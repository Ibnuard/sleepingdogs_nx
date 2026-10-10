"""Build original F1 launcher art in the FEXTendo asset format."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
PES = ROOT.parent / "pes13-nx"


def load_base_builder():
    path = PES / "tools/build-fextendo-assets.py"
    spec = importlib.util.spec_from_file_location("fextendo_assets", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def text_art(size, title, subtitle, color=(255, 255, 255)):
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    font_file = PES / "assets/fonts/Inter/Inter.ttf"
    large = ImageFont.truetype(str(font_file), round(size[1] * 0.45))
    small = ImageFont.truetype(str(font_file), round(size[1] * 0.17))
    draw.text((size[0] // 2, size[1] * 0.43), title, font=large,
              anchor="mm", fill=color, stroke_width=1)
    draw.text((size[0] // 2, size[1] * 0.78), subtitle, font=small,
              anchor="mm", fill=(211, 221, 231))
    return im


def build(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    load_base_builder().build(out)
    background = ImageOps.fit(Image.open(ROOT / "assets/race-background.png").convert("RGBA"),
                              (1280, 720), method=Image.Resampling.LANCZOS)
    (out / "background.rgba").write_bytes(background.tobytes())
    (out / "blur.rgba").write_bytes(background.filter(ImageFilter.GaussianBlur(18)).tobytes())
    icon = ImageOps.fit(background, (256, 256), method=Image.Resampling.LANCZOS)
    icon.alpha_composite(Image.new("RGBA", (256, 256), (3, 9, 21, 95)))
    icon.alpha_composite(text_art((256, 256), "F1", "2013"))
    (out / "icon.rgba").write_bytes(icon.tobytes())
    icon.convert("RGB").save(out / "nro-icon.jpg", quality=95, subsampling=0)
    # Preserve the original FEXTendo logo and wordmark produced by the PES
    # asset builder.  F1 identity stays on the game tile and NRO icon.
    manifest = json.loads((out / "assets.json").read_text())
    manifest["f1_art_source"] = hashlib.sha256((ROOT / "assets/race-background.png").read_bytes()).hexdigest()
    manifest["files"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in sorted(out.iterdir()) if p.suffix in (".rgba", ".bin", ".jpg")}
    (out / "assets.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    build(parser.parse_args().output)
