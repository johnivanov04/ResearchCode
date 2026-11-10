"""Figures for checking and reporting a growth-curve analysis.

Every fit should be looked at by a person: a glance at the selected exponential phase on a
log scale catches problems that no summary statistic does. The figures are:

* ``growth_curves``: blank-corrected OD against time for every well, on linear and log
  scales, coloured by condition.
* ``exponential_fits``: one panel per well on a log scale, with the readings used in the
  fit, the selected exponential phase (shaded), and the fitted exponential curve.
* ``growth_rate_comparison``: growth rates of every well by condition, with the mean and
  standard deviation of the credible ones.
* ``wells/<well>``: the same fit for one well, on linear and log scales.

This module uses Matplotlib's object-oriented API (``Figure``) rather than ``pyplot``, so
it opens no windows, keeps no global state, and works on machines without a display.
Colours are the Okabe-Ito palette, designed to be distinguishable with common forms of
colour blindness; each condition also has its own marker shape, so colour is never the only
cue.
"""

import math
import re
from collections.abc import Iterable, Sequence
from pathlib import Path

import matplotlib as mpl
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from growth_analysis.blank import BlankSummary
from growth_analysis.compare import ConditionSummary
from growth_analysis.exponential import WellResult

__all__ = [
    "FORMATS",
    "condition_styles",
    "figure_exponential_fits",
    "figure_growth_curves",
    "figure_growth_rate_comparison",
    "figure_well",
    "safe_filename",
    "save_figure",
]

FORMATS = ("png", "svg")
# Okabe & Ito palette (without yellow and black, which read poorly as thin lines on white).
_COLOURS = ("#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9")
_MARKERS = ("o", "s", "^", "D", "v", "P", "X", "h")
_GREY = "#6b7280"
_PNG_DPI = 200
# Fixed settings so the same results always produce byte-identical files on one machine.
_SAVE_RC = {"svg.hashsalt": "growth-analysis", "svg.fonttype": "none"}
_STYLE_RC = {
    "font.size": 9,
    "axes.titlesize": 9,
    "axes.labelsize": 9,
    "legend.fontsize": 8,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": "#e5e7eb",
    "grid.linewidth": 0.6,
    "lines.linewidth": 1.2,
}
_TIME_LABEL = "Time (h)"
_OD_LABEL = "Blank-corrected OD600"
_RATE_LABEL = r"Specific growth rate $\mu$ (h$^{-1}$)"


def condition_styles(conditions: Iterable[str]) -> dict[str, tuple[str, str]]:
    """Colour and marker for each condition, assigned in order of first appearance.

    Colours repeat after six conditions; markers then still distinguish them.
    """
    return {
        condition: (_COLOURS[i % len(_COLOURS)], _MARKERS[i % len(_MARKERS)])
        for i, condition in enumerate(dict.fromkeys(conditions))
    }


def safe_filename(name: str) -> str:
    """A file-name-safe version of a well identifier (letters, digits, ``.``, ``_``, ``-``).

    >>> safe_filename("A1")
    'A1'
    >>> safe_filename("../plate 1/B2")
    'plate_1_B2'
    """
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return cleaned or "well"


def save_figure(
    figure: Figure, stem: Path, formats: Sequence[str], *, overwrite: bool
) -> list[Path]:
    """Save ``figure`` as ``stem.<format>`` for each format and return the paths written.

    Raises:
        FileExistsError: If a file exists and ``overwrite`` is false.
    """
    written = []
    with mpl.rc_context(_SAVE_RC):
        for fmt in formats:
            if fmt not in FORMATS:
                raise ValueError(f"unsupported figure format {fmt!r}; use one of {FORMATS}")
            path = stem.with_suffix(f".{fmt}")
            mode = "wb" if overwrite else "xb"
            with path.open(mode) as handle:
                # Dates and software versions are left out so reruns produce identical files.
                metadata = {"Date": None} if fmt == "svg" else {"Software": None}
                figure.savefig(handle, format=fmt, dpi=_PNG_DPI, metadata=metadata)
            written.append(path)
    return written


def _phase_curve(result: WellResult) -> tuple[np.ndarray, np.ndarray] | None:
    """The fitted exponential OD(t) = exp(intercept + mu t) over the exponential phase."""
    if (
        result.status != "growth"
        or result.growth_rate_per_h is None
        or result.fit_intercept_ln_od is None
        or result.phase_start_h is None
        or result.phase_end_h is None
    ):
        return None
    t = np.linspace(result.phase_start_h, result.phase_end_h, 50)
    return t, np.exp(result.fit_intercept_ln_od + result.growth_rate_per_h * t)


def _result_label(result: WellResult) -> str:
    if result.status == "growth" and result.growth_rate_per_h is not None:
        text = (
            rf"$\mu$ = {result.growth_rate_per_h:.3g} h$^{{-1}}$, "
            f"Td = {result.doubling_time_h:.3g} h"
        )
        if result.r_squared is not None:
            text += f"\n$R^2$ = {result.r_squared:.3f}"
        return text if result.credible else text + "  (not credible)"
    labels = {
        "no_growth": "no growth detected",
        "decline": "declining",
        "insufficient_data": "too few valid readings",
    }
    return labels.get(result.status, result.status)


