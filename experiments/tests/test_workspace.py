"""Each trial starts from a clean, independent workspace containing only what its condition allows."""

import json

import pytest

from rc_experiments.config import CONDITIONS_DIR, EXPERIMENTS_DIR, TASKS_DIR
from rc_experiments.trials import TrialId
from rc_experiments.workspace import IsolationError, check_ancestors, prepare, starter_files


def test_condition_a_gets_only_the_task(tmp_path, config):
    trial_dir = prepare(TrialId("calibration", "A", "r01"), tmp_path, config, "fixture")
    files = sorted(p.name for p in (trial_dir / "workspace").rglob("*") if p.is_file())
    assert files == ["TASK.md", "public_examples.json"]
    record = json.loads((trial_dir / "trial.json").read_text())
    assert record["condition"] == "A"
    assert record["starter"] is None
    assert not (trial_dir / "workspace" / "trial.json").exists()


def test_condition_b_gets_the_task_and_the_starter_kit(tmp_path, config):
    trial_dir = prepare(TrialId("calibration", "B", "r01"), tmp_path, config, "fixture")
    workspace = trial_dir / "workspace"
    present = {p.relative_to(workspace).as_posix() for p in workspace.rglob("*") if p.is_file()}
    assert {p.as_posix() for p in starter_files()} | {"TASK.md", "public_examples.json"} == present
    assert (workspace / "AGENTS.md").is_file()
    assert (workspace / "TASK.md").read_bytes() == (TASKS_DIR / "calibration" / "TASK.md").read_bytes()


def test_workspaces_are_independent_and_never_reused(tmp_path, config):
    first = prepare(TrialId("serial-dilution", "A", "r01"), tmp_path, config, "fixture")
    (first / "workspace" / "serial_dilution.py").write_text("x = 1\n")
    second = prepare(TrialId("serial-dilution", "A", "r02"), tmp_path, config, "fixture")
    assert not (second / "workspace" / "serial_dilution.py").exists()
    with pytest.raises(FileExistsError):
        prepare(TrialId("serial-dilution", "A", "r01"), tmp_path, config, "fixture")


def test_refuses_trials_root_inside_the_repository(config):
    with pytest.raises(IsolationError):
        prepare(TrialId("calibration", "A", "r01"), EXPERIMENTS_DIR / "trials-tmp", config, "fixture")


def test_refuses_instruction_files_above_the_trials_root(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("instructions that would leak into a session\n")
    with pytest.raises(IsolationError):
        check_ancestors(tmp_path / "trials")


def test_pilot_and_confirmatory_kinds_match_replicates(tmp_path, config):
    with pytest.raises(ValueError, match="pilot"):
        prepare(TrialId("calibration", "A", "r01"), tmp_path, config, "pilot")


def test_prompts_share_the_core_and_differ_only_by_the_treatment():
    a = (CONDITIONS_DIR / "A-unstructured" / "PROMPT.md").read_text()
    b = (CONDITIONS_DIR / "B-structured" / "PROMPT.md").read_text()
    assert b.startswith(a.rstrip("\n"))
    assert "AGENTS.md" in b
    assert "SPEC_TEMPLATE" in b
    for word in ("AGENTS.md", "starter", "test", "specification", "ResearchCode"):
        assert word not in a


@pytest.mark.parametrize("path", sorted([*TASKS_DIR.rglob("*.*"), *CONDITIONS_DIR.rglob("*.md")]))
def test_agent_facing_text_does_not_reveal_the_experiment(path):
    """Agents should not learn that they are being compared or that hidden tests exist."""
    text = path.read_text(encoding="utf-8").lower()
    for word in ("experiment", "condition a", "condition b", "hidden", "vibe", "trial", "researchcode phase"):
        assert word not in text, (path.name, word)
