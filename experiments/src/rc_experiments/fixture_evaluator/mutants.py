"""FIXTURE defective variants of the practice references (not part of the experiment)."""

from __future__ import annotations

from rc_experiments.fixture_evaluator import reference_path
from rc_experiments.mutation import Mutant


def _mutant(task: str, name: str, description: str, *replacements: tuple[str, str]) -> Mutant:
    return Mutant(task, name, description, tuple(replacements), reference_path(task))


MUTANTS: tuple[Mutant, ...] = (
    _mutant(
        "fixture-temperature",
        "fahrenheit-offset",
        "Fahrenheit offset 30 instead of 32",
        ("return (value - 32.0) * 5.0 / 9.0", "return (value - 30.0) * 5.0 / 9.0"),
    ),
    _mutant(
        "fixture-temperature",
        "kelvin-offset-273",
        "0 C taken as 273 K",
        ("ZERO_CELSIUS_K = 273.15", "ZERO_CELSIUS_K = 273.0"),
    ),
    _mutant(
        "fixture-temperature",
        "no-absolute-zero-check",
        "temperatures below absolute zero accepted",
        ("    if kelvin < 0:\n", "    if kelvin < -1e300:\n"),
    ),
    _mutant(
        "fixture-summary",
        "population-sd",
        "SD divides by n instead of n - 1",
        ('"sd": statistics.stdev(numbers)', '"sd": statistics.pstdev(numbers)'),
    ),
    _mutant(
        "fixture-summary",
        "overwrites-output",
        "existing output is overwritten",
        ("    if args.output.exists():\n", "    if False:\n"),
    ),
    _mutant(
        "fixture-summary",
        "no-finite-check",
        "NaN values accepted",
        ("    if not all(math.isfinite(v) for v in numbers):\n", "    if False:\n"),
    ),
)