def _plot_fit_on_axes(
    ax: Axes,
    result: WellResult,
    colour: str,
    marker: str,
    quantification_limit: float,
    *,
    log: bool,
) -> None:
    times = np.array([p.time_h for p in result.points])
    od = np.array([p.od_corrected for p in result.points])
    used = np.array([p.used_in_fit for p in result.points])
    valid = np.array([p.exclusion_reason is None for p in result.points])

    if (
        result.status == "growth"
        and result.phase_start_h is not None
        and result.phase_end_h is not None
    ):
        ax.axvspan(result.phase_start_h, result.phase_end_h, color=colour, alpha=0.08, lw=0)

    plottable = od > 0 if log else np.ones_like(od, dtype=bool)
    # Only categories that occur are drawn, so the legend never lists something absent.
    excluded = plottable & ~valid
    if excluded.any():
        ax.plot(
            times[excluded],
            od[excluded],
            linestyle="none",
            marker="x",
            color=_GREY,
            markersize=4,
            label="excluded",
        )
    unused = plottable & valid & ~used
    if unused.any():
        ax.plot(
            times[unused],
            od[unused],
            linestyle="none",
            marker=marker,
            markersize=4,
            markerfacecolor="white",
            markeredgecolor=colour,
            label="not in fit",
        )
    if used.any():
        ax.plot(
            times[used],
            od[used],
            linestyle="none",
            marker=marker,
            markersize=4,
            color=colour,
            label="used in fit",
        )
    curve = _phase_curve(result)
    if curve is not None:
        ax.plot(*curve, color="#111827", linewidth=1.4, label="fitted exponential")
    if log:
        ax.set_yscale("log")
        ax.axhline(
            quantification_limit,
            color=_GREY,
            linestyle=":",
            linewidth=0.9,
            label="quantification limit",
        )
    else:
        # Start the linear axis at zero (or below, for negative values) so that noise around
        # a flat curve is not magnified into apparent change.
        ax.set_ylim(bottom=min(0.0, float(od.min()) if od.size else 0.0))
    ax.set_xlabel(_TIME_LABEL)


def _fit_legend_handles() -> list[Line2D]:
    """Colour-neutral legend entries for the per-well fit panels."""
    dark = "#374151"
    return [
        Line2D([], [], linestyle="none", marker="x", color=_GREY, label="excluded"),
        Line2D(
            [],
            [],
            linestyle="none",
            marker="o",
            markerfacecolor="white",
            markeredgecolor=dark,
            label="not in fit",
        ),
        Line2D([], [], linestyle="none", marker="o", color=dark, label="used in fit"),
        Line2D([], [], color="#111827", linewidth=1.4, label="fitted exponential"),
        Line2D([], [], color=_GREY, linestyle=":", label="quantification limit"),
    ]


def figure_growth_curves(results: Sequence[WellResult], blank: BlankSummary) -> Figure:
    """Blank-corrected OD against time for every well, on linear and log scales."""
    with mpl.rc_context(_STYLE_RC):
        figure = Figure(figsize=(9.0, 3.8), layout="constrained")
        linear, log = figure.subplots(1, 2)
        styles = condition_styles(r.condition for r in results)
        shown: set[str] = set()
        for result in results:
            colour, marker = styles[result.condition]
            t = np.array([p.time_h for p in result.points])
            od = np.array([p.od_corrected for p in result.points])
            label = None if result.condition in shown else result.condition
            shown.add(result.condition)
            linear.plot(t, od, color=colour, marker=marker, markersize=2.5, alpha=0.85, label=label)
            positive = od > 0
            log.plot(
                t[positive], od[positive], color=colour, marker=marker, markersize=2.5, alpha=0.85
            )
        log.set_yscale("log")
        log.axhline(blank.quantification_limit, color=_GREY, linestyle=":", linewidth=0.9)
        log.annotate(
            f"quantification limit {blank.quantification_limit:.3g}",
            xy=(0.99, blank.quantification_limit),
            xycoords=("axes fraction", "data"),
            xytext=(0, -3),
            textcoords="offset points",
            ha="right",
            va="top",
            fontsize=7,
            color=_GREY,
        )
        linear.axhline(0.0, color=_GREY, linewidth=0.6)
        linear.set(xlabel=_TIME_LABEL, ylabel=_OD_LABEL, title="Growth curves (linear scale)")
        log.set(
            xlabel=_TIME_LABEL,
            ylabel=f"{_OD_LABEL} (log scale)",
            title="Growth curves (log scale; values ≤ 0 not shown)",
        )
        linear.legend(title="Condition", frameon=False)
        return figure


