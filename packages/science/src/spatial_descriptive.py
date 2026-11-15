"""Descriptive spatial summaries; intentionally independent of HTTP/inference."""
import numpy as np
import xarray as xr
from .trend_estimation import cell_trends, trend_series, monthly_elapsed_years, annual_elapsed_years


def directions(slopes, eligible):
    slopes = np.asarray(slopes, dtype=float)
    eligible = np.asarray(eligible, dtype=bool)
    if slopes.shape != eligible.shape or np.isinf(slopes).any():
        raise ValueError('Aligned finite-or-missing slopes and support required')
    codes = np.zeros(slopes.shape, dtype='int8')
    valid = eligible & np.isfinite(slopes)
    codes[valid & (slopes > 0)] = 1
    codes[valid & (slopes < 0)] = -1
    codes[valid & (slopes == 0)] = 2
    return codes


def shares(slopes, eligible):
    eligible = np.asarray(eligible, dtype=bool)
    code = directions(slopes, eligible)
    counts = {name: int(((code == value) & eligible).sum())
              for name, value in [('positive', 1), ('negative', -1), ('exactly_zero', 2), ('unavailable', 0)]}
    denominator = int(eligible.sum())
    return {'eligible_cells': denominator, 'selected_cells': eligible.size,
            'excluded_cells': int((~eligible).sum()), 'counts': counts,
            'percent_of_eligible_cells': {k: 100*v/denominator if denominator else None for k, v in counts.items()},
            'denominator_definition': 'all preparation-eligible cells, including unavailable slopes'}


def analyze_window(cells, regional, support, frequency, start, end, reference=None):
    axis = 'time' if frequency == 'monthly' else 'year' if frequency == 'annual' else None
    if axis is None or start > end:
        raise ValueError('Invalid frequency/window')
    xr.testing.assert_equal(cells.lat, support.lat)
    xr.testing.assert_equal(cells.lon, support.lon)
    if support.dims != ('lat', 'lon'):
        raise ValueError('Native support dimensions required')
    xr.testing.assert_equal(cells[axis], regional[axis])
    years = cells.time.dt.year.values if axis == 'time' else cells.year.values
    if not len(years) or start < years.min() or end > years.max():
        raise ValueError('Window outside available years')
    mask = (years >= start) & (years <= end)
    subset = cells.isel({axis: mask}).where(support.astype(bool))
    grid = cell_trends(subset, frequency=frequency)
    grid['direction'] = (('lat', 'lon'), directions(grid.slope, support))
    grid.direction.attrs['codes'] = '-1 negative; 0 unavailable; 1 positive; 2 exactly zero; descriptive only'
    if reference is not None:
        xr.testing.assert_equal(grid.lat, reference.lat)
        xr.testing.assert_equal(grid.lon, reference.lon)
        comparable = np.isfinite(grid.slope) & np.isfinite(reference.slope) & support.astype(bool)
        grid['direction_agrees_full_period'] = xr.where(comparable, (np.sign(grid.slope) == np.sign(reference.slope)).astype('int8'), -1)
        grid.direction_agrees_full_period.attrs['codes'] = '-1 unavailable; 0 differs; 1 agrees; descriptive only'
    series = regional.isel({axis: mask})
    t = monthly_elapsed_years(series.time) if axis == 'time' else annual_elapsed_years(series.year)
    result = trend_series(series.values, t)
    result.update({'start_year': start, 'end_year': end, 'scheduled_observations': len(t),
                   'slope_units': grid.slope.attrs['units'], 'cell_shares': shares(grid.slope, support)})
    return grid, result
