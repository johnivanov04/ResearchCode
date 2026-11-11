"""Tests for condition summaries (spec section 3.5)."""

import math

import pytest

from growth_analysis.compare import summarise_conditions
from growth_analysis.exponential import WellResult


def result(well, condition, rate=None, *, status="growth", credible=True, flags=()):
    return WellResult(
        well=well,
        condition=condition,
        status=status,
        credible=credible,
        flags=tuple(flags),
        growth_rate_per_h=rate,
        growth_rate_se_per_h=None,
        doubling_time_h=math.log(2) / rate if rate else None,
        r_squared=None,
        n_points_in_phase=None,
        phase_start_h=None,
        phase_end_h=None,
        fold_change_in_phase=None,
        fit_intercept_ln_od=None,
        steepest_window_rate_per_h=None,
        net_rate_per_h=None,
        n_readings=10,
        n_valid=10,
        n_below_quantification_limit=0,
        n_above_max_od=0,
        points=(),
    )


def test_mean_sd_sem_min_max_and_doubling_time_of_the_mean():
    # Rates 0.5, 0.6, 0.7: mean 0.6, sample SD 0.1, SEM 0.1 / sqrt(3).
    summary = summarise_conditions(
        [result("B1", "x", 0.5), result("B2", "x", 0.6), result("B3", "x", 0.7)]
    )[0]
    assert summary.n_wells == 3
    assert summary.n_credible == 3
    assert summary.mean_growth_rate_per_h == pytest.approx(0.6, rel=1e-15)
    assert summary.sd_growth_rate_per_h == pytest.approx(0.1, rel=1e-12)
    assert summary.sem_growth_rate_per_h == pytest.approx(0.1 / math.sqrt(3), rel=1e-12)
    assert summary.min_growth_rate_per_h == 0.5
    assert summary.max_growth_rate_per_h == 0.7
    assert summary.doubling_time_of_mean_rate_h == pytest.approx(math.log(2) / 0.6, rel=1e-15)
    assert summary.wells_not_included == {}


def test_only_credible_growth_enters_the_statistics_and_the_rest_is_listed():
    results = [
        result("B1", "x", 0.5),
        result(
            "B2",
            "x",
            0.9,
            credible=False,
            flags=("low_r_squared", "phase_ends_at_last_valid_reading"),
        ),
        result("B3", "x", status="no_growth", credible=False),
        result("B4", "x", status="insufficient_data", credible=False),
    ]
    summary = summarise_conditions(results)[0]
    assert summary.n_wells == 4
    assert summary.n_credible == 1
    assert summary.mean_growth_rate_per_h == 0.5
    assert summary.sd_growth_rate_per_h is None  # needs at least two values
    assert summary.wells_not_included == {
        "B2": "not credible: low_r_squared",
        "B3": "no_growth",
        "B4": "insufficient_data",
    }
    assert summary.status_counts == {"growth": 2, "no_growth": 1, "insufficient_data": 1}


def test_condition_without_credible_growth_has_no_statistics():
    summary = summarise_conditions([result("D1", "z", status="decline", credible=False)])[0]
    assert summary.mean_growth_rate_per_h is None
    assert summary.doubling_time_of_mean_rate_h is None


def test_ratio_to_reference_condition_and_order_of_first_appearance():
    results = [result("C1", "slow", 0.3), result("B1", "ref", 0.6), result("C2", "slow", 0.3)]
    summaries = summarise_conditions(results, reference_condition="ref")
    assert [s.condition for s in summaries] == ["slow", "ref"]
    assert summaries[0].ratio_to_reference == pytest.approx(0.5, rel=1e-15)
    assert summaries[1].ratio_to_reference == 1.0


def test_unknown_reference_condition_is_an_error():
    with pytest.raises(ValueError, match="reference condition 'missing' not found"):
        summarise_conditions([result("B1", "x", 0.5)], reference_condition="missing")
