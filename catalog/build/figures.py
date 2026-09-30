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
def use_case_svg(prs: dict, img_href: str, W: float = 283, H: float = 200) -> str:
    opt = prs["by_wd"][1]
    far = prs["by_wd"][-1]
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
    out.append(camera_image(img_href, cx=apex[0] + 5, y_top=apex[1] - 36, width=140, aspect=2.2))
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
