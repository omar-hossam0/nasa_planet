"""Deterministic synthetic time-series and trend generation.

Every number produced here is derived from a sha256 seed of the request
identity, so the same request always yields byte-identical output while
different requests differ. Nothing is random at runtime and nothing is loaded
from the network.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

from app.core.timeutil import month_count, month_of, month_range, month_to_index
from app.mocks.catalog import VARIABLES_BY_ID
from app.schemas.common import EvidenceState, TrendDirection
from app.schemas.results import TimeSeriesPoint, TrendSummary

METHOD_ID = "mock_seasonal_linear_v0"
METHOD_VERSION = "0.1.0-mock"

# Slopes are small; keep four decimals so a real-looking zero is not reported.
SLOPE_DECIMALS = 4


@dataclass(frozen=True)
class SeriesProfile:
    """Shape parameters for a synthetic monthly series."""

    baseline: float
    seasonal_amplitude: float
    seasonal_phase_months: float
    trend_per_year: float
    noise_amplitude: float
    decimals: int
    unit_suffix: str

    @property
    def flat_threshold(self) -> float:
        """Slopes below 10% of the configured trend are reported as inconclusive.

        Without a significance test there is no defensible p-value, so the
        demo refuses to label a near-zero slope as a direction.
        """
        return abs(self.trend_per_year) * 0.1


PROFILES: dict[str, SeriesProfile] = {
    "air_temperature": SeriesProfile(
        baseline=296.0,
        seasonal_amplitude=6.2,
        seasonal_phase_months=6.5,
        trend_per_year=0.035,
        noise_amplitude=0.55,
        decimals=2,
        unit_suffix="K year-1",
    ),
    "soil_moisture": SeriesProfile(
        baseline=8.4,
        seasonal_amplitude=2.6,
        seasonal_phase_months=1.0,
        trend_per_year=-0.018,
        noise_amplitude=0.35,
        decimals=3,
        unit_suffix="kg m-2 year-1",
    ),
    "precipitation": SeriesProfile(
        baseline=1.05,
        seasonal_amplitude=0.62,
        seasonal_phase_months=0.5,
        trend_per_year=0.0021,
        noise_amplitude=0.14,
        decimals=3,
        unit_suffix="mm day-1 year-1",
    ),
    "vegetation_greenness": SeriesProfile(
        baseline=0.235,
        seasonal_amplitude=0.062,
        seasonal_phase_months=4.0,
        trend_per_year=0.00062,
        noise_amplitude=0.011,
        decimals=4,
        unit_suffix="index year-1",
    ),
}

def stable_seed(*parts: str) -> int:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _unit_noise(seed: int, index: int) -> float:
    """Deterministic pseudo-noise in [-1, 1]."""
    digest = hashlib.sha256(f"{seed}:{index}".encode("utf-8")).digest()
    return (int.from_bytes(digest[:4], "big") / 0xFFFFFFFF) * 2.0 - 1.0


def profile_for(variable_id: str) -> SeriesProfile:
    return PROFILES.get(variable_id, PROFILES["air_temperature"])


def build_series(
    variable_id: str,
    start_month: str,
    end_month: str,
    *,
    offset_seed: str = "",
    trend_scale: float = 1.0,
    baseline_shift: float = 0.0,
    missing_months: frozenset[str] = frozenset(),
) -> list[TimeSeriesPoint]:
    """Build a monthly series between two ``YYYY-MM`` bounds."""
    profile = profile_for(variable_id)
    seed = stable_seed(variable_id, start_month, end_month, offset_seed)
    start_index = month_to_index(start_month)
    points: list[TimeSeriesPoint] = []

    for month in month_range(start_month, end_month):
        index = month_to_index(month) - start_index
        years_elapsed = index / 12.0
        seasonal = profile.seasonal_amplitude * math.sin(
            2.0 * math.pi * (month_of(month) - profile.seasonal_phase_months) / 12.0
        )
        trend = profile.trend_per_year * trend_scale * years_elapsed
        noise = profile.noise_amplitude * _unit_noise(seed, index)
        value = round(profile.baseline + baseline_shift + seasonal + trend + noise, profile.decimals)
        if month in missing_months:
            points.append(TimeSeriesPoint(month=month, value=None, missing=True))
        else:
            points.append(TimeSeriesPoint(month=month, value=value, missing=False))

    return points


def annual_mean_slope(
    points: list[TimeSeriesPoint],
) -> tuple[float | None, float | None, float | None, int]:
    """Ordinary least squares on complete-year annual means.

    Monthly OLS would let the seasonal cycle alias into the trend: a sine over
    calendar months correlates with time when the sample is an integer number
    of years, which inflated the fitted slope by ~2x in an earlier iteration.
    Averaging complete calendar years removes the seasonal term exactly (each
    year contains all twelve months once) and reduces noise.

    Returns ``(slope_per_year, fitted_start_value, r_squared, n_years)``.
    Fewer than three complete years yields ``(None, None, None, n_years)``.
    """
    by_year: dict[int, list[float]] = {}
    for point in points:
        if point.value is None:
            continue
        by_year.setdefault(int(point.month[:4]), []).append(float(point.value))

    annual_means = {
        year: sum(values) / len(values)
        for year, values in by_year.items()
        if len(values) == 12  # complete calendar year only
    }
    if len(annual_means) < 3:
        return None, None, None, len(annual_means)

    years = sorted(annual_means)
    xs = [float(year) for year in years]
    ys = [annual_means[year] for year in years]
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if denominator == 0:
        return None, None, None, n
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denominator
    fitted_start = mean_y + slope * (xs[0] - mean_x)
    ss_total = sum((y - mean_y) ** 2 for y in ys)
    ss_residual = sum((y - (mean_y + slope * (x - mean_x))) ** 2 for x, y in zip(xs, ys))
    r_squared = 1.0 - (ss_residual / ss_total) if ss_total > 0 else None
    return slope, fitted_start, r_squared, n


def direction_for(slope: float | None, variable_id: str) -> TrendDirection:
    """Classify a slope, refusing to over-claim near-zero values."""
    if slope is None:
        return TrendDirection.insufficient_data
    threshold = profile_for(variable_id).flat_threshold
    if slope > threshold:
        return TrendDirection.increasing
    if slope < -threshold:
        return TrendDirection.decreasing
    return TrendDirection.inconclusive


def summarise_trend(
    variable_id: str,
    points: list[TimeSeriesPoint],
    *,
    label: str = "region",
) -> TrendSummary:
    """Descriptive trend summary for a synthetic series."""
    profile = profile_for(variable_id)
    slope, fitted_start, r_squared, n_years = annual_mean_slope(points)
    usable = sum(1 for point in points if point.value is not None)
    decimals = profile.decimals
    return TrendSummary(
        method_id=METHOD_ID,
        method_version=METHOD_VERSION,
        direction=direction_for(slope, variable_id),
        slope_per_year=None if slope is None else round(slope, SLOPE_DECIMALS),
        slope_unit=profile.unit_suffix,
        intercept=None if fitted_start is None else round(fitted_start, profile.decimals),
        n_months=usable,
        n_years=n_years,
        p_value=None,
        r_squared=None if r_squared is None else round(r_squared, 4),
        inference_status="not_computed",
        evidence_state=EvidenceState.synthetic_demo,
        notes=[
            f"Descriptive least-squares slope of annual means for the synthetic {label} series.",
            "Seasonality is removed by averaging complete calendar years; incomplete years are dropped.",
            "No significance test, confidence interval or p-value was computed.",
            f"Slopes below {profile.flat_threshold:g} {profile.unit_suffix} are reported as inconclusive.",
            "Slope describes this demonstration series only; it is not a NASA finding.",
        ],
    )


def period_length_months(start_month: str, end_month: str) -> int:
    return month_count(start_month, end_month)


def variable_display_name(variable_id: str) -> str:
    record = VARIABLES_BY_ID.get(variable_id)
    return record.display_name if record else variable_id


def variable_unit(variable_id: str) -> str:
    record = VARIABLES_BY_ID.get(variable_id)
    return record.unit if record else "unknown"
