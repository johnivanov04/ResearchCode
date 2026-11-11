"""Property-based tests: relationships that must hold for every input (spec section 8).

Data come from smooth models (exponential, logistic), where window slopes are distinct, so
the selected phase is determined by the data and not by rounding at the threshold.
"""

import math

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st
from support import make_well, no_blank

from growth_analysis.config import AnalysisConfig
from growth_analysis.exponential import analyse_well

CONFIG = AnalysisConfig(blank_method="none", min_od=1e-12)
# ln of scaled or shifted data differs by a few rounding errors per reading; the slope is
# a sum over at most a few hundred readings divided by a well-conditioned Sxx.
TOLERANCE = 1e-9

rates = st.floats(0.2, 2.0)
capacities = st.floats(0.3, 2.0)
start_fractions = st.floats(1e-3, 0.05)
intervals_h = st.sampled_from([1 / 12, 1 / 6, 0.25, 0.5])


def logistic_well(r, k, start_fraction, interval_h, *, scale=1.0, shift_h=0.0):
    n0 = start_fraction * k
    duration_h = (math.log(k / n0 - 1) + math.log(99)) / r + 1.0
    t = np.arange(0.0, duration_h, interval_h)
    od = k / (1.0 + (k / n0 - 1.0) * np.exp(-r * t))
    return make_well(t + shift_h, scale * od)


@given(r=rates, k=capacities, f=start_fractions, dt=intervals_h, scale=st.floats(1e-2, 1e2))
def test_scaling_od_does_not_change_the_rate(r, k, f, dt, scale):
    # Multiplying OD by a constant (a different path length, or OD proportional to cells
    # with another factor) adds a constant to ln OD and must not change any slope.
    base = analyse_well(logistic_well(r, k, f, dt), no_blank(), CONFIG)
    scaled = analyse_well(logistic_well(r, k, f, dt, scale=scale), no_blank(), CONFIG)
    assert scaled.status == base.status == "growth"
    assert scaled.growth_rate_per_h == pytest.approx(base.growth_rate_per_h, rel=TOLERANCE)
    assert scaled.phase_start_h == base.phase_start_h
    assert scaled.phase_end_h == base.phase_end_h


@given(r=rates, k=capacities, f=start_fractions, dt=intervals_h, shift=st.floats(-50, 1000))
def test_shifting_the_time_origin_does_not_change_the_rate(r, k, f, dt, shift):
    base = analyse_well(logistic_well(r, k, f, dt), no_blank(), CONFIG)
    shifted = analyse_well(logistic_well(r, k, f, dt, shift_h=shift), no_blank(), CONFIG)
    assert shifted.growth_rate_per_h == pytest.approx(base.growth_rate_per_h, rel=TOLERANCE)
    assert shifted.phase_start_h == pytest.approx(base.phase_start_h + shift, abs=1e-9)


@given(
    mu=st.floats(0.1, 3.0),
    n0=st.floats(1e-3, 0.1),
    n=st.integers(5, 80),
    dt=intervals_h,
)
def test_exact_exponential_growth_is_recovered(mu, n0, n, dt):
    t = np.arange(n) * dt
    od = n0 * np.exp(mu * t)
    result = analyse_well(make_well(t, od), no_blank(), CONFIG)
    if mu * (t[-1] - t[0]) >= math.log(2):  # at least one doubling: growth
        assert result.status == "growth"
        assert result.growth_rate_per_h == pytest.approx(mu, rel=TOLERANCE)
        assert result.doubling_time_h == pytest.approx(math.log(2) / mu, rel=TOLERANCE)
        assert result.r_squared == pytest.approx(1.0, abs=1e-9)
    else:
        assert result.status == "no_growth"
        assert result.growth_rate_per_h is None


@given(mu=st.floats(0.1, 3.0), n=st.integers(5, 80), dt=intervals_h)
def test_exact_exponential_decline_is_never_reported_as_growth(mu, n, dt):
    t = np.arange(n) * dt
    od = 0.5 * np.exp(-mu * t)
    result = analyse_well(make_well(t, od), no_blank(), CONFIG)
    assert result.status in ("decline", "no_growth")
    assert result.growth_rate_per_h is None
    assert result.net_rate_per_h == pytest.approx(-mu, rel=TOLERANCE)
    assert (result.status == "decline") == (math.exp(-mu * (t[-1] - t[0])) <= 0.5)


@given(r1=rates, factor=st.floats(1.2, 3.0), k=capacities, f=start_fractions)
def test_faster_growth_gives_a_larger_estimate(r1, factor, k, f):
    # Same curve shape, time compressed by `factor` (sampling also compressed), so every
    # slope is multiplied by exactly `factor`.
    slow = analyse_well(logistic_well(r1, k, f, 0.25), no_blank(), CONFIG)
    fast = analyse_well(logistic_well(r1 * factor, k, f, 0.25 / factor), no_blank(), CONFIG)
    assert fast.growth_rate_per_h == pytest.approx(factor * slow.growth_rate_per_h, rel=1e-6)
    assert fast.growth_rate_per_h > slow.growth_rate_per_h
