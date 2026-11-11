"""Scientific validation against independently derived reference values (spec sections 5, 7).

Logistic bound. For logistic growth N(t) = K / (1 + (K/N0 - 1) exp(-r t)), the specific
growth rate is d ln N / dt = r (1 - N/K). A least-squares slope is a positively weighted
average of the slopes between pairs of points (weights (t_j - t_i)^2), and by the mean value
theorem each pairwise slope lies between the smallest and largest derivative on the
interval. So for the readings in the selected phase, from x_start to x_end:

    r (1 - x_end / K)  <=  estimated mu  <=  r (1 - x_start / K)  <  r

This is a theorem about the data, independent of the code; no tolerance beyond floating-
point rounding is needed. It also proves the method never exceeds the true intrinsic rate
on noise-free logistic data.
"""

import math

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st
from support import make_well, no_blank

from growth_analysis.blank import BlankSummary
from growth_analysis.config import AnalysisConfig
from growth_analysis.exponential import analyse_well

ROUNDING = 1e-12  # relative; the bound itself is exact
CONFIG = AnalysisConfig(blank_method="none", min_od=1e-9)


def logistic(t, n0, k, r):
    return k / (1.0 + (k / n0 - 1.0) * np.exp(-r * np.asarray(t, dtype=float)))


def phase_bounds(result, n0, k, r):
    x_start = logistic(result.phase_start_h, n0, k, r)
    x_end = logistic(result.phase_end_h, n0, k, r)
    return r * (1 - x_end / k), r * (1 - x_start / k)


@given(
    r=st.floats(0.2, 2.0),
    k=st.floats(0.3, 2.0),
    start_fraction=st.floats(1e-3, 0.05),
    interval_min=st.sampled_from([5, 10, 15, 20, 30]),
)
def test_logistic_estimate_obeys_the_derivative_bound(r, k, start_fraction, interval_min):
    n0 = start_fraction * k
    # Long enough to reach the plateau: until N is within 1% of K.
    duration_h = (math.log(k / n0 - 1) + math.log(99)) / r + 1.0
    t = np.arange(0.0, duration_h, interval_min / 60)
    result = analyse_well(make_well(t, logistic(t, n0, k, r)), no_blank(1e-9), CONFIG)
    assert result.status == "growth"
    lower, upper = phase_bounds(result, n0, k, r)
    mu = result.growth_rate_per_h
    assert lower * (1 - ROUNDING) <= mu <= upper * (1 + ROUNDING)
    assert mu < r


@given(
    r=st.floats(0.2, 2.0),
    k=st.floats(0.3, 2.0),
    start_fraction=st.floats(1e-3, 0.05),
    interval_min=st.sampled_from([5, 10, 15, 20, 30]),
)
def test_logistic_phase_ends_before_the_inflection_point(r, k, start_fraction, interval_min):
    # Stationary phase must not be fitted. With readings at most 0.3 / r apart (for r =
    # 1.2/h, every 15 min), the selected phase must end while N < K / 2, i.e. while the
    # specific growth rate is still above r / 2.
    interval_h = min(interval_min / 60, 0.3 / r)
    n0 = start_fraction * k
    duration_h = (math.log(k / n0 - 1) + math.log(99)) / r + 1.0
    t = np.arange(0.0, duration_h, interval_h)
    result = analyse_well(make_well(t, logistic(t, n0, k, r)), no_blank(1e-9), CONFIG)
    assert logistic(result.phase_end_h, n0, k, r) < k / 2


def test_website_illustrative_well_within_rounding_bound():
    """The /example page's synthetic well: r = 1.2/h, rounded to 3 decimals like an export.

    The estimate is not expected to equal 1.2 (see the module docstring). Rounding moves
    each corrected OD by at most delta = 0.0005, hence ln x_i by at most
    e_i = -ln(1 - delta / x_i), hence the least-squares slope by at most
    sum |t_i - mean t| e_i / sum (t_i - mean t)^2 over the selected readings.
    """
    r, n0, k, blank_od = 1.2, 0.01, 1.1, 0.045
    t_min = np.arange(0, 721, 15)
    t = t_min / 60
    exact = logistic(t, n0, k, r)
    raw = np.floor((blank_od + exact) * 1000 + 0.5) / 1000  # JavaScript Math.round
    blank = BlankSummary("mean", "blank", ("A1",), t.size, blank_od, 0.0, blank_od, blank_od, 0.005)
    result = analyse_well(make_well(t, raw), blank, AnalysisConfig())
    assert result.status == "growth"
    assert result.credible

    used = np.array([p.used_in_fit for p in result.points])
    tu = t[used]
    delta = 0.0005 + 1e-12  # half a unit in the third decimal, plus float representation
    e = -np.log(1 - delta / exact[used])
    rounding_bound = float(np.abs(tu - tu.mean()) @ e / ((tu - tu.mean()) @ (tu - tu.mean())))
    lower, upper = phase_bounds(result, n0, k, r)
    mu = result.growth_rate_per_h
    assert lower - rounding_bound <= mu <= upper + rounding_bound
    assert mu < r


def test_noisy_exponential_with_fixed_seed_is_within_four_standard_errors():
    rng = np.random.default_rng(12345)
    mu_true = 0.8
    t = np.arange(0.0, 8.0 + 1e-9, 0.25)
    od = 0.01 * np.exp(mu_true * t + rng.normal(0.0, 0.03, t.size))
    result = analyse_well(make_well(t, od), no_blank(1e-9), CONFIG)
    assert result.status == "growth"
    assert result.credible
    assert abs(result.growth_rate_per_h - mu_true) <= 4 * result.growth_rate_se_per_h


def test_method_does_not_exaggerate_growth_rates_on_noisy_data():
    """Spec section 7: 200 seeded curves, SD 0.03 in ln OD.

    The mean estimate must be within 2% of the true rate and closer to it than the mean
    steepest-window slope (the method this specification replaced).
    """
    rng = np.random.default_rng(2026)
    mu_true = 0.8
    t = np.arange(0.0, 8.0 + 1e-9, 0.25)
    estimates, steepest = [], []
    for _ in range(200):
        od = 0.01 * np.exp(mu_true * t + rng.normal(0.0, 0.03, t.size))
        result = analyse_well(make_well(t, od), no_blank(1e-9), CONFIG)
        estimates.append(result.growth_rate_per_h)
        steepest.append(result.steepest_window_rate_per_h)
    bias = np.mean(estimates) / mu_true - 1
    steepest_bias = np.mean(steepest) / mu_true - 1
    assert abs(bias) < 0.02
    assert abs(bias) < abs(steepest_bias)


@pytest.mark.parametrize("mu", [0.25, 0.5, 1.0, 1.5])
def test_distinct_known_rates_are_recovered(mu):
    t = np.arange(0.0, 10.0, 1 / 6)  # every 10 min
    od = 0.005 * np.exp(mu * t)
    od = np.minimum(od, 2.0)  # an abrupt plateau after exponential growth
    result = analyse_well(make_well(t, od), no_blank(1e-9), CONFIG)
    assert result.status == "growth"
    # The local rate is mu before the plateau and 0 on it, so the estimate is at most mu.
    # A five-point window ending in one plateau reading has slope at most 0.8 mu, and with
    # two plateau readings 0.5 mu, so at most one plateau reading joins the phase; the worst
    # case, four exponential readings plus one plateau reading, has slope exactly 0.8 mu,
    # and more exponential readings only raise it.
    assert result.growth_rate_per_h <= mu * (1 + 1e-9)
    assert result.growth_rate_per_h >= 0.8 * mu
