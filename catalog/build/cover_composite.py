"""Cover product composite: the Rev. C composite (assets/pages/p01_img44.png) with
its outdated PRS (the bottom part, below 56 % of the height) cleared and the
current PRS-2500B render (assets/prs-2500b.png) placed there.

Writes assets/pages/p01_products.png. Run from anywhere:
  python3 build/cover_composite.py
Same logic as the former patch_cover() in build/build.py.
"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "assets" / "pages" / "p01_img44.png"
PRS = ROOT / "assets" / "prs-2500b.png"
OUT = ROOT / "assets" / "pages" / "p01_products.png"


def compose() -> Path:
    comp = Image.open(SRC).convert("RGBA")
    W, H = comp.size
    cut = int(H * 0.56)
    comp.paste(Image.new("RGBA", (W, H - cut), (0, 0, 0, 0)), (0, cut))
    new = Image.open(PRS).convert("RGBA")
    scale = (H - cut - 24) / new.height
    new = new.resize((int(new.width * scale), int(new.height * scale)), Image.LANCZOS)
    comp.alpha_composite(new, ((W - new.width) // 2 + 60, cut + 8))
    comp.save(OUT, "PNG")
    return OUT


if __name__ == "__main__":
    print("wrote", compose())
