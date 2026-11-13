"""Randomised schedule, trial identifiers, and the manual session workflow (protocol 1.1)."""

import json
import shutil
from collections import Counter
from pathlib import Path

import pytest

from rc_experiments import agent
from rc_experiments.trials import TrialId, make_schedule
from rc_experiments.workspace import prepare

FIXTURES = Path(__file__).parent / "fixtures"


def test_schedule_is_deterministic_and_balanced(config):
    schedule = make_schedule(config)
    assert schedule == make_schedule(config)
    cells = len(config.task_ids) * len(config.condition_ids)
    pilot = [t for t in schedule if t.phase == "pilot"]
    confirmatory = [t for t in schedule if t.phase == "confirmatory"]
    assert len(pilot) == cells * config.design["pilot_trials_per_cell"] == 6
    assert len(confirmatory) == cells * config.design["confirmatory_trials_per_cell"]
    assert schedule[: len(pilot)] == pilot  # the pilot runs first
    for block in {t.block for t in schedule}:
        members = [TrialId.parse(t.trial_id) for t in schedule if t.block == block]
        assert Counter((m.task, m.condition) for m in members) == Counter(
            {(task, c): 1 for task in config.task_ids for c in config.condition_ids}
        )
    assert len({t.trial_id for t in schedule}) == len(schedule)


def test_schedule_order_varies_between_blocks(config):
    blocks = {}
    for t in make_schedule(config):
        blocks.setdefault(t.block, []).append(t.trial_id.rsplit("--", 1)[0])
    assert len({tuple(order) for order in blocks.values()}) > 1


@pytest.mark.parametrize("bad", ["calibration--A", "calibration--A--x01", "a--b--c--r01", "calibration--A--r"])
def test_trial_id_parsing_rejects_malformed_ids(bad):
    with pytest.raises(ValueError, match="invalid trial id"):
        TrialId.parse(bad)


def test_session_command_is_interactive_with_the_configured_settings(config):
    args = agent.claude_arguments(config, "PROMPT")
    assert args[:2] == ["claude", "PROMPT"]  # interactive: no -p / --print
    assert "-p" not in args
    assert "--print" not in args
    joined = " ".join(args)
    assert f"--model {config.agent['model']}" in joined
    assert f"--effort {config.agent['effort']}" in joined
    assert f"--permission-mode {config.agent['permission_mode']}" in joined
    assert args[-2:] == ["--disallowed-tools", "WebSearch,WebFetch"]
    assert agent.claude_arguments(config, None)[1] == "--model"  # preflight: no prompt at all


def test_only_the_subscription_token_enters_the_container(config, monkeypatch, tmp_path):
    for name in agent.FORBIDDEN_VARIABLES:
        monkeypatch.setenv(name, "must-never-be-passed")
    monkeypatch.setenv(agent.SUBSCRIPTION_CREDENTIAL, "subscription-token-value")
    args = agent.container_arguments(config, "name", tmp_path / "ws", tmp_path / "cfg")
    joined = " ".join(args)
    for name in agent.FORBIDDEN_VARIABLES:
        assert name not in joined
    assert "must-never-be-passed" not in joined
    assert "subscription-token-value" not in joined  # passed by name, never by value
    assert args[args.index(agent.SUBSCRIPTION_CREDENTIAL) - 1 :][:2] == ["-e", agent.SUBSCRIPTION_CREDENTIAL]
    assert f"{(tmp_path / 'cfg').resolve()}:{agent.CONTAINER_HOME}/.claude" in args
    assert "-it" in args
    assert agent.forbidden_variables_set() == list(agent.FORBIDDEN_VARIABLES)


def test_session_log_parsing_counts_each_message_once():
    report = agent.parse_session_logs([FIXTURES / "session_log_synthetic.jsonl"])
    assert report["assistant_messages"] == 2  # msg_1 is logged twice (two content blocks)
    assert report["subagent_messages"] == 1
    assert report["output_tokens"] == 40 + 60 + 7
    assert report["human_messages"] == 1  # the prompt; tool results and meta entries are not human input
    assert report["main_models"] == ["claude-opus-5-5"]
    assert report["subagent_models"] == ["claude-haiku-5-5"]
    assert report["efforts"] == ["high"]
    assert report["tool_use_counts"] == {"Write": 1, "Bash": 1}
    assert report["first_event"] < report["last_event"]


