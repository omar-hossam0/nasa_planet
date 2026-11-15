"""One fixed, auditable synthetic Phase 4 experiment; no NASA inference."""
import calendar
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import t as student

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'packages/science'))
from src.berger_boos import (research_geometry, profile_scores, berger_boos,
                            inverted_critical)
from src.sen_uncertainty import sen_pivot, calibrated_sen
from src.reml_uncertainty import simulate_ar, fit_reml
from src.inference import wilson_interval
from review_sahel_ndvi import sha, write_json
from diagnose_double_bootstrap import preserve

REPORTS = ROOT/'packages/science/phase_reports'
OUT = ROOT/'data/derived/science_inference/berger_boos'
CONFIG = ROOT/'packages/science/config/berger_boos_research.json'
PREFIX = 'PHASE_4_BERGER_BOOS'


def protected_inputs():
    frozen = preserve()
    # Preserve all source data and existing numerical outputs, including ignored
    # caches, plus the earlier scientific source/configuration/tests/reports.
    folders = ['data/nasa', 'data/derived/science', 'data/derived/science_inference',
               'packages/science/src', 'packages/science/config',
               'packages/science/tests', 'packages/science/notebooks',
               'packages/science/phase_reports', 'tools']
    exclude = {'berger_boos.py', 'berger_boos_research.json',
               'test_berger_boos.py', 'research_berger_boos.py',
               'validate_berger_boos.py'}
    for folder in folders:
        for p in (ROOT/folder).rglob('*'):
            if (not p.is_file() or '__pycache__' in p.parts
                    or p.is_relative_to(OUT) or p.name in exclude
                    or p.name.startswith(PREFIX)):
                continue
            frozen[p.relative_to(ROOT).as_posix()] = sha(p)
    return frozen


def panel(c, n, model_index, cache):
    model = c['models'][model_index]
    rng = np.random.default_rng(np.random.SeedSequence(
        [c['validation_seed'], 703, n, cache, model_index]))
    N, phi, kind = c['records_per_panel'], model['phi'], model['kind']
    if kind in ('gaussian', 'seasonal'):
        y = simulate_ar(rng.normal(size=(N, n)), phi)*np.sqrt(1-phi*phi)
    else:
        z = (rng.standard_t(5, size=(N, n+300))*np.sqrt(3/5)
             if kind == 'student5' else rng.normal(size=(N, n+300)))
        if kind == 'heteroskedastic':
            z[:, -n:] *= np.linspace(1, 2, n)
        innovations = z.copy()
        for k in range(1, n+300):
            z[:, k] += phi*z[:, k-1]
            if kind == 'arma11':
                z[:, k] += .4*innovations[:, k-1]
        y = z[:, -n:]*np.sqrt(1-phi*phi)
    if kind == 'seasonal':
        cycle = 3*np.sin(2*np.pi*np.arange(12)/12)
        y += np.array([np.average(cycle, weights=[calendar.monthrange(2001+i, m)[1]
                       for m in range(1, 13)]) for i in range(n)])
    return y


def passes_screen(row, accept):
    return bool(accept['coverage_target_band'][0] <= row['coverage'] <= accept['coverage_target_band'][1]
        and row['coverage_mc95'][0] >= accept['coverage_lower_wilson_min']
        and (accept['null_rate_target_band'][0] <= row['rejection_rate'] <= accept['null_rate_target_band'][1]
             and row['rejection_mc95'][1] <= accept['null_upper_wilson_max']
             if row['truth'] == 0 else row['rejection_mc95'][0] >= accept['power_lower_wilson_min']))


def aggregate(rows, keys, fields):
    groups = {}
    for row in rows:
        groups.setdefault(tuple(row[k] for k in keys), []).append(row)
    result = []
    for group, items in groups.items():
        out = dict(zip(keys, group))
        out['failed_cache_screens'] = sum(not r['passes_screen'] for r in items)
        for field in fields:
            if items[0][field] is None:
                out[field] = None
                continue
            x = np.array([r[field] for r in items])
            radius = student.ppf(.975, len(x)-1)*x.std(ddof=1)/np.sqrt(len(x))
            out[field] = {'mean': float(x.mean()), 'min': float(x.min()), 'max': float(x.max()),
                          'mc95_cluster_mean': [float(x.mean()-radius), float(x.mean()+radius)]}
        result.append(out)
    return result


