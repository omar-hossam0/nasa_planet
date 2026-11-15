# Selection state and event contract (Member 5 → Member 6)

The map UI never lets another module read the DOM. It exposes one state object
and two events.

## State

`window.TDState` is replaced (never mutated in place) on every meaningful
change:

```json
{
  "lang": "ar | en",
  "regionId": "nile_corridor | morocco_comparison | sahel_comparison",
  "variableId": "air_temperature | soil_moisture | precipitation | vegetation_greenness",
  "period": { "start": "YYYY-MM", "end": "YYYY-MM" },
  "aoi": { "w": 30.5, "s": 29, "e": 32, "n": 31 } | null,
  "jobId": "job_…" | null,
  "resultState": "succeeded | insufficient_data | null"
}
```

`aoi` is the normalized bounding box of whatever the user drew or typed; it is
converted to a GeoJSON polygon only at request time, so both input paths produce
the same canonical hash.

## Events

| Event | Detail | When |
|---|---|---|
| `td:statechange` | the state object above | any selection change, after a result arrives |
| `td:result` | `result.payload` exactly as returned by `/v1/analyses/{id}/result` | after a successful analysis |

```js
window.addEventListener('td:statechange', (e) => console.log(e.detail));
window.addEventListener('td:result', (e) => renderSidePanel(e.detail));
```

## URL parameters (for the demo checklist and for automated checks)

| Parameter | Meaning |
|---|---|
| `lang=ar\|en` | start in that language |
| `region=<region_id>` | preselect the window |
| `variable=<variable_id>` | preselect the variable |
| `start=YYYY-MM`, `end=YYYY-MM` | preselect the period |
| `aoi=w,s,e,n` | preselect a bounding box |
| `autorun=1` | run one analysis immediately |

Example:
`/app/?lang=en&region=sahel_comparison&variable=vegetation_greenness&autorun=1`

## Rules the integration must keep

1. **Numbers come from the API.** The UI prints `slope_per_year`, `ci_low`,
   `ci_high`, `p_value` and `counts.*` verbatim (formatted only). It never
   recomputes a statistic.
2. **Missing is not zero.** Cells without a slope are drawn with the "no data"
   pattern and excluded from the colour scale.
3. **One palette per variable.** `PALETTES` in `app.js` maps temperature,
   soil moisture, precipitation and NDVI to different colour ramps; NDVI never
   inherits the temperature ramp.
4. **Insufficient data is a banner, not a hidden result.** The card shows
   dashes and the reason; the map keeps showing the window's spatial product
   because that product is valid for the full period.
5. **FDR is stated, not implied.** The header prints `q`, the family size and
   the eligible-cell count; significant cells are outlined.
