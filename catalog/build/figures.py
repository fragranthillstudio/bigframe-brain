"""SVG figure generators for the catalog pages.

Every figure is computed from data/models.json so a spec change redraws the
frustums, the charts and the dimension drawings with it. All sizes are in pt.
"""
from __future__ import annotations

import math

import qrcode
import qrcode.image.svg

INK = "#2d3748"
MUTED = "#5b6675"
FAINT = "#6b7787"
RULE = "#d9dcd6"
RULE_STRONG = "#c4c9c2"
LIME = "#c8ff3d"
BLUE = "#3d5afe"
BLUE_PAPER = "#3149d6"
GREEN_PAPER = "#00a86a"
AMBER = "#f2a33a"
ON_DARK = "#c9cfd8"
ON_DARK_MUTED = "#9aa3b2"

MONO = "IBM Plex Mono"
SANS = "IBM Plex Sans"


def fmt_m(mm: float) -> str:
    v = mm / 1000
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s


# ---------------------------------------------------------------- QR code
def qr_svg(url: str, color: str = "#111827") -> str:
    q = qrcode.QRCode(border=0, box_size=1, error_correction=qrcode.constants.ERROR_CORRECT_M)
    q.add_data(url)
    q.make(fit=True)
    m = q.get_matrix()
    n = len(m)
    rects = "".join(
        f'<rect x="{x}" y="{y}" width="1" height="1"/>'
        for y, row in enumerate(m) for x, v in enumerate(row) if v
    )
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n} {n}" shape-rendering="crispEdges">'
            f'<g fill="{color}">{rects}</g></svg>')


# ------------------------------------------------- oblique scene projection
class Scene:
    """Cabinet-style projection of the measuring volume under a fixed bar.

    x: field-of-view width (mm) to the right; y: field-of-view height (mm),
    receding up-right; z: working distance (mm), down the page.
    """

    def __init__(self, cx: float, cy: float, s: float, sz: float, dy=(0.52, -0.30)):
        self.cx, self.cy, self.s, self.sz, self.dy = cx, cy, s, sz, dy

    def p(self, x: float, y: float, z: float) -> tuple[float, float]:
        X = self.cx + x * self.s + y * self.s * self.dy[0]
        Y = self.cy + z * self.sz + y * self.s * self.dy[1]
        return X, Y

    def rect(self, w: float, h: float, z: float, x0: float = 0, y0: float = 0):
        return [self.p(x0 + sx * w / 2, y0 + sy * h / 2, z) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


def _poly(pts, **attrs) -> str:
    a = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items())
    return f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" {a}/>'


def _line(a, b, **attrs) -> str:
    at = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items())
    return f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" {at}/>'


def _text(x, y, s, size=6.4, fill=ON_DARK, family=MONO, anchor="start", weight=400, extra="") -> str:
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}" {extra}>{s}</text>')


def pallet(sc: Scene, z_floor: float, z_top: float, x0: float = 0, y0: float = 0,
           w: float = 1200, d: float = 800, layers: int = 3, cols: int = 3) -> str:
    """A loaded Euro pallet: pallet deck plus a block of cartons, in the scene projection."""
    out = []
    z_deck = z_floor - 144  # 144 mm pallet height
    # pallet deck (three faces)
    top = sc.rect(w, d, z_deck, x0, y0)
    front = [sc.p(x0 - w / 2, y0 - d / 2, z_deck), sc.p(x0 + w / 2, y0 - d / 2, z_deck),
             sc.p(x0 + w / 2, y0 - d / 2, z_floor), sc.p(x0 - w / 2, y0 - d / 2, z_floor)]
    side = [sc.p(x0 + w / 2, y0 - d / 2, z_deck), sc.p(x0 + w / 2, y0 + d / 2, z_deck),
            sc.p(x0 + w / 2, y0 + d / 2, z_floor), sc.p(x0 + w / 2, y0 - d / 2, z_floor)]
    out += [_poly(front, fill="#8a6a3f"), _poly(side, fill="#6e5432"), _poly(top, fill="#a8865a")]
    # pallet stringers (three dark slots on the front)
    for i in range(3):
        xa = x0 - w / 2 + 40 + i * (w - 80) / 3 + 60
        p1 = sc.p(xa, y0 - d / 2, z_deck + 40); p2 = sc.p(xa + (w - 80) / 3 - 120, y0 - d / 2, z_deck + 40)
        p3 = sc.p(xa + (w - 80) / 3 - 120, y0 - d / 2, z_floor - 22); p4 = sc.p(xa, y0 - d / 2, z_floor - 22)
        out.append(_poly([p1, p2, p3, p4], fill="#4a3822"))
    # cartons: block from z_deck up to z_top, layers × cols × 2 rows
    lh = (z_deck - z_top) / layers
    for li in range(layers):
        zt = z_top + li * lh
        zb = zt + lh
        # alternate layers: cols × 2 cartons, then 2 × 3 turned the other way
        nx, ny = (cols, 2) if li % 2 == 0 else (2, 3)
        cw, cd = w / nx, d / ny
        for ri in range(ny):
            for ci in range(nx):
                cx_ = x0 - w / 2 + ci * cw + cw / 2
                cy_ = y0 - d / 2 + ri * cd + cd / 2
                t = sc.rect(cw, cd, zt, cx_, cy_)
                f = [sc.p(cx_ - cw / 2, cy_ - cd / 2, zt), sc.p(cx_ + cw / 2, cy_ - cd / 2, zt),
                     sc.p(cx_ + cw / 2, cy_ - cd / 2, zb), sc.p(cx_ - cw / 2, cy_ - cd / 2, zb)]
                s_ = [sc.p(cx_ + cw / 2, cy_ - cd / 2, zt), sc.p(cx_ + cw / 2, cy_ + cd / 2, zt),
                      sc.p(cx_ + cw / 2, cy_ + cd / 2, zb), sc.p(cx_ + cw / 2, cy_ - cd / 2, zb)]
                out += [_poly(f, fill="#c9a77c", stroke="#9a7b52", stroke_width=0.35),
                        _poly(s_, fill="#a98a62", stroke="#8a6d47", stroke_width=0.35),
                        _poly(t, fill="#e2c9a4", stroke="#b0925f", stroke_width=0.35)]
    return "".join(out)


def camera_image(href: str, cx: float, y_top: float, width: float, aspect: float) -> str:
    h = width / aspect
    return f'<image href="{href}" x="{cx - width / 2:.1f}" y="{y_top:.1f}" width="{width:.1f}" height="{h:.1f}"/>'


# ------------------------------------------------------- page 14: FOV scene
def fov_scene_svg(prs: dict, img_href: str, W: float = 510, H: float = 363) -> str:
    """Field of view at the three specified working distances, planes to scale, camera not to scale."""
    by = prs["by_wd"]
    far = by[-1]
    # scale: far plane width must fit the panel; z compressed
    s = 0.058                      # pt per mm: far plane 209 pt wide, clear of the labels
    sz = 235 / far["wd"]
    sc = Scene(cx=190, cy=78, s=s, sz=sz)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}pt" height="{H}pt">']
    out.append('<defs><linearGradient id="beam" x1="0" y1="0" x2="0" y2="1">'
               '<stop offset="0" stop-color="#3d5afe" stop-opacity="0.32"/>'
               '<stop offset="1" stop-color="#3d5afe" stop-opacity="0.06"/></linearGradient></defs>')
    apex = sc.p(0, 0, 0)
    # frustum body
    fr = sc.rect(far["fov_w"], far["fov_h"], far["wd"])
    out.append(_poly([apex, fr[0], fr[3]], fill="url(#beam)"))
    out.append(_poly([apex, fr[0], fr[1]], fill="url(#beam)"))
    out.append(_poly([apex, fr[1], fr[2]], fill="url(#beam)"))
    out.append(_poly([apex, fr[3], fr[2]], fill="url(#beam)"))
    # floor at far WD, pallet with its top at the optimum WD
    opt = by[1]
    out.append(pallet(sc, z_floor=far["wd"], z_top=opt["wd"], x0=-250, y0=-150))
    # planes, far to near so nearer planes draw on top
    styles = {"near": ("#ffffff", 0.7, "#ffffff", 0.05), "opt.": (LIME, 1.1, LIME, 0.10), "far": ("#ffffff", 0.7, "#ffffff", 0.04)}
    labels = []
    for row in reversed(by):
        stroke, sw, fill, fo = styles[row["tag"]]
        r = sc.rect(row["fov_w"], row["fov_h"], row["wd"])
        out.append(_poly(r, fill=fill, fill_opacity=fo, stroke=stroke, stroke_width=sw, stroke_linejoin="round"))
        labels.append((row, r))
    # frustum edges
    for c in fr:
        out.append(_line(apex, c, stroke="#ffffff", stroke_width=0.45, stroke_opacity=0.55))
    # camera bar over the apex (drawn after the beam so it sits on top)
    out.append(camera_image(img_href, cx=apex[0] + 8, y_top=apex[1] - 52, width=205, aspect=2.2))
    # labels on the right, with leaders from the right-hand corner of each plane
    lx = 372
    ys = {"near": 150, "opt.": 218, "far": 288}
    for row, r in labels:
        corner = r[1]
        y = ys[row["tag"]]
        col = LIME if row["tag"] == "opt." else "#ffffff"
        out.append(_line(corner, (lx - 8, y - 3), stroke="#ffffff", stroke_width=0.45, stroke_opacity=0.7))
        out.append(f'<circle cx="{corner[0]:.1f}" cy="{corner[1]:.1f}" r="1.6" fill="#ffffff"/>')
        tag = {"near": " · near", "opt.": " · optimum", "far": " · far"}[row["tag"]]
        out.append(_text(lx, y, f"WD {fmt_m(row['wd'])} m{tag}", size=7.6, fill=col, family=SANS, weight=600))
        out.append(_text(lx, y + 10, f"{row['fov_w']} × {row['fov_h']} mm", size=6.4, fill=ON_DARK))
        out.append(_text(lx, y + 19, f"{row['spacing_um']} µm point spacing", size=5.9, fill=ON_DARK_MUTED))
    out.append("</svg>")
    return "".join(out)


