"""Property-based and numerical-accuracy tests for scientific_starter.growth.

Hypothesis generates many inputs and checks relationships that must hold for every
valid input, not just the handful of examples in test_growth.py. When a property fails,
Hypothesis shrinks the input to a minimal counterexample and prints it.
"""

import math
import sys
from decimal import Decimal, localcontext

import pytest
from hypothesis import assume, example, given
from hypothesis import strategies as st

from scientific_starter.growth import doubling_time, specific_growth_rate

EPS = sys.float_info.epsilon  # 2.2e-16: spacing of floats near 1.0

# Blank-corrected optical densities. Real readings lie roughly between 1e-3 and 10, but
# the function must be correct for any positive finite float, so test a much wider range.
ods = st.floats(min_value=1e-300, max_value=1e300, allow_nan=False, allow_infinity=False)
realistic_ods = st.floats(min_value=1e-4, max_value=10.0)
times_h = st.floats(min_value=-1e4, max_value=1e4)
intervals_h = st.floats(min_value=1e-3, max_value=1e3)
rates_per_h = st.floats(min_value=-5.0, max_value=5.0)


def exact_rate(od1: float, od2: float, t1_h: float, t2_h: float) -> Decimal:
    """Reference value computed with 50 significant digits using Decimal.

    Converting a float to Decimal is exact, so this is the true rate for the exact
    floating-point inputs, independent of the implementation under test.
    """
    with localcontext() as context:
        context.prec = 50
        return (Decimal(od2).ln() - Decimal(od1).ln()) / (Decimal(t2_h) - Decimal(t1_h))


# ---------------------------------------------------------------------------------------
# Numerical accuracy against a high-precision reference
# ---------------------------------------------------------------------------------------


@given(od1=ods, od2=ods, t1_h=times_h, interval_h=intervals_h)
@example(od1=0.1, od2=0.2, t1_h=0.0, interval_h=2.0)
@example(od1=1.0, od2=1.0 + 2**-52, t1_h=0.0, interval_h=1.0)  # smallest possible change
def test_matches_high_precision_reference(od1, od2, t1_h, interval_h):
    t2_h = t1_h + interval_h
    assume(t2_h > t1_h)
    rate = specific_growth_rate(od1, od2, t1_h, t2_h)
    reference = float(exact_rate(od1, od2, t1_h, t2_h))

    # Error bound derived from how the result is computed, (ln od2 - ln od1) / (t2 - t1):
    # each log carries a relative error of a few EPS, so the numerator's absolute error is
    # a few EPS * (|ln od1| + |ln od2|); the subtraction t2 - t1 and the division each add
    # a relative error of about EPS. A factor of 8 covers library and rounding variation.
    elapsed = t2_h - t1_h
    tolerance = 8 * EPS * ((abs(math.log(od1)) + abs(math.log(od2))) / elapsed + abs(reference))
    assert abs(rate - reference) <= tolerance


@given(od1=realistic_ods, rate=rates_per_h, t1_h=times_h, interval_h=intervals_h)
def test_recovers_rate_of_exact_exponential(od1, rate, t1_h, interval_h):
    # Known-answer property: data generated from N(t) = N0 * exp(mu * t) must give back mu.
    t2_h = t1_h + interval_h
    assume(t2_h > t1_h)
    elapsed = t2_h - t1_h
    # math.exp raises OverflowError above about 709.78; stay well inside the float range.
    assume(abs(rate * elapsed) < 700)
    od2 = od1 * math.exp(rate * elapsed)
    # Exclude overflow and subnormal results, which have lost most of their precision.
    assume(sys.float_info.min <= od2 < math.inf)

    # Generating od2 rounds rate * elapsed, exp(), and the product: relative error about
    # EPS * (1 + |rate * elapsed|). Taking logs adds a few EPS * |ln od| for each reading.
    # The recovered slope divides the total by the interval.
    log_size = 1 + abs(rate * elapsed) + abs(math.log(od1)) + abs(math.log(od2))
    tolerance = 8 * EPS * log_size / elapsed + 8 * EPS * abs(rate)
    assert specific_growth_rate(od1, od2, t1_h, t2_h) == pytest.approx(rate, abs=tolerance)


# ---------------------------------------------------------------------------------------
# Structural properties that hold for every valid input
# ---------------------------------------------------------------------------------------


