"""Phase 5 descriptive-only artifacts; never invokes an inference method."""
import json
import sys
from pathlib import Path
import numpy as np
import xarray as xr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'packages/science'))
from src.spatial_descriptive import analyze_window
from run_science_trends import load_cases, load_prepared, assert_no_inference
from research_berger_boos import protected_inputs
from review_sahel_ndvi import sha, write_json

OUT = ROOT/'data/derived/science_spatial/phase_5'
REPORTS = ROOT/'packages/science/phase_reports'
WINDOWS = [(2001, 2024), (2001, 2012), (2013, 2024), (2005, 2024)]


def numbers(a):
    return [float(v) if np.isfinite(v) else None for v in a]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    before = protected_inputs()
    # The older preservation helper also scans prior scientific outputs. Our
    # new outputs live in a separate directory to preserve all old manifests.
    prior = json.loads((REPORTS/'PHASE_3_RESULTS.json').read_text())
    results, artifacts, references = [], {}, 0
    supports, annual_slopes = {}, {}
    for case in load_cases():
        print(case['key'], flush=True)
        ds = load_prepared(case)
        support = ds.eligible_support.astype(bool)
        eligible = support.values
        weights = ds.native_cell_solid_angle
        row = {k: case[k] for k in ['key', 'variable_id', 'region_id', 'policy', 'experimental']}
        row.update({'prepared_source': case['record'], 'inference_status': 'disabled_failed_validation',
                    'estimated_change_only': True, 'periods': {},
                    'eligible_area_fraction_selected': float(weights.where(support, 0).sum()/weights.sum()),
                    'annual_years': ds.year.values.tolist(), 'regional_annual': numbers(ds.regional_annual.values),
                    'annual_units': ds.cell_annual.attrs['units'],
                    'annual_missing_eligible_cell_years': int((ds.cell_annual.isnull() & support).sum()),
                    'monthly_dates': ds.time.values.astype('datetime64[M]').astype(str).tolist(),
                    'monthly_valid_area_fraction_selected': numbers((weights.where(ds.cell_monthly.notnull() & support, 0).sum(('lat','lon'))/weights.sum()).values),
                    'annual_definition': 'changing-support monthly-regional annual mean; incomplete cell-years remain missing' if case['experimental'] else 'complete annual records on fixed preparation support'})
        output = xr.Dataset({'eligible_support': support.astype('int8'), 'native_cell_solid_angle': weights})
        full = {}
        for frequency in ['monthly', 'annual']:
            records, grids = [], []
            for start, end in WINDOWS:
                grid, record = analyze_window(ds['cell_'+frequency], ds['regional_'+frequency], support,
                                             frequency, start, end, full.get(frequency))
                if (start, end) == WINDOWS[0]:
                    full[frequency] = grid
                    old = next(x for x in prior['cases'] if x['case'] == case['key'])
                    with xr.open_dataset(ROOT/old['grid_artifact']) as existing:
                        np.testing.assert_allclose(grid.slope, existing[frequency+'_slope'], rtol=0, atol=0, equal_nan=True)
                        xr.testing.assert_equal(grid.lat, existing.lat)
                        xr.testing.assert_equal(grid.lon, existing.lon)
                    assert record['slope_per_year'] == old['regional'][frequency]['slope_per_year']
                    references += 1
                    grid['direction_agrees_full_period'] = xr.where(grid.slope.notnull(), 1, -1).astype('int8')
                reference = records[0]['slope_per_year'] if records else record['slope_per_year']
                record['regional_direction_agrees_full_period'] = (bool(np.sign(record['slope_per_year']) == np.sign(reference))
                    if record['slope_per_year'] is not None and reference is not None else None)
                records.append(record)
                grids.append(grid.expand_dims(window=[f'{start}_{end}']))
            row['periods'][frequency] = records
            merged = xr.concat(grids, dim='window')
            output = xr.merge([output, merged.rename({v: frequency+'_'+v for v in merged.data_vars})])
        observed = ds.cell_monthly.notnull() & support
        output['monthly_observed_fraction'] = observed.sum('time')/ds.sizes['time']
        output.attrs.update({'method': 'exact descriptive Theil-Sen; min_points=3 computational guard only',
            'policy': case['policy'], 'experimental': int(case['experimental']),
            'source_prepared_sha256': case['record']['artifact_sha256'],
            'inference_status': 'disabled_failed_validation', 'estimated_change_only': 1,
            'time_units': 'calendar-month ordinal difference / 12; actual annual-year differences',
            'limitations': 'No demonstrated significance, stability or causation; fixed eligibility across windows; missing observations not filled'})
        target = OUT/(case['key']+'.nc')
        output.to_netcdf(target)
        with xr.open_dataset(target) as reopened:
            xr.testing.assert_allclose(output, reopened)
        artifacts[target.relative_to(ROOT).as_posix()] = sha(target)
        row['grid_artifact'] = target.relative_to(ROOT).as_posix()
        fig, axes = plt.subplots(1, 4, figsize=(16, 3.6), layout='constrained')
        fields = [full['annual'].slope, full['annual'].direction, support, output.monthly_observed_fraction]
        labels = ['Annual Sen slope ('+ds.cell_annual.attrs['units']+'/year)', 'Descriptive direction', 'Preparation-eligible footprint', 'Observed months / 288']
        for i, (ax, data, label) in enumerate(zip(axes, fields, labels)):
            kwargs = {}
            if i == 0:
                bound = max(float(abs(data).max()), 1e-12)
                kwargs = {'cmap': 'RdBu_r', 'vmin': -bound, 'vmax': bound}
            elif i == 1:
                kwargs = {'cmap': ListedColormap(['#366cac','#cccccc','#bd513c','#e3c55c']),
                          'norm': BoundaryNorm([-1.5,-.5,.5,1.5,2.5],4)}
            else:
                kwargs = {'vmin': 0, 'vmax': 1, 'cmap': 'viridis'}
            im = ax.pcolormesh(ds.lon, ds.lat, data, shading='auto', **kwargs)
            bar = fig.colorbar(im, ax=ax, shrink=.75)
            if i == 1:
                bar.set_ticks([-1,0,1,2], labels=['Negative','Unavailable','Positive','Exactly zero'])
            ax.set(title=label, xlabel='Longitude', ylabel='Latitude', facecolor='#dddddd')
        fig.suptitle(case['key']+' | 2001-2024 | Estimated change only; inference disabled', fontsize=10)
        image = OUT/(case['key']+'.png');fig.savefig(image, dpi=120);plt.close(fig)
        artifacts[image.relative_to(ROOT).as_posix()] = sha(image)
        row['map_artifact'] = image.relative_to(ROOT).as_posix()
        results.append(row)
        if case['region_id'] == 'sahel_comparison' and case['variable_id'] == 'vegetation_greenness':
            supports[case['policy']] = support
            annual_slopes[case['policy']] = full['annual'].slope
    comparisons = []
    for baseline, candidate in [('strict_100', 'standard_100'), ('standard_100', 'standard_95')]:
        a, b = supports[baseline], supports[candidate]
        xr.testing.assert_equal(a.lat, b.lat);xr.testing.assert_equal(a.lon, b.lon)
        common = a & b
        diff = annual_slopes[candidate]-annual_slopes[baseline]
        valid = common & diff.notnull()
        comparison = {'baseline': baseline, 'candidate': candidate, 'common_cells': int(common.sum()),
            'gained_cells': int((b & ~a).sum()), 'lost_cells': int((a & ~b).sum()),
            'common_computable_annual_cells': int(valid.sum()),
            'mean_annual_slope_difference_common_cells': float(diff.where(valid).mean()) if valid.any() else None,
            'interpretation': 'different supports are not interchangeable; regional differences combine location selection and preparation'}
        loc = xr.Dataset({'common_support': common.astype('int8'), 'gained_support': (b & ~a).astype('int8'),
            'lost_support': (a & ~b).astype('int8'), 'annual_slope_difference_common': diff.where(valid)})
        loc.annual_slope_difference_common.attrs['units'] = 'NDVI per year'
        p = OUT/f'{candidate}_vs_{baseline}.nc';loc.to_netcdf(p)
        comparison['location_artifact'] = p.relative_to(ROOT).as_posix();artifacts[comparison['location_artifact']] = sha(p)
        comparisons.append(comparison)
    result = {'revision': 'descriptive-spatial-1', 'cases': results, 'policy_comparisons': comparisons,
        'windows': WINDOWS, 'inference_status': 'disabled_failed_validation', 'application_release': False,
        'default_policy': 'strict_100', 'phase6_started': False,
        'limitations': ['Estimated change is not statistically demonstrated change', 'Three points is computability only',
                        'Raw monthly slopes retain seasonality', 'Window signs and policy spreads are descriptive, not uncertainty intervals'],
        'source_method_sha256': {p: sha(ROOT/p) for p in ['packages/science/src/trend_estimation.py',
            'packages/science/src/spatial_descriptive.py','packages/science/config/preparation_policy.json','tools/run_science_spatial.py']}}
    assert_no_inference(result)
    write_json(OUT/'results.json', result)
    artifacts[(OUT/'results.json').relative_to(ROOT).as_posix()] = sha(OUT/'results.json')
    for p, h in before.items():
        assert sha(ROOT/p) == h, p
    write_json(REPORTS/'PHASE_5_VALIDATION.json', {'status': 'numerical_checks_passed_tests_pending',
        'full_period_phase3_equalities': references, 'native_grid_roundtrips': len(results),
        'prior_hashes': before, 'prior_files_unchanged': True, 'artifacts': artifacts,
        'inference_enabled': False, 'default_changed': False, 'phase6_started': False})
    print('PASS', len(results), 'cases;', references, 'Phase 3 equalities', flush=True)


if __name__ == '__main__':
    main()