# ------------------------------------------------- page 13: PRS in use scene
def use_case_svg(prs: dict, img_href: str, W: float = 283, H: float = 200, compact: bool = False) -> str:
    """The PRS over a loaded Euro pallet; compact=True is the small applications tile (page 4)."""
    opt = prs["by_wd"][1]
    far = prs["by_wd"][-1]
    if compact:
        s, sz, sc = 108 / opt["fov_w"], 84 / far["wd"], None
        sc = Scene(cx=150, cy=34, s=s, sz=sz)
    else:
        s = 150 / opt["fov_w"]
        sz = 118 / far["wd"]
        sc = Scene(cx=118, cy=56, s=s, sz=sz)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}pt" height="{H}pt">']
    out.append('<defs><linearGradient id="beam2" x1="0" y1="0" x2="0" y2="1">'
               '<stop offset="0" stop-color="#3d5afe" stop-opacity="0.34"/>'
               '<stop offset="1" stop-color="#3d5afe" stop-opacity="0.08"/></linearGradient></defs>')
    apex = sc.p(0, 0, 0)
    r = sc.rect(opt["fov_w"], opt["fov_h"], opt["wd"])
    for a, b in ((0, 3), (0, 1), (1, 2), (3, 2)):
        out.append(_poly([apex, r[a], r[b]], fill="url(#beam2)"))
    out.append(pallet(sc, z_floor=far["wd"], z_top=opt["wd"], x0=-200, y0=-150, layers=3, cols=3))
    out.append(_poly(r, fill=LIME, fill_opacity=0.10, stroke=LIME, stroke_width=1.0, stroke_linejoin="round"))
    for c in r:
        out.append(_line(apex, c, stroke="#ffffff", stroke_width=0.4, stroke_opacity=0.5))
    out.append(camera_image(img_href, cx=apex[0] + 5, y_top=apex[1] - (26 if compact else 36), width=(100 if compact else 140), aspect=2.2))
    if compact:
        out.append("</svg>")
        return "".join(out)
    # WD dimension at the right edge
    x = 262
    out.append(_line((x, apex[1]), (x, r[1][1]), stroke=ON_DARK, stroke_width=0.5))
    out.append(_line((x - 3, apex[1]), (x + 3, apex[1]), stroke=ON_DARK, stroke_width=0.5))
    out.append(_line((x - 3, r[1][1]), (x + 3, r[1][1]), stroke=ON_DARK, stroke_width=0.5))
    out.append(_text(x - 5, (apex[1] + r[1][1]) / 2 + 2, f"WD {fmt_m(opt['wd'])} m", size=5.6, fill=ON_DARK, anchor="end"))
    out.append(_text(10, H - 12, f"FOV {fmt_m(opt['fov_w'])} × {fmt_m(opt['fov_h'])} m at the optimum", size=5.6, fill=ON_DARK))
    out.append("</svg>")
    return "".join(out)


# ------------------------------------------------ dimension drawings
def measuring_face_svg(prs: dict, W: float = 196, H: float = 66, label: bool = True) -> str:
    """Measuring face: the 890 mm bar with both camera windows, the RGB window and the projector module."""
    L, Wd = prs["dimensions_mm"]["l"], prs["dimensions_mm"]["w"]
    k = (W - 34) / L  # pt per mm, leaving room for the width dimension at the right
    x0, y0 = 8, 16
    w, h = L * k, Wd * k
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}pt" height="{H}pt">',
           '<defs><pattern id="weave" width="3" height="3" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
           '<rect width="3" height="3" fill="#e9ebe7"/><line x1="0" y1="0" x2="0" y2="3" stroke="#d3d6d0" stroke-width="0.7"/></pattern></defs>']
    out.append(f'<rect x="{x0}" y="{y0}" width="{w:.1f}" height="{h:.1f}" fill="url(#weave)" stroke="{INK}" stroke-width="0.7"/>')
    # end caps
    cap = 42 * k
    for xx in (x0, x0 + w - cap):
        out.append(f'<rect x="{xx:.1f}" y="{y0}" width="{cap:.1f}" height="{h:.1f}" fill="#cfd3cc" stroke="{INK}" stroke-width="0.6"/>')
    # camera windows near each end, RGB window and projector module
    win = 58 * k
    for xx in (x0 + 52 * k, x0 + w - 52 * k - win):
        out.append(f'<rect x="{xx:.1f}" y="{y0 + (h - win) / 2:.1f}" width="{win:.1f}" height="{win:.1f}" fill="#ffffff" stroke="{INK}" stroke-width="0.6"/>')
        out.append(f'<rect x="{xx + 4:.1f}" y="{y0 + (h - win) / 2 + 4:.1f}" width="{win - 8:.1f}" height="{win - 8:.1f}" fill="{BLUE_PAPER}" fill-opacity="0.75"/>')
    rgb_x = x0 + 300 * k
    out.append(f'<circle cx="{rgb_x:.1f}" cy="{y0 + h / 2:.1f}" r="{20 * k:.1f}" fill="#ffffff" stroke="{INK}" stroke-width="0.6"/>')
    out.append(f'<circle cx="{rgb_x:.1f}" cy="{y0 + h / 2:.1f}" r="{14 * k:.1f}" fill="{BLUE_PAPER}" fill-opacity="0.75"/>')
    mod_w, mod_h = 170 * k, 86 * k
    mx = x0 + w / 2 - mod_w / 2 + 20 * k
    out.append(f'<rect x="{mx:.1f}" y="{y0 + (h - mod_h) / 2:.1f}" width="{mod_w:.1f}" height="{mod_h:.1f}" rx="2" fill="#dfe3f5" stroke="{INK}" stroke-width="0.6"/>')
    out.append(f'<rect x="{mx + mod_w / 2 - 34 * k:.1f}" y="{y0 + h / 2 - 16 * k:.1f}" width="{68 * k:.1f}" height="{32 * k:.1f}" fill="{BLUE_PAPER}" fill-opacity="0.75"/>')
    # dimension: length below
    dy = y0 + h + 12
    out += [_line((x0, dy), (x0 + w, dy), stroke=INK, stroke_width=0.5),
            _line((x0, y0 + h + 3), (x0, dy + 3), stroke=INK, stroke_width=0.4),
            _line((x0 + w, y0 + h + 3), (x0 + w, dy + 3), stroke=INK, stroke_width=0.4),
            f'<rect x="{x0 + w / 2 - 11:.1f}" y="{dy - 4.5:.1f}" width="22" height="9" fill="#ffffff"/>',
            _text(x0 + w / 2, dy + 2.3, f"{L}", size=6.5, fill=INK, anchor="middle")]
    # dimension: width at the right
    dx = x0 + w + 9
    out += [_line((dx, y0), (dx, y0 + h), stroke=INK, stroke_width=0.5),
            _line((x0 + w + 3, y0), (dx + 3, y0), stroke=INK, stroke_width=0.4),
            _line((x0 + w + 3, y0 + h), (dx + 3, y0 + h), stroke=INK, stroke_width=0.4),
            _text(dx + 3, y0 + h / 2 + 2, f"{Wd}", size=5.9, fill=INK, extra=f'transform="rotate(-90 {dx + 3:.1f} {y0 + h / 2 + 2:.1f})" text-anchor="middle"')]
    if label:
        out.append(_text(x0 + w / 2, H - 2, "MEASURING FACE", size=6.2, fill=FAINT, family=SANS, anchor="middle", extra='letter-spacing="0.8"'))
    out.append("</svg>")
    return "".join(out)


def end_view_svg(prs: dict, W: float = 56, H: float = 66, k: float = 0.182) -> str:
    Wd, Hh = prs["dimensions_mm"]["w"], prs["dimensions_mm"]["h"]
    w, h = Wd * k, Hh * k
    x0, y0 = 16, 16
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}pt" height="{H}pt">']
    out.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{w:.1f}" height="{h:.1f}" fill="#cfd3cc" stroke="{INK}" stroke-width="0.7"/>')
    win = 58 * k
    out.append(f'<rect x="{x0 + (w - win) / 2:.1f}" y="{y0 + (h - win) / 2:.1f}" width="{win:.1f}" height="{win:.1f}" fill="#ffffff" stroke="{INK}" stroke-width="0.6"/>')
    out.append(f'<rect x="{x0 + (w - win) / 2 + 2:.1f}" y="{y0 + (h - win) / 2 + 2:.1f}" width="{win - 4:.1f}" height="{win - 4:.1f}" fill="{BLUE_PAPER}" fill-opacity="0.75"/>')
    dy = y0 + h + 12
    out += [_line((x0, dy), (x0 + w, dy), stroke=INK, stroke_width=0.5),
            _line((x0, y0 + h + 3), (x0, dy + 3), stroke=INK, stroke_width=0.4),
            _line((x0 + w, y0 + h + 3), (x0 + w, dy + 3), stroke=INK, stroke_width=0.4),
            f'<rect x="{x0 + w / 2 - 6:.1f}" y="{dy - 4.5:.1f}" width="12" height="9" fill="#ffffff"/>',
            _text(x0 + w / 2, dy + 2.3, f"{Hh}", size=6.5, fill=INK, anchor="middle")]
    out.append(_text(x0 + w / 2, H - 2, "END VIEW", size=6.2, fill=FAINT, family=SANS, anchor="middle", extra='letter-spacing="0.8"'))
    out.append("</svg>")
    return "".join(out)


