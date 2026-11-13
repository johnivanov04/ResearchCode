"""FIXTURE cases for the public practice task fixture-temperature (not part of the experiment).

Expected values are derived with exact rational arithmetic from the conversion formulas.
"""

from __future__ import annotations

from fractions import Fraction as F

from rc_experiments.cases import Case, call
from rc_experiments.checks import Approx, Deterministic, Raises, Returns

MODULE = "fixture_temperature"
TASK = "fixture-temperature"
ZERO_C = F(27315, 100)


def kelvin(value: float, unit: str) -> F:
    v = F(value)
    return {"C": v + ZERO_C, "F": (v - 32) * F(5, 9) + ZERO_C, "K": v}[unit]


def convert(value: float, source: str, target: str) -> float:
    k = kelvin(value, source)
    return float({"C": k - ZERO_C, "F": (k - ZERO_C) * F(9, 5) + 32, "K": k}[target])


def cases() -> list[Case]:
    c: list[Case] = []

    def add(id_: str, category: str, description: str, request: dict, check) -> None:
        c.append(Case(f"ft-{id_}", category, description, request, check))

    for id_, (value, source, target) in {
        "boiling": (100, "C", "F"),
        "freezing-k": (0, "C", "K"),
        "minus-forty": (-40, "F", "C"),
        "body": (98.6, "F", "C"),
        "k-to-f": (300, "K", "F"),
    }.items():
        add(
            id_,
            "known_answer",
            f"{value} {source} in {target}",
            call("convert_temperature", value, source, target),
            Returns(Approx(convert(value, source, target), abs_tol=1e-9)),
        )
    add(
        "absolute-zero",
        "edge_case",
        "0 K in C",
        call("convert_temperature", 0, "K", "C"),
        Returns(Approx(convert(0, "K", "C"))),
    )
    add("below-zero-k", "invalid_input", "negative kelvin", call("convert_temperature", -1, "K", "C"), Raises())
    add("below-zero-c", "invalid_input", "-300 C", call("convert_temperature", -300, "C", "K"), Raises())
    add("bad-unit", "invalid_input", "unknown unit", call("convert_temperature", 1, "X", "C"), Raises())
    add("nan", "invalid_input", "NaN", call("convert_temperature", float("nan"), "C", "F"), Raises())
    add(
        "string",
        "invalid_input",
        "a string value",
        call("convert_temperature", "10", "C", "F"),
        Raises(("ValueError", "TypeError")),
    )
    add(
        "repeat",
        "reproducibility",
        "repeated calls agree",
        call("convert_temperature", 25, "C", "F", repeat=2),
        Deterministic(Approx(convert(25, "C", "F"))),
    )
    return c
