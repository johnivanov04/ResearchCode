"""Host-side checks grade observations exactly as the protocol describes."""

import math

import pytest

from rc_experiments.checks import (
    Approx,
    CliFails,
    CliRefusesOverwrite,
    CliReproducible,
    CliSucceeds,
    Deterministic,
    Equals,
    Fields,
    IsBool,
    IsNone,
    Raises,
    Returns,
    SeqApprox,
)


def returned(value, **extra):
    return {"status": "returned", "value": value, "values": [value, value], "inputs_mutated": False, **extra}


def raised(*types):
    return {
        "status": "raised",
        "exception": {"types": [*types, "Exception", "BaseException", "object"], "message": "x"},
    }


@pytest.mark.parametrize(
    ("value", "passes"),
    [
        (10.0, True),
        (10.0 + 5e-9, True),
        (10.0 + 2e-8, False),
        (10, True),
        (True, False),
        ("10", False),
        (math.nan, False),
        (math.inf, False),
        (None, False),
    ],
)
def test_approx_uses_relative_tolerance_and_rejects_non_numbers(value, passes):
    # rel 1e-9 of 10.0 allows an absolute difference of 1e-8.
    assert Approx(10.0, rel=1e-9).evaluate(value).passed is passes


def test_approx_absolute_floor_for_zero():
    assert Approx(0.0, abs_tol=1e-12).evaluate(1e-13).passed
    assert not Approx(0.0, abs_tol=1e-12).evaluate(1e-11).passed


def test_equals_requires_integers_not_booleans_or_floats():
    assert Equals(3).evaluate(3).passed
    assert not Equals(1).evaluate(True).passed
    assert not Equals(3).evaluate(3.0).passed
    assert Equals("ok").evaluate("ok").passed
    assert not Equals("ok").evaluate("OK").passed


def test_booleans_and_none():
    assert IsBool(True).evaluate(True).passed
    assert not IsBool(True).evaluate(1).passed
    assert IsNone().evaluate(None).passed
    assert not IsNone().evaluate(0).passed


def test_sequence_and_fields():
    assert SeqApprox((1.0, 2.0)).evaluate([1.0, 2.0]).passed
    assert not SeqApprox((1.0, 2.0)).evaluate([1.0]).passed
    check = Fields({"a": Approx(1.0), "b": Equals("x")})
    assert check.evaluate({"a": 1.0, "b": "x", "extra": 5}).passed
    result = check.evaluate({"a": 1.0, "b": {"__missing__": True}})
    assert not result.passed
    assert "b: missing" in result.detail


def test_returns_fails_on_exceptions_and_mutated_inputs():
    assert Returns(Approx(2.0)).evaluate(returned(2.0)).passed
    assert not Returns(Approx(2.0)).evaluate(raised("ValueError")).passed
    assert not Returns(Approx(2.0)).evaluate(returned(2.0, inputs_mutated=True)).passed
    assert not Returns(Approx(2.0)).evaluate({"status": "timeout"}).passed
    assert not Returns(Approx(2.0)).evaluate({"status": "import_error"}).passed


def test_raises_accepts_subclasses_by_name_and_rejects_returns():
    assert Raises().evaluate(raised("UnitError", "ValueError")).passed
    assert not Raises().evaluate(raised("KeyError", "LookupError")).passed
    assert Raises(("ValueError", "TypeError")).evaluate(raised("TypeError")).passed
    assert not Raises().evaluate(returned(1.0)).passed


def test_deterministic_requires_identical_repeats():
    assert Deterministic(Approx(1.0)).evaluate(returned(1.0)).passed
    changing = {"status": "returned", "value": 1.0, "values": [1.0, 2.0], "inputs_mutated": False}
    assert not Deterministic(Approx(1.0)).evaluate(changing).passed


def test_cli_checks():
    ok = {"status": "returned", "exit_code": 0, "files_after": {"out.json": '{"k": 2.0}'}}
    assert CliSucceeds("out.json", Fields({"k": Approx(2.0)})).evaluate(ok).passed
    assert not CliSucceeds("out.json", Fields({"k": Approx(3.0)})).evaluate(ok).passed
    failed = {"status": "returned", "exit_code": 2, "files_after": {"out.json": None}}
    assert CliFails("out.json").evaluate(failed).passed
    assert CliFails("out.json").evaluate({"status": "raised", "files_after": {"out.json": None}}).passed
    assert (
        not CliFails("out.json")
        .evaluate({"status": "returned", "exit_code": 2, "files_after": {"out.json": "{}"}})
        .passed
    )
    assert not CliFails("out.json").evaluate(ok).passed
    kept = {"status": "returned", "exit_code": 1, "unchanged": {"out.json": True}}
    assert CliRefusesOverwrite("out.json").evaluate(kept).passed
    assert not CliRefusesOverwrite("out.json").evaluate({**kept, "unchanged": {"out.json": False}}).passed
    second = {"status": "returned", "exit_code": 0, "files_after": {"b.json": '{"k": 2.0}'}}
    assert CliReproducible(("out.json", "b.json"), Fields({"k": Approx(2.0)})).evaluate({"runs": [ok, second]}).passed
    different = {"status": "returned", "exit_code": 0, "files_after": {"b.json": '{"k": 2.0000001}'}}
    assert (
        not CliReproducible(("out.json", "b.json"), Fields({"k": Approx(2.0, rel=1e-3)}))
        .evaluate({"runs": [ok, different]})
        .passed
    )
