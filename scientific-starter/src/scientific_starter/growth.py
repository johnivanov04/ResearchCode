"""Exponential growth rate and doubling time from two optical density readings.

The definitions and the behaviour for every edge case are specified in
``docs/spec-growth-rate.md``. If you change this module, change the specification first.

During exponential growth, cell density follows N(t) = N0 * exp(mu * t). If optical
density (OD) is proportional to cell density, the specific growth rate between two
readings is

    mu = ln(OD2 / OD1) / (t2 - t1)

and, for positive growth, the doubling time is

    Td = ln(2) / mu

Units: optical densities are dimensionless and must already be blank-corrected (medium
background subtracted). Times are in hours, so mu is in 1/h and Td is in hours.

This is a deliberately small example of a well-specified, well-tested scientific
function. Choosing which two readings lie in the exponential phase is a scientific
decision that these functions do not make for you.
"""

import math
from decimal import Decimal
from numbers import Real

__all__ = ["doubling_time", "specific_growth_rate"]


def _finite_real(name: str, value: object) -> float:
    """Return ``value`` as a float, or raise if it is not a finite real number.

    Accepts int, float, fractions.Fraction, decimal.Decimal, and NumPy integer and
    floating scalars.
    """
    # bool is a subclass of int in Python; True/False are almost certainly a mistake here.
    if isinstance(value, bool) or not isinstance(value, Real | Decimal):
        raise TypeError(f"{name} must be a real number, got {type(value).__name__}")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite, got {number!r}")
    return number


def _log_ratio(od1: float, od2: float) -> float:
    """Return ln(od2 / od1) accurately, with the correct sign, for any positive finite floats.

    The obvious formulas both fail at the extremes:

    * ``math.log(od2 / od1)``: the division can overflow or underflow, and for nearly equal
      values the rounded ratio loses most of the information about the change.
    * ``math.log(od2) - math.log(od1)``: for nearly equal large values both logs round to
      the same float, so a real increase is reported as exactly zero growth.
    """
    if 0.5 <= od2 / od1 <= 2.0:
        # Within a factor of two, od2 - od1 is computed exactly (Sterbenz lemma) and log1p
        # stays accurate for tiny arguments, so even the smallest possible change in OD
        # gives a rate with the right sign. Equal values give exactly +0.0.
        return math.log1p((od2 - od1) / od1)
    # Otherwise |ln(od2 / od1)| > ln 2, so subtracting logs is accurate, and it cannot
    # overflow or underflow because the log of a positive finite float is always finite.
    return math.log(od2) - math.log(od1)


def specific_growth_rate(od1: float, od2: float, t1_h: float, t2_h: float) -> float:
    """Return the specific growth rate mu, in 1/h, between two readings.

    mu = ln(od2 / od1) / (t2_h - t1_h)

    Args:
        od1: Blank-corrected optical density at time ``t1_h``. Dimensionless, finite, > 0.
        od2: Blank-corrected optical density at time ``t2_h``. Dimensionless, finite, > 0.
        t1_h: Time of the first reading, in hours. Finite.
        t2_h: Time of the second reading, in hours. Finite and strictly later than ``t1_h``.
            If your instrument exports minutes or seconds, convert to hours first.

    Returns:
        The specific growth rate in 1/h:

        * positive when the optical density increased,
        * exactly ``0.0`` when ``od2 == od1``,
        * negative when the optical density decreased. A negative rate is returned rather
          than rejected, because it may be real (death, lysis) or a measurement problem
          that a person should look at.

    Raises:
        TypeError: If an argument is not a real number (including ``bool``).
        ValueError: If an argument is NaN or infinite, an optical density is not
            positive, ``t2_h`` is not later than ``t1_h``, or the result is not finite
            (the time interval is too short to represent the rate).

    Example:
        >>> round(specific_growth_rate(0.1, 0.2, 0.0, 2.0), 8)
        0.34657359
    """
    od1 = _finite_real("od1", od1)
    od2 = _finite_real("od2", od2)
    t1_h = _finite_real("t1_h", t1_h)
    t2_h = _finite_real("t2_h", t2_h)

    if od1 <= 0.0:
        raise ValueError(f"od1 must be > 0 (blank-corrected optical density), got {od1!r}")
    if od2 <= 0.0:
        raise ValueError(f"od2 must be > 0 (blank-corrected optical density), got {od2!r}")
    if not t2_h > t1_h:
        raise ValueError(f"t2_h must be later than t1_h, got t1_h={t1_h!r}, t2_h={t2_h!r}")

    elapsed_h = t2_h - t1_h
    if not math.isfinite(elapsed_h):
        raise ValueError(f"time interval overflows: t1_h={t1_h!r}, t2_h={t2_h!r}")

    rate_per_h = _log_ratio(od1, od2) / elapsed_h
    if not math.isfinite(rate_per_h):
        raise ValueError(f"time interval {elapsed_h!r} h is too short to give a finite growth rate")
    return rate_per_h


def doubling_time(rate_per_h: float) -> float:
    """Return the doubling time, in hours, for a specific growth rate in 1/h.

    Td = ln(2) / rate_per_h

    Behaviour by sign of the rate:

    * ``rate_per_h > 0``: returns ln(2) / rate_per_h. For extremely small positive rates
      the result can overflow to ``math.inf``.
    * ``rate_per_h == 0``: returns ``math.inf``. A population that does not grow never
      doubles. Measured rates are rarely exactly zero, so decide in your specification
      what counts as "no growth" for your data; this function does not apply a tolerance.
    * ``rate_per_h < 0``: raises ``ValueError``. A declining population has no doubling
      time. If you need a halving time, compute ``math.log(2) / abs(rate_per_h)``
      explicitly so that the choice is visible in your analysis code.

    Raises:
        TypeError: If ``rate_per_h`` is not a real number (including ``bool``).
        ValueError: If ``rate_per_h`` is NaN, infinite, or negative.

    Example:
        >>> doubling_time(math.log(2) / 3.0)
        3.0
    """
    rate_per_h = _finite_real("rate_per_h", rate_per_h)
    if rate_per_h < 0.0:
        raise ValueError(
            f"doubling time is undefined for a negative growth rate ({rate_per_h!r} 1/h); "
            "the population is declining"
        )
    if rate_per_h == 0.0:
        return math.inf
    return math.log(2.0) / rate_per_h