def test_empty_logs_leave_usage_missing():
    report = agent.parse_session_logs([])
    assert report["assistant_messages"] is None
    assert report["output_tokens"] is None


def base_report(**changes):
    report = {
        "session_log_files": 1,
        "main_models": ["claude-opus-5-5"],
        "efforts": ["high"],
        "tool_versions": ["2.1.319"],
        "tool_use_counts": {"Bash": 3},
        "continuation_messages": 0,
        "operator_other_input": False,
        "timed_out": False,
    }
    return report | changes


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({}, "valid"),
        ({"timed_out": True}, "valid"),
        ({"main_models": ["claude-sonnet-5-5"]}, "invalid"),
        ({"main_models": ["claude-opus-5-5", "claude-sonnet-5-5"]}, "invalid"),
        ({"efforts": ["medium"]}, "invalid"),
        ({"tool_versions": ["2.2.0"]}, "invalid"),
        ({"tool_use_counts": {"WebFetch": 1}}, "invalid"),
        ({"continuation_messages": 3}, "invalid"),
        ({"operator_other_input": True}, "invalid"),
        ({"operator_reported_usage_limit": True}, "invalid"),
        ({"operator_reported_extra_usage": True}, "invalid"),
        ({"extra_usage_notices": 1}, "invalid"),
        ({"session_log_files": 0}, "needs_review"),
    ],
)
def test_classification_rules(config, changes, expected):
    assert agent.classify_session(base_report(**changes), config)[0] == expected


def test_a_session_records_the_operator_report_and_never_keeps_credentials(config, tmp_path, monkeypatch):
    """The whole session flow with a stand-in for the interactive container (no model, no Docker)."""
    monkeypatch.setattr(agent, "check_environment", lambda *a, **k: [])
    trial_dir = prepare(TrialId("calibration", "B", "r01"), tmp_path, config, "fixture")
    seen = {}

    def fake_runner(command, limit_s, name):
        seen["command"], seen["limit"] = command, limit_s
        logs = trial_dir / "claude-config" / "projects" / "-workspace"
        logs.mkdir(parents=True)
        shutil.copyfile(FIXTURES / "session_log_synthetic.jsonl", logs / "session.jsonl")
        (trial_dir / "claude-config" / ".credentials.json").write_text("{}")
        return 0, False

    answers = iter(["1", "n", "n", "n", "agent asked which unit to use"])
    result = agent.session(trial_dir, config, ask=lambda _: next(answers), runner=fake_runner)
    assert seen["limit"] == 60 * config.agent["wall_clock_limit_minutes"]
    assert (trial_dir / "prompt.txt").read_text() in seen["command"]
    assert result["continuation_messages"] == 1
    assert result["assistant_messages"] == 2
    assert not (trial_dir / "claude-config" / ".credentials.json").exists()
    record = json.loads((trial_dir / "trial.json").read_text())
    assert record["validity"] == "valid"
    with pytest.raises(agent.AgentError, match="already has a session"):
        agent.session(trial_dir, config, ask=lambda _: "n", runner=fake_runner)


def test_collection_keeps_only_session_logs(config, tmp_path, monkeypatch):
    from rc_experiments.pipeline import collect

    monkeypatch.setattr(agent, "check_environment", lambda *a, **k: [])
    trial_dir = prepare(TrialId("serial-dilution", "A", "r01"), tmp_path / "trials", config, "fixture")

    def fake_runner(command, limit_s, name):
        config_dir = trial_dir / "claude-config"
        (config_dir / "projects" / "-workspace").mkdir(parents=True)
        shutil.copyfile(FIXTURES / "session_log_synthetic.jsonl", config_dir / "projects" / "-workspace" / "s.jsonl")
        (config_dir / "settings.json").write_text("{}")
        return 0, False

    answers = iter(["0", "n", "n", "n", ""])
    agent.session(trial_dir, config, ask=lambda _: next(answers), runner=fake_runner)
    collected = collect(trial_dir, tmp_path / "results")
    assert [p.name for p in (collected / "session-logs").iterdir()] == ["00-s.jsonl"]
    assert not (collected / "settings.json").exists()
    assert not any("claude-config" in str(p) for p in collected.rglob("*"))
