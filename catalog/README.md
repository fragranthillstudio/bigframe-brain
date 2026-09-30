# Bigframe Product Catalog 2026 — build

Code-built pages for the English product catalog. This first revision corrects the
**PRS series** (model PRS-2500B): specification, dimensions, renderings and every
figure that quotes them.

## What is here

| Path | Role |
| --- | --- |
| `data/models.json` | **Single source of truth** for the pages built here: the PRS specification, the 18-model table, the series cards and the large-scene comparison. Change a number here and every table, chart, frustum and caption follows. |
| `data/PRS_spec_2026-09-30.xlsx` | The engineering sheet the PRS figures were taken from (right-hand column). |
| `source/…RevC.pdf` | The Rev. C catalog as designed; pages not rebuilt here are carried over unchanged. |
| `src/catalog.css` | Page stylesheet in pt, measured from the Rev. C pages: 612 × 858.96 pt, 51 pt margins, IBM Plex Sans / Mono, Bodoni Moda titles, Big Frame colour tokens. |
| `src/templates/` | Jinja2 templates for the rebuilt pages: `p02` range overview, `p13` PRS series page, `p14` PRS field of view and dimensions, `p17` all models, `p20` PRS technical data. |
| `build/figures.py` | Figures generated from the data: the FOV frustum scenes (planes to scale), the pallet use case, the measuring-face and end-view drawings, the FOV-vs-WD chart, the range scatter and the QR code. |
| `build/build.py` | Renders the templates, prints them with headless Chromium, swaps the PRS render into the cover composite and assembles the final PDF. |
| `assets/prs-2500b.png` | PRS render, blue-plate colourway (from the supplied rendering PDF), background removed. `prs-2500b-black-plate.png` is the WebP colourway, kept as an alternative. |
| `output/` | The assembled catalog and the individual rebuilt pages. |

## Build

```bash
pip install pymupdf jinja2 pillow playwright qrcode
python3 build/build.py          # from catalog/
```

`CHROMIUM_PATH` overrides the Chromium binary (defaults to the Playwright install in
`/opt/pw-browsers`). Playwright's `page.pdf` takes inches: 8.5 × 11.93 in is the
catalog's 612 × 858.96 pt page.

## PRS-2500B — what changed against Rev. C

| Figure | Rev. C (wrong) | Now |
| --- | --- | --- |
| Working distance near / optimum / far | 1500 / 2500 / 4000 mm | **1200 / 2500 / 3500 mm** |
| Field of view near / optimum / far | 1339 × 1251 / 2236 × 2090 / 3582 × 3349 | **1300 × 1050 / 2560 × 2060 / 3600 × 2907** |
| XY point spacing | 643 / 1074 / 1721 µm | **680 / 1400 / 2000 µm** |
| Measuring depth | 2500 mm | **2300 mm** |
| Z repeatability | 250 µm | **300 µm** |
| Stereo baseline | 800 mm | **approx. 300 mm** |
| Model code | PRS-2500 | **PRS-2500B** |
| Housing, weight, sensor, interface, power, laser, temperature | unchanged | 890 × 97.5 × 95 mm, 3.9 kg, 2 × 5 MP (2448 × 2048), GigE, 24 V / 4 A, 638 nm, 0–45 °C |

Pages touched: cover (render only), 2, 13, 14, 17, 20. All other pages are the Rev. C
originals. The footer still reads *EN 2026-10 · Rev. C*; bump it in `data/models.json`
(`catalog.footer`) when the revision letter is decided — the carried-over pages would
then need the same footer patch.

## Open points to confirm with engineering

1. **Baseline vs. housing.** The sheet gives a stereo baseline of ~300 mm, but the render
   shows camera windows at both ends of the 890 mm bar. The drawings therefore show the
   housing without a baseline dimension; the baseline is stated in the tables only.
2. **Plate colour.** The rendering PDF shows the cobalt-blue plate (the CMF of every other
   series); the WebP shows a black plate. The blue one is used everywhere.
3. **Points per frame** for the PRS is still "on request".
