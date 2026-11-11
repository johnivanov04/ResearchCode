"""Exponential-phase detection and specific growth rate for one well.

Implements section 3 of ``docs/spec-growth-curve.md``. During exponential growth
OD(t) = OD0 * exp(mu * t), so ln OD(t) = ln OD0 + mu * t is a straight line whose slope is
the specific growth rate mu (1/h).

The exponential phase is found in three steps:

1. fit a line to every window of ``window_points`` consecutive valid readings;
2. start from the steepest window and extend over adjacent windows whose slope is at least
   ``min_relative_rate`` times the steepest slope;
3. fit one line to all readings in that contiguous region. Its slope is reported as mu.

The steepest window's slope is reported only as a diagnostic: with noisy data the steepest
of many windows overestimates mu (section 3.3 of the specification).

All functions here are pure: arrays in, results out, no file access.
"""

import math
from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np

from growth_analysis.blank import BlankSummary
from growth_analysis.config import AnalysisConfig
from growth_analysis.readings import Well
from growth_analysis.regression import LinearFit, fit_line

__all__ = [
    "PhaseSelection",
    "PointRecord",
    "Status",
    "WellResult",
    "analyse_well",
    "select_exponential_phase",
    "window_slopes",
]

Status = Literal["growth", "no_growth", "decline", "insufficient_data"]

# Flags that make a "growth" result not credible (section 3.4).
CREDIBILITY_FLAGS = ("low_r_squared", "high_relative_se", "excluded_reading_inside_phase")


def window_slopes(time_h: np.ndarray, ln_od: np.ndarray, window_points: int) -> np.ndarray:
    """Least-squares slope of every window of ``window_points`` consecutive readings.

    Element k is the slope fitted to readings k, k+1, ..., k + window_points - 1.

    Raises:
        ValueError: If there are fewer readings than ``window_points``.
    """
    n = len(time_h)
    if n < window_points:
        raise ValueError(f"need at least {window_points} readings, got {n}")
    return np.array(
        [
            fit_line(time_h[k : k + window_points], ln_od[k : k + window_points]).slope
            for k in range(n - window_points + 1)
        ]
    )


@dataclass(frozen=True)
class PhaseSelection:
    """Readings ``first``..``last`` (inclusive indices into the valid readings) form the
    exponential phase. ``steepest`` is the index of the steepest window."""

    first: int
    last: int
    steepest: int
    steepest_slope: float


def select_exponential_phase(
    time_h: np.ndarray, ln_od: np.ndarray, window_points: int, min_relative_rate: float
) -> PhaseSelection | None:
    """Select the exponential phase as in section 3.2, steps 2-3, of the specification.

    Returns:
        The selection, or ``None`` if no window has a positive slope.

    Example:
        Exactly exponential data: every window has the same slope, so every reading is in
        the exponential phase.

        >>> t = np.arange(8.0)
        >>> select_exponential_phase(t, 0.5 * t, window_points=5, min_relative_rate=0.8)
        PhaseSelection(first=0, last=7, steepest=0, steepest_slope=0.5)
    """
    slopes = window_slopes(time_h, ln_od, window_points)
    steepest = int(np.argmax(slopes))  # The earliest window if several are equally steep.
    steepest_slope = float(slopes[steepest])
    if not steepest_slope > 0.0:
        return None
    threshold = min_relative_rate * steepest_slope
    lo = hi = steepest
    while lo > 0 and slopes[lo - 1] >= threshold:
        lo -= 1
    while hi < len(slopes) - 1 and slopes[hi + 1] >= threshold:
        hi += 1
    return PhaseSelection(
        first=lo,
        last=hi + window_points - 1,
        steepest=steepest,
        steepest_slope=steepest_slope,
    )


@dataclass(frozen=True)
class PointRecord:
    """One reading of a sample well, and whether it was used in the growth-rate fit."""

    time_h: float
    od600: float
    od_corrected: float
    used_in_fit: bool
    exclusion_reason: str | None


