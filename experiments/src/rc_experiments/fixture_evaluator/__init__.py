"""FIXTURE evaluator: two public practice tasks used to test the harness. NOT part of the experiment.

The genuine evaluator for the three experiment tasks is private (see ``rc_experiments.evaluators``).
This package mirrors its structure so that public CI and dry runs can exercise every stage
(sandboxed probing, host-side grading, mutation analysis, analysis) without exposing any
genuine hidden case, expected value, or reference solution. Nothing produced with these
fixtures is an experimental result.
"""

from __future__ import annotations

from pathlib import Path

from rc_experiments.fixture_evaluator import summary, temperature

KIND = "fixture"
ROOT = Path(__file__).resolve().parent
REFERENCES_DIR = ROOT / "references"
TASK_MODULES = {module.TASK: module for module in (temperature, summary)}


def reference_path(task: str) -> Path:
    return REFERENCES_DIR / f"{TASK_MODULES[task].MODULE}.py"
