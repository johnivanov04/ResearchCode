"""Known-answer, edge-case, and invalid-input tests for scientific_starter.growth.

Every expected value comes from the mathematics in docs/spec-growth-rate.md, never from
running the code. Tolerances are stated next to each comparison.
"""

import math
from decimal import Decimal, localcontext
from fractions import Fraction

import pytest

from scientific_starter.growth import doubling_time, specific_growth_rate

# Relative tolerance for known-answer tests. The inputs (0.1, 0.2, ...) are not exactly
# representable in binary floating point, so results can differ from the exact value by a
# few units in the last place (about 1e-16 relative). 1e-12 leaves a wide safety margin
# while still catching any real formula error, which would be off by far more.
REL_TOL = 1e-12


# ---------------------------------------------------------------------------------------
# Known answers
# ---------------------------------------------------------------------------------------


def test_reference_case_from_specification():
    # OD doubles from 0.1 to 0.2 in 2 h: mu = ln(2) / 2 h, Td = 2 h.
    rate = specific_growth_rate(0.1, 0.2, 0.0, 2.0)
    assert rate == pytest.approx(0.34657359027997264, rel=REL_TOL)
    assert rate == pytest.approx(math.log(2) / 2, rel=REL_TOL)
    assert doubling_time(rate) == pytest.approx(2.0, rel=REL_TOL)


@pytest.mark.parametrize(
    ("od1", "od2", "t1_h", "t2_h", "expected_rate_per_h"),
    [
        # Ten-fold increase in 1 h: mu = ln(10).
        (0.05, 0.5, 0.0, 1.0, math.log(10)),
        # Three doublings (1 -> 8) in 3 h: mu = ln(2) per hour.
        (1.0, 8.0, 0.0, 3.0, math.log(2)),
        # Times need not start at zero; only the interval matters.
        (0.1, 0.2, 10.0, 12.0, math.log(2) / 2),
        # Negative times are allowed (for example, time relative to an induction event).
        (0.1, 0.2, -1.0, 1.0, math.log(2) / 2),
        # Halving in 2 h: mu = -ln(2) / 2.
        (0.4, 0.2, 0.0, 2.0, -math.log(2) / 2),
    ],
)
def test_known_rates(od1, od2, t1_h, t2_h, expected_rate_per_h):
    assert specific_growth_rate(od1, od2, t1_h, t2_h) == pytest.approx(
        expected_rate_per_h, rel=REL_TOL
    )


@pytest.mark.parametrize(
    ("rate_per_h", "expected_hours"),
    [
        (math.log(2), 1.0),
        (math.log(2) / 3, 3.0),
        (math.log(2) * 2, 0.5),
        # Ten-fold increase in 1 h (mu = ln 10): Td = ln 2 / ln 10, about 0.30103 h.
        (math.log(10), math.log(2) / math.log(10)),
    ],
)
def test_known_doubling_times(rate_per_h, expected_hours):
    assert doubling_time(rate_per_h) == pytest.approx(expected_hours, rel=REL_TOL)


def test_minutes_give_a_per_minute_rate():
    # Units pitfall: passing minutes where hours are expected returns a per-minute rate,
    # 60 times smaller. Convert to hours before calling.
    per_minute = specific_growth_rate(0.1, 0.2, 0.0, 120.0)
    per_hour = specific_growth_rate(0.1, 0.2, 0.0, 120.0 / 60.0)
    assert per_minute * 60 == pytest.approx(per_hour, rel=REL_TOL)


def test_accepts_other_real_number_types():
    # ints, Fractions, and Decimals are real numbers and are converted to float.
    expected = math.log(2) / 2
    assert specific_growth_rate(1, 2, 0, 2) == pytest.approx(expected, rel=REL_TOL)
    assert specific_growth_rate(
        Fraction(1, 10), Fraction(2, 10), Fraction(0), Fraction(2)
    ) == pytest.approx(expected, rel=REL_TOL)
    assert specific_growth_rate(Decimal("0.1"), 0.2, 0, 2) == pytest.approx(expected, rel=REL_TOL)


# ---------------------------------------------------------------------------------------
# Zero and negative growth: behaviour defined in the specification
# ---------------------------------------------------------------------------------------


def test_zero_growth_is_exactly_zero():
    rate = specific_growth_rate(0.37, 0.37, 0.0, 5.0)
    assert rate == 0.0
    assert math.copysign(1.0, rate) == 1.0  # +0.0, not -0.0


