"""Known-answer and edge-case tests for growth-rate estimation (spec sections 3, 5, 6).

Expected values come from the mathematics of the test curves, never from running the code:
for exactly exponential data, ln OD is exactly linear in time, so every window and the
whole curve have slope mu.
"""

import math
from fractions import Fraction

import numpy as np
import pytest
from support import make_well, no_blank

from growth_analysis.blank import BlankSummary
from growth_analysis.config import AnalysisConfig
from growth_analysis.exponential import analyse_well, select_exponential_phase, window_slopes

# Exact exponential data: the least-squares slope is exact up to a few hundred rounding
# errors (about 1e-13 relative); 1e-9 leaves room for platform differences in log and exp.
EXACT = 1e-9
CONFIG = AnalysisConfig(blank_method="none", min_od=1e-6)


def exponential(t, n0, mu):
    return n0 * np.exp(mu * np.asarray(t, dtype=float))


def test_exact_exponential_with_blank_gives_mu_and_doubling_time():
    t = np.arange(0.0, 8.0 + 1e-9, 0.5)
    raw = exponential(t, 0.02, 0.7) + 0.05
    blank = BlankSummary("mean", "blank", ("A1",), 17, 0.05, 0.0, 0.05, 0.05, 0.005)
    result = analyse_well(make_well(t, raw), blank, AnalysisConfig())
    assert result.status == "growth"
    assert result.credible
    assert result.growth_rate_per_h == pytest.approx(0.7, rel=EXACT)
    assert result.doubling_time_h == pytest.approx(math.log(2) / 0.7, rel=EXACT)
    assert result.n_points_in_phase == t.size  # every window has the same slope
    assert result.phase_start_h == 0.0
    assert result.phase_end_h == 8.0
    assert result.r_squared == pytest.approx(1.0, abs=1e-12)
    assert result.fold_change_in_phase == pytest.approx(math.exp(0.7 * 8), rel=EXACT)
    assert result.fit_intercept_ln_od == pytest.approx(math.log(0.02), rel=EXACT)
    assert set(result.flags) == {
        "phase_starts_at_first_valid_reading",
        "phase_ends_at_last_valid_reading",
    }
    assert all(point.used_in_fit for point in result.points)


def test_doubling_time_is_ln2_over_rate_exactly():
    t = np.arange(0.0, 6.0, 0.25)
    result = analyse_well(make_well(t, exponential(t, 0.01, 1.3)), no_blank(), CONFIG)
    assert result.doubling_time_h == math.log(2.0) / result.growth_rate_per_h


def test_exponential_decline_is_reported_as_decline_with_its_net_rate():
    t = np.arange(0.0, 10.0 + 1e-9, 0.5)
    result = analyse_well(make_well(t, exponential(t, 0.8, -0.3)), no_blank(), CONFIG)
    assert result.status == "decline"
    assert not result.credible
    assert result.growth_rate_per_h is None
    assert result.doubling_time_h is None
    assert result.net_rate_per_h == pytest.approx(-0.3, rel=EXACT)
    assert "no_window_with_positive_slope" in result.flags


def test_constant_od_is_no_growth_with_zero_net_rate():
    t = np.arange(0.0, 10.0, 0.5)
    result = analyse_well(make_well(t, np.full(t.size, 0.3)), no_blank(), CONFIG)
    assert result.status == "no_growth"
    assert result.net_rate_per_h == 0.0
    assert result.growth_rate_per_h is None
    assert result.steepest_window_rate_per_h == 0.0


def test_slow_decline_of_less_than_half_is_no_growth_not_decline():
    # Net fold change exp(-0.05 * 9.5) = 0.62 > 1/2: not enough to call a decline.
    t = np.arange(0.0, 10.0, 0.5)
    result = analyse_well(make_well(t, exponential(t, 0.5, -0.05)), no_blank(), CONFIG)
    assert result.status == "no_growth"