# ------------------------------------------------ page 20: FOV vs WD chart
def fov_wd_chart_svg(prs: dict, W: float = 510, H: float = 192) -> str:
    by = prs["by_wd"]
    x0, x1, y0, y1 = 48, 480, 22, 158  # plot box
    wds = [r["wd"] for r in by]
    wmin, wmax = 1000, 3700
    ymax = 4000

    def X(wd): return x0 + (wd - wmin) / (wmax - wmin) * (x1 - x0)
    def Y(mm): return y1 - mm / ymax * (y1 - y0)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}pt" height="{H}pt">']
    for m in range(0, ymax + 1, 1000):
        out.append(_line((x0, Y(m)), (x1, Y(m)), stroke=RULE, stroke_width=0.5))
        out.append(_text(x0 - 6, Y(m) + 2, f"{m // 1000} m" if m else "0", size=5.7, fill=FAINT, anchor="end"))
    for r in by:
        out.append(_line((X(r["wd"]), y0), (X(r["wd"]), y1), stroke=RULE, stroke_width=0.5, stroke_dasharray="1.5 1.5"))
    for key, col, lab in (("fov_w", BLUE, "Field-of-view width, mm"), ("fov_h", GREEN_PAPER, "Field-of-view height, mm")):
        pts = [(X(r["wd"]), Y(r[key])) for r in by]
        out.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="none" stroke="{col}" stroke-width="1.4" stroke-linejoin="round"/>')
        for (x, y), r in zip(pts, by):
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.4" fill="{col}"/>')
            dy = -5 if key == "fov_w" else 10.5
            out.append(_text(x + 5, y + dy, f"{r[key]}", size=5.7, fill=INK))
    # x labels
    for r in by:
        x = X(r["wd"])
        bold = 600 if r["tag"] == "opt." else 400
        t = f"WD {fmt_m(r['wd'])} m" + (" (opt.)" if r["tag"] == "opt." else "")
        out.append(_text(x, y1 + 12, t, size=5.9, fill=INK, family=SANS, anchor="middle", weight=bold))
        out.append(_text(x, y1 + 21.5, f"{r['spacing_um']} µm spacing", size=5.4, fill=FAINT, anchor="middle"))
    # legend
    lx = x0 + 8
    for i, (col, lab) in enumerate(((BLUE, "Field-of-view width, mm"), (GREEN_PAPER, "Field-of-view height, mm"))):
        xx = lx + i * 135
        out.append(f'<rect x="{xx}" y="{y0 - 12}" width="9" height="3" fill="{col}"/>')
        out.append(_text(xx + 13, y0 - 8.6, lab, size=5.9, fill=FAINT, family=SANS))
    out.append("</svg>")
    return "".join(out)


# ------------------------------------------------ page 2: range scatter
LABEL_OFFSETS = {
    # model: (dx, dy, anchor) relative to the point, tuned so labels do not collide
    "TRS-010B": (6, 2.5, "start"), "TRS-025B": (6, 2.5, "start"), "TRS-050B": (6, 5, "start"), "TRS-075B": (-6, 2.5, "end"),
    "VRH9-020B": (-6, 2.5, "end"), "VRH9-040B": (-6, 2.5, "end"), "VRH9-080B": (-6, 2.5, "end"),
    "VRH9-120B": (6, 4.5, "start"), "VRH9-160B": (6, 3, "start"), "VRH9-200B": (6, 1, "start"), "VRH9-280B": (-6, 2.5, "end"),
    "VR-400B": (6, 1.5, "start"), "VR-600B": (-6, 2.5, "end"), "VR-1300B": (6, 2.5, "start"), "VR-2300B": (-6, 2.5, "end"),
    "VRD-600B": (6, 2.5, "start"), "VRD-1200B": (-6, 2.5, "end"), "PRS-2500B": (-6, 2.5, "end"),
}


