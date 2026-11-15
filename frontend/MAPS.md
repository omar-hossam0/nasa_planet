# Interactive study map

`src/RegionMap.tsx` uses Leaflet and OpenStreetMap raster tiles, without an API key.
The map is available before running an analysis. Region boundaries come from the
catalog, filtered to the selected variable, rather than hard-coded geographic areas.

- Click a study rectangle to select its region. The configuration rail stays in sync.
- Use **All regions** to see every available study region.
- Navigation is free: pan and zoom outside study regions for geographic context.
  The map initially fits every configured study region. **All regions** and
  **Selected region** change the view without imposing navigation boundaries.
  Geographic exploration never permits analysis outside the server allowlist.
- Use **Select area**, then click two opposite corners inside the selected region.
  This also works by tapping on touchscreens. The rectangle is sent to the existing
  analysis API as a WGS84 bbox, in west/south/east/north order.
- **Use full region** clears the custom area. Areas below 0.25 degrees on either
  axis are rejected to match the current backend minimum.
- Outside-region selections are rejected; the world basemap does not imply
  global scientific coverage. The backend remains the final availability validator.
- Backend analysis and availability checks enforce strict bbox containment,
  including tiny excursions outside any edge, unregistered regions, unsupported
  region-variable pairs and dates outside regional coverage. Region aliases resolve only to
  existing configured regions. In-flight responses are ignored if the user
  changes region, variable, period or area before they finish.
- Returned slope cells appear above the basemap at their geographic coordinates;
  they remain explicitly synthetic when the backend is in mock mode.

Default tiles: https://tile.openstreetmap.org/{z}/{x}/{y}.png
Visible OpenStreetMap attribution must remain on the map. Standard browser caching
is used, and there is no tile prefetch, bulk download or offline tile caching.
The background requires connectivity; region outlines and selection remain usable
if tiles fail. The existing scientific offline snapshot is independent of map tiles.

Configure `VITE_MAP_TILE_URL` and `VITE_MAP_ATTRIBUTION` before building to switch
providers. The public OSM service is best effort, has no SLA, and is subject to its
[tile usage policy](https://operations.osmfoundation.org/policies/tiles/). Evaluate
a suitable provider or self-hosted tiles for production traffic; free map data does
not imply unlimited free hosting. Basemap requests disclose the viewed tile area
and the browser's normal request metadata to the provider.

Leaflet: https://leafletjs.com/reference-1.9.4.html

## Adding regions

The active backend's region allowlist is `backend/config/regions.json`. Each entry
declares a unique `region_id`, names, bbox, aliases, coverage dates and
`supported_variable_ids`. Restart API and workers after editing it. A different
server-owned file can be selected with `REGIONS_FILE`; clients cannot change it.
Duplicate IDs/aliases, unknown variables and invalid coordinates fail startup.

The frontend fetches `/v1/catalog/regions`; map shapes, configuration choices,
labels and region comparisons derive from that response. No TypeScript region
enum or fixed three-region comparison list needs updating. A registered region
must also support the selected variable before an analysis can be submitted.

Registration enables only the current explicitly synthetic demo workflow. Real
science still requires corresponding NASA inputs, provenance and scientific
validation. Adding a rectangle does not create those datasets or approve them.
The registry content is hashed into revisions so cached results from a previous
configuration are not reused after a change.