def test_growth_of_less_than_one_doubling_is_no_growth():
    # exp(0.05 * 9.5) = 1.61 < 2 across the whole time course.
    t = np.arange(0.0, 10.0, 0.5)
    result = analyse_well(make_well(t, exponential(t, 0.1, 0.05)), no_blank(), CONFIG)
    assert result.status == "no_growth"
    assert result.growth_rate_per_h is None
    assert "less_than_min_fold_change_in_phase" in result.flags
    assert not any(point.used_in_fit for point in result.points)


def test_stationary_phase_only_is_no_growth():
    # A culture already at its carrying capacity: logistic values within 1e-6 of K.
    t = np.arange(0.0, 6.0, 0.25)
    k = 1.2
    od = k / (1 + 1e-6 * np.exp(-1.0 * t))
    result = analyse_well(make_well(t, od), no_blank(), CONFIG)
    assert result.status == "no_growth"


def test_too_few_valid_readings_is_insufficient_data():
    t = np.arange(4.0)
    result = analyse_well(make_well(t, exponential(t, 0.1, 1.0)), no_blank(), CONFIG)
    assert result.status == "insufficient_data"
    assert result.growth_rate_per_h is None
    assert result.n_valid == 4
    assert result.flags == ("fewer_valid_readings_than_window",)


def test_readings_below_quantification_limit_are_excluded_and_recorded():
    t = np.arange(0.0, 6.0, 0.5)
    od = exponential(t, 0.002, 1.0)  # 0.002 ... 0.12
    result = analyse_well(make_well(t, od), no_blank(0.01), CONFIG)
    below = od < 0.01
    assert result.n_below_quantification_limit == int(below.sum()) == 4
    reasons = [point.exclusion_reason for point in result.points]
    assert reasons[:4] == ["below_quantification_limit"] * 4
    assert all(reason is None for reason in reasons[4:])
    assert not any(point.used_in_fit for point in result.points[:4])
    assert result.growth_rate_per_h == pytest.approx(1.0, rel=EXACT)
    assert result.phase_start_h == 2.0


def test_non_positive_corrected_od_is_excluded_never_logged():
    t = np.arange(0.0, 6.0, 0.5)
    od = exponential(t, 0.05, 0.8)
    od[1] = 0.0
    od[2] = -0.003
    result = analyse_well(make_well(t, od), no_blank(1e-6), CONFIG)
    assert [p.exclusion_reason for p in result.points[1:3]] == ["below_quantification_limit"] * 2
    assert result.growth_rate_per_h == pytest.approx(0.8, rel=EXACT)


def test_readings_above_max_od_are_excluded():
    t = np.arange(0.0, 6.0, 0.5)
    od = exponential(t, 0.02, 0.8)  # up to 0.02 * e^4.4 = 1.63
    config = AnalysisConfig(blank_method="none", min_od=1e-6, max_od=1.0)
    result = analyse_well(make_well(t, od), no_blank(1e-6), config)
    assert result.n_above_max_od == int((od > 1.0).sum()) > 0
    assert result.phase_end_h < 6.0
    assert result.growth_rate_per_h == pytest.approx(0.8, rel=EXACT)


def test_excluded_reading_inside_the_phase_makes_the_result_not_credible():
    t = np.arange(0.0, 6.0, 0.5)
    od = exponential(t, 0.05, 0.8)
    od[5] = 0.0  # a single dropout in the middle of exponential growth
    result = analyse_well(make_well(t, od), no_blank(1e-6), CONFIG)
    assert result.status == "growth"
    assert "excluded_reading_inside_phase" in result.flags
    assert not result.credible


def test_noisy_short_phase_is_flagged_low_r_squared_and_high_se():
    # Alternating +-15% errors on a slow exponential: the fit succeeds mathematically, but
    # R^2 and the relative standard error show that it is not a credible estimate.
    t = np.arange(0.0, 8.0, 0.5)
    od = exponential(t, 0.05, 0.12) * np.where(np.arange(t.size) % 2 == 0, 1.15, 0.85)
    result = analyse_well(make_well(t, od), no_blank(), CONFIG)
    assert result.status == "growth"
    assert not result.credible
    assert "low_r_squared" in result.flags
    assert "high_relative_se" in result.flags


