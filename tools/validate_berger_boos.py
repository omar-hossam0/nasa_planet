"""Check saved record-level evidence, scientific arithmetic and preservation."""
import json
import sys
import unittest
from pathlib import Path

import numpy as np
from scipy.stats import theilslopes

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'packages/science'))
from src.berger_boos import berger_boos, research_geometry
from src.inference import wilson_interval
from review_sahel_ndvi import sha, write_json
from research_berger_boos import aggregate, passes_screen

REPORTS = ROOT/'packages/science/phase_reports'
path = REPORTS/'PHASE_4_BERGER_BOOS_RESEARCH.json'
r = json.loads(path.read_text())
c = r['config']
for p, h in {**r['prior_hashes'], **r['identity'], **r['artifacts']}.items():
    assert sha(ROOT/p) == h, p
protocol = ROOT/'data/derived/science_inference/berger_boos/protocol_before_evaluation.json'
assert sha(protocol) == r['protocol_sha256']
before = json.loads(protocol.read_text())
for field in ['config', 'acceptance_unchanged', 'identity', 'prior_hashes']:
    assert before[field] == r[field], field
assert c['alpha'] == .05 and c['gamma'] == .005
assert np.isclose(c['simple_null_alpha'], c['alpha']-c['gamma'], rtol=0, atol=1e-15)
assert len(r['rows']) == 792 and len(r['nuisance']) == 88
assert r['unique_validation_noise_records'] == 176000
assert r['calibration_records'] == 2399760
assert r['paired_record_evaluations'] == 1584000
references, max_error, checked = 0, 0., 0
for n in c['lengths']:
    for cache in range(c['cache_realizations']):
        base = ROOT/'data/derived/science_inference/berger_boos'
        with np.load(base/f'cache_n{n}_{cache}.npz') as z:
            lr, pivot = z['lr'], z['pivot']
        for model in c['models']:
            with np.load(base/f'panel_n{n}_{cache}_{model["name"]}.npz') as z:
                # Recompute the complete new candidate from saved noise/caches;
                # old comparators keep their historical implementation unchanged.
                out = berger_boos(z['noise'], research_geometry(n, c['rho_grid']), lr, pivot)
                np.testing.assert_array_equal(out['members'], z['members'])
                np.testing.assert_allclose(out['p'], z['sen_berger_boos_0.0_p'])
                np.testing.assert_allclose(out['radius'], z['sen_berger_boos_0.0_radius'])
                for index in range(3):
                    reference = theilslopes(z['noise'][index], np.arange(n)).slope
                    max_error = max(max_error, abs(reference-z['sen_noise'][index]))
                    np.testing.assert_allclose(reference, z['sen_noise'][index], atol=1e-12)
                    references += 1
                diag = next(d for d in r['nuisance'] if (d['n'], d['cache'], d['model'])
                            == (n, cache, model['name']))
                np.testing.assert_allclose(diag['per_rho_inclusion_rate'], z['members'].mean(0))
                for row in r['rows']:
                    if (row['n'], row['cache'], row['model']) != (n, cache, model['name']):
                        continue
                    method, truth = row['method'], row['truth']
                    p, radius = z[f'{method}_{truth}_p'], z[f'{method}_{truth}_radius']
                    rejected = int((p <= c['alpha']).sum())
                    covered = int((abs(z['sen_noise']) <= radius).sum())
                    assert row['rejected'] == rejected and row['covered'] == covered
                    assert row['rejection_rate'] == rejected/row['trials']
                    assert row['coverage'] == covered/row['trials']
                    assert row['passes_screen'] == passes_screen(row, r['acceptance_unchanged'])
                    np.testing.assert_allclose(row['rejection_mc95'], wilson_interval(rejected, row['trials']))
                    checked += 1
assert checked == 792
assert aggregate(r['rows'], ['n', 'method', 'model', 'phi', 'truth'],
                 ['coverage', 'rejection_rate', 'mean_interval_width']) == r['aggregate']
assert aggregate(r['nuisance'], ['n', 'model', 'phi', 'core'],
                 ['exclusion_rate', 'mean_set_size', 'mean_set_span', 'upper_boundary_inclusion']) == r['nuisance_aggregate']
assert not r['application_release'] and not r['phase5_started']
assert r['numerical_failures'] == 0
assert all(x['p_interval_disagreements'] == 0 for x in r['rows'] if x['method'] == 'sen_berger_boos')
suite = unittest.defaultTestLoader.discover(str(ROOT/'packages/science/tests'))
run = unittest.TextTestRunner(verbosity=1).run(suite)
write_json(REPORTS/'PHASE_4_BERGER_BOOS_TESTS.json', {
    'tests_run': run.testsRun, 'passed': run.wasSuccessful(), 'errors': len(run.errors),
    'failures': len(run.failures), 'skipped': len(run.skipped),
    'research_sha256': sha(path), 'protocol_before_evaluation_verified': True,
    'prior_hashes_unchanged': True, 'protected_file_count': len(r['prior_hashes']),
    'saved_evidence_files_verified': len(r['artifacts']),
    'record_level_summaries_verified': checked, 'scipy_sen_references': references,
    'scipy_max_absolute_slope_error': max_error, 'accounting_verified': True,
    'application_release': False, 'phase5_started': False})
if not run.wasSuccessful():
    raise SystemExit(1)
