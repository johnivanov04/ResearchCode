"""Validate an evaluator: references must pass everything, every defect must be caught.

``validate_evaluator`` scores each task's reference solution and every defective variant with
the real grading pipeline. It is the evidence that an evaluator measures what it claims to:
a correct implementation scores 100%, and each realistic defect lowers the score.

For the genuine (private) evaluator, the summary (case counts and scores; no inputs, expected
values, or code) is written to ``docs/evaluator-validation.json`` and shown on the website.
Public CI validates the fixture evaluator the same way.
"""

from __future__ import annotations

import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from rc_experiments.config import EXPERIMENTS_DIR, Config
from rc_experiments.evaluators import Evaluator, TaskEvaluator
from rc_experiments.grading import evaluate_hidden
from rc_experiments.sandbox import Backend

VALIDATION_PATH = EXPERIMENTS_DIR / "docs" / "evaluator-validation.json"


def _score(task: TaskEvaluator, source: str, backend: Backend, config: Config) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="rc-validate-") as tmp:
        (Path(tmp) / f"{task.module}.py").write_text(source, encoding="utf-8")
        evaluation = evaluate_hidden(task, Path(tmp), backend, config)
    if evaluation["evaluation_error"]:
        raise RuntimeError(f"{task.task}: evaluation failed: {evaluation['evaluation_error']}")
    return evaluation["summary"] | {"failed": [c for c in evaluation["cases"] if not c["passed"]]}


def validate_evaluator(evaluator: Evaluator, backend: Backend, config: Config) -> dict[str, Any]:
    tasks: dict[str, Any] = {}
    problems: list[str] = []
    for task_id, task in evaluator.tasks.items():
        cases = task.cases()
        reference = _score(task, task.reference_path.read_text(encoding="utf-8"), backend, config)
        if reference["passed"] != reference["cases"]:
            problems.append(f"{task_id}: the reference fails {[c['id'] for c in reference['failed']]}")
        mutants = []
        for mutant in task.mutants():
            score = _score(task, mutant.source(), backend, config)
            if score["passed"] >= reference["passed"]:
                problems.append(f"{task_id}: defect {mutant.name!r} is not detected")
            mutants.append(
                {
                    "name": mutant.name,
                    "description": mutant.description,
                    "pass_rate": round(score["hidden_pass_rate"], 4),
                    "cases_failed": score["cases"] - score["passed"],
                    "categories_failed": sorted({c["category"] for c in score["failed"]}),
                }
            )
        tasks[task_id] = {
            "module": task.module,
            "cases": len(cases),
            "cases_by_category": dict(sorted(Counter(c.category for c in cases).items())),
            "reference_pass_rate": round(reference["hidden_pass_rate"], 4),
            "mutants": mutants,
            "mutants_detected": sum(1 for m in mutants if m["cases_failed"] > 0),
        }
    return {
        "protocol_version": config.protocol_version,
        "evaluator": evaluator.kind,
        "note": "Evaluator validation with the experimenters' reference solutions and deliberately defective "
        "variants. These are checks of the scoring system, not experimental results.",
        "backend": backend.name,
        "tasks": tasks,
        "total_cases": sum(t["cases"] for t in tasks.values()),
        "total_mutants": sum(len(t["mutants"]) for t in tasks.values()),
        "problems": problems,
    }
