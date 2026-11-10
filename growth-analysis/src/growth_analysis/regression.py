"""Ordinary least-squares straight-line fit with the statistics the analysis reports.

For points (x_i, y_i), i = 1..n, the fitted line is y = intercept + slope * x with

    slope     = Sxy / Sxx,   Sxx = sum (x_i - mean x)^2,  Sxy = sum (x_i - mean x)(y_i - mean y)
    intercept = mean y - slope * mean x
    SSR       = sum of squared residuals
    SE(slope) = sqrt(SSR / (n - 2) / Sxx)          (n >= 3)
    R^2       = 1 - SSR / SST,  SST = sum (y_i - mean y)^2

Sums are taken over centred values, which is far more accurate than the textbook
"sum of x*y minus n * mean x * mean y" form when x is large compared with its spread
(for example, times late in a long experiment).
"""

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike

__all__ = ["LinearFit", "fit_line"]


@dataclass(frozen=True)
class LinearFit:
    """Result of :func:`fit_line`.

    Attributes:
        slope: Fitted slope.
        intercept: Fitted value at x = 0.
        slope_se: Standard error of the slope, assuming independent errors with constant
            variance; ``None`` when n = 2 (no residual degrees of freedom).
        r_squared: Coefficient of determination; ``None`` when all y are equal (SST = 0),
            where it is undefined.
        n: Number of points.
    """

    slope: float
    intercept: float
    slope_se: float | None
    r_squared: float | None
    n: int


def fit_line(x: ArrayLike, y: ArrayLike) -> LinearFit:
    """Fit y = intercept + slope * x by ordinary least squares.

    Raises:
        ValueError: If x and y differ in length, there are fewer than two points, any
            value is not finite, or all x values are equal.

    Example:
        >>> fit = fit_line([0.0, 1.0, 2.0], [1.0, 3.0, 5.0])
        >>> fit.slope, fit.intercept, fit.r_squared
        (2.0, 1.0, 1.0)
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.ndim != 1 or x.shape != y.shape:
        raise ValueError(f"x and y must be 1-D and the same length, got {x.shape} and {y.shape}")
    n = x.size
    if n < 2:
        raise ValueError(f"at least two points are required, got {n}")
    if not (np.all(np.isfinite(x)) and np.all(np.isfinite(y))):
        raise ValueError("x and y must be finite")

    dx = x - x.mean()
    dy = y - y.mean()
    sxx = float(dx @ dx)
    if sxx == 0.0:
        raise ValueError("x values must not all be equal")
    slope = float(dx @ dy) / sxx
    intercept = float(y.mean() - slope * x.mean())

    residuals = dy - slope * dx
    ssr = float(residuals @ residuals)
    sst = float(dy @ dy)
    slope_se = math.sqrt(ssr / (n - 2) / sxx) if n > 2 else None
    # Clip tiny negative values caused by rounding when the fit is essentially perfect.
    r_squared = None if sst == 0.0 else min(1.0, max(0.0, 1.0 - ssr / sst))
    return LinearFit(slope=slope, intercept=intercept, slope_se=slope_se, r_squared=r_squared, n=n)
