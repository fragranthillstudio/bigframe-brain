# Rebuilding a Rev. C page in code — working rules

You are reproducing one or more pages of the Bigframe Product Catalog 2026 (English, Rev. C)
as Jinja2 templates so the catalog can be built in any language. Fidelity to the designed
page is the goal: a reader comparing the Rev. C page with your rendered page should see the
same layout, type, colours and figures. Improve only what is clearly a defect.

## Where things are (all paths relative to `catalog/`)

| Path | What |
| --- | --- |
| `reference/pages/pNN.png` | The Rev. C page rendered at 110 dpi. **Look at it first.** 1 pt = 1.528 px in this image. |
| `reference/pages/pNN.json` | Every text span (bbox in pt, font, size, colour, text), every filled/stroked rect, every image placement with its extracted file. Use it for exact positions and sizes. |
| `assets/pages/pNN_imgXXX.png` | The page's images, extracted with alpha where the PDF had it. Reference them from templates as `../../assets/pages/…`. |
| `src/catalog.css` | The stylesheet. Reuse its classes (`.tab`, `.footer`, `h1.title`, `.card`, `.panel-dark`, `.stats/.stat`, `table.data`, `table.spec`, `table.kv`, `.cta`, `.badge`, `.note`, `.caption`, `.fig-label`). Add page-specific rules in a `{% block head %}<style>…</style>{% endblock %}` inside your template, not in catalog.css. |
| `src/templates/base.html` | Header tab + footer. Extend it. Pages with a dark hero use the right-hand tab: see `p13.html`. |
| `src/templates/p13.html`, `p14.html`, `p20.html`, `p02.html`, `p17.html` | Finished examples of the conventions (they still hold inline English; they are being converted to strings in parallel). |
| `build/figures.py` | SVG generators (QR code, drawings, charts, scenes). Add a generator there if a page needs a data-driven figure (e.g. FOV cone diagrams on series pages). |
| `data/models.json` | All product figures. **Never type a number that exists in the data**; loop over `models`, `series_cards`, `prs`, etc. Add structured data there if a page needs it (e.g. per-series spec tables for p18/p19, accessories for p21) — keep the JSON valid and keep existing keys. |
| `data/i18n/en.json` | All strings, keyed by page: `"p05": {"title": "…", …}` plus `"common"`. |

## Page geometry

- Page: 612 × 858.96 pt, margins 51 pt (content 51 → 561 pt). Use **pt units** in CSS, absolute positioning for major blocks (`class="abs" style="left:51pt; top:90pt; width:…"`), normal flow inside.
- Header tab at top 27 pt; footer spectrum rule at 811.5 pt — both come from `base.html`.
- Fonts: IBM Plex Sans (text), IBM Plex Mono (data, labels, tracked eyebrows), Bodoni Moda (page titles only). Sizes in the JSON are exact; copy them.
- Colours: ink `#2d3748`, muted `#5b6675`, paper `#f4f5f2`, deep `#111827`, lime `#c8ff3d`, rules `#d9dcd6` / `#c4c9c2`. Use the CSS variables.

## Strings (i18n)

- Every human-readable string goes into `data/i18n/en.json` under your page key and is used as `{{ t.key }}` (page strings) or `{{ c.key }}` (common strings: footer, "Page", "NEW", "Preliminary specification…" etc. — add to `common` if the same string appears on several pages).
- Keys: short snake_case (`title`, `lede`, `stat1_label`, `table_h_model`, `caption_fig1`). Keep the English text exactly as the Rev. C page has it (fix only typos).
- Strings may contain simple inline HTML (`<b>`, `<br>`, `<sup>1</sup>`) — templates output them with `|safe`.
- Numbers from data render through filters: `{{ value|n }}` (decimal separator localised), `{{ mm|m }}` (mm → m short, e.g. 2500 → 2.5), `{{ mm|m2 }}` (two decimals). A text string that embeds a data figure is composed in the template, not hard-coded in the JSON (e.g. `{{ t.stat1_desc_prefix }} {{ prs.wd.near|m }} m`).
- German will be ~25 % longer: leave sensible slack in text boxes (don't rely on a paragraph ending exactly at a fixed height); prefer widths from the JSON but flow heights.

## Verify before you finish

```bash
cd catalog
python3 build/build.py --pages NN            # renders output/pages/en/pNN.pdf and pNN.png
```
Open `output/pages/en/pNN.png` next to `reference/pages/pNN.png` and compare. The build prints a WARNING if the page overflows its width — that must be fixed. Check: nothing clipped, nothing overlapping, all figures present, footer page number right.

## Don't

- Don't edit pages you were not assigned; don't change `catalog.css` classes other pages rely on (append new rules only if truly shared and say so).
- Don't paste base64 images; reference files.
- Don't invent content. If a reference figure is an illustration you cannot reconstruct (e.g. a photo), use the extracted image file.