@dataclass(frozen=True)
class WellResult:
    """Analysis result for one sample well. Units: 1/h for rates, h for times.

    ``growth_rate_per_h`` and ``doubling_time_h`` are set only for status ``"growth"``;
    ``credible`` is ``True`` only for a ``"growth"`` result that passes every check in
    section 3.4 of the specification.
    """

    well: str
    condition: str
    status: Status
    credible: bool
    flags: tuple[str, ...]
    growth_rate_per_h: float | None
    growth_rate_se_per_h: float | None
    doubling_time_h: float | None
    r_squared: float | None
    n_points_in_phase: int | None
    phase_start_h: float | None
    phase_end_h: float | None
    fold_change_in_phase: float | None
    fit_intercept_ln_od: float | None
    steepest_window_rate_per_h: float | None
    net_rate_per_h: float | None
    n_readings: int
    n_valid: int
    n_below_quantification_limit: int
    n_above_max_od: int
    points: tuple[PointRecord, ...] = field(repr=False)

    def summary_dict(self) -> dict[str, Any]:
        """Every field except the per-reading records, JSON-serialisable."""
        return {
            "well": self.well,
            "condition": self.condition,
            "status": self.status,
            "credible": self.credible,
            "flags": list(self.flags),
            "growth_rate_per_h": self.growth_rate_per_h,
            "growth_rate_se_per_h": self.growth_rate_se_per_h,
            "doubling_time_h": self.doubling_time_h,
            "r_squared": self.r_squared,
            "n_points_in_phase": self.n_points_in_phase,
            "phase_start_h": self.phase_start_h,
            "phase_end_h": self.phase_end_h,
            "fold_change_in_phase": self.fold_change_in_phase,
            "fit_intercept_ln_od": self.fit_intercept_ln_od,
            "steepest_window_rate_per_h": self.steepest_window_rate_per_h,
            "net_rate_per_h": self.net_rate_per_h,
            "n_readings": self.n_readings,
            "n_valid": self.n_valid,
            "n_below_quantification_limit": self.n_below_quantification_limit,
            "n_above_max_od": self.n_above_max_od,
        }


def _classify_points(
    od_corrected: np.ndarray, quantification_limit: float, max_od: float | None
) -> list[str | None]:
    """Exclusion reason for each reading (``None`` if valid for fitting)."""
    reasons: list[str | None] = []
    for value in od_corrected:
        if value < quantification_limit:
            reasons.append("below_quantification_limit")
        elif max_od is not None and value > max_od:
            reasons.append("above_max_od")
        else:
            reasons.append(None)
    return reasons


def _net_status(net_fit: LinearFit | None, duration_h: float, min_fold: float) -> Status:
    """``decline`` if OD fell by at least ``min_fold`` over the time course, else ``no_growth``."""
    if (
        net_fit is not None
        and net_fit.slope < 0
        and duration_h > 0
        and math.exp(net_fit.slope * duration_h) <= 1.0 / min_fold
    ):
        return "decline"
    return "no_growth"