def range_scatter_svg(models: list[dict], groups: list[dict], W: float = 510, H: float = 268) -> str:
    x0, x1 = 44, 506  # plot box in figure coordinates
    y0, y1 = 24, 222
    xmin, xmax = 5, 5000        # mm
    ymin, ymax = 0.03, 1000     # µm
    lx = math.log10

    def X(v): return x0 + (lx(v) - lx(xmin)) / (lx(xmax) - lx(xmin)) * (x1 - x0)
    def Y(v): return y1 - (lx(v) - lx(ymin)) / (lx(ymax) - lx(ymin)) * (y1 - y0)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}pt" height="{H}pt">']
    out.append(f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" fill="#ffffff"/>')
    # minor and major grid
    for dec in range(0, 4):
        for k in range(1, 10):
            v = 5 * 10 ** dec * k / 5 if False else (10 ** dec) * k
            if xmin <= v <= xmax:
                out.append(_line((X(v), y0), (X(v), y1), stroke=RULE, stroke_width=0.85 if k == 1 else 0.35))
    for dec in range(-2, 4):
        for k in range(1, 10):
            v = (10 ** dec) * k
            if ymin <= v <= ymax:
                out.append(_line((x0, Y(v)), (x1, Y(v)), stroke=RULE, stroke_width=0.85 if k == 1 else 0.35))
    for v, lab in ((10, "10 mm"), (100, "100 mm"), (1000, "1 m")):
        out.append(_text(X(v), y1 + 11, lab, size=6.7, fill=INK, anchor="middle"))
    for v, lab in ((0.1, "0.1 µm"), (1, "1 µm"), (10, "10 µm"), (100, "100 µm"), (1000, "1 mm")):
        out.append(_text(x0 - 5, Y(v) + 2.3, lab, size=6.7, fill=INK, anchor="end"))
    out.append(_text((x0 + x1) / 2, y1 + 22, "FIELD OF VIEW, WIDTH AT OPTIMUM WORKING DISTANCE", size=6.4, fill=FAINT, anchor="middle", extra='letter-spacing="0.7"'))
    out.append(_text(9, (y0 + y1) / 2, "Z REPEATABILITY, REGIONAL 2σ", size=6.4, fill=FAINT, anchor="middle",
                     extra=f'letter-spacing="0.7" transform="rotate(-90 9 {(y0 + y1) / 2:.1f})"'))
    color = {g["id"]: g["color"] for g in groups}
    for m in models:
        px, py = X(m["fov_w"]), Y(m["z"])
        col = color[m["series"]]
        dx, dy, anchor = LABEL_OFFSETS.get(m["model"], (6, 2.5, "start"))
        label = m["model"] + (" ¹" if m["series"] == "prs" else "")
        # leader: short line from the point to the label
        out.append(_line((px, py), (px + (dx - 2 if dx > 0 else dx + 2), py + dy - 2.5), stroke=RULE_STRONG, stroke_width=0.5))
        if m["series"] == "prs":
            out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.4" fill="#ffffff" stroke="{col}" stroke-width="1.3"/>')
        else:
            out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.2" fill="{col}"/>')
        out.append(_text(px + dx, py + dy, label, size=7.4, fill=INK, anchor=anchor))
    # legend
    names = {"trs": "TRS series", "vrh9": "VRH9 series", "vr": "VR series", "vrd": "VRD series", "prs": "PRS series (preliminary)"}
    xx = 60
    for g in groups:
        col = g["color"]
        if g["id"] == "prs":
            out.append(f'<circle cx="{xx}" cy="{H - 10}" r="3" fill="#ffffff" stroke="{col}" stroke-width="1.2"/>')
        else:
            out.append(f'<circle cx="{xx}" cy="{H - 10}" r="3" fill="{col}"/>')
        out.append(_text(xx + 7, H - 7.6, names[g["id"]], size=6.7, fill=INK, family=SANS))
        xx += 84 if g["id"] != "vrd" else 84
    out.append("</svg>")
    return "".join(out)


# ------------------------------------------------ VR / VRD series pages (p10, p12)
def fov_cone_vr_svg(wd_near: float, wd_opt: float, wd_far: float, opt_w: float, opt_h: float,
                    far_w: float, far_h: float, img_href: str, img_w: float, img_h: float,
                    labels: dict, uid: str, W: float = 129.4, H: float = 200, apex_y: float = 27.5,
                    far_y: float = 153.5, far_px: float = 73.5, img_top: float = 2.0,
                    caption_top: float = 160.7, axis_dx: float = 41.9, decimal: str = ".") -> str:
    """Oblique measuring-volume pyramid of one VR/VRD model: near, optimum (hatched) and far
    field-of-view planes at their working distances, drawn to scale within the model.
    `labels`: wd, opt, far, depth, mm. `decimal`: the language's decimal separator."""
    fmt = lambda v: str(v).replace(".", decimal)  # noqa: E731
    ax = W / 2
    s = far_px / far_w                       # pt per mm across the field of view
    kx, ky = 0.36, 0.21                      # oblique shear of the depth axis

    def fov(w):                              # linear field of view between optimum and far
        f = (w - wd_opt) / (wd_far - wd_opt)
        return opt_w + (far_w - opt_w) * f, opt_h + (far_h - opt_h) * f

    def plane(w):
        y = apex_y + (far_y - apex_y) * w / wd_far
        fw, fh = fov(w)
        fw, fh = fw * s, fh * s
        dx, dy = kx * fh, ky * fh
        return dict(y=y, fl=(ax - fw / 2, y), fr=(ax + fw / 2, y), br=(ax + fw / 2 + dx, y - dy),
                    bl=(ax - fw / 2 + dx, y - dy))

    near, opt, far = plane(wd_near), plane(wd_opt), plane(wd_far)
    apex = (ax, apex_y)
    o = []
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}pt" height="{H}pt" viewBox="0 0 {W} {H}" '
             f'font-family="{MONO}">')
    o.append(f'<defs><linearGradient id="g{uid}" x1="0" y1="0" x2="0" y2="1">'
             f'<stop offset="0" stop-color="{BLUE_PAPER}" stop-opacity="0.55"/>'
             f'<stop offset="0.25" stop-color="{BLUE_PAPER}" stop-opacity="0.12"/>'
             f'<stop offset="1" stop-color="{BLUE_PAPER}" stop-opacity="0.06"/></linearGradient>'
             f'<pattern id="h{uid}" patternUnits="userSpaceOnUse" width="2.6" height="2.6" patternTransform="rotate(45)">'
             f'<line x1="0" y1="0" x2="0" y2="2.6" stroke="{INK}" stroke-width="0.7" stroke-opacity="0.6"/></pattern>'
             f'<radialGradient id="s{uid}" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="{BLUE_PAPER}" stop-opacity="0.35"/>'
             f'<stop offset="1" stop-color="{BLUE_PAPER}" stop-opacity="0"/></radialGradient></defs>')
    # camera shadow and image
    o.append(f'<ellipse cx="{ax}" cy="{apex_y + 1.5}" rx="{img_w * 0.55}" ry="4" fill="url(#s{uid})"/>')
    o.append(f'<image href="{img_href}" x="{ax - img_w / 2}" y="{img_top}" width="{img_w}" height="{img_h}"/>')
    # light cone from the camera to the far plane
    o.append(_poly([apex, far["fl"], far["fr"], far["br"], far["bl"]], fill=f"url(#g{uid})", stroke="none"))
    for c in ("fl", "fr", "br", "bl"):
        o.append(_line(apex, far[c], stroke=BLUE_PAPER, **{"stroke-width": 0.45, "stroke-opacity": 0.75}))
    # far plane
    o.append(_poly([far["fl"], far["fr"], far["br"], far["bl"]], fill=BLUE_PAPER, **{"fill-opacity": 0.3, "stroke": INK, "stroke-width": 0.74}))
    # measuring depth: front and side faces between near and far
    o.append(_poly([near["fl"], far["fl"], far["fr"], near["fr"]], fill=BLUE_PAPER, **{"fill-opacity": 0.28, "stroke": "none"}))
    o.append(_poly([near["fr"], far["fr"], far["br"], near["br"]], fill=BLUE_PAPER, **{"fill-opacity": 0.2, "stroke": "none"}))
    for c in ("fl", "fr", "br", "bl"):
        o.append(_line(near[c], far[c], stroke=BLUE_PAPER, **{"stroke-width": 0.57}))
    # optimum plane (hatched) and near plane
    o.append(_poly([opt["fl"], opt["fr"], opt["br"], opt["bl"]], fill=BLUE_PAPER, **{"fill-opacity": 0.5, "stroke": "none"}))
    o.append(_poly([opt["fl"], opt["fr"], opt["br"], opt["bl"]], fill=f"url(#h{uid})", stroke=INK, **{"stroke-width": 0.85}))
    o.append(_poly([near["fl"], near["fr"], near["br"], near["bl"]], fill=BLUE_PAPER, **{"fill-opacity": 0.42, "stroke": INK, "stroke-width": 0.74}))
    # working-distance axis
    axx = ax - axis_dx
    o.append(_line((axx, apex_y), (axx, far_y), stroke=FAINT, **{"stroke-width": 0.57}))
    o.append(f'<circle cx="{axx}" cy="{apex_y}" r="1.1" fill="{FAINT}"/>')
    o.append(_text(axx - 3.6, apex_y + 2, labels["wd"], size=5.1, fill=FAINT, anchor="end"))
    for p, w in ((near, wd_near), (opt, wd_opt), (far, wd_far)):
        o.append(_line((axx, p["y"]), p["fl"], stroke=FAINT, **{"stroke-width": 0.45, "stroke-dasharray": "1.2 1.2"}))
        o.append(_text(axx - 3.6, p["y"] + 2.3, fmt(w), size=6.4, fill=INK, anchor="end"))
    # caption
    mm = labels["mm"]
    lines = [(f'{labels["wd"]} {fmt(wd_near)}–{fmt(wd_far)} {mm}', INK),
             (f'{labels["opt"]} {fmt(opt_w)} × {fmt(opt_h)} {mm}', INK),
             (f'{labels["far"]} {fmt(far_w)} × {fmt(far_h)} {mm}', INK),
             (f'{labels["depth"]} {fmt(wd_far - wd_near)} {mm}', FAINT)]
    for i, (txt, col) in enumerate(lines):
        o.append(_text(ax, caption_top + 6.9 + i * 9.4, txt, size=6.7, fill=col, anchor="middle"))
    o.append("</svg>")
    return "".join(o)


