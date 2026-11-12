"""Host-side checks that grade what a submission produced.

The sandbox only *observes*: it calls the submission and reports return values,
exceptions, and files as JSON (see ``probe_runner.py``). Every comparison with an expected
value happens here, on the host, so expected values never enter the sandbox and a
submission cannot see or change its own scoring criteria.

Each check returns a :class:`CheckResult`. A hidden case passes only if its check passes.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

Observation = Mapping[str, Any]


@dataclass(frozen=True)
class CheckResult:
    passed: bool
    detail: str = ""
    # Relative errors of numeric comparisons (for the numerical-accuracy metric).
    rel_errors: tuple[float, ...] = field(default=())


def _ok(detail: str = "", rel_errors: Sequence[float] = ()) -> CheckResult:
    return CheckResult(True, detail, tuple(rel_errors))


def _fail(detail: str, rel_errors: Sequence[float] = ()) -> CheckResult:
    return CheckResult(False, detail, tuple(rel_errors))


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def relative_error(actual: float, expected: float) -> float:
    """|actual - expected| / |expected|, or the absolute error when expected is 0."""
    if math.isnan(actual) or math.isinf(actual):
        return math.inf
    scale = abs(expected)
    return abs(actual - expected) / scale if scale > 0 else abs(actual - expected)


class Check:
    """A predicate on a plain (JSON) value or on a whole observation."""

    def evaluate(self, value: Any) -> CheckResult:  # pragma: no cover - interface
        raise NotImplementedError

    def describe(self) -> str:  # pragma: no cover - interface
        raise NotImplementedError


# --------------------------------------------------------------------------------------
# Value checks
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Approx(Check):
    """A finite number within max(rel * |expected|, abs_tol) of ``expected``."""

    expected: float
    rel: float = 1e-9
    abs_tol: float = 0.0

    def evaluate(self, value: Any) -> CheckResult:
        if not _is_number(value):
            return _fail(f"expected a number close to {self.expected!r}, got {value!r}")
        actual = float(value)
        if not math.isfinite(actual):
            return _fail(f"expected {self.expected!r}, got non-finite {actual!r}", [math.inf])
        error = relative_error(actual, self.expected)
        tolerance = max(self.rel * abs(self.expected), self.abs_tol)
        if abs(actual - self.expected) <= tolerance:
            return _ok(rel_errors=[error])
        return _fail(f"expected {self.expected!r} (tolerance {tolerance:.3g}), got {actual!r}", [error])

    def describe(self) -> str:
        return f"≈ {self.expected!r} (rel {self.rel:g}, abs {self.abs_tol:g})"


@dataclass(frozen=True)
class Equals(Check):
    """Exact equality for strings; for integers, an ``int`` (not ``bool``) with this value."""

    expected: str | int

    def evaluate(self, value: Any) -> CheckResult:
        if isinstance(self.expected, str):
            if value == self.expected:
                return _ok()
            return _fail(f"expected {self.expected!r}, got {value!r}")
        if isinstance(value, int) and not isinstance(value, bool) and value == self.expected:
            return _ok()
        return _fail(f"expected the integer {self.expected!r}, got {value!r}")

    def describe(self) -> str:
        return f"== {self.expected!r}"


@dataclass(frozen=True)
class IsBool(Check):
    expected: bool

    def evaluate(self, value: Any) -> CheckResult:
        if isinstance(value, bool) and value is self.expected:
            return _ok()
        return _fail(f"expected the boolean {self.expected!r}, got {value!r}")

    def describe(self) -> str:
        return f"is {self.expected!r}"


@dataclass(frozen=True)
class IsNone(Check):
    def evaluate(self, value: Any) -> CheckResult:
        return _ok() if value is None else _fail(f"expected None, got {value!r}")

    def describe(self) -> str:
        return "is None"


@dataclass(frozen=True)
class SeqApprox(Check):
    """A list of numbers of the same length, each within tolerance."""

    expected: tuple[float, ...]
    rel: float = 1e-9
    abs_tol: float = 0.0

    def evaluate(self, value: Any) -> CheckResult:
        if not isinstance(value, list):
            return _fail(f"expected a list of {len(self.expected)} numbers, got {value!r}")
        if len(value) != len(self.expected):
            return _fail(f"expected {len(self.expected)} values, got {len(value)}")
        errors: list[float] = []
        for index, (item, target) in enumerate(zip(value, self.expected, strict=True)):
            result = Approx(target, self.rel, self.abs_tol).evaluate(item)
            errors.extend(result.rel_errors)
            if not result.passed:
                return _fail(f"element {index}: {result.detail}", errors)
        return _ok(rel_errors=errors)

    def describe(self) -> str:
        return f"≈ {list(self.expected)!r} (rel {self.rel:g})"


@dataclass(frozen=True)
class Fields(Check):
    """A mapping whose named fields each satisfy a check (extra fields are allowed)."""

    checks: Mapping[str, Check]

    def evaluate(self, value: Any) -> CheckResult:
        if not isinstance(value, dict):
            return _fail(f"expected a mapping with fields {sorted(self.checks)}, got {value!r}")
        errors: list[float] = []
        failures: list[str] = []
        for name, check in self.checks.items():
            item = value.get(name, _MISSING)
            if item is _MISSING or (isinstance(item, dict) and item.get("__missing__")):
                failures.append(f"{name}: missing")
                continue
            result = check.evaluate(item)
            errors.extend(result.rel_errors)
            if not result.passed:
                failures.append(f"{name}: {result.detail}")
        if failures:
            return _fail("; ".join(failures), errors)
        return _ok(rel_errors=errors)

    def describe(self) -> str:
        return "{" + ", ".join(f"{k}: {c.describe()}" for k, c in self.checks.items()) + "}"


_MISSING = object()


# --------------------------------------------------------------------------------------
# Observation checks (function calls)
# --------------------------------------------------------------------------------------


def _status_problem(observation: Observation, wanted: str) -> str | None:
    status = observation.get("status")
    if status == wanted:
        return None
    if status == "raised":
        exc = observation.get("exception") or {}
        return f"raised {exc.get('types', ['?'])[0]}: {str(exc.get('message', ''))[:200]}"
    if status == "returned":
        return f"returned {observation.get('value')!r} instead of raising"
    return f"{status}: {str(observation.get('detail', ''))[:200]}"


@dataclass(frozen=True)
class Returns(Check):
    """The call returned a value satisfying ``check``, without modifying its inputs."""

    check: Check

    def evaluate(self, value: Any) -> CheckResult:
        observation: Observation = value
        problem = _status_problem(observation, "returned")
        if problem:
            return _fail(problem)
        if observation.get("inputs_mutated"):
            return _fail("modified its arguments")
        return self.check.evaluate(observation.get("value"))

    def describe(self) -> str:
        return f"returns {self.check.describe()}"


@dataclass(frozen=True)
class Raises(Check):
    """The call raised one of ``types`` (or a subclass)."""

    types: tuple[str, ...] = ("ValueError",)

    def evaluate(self, value: Any) -> CheckResult:
        observation: Observation = value
        problem = _status_problem(observation, "raised")
        if problem:
            return _fail(problem)
        raised = (observation.get("exception") or {}).get("types", [])
        if any(name in raised for name in self.types):
            return _ok()
        return _fail(f"raised {raised[:1]}, expected one of {list(self.types)}")

    def describe(self) -> str:
        return f"raises {' or '.join(self.types)}"


@dataclass(frozen=True)
class Deterministic(Check):
    """Repeated calls return identical values, do not modify inputs, and satisfy ``check``."""

    check: Check

    def evaluate(self, value: Any) -> CheckResult:
        observation: Observation = value
        problem = _status_problem(observation, "returned")
        if problem:
            return _fail(problem)
        if observation.get("inputs_mutated"):
            return _fail("modified its arguments")
        values = observation.get("values") or []
        if len(values) < 2:
            return _fail("the call was not repeated")
        first = json.dumps(values[0], sort_keys=True)
        if any(json.dumps(v, sort_keys=True) != first for v in values[1:]):
            return _fail("repeated calls returned different results")
        return self.check.evaluate(values[0])

    def describe(self) -> str:
        return f"deterministic and {self.check.describe()}"


# --------------------------------------------------------------------------------------
# Command-line checks
# --------------------------------------------------------------------------------------


def _cli_failed(observation: Observation) -> bool:
    """A non-zero exit status, or an uncaught exception (which exits non-zero in a real run)."""
    if observation.get("status") == "raised":
        return True
    return observation.get("status") == "returned" and observation.get("exit_code") not in (0, None)


@dataclass(frozen=True)
class CliSucceeds(Check):
    """Exit status 0 and the output file is a JSON object satisfying ``check``."""

    output: str
    check: Check

    def evaluate(self, value: Any) -> CheckResult:
        observation: Observation = value
        if observation.get("status") != "returned":
            return _fail(_status_problem(observation, "returned") or "did not return")
        if observation.get("exit_code") not in (0, None):
            stderr = str(observation.get("stderr", ""))[:200]
            return _fail(f"exit status {observation.get('exit_code')!r}: {stderr}")
        text = (observation.get("files_after") or {}).get(self.output)
        if text is None:
            return _fail(f"{self.output} was not written")
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as error:
            return _fail(f"{self.output} is not valid JSON: {error}")
        return self.check.evaluate(parsed)

    def describe(self) -> str:
        return f"exits 0 and writes {self.output}: {self.check.describe()}"


@dataclass(frozen=True)
class CliFails(Check):
    """A non-zero exit status (or uncaught exception), and the output file not created."""

    output: str

    def evaluate(self, value: Any) -> CheckResult:
        observation: Observation = value
        if observation.get("status") not in ("returned", "raised"):
            return _fail(_status_problem(observation, "returned") or "did not run")
        if not _cli_failed(observation):
            return _fail("reported success (exit status 0) for invalid input")
        if (observation.get("files_after") or {}).get(self.output) is not None:
            return _fail(f"created {self.output} despite the error")
        return _ok()

    def describe(self) -> str:
        return f"exits non-zero and does not create {self.output}"


@dataclass(frozen=True)
class CliRefusesOverwrite(Check):
    """A non-zero exit status, and the pre-existing output file left byte-for-byte unchanged."""

    output: str

    def evaluate(self, value: Any) -> CheckResult:
        observation: Observation = value
        if observation.get("status") not in ("returned", "raised"):
            return _fail(_status_problem(observation, "returned") or "did not run")
        if not _cli_failed(observation):
            return _fail("reported success although the output file already existed")
        if not (observation.get("unchanged") or {}).get(self.output, False):
            return _fail(f"modified the existing {self.output}")
        return _ok()

    def describe(self) -> str:
        return f"exits non-zero and leaves the existing {self.output} unchanged"


@dataclass(frozen=True)
class CliReproducible(Check):
    """Two runs succeed and write JSON outputs with identical content."""

    outputs: tuple[str, str]
    check: Check

    def evaluate(self, value: Any) -> CheckResult:
        observation: Observation = value
        runs = observation.get("runs") or []
        if len(runs) != 2:
            return _fail(_status_problem(observation, "returned") or "expected two runs")
        parsed = []
        for run, output in zip(runs, self.outputs, strict=True):
            result = CliSucceeds(output, self.check).evaluate(run)
            if not result.passed:
                return result
            parsed.append(json.loads(run["files_after"][output]))
        if json.dumps(parsed[0], sort_keys=True) != json.dumps(parsed[1], sort_keys=True):
            return _fail("two runs on the same input wrote different results")
        return _ok()

    def describe(self) -> str:
        return f"two runs write identical results: {self.check.describe()}"
