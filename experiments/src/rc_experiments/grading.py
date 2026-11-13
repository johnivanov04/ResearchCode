"""Run the hidden cases against a submission and grade the observations on the host."""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from rc_experiments.cases import CATEGORIES, Case, sandbox_request
from rc_experiments.checks import CheckResult
from rc_experiments.config import Config
from rc_experiments.evaluators import TaskEvaluator
from rc_experiments.sandbox import Backend

# Hidden runs: generous overall limit; each case has its own limit inside the runner.
_PER_CASE_OVERHEAD_S = 5.0
_RUN_OVERHEAD_S = 120.0


def grade(cases: Sequence[Case], observations: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Grade observations against the cases' checks (host side)."""
    by_id = {obs.get("id"): obs for obs in observations}
    results = []
    for case in cases:
        observation = by_id.get(case.id, {"status": "missing", "detail": "no observation"})
        result: CheckResult = case.check.evaluate(observation)
        results.append(
            {
                "id": case.id,
                "category": case.category,
                "passed": result.passed,
                "status": observation.get("status"),
                "detail": result.detail[:500],
                "rel_errors": [min(e, 1.0) for e in result.rel_errors],
            }
        )
    return results


def summarise(results: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Pass rates overall and per category, numerical accuracy, and import failure."""
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    categories: dict[str, dict[str, Any]] = {}
    for category in CATEGORIES:
        members = [r for r in results if r["category"] == category]
        if members:
            n_pass = sum(1 for r in members if r["passed"])
            categories[category] = {"cases": len(members), "passed": n_pass, "pass_rate": n_pass / len(members)}
    errors = [e for r in results if r["category"] == "known_answer" for e in r["rel_errors"]]
    return {
        "cases": total,
        "passed": passed,
        "hidden_pass_rate": passed / total if total else 0.0,
        # Sensitivity analysis (protocol 11): every category weighted equally within the task.
        "category_balanced_pass_rate": (
            statistics.fmean(c["pass_rate"] for c in categories.values()) if categories else 0.0
        ),
        "categories": categories,
        "import_failed": bool(results) and all(r["status"] == "import_error" for r in results),
        "median_rel_error_known_answer": statistics.median(errors) if errors else None,
    }


def evaluate_hidden(task: TaskEvaluator, submission: Path, backend: Backend, config: Config) -> dict[str, Any]:
    cases = task.cases()
    case_timeout = float(config.evaluation["case_timeout_seconds"])
    timeout = len(cases) * (case_timeout + _PER_CASE_OVERHEAD_S) + _RUN_OVERHEAD_S
    run = backend.run(
        "probe_runner.py",
        submission,
        sandbox_request(task.module, cases),
        ["--timeout", str(case_timeout)],
        timeout,
    )
    observations = run.report["observations"] if run.report else []
    results = grade(cases, observations)
    return {
        "task": task.task,
        "backend": run.backend,
        "sandbox_image_id": run.image_id,
        "runner": {k: v for k, v in (run.report or {}).items() if k != "observations"},
        "evaluation_error": run.error,
        "summary": summarise(results),
        "cases": results,
    }
