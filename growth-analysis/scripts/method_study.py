"""Reproduce the design study behind the method's defaults (spec section 3.3).

Run from the project directory::

    uv run python scripts/method_study.py > docs/method-study.md

All data are synthetic, generated with fixed seeds, so the output is reproducible on a
given platform. The study uses the package's own functions, so it describes the method as
implemented. It answers two questions:

1. How biased are (a) the steepest window's slope and (b) the reported growth rate, for
   several settings of ``min_relative_rate``, on noisy exponential data and on noise-free
   logistic data?
2. On the synthetic sample plate (additive and multiplicative noise), how does the
   quantification limit (``blank_sd_multiple``) affect the estimates, compared with the
   method's own result on the same curves without noise?
"""

import tempfile
from pathlib import Path

import numpy as np

from growth_analysis import AnalysisConfig, analyse_plate, fit_line, read_plate
from growth_analysis.blank import BlankSummary
from growth_analysis.exponential import analyse_well, select_exponential_phase
from growth_analysis.readings import Well
from growth_analysis.synthetic import (
    SAMPLE_CULTURES,
    SAMPLE_DURATION_MIN,
    SAMPLE_INTERVAL_MIN,
    csv_text,
    exponential_od,
    logistic_od,
    sample_plate_rows,
)

STUDY_SEED = 1
REPLICATES = 400
PLATE_SEEDS = range(150)
RELATIVE_RATES = (0.8, 0.9, 0.95)
NOISE_SDS = (0.01, 0.03, 0.05)


def estimate(time_h: np.ndarray, od: np.ndarray, q: float) -> tuple[float, float]:
    """Reported rate and steepest-window slope for one curve (default window, given q)."""
    ln_od = np.log(od)
    selection = select_exponential_phase(time_h, ln_od, window_points=5, min_relative_rate=q)
    if selection is None:
        raise RuntimeError("no positive window in a growing curve")
    phase = slice(selection.first, selection.last + 1)
    return fit_line(time_h[phase], ln_od[phase]).slope, selection.steepest_slope


def exponential_study() -> None:
    mu = 0.8
    time_h = np.arange(0.0, 8.0 + 1e-9, 0.25)
    rng = np.random.default_rng(STUDY_SEED)
    print("## 1. Noisy exponential data\n")
    print(
        f"OD = 0.01 exp({mu} t) exp(e), e ~ Normal(0, SD), readings every 15 min for 8 h, "
        f"{REPLICATES} curves per row. Bias is (mean estimate / true rate) - 1.\n"
    )
    print(
        "| SD of ln OD | min_relative_rate | Reported rate: bias | Reported rate: SD "
        "| Steepest window: bias |"
    )
    print("| --- | --- | --- | --- | --- |")
    for sd in NOISE_SDS:
        curves = [
            exponential_od(time_h, 0.01, mu) * np.exp(rng.normal(0.0, sd, time_h.size))
            for _ in range(REPLICATES)
        ]
        for q in RELATIVE_RATES:
            results = np.array([estimate(time_h, od, q) for od in curves]) / mu
            reported, steepest = results[:, 0], results[:, 1]
            print(
                f"| {sd} | {q} | {reported.mean() - 1:+.2%} | {reported.std(ddof=1):.2%} "
                f"| {steepest.mean() - 1:+.2%} |"
            )
    print()


def logistic_study() -> None:
    r, k, n0 = 1.2, 1.1, 0.01
    time_h = np.arange(0.0, 12.0 + 1e-9, 0.25)
    od = logistic_od(time_h, n0, k, r)
    print("## 2. Noise-free logistic data\n")
    print(
        f"N(t) logistic with r = {r}/h, K = {k}, N0 = {n0}, readings every 15 min for 12 h "
        "(the website's illustrative curve without rounding).\n"
    )
    print("| min_relative_rate | Reported rate / r | Steepest window / r |")
    print("| --- | --- | --- |")
    for q in RELATIVE_RATES:
        reported, steepest = estimate(time_h, od, q)
        print(f"| {q} | {reported / r:.3f} | {steepest / r:.3f} |")
    print()


def noise_free_rate(culture, quantification_limit: float) -> float:
    """The method's estimate on the culture's noise-free curve, with the given limit.

    This, not r, is the reference for bias: on a logistic curve the method reports an
    average rate over the exponential phase, which is below r even without noise.
    """
    time_h = np.arange(0, SAMPLE_DURATION_MIN + 1, SAMPLE_INTERVAL_MIN) / 60.0
    od = logistic_od(time_h, culture.n0, culture.k, culture.r_per_h, culture.lag_h)
    well = Well("noise-free", culture.condition, time_h, od, tuple(range(time_h.size)))
    blank = BlankSummary("none", "blank", (), 0, 0.0, None, None, None, quantification_limit)
    result = analyse_well(well, blank, AnalysisConfig(blank_method="none"))
    if result.growth_rate_per_h is None:
        raise RuntimeError("no growth rate on a noise-free growing curve")
    return result.growth_rate_per_h


def plate_study() -> None:
    print("## 3. Quantification limit on the synthetic sample plate\n")
    print(
        f"The sample plate model (see `synthetic.py`) with {len(PLATE_SEEDS)} different "
        "seeds; credible wells only. *Noise-free / r* is the method's estimate on the same "
        "curve without noise (using the mean quantification limit of the noisy plates); it is "
        "the right reference for bias, because the method reports an average rate over the "
        "exponential phase, which is below r for logistic growth. *Bias* is the mean estimate "
        "relative to that noise-free value.\n"
    )
    print(
        "| blank_sd_multiple | Condition | Mean / r | Noise-free / r | Bias | SD / r "
        "| Non-credible growth wells |"
    )
    print("| --- | --- | --- | --- | --- | --- | --- |")
    growing = [c for c in SAMPLE_CULTURES if c.r_per_h > 0]
    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for seed in PLATE_SEEDS:
            path = Path(tmp) / f"plate_{seed}.csv"
            path.write_text(csv_text(sample_plate_rows(seed)), encoding="utf-8")
            paths.append(path)
        for multiple in (3.0, 10.0):
            config = AnalysisConfig(blank_sd_multiple=multiple)
            rates: dict[str, list[float]] = {c.condition: [] for c in growing}
            not_credible = dict.fromkeys(rates, 0)
            limits = []
            for path in paths:
                output = analyse_plate(read_plate(path), config)
                limits.append(output.blank.quantification_limit)
                for well in output.wells:
                    if well.condition not in rates or well.status != "growth":
                        continue
                    if well.credible and well.growth_rate_per_h is not None:
                        rates[well.condition].append(well.growth_rate_per_h)
                    else:
                        not_credible[well.condition] += 1
            for culture in growing:
                values = np.array(rates[culture.condition]) / culture.r_per_h
                reference = noise_free_rate(culture, float(np.mean(limits))) / culture.r_per_h
                print(
                    f"| {multiple:g} | {culture.condition} (r = {culture.r_per_h}) "
                    f"| {values.mean():.3f} | {reference:.3f} "
                    f"| {values.mean() / reference - 1:+.1%} | {values.std(ddof=1):.3f} "
                    f"| {not_credible[culture.condition]} |"
                )


def main() -> None:
    print("# Method study (synthetic data)\n")
    print(
        "Generated by `uv run python scripts/method_study.py`. Every curve is synthetic; "
        "no measured data are involved.\n"
    )
    exponential_study()
    logistic_study()
    plate_study()


if __name__ == "__main__":
    main()