def housing_views_vr_svg(l: float, w: float, h: float, pattern_l: float, pattern_w: float, hole_d: float,
                         conn_spacing: float, labels: dict, variant: str = "vr", s: float = 0.264,
                         mx: float = 49.0, my: float = 62.0, bx: float = 154.3, fs: float = 1.0,
                         W: float = 250, H: float = 170, decimal: str = ".") -> str:
    """Mounting face, back and measuring face of a VR (variant 'vr') or VRD ('vrd') housing with
    dimension lines. l, w, h in mm; s in pt/mm; mx/my/bx: drawing origins; fs: label size factor.
    `labels`: through, mounting_face, back, measuring_face. `decimal`: the language's decimal separator."""
    fmt = lambda v: str(v).replace(".", decimal)  # noqa: E731
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}pt" height="{H}pt" viewBox="0 0 {W} {H}" font-family="{MONO}">']
    dim = dict(stroke=FAINT, **{"stroke-width": 0.54})
    dimline = dict(stroke=FAINT, **{"stroke-width": 0.73})

    def arrow(a, b):
        """Dimension line with filled arrowheads at both ends."""
        (x1, y1), (x2, y2) = a, b
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy) or 1
        ux, uy = dx / L, dy / L
        px, py = -uy, ux
        parts = [_line(a, b, **dimline)]
        for (x, y), d in ((a, 1), (b, -1)):
            tip = (x, y)
            b1 = (x + d * ux * 3.2 + px * 0.9, y + d * uy * 3.2 + py * 0.9)
            b2 = (x + d * ux * 3.2 - px * 0.9, y + d * uy * 3.2 - py * 0.9)
            parts.append(_poly([tip, b1, b2], fill=FAINT, stroke="none"))
        return "".join(parts)

    def label(x, y, txt, size, rot=0):
        t = f'transform="rotate(-90 {x} {y})"' if rot else ""
        return _text(x, y, txt, size=size * fs, fill=INK, anchor="middle", extra=t)

    def face_label(x, y, txt):
        return _text(x, y, txt, size=8.0 * fs, fill=FAINT, family=SANS, anchor="middle",
                     extra='letter-spacing="0.12em"')

    # ---- mounting face (top view of the housing) ----
    L, Wd, Hh = l * s, w * s, h * s
    x0, y0 = mx, my
    ch = 3.0
    outline = [(x0 + ch, y0), (x0 + L - ch, y0), (x0 + L, y0 + ch), (x0 + L, y0 + Wd - ch), (x0 + L - ch, y0 + Wd),
               (x0 + ch, y0 + Wd), (x0, y0 + Wd - ch), (x0, y0 + ch)]
    o.append(_poly(outline, fill="#e8ecef", stroke=INK, **{"stroke-width": 1.45, "stroke-linejoin": "round"}))
    # the two M12 connectors seen edge-on on the back face
    for cx in (x0 + L / 2 - conn_spacing * s / 2, x0 + L / 2 + conn_spacing * s / 2):
        o.append(f'<rect x="{cx - 1.2}" y="{y0 - 2.2}" width="2.4" height="2.4" fill="#e8ecef" stroke="{INK}" stroke-width="0.7"/>')
    # mounting holes: three, pattern centred
    hx0, hx1 = x0 + (l - pattern_l) / 2 * s, x0 + (l + pattern_l) / 2 * s
    hy0, hy1 = y0 + (w - pattern_w) / 2 * s, y0 + (w + pattern_w) / 2 * s
    r = hole_d * s / 2
    for (cx, cy) in ((hx0, hy0), (hx1, hy0), (hx0, hy1)):
        o.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#fff" stroke="{INK}" stroke-width="0.7"/>')
    o.append(f'<circle cx="{hx1}" cy="{hy1}" r="{r * 0.7}" fill="{INK}"/>')
    # length dimensions above
    yd1, yd2 = y0 - 34.8, y0 - 19.6
    o.append(_line((x0, yd1 - 4.4), (x0, y0 - 2.9), **dim) + _line((x0 + L, yd1 - 4.4), (x0 + L, y0 - 2.9), **dim))
    o.append(arrow((x0, yd1), (x0 + L, yd1)))
    o.append(label(x0 + L / 2, yd1 - 2.4, fmt(l), 8.3))
    o.append(arrow((hx0, yd2), (hx1, yd2)))
    o.append(label(x0 + L / 2, yd2 - 2.4, fmt(pattern_l), 8.3))
    # width dimensions left
    xd1, xd2 = x0 - 23.3, x0 - 9.5
    o.append(_line((x0 - 27.6, y0), (x0 - 3, y0), **dim) + _line((x0 - 27.6, y0 + Wd), (x0 - 3, y0 + Wd), **dim))
    o.append(arrow((xd1, y0), (xd1, y0 + Wd)))
    o.append(label(xd1 - 3.5, y0 + Wd / 2, fmt(w), 8.3, rot=1))
    o.append(arrow((xd2, hy0), (xd2, hy1)))
    o.append(label(xd2 - 3.5, y0 + Wd / 2, fmt(pattern_w), 7.6, rot=1))
    # hole callout
    o.append(_line((hx0 + 0.6, hy1 + 1.2), (x0 + 6.5, y0 + Wd + 15), stroke=INK, **{"stroke-width": 0.5}))
    o.append(_text(x0 + 4.7, y0 + Wd + 17.9, f'3 × Ø {fmt(hole_d)} {labels["through"]}', size=7.3 * fs, fill=INK))
    o.append(face_label(x0 + L / 2, y0 + Wd + 35.5, labels["mounting_face"]))

    # ---- back ----
    bx0, by0 = bx, y0
    o.append(f'<rect x="{bx0}" y="{by0}" width="{L}" height="{Hh}" rx="1.4" fill="#e8ecef" stroke="{INK}" stroke-width="1.45"/>')
    o.append(_line((bx0, by0 + 1.4), (bx0 + L, by0 + 1.4), stroke=FAINT, **{"stroke-width": 0.65}))
    o.append(_line((bx0, by0 + Hh - 1.3), (bx0 + L, by0 + Hh - 1.3), stroke=FAINT, **{"stroke-width": 0.65}))
    c1 = bx0 + L * 0.42
    c2 = c1 + conn_spacing * s
    cy = by0 + Hh / 2
    for cx in (c1, c2):
        o.append(f'<circle cx="{cx}" cy="{cy}" r="2.1" fill="{INK}"/><circle cx="{cx}" cy="{cy}" r="1.1" fill="#6b7787"/>')
    for i in range(3):   # status LEDs
        for j in range(2):
            o.append(f'<circle cx="{c2 + 4.5 + j * 2.4}" cy="{cy - 2.4 + i * 2.4}" r="0.8" fill="none" stroke="{INK}" stroke-width="0.45"/>')
    o.append(f'<rect x="{bx0 + L - 13}" y="{cy - 4.2}" width="10.5" height="8.4" rx="1.1" fill="#fff" stroke="{INK}" stroke-width="0.7"/>')
    # connector spacing dimension
    o.append(_line((c1, by0 - 20.3), (c1, by0 + 2.5), **dim) + _line((c2, by0 - 20.3), (c2, by0 + 2.5), **dim))
    o.append(arrow((c1, by0 - 15.4), (c2, by0 - 15.4)))
    o.append(label((c1 + c2) / 2, by0 - 18.6, fmt(conn_spacing), 7.6))
    # height dimension
    o.append(_line((bx0 + L + 3, by0), (bx0 + L + 21, by0), **dim) + _line((bx0 + L + 3, by0 + Hh), (bx0 + L + 21, by0 + Hh), **dim))
    o.append(arrow((bx0 + L + 15, by0), (bx0 + L + 15, by0 + Hh)))
    o.append(label(bx0 + L + 22.5, by0 + Hh / 2, fmt(h), 8.3, rot=1))
    o.append(face_label(bx0 + L / 2, by0 + Hh + 16, labels["back"]))

    # ---- measuring face ----
    fy0 = by0 + 45.7
    o.append(f'<rect x="{bx0}" y="{fy0}" width="{L}" height="{Hh}" rx="1.4" fill="#e8ecef" stroke="{INK}" stroke-width="1.45"/>')
    o.append(_line((bx0, fy0 + 1.3), (bx0 + L, fy0 + 1.3), stroke=FAINT, **{"stroke-width": 0.65}))
    o.append(_line((bx0, fy0 + Hh - 1.4), (bx0 + L, fy0 + Hh - 1.4), stroke=FAINT, **{"stroke-width": 0.65}))
    fcy = fy0 + Hh / 2
    win = dict(fill=BLUE_PAPER, stroke=INK)
    if variant == "vrd":
        # small aperture, color camera lens, projector window, small aperture
        o.append(f'<rect x="{bx0 + 3.2}" y="{fcy - 4.2}" width="5" height="8.4" rx="2.2" fill="{BLUE_PAPER}" stroke="{INK}" stroke-width="0.6"/>')
        o.append(f'<rect x="{bx0 + 10.5}" y="{fcy - 5.6}" width="13" height="11.2" rx="1.2" fill="#f4f5f2" stroke="{INK}" stroke-width="0.6"/>')
        o.append(f'<circle cx="{bx0 + 17}" cy="{fcy}" r="4.3" fill="{BLUE_PAPER}" stroke="{INK}" stroke-width="0.6"/>')
        o.append(f'<circle cx="{bx0 + 17}" cy="{fcy}" r="2.2" fill="#f4f5f2" fill-opacity="0.85"/>')
        o.append(f'<rect x="{bx0 + 30}" y="{fcy - 4.2}" width="16" height="8.4" rx="1.6" fill="{BLUE_PAPER}" stroke="{INK}" stroke-width="0.6"/>')
        o.append(f'<rect x="{bx0 + L - 8.5}" y="{fcy - 4.2}" width="5" height="8.4" rx="2.2" fill="{BLUE_PAPER}" stroke="{INK}" stroke-width="0.6"/>')
    else:
        for wx in (bx0 + 6.5, bx0 + L - 22.5):
            o.append(f'<rect x="{wx - 1.6}" y="{fcy - 6}" width="19.2" height="12" rx="1.4" fill="#f4f5f2" stroke="{INK}" stroke-width="0.5"/>')
            o.append(f'<rect x="{wx}" y="{fcy - 4.4}" width="16" height="8.8" rx="1.6" fill="{BLUE_PAPER}" stroke="{INK}" stroke-width="0.6"/>')
    for (cx, cy2) in ((bx0 + 3.2, fy0 + 3.2), (bx0 + L - 3.2, fy0 + 3.2), (bx0 + 3.2, fy0 + Hh - 3.2), (bx0 + L - 3.2, fy0 + Hh - 3.2)):
        o.append(f'<circle cx="{cx}" cy="{cy2}" r="0.9" fill="{INK}"/>')
    yd = fy0 + Hh + 18.1
    o.append(_line((bx0, fy0 + Hh + 3), (bx0, yd + 2.5), **dim) + _line((bx0 + L, fy0 + Hh + 3), (bx0 + L, yd + 2.5), **dim))
    o.append(arrow((bx0, yd), (bx0 + L, yd)))
    o.append(label(bx0 + L / 2, yd - 3.3, fmt(l), 8.3))
    o.append(face_label(bx0 + L / 2, fy0 + Hh + 36.3, labels["measuring_face"]))
    o.append("</svg>")
    return "".join(o)


# ------------------------------------------- series pages: FOV cone diagrams
def _num(s) -> float:
    return float(str(s).replace("–", "-").replace(",", ".").strip())


def model_wd(m: dict) -> tuple[float, float, float]:
    """(near, optimum, far) working distance in mm of a models.json entry.

    `wd` is "62–63" or "on request"; when the range is not specified the near and far
    distances are the optimum ± half the measuring depth.
    """
    opt = _num(m["opt"])
    depth = _num(m["depth"])
    wd = str(m.get("wd", ""))
    if "–" in wd or "-" in wd:
        a, b = wd.replace("–", "-").split("-", 1)
        return _num(a), opt, _num(b)
    return opt - depth / 2, opt, opt + depth / 2


def model_fov(m: dict) -> tuple[float, float]:
    """(width, height) of the field of view at the optimum working distance, mm."""
    parts = [p.strip() for p in str(m["fov"]).replace("x", "×").split("×")]
    w = _num(parts[0])
    h = _num(parts[1]) if len(parts) > 1 else w
    return w, h


