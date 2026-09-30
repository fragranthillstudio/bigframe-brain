"""Build the Bigframe Product Catalog 2026 from code, in any language.

Pipeline
  1. data/models.json is the single source of truth for every figure.
  2. data/i18n/<lang>.json holds every string of every page, keyed by page
     ("common", "p01" … "p24").
  3. Each page with a template in src/templates/pNN.html is rendered with
     Jinja2 and printed to PDF with headless Chromium at the catalog's page
     size, 612 × 858.96 pt (8.5 × 11.93 in).
  4. Pages without a template fall back to the Rev. C source PDF (English
     only) with in-place patches, so the build always yields 24 pages.

Run (from catalog/):
  python3 build/build.py                 # English
  python3 build/build.py --lang de       # German
  python3 build/build.py --pages 3 14    # only these pages, as loose PDFs + PNGs in output/pages/<lang>
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
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

PAGE_W, PAGE_H = "8.5in", "11.93in"  # 612 × 858.96 pt
CHROMIUM = os.environ.get("CHROMIUM_PATH", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
MONO_TTF = ROOT / "assets" / "fonts" / "IBMPlexMono-400-normal.ttf"
INK = (0x2d / 255, 0x37 / 255, 0x48 / 255)
PAGES = range(1, 25)


# ----------------------------------------------------------------- data
def load_data() -> dict:
    return json.loads((ROOT / "data" / "models.json").read_text())


def load_strings(lang: str) -> dict:
    """data/i18n/<lang>.json (common strings) merged with data/i18n/<lang>/pNN.json (one file per page)."""
    base = ROOT / "data" / "i18n" / f"{lang}.json"
    if not base.exists():
        raise SystemExit(f"no strings for language '{lang}': {base}")
    strings = json.loads(base.read_text())
    for f in sorted((ROOT / "data" / "i18n" / lang).glob("p[0-9][0-9].json")):
        strings[f.stem] = json.loads(f.read_text())
    return strings


def load_page_data() -> dict:
    """data/pages/pNN.json: structured, language-independent content of one page (tables, lists)."""
    return {f.stem: json.loads(f.read_text()) for f in sorted((ROOT / "data" / "pages").glob("p[0-9][0-9].json"))}


def localize_number(value, lang: str) -> str:
    """Decimal comma for German; leaves everything else as it is."""
    s = str(value)
    if lang == "de":
        s = re.sub(r"(?<=\d)\.(?=\d)", ",", s)
    return s


# ------------------------------------------------------------- render
def make_env(lang: str) -> Environment:
    env = Environment(loader=FileSystemLoader(SRC / "templates"), autoescape=False)
    env.filters["n"] = lambda v: localize_number(v, lang)
    env.filters["m"] = lambda mm: localize_number(figures.fmt_m(mm), lang)  # mm → m, short
    env.filters["m2"] = lambda mm: localize_number(f"{mm / 1000:.2f}", lang)  # mm → m, two decimals
    return env


def template_pages() -> list[int]:
    return sorted(int(p.stem[1:]) for p in (SRC / "templates").glob("p[0-9][0-9].html"))


def render_html(data: dict, strings: dict, lang: str, pages: list[int]) -> dict[int, Path]:
    env = make_env(lang)
    prs = data["prs"]
    img = "../../../assets/prs-2500b.png"
    ctx = dict(
        lang=lang, catalog=data["catalog"], c=strings.get("common", {}),
        prs=prs, models=data["models"], series_groups=data["series_groups"],
        series_cards=data["series_cards"], compare=data["large_scene_compare"],
        series_specs=data.get("series_specs", {}), accessories=data.get("accessories", {}),
        data=data,
        qr_svg=figures.qr_svg(data["catalog"]["qr_url"]),
        qr_svg_white=figures.qr_svg(data["catalog"]["qr_url"], color="#ffffff"),
        use_case_svg=figures.use_case_svg(prs, img),
        use_case_compact_svg=figures.use_case_svg(prs, img, W=283, H=154, compact=True),
        fov_scene_svg=figures.fov_scene_svg(prs, img),
        measuring_face_svg=figures.measuring_face_svg(prs),
        measuring_face_small_svg=figures.measuring_face_svg(prs, W=198, H=66),
        end_view_svg=figures.end_view_svg(prs),
        fov_wd_chart_svg=figures.fov_wd_chart_svg(prs),
        range_scatter_svg=figures.range_scatter_svg(data["models"], data["series_groups"]),
        figures=figures,
    )
    page_data = load_page_data()
    html_dir = SRC / "rendered" / lang
    html_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for n in pages:
        tpl = env.get_template(f"p{n:02d}.html")
        html = tpl.render(page_number=n, t=strings.get(f"p{n:02d}", {}), d=page_data.get(f"p{n:02d}", {}), **ctx)
        p = html_dir / f"p{n:02d}.html"
        p.write_text(html)
        paths[n] = p
    return paths


def print_pdfs(html_paths: dict[int, Path], lang: str, png: bool = False) -> dict[int, Path]:
    out_dir = RENDER / lang
    out_dir.mkdir(parents=True, exist_ok=True)
    pdfs = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROMIUM)
        page = browser.new_page(viewport={"width": 816, "height": 1145})
        for n, hp in html_paths.items():
            page.goto(hp.resolve().as_uri())
            page.wait_for_load_state("networkidle")
            page.evaluate("document.fonts.ready")
            width = page.evaluate("Math.max(document.body.scrollWidth, ...[...document.body.querySelectorAll('*')].map(e => e.getBoundingClientRect().right))")
            if width > 817:
                print(f"WARNING p{n:02d}: content overflows the page width ({width}px > 816px)")
            out = out_dir / f"p{n:02d}.pdf"
            page.pdf(path=str(out), width=PAGE_W, height=PAGE_H, print_background=True, prefer_css_page_size=True,
                     margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
            pdfs[n] = out
            if png:
                pymupdf.open(out)[0].get_pixmap(dpi=110).save(out_dir / f"p{n:02d}.png")
        browser.close()
    return pdfs


# ------------------------------------------ in-place patches, source pages
def patch_cover(doc: pymupdf.Document) -> None:
    """Swap the PRS in the Rev. C cover composite for the new render (used only without a p01 template)."""
    page = doc[0]
    xref = next(i["xref"] for i in page.get_image_info(xrefs=True) if i["xref"])
    pix = pymupdf.Pixmap(doc, xref)
    smask = doc.xref_get_key(xref, "SMask")
    if smask[0] == "xref":
        pix = pymupdf.Pixmap(pix, pymupdf.Pixmap(doc, int(smask[1].split()[0])))
    comp = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGBA")
    W, H = comp.size
    cut = int(H * 0.56)
    comp.paste(Image.new("RGBA", (W, H - cut), (0, 0, 0, 0)), (0, cut))
    new = Image.open(ROOT / "assets" / "prs-2500b.png").convert("RGBA")
    scale = (H - cut - 24) / new.height
    new = new.resize((int(new.width * scale), int(new.height * scale)), Image.LANCZOS)
    comp.alpha_composite(new, ((W - new.width) // 2 + 60, cut + 8))
    buf = io.BytesIO()
    comp.save(buf, "PNG")
    page.replace_image(xref, stream=buf.getvalue())


def patch_cells(doc: pymupdf.Document, data: dict, only_pages: set[int]) -> None:
    """Replace single table cells on source pages (data/models.json 'cell_patches')."""
    for patch in data.get("cell_patches", []):
        if patch["page"] not in only_pages:
            continue
        page = doc[patch["page"] - 1]
        spans = [s for b in page.get_text("dict")["blocks"] for l in b.get("lines", []) for s in l["spans"]]
        anchors = [s for s in spans if s["text"].strip() == patch["near"]]
        targets = []
        for a in anchors:
            for s in spans:
                if s["text"].strip() != patch["old"]:
                    continue
                same_row = abs(s["bbox"][3] - a["bbox"][3]) < 2 and s["bbox"][0] > a["bbox"][2]
                same_col = abs(s["bbox"][0] - a["bbox"][0]) < 2 and s["bbox"][1] > a["bbox"][3]
                if same_row or same_col:
                    targets.append(s)
        if len(targets) != 1:
            raise SystemExit(f"cell patch p{patch['page']} {patch['near']} {patch['old']}: {len(targets)} matches")
        s = targets[0]
        r = pymupdf.Rect(s["bbox"])
        pix = page.get_pixmap(dpi=144, clip=pymupdf.Rect(r.x1 + 3, r.y0, r.x1 + 4, r.y1))
        px = pix.pixel(0, pix.height // 2)
        page.add_redact_annot(r + (-0.5, -0.5, 2, 0.5), fill=tuple(c / 255 for c in px[:3]))
        page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE)
        page.insert_text((r.x0, r.y1 - 0.22 * s["size"]), patch["new"], fontsize=s["size"], color=INK,
                         fontfile=str(MONO_TTF), fontname="PlexMono")


def render_scene_png(data: dict) -> Path:
    """The depalletizing tile on page 4 as a PNG (used only without a p04 template)."""
    svg = figures.use_case_svg(data["prs"], "../../assets/prs-2500b.png", W=283, H=154, compact=True)
    html = SRC / "rendered" / "scene-p04.html"
    html.parent.mkdir(exist_ok=True)
    html.write_text('<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="../catalog.css">'
                    '<body style="background:#111827;width:283pt;height:154pt;overflow:hidden">'
                    '<div class="fig-label" style="position:absolute;left:28pt;top:8pt">PRS over a Euro pallet · illustration</div>'
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


def patch_page4(doc: pymupdf.Document, data: dict) -> None:
    page = doc[3]
    infos = sorted((i for i in page.get_image_info(xrefs=True) if i["xref"]), key=lambda i: (i["bbox"][1], i["bbox"][0]))
    page.replace_image(infos[1]["xref"], filename=str(render_scene_png(data)))
    old, new = "PRS-2500 · VR-2300B", f"{data['prs']['model']} · VR-2300B"
    for r in page.search_for(old):
        page.add_redact_annot(r, fill=(1, 1, 1))
        page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE)
        page.insert_text((r.x0, r.y1 - 0.22 * 6.6), new, fontsize=6.6, color=INK, fontfile=str(MONO_TTF), fontname="PlexMono")


# ------------------------------------------------------------ assemble
def assemble(pdfs: dict[int, Path], data: dict, lang: str) -> Path:
    doc = pymupdf.open(SOURCE_PDF)
    fallback = {n for n in PAGES if n not in pdfs}
    if fallback and lang != "en":
        print(f"WARNING: pages {sorted(fallback)} have no template and fall back to the English Rev. C pages")
    if 1 in fallback:
        patch_cover(doc)
    patch_cells(doc, data, fallback)
    if 4 in fallback:
        patch_page4(doc, data)
    for n, p in pdfs.items():
        new = pymupdf.open(p)
        doc.delete_page(n - 1)
        doc.insert_pdf(new, from_page=0, to_page=0, start_at=n - 1)
    doc.set_metadata({**doc.metadata, "title": f"Bigframe Product Catalog 2026 — {lang.upper()}"})
    OUT.mkdir(exist_ok=True)
    final = OUT / f"Bigframe_Product_Catalog_2026_{lang.upper()}.pdf"
    doc.save(final, garbage=4, deflate=True)
    return final


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="en")
    ap.add_argument("--pages", nargs="*", type=int, help="render only these pages (loose PDFs + PNGs), no assembly")
    args = ap.parse_args()
    data = load_data()
    strings = load_strings(args.lang)
    available = template_pages()
    if args.pages:
        missing = [n for n in args.pages if n not in available]
        if missing:
            raise SystemExit(f"no template for pages {missing}")
        html = render_html(data, strings, args.lang, args.pages)
        pdfs = print_pdfs(html, args.lang, png=True)
        for n, p in pdfs.items():
            print("rendered", p, "and", p.with_suffix(".png"))
        return
    html = render_html(data, strings, args.lang, available)
    pdfs = print_pdfs(html, args.lang)
    final = assemble(pdfs, data, args.lang)
    print("built", final, f"({final.stat().st_size / 1e6:.1f} MB); pages from code: {available}")


if __name__ == "__main__":
    main()
