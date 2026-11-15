# AstraVerd React product

This is the new landing page and analysis workspace. The previous static UI
remains at `/app/`; the backend root serves the React build at `/product/`.

The landing hero, three story chapters, and investigation console share an
astrobotany observatory art direction. Small canvas sprite characters remain anchored to the planting section and chart card; scroll changes their animation frames. The three explanatory sections use the reference layout with a split map/setup panel, period slider, and evidence receipt flowing into the Earth-horizon closing section.
The
hero image is decorative. All headings, methods, numbers, and results are
React elements. On a phone, a right swipe on the hero opens the investigation,
and the investigation has a fixed four-stage navigator.

The name AstraVerd is a provisional design name. The NASA data and analysis
retain their existing scientific labels and provenance.

## Implemented design

The three landing chapters now use a shared expedition landscape, a geographic
observatory preview, the period illustration, and a light evidence receipt.
The dashboard has a setup rail, geographic trend map and time series, and a
light evidence panel. `product-theme.css` owns this visual layer.
`GeoBackdrop.tsx` draws a locally bundled NASA Blue Marble image with Natural
Earth country outlines. The analysis canvas remains georeferenced to the
returned bounding box, with unchanged scientific values. See
`public/MAP_SOURCES.md` for asset provenance. The background is static context,
not current satellite observations. The stored data still covers the three
configured study regions; the visual design does not add global analysis.

## Develop

```powershell
cd frontend
npm ci
npm run dev
```

Vite proxies `/v1` to the FastAPI backend at `127.0.0.1:8000`.

## Build and serve

```powershell
cd frontend
npm run build
cd ..
python backend/run.py
```

Open `http://127.0.0.1:8000/`. The root redirects to `/product/`.

## Offline demo

The build includes `offline_data.js`, a precomputed snapshot. With Node.js
installed, run `dist/product/START_OFFLINE.cmd` on Windows or
`node dist/product/serve-offline.cjs` elsewhere. Open the printed URL.
Offline mode supports the 12 predefined variable-region analyses over the full
2001–2024 period. Custom dates and AOIs require the backend. The interface
labels offline results as precomputed and does not invent missing analyses.

## Scientific boundaries

The hero art and landing illustrations are conceptual. Analysis numbers,
series, sensitivity windows, spatial significance and explanations come from
the existing API or its frozen offline snapshot. The spatial layer is the
full-period reference product, even when an analysis uses another time window.
The UI copies statistics; it never computes a new trend or p-value.