def exact_slope(x, y):
    """Least-squares slope in exact rational arithmetic (independent of the package)."""
    xs = [Fraction(v) for v in x]
    ys = [Fraction(v) for v in y]
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    return sum((a - mx) * (b - my) for a, b in zip(xs, ys, strict=True)) / sum(
        (a - mx) ** 2 for a in xs
    )


def test_lag_exponential_and_stationary_segments():
    # ln OD is piecewise linear: flat to 2 h, slope 1.0 to 6 h, flat after (readings every
    # 0.25 h, five-point windows). Every window inside the exponential segment has slope
    # exactly 1.0, the maximum, so the phase contains the whole segment. A window with one
    # flat reading has slope exactly 0.8 (at the threshold, so rounding decides) and one
    # with two flat readings has 0.5, so the phase gains at most one flat reading per end.
    step = Fraction(1, 4)
    t = np.arange(0.0, 10.0 + 1e-9, 0.25)
    ln_od = math.log(0.01) + np.clip(t - 2.0, 0.0, 4.0)
    result = analyse_well(make_well(t, np.exp(ln_od)), no_blank(), CONFIG)
    assert result.status == "growth"
    assert result.steepest_window_rate_per_h == pytest.approx(1.0, rel=EXACT)
    assert 1.75 <= result.phase_start_h <= 2.0
    assert 6.0 <= result.phase_end_h <= 6.25
    # Bounds: the local rate never exceeds 1.0; the worst case adds one flat reading at
    # each end, whose exact least-squares slope is computed here.
    worst_x = [Fraction(7, 4) + i * step for i in range(19)]
    worst_y = [min(max(x - 2, 0), 4) for x in worst_x]
    lower = float(exact_slope(worst_x, worst_y))
    assert lower * (1 - EXACT) <= result.growth_rate_per_h <= 1.0 + EXACT


def test_window_slopes_known_answer():
    t = np.arange(6.0)
    z = np.array([0.0, 0.0, 1.0, 2.0, 3.0, 3.0])
    np.testing.assert_allclose(window_slopes(t, z, 3), [0.5, 1.0, 1.0, 0.5], rtol=1e-15)
    with pytest.raises(ValueError, match="at least 7"):
        window_slopes(t, z, 7)


def test_phase_selection_starts_from_the_steepest_window_and_stops_below_threshold():
    t = np.arange(8.0)
    # Window slopes (3 points) for these values: 0.5, 2.0, 1.75, 0.5, 0.5, 0.0.
    z = np.array([0.0, 0.0, 1.0, 4.0, 4.5, 5.0, 5.5, 5.0])
    slopes = window_slopes(t, z, 3)
    steepest = int(np.argmax(slopes))
    selection = select_exponential_phase(t, z, window_points=3, min_relative_rate=0.8)
    assert selection.steepest == steepest
    assert selection.steepest_slope == slopes[steepest]
    kept = [k for k in range(len(slopes)) if slopes[k] >= 0.8 * slopes[steepest]]
    # The kept windows here are contiguous, so the phase spans exactly their readings.
    assert kept == list(range(kept[0], kept[-1] + 1))
    assert (selection.first, selection.last) == (kept[0], kept[-1] + 2)


def test_phase_selection_returns_none_without_a_positive_slope():
    t = np.arange(6.0)
    assert select_exponential_phase(t, -0.1 * t, 3, 0.8) is None
    assert select_exponential_phase(t, np.zeros(6), 3, 0.8) is None


def test_point_records_keep_raw_and_corrected_values():
    t = np.arange(0.0, 4.0, 0.5)
    raw = exponential(t, 0.05, 0.9) + 0.04
    blank = BlankSummary("mean", "blank", ("A1",), 8, 0.04, 0.0, 0.04, 0.04, 0.005)
    result = analyse_well(make_well(t, raw), blank, AnalysisConfig())
    first = result.points[0]
    assert first.time_h == 0.0
    assert first.od600 == raw[0]
    assert first.od_corrected == raw[0] - 0.04
