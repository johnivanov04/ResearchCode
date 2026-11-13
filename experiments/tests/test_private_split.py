"""The genuine evaluator stays out of the public repository, and the harness behaves safely without it.

These tests simulate a machine without the private evaluator (as in public CI) by pointing
RC_PRIVATE_EVALUATOR at an empty directory.
"""

import json
import re
import subprocess

import pytest

from rc_experiments import evaluators
from rc_experiments.config import EXPERIMENTS_DIR, REPO_DIR
from rc_experiments.freeze import verify_freeze
from rc_experiments.trials import TrialId
from rc_experiments.workspace import prepare

GENUINE_MODULES = ("serial_dilution", "calibration", "enzyme_kinetics")
# Built at run time so that this file does not contain the markers it searches for.
HIDDEN_DOCSTRING = '"' * 3 + "HIDDEN"
PRIVATE_IMPORT = "from " + "rc_private_evaluator"


@pytest.fixture
def without_private(monkeypatch, tmp_path):
    monkeypatch.setenv(evaluators.PRIVATE_ENV, str(tmp_path / "no-private-evaluator"))
    evaluators.load_genuine.cache_clear()
    yield
    evaluators.load_genuine.cache_clear()


def test_genuine_evaluator_is_unavailable_without_the_private_directory(without_private):
    assert evaluators.private_available() is False
    with pytest.raises(evaluators.EvaluatorUnavailableError, match="deliberately not in the public repository"):
        evaluators.load_genuine()


def test_genuine_and_pilot_trials_cannot_be_prepared_without_it(without_private, tmp_path, config):
    with pytest.raises(evaluators.EvaluatorUnavailableError):
        prepare(TrialId("calibration", "A", "p01"), tmp_path / "trials", config, "pilot")


def test_fixture_work_needs_no_private_files(without_private, tmp_path, config):
    trial_dir = prepare(TrialId("fixture-summary", "B", "r01"), tmp_path / "trials", config, "fixture")
    assert (trial_dir / "workspace" / "TASK.md").read_text().startswith("# FIXTURE task")
    assert evaluators.for_data_kind("fixture").kind == "fixture"


def test_freeze_check_reports_the_private_part_as_unchecked(without_private):
    result = verify_freeze()
    assert result["private_checked"] is False
    assert result["mismatches"] == []
    strict = verify_freeze(require_private=True)
    assert "private evaluator not available, so it could not be checked" in strict["mismatches"]


def committable_files() -> list[str]:
    listed = (
        subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=REPO_DIR,
            capture_output=True,
            check=True,
        )
        .stdout.decode()
        .split("\0")
    )
    return [p for p in listed if p]


def test_no_genuine_evaluator_files_are_committable():
    """Nothing that looks like the genuine evaluator can be committed to the public repository."""
    for relative in committable_files():
        assert "rc_private_evaluator" not in relative, relative
        assert "/hidden/" not in relative, relative
        if relative.startswith("experiments/src/") and relative.endswith(".py"):
            assert not any(relative.endswith(f"/{m}.py") for m in GENUINE_MODULES), relative
    for relative in committable_files():
        path = REPO_DIR / relative
        if path.suffix == ".py" and path.is_file():
            text = path.read_text(encoding="utf-8", errors="replace")
            assert HIDDEN_DOCSTRING not in text, relative
            assert PRIVATE_IMPORT not in text, relative


def test_gitignore_blocks_private_material_inside_the_repository():
    ignored = (EXPERIMENTS_DIR / ".gitignore").read_text()
    for pattern in ("rc_private_evaluator/", "private-evaluator/", "**/hidden/"):
        assert pattern in ignored


def test_ci_publishes_no_experiment_artifacts():
    workflow = (REPO_DIR / ".github" / "workflows" / "experiments.yml").read_text()
    assert "upload-artifact" not in workflow
    assert "RC_PRIVATE_EVALUATOR" not in workflow
    assert "--evaluator fixture" in workflow


def test_the_website_shows_only_aggregate_validation_figures():
    validation = json.loads((EXPERIMENTS_DIR / "docs" / "evaluator-validation.json").read_text())
    text = json.dumps(validation)
    assert "expected" not in text
    assert not re.search(r"\b(def|import) ", text)  # no code
    assert set(validation["tasks"]) == {"serial-dilution", "calibration", "enzyme-kinetics"}
