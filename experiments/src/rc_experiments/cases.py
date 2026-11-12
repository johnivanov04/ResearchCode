"""Hidden evaluation cases: what to run in the sandbox, and how to grade it on the host.

A :class:`Case` has two halves:

* ``request``: plain JSON sent into the sandbox (function name and inputs only);
* ``check``: kept on the host, holding the expected values.

``sandbox_request`` builds the document sent to the sandbox; it contains no checks.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from rc_experiments.checks import Check

CATEGORIES = (
    "known_answer",
    "edge_case",
    "invalid_input",
    "numerical",
    "reproducibility",
    "integration",
)


@dataclass(frozen=True)
class Case:
    id: str
    category: str
    description: str
    request: Mapping[str, Any]
    check: Check

    def __post_init__(self) -> None:
        if self.category not in CATEGORIES:
            raise ValueError(f"{self.id}: unknown category {self.category!r}")


# Tagged values: JSON cannot express tuples or NumPy arrays, so the sandbox runner converts
# these tags back into the real types before calling the submission.
def ndarray(values: Sequence[float]) -> dict[str, Any]:
    return {"__ndarray__": [float(v) for v in values]}


def as_tuple(values: Sequence[Any]) -> dict[str, Any]:
    return {"__tuple__": list(values)}


def call(
    function: str,
    *args: Any,
    fields: Sequence[str] | None = None,
    repeat: int = 1,
    **kwargs: Any,
) -> dict[str, Any]:
    """Request a function call. ``fields`` names the attributes or keys to report."""
    return {
        "kind": "call",
        "function": function,
        "args": list(args),
        "kwargs": kwargs,
        "fields": list(fields) if fields is not None else None,
        "repeat": repeat,
    }


def cli(
    argv: Sequence[str],
    files: Mapping[str, str] | None = None,
    *,
    report: Sequence[str] = (),
    runs: int = 1,
    argv_second: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Request a call of ``main(argv)`` in a fresh directory.

    ``files`` are written (UTF-8) before the call; ``{dir}`` in ``argv`` is replaced by
    that directory. ``report`` lists files whose contents (or absence) are reported after
    the call, and whether files that existed before are unchanged. With ``runs=2`` the
    call is made a second time with ``argv_second``.
    """
    return {
        "kind": "cli",
        "function": "main",
        "argv": list(argv),
        "argv_second": list(argv_second) if argv_second is not None else None,
        "files": dict(files or {}),
        "report": list(report),
        "runs": runs,
    }


def sandbox_request(module: str, cases: Sequence[Case]) -> dict[str, Any]:
    """The document sent into the sandbox: module name and case inputs, no expected values."""
    return {
        "module": module,
        "cases": [{"id": case.id, **case.request} for case in cases],
    }
