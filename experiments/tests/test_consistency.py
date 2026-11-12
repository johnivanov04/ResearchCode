"""The protocol, configuration, task statements, Docker files, and results directories agree."""

import json
import re
import tomllib

import pytest

from rc_experiments.agent import run_fixture
from rc_experiments.config import EXPERIMENTS_DIR, RESULTS_DIR, TASKS_DIR, Config
from rc_experiments.evaluators import load_fixture
from rc_experiments.freeze import FREEZE_PATH, verify_freeze
from rc_experiments.grading import grade
from rc_experiments.sandbox import LocalBackend

PROTOCOL = (EXPERIMENTS_DIR / "docs" / "PROTOCOL.md").read_text(encoding="utf-8")


def test_configuration_matches_the_public_task_statements(config):
    """The genuine evaluator is private (checked by its own tests); the statements are public."""
    for task in config.raw["tasks"]:
        assert f"importable as **`{task['module']}`**" in (TASKS_DIR / task["id"] / "TASK.md").read_text()
    for condition in config.raw["conditions"]:
        assert (EXPERIMENTS_DIR / condition["prompt_file"]).is_file()
    assert set(load_fixture().task_ids).isdisjoint(config.task_ids)


def test_protocol_states_the_configured_parameters(config):
    agent, design = config.agent, config.design
    assert f"Protocol version | {config.protocol_version}" in PROTOCOL
    assert f"Claude Code {agent['tool_version']}" in PROTOCOL
    assert f"`{agent['model']}`, effort `{agent['effort']}`" in PROTOCOL
    assert f"{agent['wall_clock_limit_minutes']} minutes" in PROTOCOL
    assert "Additional spending | **$0.**" in PROTOCOL
    assert f"`{config.raw['billing']['credential']}`" in PROTOCOL
    for name in config.raw["billing"]["forbidden_credentials"][:3]:
        assert f"`{name}`" in PROTOCOL
    assert "--max-budget-usd 10`) and the total-cost estimate were removed" in PROTOCOL  # recorded as an amendment
    assert "Claude Code 2.1.319 in **interactive mode**" in PROTOCOL
    assert "at most twice per trial" in PROTOCOL
    assert agent["max_continuation_messages"] == 2
    assert f"{design['confirmatory_trials_per_cell']} trials per task and condition" in PROTOCOL
    assert f"{design['pilot_trials_per_cell']} trial per task and condition" in PROTOCOL
    assert f"({design['schedule_seed']})" in PROTOCOL
    assert f"fewer than {design['minimum_valid_trials_per_cell_for_inference']} valid trials" in PROTOCOL
    assert f"{config.analysis['bootstrap_resamples']:,} resamples" in PROTOCOL
    assert f"{config.evaluation['case_timeout_seconds']} s per hidden case" in PROTOCOL
    for host in agent["network_allowlist"]:
        assert f"`{host}`" in PROTOCOL
    for tool in agent["disallowed_tools"]:
        assert f"`{tool}`" in PROTOCOL


def test_docker_files_match_the_configuration_and_lock(config):
    agent_dockerfile = (EXPERIMENTS_DIR / "docker" / "agent" / "Dockerfile").read_text()
    assert f"ARG CLAUDE_CODE_VERSION={config.agent['tool_version']}" in agent_dockerfile
    allowlist = (EXPERIMENTS_DIR / "docker" / "proxy" / "allowlist").read_text().split()
    assert allowlist == [f"^{re.escape(h)}$" for h in config.agent["network_allowlist"]]
    lock = tomllib.loads((EXPERIMENTS_DIR / "uv.lock").read_text())
    locked = {p["name"]: p["version"] for p in lock["package"]}
    requirements = (EXPERIMENTS_DIR / "docker" / "sandbox" / "requirements.txt").read_text()
    pins = dict(re.findall(r"^([a-z0-9-]+)==([^ ;\\\n]+)", requirements, re.MULTILINE))
    assert {"numpy", "scipy", "pytest", "hypothesis"} <= set(pins)
    for name, version in pins.items():
        assert locked[name] == version, name
    for dockerfile in (EXPERIMENTS_DIR / "docker").rglob("Dockerfile"):
        for line in dockerfile.read_text().splitlines():
            if line.startswith("FROM "):
                assert "@sha256:" in line, f"{dockerfile}: base image not pinned by digest"


@pytest.mark.parametrize("task", ["serial-dilution", "calibration", "enzyme-kinetics"])
def test_public_examples_are_valid_json_and_labelled(task):
    examples = json.loads((TASKS_DIR / task / "public_examples.json").read_text())
    assert examples["task"] == task
    assert len(examples["examples"]) >= 3


def test_freeze_record_covers_every_defining_file():
    from rc_experiments.freeze import frozen_files

    files = set(frozen_files())
    for required in (
        "experiments/docs/PROTOCOL.md",
        "experiments/experiment.json",
        "experiments/tasks/calibration/TASK.md",
        "experiments/conditions/B-structured/PROMPT.md",
        "experiments/src/rc_experiments/checks.py",
        "experiments/src/rc_experiments/analysis.py",
        "experiments/src/rc_experiments/evaluators.py",
        "experiments/src/rc_experiments/fixture_evaluator/references/fixture_summary.py",
        "experiments/src/rc_experiments/fixture_evaluator/tasks/fixture-summary/TASK.md",
        "experiments/conditions/CONTINUE.md",
        "experiments/src/rc_experiments/sandbox_scripts/probe_runner.py",
        "experiments/docker/sandbox/Dockerfile",
        "scientific-starter/AGENTS.md",
        "scientific-starter/pyproject.toml",
        "scientific-starter/src/scientific_starter/growth.py",
    ):
        assert required in files, required
    assert not any("__pycache__" in f for f in files)


def test_freeze_record_matches_the_current_files():
    """FREEZE.json must be regenerated (and the change recorded) whenever a frozen file changes."""
    assert FREEZE_PATH.is_file()
    assert verify_freeze()["mismatches"] == []  # public files; the private part is checked where present


def test_freeze_record_commits_to_the_private_evaluator():
    record = json.loads(FREEZE_PATH.read_text())
    private = record["private_evaluator"]["files"]
    assert len(private) == 8
    assert all(path.startswith("rc_private_evaluator/") for path in private)
    assert not any(path.startswith("experiments/src/rc_experiments/hidden") for path in record["files"])


def test_no_experimental_results_exist_before_trials_are_run(config):
    """While the protocol status is 'framework-ready', no genuine or pilot trial may be present."""
    if config.raw["status"] == "framework-ready":
        for kind in ("genuine", "pilot"):
            folder = RESULTS_DIR / kind
            assert not any(p.is_dir() for p in folder.glob("*")), f"{folder} contains trials"


def test_fixture_agents_cannot_write_into_genuine_trials(tmp_path, config):
    from rc_experiments.trials import TrialId
    from rc_experiments.workspace import prepare

    trial_dir = prepare(TrialId("calibration", "A", "r01"), tmp_path, config, "fixture")
    record = json.loads((trial_dir / "trial.json").read_text())
    record["data_kind"] = "genuine"
    (trial_dir / "trial.json").write_text(json.dumps(record))
    with pytest.raises(Exception, match="fixture"):
        run_fixture(trial_dir, {"calibration.py": "x = 1\n"})


def test_grading_without_observations_fails_every_case(config):
    results = grade(load_fixture().task("fixture-summary").cases(), [])
    assert not any(r["passed"] for r in results)
    assert isinstance(Config.load(), Config)
    assert isinstance(LocalBackend(trusted=True).name, str)