def test_zero_growth_never_doubles():
    assert doubling_time(0.0) == math.inf
    assert doubling_time(-0.0) == math.inf


def test_negative_growth_rate_is_returned_not_hidden():
    rate = specific_growth_rate(0.2, 0.1, 0.0, 1.0)
    assert rate == pytest.approx(-math.log(2), rel=REL_TOL)


def test_negative_growth_has_no_doubling_time():
    with pytest.raises(ValueError, match="negative growth rate"):
        doubling_time(-0.1)


@pytest.mark.parametrize("od1", [1e-300, 1e-3, 0.1, 1.0, 1.9999999999999998, 7.5, 1e300])
@pytest.mark.parametrize("direction", [math.inf, -math.inf])
def test_smallest_possible_change_in_od_has_correct_sign_and_size(od1, direction):
    # od2 is the adjacent floating-point number: the smallest change that can be represented.
    # A naive ln(od2) - ln(od1) returns exactly 0.0 here for large values (both logs round
    # to the same float), and ln(od2 / od1) can be off by 50%. Found by a property test.
    od2 = math.nextafter(od1, direction)
    rate = specific_growth_rate(od1, od2, 0.0, 1.0)
    with localcontext() as context:
        context.prec = 50
        exact = float(Decimal(od2).ln() - Decimal(od1).ln())
    assert rate == pytest.approx(exact, rel=1e-12)
    assert (rate > 0) == (od2 > od1)


def test_tiny_positive_rate_doubling_time_overflows_to_infinity():
    assert doubling_time(5e-324) == math.inf


# ---------------------------------------------------------------------------------------
# Invalid inputs
# ---------------------------------------------------------------------------------------

VALID = {"od1": 0.1, "od2": 0.2, "t1_h": 0.0, "t2_h": 2.0}


@pytest.mark.parametrize("name", ["od1", "od2"])
@pytest.mark.parametrize("bad_od", [0.0, -0.0, -0.1, -1e-300])
def test_rejects_non_positive_optical_density(name, bad_od):
    with pytest.raises(ValueError, match=f"{name} must be > 0"):
        specific_growth_rate(**{**VALID, name: bad_od})


@pytest.mark.parametrize("name", ["od1", "od2", "t1_h", "t2_h"])
@pytest.mark.parametrize("bad_value", [math.nan, math.inf, -math.inf])
def test_rejects_nan_and_infinity(name, bad_value):
    with pytest.raises(ValueError, match=f"{name} must be finite"):
        specific_growth_rate(**{**VALID, name: bad_value})


@pytest.mark.parametrize("name", ["od1", "od2", "t1_h", "t2_h"])
@pytest.mark.parametrize("bad_value", [None, "0.1", True, False, [0.1], 1 + 0j])
def test_rejects_non_real_types(name, bad_value):
    with pytest.raises(TypeError, match=f"{name} must be a real number"):
        specific_growth_rate(**{**VALID, name: bad_value})


@pytest.mark.parametrize(("t1_h", "t2_h"), [(2.0, 2.0), (2.0, 1.0), (0.0, -0.0), (1.0, 0.0)])
def test_rejects_times_that_do_not_increase(t1_h, t2_h):
    with pytest.raises(ValueError, match="t2_h must be later than t1_h"):
        specific_growth_rate(0.1, 0.2, t1_h, t2_h)


def test_rejects_interval_that_overflows():
    with pytest.raises(ValueError, match="time interval overflows"):
        specific_growth_rate(0.1, 0.2, -1e308, 1e308)


def test_rejects_interval_too_short_for_a_finite_rate():
    # ln(1e300 / 1e-300) is about 1382; divided by the smallest positive float it overflows.
    with pytest.raises(ValueError, match="too short"):
        specific_growth_rate(1e-300, 1e300, 0.0, 5e-324)


@pytest.mark.parametrize("bad_rate", [math.nan, math.inf, -math.inf])
def test_doubling_time_rejects_non_finite_rates(bad_rate):
    with pytest.raises(ValueError, match="must be finite"):
        doubling_time(bad_rate)


@pytest.mark.parametrize("bad_rate", [None, "0.3", True])
def test_doubling_time_rejects_non_real_types(bad_rate):
    with pytest.raises(TypeError, match="must be a real number"):
        doubling_time(bad_rate)
