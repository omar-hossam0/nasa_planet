# Role 06 — Integration, release checks and presentation

Status: **DELIVERED** (14 November 2026, 21:45 Egypt time)
Software **m3-1.0.0** · method **m2-1.0.0** · explanation schema **m4-1.0.0**

Mission from `docs/architecture/PLAN.md`: own time series, Spin It, Reality
Check, region comparison, receipt export and end-to-end integration. Coordinate
early integration instead of collecting last-minute bugs. Reserve presentation
time and build the real-data path before decorative animation.

## Deliverables

| Deliverable | Path | Status | Evidence |
|---|---|---|---|
| Monthly time series | `GET /v1/analyses/{id}/series` + chart in `web/app.js` | DONE | 288 months, server-computed trend line |
| Spin It | card section (11 frozen windows) | DONE | sign-agreement fraction shown as descriptive |
| Reality Check | card section + `realityCheck()` | DONE | expectation vs sign/significance, no probability language |
| Region comparison | `POST /v1/compare` + table | DONE | same variable/period/method; native-grid caveat printed |
| Receipt export | `/v1/receipts/{id}` + download buttons | DONE | 13/13 fields, 288 granules, no secrets |
| Result + CSV export | `exportResult()`, `exportCsv()` | DONE | JSON reopens, CSV 288 rows |
| Reproducible demo preset | URL parameters + `warm_cache.py` | DONE | one URL reproduces the stage state |
| Offline build | `tools/export_offline.py` → `dist/offline/` | DONE | 12 analyses, 12 maps, 2.75 MB, runs from `file://` |
| Recorded fallback | offline snapshot + banner | DONE | screenshot `docs/screenshots/05_offline.png` |
| Release checks | `tools/acceptance_check.py` → `docs/acceptance_report.json` | DONE | **15/15 pass** |
| Presentation | `docs/DEMO_SCRIPT.md` | DONE | 90-second script with timings and forbidden claims |
| `app_available` sign-off | `docs/architecture/scope.v2.json` | DONE | 12/12 entries, signed by Member 6 |

## Release checks actually run

```
python tools/acceptance_check.py
```

| Check | Observed |
|---|---|
| readiness 12 pairs | 12/12 measurement+method ready |
| revisions exposed | data `09a11b7f41bd`, method `m2-1.0.0` |
| analysis succeeds | job `job_f0706db4604448cb` → succeeded |
| slope present | +0.03086 K/yr |
| receipt complete | 13/13 fields, 288 granules |
| receipt has no secrets | no credential-like keys |
| citations resolve | 2 citations, all in the retrieved set |
| explanation validated | path `deterministic` |
| LLM disabled falls back | deterministic answer served |
| chart matches card | +0.030859 == +0.030859 |
| compare matches card | +0.030859 == +0.030859 |
| units present | every ready entry |
| export reopens | JSON reopens, CSV 288 rows |
| offline bundle complete | 12 analyses, 12 spatial products |
| offline matches live | snapshot slope equals live slope |

## Defects found during integration (and fixed)

1. **A failed job was permanent.** Resubmitting the same canonical request
   returned the failed job forever, so the "resubmit to retry" message was a
   lie. Now a failed job is requeued, and stale result/receipt rows from the
   earlier attempt are removed first (a retried job must not inherit them).
2. **Worker died on a transient SQLite lock** (`attempt to write a readonly
   database`) when two processes shared the database. Claiming now retries with
   backoff instead of killing the worker.
3. **Series endpoint returned no trend line** because it was called without
   `with_trend`; the chart would have shown a flat line.
4. **Compare note arrived in English** inside the Arabic UI; localised.

## Acceptance statement

> Verify readiness, citations, units, numeric consistency, export reopening and
> behaviour with network/LLM disabled.

All six are covered by the table above, and the offline check is the
network-disabled case. `app_available` was flipped to `true` only after this
report existed.

## Handoffs / what is left to a human

- **Rehearse the script twice** with a timer; the numbers are stable but the
  pacing is not automatic.
- **Record a 90-second screen capture** as a second fallback (the offline
  folder is the first).
- **Upload the submission materials** (video link, repo URL, team details) to
  the official portal — not something this repository can do.
- **Source credits** are in `README.md`; verify they appear in the video
  description.

## Open items

1. **No automated browser test.** The UI was verified with headless Chromium
   screenshots of four states plus the offline build; there is no Playwright
   test suite in the repo.
2. **No recorded video yet.** The script and the offline build are ready; the
   recording is a human task.
3. **Comparison is slope-only by default** (`with_ci=false`); intervals per
   region would triple the wait.
4. **The offline snapshot covers the full-period presets only.** A custom
   period or AOI needs the server.
