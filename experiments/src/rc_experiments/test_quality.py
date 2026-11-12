"""Measure the quality of a submission's own tests by mutation analysis (protocol section 5.2).

**Which tests count.** Condition B's workspace starts with the starter kit's own tests (137 of
them, for its growth-rate example). Those are *inherited*, not written for the task, so they
are excluded: a test is inherited if the file it comes from is byte-identical to a tracked
file of ``scientific-starter/``, wherever the file now sits. Tests in new files, or in files the
agent changed, count as created or adapted for the task (protocol 1.2).

The task tests are run three ways, each in a fresh sandbox:

1. against the submission's own code (do its tests pass?);
2. against the reference solution, with the submission's module replaced. Tests that do not pass
   here are *invalid* (they test internals or assert wrong behaviour) and are excluded;
3. against each defective variant (mutant). A mutant is *detected* if at least one valid task
   test fails or errors, or the run times out.

Mutation score = detected mutants / all mutants of the task; 0 when there are no valid task tests.
Tests written by a submission never count as evidence of its correctness.
"""

from __future__ import annotations

import hashlib
from functools import cache
from pathlib import Path
from typing import Any

from rc_experiments.config import STARTER_DIR, Config
from rc_experiments.evaluators import TaskEvaluator
from rc_experiments.sandbox import Backend


@cache
def starter_file_hashes() -> frozenset[str]:
    """SHA-256 of every tracked starter-kit file (the inherited material)."""
    from rc_experiments.workspace import starter_files

    return frozenset(hashlib.sha256((STARTER_DIR / p).read_bytes()).hexdigest() for p in starter_files())


def inherited_tests(submission: Path, files: dict[str, str | None], inherited: frozenset[str]) -> set[str]:
    """Test ids whose source file is byte-identical to a starter-kit file."""
    result = set()
    for test_id, relative in files.items():
        if not relative:
            continue
        path = (submission / relative).resolve()
        inside = path.is_relative_to(submission.resolve()) and path.is_file()
        if inside and hashlib.sha256(path.read_bytes()).hexdigest() in inherited:
            result.add(test_id)
    return result


def _run(backend: Backend, submission: Path, module: str, source: str | None, timeout: float) -> dict[str, Any]:
    result = backend.run(
        "suite_runner.py",
        submission,
        {"module": module, "replacement_source": source},
        ["--timeout", str(timeout)],
        timeout + 120,
    )
    if result.report is None:
        return {"status": "sandbox_error", "detail": result.error, "tests": {}, "files": {}, "collected": 0}
    return result.report


def evaluate_own_tests(
    task: TaskEvaluator,
    submission: Path,
    backend: Backend,
    config: Config,
    inherited_hashes: frozenset[str] | None = None,
) -> dict[str, Any]:
    timeout = float(config.evaluation["own_tests_timeout_seconds"])
    inherited_hashes = starter_file_hashes() if inherited_hashes is None else inherited_hashes
    own = _run(backend, submission, task.module, None, timeout)
    reference = _run(backend, submission, task.module, task.reference_path.read_text(encoding="utf-8"), timeout)

    own_tests: dict[str, str] = own.get("tests", {})
    inherited = inherited_tests(submission, {**reference.get("files", {}), **own.get("files", {})}, inherited_hashes)
    task_tests = {t: o for t, o in own_tests.items() if t not in inherited}
    valid = sorted(t for t, o in reference.get("tests", {}).items() if o == "passed" and t not in inherited)

    mutant_results = []
    for mutant in task.mutants():
        if not valid:
            mutant_results.append({"name": mutant.name, "detected": False, "reason": "no valid task tests"})
            continue
        run = _run(backend, submission, task.module, mutant.source(), timeout)
        outcomes = run.get("tests", {})
        if run.get("status") == "timeout":
            detected, reason = True, "timeout"
        else:
            failing = [t for t in valid if outcomes.get(t) != "passed"]
            detected, reason = bool(failing), (f"{len(failing)} valid task tests failed" if failing else "all passed")
        mutant_results.append({"name": mutant.name, "detected": detected, "reason": reason})

    n_mutants = len(mutant_results)
    return {
        "own_status": own.get("status"),
        "tests_collected_total": len(own_tests),
        "tests_inherited": len(set(own_tests) & inherited),
        # The counts below exclude inherited starter-kit tests (protocol 1.2).
        "tests_collected": len(task_tests),
        "tests_passed_on_own_code": sum(1 for o in task_tests.values() if o == "passed"),
        "all_own_tests_pass": bool(task_tests) and all(o == "passed" for o in task_tests.values()),
        "reference_status": reference.get("status"),
        "valid_tests": len(valid),
        "mutants": mutant_results,
        "mutation_score": (sum(1 for m in mutant_results if m["detected"]) / n_mutants) if n_mutants else None,
    }
