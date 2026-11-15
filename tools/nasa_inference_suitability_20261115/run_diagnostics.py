"""Read-only NASA annual-series diagnostics; no inference release or deletion.

Run: python tools/nasa_inference_suitability_20261115/run_diagnostics.py
Diagnostic bootstrap p-values are exploratory fitted-model checks, NOT trend
p-values or proof of assumptions. All model fits are repeated in bootstraps.
"""
from pathlib import Path
import csv
import hashlib
import importlib.metadata
import json
import sys
import time

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from packages.science.src.preparation import prepare_registered
from packages.science.src.trend_estimation import trend_series
from packages.science.src.gaussian_ar1_inference import _geometry
from packages.science.src.inference import adjust_fdr

NAMES = ['remaining_serial_dependence', 'non_gaussian_innovations',
         'variance_time_association', 'extreme_innovation', 'quadratic_departure']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    (OUT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def fit(y, ar1):
    """Profile Gaussian ML, same complete linear model for observed/bootstrap rows."""
    y = np.atleast_2d(y).astype(float)
    n = y.shape[1]
    if n < 8 or not np.isfinite(y).all():
        raise ValueError('Diagnostics require complete finite annual rows of length >=8')
    mean = y.mean(axis=1, keepdims=True)
    centered = y-mean
    rho, inverse, score = _geometry(n, -.99 if ar1 else 0., .99 if ar1 else 0., 1001 if ar1 else 1)
    g = np.einsum('rin,bn->rib', score, centered, optimize=True)
    beta = np.einsum('rij,rjb->rib', inverse, g, optimize=True)
    quadratic = ((centered*centered).sum(axis=1)[None, :]
        +rho[:, None]**2*(centered[:, 1:-1]**2).sum(axis=1)[None, :]
        -2*rho[:, None]*(centered[:, 1:]*centered[:, :-1]).sum(axis=1)[None, :])
    sse = quadratic-np.sum(g*beta, axis=1)
    if np.any(sse <= 0):
        raise ValueError('Degenerate variance in profile fit')
    objective = n*np.log(sse/n)-np.log1p(-rho*rho)[:, None]
    index = np.argmin(objective, axis=0)
    col = np.arange(len(y))
    selected = rho[index]
    coefficients = beta[index, :, col]
    residual = centered-coefficients[:, :1]-coefficients[:, 1:2]*np.arange(n)
    innovation = residual.copy()
    innovation[:, 0] *= np.sqrt(1-selected*selected)
    innovation[:, 1:] -= selected[:, None]*residual[:, :-1]
    return {'rho': selected, 'slope': coefficients[:, 1],
            'intercept': coefficients[:, 0]+mean[:, 0], 'residual': residual,
            'innovation': innovation, 'inverse': inverse[index],
            'innovation_sd': np.sqrt(sse[index, col]/(n-2)),
            'boundary': ((index == 0)|(index == len(rho)-1)) if ar1 else np.zeros(len(y), dtype=bool)}


def acf(rows, lag):
    centered = rows-rows.mean(axis=1, keepdims=True)
    return (centered[:, lag:]*centered[:, :-lag]).sum(axis=1)/(centered*centered).sum(axis=1)


def diagnostics(fitted):
    e, rho = fitted['innovation'], fitted['rho']
    n = e.shape[1]
    lags = np.arange(1, 5)
    coefficients = np.stack([acf(e, lag) for lag in lags], axis=1)
    ljung = n*(n+2)*np.sum(coefficients**2/(n-lags), axis=1)
    normality = 1-stats.shapiro(e, axis=1).statistic
    ranks = stats.rankdata(e*e, axis=1)
    ranks -= ranks.mean(axis=1, keepdims=True)
    axis = np.arange(n)-np.mean(np.arange(n))
    variance = abs(ranks@axis/np.sqrt((ranks*ranks).sum(axis=1)*(axis@axis)))
    deviation = abs(e-np.median(e, axis=1, keepdims=True))
    outlier = deviation.max(axis=1)/(1.4826*np.median(deviation, axis=1))
    # Extra whitened quadratic regressor, residualized against linear design.
    x = np.arange(n, dtype=float)
    linear = np.stack([np.ones(n), x], axis=1)
    wlinear = np.broadcast_to(linear, (len(e), n, 2)).copy()
    wlinear[:, 0] *= np.sqrt(1-rho*rho)[:, None]
    wlinear[:, 1:] -= rho[:, None, None]*linear[:-1]
    q = np.broadcast_to(x*x, e.shape).copy()
    q[:, 0] *= np.sqrt(1-rho*rho)
    q[:, 1:] -= rho[:, None]*(x*x)[:-1]
    gq = np.einsum('bni,bn->bi', wlinear, q)
    qnorm = (q*q).sum(axis=1)-np.einsum('bi,bij,bj->b', gq, fitted['inverse'], gq)
    extra = (q*e).sum(axis=1)**2/qnorm
    sse = (e*e).sum(axis=1)
    curvature = extra/np.maximum(sse-extra, np.finfo(float).tiny)*(n-3)
    return np.column_stack([ljung, normality, variance, outlier, curvature])


def bootstrap(y, observed, ar1, rng, count):
    n = len(y)
    rho = float(observed['rho'][0])
    references, correlations = [], []
    for start in range(0, count, 500):
        size = min(500, count-start)
        noise = rng.normal(size=(size, n))*float(observed['innovation_sd'][0])
        noise[:, 0] /= np.sqrt(1-rho*rho)
        for i in range(1, n):
            noise[:, i] += rho*noise[:, i-1]
        samples = observed['intercept'][0]+observed['slope'][0]*np.arange(n)+noise
        refitted = fit(samples, ar1)
        references.append(diagnostics(refitted))
        correlations.extend(refitted['rho'])
    reference = np.concatenate(references)
    actual = diagnostics(observed)[0]
    return ((1+(reference >= actual).sum(axis=0))/(count+1), reference,
            np.quantile(correlations, [.025, .975]).tolist())


def self_checks():
    x = np.arange(24)
    y = 290+.03*x+np.random.default_rng(52).normal(size=24)
    fitted = fit(y, False)
    reference = stats.linregress(x, y)
    assert abs(fitted['slope'][0]-reference.slope) < 1e-12
    assert abs(fitted['intercept'][0]-reference.intercept) < 1e-12
    direct_sse = np.sum((y-reference.intercept-reference.slope*x)**2)
    assert abs(np.sum(fitted['innovation']**2)-direct_sse) < 1e-10
    # Dense precision GLS oracle at the chosen profile rho.
    fitted_ar = fit(y, True)
    r = float(fitted_ar['rho'][0])
    covariance = r**abs(x[:, None]-x)
    design = np.column_stack([np.ones(24), x])
    expected = np.linalg.solve(design.T@np.linalg.solve(covariance, design), design.T@np.linalg.solve(covariance, y))
    assert np.allclose([fitted_ar['intercept'][0], fitted_ar['slope'][0]], expected, atol=1e-10)
    assert diagnostics(fitted).shape == (1, 5)
    return {'independent_OLS_reference': True, 'residual_SSE_reference': True,
            'dense_covariance_GLS_reference': True, 'diagnostic_shape': True}


def figure(case):
    years, y = np.array(case['years']), np.array(case['annual_values'])
    fig, axes = plt.subplots(2, 3, figsize=(14, 8), constrained_layout=True)
    x = years-years[0]
    axes[0, 0].plot(years, y, 'o-', color='#236d81', label='Annual observations')
    axes[0, 0].plot(years, case['AR1']['intercept']+case['AR1']['slope']*x, color='#bd7542', label='Fitted linear mean (diagnostic)')
    axes[0, 0].set_ylabel('unitless' if case['units']=='1' else case['units'])
    axes[0, 0].legend(fontsize=8)
    residual, innovation = np.array(case['AR1']['residuals']), np.array(case['AR1']['innovations'])
    axes[0, 1].plot(years, residual, 'o-'); axes[0, 1].axhline(0, color='grey', lw=.8)
    axes[0, 1].set_title('AR1 linear-fit residuals')
    axes[0, 2].plot(years, innovation, 'o-'); axes[0, 2].axhline(0, color='grey', lw=.8)
    axes[0, 2].set_title('Whitened innovations (estimated rho)')
    stats.probplot(innovation, dist='norm', plot=axes[1, 0])
    axes[1, 0].set_title('Innovation normal Q-Q (exploratory)')
    lags = np.arange(1, 7)
    axes[1, 1].bar(lags, [acf(innovation[None, :], lag)[0] for lag in lags], color='#236d81')
    axes[1, 1].axhline(0, color='grey', lw=.8)
    axes[1, 1].set_title('Innovation ACF; no uncalibrated bands')
    axes[1, 1].set_xlabel('Lag (years)')
    axes[1, 2].plot(years, abs(innovation), 'o-', color='#bd7542')
    axes[1, 2].set_title('Absolute innovations vs year')
    fig.suptitle(case['variable_id']+' / '+case['region_id']+'\n24 annual values; diagnostics do not approve trend inference', fontsize=13)
    for ax in axes.flat:
        ax.grid(alpha=.15)
    fig.savefig(OUT/(case['case']+'.png'), dpi=125)
    plt.close(fig)


def main():
    started = time.perf_counter()
    scope_path = ROOT/'docs/architecture/scope.v2.json'
    entries = json.loads(scope_path.read_text(encoding='utf-8'))['entries']
    paths = [ROOT/e['cube_file'] for e in entries]+[scope_path, ROOT/'packages/science/config/preparation_policy.json']
    before = {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}
    protocol = {'seed': 2026111702, 'bootstrap_replicates': 19999,
        'basis': 'actual complete regional annual series, 2001-2024, strict full-reference QA support',
        'models': ['linear Gaussian IID', 'linear stationary Gaussian AR1 with fitted rho'],
        'AR1_profile_grid': [-.99, .99, 1001], 'diagnostics': NAMES,
        'diagnostic_tail': 'large statistic; plus-one parametric bootstrap, full refit',
        'exploratory_threshold': .05, 'multiplicity': 'BY across all 12*2*5=120 diagnostic p-values',
        'retained_area_review_threshold': .5,
        'pilot': '999-replicate run preserved in pilot_999; increased resolution only, model/statistics/thresholds unchanged',
        'limitations': ['fitted-parameter bootstrap is approximate, especially with 24 years',
            'diagnostic p-values are not p-values for trend',
            'no detected contradiction does not validate assumptions',
            'BY cannot repair invalid marginal diagnostic p-values',
            'do not select a model by p-values and then treat it as fixed for trend inference'],
        'production_enabled': False}
    save('protocol.json', protocol)
    save('source_hashes_before.json', before)
    save('self_checks.json', self_checks())
    rng = np.random.default_rng(protocol['seed'])
    cases, reference_arrays = [], {}
    for entry in entries:
        variable, region = entry['variable_id'], entry['region_id']
        prepared, metadata = prepare_registered(variable, region)
        years, y = prepared.year.values, prepared.regional_annual.values
        if len(y) != 24 or not np.isfinite(y).all() or not np.all(np.diff(years)==1):
            raise ValueError(f'Incomplete annual record: {variable}/{region}; never drop/compress years')
        case = {'case': variable+'__'+region, 'variable_id': variable, 'region_id': region,
            'source_file': entry['cube_file'], 'source_sha256': before[entry['cube_file']],
            'product': entry['product_id'], 'years': years.astype(int).tolist(),
            'annual_values': y.tolist(), 'units': metadata['annual_units'],
            'sen_slope': trend_series(y, years)['slope_per_year'],
            'annual_aggregation': metadata['annual_aggregation'],
            'n_years': len(y), 'selected_cells': metadata['selected_cell_count'],
            'retained_cells': metadata['eligible_fixed_support_cells'],
            'retained_area_fraction': metadata['fixed_support_area_fraction_of_selected_native_cells'],
            'low_spatial_support_review': metadata['fixed_support_area_fraction_of_selected_native_cells'] < .5,
            'trend_p_value': None, 'inference_enabled': False}
        leave_one = [trend_series(np.delete(y, i), np.delete(years, i))['slope_per_year'] for i in range(len(y))]
        case['leave_one_year_out_sen_range'] = [min(leave_one), max(leave_one)]
        case['leave_one_year_out_sign_agreement'] = float(np.mean(np.sign(leave_one)==np.sign(case['sen_slope'])))
        for name, ar1 in [('IID', False), ('AR1', True)]:
            fitted = fit(y, ar1)
            probability, reference, rho_bootstrap_range = bootstrap(y, fitted, ar1, rng, protocol['bootstrap_replicates'])
            raw = diagnostics(fitted)[0]
            case[name] = {'rho_hat': float(fitted['rho'][0]), 'rho_grid_boundary': bool(fitted['boundary'][0]),
                'slope': float(fitted['slope'][0]), 'intercept': float(fitted['intercept'][0]),
                'residuals': fitted['residual'][0].tolist(), 'innovations': fitted['innovation'][0].tolist(),
                'residual_lag1_acf': float(acf(fitted['residual'], 1)[0]),
                'innovation_lag1_acf': float(acf(fitted['innovation'], 1)[0]),
                'fitted_model_bootstrap_rho_quantiles_025_975_not_validated_CI': rho_bootstrap_range,
                'diagnostics': {label: {'statistic': float(raw[i]), 'exploratory_bootstrap_p': float(probability[i])}
                                for i, label in enumerate(NAMES)}}
            reference_arrays[case['case']+'_'+name] = reference
        cases.append(case)
        save('case_results.json', cases)
        figure(case)
        print(json.dumps({'case': case['case'], 'done': len(cases), 'elapsed_seconds': round(time.perf_counter()-started, 1)}), flush=True)
    flattened = [d for c in cases for model in ['IID', 'AR1'] for d in c[model]['diagnostics'].values()]
    adjusted = adjust_fdr([d['exploratory_bootstrap_p'] for d in flattened], method='BY', q=.05)['adjusted_p']
    for d, value in zip(flattened, adjusted):
        d['exploratory_BY_adjusted_p'] = float(value)
    for case in cases:
        for model in ['IID', 'AR1']:
            raw = [k for k, d in case[model]['diagnostics'].items() if d['exploratory_bootstrap_p'] < .05]
            family = [k for k, d in case[model]['diagnostics'].items() if d['exploratory_BY_adjusted_p'] < .05]
            case[model]['raw_review_flags'] = raw
            case[model]['BY_review_flags'] = family
            case[model]['suitability'] = ('review_concerns_detected' if raw or case[model]['rho_grid_boundary']
                else 'no_clear_contradiction_detected_not_validated')
    save('case_results.json', cases)
    np.savez_compressed(OUT/'bootstrap_diagnostic_statistics.npz', **reference_arrays)
    save('source_hashes_after.json', {p.relative_to(ROOT).as_posix(): sha(p) for p in paths})
    assert before == json.loads((OUT/'source_hashes_after.json').read_text()), 'Source changed during audit'
    summary = {'cases': len(cases), 'diagnostic_p_values': len(flattened),
        'bootstrap_synthetic_records': len(cases)*2*protocol['bootstrap_replicates'],
        'IID_raw_flag_cases': [c['case'] for c in cases if c['IID']['raw_review_flags']],
        'AR1_raw_flag_cases': [c['case'] for c in cases if c['AR1']['raw_review_flags']],
        'BY_flag_cases': [c['case'] for c in cases if c['IID']['BY_review_flags'] or c['AR1']['BY_review_flags']],
        'low_spatial_support_cases': [c['case'] for c in cases if c['low_spatial_support_review']],
        'source_bytes_unchanged': True, 'inference_enabled': False,
        'elapsed_seconds': round(time.perf_counter()-started, 2)}
    save('summary.json', summary)
    with (OUT/'overview.csv').open('w', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file)
        writer.writerow(['variable', 'region', 'n', 'Sen_slope', 'units_per_year', 'retained_area_percent', 'AR1_rho_hat', 'IID_raw_review_flags', 'AR1_raw_review_flags', 'BY_flags', 'inference_enabled'])
        for c in cases:
            writer.writerow([c['variable_id'], c['region_id'], c['n_years'], c['sen_slope'], c['units']+'/year', 100*c['retained_area_fraction'], c['AR1']['rho_hat'], ';'.join(c['IID']['raw_review_flags']), ';'.join(c['AR1']['raw_review_flags']), ';'.join(c['AR1']['BY_review_flags']), False])
    save('reproducibility.json', {'code_sha256': sha(Path(__file__)),
        'versions': {name: importlib.metadata.version(name) for name in ['numpy', 'scipy', 'xarray', 'matplotlib']}})
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