@given(od1=ods, od2=ods, t1_h=times_h, interval_h=intervals_h)
def test_swapping_readings_negates_the_rate(od1, od2, t1_h, interval_h):
    t2_h = t1_h + interval_h
    assume(t2_h > t1_h)
    forward = specific_growth_rate(od1, od2, t1_h, t2_h)
    backward = specific_growth_rate(od2, od1, t1_h, t2_h)
    # Mathematically exact negatives. The two directions round differently (each result is
    # within a few EPS of the truth), so compare with a relative tolerance, but require the
    # signs to be exactly opposite.
    assert forward == pytest.approx(-backward, rel=8 * EPS, abs=0)
    assert (forward > 0) == (backward < 0)
    assert (forward == 0) == (backward == 0)


@given(od1=ods, od2=ods, t1_h=times_h, interval_h=intervals_h)
def test_sign_follows_direction_of_change(od1, od2, t1_h, interval_h):
    t2_h = t1_h + interval_h
    assume(t2_h > t1_h)
    rate = specific_growth_rate(od1, od2, t1_h, t2_h)
    if od2 > od1:
        assert rate > 0
    elif od2 < od1:
        assert rate < 0
    else:
        assert rate == 0.0


@given(od1=realistic_ods, od2=realistic_ods, scale=st.floats(1e-3, 1e3), interval_h=intervals_h)
def test_rate_does_not_depend_on_od_units(od1, od2, scale, interval_h):
    # Multiplying every OD by a constant (a different path length or calibration factor)
    # must not change the growth rate.
    original = specific_growth_rate(od1, od2, 0.0, interval_h)
    scaled = specific_growth_rate(od1 * scale, od2 * scale, 0.0, interval_h)
    # Scaling rounds each OD (relative error EPS); each log adds a few EPS * |ln od|.
    log_size = 2 + sum(abs(math.log(od)) for od in (od1, od2, od1 * scale, od2 * scale))
    assert scaled == pytest.approx(original, abs=8 * EPS * log_size / interval_h)


@given(od1=realistic_ods, od2=realistic_ods, t1_h=times_h, shift=times_h, interval_h=intervals_h)
def test_rate_does_not_depend_on_time_origin(od1, od2, t1_h, shift, interval_h):
    t2_h = t1_h + interval_h
    s1, s2 = t1_h + shift, t2_h + shift
    assume(t2_h > t1_h and s2 > s1)
    original = specific_growth_rate(od1, od2, t1_h, t2_h)
    shifted = specific_growth_rate(od1, od2, s1, s2)
    # Only the interval matters, but adding the shift rounds each time by up to
    # EPS * |t|, which changes the interval slightly. Bound the relative change.
    interval_error = 4 * EPS * (abs(t1_h) + abs(t2_h) + abs(s1) + abs(s2))
    relative = interval_error / min(t2_h - t1_h, s2 - s1)
    assert shifted == pytest.approx(original, rel=4 * relative + 8 * EPS, abs=1e-300)


@given(od1=realistic_ods, od2=realistic_ods, od3=realistic_ods, d12=intervals_h, d23=intervals_h)
def test_rates_over_consecutive_intervals_combine(od1, od2, od3, d12, d23):
    # ln(od3/od1) = ln(od2/od1) + ln(od3/od2), so the rate over the whole interval is the
    # time-weighted average of the rates over the two parts.
    t1, t2 = 0.0, d12
    t3 = t2 + d23
    whole = specific_growth_rate(od1, od3, t1, t3)
    first = specific_growth_rate(od1, od2, t1, t2)
    second = specific_growth_rate(od2, od3, t2, t3)
    combined = (first * (t2 - t1) + second * (t3 - t2)) / (t3 - t1)
    log_size = abs(math.log(od1)) + abs(math.log(od2)) + abs(math.log(od3)) + 1
    assert combined == pytest.approx(whole, abs=16 * EPS * log_size / (t3 - t1))


@given(od1=realistic_ods, interval_h=intervals_h)
def test_doubling_od_over_an_interval_gives_that_doubling_time(od1, interval_h):
    rate = specific_growth_rate(od1, 2 * od1, 0.0, interval_h)
    # 2 * od1 is exact; ln(2 od1) - ln(od1) has absolute error a few EPS * |ln od1|.
    relative = 8 * EPS * (abs(math.log(od1)) + 2) / math.log(2)
    assert doubling_time(rate) == pytest.approx(interval_h, rel=relative)


@given(rate=st.floats(min_value=1e-6, max_value=1e6))
def test_doubling_time_times_rate_is_ln2(rate):
    assert doubling_time(rate) * rate == pytest.approx(math.log(2), rel=4 * EPS)


@given(slower=st.floats(min_value=1e-6, max_value=1e6), factor=st.floats(1.0001, 1e3))
def test_faster_growth_doubles_sooner(slower, factor):
    faster = slower * factor
    assert doubling_time(faster) < doubling_time(slower)