def fov_cone_svg(m: dict, W: float = 122.8, cone_h: float = 147.4, cx: float | None = None,
                 wd_size: float = 6.4, top: float = 12.0, bottom: float = 6.0,
                 wd_label: str = "WD", stack_gap: float = 8.0, uid: str | None = None) -> str:
    """Measuring volume of one model, to scale in angle and depth: the cone from the
    camera to the far plane, the near / optimum / far planes and the WD dimension.

    The far plane is `cone_h` pt below the apex; the plane widths follow the true
    cone angle (FOV / WD) and the depth axis recedes up-right in cabinet projection.
    """
    near, opt, far = model_wd(m)
    fw, fh = model_fov(m)
    cx = W / 2 + 6 if cx is None else cx
    ay = top                          # apex y
    uid = uid or m["model"].replace(" ", "_")
    DX, DY = 0.36, -0.21              # depth axis, per pt of plane height

    def y_of(wd): return ay + wd / far * cone_h
    def w_of(wd): return fw / opt * wd / far * cone_h
    def h_of(wd): return fh / opt * wd / far * cone_h

    def plane(wd):
        y, w, h = y_of(wd), w_of(wd), h_of(wd)
        fl, fr = (cx - w / 2, y), (cx + w / 2, y)
        bl, br = (fl[0] + DX * h, y + DY * h), (fr[0] + DX * h, y + DY * h)
        return fl, fr, br, bl

    H = top + cone_h + bottom
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H:.1f}" width="{W}pt" height="{H:.1f}pt" overflow="visible">',
         f'<defs><linearGradient id="cg{uid}" x1="0" y1="0" x2="0" y2="1">'
         f'<stop offset="0" stop-color="{BLUE_PAPER}" stop-opacity="0.07"/>'
         f'<stop offset="1" stop-color="{BLUE_PAPER}" stop-opacity="0.22"/></linearGradient></defs>']
    apex = (cx, ay)
    ffl, ffr, fbr, fbl = plane(far)
    # cone: back faces first, then the front face
    for tri in ((apex, fbl, fbr), (apex, fbl, ffl), (apex, ffr, fbr), (apex, ffl, ffr)):
        o.append(_poly(tri, fill=f"url(#cg{uid})", stroke=BLUE_PAPER, stroke_width=0.45, stroke_linejoin="round"))
    # measuring depth: box between the near and the far plane
    nfl, nfr, nbr, nbl = plane(near)
    box_style = dict(fill=BLUE_PAPER, fill_opacity=0.22, stroke=BLUE_PAPER, stroke_width=0.45, stroke_linejoin="round")
    o.append(_poly((nbl, nbr, fbr, fbl), **box_style))
    o.append(_poly((nfl, nbl, fbl, ffl), **box_style))
    o.append(_poly((nfr, nbr, fbr, ffr), **box_style))
    # far plane
    o.append(_poly((ffl, ffr, fbr, fbl), fill=BLUE_PAPER, fill_opacity=0.85, stroke=INK, stroke_width=0.74, stroke_linejoin="round"))
    o.append(_poly((nfl, nfr, ffr, ffl), **box_style))
    # optimum plane, striped along the depth axis
    ofl, ofr, obr, obl = plane(opt)
    o.append(f'<clipPath id="cp{uid}"><polygon points="{" ".join(f"{x:.2f},{y:.2f}" for x, y in (ofl, ofr, obr, obl))}"/></clipPath>')
    o.append(_poly((ofl, ofr, obr, obl), fill=BLUE_PAPER, fill_opacity=0.95))
    stripes = []
    x = ofl[0] - DX * h_of(opt) - 2
    while x < ofr[0] + 2:
        stripes.append(_line((x, ofl[1] + 1), (x + DX * (h_of(opt) + 2), ofl[1] + 1 + DY * (h_of(opt) + 2)), stroke=INK, stroke_width=0.55))
        x += 2.4
    o.append(f'<g clip-path="url(#cp{uid})">{"".join(stripes)}</g>')
    o.append(_poly((ofl, ofr, obr, obl), fill="none", stroke=INK, stroke_width=0.85, stroke_linejoin="round"))
    # near plane
    o.append(_poly((nfl, nfr, nbr, nbl), fill=BLUE_PAPER, fill_opacity=0.85, stroke=INK, stroke_width=0.74, stroke_linejoin="round"))
    # WD dimension at the left
    lx = ffl[0] - 5.1
    o.append(_line((lx, ay), (lx, ffl[1]), stroke=FAINT, stroke_width=0.57))
    o.append(f'<circle cx="{lx:.1f}" cy="{ay:.1f}" r="0.9" fill="{FAINT}"/>')
    o.append(_line((lx - 1.6, ffl[1]), (lx + 1.6, ffl[1]), stroke=FAINT, stroke_width=0.57))
    o.append(_text(lx - 3.6, ay + 1.9, wd_label, size=5.1, fill=FAINT, anchor="end"))
    span = ffl[1] - nfl[1]
    ranged = "–" in str(m.get("wd", "")) or "-" in str(m.get("wd", ""))
    if span > stack_gap and ranged:
        for wd in (near, opt, far):
            yy = y_of(wd)
            o.append(_line((lx, yy), (ffl[0] - 1.5, yy), stroke=FAINT, stroke_width=0.4))
            o.append(_text(lx - 3.6, yy + wd_size * 0.36, fmt_n(wd), size=wd_size, fill=INK, anchor="end"))
    else:
        yy = ofl[1]
        o.append(_line((lx, yy), (ofl[0] - 1.5, yy), stroke=FAINT, stroke_width=0.4))
        label = f"{fmt_n(near)}–{fmt_n(far)}" if ranged else fmt_n(opt)
        o.append(_text(lx - 3.6, yy + wd_size * 0.36, label, size=wd_size, fill=INK, anchor="end"))
    o.append("</svg>")
    return "".join(o)


def fmt_n(v: float) -> str:
    """A number without a trailing .0 (62.5 → '62.5', 63.0 → '63')."""
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s


# ---------------------------------------------- page 6/8: dimension drawings
_DIM = dict(stroke=FAINT, stroke_width=0.55)


def _arrow_defs(uid: str) -> str:
    return (f'<defs><marker id="as{uid}" viewBox="0 0 6 6" refX="0.5" refY="3" markerWidth="4" markerHeight="4" orient="auto-start-reverse" markerUnits="userSpaceOnUse">'
            f'<path d="M0,3 L6,1 L6,5 z" fill="{FAINT}"/></marker></defs>')


def _dim_h(x0, x1, y, label, uid, size=6.7, above=True, ext=None, color=INK) -> str:
    out = [f'<line x1="{x0:.1f}" y1="{y:.1f}" x2="{x1:.1f}" y2="{y:.1f}" stroke="{FAINT}" stroke-width="0.55" '
           f'marker-start="url(#as{uid})" marker-end="url(#as{uid})"/>']
    if ext:
        for x in (x0, x1):
            out.append(_line((x, ext[0]), (x, ext[1]), stroke=FAINT, stroke_width=0.4))
    ty = y - 2.6 if above else y + size + 1.2
    out.append(_text((x0 + x1) / 2, ty, label, size=size, fill=color, anchor="middle"))
    return "".join(out)


def _dim_v(x, y0, y1, label, uid, size=6.1, ext=None, dx=4.2) -> str:
    out = [f'<line x1="{x:.1f}" y1="{y0:.1f}" x2="{x:.1f}" y2="{y1:.1f}" stroke="{FAINT}" stroke-width="0.55" '
           f'marker-start="url(#as{uid})" marker-end="url(#as{uid})"/>']
    if ext:
        for y in (y0, y1):
            out.append(_line((ext[0], y), (ext[1], y), stroke=FAINT, stroke_width=0.4))
    cy = (y0 + y1) / 2
    out.append(_text(x + dx, cy, label, size=size, fill=INK, anchor="middle",
                     extra=f'transform="rotate(-90 {x + dx:.1f} {cy:.1f})" dominant-baseline="central"'))
    return "".join(out)


def _view_label(x, y, s, size=6.4) -> str:
    return _text(x, y, s, size=size, fill=FAINT, family=SANS, anchor="middle", extra='letter-spacing="0.9"')


