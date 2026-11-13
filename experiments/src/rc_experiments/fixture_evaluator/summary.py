"""FIXTURE cases for the public practice task fixture-summary (not part of the experiment).

Expected values are derived with exact rational arithmetic (sample SD with n - 1).
"""

from __future__ import annotations

import json
from decimal import Decimal, localcontext
from fractions import Fraction as F

from rc_experiments.cases import Case, call, cli
from rc_experiments.checks import (
    Approx,
    CliFails,
    CliRefusesOverwrite,
    CliSucceeds,
    Deterministic,
    Equals,
    Fields,
    Raises,
    Returns,
)

MODULE = "fixture_summary"
TASK = "fixture-summary"


def expected(values: list[float]) -> Fields:
    xs = [F(v) for v in values]
    n = len(xs)
    mean = sum(xs) / n
    variance = sum((x - mean) ** 2 for x in xs) / (n - 1)
    with localcontext() as ctx:
        ctx.prec = 40
        sd = float((Decimal(variance.numerator) / Decimal(variance.denominator)).sqrt())
    return Fields({"mean": Approx(float(mean)), "sd": Approx(sd, abs_tol=1e-12), "n": Equals(n)})


A = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
B = [1.0, 2.0, 3.0, 4.0]


def cases() -> list[Case]:
    c: list[Case] = []
    fields = ["mean", "sd", "n"]

    def add(id_: str, category: str, description: str, request: dict, check) -> None:
        c.append(Case(f"fs-{id_}", category, description, request, check))

    add("eight", "known_answer", "eight values", call("summarize", A, fields=fields), Returns(expected(A)))
    add("four", "known_answer", "four values", call("summarize", B, fields=fields), Returns(expected(B)))
    add(
        "two",
        "edge_case",
        "two equal values (SD 0)",
        call("summarize", [3.0, 3.0], fields=fields),
        Returns(expected([3.0, 3.0])),
    )
    add("one", "invalid_input", "a single value", call("summarize", [1.0]), Raises())
    add("empty", "invalid_input", "no values", call("summarize", []), Raises())
    add("nan", "invalid_input", "a NaN value", call("summarize", [1.0, float("nan")]), Raises())
    add(
        "repeat",
        "reproducibility",
        "repeated calls agree and leave the list unchanged",
        call("summarize", A, fields=fields, repeat=2),
        Deterministic(expected(A)),
    )
    csv_a = "value\n" + "\n".join(str(v) for v in A) + "\n"
    run = ["--input", "{dir}/in.csv", "--output", "{dir}/out.json"]
    add(
        "cli-ok",
        "integration",
        "the command-line tool on a valid file",
        cli(run, {"in.csv": csv_a}, report=["out.json"]),
        CliSucceeds("out.json", expected(A)),
    )
    add(
        "cli-no-overwrite",
        "integration",
        "refuses to overwrite",
        cli(run, {"in.csv": csv_a, "out.json": json.dumps({"keep": True})}, report=["out.json"]),
        CliRefusesOverwrite("out.json"),
    )
    add(
        "cli-missing-column",
        "integration",
        "no 'value' column",
        cli(run, {"in.csv": "x\n1\n2\n"}, report=["out.json"]),
        CliFails("out.json"),
    )
    return c
