# Role 05 — Spatial UX

Status: **DELIVERED** (14 November 2026, 21:00 Egypt time)
Served at `/app/` by the backend · no build step, no external tiles, no API key.

Mission from `docs/architecture/PLAN.md`: own window selection, AOI drawing,
variable browser, native-grid layers, legends, evidence cards and bilingual
layout. Show loaded boundaries and coverage. Do not imply neighbourhood
precision by visual interpolation.

## Deliverables

| Deliverable | Path | Status | Evidence |
|---|---|---|---|
| Responsive map flow | `web/index.html`, `web/app.js`, `web/style.css` | DONE | 3-column layout, collapses to one column under 1150 px |
| Native-grid cell layer | `app.js` `drawMap()` | DONE | cells drawn from `/v1/spatial`, no interpolation |
| AOI drawing | pointer drag + numeric W/S/E/N inputs | DONE | same canonical request from both paths |
| Variable browser | `app.js` `renderVariables()` | DONE | units + product id per entry, readiness from the catalog |
| Per-product legends | `app.js` `PALETTES` | DONE | temperature, soil moisture, precipitation, NDVI each own ramp |
| Bilingual layout | `app.js` `I18N` | DONE | AR (RTL) and EN (LTR), same numbers and source ids |
| Loading / error / insufficient states | overlay + banner | DONE | insufficient is a banner so the map stays readable |
| Basemap-independent | canvas background + graticule + attribution | DONE | works with zero network tiles |
| Keyboard access | native inputs, buttons, focus rings, `aria-*` | DONE | numeric AOI path is fully keyboard operable |
| State/event contract | `web/STATE_CONTRACT.md` | DONE | `window.TDState`, `td:statechange`, `td:result` |
| Visual evidence | `docs/screenshots/01…04` | DONE | AR temperature + AOI, AR NDVI, EN precipitation, AR insufficient |

## What was verified, and how

Rendered with headless Chromium (Playwright 1.65) against the real API:

| Screenshot | Check |
|---|---|
| `01_ar_temperature_aoi.png` | AR RTL, dashed AOI over cells, card switches to the 12-cell subset (+0.0280 K/yr vs +0.0309 full window) |
| `02_ar_ndvi_sahel.png` | NDVI uses a brown→green ramp, 20,000 cells, 11,640 FDR cells with subtle outlines |
| `03_en_precipitation_morocco.png` | EN LTR, yellow→blue precipitation ramp, mm/hr per year, mixed-sign Spin It rows |
| `04_ar_insufficient_data.png` | warning banner, card shows dashes, no slope invented |

Defects found and fixed during verification (worth recording):

1. **Canvas text was mangled in RTL.** Chromium applied Arabic digit shaping,
   turning `24.0°` into a single Arabic-Indic glyph. Fixed with
   `ctx.direction = 'ltr'`.
2. **Legend flipped in RTL**, so colours did not match the labels. Fixed with
   `direction: ltr` on the legend bar.
3. **Shrinking feedback loop**: the canvas measured its own wrapper, which was
   sized by the canvas. Fixed by measuring the panel.
4. **Insufficient data covered the whole map.** Now a banner, so the valid
   spatial product stays visible while the card states the rule.
5. **Colour scale washed out** by a few extreme cells in NDVI; now clipped at
   the 95th percentile with the maximum noted in the legend tooltip.

## Acceptance statement

> A new user can choose an area/variable, inspect a real result and identify its
> main limitation.

Verified by walking that path in the screenshots: pick a window chip → pick a
variable → press Analyse → the card shows slope, interval, p-value, coverage and
the product limitations, and the banner/card states the coverage rule when it is
not met. NDVI and precipitation do not inherit temperature labels or colours.

## Handoffs

- **Member 6:** read `window.TDState` and listen to `td:statechange` /
  `td:result`; do not scrape the DOM. Use `?autorun=1` for the demo preset.
- **Member 3:** the page is served from `/app/` by the same process, so the
  demo is one command.
- **Member 4:** citations arrive from the explanation endpoint and are rendered
  as a source list with page numbers and authority labels.

## Open items

1. **No basemap tiles by design.** Coastlines are not drawn; the graticule and
   cell grid carry the geography. Adding a tile layer would need an offline
   tile pack or a network dependency the demo cannot rely on.
2. **Bounded aspect stretch (max 1.35:1)** for tall windows. The graticule keeps
   true coordinates, but the map is not an equal-area projection; this is stated
   in the code comment, not hidden.
3. **Touch pinch-zoom is not implemented.** The window fills the canvas; no
   zoom/pan, so no false impression of street-level resolution.
4. **No automated browser test suite** beyond the screenshot walk-through;
   the four screenshots are the record of the states exercised.