def analyse_well(well: Well, blank: BlankSummary, config: AnalysisConfig) -> WellResult:
    """Estimate the specific growth rate of one well (section 3 of the specification).

    Args:
        well: Validated readings for one sample well.
        blank: Blank value and quantification limit, from
            :func:`~growth_analysis.blank.estimate_blank`.
        config: Analysis settings.

    Returns:
        The result, including a record of every reading and why any were excluded.
    """
    od_corrected = well.od600 - blank.value
    reasons = _classify_points(od_corrected, blank.quantification_limit, config.max_od)
    valid = np.array([reason is None for reason in reasons], dtype=bool)
    t_valid = well.time_h[valid]
    # Valid readings are >= quantification limit > 0, so the logarithm is always defined.
    ln_valid = np.log(od_corrected[valid])
    n_valid = int(valid.sum())

    used = np.zeros(len(reasons), dtype=bool)
    flags: list[str] = []
    net_fit = fit_line(t_valid, ln_valid) if n_valid >= 2 else None
    duration_h = float(t_valid[-1] - t_valid[0]) if n_valid >= 2 else 0.0

    base: dict[str, Any] = {
        "well": well.well,
        "condition": well.condition,
        "net_rate_per_h": net_fit.slope if net_fit is not None else None,
        "n_readings": len(reasons),
        "n_valid": n_valid,
        "n_below_quantification_limit": reasons.count("below_quantification_limit"),
        "n_above_max_od": reasons.count("above_max_od"),
    }
    empty: dict[str, Any] = {
        "growth_rate_per_h": None,
        "growth_rate_se_per_h": None,
        "doubling_time_h": None,
        "r_squared": None,
        "n_points_in_phase": None,
        "phase_start_h": None,
        "phase_end_h": None,
        "fold_change_in_phase": None,
        "fit_intercept_ln_od": None,
        "steepest_window_rate_per_h": None,
    }

    def points() -> tuple[PointRecord, ...]:
        return tuple(
            PointRecord(
                time_h=float(t),
                od600=float(raw),
                od_corrected=float(corrected),
                used_in_fit=bool(in_fit),
                exclusion_reason=reason,
            )
            for t, raw, corrected, in_fit, reason in zip(
                well.time_h, well.od600, od_corrected, used, reasons, strict=True
            )
        )

    if n_valid < config.window_points:
        return WellResult(
            **base,
            **empty,
            status="insufficient_data",
            credible=False,
            flags=("fewer_valid_readings_than_window",),
            points=points(),
        )

    selection = select_exponential_phase(
        t_valid, ln_valid, config.window_points, config.min_relative_rate
    )
    if selection is None:
        status = _net_status(net_fit, duration_h, config.min_fold_change)
        steepest = float(window_slopes(t_valid, ln_valid, config.window_points).max())
        return WellResult(
            **base,
            **{**empty, "steepest_window_rate_per_h": steepest},
            status=status,
            credible=False,
            flags=("no_window_with_positive_slope",),
            points=points(),
        )

    phase = slice(selection.first, selection.last + 1)
    fit = fit_line(t_valid[phase], ln_valid[phase])
    start_h = float(t_valid[selection.first])
    end_h = float(t_valid[selection.last])
    fold_change = math.exp(fit.slope * (end_h - start_h))

    phase_result: dict[str, Any] = {
        "steepest_window_rate_per_h": selection.steepest_slope,
        "r_squared": fit.r_squared,
        "n_points_in_phase": fit.n,
        "phase_start_h": start_h,
        "phase_end_h": end_h,
        "fold_change_in_phase": fold_change,
        "fit_intercept_ln_od": fit.intercept,
    }

    if not (fit.slope > 0 and fold_change >= config.min_fold_change):
        status = _net_status(net_fit, duration_h, config.min_fold_change)
        flags.append("less_than_min_fold_change_in_phase")
        return WellResult(
            **base,
            **{**empty, **phase_result},
            status=status,
            credible=False,
            flags=tuple(flags),
            points=points(),
        )

    # Mark the readings used in the fit, in the original (all-readings) indexing.
    valid_indices = np.flatnonzero(valid)
    used[valid_indices[phase]] = True

    if fit.r_squared is None or fit.r_squared < config.min_r_squared:
        flags.append("low_r_squared")
    # window_points >= 3, so the phase has at least 3 readings and slope_se is defined.
    slope_se = fit.slope_se if fit.slope_se is not None else math.inf
    if slope_se / fit.slope > config.max_relative_se:
        flags.append("high_relative_se")
    inside = (well.time_h > start_h) & (well.time_h < end_h) & ~valid
    if inside.any():
        flags.append("excluded_reading_inside_phase")
    if selection.first == 0:
        flags.append("phase_starts_at_first_valid_reading")
    if selection.last == n_valid - 1:
        flags.append("phase_ends_at_last_valid_reading")

    credible = not any(flag in CREDIBILITY_FLAGS for flag in flags)
    return WellResult(
        **base,
        **phase_result,
        status="growth",
        credible=credible,
        flags=tuple(flags),
        growth_rate_per_h=fit.slope,
        growth_rate_se_per_h=fit.slope_se,
        doubling_time_h=math.log(2.0) / fit.slope,
        points=points(),
    )
