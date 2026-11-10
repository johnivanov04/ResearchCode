"""Regression test: the committed example outputs in docs/example-output/ are current.

The README and the ResearchCode website show these files. Regenerating them with the
documented commands must give the same tables. Numbers are compared to a relative
tolerance of 1e-9 because another platform's ``log`` and ``exp`` may differ in the last bit;
anything larger means the analysis changed, and the examples must be regenerated
(see docs/example-output/README.md) and reviewed. Figures are not compared byte for byte,
because font rendering differs between platforms.
"""

import csv
import json
import math
from pathlib import Path

import pytest
from support import EXAMPLE_OUTPUT_DIR, SAMPLE_DIR

from growth_analysis.cli import main

EXAMPLES = {
    "plate": "synthetic_plate.csv",
    "website-example": "synthetic_website_example.csv",
}
TABLES = ("results.json", "well_results.csv", "condition_summary.csv", "points.csv")
RELATIVE = 1e-9


def assert_same(expected, actual, where):
    if isinstance(expected, float) and isinstance(actual, float):
        assert math.isclose(expected, actual, rel_tol=RELATIVE, abs_tol=1e-15), where
    elif isinstance(expected, dict):
        assert expected.keys() == actual.keys(), where
        for key in expected:
            assert_same(expected[key], actual[key], f"{where}.{key}")
    elif isinstance(expected, list):
        assert len(expected) == len(actual), where
        for index, (a, b) in enumerate(zip(expected, actual, strict=True)):
            assert_same(a, b, f"{where}[{index}]")
    else:
        assert expected == actual, where


def csv_cells(path: Path) -> list[list[object]]:
    def convert(cell: str) -> object:
        try:
            return float(cell)
        except ValueError:
            return cell

    rows = list(csv.reader(path.read_text(encoding="utf-8").splitlines()))
    return [[convert(cell) for cell in row] for row in rows]


@pytest.mark.parametrize("example", EXAMPLES)
def test_committed_example_output_matches_a_fresh_run(example, tmp_path):
    committed = EXAMPLE_OUTPUT_DIR / example
    out = tmp_path / example
    args = [
        "--input",
        str(SAMPLE_DIR / EXAMPLES[example]),
        "--output",
        str(out),
        "--plot-format",
        "png",
    ]
    assert main(args) == 0
    for name in TABLES:
        if name.endswith(".json"):
            expected = json.loads((committed / name).read_text(encoding="utf-8"))
            actual = json.loads((out / name).read_text(encoding="utf-8"))
        else:
            expected = csv_cells(committed / name)
            actual = csv_cells(out / name)
        assert_same(expected, actual, f"{example}/{name}")
    committed_figures = {p.relative_to(committed) for p in committed.rglob("*.png")}
    fresh_figures = {p.relative_to(out) for p in out.rglob("*.png")}
    assert committed_figures == fresh_figures