def trs_dimensions_svg(dims: dict, labels: dict | None = None, W: float = 240, H: float = 132) -> str:
    """TRS front view and measuring face with the housing dimensions.

    dims: {"l": 230, "w": 230, "h": 250, "body_h": 186, "face": 144} (mm).
    """
    L, Hh, body, face = dims["l"], dims["h"], dims["body_h"], dims["face"]
    labels = labels or {}
    k = 79.9 / L                                    # pt per mm
    uid = "trs"
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}pt" height="{H}pt" overflow="visible">', _arrow_defs(uid)]
    # ---- front view
    x0, x1 = 11.6, 11.6 + L * k
    yb = 101.0                                      # housing bottom
    yt = yb - body * k                              # body top (under the top plate)
    ysh = yb - 20.6                                 # shoulder: the taper begins
    ytop = yb - Hh * k                              # top of the heat sink connector
    xm = (x0 + x1) / 2
    body_pts = [(x0, yt), (x1, yt), (x1, ysh), (x1 - 12.4, yb), (x0 + 12.4, yb), (x0, ysh)]
    o.append(_poly(body_pts, fill="#e8ecef", stroke=INK, stroke_width=1.1, stroke_linejoin="round"))
    # heat sink block with fins, connector on top, top plate
    hs_w, hs_h = 29.2, 21.1
    o.append(f'<rect x="{xm - hs_w / 2:.1f}" y="{yt - 1.1 - hs_h:.1f}" width="{hs_w:.1f}" height="{hs_h:.1f}" fill="#dbe1e6" stroke="{INK}" stroke-width="0.85"/>')
    for i in range(1, 10):
        xx = xm - hs_w / 2 + i * hs_w / 10
        o.append(_line((xx, yt - 1.1 - hs_h + 2), (xx, yt - 1.6), stroke=FAINT, stroke_width=0.4))
    o.append(f'<rect x="{xm + 3.5:.1f}" y="{ytop:.1f}" width="8" height="{yt - 1.1 - hs_h - ytop + 0.5:.1f}" rx="1" fill="#dbe1e6" stroke="{INK}" stroke-width="0.7"/>')
    o.append(f'<rect x="{x0 - 0.8:.1f}" y="{yt - 1.1:.1f}" width="{x1 - x0 + 1.6:.1f}" height="1.1" fill="#dbe1e6" stroke="{INK}" stroke-width="0.85"/>')
    # panel lines, band, side fins
    o.append(_line((x0, yt + 18.1), (x1, yt + 18.1), stroke=FAINT, stroke_width=0.55))
    o.append(_line((x0, ysh), (x1, ysh), stroke=INK, stroke_width=0.7))
    for xx in (x0 + 15, x1 - 15):
        o.append(_line((xx, yt + 1), (xx, ysh), stroke=FAINT, stroke_width=0.55))
    for i in range(5):
        for xx in (x0 + 2.5 + i * 2.5, x1 - 2.5 - i * 2.5):
            o.append(_line((xx, yt + 19.3), (xx, ysh - 1), stroke=FAINT, stroke_width=0.38))
    for i in range(1, 12):
        f = i / 12
        o.append(_line((x0 + f * (x1 - x0), ysh + 0.6), (x0 + 12.4 + f * (x1 - x0 - 24.8), yb - 0.6), stroke=FAINT, stroke_width=0.35))
    # dimensions
    o.append(_dim_v(x1 + 7.6, yt - 1.1, yb, str(body), uid, ext=(x1 + 1, x1 + 10)))
    o.append(_dim_v(x1 + 19.2, ytop, yb, str(Hh), uid, ext=(xm + 12, x1 + 21.5)))
    o.append(_dim_h(x0, x1, yb + 14.6, str(L), uid, ext=(yb + 2, yb + 18)))
    o.append(_view_label(xm, yb + 29.5, labels.get("front", "FRONT")))
    # ---- measuring face (plus-shaped heat sink around the 144 mm face)
    fx0, fy0 = 129.3, 17.7
    S = L * k
    fc = face * k
    a0 = (S - fc) / 2                               # arm offset
    cx_, cy_ = fx0 + S / 2, fy0 + S / 2
    plus = [(fx0 + a0, fy0), (fx0 + a0 + fc, fy0), (fx0 + a0 + fc, fy0 + a0), (fx0 + S, fy0 + a0), (fx0 + S, fy0 + a0 + fc),
            (fx0 + a0 + fc, fy0 + a0 + fc), (fx0 + a0 + fc, fy0 + S), (fx0 + a0, fy0 + S), (fx0 + a0, fy0 + a0 + fc),
            (fx0, fy0 + a0 + fc), (fx0, fy0 + a0), (fx0 + a0, fy0 + a0)]
    o.append(_poly(plus, fill="#e8ecef", stroke=INK, stroke_width=1.1, stroke_linejoin="round"))
    n = 9
    for i in range(1, n):
        f = i / n
        xx = fx0 + a0 + f * fc
        o.append(_line((xx, fy0 + 1.2), (xx, fy0 + a0 - 0.5), stroke=FAINT, stroke_width=0.4))
        o.append(_line((xx, fy0 + a0 + fc + 0.5), (xx, fy0 + S - 1.2), stroke=FAINT, stroke_width=0.4))
        yy = fy0 + a0 + f * fc
        o.append(_line((fx0 + 1.2, yy), (fx0 + a0 - 0.5, yy), stroke=FAINT, stroke_width=0.4))
        o.append(_line((fx0 + a0 + fc + 0.5, yy), (fx0 + S - 1.2, yy), stroke=FAINT, stroke_width=0.4))
    o.append(f'<rect x="{fx0 + a0:.1f}" y="{fy0 + a0:.1f}" width="{fc:.1f}" height="{fc:.1f}" fill="#dbe1e6" stroke="{INK}" stroke-width="0.73"/>')
    o.append(f'<rect x="{fx0 + a0 + 4:.1f}" y="{fy0 + a0 + 4:.1f}" width="{fc - 8:.1f}" height="{fc - 8:.1f}" rx="1.5" fill="#e8ecef" stroke="{INK}" stroke-width="0.85"/>')
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        o.append(f'<circle cx="{cx_ + sx * (fc / 2 - 6):.1f}" cy="{cy_ + sy * (fc / 2 - 6):.1f}" r="0.8" fill="none" stroke="{FAINT}" stroke-width="0.4"/>')
    # cross-shaped projector carrier, four projection windows, central camera lens
    arm, aw = 13.5, 6.4
    o.append(f'<rect x="{cx_ - aw / 2:.1f}" y="{cy_ - arm - aw / 2:.1f}" width="{aw}" height="{2 * arm + aw:.1f}" rx="1" fill="#dbe1e6" stroke="{INK}" stroke-width="0.5"/>')
    o.append(f'<rect x="{cx_ - arm - aw / 2:.1f}" y="{cy_ - aw / 2:.1f}" width="{2 * arm + aw:.1f}" height="{aw}" rx="1" fill="#dbe1e6" stroke="{INK}" stroke-width="0.5"/>')
    for dx, dy in ((0, -arm), (0, arm), (-arm, 0), (arm, 0)):
        o.append(f'<rect x="{cx_ + dx - 2.4:.1f}" y="{cy_ + dy - 2.4:.1f}" width="4.8" height="4.8" rx="0.8" fill="{BLUE_PAPER}" stroke="{INK}" stroke-width="0.5"/>')
    o.append(f'<circle cx="{cx_:.1f}" cy="{cy_:.1f}" r="5.2" fill="{BLUE_PAPER}" stroke="{INK}" stroke-width="0.6"/>')
    o.append(f'<circle cx="{cx_:.1f}" cy="{cy_:.1f}" r="2.6" fill="#ffffff" stroke="{INK}" stroke-width="0.4"/>')
    o.append(_dim_h(fx0 + a0, fx0 + a0 + fc, fy0 + S + 14.5, str(face), uid, ext=(fy0 + S + 2, fy0 + S + 18)))
    o.append(_dim_v(fx0 + S + 7.5, fy0 + a0, fy0 + a0 + fc, str(face), uid, ext=(fx0 + S + 1, fx0 + S + 10)))
    o.append(_view_label(cx_, fy0 + S + 29.5, labels.get("face", "MEASURING FACE")))
    o.append("</svg>")
    return "".join(o)


