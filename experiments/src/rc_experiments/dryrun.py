"""End-to-end dry run with the public FIXTURE evaluator instead of an AI agent.

Every stage of the real pipeline runs (prepare isolated workspaces, "agent", collect,
evaluate, analyse). The tasks are the two public practice tasks of
``rc_experiments.fixture_evaluator``, and the "agent" writes their reference solutions and
defective variants (plus small fixture test suites in Condition B). No genuine hidden case,
expected value, or reference solution is used. All output is ``data_kind = "fixture"`` and
labelled as not being experimental results. It must be written outside ``experiments/results``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rc_experiments.agent import run_fixture
from rc_experiments.analysis import analyse
from rc_experiments.config import Config
from rc_experiments.evaluators import load_fixture
from rc_experiments.pipeline import collect, evaluate_collected, results_dir_for
from rc_experiments.sandbox import Backend
from rc_experiments.trials import TrialId
from rc_experiments.workspace import prepare

# Small fixture test suites. The last test in each is deliberately wrong, so the dry run
# exercises the rule that tests failing against the reference solution are excluded.
FIXTURE_TESTS: dict[str, str] = {
    "fixture-temperature": '''"""Fixture tests (dry run only)."""
import pytest
from fixture_temperature import convert_temperature


def test_boiling_point_from_fahrenheit():
    assert convert_temperature(212, "F", "C") == pytest.approx(100)


def test_deliberately_wrong():
    assert convert_temperature(0, "C", "K") == pytest.approx(273)
''',
    "fixture-summary": '''"""Fixture tests (dry run only)."""
import pytest
from fixture_summary import summarize


def test_mean():
    assert summarize([1, 2, 3, 4])["mean"] == pytest.approx(2.5)


def test_deliberately_wrong():
    assert summarize([1, 2, 3, 4])["n"] == 5
''',
}


def fixture_files(task: str, condition: str, replicate: int) -> dict[str, str]:
    """A: module at the top level; B: package under src/ plus fixture tests. Odd replicates use a defect."""
    evaluator = load_fixture().task(task)
    mutants = evaluator.mutants()
    if replicate % 2 == 1:
        source = mutants[(replicate // 2 + (0 if condition == "A" else 1)) % len(mutants)].source()
    else:
        source = evaluator.reference_path.read_text(encoding="utf-8")
    if condition == "A":
        return {f"{evaluator.module}.py": source}
    return {
        f"src/{evaluator.module}/__init__.py": source,
        f"tests/test_fixture_{evaluator.module}.py": FIXTURE_TESTS[task],
    }


def dry_run(
    out_dir: Path,
    backend: Backend,
    config: Config,
    *,
    replicates: int = 2,
    own_tests: bool = True,
) -> dict[str, Any]:
    evaluator = load_fixture()
    trials_root = out_dir / "trials"
    results_root = results_dir_for("fixture", out_dir / "results")
    results_root.mkdir(parents=True, exist_ok=True)
    for task in evaluator.task_ids:
        for condition in config.condition_ids:
            for replicate in range(1, replicates + 1):
                trial = TrialId(task, condition, f"r{replicate:02d}")
                trial_dir = prepare(trial, trials_root, config, "fixture")
                run_fixture(trial_dir, fixture_files(task, condition, replicate))
                collected = collect(trial_dir, results_root)
                evaluate_collected(collected, backend, config, own_tests=own_tests)
    result = analyse(results_root, out_dir / "analysis", config)
    return {"results": str(results_root), "analysis": str(out_dir / "analysis"), "label": result["label"]}
