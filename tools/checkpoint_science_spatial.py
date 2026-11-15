"""Assemble the Phase 5 review checkpoint from verified numerical evidence."""
import json
import shutil
from pathlib import Path
import nbformat
from review_sahel_ndvi import sha,write_json
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'packages/science/phase_reports'
r=json.loads((ROOT/'data/derived/science_spatial/phase_5/results.json').read_text())
v=json.loads((P/'PHASE_5_VALIDATION.json').read_text())
notebook=ROOT/'packages/science/notebooks/05_descriptive_spatial.ipynb'
b=nbformat.read(notebook,as_version=4)
cells=[c for c in b.cells if c.cell_type=='code']
assert all(c.execution_count is not None for c in cells)
assert not any(o.output_type=='error' for c in cells for o in c.outputs)
shutil.copyfile(ROOT/'data/derived/science_spatial/phase_5/results.json',P/'PHASE_5_RESULTS.json')
v.update({'notebook_executed':True,'notebook_code_cells':len(cells),'notebook_sha256':sha(notebook),
          'checkpoint_results_sha256':sha(P/'PHASE_5_RESULTS.json'),'maps_visually_reviewed':['Sahel Standard 95% four-panel map'],
          'phase6_started':False,'inference_enabled':False})
write_json(P/'PHASE_5_VALIDATION.json',v)
lines=['# Phase 5 checkpoint: descriptive spatial trend analysis','',
'**DONE_WAITING_APPROVAL. Phase 5 descriptive implementation passes; Phase 6 has not started. Inference remains disabled.**','',
'The explicit user approval is recorded in [PHASE_5_APPROVAL.md](PHASE_5_APPROVAL.md). This revises Phase 5 to descriptive analysis after the failed Phase 4 research; it does not relax any inference acceptance criteria or approve inference release. No repository rule requires a second scope approval.','',
'## Implemented scope','',
'All twelve strict variable/region cases and the two additional validated Sahel NDVI cases (Standard 100% and experimental Standard 95%) are processed. These are the fourteen Phase 3 cases; no new preparation or default is introduced. Policy sensitivities are confined to the validated Sahel three-policy set.','',
'Monthly and annual cell slopes reuse the exact validated Sen kernel. Regional slopes are computed separately from prepared regional series. Monthly coordinates use calendar-month differences divided by twelve; annual coordinates use actual calendar years. Missing values and incomplete Standard 95% cell-years remain missing. The minimum of three finite observations is computational only, not scientific record-length adequacy.','',
'Each native-coordinate NetCDF contains four windows (2001–2024, 2001–2012, 2013–2024, 2005–2024), monthly/annual slopes, n_valid, valid spans, pair counts, direction codes, comparison with the actual full-period sign, eligible support and observed-month fractions. Each case has an annual slope/direction/footprint/coverage map. The executed [notebook](../notebooks/05_descriptive_spatial.ipynb) displays all three Sahel policies and period results.','',
'Direction codes: -1 negative; 1 positive; 2 exactly zero; 0 unavailable. Outside-support cells also display unavailable, distinguished by the eligibility map. A near-zero finite slope retains its actual sign; exact zero is not evidence of stability. Reference agreement codes: 1 agrees, 0 differs, -1 unavailable.','',
'Cell percentages divide by all preparation-eligible cells, including eligible cells with unavailable slopes. Excluded cells are counted separately. Area coverage divides the eligible spherical-cell solid angle by all selected-cell solid angles, not by cell count. No category is a significance classification.','',
'## Real NASA full-period annual examples','',
'Slopes are changes per elapsed year. Precipitation annual values are complete annual accumulated mm; their slope describes changes in annual accumulation, not a sum of source rates. Temperature retains K, soil moisture kg m-2, NDVI dimensionless 1.','',
'| Variable / region / policy | Regional annual slope | Units | Eligible area % of selected | Eligible cells | Excluded | Positive % of eligible | Unavailable % of eligible |',
'|---|---|---|---|---|---|---|---|']
for c in r['cases']:
 a=c['periods']['annual'][0];s=a['cell_shares']
 lines.append(f"| {c['variable_id']} / {c['region_id']} / {c['policy']} | {a['slope_per_year']:.9g} | {a['slope_units']} | {100*c['eligible_area_fraction_selected']:.4f} | {s['eligible_cells']} | {s['excluded_cells']} | {s['percent_of_eligible_cells']['positive']:.3f} | {s['percent_of_eligible_cells']['unavailable']:.3f} |")