def figure_exponential_fits(
    results: Sequence[WellResult], blank: BlankSummary, columns: int = 4
) -> Figure:
    """One log-scale panel per well with the exponential phase and fitted curve."""
    with mpl.rc_context(_STYLE_RC):
        n = len(results)
        columns = max(1, min(columns, n))
        rows = math.ceil(n / columns)
        figure = Figure(figsize=(2.6 * columns, 2.6 * rows + 0.6), layout="constrained")
        axes = np.atleast_1d(figure.subplots(rows, columns, squeeze=False).ravel())
        styles = condition_styles(r.condition for r in results)
        for ax, result in zip(axes, results, strict=False):
            colour, marker = styles[result.condition]
            _plot_fit_on_axes(ax, result, colour, marker, blank.quantification_limit, log=True)
            # Results go in the title, not over the data, so no reading is hidden.
            ax.set_title(
                f"{result.well} ({result.condition})\n{_result_label(result)}", fontsize=7.5
            )
        for ax in axes[::columns]:
            ax.set_ylabel(f"{_OD_LABEL} (log scale)")
        for ax in axes[n:]:
            ax.set_visible(False)
        figure.legend(
            handles=_fit_legend_handles(), loc="outside lower center", ncols=5, frameon=False
        )
        figure.suptitle("Exponential phase (shaded) and fitted curve for each well")
        return figure


def figure_well(result: WellResult, blank: BlankSummary, colour: str, marker: str) -> Figure:
    """The fit for one well, on linear and log scales."""
    with mpl.rc_context(_STYLE_RC):
        figure = Figure(figsize=(8.0, 3.4), layout="constrained")
        linear, log = figure.subplots(1, 2)
        _plot_fit_on_axes(linear, result, colour, marker, blank.quantification_limit, log=False)
        _plot_fit_on_axes(log, result, colour, marker, blank.quantification_limit, log=True)
        linear.set_ylabel(_OD_LABEL)
        log.set_ylabel(f"{_OD_LABEL} (log scale)")
        handles, labels = log.get_legend_handles_labels()
        figure.legend(handles, labels, loc="outside lower center", ncols=len(labels), frameon=False)
        summary = _result_label(result).replace("\n", ", ")
        figure.suptitle(f"Well {result.well} ({result.condition}): {summary}")
        return figure


def figure_growth_rate_comparison(
    results: Sequence[WellResult], summaries: Sequence[ConditionSummary]
) -> Figure:
    """Growth rate of every well by condition, with mean ± SD of the credible wells.

    Credible wells are filled markers; growth results that are not credible are hollow
    grey markers (shown, but not included in the mean). Wells without a growth rate are
    counted in the annotation under each condition.
    """
    with mpl.rc_context(_STYLE_RC):
        conditions = [s.condition for s in summaries]
        styles = condition_styles(conditions)
        figure = Figure(figsize=(max(4.0, 1.4 * len(conditions) + 1.5), 3.8), layout="constrained")
        ax = figure.subplots()
        for x, summary in enumerate(conditions):
            colour, marker = styles[summary]
            wells = [r for r in results if r.condition == summary]
            rated = [r for r in wells if r.growth_rate_per_h is not None]
            # Evenly spaced horizontal offsets (not random jitter) keep the figure reproducible.
            offsets = np.linspace(-0.18, 0.18, len(rated)) if len(rated) > 1 else [0.0]
            for offset, r in zip(offsets, rated, strict=False):
                if r.credible:
                    ax.plot(
                        x + offset,
                        r.growth_rate_per_h,
                        marker=marker,
                        color=colour,
                        linestyle="none",
                        markersize=6,
                    )
                else:
                    ax.plot(
                        x + offset,
                        r.growth_rate_per_h,
                        marker=marker,
                        linestyle="none",
                        markersize=6,
                        markerfacecolor="white",
                        markeredgecolor=_GREY,
                    )
        for x, summary in enumerate(summaries):
            if summary.mean_growth_rate_per_h is not None:
                ax.hlines(
                    summary.mean_growth_rate_per_h, x - 0.3, x + 0.3, color="#111827", linewidth=1.5
                )
                if summary.sd_growth_rate_per_h is not None:
                    ax.errorbar(
                        x + 0.3,
                        summary.mean_growth_rate_per_h,
                        yerr=summary.sd_growth_rate_per_h,
                        color="#111827",
                        capsize=3,
                        linewidth=1,
                    )
            no_rate = summary.n_wells - sum(
                1
                for r in results
                if r.condition == summary.condition and r.growth_rate_per_h is not None
            )
            note = f"n = {summary.n_credible} credible / {summary.n_wells}"
            if no_rate:
                note += f"\n{no_rate} without growth rate"
            ax.annotate(
                note,
                xy=(x, 0),
                xycoords=("data", "axes fraction"),
                xytext=(0, -26),
                textcoords="offset points",
                ha="center",
                va="top",
                fontsize=7,
            )
        ax.set_xticks(range(len(conditions)), conditions)
        ax.set_xlim(-0.6, len(conditions) - 0.4)
        ax.set_ylim(bottom=0)
        ax.set_ylabel(_RATE_LABEL)
        ax.set_title(
            "Growth rate by condition (filled: credible; hollow: not credible;\n"
            "bar: mean of credible wells; whisker: ±1 SD)"
        )
        return figure