def vrh9_dimensions_svg(dims: dict, labels: dict | None = None, W: float = 240, H: float = 160) -> str:
    """VRH9 housing: mounting face, back and measuring face with dimensions.

    dims: {"l": 190, "w": 140, "h": 60, "pattern_l": 180, "pattern_w": 130, "hole_d": 6.2} (mm).
    """
    L, Wd, Hh = dims["l"], dims["w"], dims["h"]
    pl, pw, hd = dims["pattern_l"], dims["pattern_w"], dims["hole_d"]
    labels = labels or {}
    k = 58.1 / L
    uid = "vrh9"
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}pt" height="{H}pt" overflow="visible">', _arrow_defs(uid)]
    # ---- mounting face
    x0, y0 = 45.0, 52.5
    w, h = L * k, Wd * k
    o.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{w:.1f}" height="{h:.1f}" rx="3" fill="#e8ecef" stroke="{INK}" stroke-width="1.4"/>')
    ox, oy = (L - pl) / 2 * k, (Wd - pw) / 2 * k
    holes = [(x0 + ox, y0 + oy), (x0 + ox, y0 + h - oy), (x0 + w - ox, y0 + h - oy)]
    for hx, hy in holes:
        o.append(f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="{hd / 2 * k:.2f}" fill="#ffffff" stroke="{INK}" stroke-width="0.6"/>')
    o.append(f'<circle cx="{x0 + w - ox:.1f}" cy="{y0 + oy:.1f}" r="0.7" fill="none" stroke="{FAINT}" stroke-width="0.4"/>')
    for i in (1, 2):
        o.append(f'<rect x="{x0 + w:.1f}" y="{y0 + 3.5 + i * 4.2:.1f}" width="2.4" height="1.6" fill="#dbe1e6" stroke="{INK}" stroke-width="0.5"/>')
    for f in (0.25, 0.5, 0.75):
        for yy in (y0 + 1.6, y0 + h - 1.6):
            o.append(f'<circle cx="{x0 + f * w:.1f}" cy="{yy:.1f}" r="0.5" fill="{FAINT}"/>')
    o.append(_dim_h(x0, x0 + w, y0 - 34.9, str(L), uid, size=8.3, ext=(y0 - 39.3, y0 - 3)))
    o.append(_dim_h(x0 + ox, x0 + w - ox, y0 - 19.7, str(pl), uid, size=8.3, ext=(y0 - 24, y0 - 3)))
    o.append(_dim_v(x0 - 23.3, y0, y0 + h, str(Wd), uid, size=8.3, ext=(x0 - 27.6, x0 - 3), dx=-4.5))
    o.append(_dim_v(x0 - 9.5, y0 + oy, y0 + h - oy, str(pw), uid, size=7.6, ext=(x0 - 13, x0 - 3), dx=-4.2))
    hx, hy = holes[1]
    o.append(_line((hx + 1.5, hy + 1.5), (hx + 6, hy + 10), stroke=FAINT, stroke_width=0.5))
    o.append(_text(hx + 4.5, hy + 19.5, f"3 × Ø {fmt_n(hd)} {labels.get('through', 'through')}", size=7.3, fill=INK))
    o.append(_view_label(x0 + w / 2, y0 + 78.5, labels.get("mounting", "MOUNTING FACE"), size=8))
    # ---- back
    bx, by = 150.3, 52.5
    bh = Hh * k
    o.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{w:.1f}" height="{bh:.1f}" rx="1.6" fill="#e8ecef" stroke="{INK}" stroke-width="1.4"/>')
    o.append(_line((bx, by + 1.6), (bx + w, by + 1.6), stroke=FAINT, stroke_width=0.6))
    o.append(_line((bx, by + bh - 1.6), (bx + w, by + bh - 1.6), stroke=FAINT, stroke_width=0.6))
    o.append(f'<rect x="{bx + w - 18:.1f}" y="{by + 3.4:.1f}" width="13" height="{bh - 6.8:.1f}" rx="1.4" fill="#e8ecef" stroke="{INK}" stroke-width="0.9"/>')
    o.append(_dim_v(bx + w + 7.6, by, by + bh, str(Hh), uid, size=8.3, ext=(bx + w + 1, bx + w + 10), dx=5.5))
    o.append(_view_label(bx + w / 2, by + 34.5, labels.get("back", "BACK"), size=8))
    # ---- measuring face
    mx, my = 150.3, 101.7
    o.append(f'<rect x="{mx:.1f}" y="{my:.1f}" width="{w:.1f}" height="{bh:.1f}" rx="1.6" fill="#e8ecef" stroke="{INK}" stroke-width="1.4"/>')
    o.append(_line((mx, my + 1.6), (mx + w, my + 1.6), stroke=FAINT, stroke_width=0.6))
    o.append(_line((mx, my + bh - 1.6), (mx + w, my + bh - 1.6), stroke=FAINT, stroke_width=0.6))
    o.append(f'<rect x="{mx + 7:.1f}" y="{my + 3.6:.1f}" width="13" height="11" rx="2" fill="#dbe1e6" stroke="{INK}" stroke-width="0.9"/>')
    o.append(f'<rect x="{mx + 9.2:.1f}" y="{my + 5.6:.1f}" width="8.6" height="7" rx="1.2" fill="{BLUE_PAPER}" stroke="{INK}" stroke-width="0.5"/>')
    o.append(f'<rect x="{mx + 29.9:.1f}" y="{my + 3.6:.1f}" width="22" height="11" rx="2" fill="#dbe1e6" stroke="{INK}" stroke-width="0.9"/>')
    o.append(f'<rect x="{mx + 32.2:.1f}" y="{my + 5.6:.1f}" width="17.4" height="7" rx="1.2" fill="{BLUE_PAPER}" stroke="{INK}" stroke-width="0.5"/>')
    for sx in (mx + 3, mx + w - 3):
        for sy in (my + 3.2, my + bh - 3.2):
            o.append(f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="0.6" fill="{FAINT}"/>')
    o.append(_dim_h(mx, mx + w, my + 36.5, str(L), uid, size=8.3, ext=(my + bh + 2, my + 40)))
    o.append(_view_label(mx + w / 2, my + 56.5, labels.get("face", "MEASURING FACE"), size=8))
    o.append("</svg>")
    return "".join(o)


# ------------------------------------------- page 22: reference-plate method
def plate_method_svg(img_href: str, W: float = 261, H: float = 196) -> str:
    """The Z-repeatability method: a camera over the ceramic reference plate at the near,
    optimum and far working distance; nine regions per plate with the A / B areas."""
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}pt" height="{H}pt">',
           '<defs><linearGradient id="pm-beam" x1="0" y1="0" x2="0" y2="1">'
           '<stop offset="0" stop-color="#3d5afe" stop-opacity="0.40"/>'
           '<stop offset="1" stop-color="#3d5afe" stop-opacity="0.06"/></linearGradient></defs>']
    cam_w, cam_h = 66, 66 * 747 / 900
    cam_x, cam_y = 100, 20
    apex = (cam_x + cam_w * 0.42, cam_y + cam_h * 0.90)
    # plates: (y centre, width, depth, skew, fill, opacity)
    plates = [(121, 102, 18, 8, "#a9aeb8", 0.72), (153, 130, 24, 10, "#c3c7cf", 0.82), (183, 156, 27, 12, "#eef0f3", 1.0)]
    cx = 149

    def quad(yc, w, dpt, sk):
        return [(cx - w / 2 + sk, yc - dpt / 2), (cx + w / 2 + sk, yc - dpt / 2),
                (cx + w / 2 - sk, yc + dpt / 2), (cx - w / 2 - sk, yc + dpt / 2)]

    far = quad(*plates[-1][:4])
    # beam to the far plate, drawn under the plates
    out.append(_poly([apex, far[0], far[1]], fill="url(#pm-beam)"))
    out.append(_poly([apex, far[3], far[2]], fill="url(#pm-beam)"))
    out.append(_poly([apex, far[0], far[3]], fill="#3d5afe", fill_opacity="0.10"))
    out.append(_poly([apex, far[1], far[2]], fill="#3d5afe", fill_opacity="0.10"))
    for c in far:
        out.append(_line(apex, c, stroke="#9fb0ff", stroke_width=0.45, stroke_opacity=0.8))
    for yc, w, dpt, sk, fill, op in plates:
        q = quad(yc, w, dpt, sk)
        out.append(_poly(q, fill=fill, fill_opacity=op))
        # 3 × 3 grid
        for i in (1, 2):
            f = i / 3
            a = (q[0][0] + (q[1][0] - q[0][0]) * f, q[0][1])
            b = (q[3][0] + (q[2][0] - q[3][0]) * f, q[3][1])
            out.append(_line(a, b, stroke="#7d8593", stroke_width=0.35, stroke_opacity=0.7))
            a = (q[0][0] + (q[3][0] - q[0][0]) * f, q[0][1] + (q[3][1] - q[0][1]) * f)
            b = (q[1][0] + (q[2][0] - q[1][0]) * f, q[1][1] + (q[2][1] - q[1][1]) * f)
            out.append(_line(a, b, stroke="#7d8593", stroke_width=0.35, stroke_opacity=0.7))
        # A / B areas in the centre region
        bw, bh = w * 0.045, dpt * 0.10
        out.append(f'<rect x="{cx - bw - 0.6:.1f}" y="{yc - bh / 2:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="{BLUE_PAPER}"/>')
        out.append(f'<rect x="{cx + 0.6:.1f}" y="{yc - bh / 2:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="{GREEN_PAPER}"/>')
    out.append(camera_image(img_href, cx=cam_x + cam_w / 2, y_top=cam_y, width=cam_w, aspect=900 / 747))
    out.append("</svg>")
    return "".join(out)


def plate_plan_svg(label_a: str = "A", label_b: str = "B", W: float = 119.1, H: float = 74.6) -> str:
    """Plan view of the reference plate: nine regions, A and B adjacent in each."""
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}pt" height="{H}pt">',
           f'<rect x="0.45" y="0.45" width="{W - 0.9:.1f}" height="{H - 0.9:.1f}" fill="#ecedf1" stroke="{INK}" stroke-width="0.85"/>']
    for i in (1, 2):
        x = W * i / 3
        y = H * i / 3
        out.append(_line((x, 0.9), (x, H - 0.9), stroke="#6a7786", stroke_width=0.6, stroke_dasharray="2.2 1.6"))
        out.append(_line((0.9, y), (W - 0.9, y), stroke="#6a7786", stroke_width=0.6, stroke_dasharray="2.2 1.6"))
    bw, bh = 6.2, 5.6
    for r in range(3):
        for c in range(3):
            x = W * (c + 0.5) / 3
            y = H * (r + 0.5) / 3
            centre = r == 1 and c == 1
            fa, fb = (BLUE_PAPER, GREEN_PAPER) if centre else ("#c3c7cf", "#c3c7cf")
            out.append(f'<rect x="{x - bw - 0.4:.1f}" y="{y - bh / 2 + (1.6 if centre else 0):.1f}" width="{bw}" height="{bh}" fill="{fa}"/>')
            out.append(f'<rect x="{x + 0.4:.1f}" y="{y - bh / 2 + (1.6 if centre else 0):.1f}" width="{bw}" height="{bh}" fill="{fb}"/>')
            if centre:
                out.append(_text(x - 3.6, y - 3.4, label_a, size=6.2, fill=BLUE_PAPER, anchor="middle", weight=600))
                out.append(_text(x + 3.6, y - 3.4, label_b, size=6.2, fill=GREEN_PAPER, anchor="middle", weight=600))
    out.append("</svg>")
    return "".join(out)