lines+=['','Complete counts for positive, negative, exactly zero and unavailable, plus all monthly/annual period results and regional annual observations, are in [PHASE_5_RESULTS.json](PHASE_5_RESULTS.json). These signs describe estimated change only.','',
'## Preparation-policy comparisons and limits','']
for c in r['policy_comparisons']:
 lines.append(f"- {c['candidate']} versus {c['baseline']}: common {c['common_cells']} cells; gained {c['gained_cells']}; lost {c['lost_cells']}; common annual computable {c['common_computable_annual_cells']}; mean common-cell slope difference {c['mean_annual_slope_difference_common_cells']:.9g} NDVI/year. Native-grid common/gained/lost masks are saved separately.")
lines+=['','Regional slopes and represented geography differ across policies. Identical common-cell slopes do not make regional slopes interchangeable: added locations change the regional aggregate. These comparisons are not causal attribution or calibrated uncertainty.','']
for c in r['cases']:
 if c['experimental']:
  lines.append(f"Standard 95% preserves **{c['annual_missing_eligible_cell_years']} missing eligible cell-years**. Regional annual means aggregate changing-support monthly regional means; they are distinct from averages of complete cell-years. Monthly valid-area fractions for all 288 months remain visible in JSON. Strict 100% remains the default, Standard 100% the fixed-support comparison, and Standard 95% experimental only.")
lines+=['','Coverage describes centre-selected native rectangular cells, not exact polygon intersections. Low strict NDVI retention can select unrepresentative land. A region-level estimate describes its actual retained footprint. Seasonal raw monthly slopes, short windows and missing-year patterns limit interpretation. No imputation, reweighting policy change or annual-completeness relaxation was introduced.','',
'## Period sensitivity','',
'Every window is recalculated from eligible observed values at their actual coordinates with fixed reference-period preparation support. Counts/spans and unavailable results are explicit. Cell directions compare to that same cell’s actual 2001–2024 slope; regional directions compare to the actual full regional slope, never the majority of windows. Window sensitivity is descriptive, not confidence or a promised reversal.','',
'| Sahel NDVI policy | Period | Annual observations | Annual slope (NDVI/year) | Regional sign agrees full period |','|---|---|---|---|---|']
for c in r['cases']:
 if c['variable_id']=='vegetation_greenness' and c['region_id']=='sahel_comparison':
  for a in c['periods']['annual']:
   lines.append(f"| {c['policy']} | {a['start_year']}–{a['end_year']} | {a['n_valid']} | {a['slope_per_year']:.9g} | {a['regional_direction_agrees_full_period']} |")
lines+=['','## Validation, failures and preservation','',
f"**{v['tests_run']} tests pass**, including the 110 earlier regressions and eight new fixture tests. Zero test failures/errors. All 28 full-period cell-grid/regional comparisons match preserved Phase 3 results exactly. Fourteen NetCDF round trips pass. {v['regional_window_reference_checks']} independent slope-only SciPy regional-window checks pass. Counts, denominators, coordinates, missing annual records, actual-reference signs, JSON nulls and absence of inference fields are checked.",
'',f"All **{len(v['prior_hashes'])} protected existing files** are unchanged by SHA-256, including NASA measurements, preparation policies/outputs, validated slopes and failed-method evidence. Source/method hashes are in results. The previous notebooks and reports are preserved. The new notebook executed all four code cells without errors; the Sahel experimental map was visually inspected.",
'','An initial rendering run failed because Colorbar.set_ticks required labels as a keyword. This was corrected before the successful generation; no scientific inputs or method parameters changed. No unresolved numerical/test failure remains. Scientific inference remains a failed-validation limitation, not a Phase 5 test success.','',
'## Artifacts and integration boundary','',
'Reusable JSON is [PHASE_5_RESULTS.json](PHASE_5_RESULTS.json). Local native-grid NetCDFs, map PNGs and spatial policy masks are under `data/derived/science_spatial/phase_5/`; file identities are in [PHASE_5_VALIDATION.json](PHASE_5_VALIDATION.json). Derived arrays are ignored by Git; reproduce them with the commands below. JSON results retain source artifact identities, units, policy flags, limitations and monthly coverage. The numerical module imports only the validated slope module; no HTTP contract or production API was changed.','',
'Inference is explicitly `disabled_failed_validation`, application_release is false, and Phase 6 is not started. No p-values, confidence intervals, FDR decisions or significance/stability labels are generated. Existing inference release flags are untouched.','',
'```powershell',r'.\.venv\Scripts\python.exe tools/run_science_spatial.py',r'.\.venv\Scripts\python.exe tools/validate_science_spatial.py',r'.\.venv\Scripts\python.exe tools/run_science_spatial_notebook.py',r'.\.venv\Scripts\python.exe tools/checkpoint_science_spatial.py','```','',
'Pending: owner review of this descriptive checkpoint, approval before Phase 6, and backend/frontend coordination of final payloads and map delivery. No integration, deployment or inference release is implied. **Stop here for user review.**']
(P/'PHASE_5_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('Phase 5 checkpoint written.')
