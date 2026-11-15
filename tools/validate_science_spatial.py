"""Independent artifact accounting, fixture regression and notebook checkpoint."""
import json
import sys
import unittest
from pathlib import Path
import numpy as np
import xarray as xr
from scipy.stats.mstats import sen_seasonal_slopes
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/science'))
from review_sahel_ndvi import sha,write_json
from run_science_trends import assert_no_inference,load_cases,load_prepared
from src.spatial_descriptive import shares
P=ROOT/'packages/science/phase_reports/PHASE_5_VALIDATION.json'
v=json.loads(P.read_text());r=json.loads((ROOT/'data/derived/science_spatial/phase_5/results.json').read_text())
for p,h in {**v['prior_hashes'],**v['artifacts']}.items():assert sha(ROOT/p)==h,p
assert_no_inference(r)
checks=0
for case,row in zip(load_cases(),r['cases']):
 ds=load_prepared(case)
 with xr.open_dataset(ROOT/row['grid_artifact']) as grid:
  xr.testing.assert_equal(grid.lat,ds.lat);xr.testing.assert_equal(grid.lon,ds.lon)
  for frequency in ['monthly','annual']:
   for j,period in enumerate(row['periods'][frequency]):
    values=grid[frequency+'_slope'].isel(window=j)
    assert shares(values,ds.eligible_support)==period['cell_shares']
    assert sum(period['cell_shares']['counts'].values())==period['cell_shares']['eligible_cells']
    start,end=period['start_year'],period['end_year']
    series=ds['regional_'+frequency]
    years=series.time.dt.year if frequency=='monthly' else series.year
    series=series.where((years>=start)&(years<=end),drop=True)
    # Independent regular-row reference preserves missing positions; annual
    # windows are consecutive year coordinates, monthly rows are original months.
    ref=sen_seasonal_slopes(np.ma.masked_invalid(series.values[:,None])).intra_slope[0]
    np.testing.assert_allclose(period['slope_per_year'],float(ref)*(12 if frequency=='monthly' else 1),atol=1e-10)
    checks+=1
    refgrid=grid[frequency+'_slope'].isel(window=0)
    expected=xr.where(values.notnull() & refgrid.notnull(),np.sign(values)==np.sign(refgrid),-1)
    np.testing.assert_array_equal(grid[frequency+'_direction_agrees_full_period'].isel(window=j),expected)
 assert row['annual_missing_eligible_cell_years']==int((ds.cell_annual.isnull() & ds.eligible_support.astype(bool)).sum())
suite=unittest.defaultTestLoader.discover(str(ROOT/'packages/science/tests'))
run=unittest.TextTestRunner(verbosity=1).run(suite)
v.update({'status':'passed' if run.wasSuccessful() else 'failed','tests_run':run.testsRun,
 'failures':len(run.failures),'errors':len(run.errors),'skipped':len(run.skipped),
 'regional_window_reference_checks':checks,'counts_coordinates_reference_signs_verified':True,
 'json_nulls_and_no_inference_fields_verified':True,
 'tested_limitations':['minimum 3 finite values is computational only','no calibrated uncertainty or significance',
 'coverage/preparation selection may bias spatial representation','raw monthly seasonality retained'],
 'initial_implementation_failure':'Colorbar.set_ticks positional labels error; corrected to labels keyword before successful run'})
write_json(P,v)
if not run.wasSuccessful():raise SystemExit(1)
