"""Retained inference repair experiment. No NASA writes or automatic cleanup."""
from pathlib import Path
import hashlib
import json
import math
import sys
import time

import numpy as np
from scipy.stats import t as student

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from packages.science.src.gaussian_ar1_inference import known_rho_inference, bounded_ar1_inference
from packages.science.src.inference import wilson_interval

OUT = Path(__file__).resolve().parent


def save(name, value):
    (OUT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def summarize(result, truth):
    p, interval, estimate = result['p'], result['interval'], result['slope']
    n = len(p)
    rejected = int((p < .05).sum())
    covered = int(((interval[:, 0] <= truth) & (truth <= interval[:, 1])).sum())
    return {'records': n, 'rejection_rate': rejected/n,
            'rejection_MC95': wilson_interval(rejected, n),
            'coverage': covered/n, 'coverage_MC95': wilson_interval(covered, n),
            'bias': float(np.mean(estimate-truth)),
            'RMSE': float(np.sqrt(np.mean((estimate-truth)**2))),
            'p_min': float(p.min()), 'p_median': float(np.median(p)),
            'p_max': float(p.max()),
            'continuous_rho_guard': result.get('continuous_rho_TV_guard', 0),
            'application_release': False}


def main():
    started = time.perf_counter()
    protocol = {
        'seed': 2026111601, 'validation_seed': 2026111602,
        'method': 'known-rho Student reference plus continuous-rho guarded GLS envelope',
        'rho_bounds': [-.95, .95], 'grid_size': 4001, 'confidence': .95,
        'nominal_alpha': .05, 'primary_n': 24, 'records_per_primary_scenario': 1000,
        'primary_rho': [-.5, 0., .4, .7, .9, .9333],
        'primary_slopes': [0., .08, .5],
        'extra_lengths': [20, 48], 'extra_rho': [.7, .9333],
        'extra_slopes': [0., -.5], 'records_per_extra_scenario': 500,
        'stress_records': 1000, 'stress_noise': ['student3_AR1', 'AR2', 'heteroskedastic_AR1', 'outside_range_rho_0.99'],
        'numeric_reference': {'n': 24, 'target_abs_t': [0., 3., 8.], 'known_rho': [0., .7, .9333]},
        'screens': {
            'minimum_safety': 'null Wilson upper <= .08; coverage Wilson lower >= .90',
            'historical_practical': 'null rate .03-.07; coverage .93-.97; strong-trend power >= .20',
            'interpretation': 'conservative control is not the same as nominal calibration; retain failures'},
        'scope': 'Gaussian stationary AR1, linear conditional mean, fixed external rho range; no NASA release',
        'retention': 'All test data and earlier experiments retained until explicit user deletion request'}
    save('protocol.json', protocol)
    rng = np.random.default_rng(protocol['seed'])
    fixtures, numeric = [], []
    x = np.arange(24, dtype=float)
    design = np.column_stack([np.ones(24), x])
    for rho in protocol['numeric_reference']['known_rho']:
        transform = np.eye(24)
        transform[0, 0] = math.sqrt(1-rho*rho)
        transform[np.arange(1, 24), np.arange(23)] = -rho
        z = transform@design
        inverse = np.linalg.inv(z.T@z)
        for target in protocol['numeric_reference']['target_abs_t']:
            residual = rng.normal(size=24)
            residual -= z@np.linalg.lstsq(z, residual, rcond=None)[0]
            residual /= np.linalg.norm(residual)
            beta = .08 if target else 0.
            norm = beta*math.sqrt(22)/(target*math.sqrt(inverse[1, 1])) if target else 1.
            y = np.linalg.solve(transform, z@np.array([290., beta])+norm*residual)
            expected = float(2*student.sf(target, 22))
            actual = known_rho_inference(y, x+2001, rho=rho)
            guarded = bounded_ar1_inference(y, x+2001)
            error = abs(actual['p']-expected)
            fixtures.append({'rho': rho, 'target_t': target, 'expected_p': expected,
                             'years': (x+2001).astype(int).tolist(), 'values': y.tolist()})
            numeric.append({'rho': rho, 'target_t': target, 'expected_p': expected,
                            'actual_known_rho_p': actual['p'], 'absolute_error': error,
                            'guarded_unknown_rho_p': guarded['p'],
                            'passed': error < 1e-10,
                            'note': 'manufactured algebraic reference, not a random calibration record'})
    save('numeric_fixtures.json', fixtures)
    save('numeric_reference_results.json', numeric)
    print(json.dumps({'numeric_references_passed': sum(r['passed'] for r in numeric), 'total': len(numeric)}), flush=True)

    rng = np.random.default_rng(protocol['validation_seed'])
    records, outputs, results = {}, {}, []
    def evaluate(name, y, n, rho, beta, inside, known=True):
        years = np.arange(2001, 2001+n)
        records[name] = y
        methods = [('bounded_rho', bounded_ar1_inference(y, years))]
        if known:
            methods.append(('known_rho_reference', known_rho_inference(y, years, rho=rho)))
        for method, output in methods:
            outputs[name+'_'+method+'_p'] = output['p']
            outputs[name+'_'+method+'_interval'] = output['interval']
            row = {'scenario': name, 'method': method, 'n': n, 'rho': rho,
                   'true_slope': beta, 'inside_declared_model': inside, **summarize(output, beta)}
            row['minimum_safety_pass'] = (row['coverage_MC95'][0] >= .90 and
                (beta != 0 or row['rejection_MC95'][1] <= .08)) if inside else None
            row['historical_practical_pass'] = (.93 <= row['coverage'] <= .97 and
                (beta != 0 or .03 <= row['rejection_rate'] <= .07) and
                (abs(beta) < .5 or row['rejection_rate'] >= .20)) if inside else None
            results.append(row)
        save('scenario_results.json', results)  # Preserve progress if interrupted.
        print(json.dumps({'scenario': name, 'done': len(results),
                          'elapsed_seconds': round(time.perf_counter()-started, 1)}), flush=True)

    def ar1(n, count, rho, heavy=False):
        normal = rng.normal(size=(count, n+500)) if not heavy else rng.standard_t(3, size=(count, n+500))/math.sqrt(3)
        # Long independent burn-in also handles non-Gaussian innovation stresses.
        for i in range(1, normal.shape[1]):
            normal[:, i] = rho*normal[:, i-1]+math.sqrt(1-rho*rho)*normal[:, i]
        return normal[:, -n:]

    for rho in protocol['primary_rho']:
        for beta in protocol['primary_slopes']:
            y = 290+beta*x+ar1(24, 1000, rho)
            evaluate(f'n24_rho{rho}_beta{beta}', y, 24, rho, beta, True)
    for n in protocol['extra_lengths']:
        for rho in protocol['extra_rho']:
            for beta in protocol['extra_slopes']:
                y = 290+beta*np.arange(n)+ar1(n, 500, rho)
                evaluate(f'n{n}_rho{rho}_beta{beta}', y, n, rho, beta, True)
    for stress in protocol['stress_noise']:
        if stress == 'student3_AR1':
            noise = ar1(24, 1000, .7, heavy=True)
        elif stress == 'AR2':
            noise = rng.normal(size=(1000, 524))
            for i in range(2, 524):
                noise[:, i] += .5*noise[:, i-1]+.3*noise[:, i-2]
            noise = noise[:, -24:]
        elif stress == 'heteroskedastic_AR1':
            noise = ar1(24, 1000, .7)*np.linspace(.1, 3, 24)
        else:
            noise = ar1(24, 1000, .99)
        evaluate('stress_'+stress, 290+noise, 24, None, 0., False, known=False)
    np.savez_compressed(OUT/'synthetic_records.npz', **records)
    np.savez_compressed(OUT/'p_values_and_intervals.npz', **outputs)
    summary = {'numeric_references_passed': sum(r['passed'] for r in numeric),
               'numeric_references_total': len(numeric),
               'maximum_numeric_p_error': max(r['absolute_error'] for r in numeric),
               'generated_records': sum(len(v) for v in records.values()),
               'scenario_method_evaluations': sum(r['records'] for r in results),
               'inside_model_bounded_scenarios': sum(r['inside_declared_model'] and r['method']=='bounded_rho' for r in results),
               'inside_model_bounded_minimum_safety_failures': [r['scenario'] for r in results if r['inside_declared_model'] and r['method']=='bounded_rho' and not r['minimum_safety_pass']],
               'inside_model_bounded_historical_practical_failures': [r['scenario'] for r in results if r['inside_declared_model'] and r['method']=='bounded_rho' and not r['historical_practical_pass']],
               'elapsed_seconds': round(time.perf_counter()-started, 2),
               'production_enabled': False}
    save('summary.json', summary)
    paths = [Path(__file__), ROOT/'packages/science/src/gaussian_ar1_inference.py', ROOT/'packages/science/tests/test_gaussian_ar1_inference.py']
    save('code_hashes.json', {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    print(json.dumps(summary), flush=True)
    return int(summary['numeric_references_passed'] != len(numeric))


if __name__ == '__main__':
    sys.exit(main())
