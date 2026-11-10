"""Helpers shared by the tests (importable because pyproject sets pythonpath = ["tests"]).

Test data are built here from explicit formulas, independently of
``growth_analysis.synthetic``, so that a mistake in the package's own generators cannot
hide a mistake in the analysis.
"""

from collections.abc import Iterable, Sequence
from pathlib import Path

import numpy as np

from growth_analysis.blank import BlankSummary
from growth_analysis.readings import Well

PROJECT_DIR = Path(__file__).resolve().parents[1]
SAMPLE_DIR = PROJECT_DIR / "data" / "sample"
EXAMPLE_OUTPUT_DIR = PROJECT_DIR / "docs" / "example-output"

Row = tuple[str, str, float, float]


def csv_text(rows: Iterable[Row], time_column: str = "time_h") -> str:
    lines = [f"well,condition,{time_column},od600"]
    lines += [f"{well},{condition},{time!r},{od!r}" for well, condition, time, od in rows]
    return "\n".join(lines) + "\n"


def well_rows(well: str, condition: str, time_h: Sequence[float], od: Sequence[float]) -> list[Row]:
    return [(well, condition, float(t), float(x)) for t, x in zip(time_h, od, strict=True)]


def make_well(
    time_h: Sequence[float], od: Sequence[float], name: str = "W1", condition: str = "test"
) -> Well:
    """A validated well built directly, bypassing CSV parsing."""
    return Well(
        well=name,
        condition=condition,
        time_h=np.asarray(time_h, dtype=float),
        od600=np.asarray(od, dtype=float),
        lines=tuple(range(2, 2 + len(time_h))),
    )


def no_blank(quantification_limit: float = 1e-12) -> BlankSummary:
    """Blank summary for already blank-corrected data with a chosen quantification limit."""
    return BlankSummary(
        method="none",
        label="blank",
        wells=(),
        n_readings=0,
        value=0.0,
        sd=None,
        min_reading=None,
        max_reading=None,
        quantification_limit=quantification_limit,
    )
