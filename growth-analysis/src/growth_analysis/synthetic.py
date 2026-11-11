"""Synthetic growth curves with known parameters, and the bundled sample datasets.

Everything produced here is **synthetic**: generated from mathematical models with chosen
parameters and seeded random noise. It describes no real organism or experiment. It exists
so that the analysis can be checked against known answers and tried without real data.

Models (time t in hours, N is blank-corrected OD):

* exponential: N(t) = N0 * exp(mu * t)
* logistic with lag: N(t) = N0 for t <= lag, and for t > lag
  N(t) = K / (1 + (K / N0 - 1) * exp(-r * (t - lag)))

Measurement model for the sample plate: raw OD = blank + N(t) * exp(e1) + e2, with
e1 ~ Normal(0, sd_multiplicative) and e2 ~ Normal(0, sd_additive), rounded to 3 decimals as
plate readers export it.

Regenerate the bundled files (they are checked against this module by the tests)::

    uv run python -m growth_analysis.synthetic --output-dir data/sample --overwrite
"""

import argparse
import math
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

__all__ = [
    "SAMPLE_PLATE_FILENAME",
    "SAMPLE_SEED",
    "WEBSITE_EXAMPLE_FILENAME",
    "Culture",
    "exponential_od",
    "logistic_od",
    "sample_plate_rows",
    "website_example_rows",
]

SAMPLE_SEED = 20261110
SAMPLE_PLATE_FILENAME = "synthetic_plate.csv"
WEBSITE_EXAMPLE_FILENAME = "synthetic_website_example.csv"
HEADER = ("well", "condition", "time_min", "od600")


def exponential_od(time_h: np.ndarray, n0: float, mu_per_h: float) -> np.ndarray:
    """N(t) = N0 * exp(mu * t)."""
    return n0 * np.exp(mu_per_h * np.asarray(time_h, dtype=float))


def logistic_od(
    time_h: np.ndarray, n0: float, k: float, r_per_h: float, lag_h: float = 0.0
) -> np.ndarray:
    """Logistic growth from N0 towards carrying capacity K, starting after ``lag_h``.

    The specific growth rate d ln N / dt is r (1 - N / K) after the lag, and 0 before it.
    """
    elapsed = np.maximum(np.asarray(time_h, dtype=float) - lag_h, 0.0)
    return k / (1.0 + (k / n0 - 1.0) * np.exp(-r_per_h * elapsed))


@dataclass(frozen=True)
class Culture:
    """Parameters of one synthetic condition on the sample plate."""

    condition: str
    wells: tuple[str, ...]
    n0: float
    k: float
    r_per_h: float
    lag_h: float


# The sample plate: two growing conditions, one without growth, and blank wells.
SAMPLE_CULTURES = (
    Culture("condition_A", ("B2", "B3", "B4"), n0=0.004, k=1.0, r_per_h=1.0, lag_h=2.0),
    Culture("condition_B", ("C2", "C3", "C4"), n0=0.010, k=0.8, r_per_h=0.6, lag_h=1.0),
    Culture("condition_C", ("D2", "D3", "D4"), n0=0.050, k=0.050, r_per_h=0.0, lag_h=0.0),
)
SAMPLE_BLANK_WELLS = ("A1", "A2", "A3")
SAMPLE_BLANK_OD = 0.040
SAMPLE_INTERVAL_MIN = 15
SAMPLE_DURATION_MIN = 960
SAMPLE_SD_MULTIPLICATIVE = 0.02
SAMPLE_SD_ADDITIVE = 0.001


def _od_text(value: float) -> str:
    return f"{value:.3f}"


def sample_plate_rows(seed: int = SAMPLE_SEED) -> list[tuple[str, str, str, str]]:
    """Rows of the synthetic sample plate (header excluded), ordered by time, then well.

    Condition C has K = N0, so its true OD is constant: a no-growth control.
    """
    rng = np.random.default_rng(seed)
    times_min = np.arange(0, SAMPLE_DURATION_MIN + 1, SAMPLE_INTERVAL_MIN)
    times_h = times_min / 60.0
    series: list[tuple[str, str, np.ndarray]] = []
    for well in SAMPLE_BLANK_WELLS:
        noise = rng.normal(0.0, SAMPLE_SD_ADDITIVE, times_h.size)
        series.append((well, "blank", SAMPLE_BLANK_OD + noise))
    for culture in SAMPLE_CULTURES:
        signal = logistic_od(times_h, culture.n0, culture.k, culture.r_per_h, culture.lag_h)
        for well in culture.wells:
            multiplicative = rng.normal(0.0, SAMPLE_SD_MULTIPLICATIVE, times_h.size)
            additive = rng.normal(0.0, SAMPLE_SD_ADDITIVE, times_h.size)
            raw = SAMPLE_BLANK_OD + signal * np.exp(multiplicative) + additive
            series.append((well, culture.condition, raw))
    rows = []
    for index, time_min in enumerate(times_min):
        for well, condition, raw in series:
            rows.append((well, condition, str(int(time_min)), _od_text(float(raw[index]))))
    return rows


# Parameters of the illustrative well on the ResearchCode website's /example page
# (web/src/lib/growth.ts). The website test checks that this file matches its data.
WEBSITE_RATE_PER_H = 1.2
WEBSITE_N0 = 0.01
WEBSITE_K = 1.1
WEBSITE_BLANK_OD = 0.045
WEBSITE_INTERVAL_MIN = 15
WEBSITE_DURATION_MIN = 720


def _js_round_3(value: float) -> float:
    """``Math.round(value * 1000) / 1000`` as JavaScript computes it, for positive values."""
    return math.floor(value * 1000.0 + 0.5) / 1000.0


def website_example_rows() -> list[tuple[str, str, str, str]]:
    """The website's illustrative well (logistic, r = 1.2/h) plus a constant blank well.

    The website subtracts a known constant blank of 0.045; here that is represented by a
    blank well reading 0.045 at every time point.
    """
    rows = []
    for time_min in range(0, WEBSITE_DURATION_MIN + 1, WEBSITE_INTERVAL_MIN):
        time_h = time_min / 60.0
        ratio = (WEBSITE_K - WEBSITE_N0) / WEBSITE_N0
        signal = WEBSITE_K / (1.0 + ratio * math.exp(-WEBSITE_RATE_PER_H * time_h))
        od = _js_round_3(WEBSITE_BLANK_OD + signal)
        rows.append(("A1", "blank", str(time_min), _od_text(WEBSITE_BLANK_OD)))
        rows.append(("B3", "illustrative", str(time_min), _od_text(od)))
    return rows


def csv_text(rows: Sequence[Sequence[str]]) -> str:
    """CSV text with the standard header and Unix line endings."""
    return "\n".join(",".join(row) for row in (HEADER, *rows)) + "\n"


def write_sample_data(output_dir: Path, *, overwrite: bool = False) -> list[Path]:
    """Write both sample datasets into ``output_dir`` and return their paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        SAMPLE_PLATE_FILENAME: csv_text(sample_plate_rows()),
        WEBSITE_EXAMPLE_FILENAME: csv_text(website_example_rows()),
    }
    written = []
    for name, text in files.items():
        path = output_dir / name
        with path.open("w" if overwrite else "x", encoding="utf-8", newline="") as handle:
            handle.write(text)
        written.append(path)
    return written


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m growth_analysis.synthetic",
        description="Write the synthetic sample datasets.",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    try:
        written = write_sample_data(args.output_dir, overwrite=args.overwrite)
    except FileExistsError as error:
        print(f"error: {error.filename} exists; use --overwrite to replace it", file=sys.stderr)
        return 1
    for path in written:
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