def main():
    start = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    c = json.loads(CONFIG.read_text())
    assert np.isclose(c['alpha']-c['gamma'], c['simple_null_alpha'])
    accept = json.loads((ROOT/'packages/science/config/double_bootstrap_research.json').read_text())['acceptance']
    frozen = protected_inputs()
    identity = {p.relative_to(ROOT).as_posix(): sha(p) for p in [CONFIG, Path(__file__),
        ROOT/'packages/science/src/berger_boos.py', ROOT/'packages/science/tests/test_berger_boos.py',
        REPORTS/(PREFIX+'_PROTOCOL.md')]}
    protocol = {'config': c, 'acceptance_unchanged': accept, 'identity': identity,
                'prior_hashes': frozen, 'started_before_calibration': True}
    write_json(OUT/'protocol_before_evaluation.json', protocol)
    print('Protocol recorded; protected files:', len(frozen), flush=True)
    artifacts = {}

    def save(path, **arrays):
        np.savez_compressed(path, **arrays)
        artifacts[path.relative_to(ROOT).as_posix()] = sha(path)

    rows, nuisance = [], []
    for n in c['lengths']:
        geo = research_geometry(n, c['rho_grid'])
        for cache in range(c['cache_realizations']):
            pivots, lr = [], []
            for j, rho in enumerate(c['rho_grid']):
                rng = np.random.default_rng(np.random.SeedSequence([c['cache_seed'], 101, n, cache, j]))
                y = simulate_ar(rng.normal(size=(c['calibration_replicates'], n)), rho)
                scores = profile_scores(y, geo)
                lr.append(np.sort(np.maximum(0., scores[j]-scores.min(axis=0))))
                rng = np.random.default_rng(np.random.SeedSequence([c['cache_seed'], 202, n, cache, j]))
                slope, scale = sen_pivot(simulate_ar(rng.normal(size=(c['calibration_replicates'], n)), rho))
                pivots.append(np.sort(abs(slope/scale)))
            save(OUT/f'cache_n{n}_{cache}.npz', rho_grid=np.array(c['rho_grid']),
                 lr=np.array(lr), pivot=np.array(pivots))
            for index, model in enumerate(c['models']):
                y = panel(c, n, index, cache)
                N = len(y)
                fitted_rho = fit_reml(y)['rho']  # original plug-in comparator only
                null = berger_boos(y, geo, lr, pivots, c['gamma'], c['alpha'])
                members = null['members']
                sizes = members.sum(axis=1)
                lower = np.where(members, np.array(c['rho_grid']), np.inf).min(axis=1)
                upper = np.where(members, np.array(c['rho_grid']), -np.inf).max(axis=1)
                exact = np.flatnonzero(np.isclose(c['rho_grid'], model['phi']))
                excluded = int((~members[:, exact[0]]).sum()) if len(exact) else None
                core = model['core']
                ns = c['nuisance_screen']
                diag = {'n': n, 'cache': cache, 'model': model['name'], 'phi': model['phi'],
                    'core': core, 'trials': N, 'excluded': excluded,
                    'exclusion_rate': excluded/N if excluded is not None else None,
                    'exclusion_mc95': wilson_interval(excluded, N) if excluded is not None else None,
                    'range_brackets_phi_rate': float(((lower <= model['phi']) & (model['phi'] <= upper)).mean()),
                    'mean_set_size': float(sizes.mean()), 'mean_set_span': float((upper-lower).mean()),
                    'size_quantiles': np.quantile(sizes, [0, .25, .5, .75, 1]).tolist(),
                    'upper_boundary_inclusion': float(members[:, -1].mean()),
                    'lower_boundary_inclusion': float(members[:, 0].mean()),
                    'disconnected_rate': float((np.sum(np.diff(members.astype(int), axis=1) == 1, axis=1)
                                                + members[:, 0].astype(int) > 1).mean()),
                    'empty_fallbacks': int(null['empty_fallback'].sum()),
                    'per_rho_inclusion_rate': members.mean(axis=0).tolist()}
                diag['passes_screen'] = bool(not core or (diag['exclusion_rate'] <= ns['per_cache_exclusion_max']
                    and diag['exclusion_mc95'][1] <= ns['per_cache_exclusion_wilson_upper_max']))
                nuisance.append(diag)
                arrays = {'noise': y, 'sen_noise': null['slope'], 'scale': null['scale'],
                          'members': members, 'nuisance_p': null['nuisance_p'], 'fitted_rho': fitted_rho}
                for truth in c['truths']:
                    values = y+truth*np.arange(n)
                    outputs = {
                        'sen_berger_boos': berger_boos(values, geo, lr, pivots, c['gamma'], c['alpha']),
                        'sen_parametric_plugin': calibrated_sen(values, c['rho_grid'], pivots, fitted_rho),
                        'sen_nuisance_grid_envelope': calibrated_sen(values, c['rho_grid'], pivots)}
                    np.testing.assert_array_equal(outputs['sen_berger_boos']['members'], members)
                    for method, out in outputs.items():
                        np.testing.assert_allclose(out['slope'], null['slope']+truth, atol=1e-12)
                        np.testing.assert_allclose(out['scale'], null['scale'], atol=1e-12)
                        rejected = int((out['p'] <= c['alpha']).sum())
                        covered = int((abs(out['slope']-truth) <= out['radius']).sum())
                        # A tested zero slope belongs to the inverted confidence interval
                        # exactly when that null is not rejected (except continuous endpoints).
                        disagreement = int(((out['p'] <= c['alpha']) != (abs(out['slope']) > out['radius'])).sum())
                        row = {'method': method, 'n': n, 'cache': cache, 'model': model['name'],
                            'phi': model['phi'], 'core': core, 'truth': truth, 'trials': N,
                            'rejected': rejected, 'covered': covered,
                            'rejection_rate': rejected/N, 'coverage': covered/N,
                            'rejection_mc95': wilson_interval(rejected, N), 'coverage_mc95': wilson_interval(covered, N),
                            'mean_interval_width': float(np.mean(2*out['radius'])),
                            'sen_bias': float(np.mean(out['slope']-truth)), 'p_interval_disagreements': disagreement}
                        row['passes_screen'] = passes_screen(row, accept)
                        rows.append(row)
                        arrays[f'{method}_{truth}_p'] = out['p']
                        arrays[f'{method}_{truth}_radius'] = out['radius']
                        if method == 'sen_berger_boos':
                            assert disagreement == 0
                save(OUT/f'panel_n{n}_{cache}_{model["name"]}.npz', **arrays)
            print('n', n, 'cache', cache, 'complete; seconds', round(time.perf_counter()-start, 1), flush=True)
    ag = aggregate(rows, ['n', 'method', 'model', 'phi', 'truth'],
                   ['coverage', 'rejection_rate', 'mean_interval_width'])
    ng = aggregate(nuisance, ['n', 'model', 'phi', 'core'],
                   ['exclusion_rate', 'mean_set_size', 'mean_set_span', 'upper_boundary_inclusion'])
    for p, h in {**frozen, **identity}.items():
        assert sha(ROOT/p) == h, p
    candidate = [r for r in rows if r['method'] == 'sen_berger_boos']
    nuisance_pass = (all(r['passes_screen'] for r in nuisance)
        and all(r['exclusion_rate']['mean'] <= c['nuisance_screen']['aggregate_exclusion_max']
                for r in ng if r['core']))
    result = {**protocol, 'rows': rows, 'aggregate': ag, 'nuisance': nuisance, 'nuisance_aggregate': ng,
        'artifacts': artifacts, 'protocol_sha256': sha(OUT/'protocol_before_evaluation.json'),
        'numerical_failures': 0, 'nuisance_screen_passed': bool(nuisance_pass),
        'candidate_all_screens_passed': bool(nuisance_pass and all(r['passes_screen'] for r in candidate)),
        'application_release': False, 'phase5_started': False,
        'unique_validation_noise_records': len(c['lengths'])*c['cache_realizations']*len(c['models'])*c['records_per_panel'],
        'calibration_records': 2*len(c['lengths'])*c['cache_realizations']*len(c['rho_grid'])*c['calibration_replicates'],
        'paired_record_evaluations': len(rows)*c['records_per_panel'],
        'elapsed_seconds': time.perf_counter()-start,
        'accounting': 'Four independent cache/panel units. Trends and methods paired within noise panel; separate nuisance/pivot calibration streams. Wilson intervals conditional on one cache; cluster-t ranges have only four units.',
        'decision_if_failed': 'Stop method search; recommend existing descriptive-only Phase 3 outputs. No inference or Phase 5 without review.'}
    write_json(REPORTS/(PREFIX+'_RESEARCH.json'), result)
    print('COMPLETE', len(rows), 'rows; candidate accepted:', result['candidate_all_screens_passed'], flush=True)


if __name__ == '__main__':
    main()
