"""Tests for the least-squares line fit.

The reference is an exact least-squares fit in rational arithmetic (``fractions``), which
shares no code with the implementation.
"""

import math
from fractions import Fraction

import numpy as np
import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from growth_analysis.regression import fit_line

EPS = np.finfo(float).eps


def exact_fit(x: list[float], y: list[float]) -> tuple[Fraction, Fraction]:
    """Exact slope and intercept by the normal equations in rational arithmetic."""
    xs = [Fraction(v) for v in x]
    ys = [Fraction(v) for v in y]
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((a - mx) ** 2 for a in xs)
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys, strict=True))
    slope = sxy / sxx
    return slope, my - slope * mx


def test_known_line_is_recovered_exactly():
    fit = fit_line([0.0, 1.0, 2.0, 3.0], [1.0, 3.0, 5.0, 7.0])
    assert fit.slope == 2.0
    assert fit.intercept == 1.0
    assert fit.r_squared == 1.0
    assert fit.slope_se == 0.0
    assert fit.n == 4


def test_standard_error_and_r_squared_hand_calculation():
    # x = 0, 1, 2, 3 and y = 0, 2, 2, 4:
    #   mean x = 1.5, mean y = 2, Sxx = 5, Sxy = 6, slope = 1.2, intercept = 0.2
    #   fitted = 0.2, 1.4, 2.6, 3.8; residuals = -0.2, 0.6, -0.6, 0.2; SSR = 0.8
    #   SST = 8, R^2 = 1 - 0.8 / 8 = 0.9, SE = sqrt(0.8 / 2 / 5) = sqrt(0.08)
    fit = fit_line([0.0, 1.0, 2.0, 3.0], [0.0, 2.0, 2.0, 4.0])
    assert fit.slope == pytest.approx(1.2, rel=1e-15)
    assert fit.intercept == pytest.approx(0.2, rel=1e-14)
    assert fit.r_squared == pytest.approx(0.9, rel=1e-14)
    assert fit.slope_se == pytest.approx(math.sqrt(0.08), rel=1e-14)


def test_two_points_have_no_standard_error():
    fit = fit_line([0.0, 2.0], [1.0, 0.0])
    assert fit.slope == -0.5
    assert fit.slope_se is None


def test_r_squared_is_undefined_for_constant_y():
    fit = fit_line([0.0, 1.0, 2.0], [3.0, 3.0, 3.0])
    assert fit.slope == 0.0
    assert fit.r_squared is None


def test_large_time_offsets_do_not_lose_precision():
    # Centred sums keep full accuracy when x is large compared with its spread; the
    # uncentred textbook formula loses about log10(1e6^2) = 12 digits here.
    x = 1e6 + np.arange(5.0)
    y = 0.25 * np.arange(5.0)
    assert fit_line(x, y).slope == pytest.approx(0.25, rel=1e-12)


@pytest.mark.parametrize(
    ("x", "y", "message"),
    [
        ([0.0], [1.0], "at least two"),
        ([0.0, 1.0], [1.0], "same length"),
        ([1.0, 1.0, 1.0], [0.0, 1.0, 2.0], "must not all be equal"),
        ([0.0, math.nan], [1.0, 2.0], "finite"),
        ([0.0, 1.0], [1.0, math.inf], "finite"),
    ],
)
def test_invalid_input_is_rejected(x, y, message):
    with pytest.raises(ValueError, match=message):
        fit_line(x, y)


small = st.integers(min_value=-1000, max_value=1000).map(float)


@given(data=st.lists(st.tuples(st.integers(0, 200).map(float), small), min_size=3, max_size=40))
def test_matches_exact_rational_least_squares(data):
    x = [a for a, _ in data]
    y = [b for _, b in data]
    assume(len(set(x)) > 1)
    slope, intercept = exact_fit(x, y)
    fit = fit_line(x, y)
    # Rounding bound: each of the n products and sums contributes at most a few units of
    # EPS relative to the magnitude of the terms, so the error is bounded by roughly
    # n * EPS * (sum of |terms|) / |result|. Compute that bound from the data.
    xs = np.array(x)
    ys = np.array(y)
    dx = xs - xs.mean()
    dy = ys - ys.mean()
    sxx = float(dx @ dx)
    terms = float(np.abs(dx) @ np.abs(dy)) / sxx
    tolerance = 8 * len(x) * EPS * (terms + abs(float(slope)) + 1.0)
    assert abs(fit.slope - float(slope)) <= tolerance
    intercept_scale = abs(float(intercept)) + (terms + abs(float(slope))) * xs.max() + 1.0
    assert abs(fit.intercept - float(intercept)) <= 8 * len(x) * EPS * intercept_scale
