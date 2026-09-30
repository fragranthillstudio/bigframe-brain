"""Build the Rev. C catalog with the corrected PRS pages.

Pipeline
  1. data/models.json is the single source of truth for every figure.
  2. Pages 2, 13, 14, 17 and 20 are rendered from src/templates with Jinja2
     and printed to PDF with headless Chromium (Playwright) at the catalog's
     page size, 612 × 858.96 pt.
  3. The cover (page 1) keeps its typography; only the PRS render in the
     product composite is swapped for the new one.
  4. The rendered pages replace their counterparts in the Rev. C source PDF.

Run:  python3 build/build.py            (from the catalog/ directory)
"""
from __future__ import annotations

import io
import json
import os
import sys
from pathlib import Path

import pymupdf
from jinja2 import Environment, FileSystemLoader
from PIL import Image
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
import figures  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "output"
RENDER = OUT / "pages"
SOURCE_PDF = ROOT / "source" / "Bigframe_Product_Catalog_2026_EN_RevC.pdf"
FINAL_PDF = OUT / "Bigframe_Product_Catalog_2026_EN_RevC_PRS-update.pdf"

PAGE_W, PAGE_H = "8.5in", "11.93in"  # 612 × 858.96 pt
CHROMIUM = os.environ.get("CHROMIUM_PATH", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

REBUILT = [2, 13, 14, 17, 20]


def load_data() -> dict:
    return json.loads((ROOT / "data" / "models.json").read_text())


def render_html(data: dict) -> dict[int, Path]:
    env = Environment(loader=FileSystemLoader(SRC / "templates"), autoescape=False)
    prs = data["prs"]
    img = "../../assets/prs-2500b.png"
    ctx = dict(
        catalog=data["catalog"], prs=prs, models=data["models"], series_groups=data["series_groups"],
        series_cards=data["series_cards"], compare=data["large_scene_compare"],
        qr_svg=figures.qr_svg(data["catalog"]["qr_url"]),
        use_case_svg=figures.use_case_svg(prs, img),
        fov_scene_svg=figures.fov_scene_svg(prs, img),
        measuring_face_svg=figures.measuring_face_svg(prs),
        measuring_face_small_svg=figures.measuring_face_svg(prs, W=198, H=66),
        end_view_svg=figures.end_view_svg(prs),
        fov_wd_chart_svg=figures.fov_wd_chart_svg(prs),
        range_scatter_svg=figures.range_scatter_svg(data["models"], data["series_groups"]),
    )
    RENDER.mkdir(parents=True, exist_ok=True)
    html_dir = SRC / "rendered"
    html_dir.mkdir(exist_ok=True)
    paths = {}
    for n in REBUILT:
        tpl = env.get_template(f"p{n:02d}.html")
        html = tpl.render(page_number=n, **ctx)
        p = html_dir / f"p{n:02d}.html"
        p.write_text(html)
        paths[n] = p
    return paths


def print_pdfs(html_paths: dict[int, Path]) -> dict[int, Path]:
    pdfs = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROMIUM)
        page = browser.new_page()
        for n, hp in html_paths.items():
            page.goto(hp.resolve().as_uri())
            page.wait_for_load_state("networkidle")
            page.evaluate("document.fonts.ready")
            out = RENDER / f"p{n:02d}.pdf"
            page.pdf(path=str(out), width=PAGE_W, height=PAGE_H, print_background=True, prefer_css_page_size=True,
                     margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
            pdfs[n] = out
        browser.close()
    return pdfs


def patch_cover(doc: pymupdf.Document) -> None:
    """Swap the PRS in the cover composite (image xref 44) for the new render."""
    page = doc[0]
    xref = next(i["xref"] for i in page.get_image_info(xrefs=True) if i["xref"])
    pix = pymupdf.Pixmap(doc, xref)
    smask = doc.xref_get_key(xref, "SMask")
    if smask[0] == "xref":
        pix = pymupdf.Pixmap(pix, pymupdf.Pixmap(doc, int(smask[1].split()[0])))
    comp = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGBA")
    W, H = comp.size  # 2551 × 1559 in Rev. C
    # clear the old PRS: everything below the row of VR/VRD cameras
    cut = int(H * 0.56)
    clear = Image.new("RGBA", (W, H - cut), (0, 0, 0, 0))
    comp.paste(clear, (0, cut))
    new = Image.open(ROOT / "assets" / "prs-2500b.png").convert("RGBA")
    target_h = H - cut - 24
    scale = target_h / new.height
    new = new.resize((int(new.width * scale), int(new.height * scale)), Image.LANCZOS)
    x = (W - new.width) // 2 + 60
    comp.alpha_composite(new, (x, cut + 8))
    buf = io.BytesIO()
    comp.save(buf, "PNG")
    page.replace_image(xref, stream=buf.getvalue())


def render_scene_png(data: dict) -> Path:
    """The depalletizing tile on page 4: the use-case scene on the dark ground, 1087 × 591 px."""
    svg = figures.use_case_svg(data["prs"], "../../assets/prs-2500b.png", W=283, H=154)
    html = (SRC / "rendered" / "scene-p04.html")
    html.write_text('<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="../catalog.css">'
                    '<body style="background:#111827;width:283pt;height:154pt;overflow:hidden">'
                    '<div class="fig-label" style="position:absolute;left:8.5pt;top:8pt">Depalletizing · illustration</div>'
                    + svg + '</body>')
    out = RENDER / "scene-p04.png"
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROMIUM)
        page = browser.new_page(viewport={"width": 378, "height": 206}, device_scale_factor=3)
        page.goto(html.resolve().as_uri())
        page.wait_for_load_state("networkidle")
        page.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": 377.3, "height": 205.3})
        browser.close()
    return out


def patch_page4(doc: pymupdf.Document, data: dict, scene_png: Path) -> None:
    """Applications page: swap the depalletizing illustration and the model code in its caption."""
    page = doc[3]
    infos = sorted((i for i in page.get_image_info(xrefs=True) if i["xref"]), key=lambda i: (i["bbox"][1], i["bbox"][0]))
    tile = infos[1]  # second tile of the first row
    page.replace_image(tile["xref"], filename=str(scene_png))
    old, new = "PRS-2500 · VR-2300B", f"{data['prs']['model']} · VR-2300B"
    for r in page.search_for(old):
        page.add_redact_annot(r, fill=(1, 1, 1))
        page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE)
        page.insert_text((r.x0, r.y1 - 0.22 * 6.6), new, fontsize=6.6, color=(0x2d / 255, 0x37 / 255, 0x48 / 255),
                         fontfile=str(ROOT / "assets" / "fonts" / "IBMPlexMono-400-normal.ttf"), fontname="PlexMono")


def assemble(pdfs: dict[int, Path], data: dict) -> Path:
    doc = pymupdf.open(SOURCE_PDF)
    patch_cover(doc)
    patch_page4(doc, data, render_scene_png(data))
    for n, p in pdfs.items():
        new = pymupdf.open(p)
        doc.delete_page(n - 1)
        doc.insert_pdf(new, from_page=0, to_page=0, start_at=n - 1)
    doc.set_metadata({**doc.metadata, "title": "Bigframe Product Catalog 2026 — EN — Rev. C (PRS update)"})
    OUT.mkdir(exist_ok=True)
    doc.save(FINAL_PDF, garbage=4, deflate=True)
    return FINAL_PDF


def main() -> None:
    data = load_data()
    html = render_html(data)
    pdfs = print_pdfs(html)
    final = assemble(pdfs, data)
    print("built", final, f"({final.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
