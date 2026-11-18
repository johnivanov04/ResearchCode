"""Unattended batches (protocol 1.5) with mocked Claude processes: no model, no Docker, no network.

Every token here is a fake placeholder, every stream event is synthetic (shaped like Claude
Code 2.1.319's real stream-json output), and every trial is written to a temporary directory.
Nothing in this file can start a real session or consume model usage.
"""

from __future__ import annotations

import functools
import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

from rc_experiments import agent
from rc_experiments.batch import (
    JOURNAL_NAME,
    LOCK_NAME,
    BatchDeps,
    BatchRefusedError,
    plan,
    run_batch,
)
from rc_experiments.pipeline import CollectionError, collect
from rc_experiments.trials import TrialId, make_schedule, read_json, update_record, write_json

FIXTURES = Path(__file__).parent / "fixtures"
FAKE_TOKEN = "sk-ant-oat01-" + "FAKEPLACEHOLDER" * 6 + "QQQQQ"  # not a credential
SUBSCRIPTION_ENV = {agent.SUBSCRIPTION_CREDENTIAL: FAKE_TOKEN}


# --------------------------------------------------------------------------------------
# Synthetic stream-json events (shapes from Claude Code 2.1.319)
# --------------------------------------------------------------------------------------


def init_event(config, **changes):
    event = {
        "type": "system",
        "subtype": "init",
        "cwd": "/workspace",
        "session_id": "00000000-synthetic",
        "tools": ["Task", "Bash", "Edit", "Read", "Write"],
        "model": config.agent["model"],
        "permissionMode": config.agent["permission_mode"],
        "apiKeySource": "none",
        "claude_code_version": config.agent["tool_version"],
    }
    return json.dumps(event | changes)


def assistant_text(text="Working on it."):
    return json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}})


def assistant_error(error, text):
    return json.dumps(
        {
            "type": "assistant",
            "message": {"model": "<synthetic>", "content": [{"type": "text", "text": text}]},
            "error": error,
            "is_api_error_message": True,
        }
    )


def api_retry(error, status):
    return json.dumps({"type": "system", "subtype": "api_retry", "attempt": 1, "error_status": status, "error": error})


def rate_limit(**info):
    return json.dumps({"type": "rate_limit_event", "rate_limit_info": {"status": "allowed"} | info})


def result_event(*, is_error=False, terminal_reason="completed", total_cost_usd=1.23):
    return json.dumps(
        {
            "type": "result",
            "subtype": "success",
            "is_error": is_error,
            "terminal_reason": terminal_reason,
            "num_turns": 7,
            "duration_ms": 1000,
            "api_error_status": None,
            "total_cost_usd": total_cost_usd,
            "result": "Done.",
        }
    )


def success_lines(config):
    return [init_event(config), rate_limit(overageStatus="rejected"), assistant_text(), result_event()]


# --------------------------------------------------------------------------------------
# Authentication: subscription only
# --------------------------------------------------------------------------------------


def test_only_an_unambiguous_subscription_token_is_accepted():
    assert agent.subscription_auth_problems(SUBSCRIPTION_ENV) == []
    cases = {
        "missing": {},
        "whitespace": {agent.SUBSCRIPTION_CREDENTIAL: FAKE_TOKEN[:40] + " " + FAKE_TOKEN[40:]},
        "api key in the token variable": {agent.SUBSCRIPTION_CREDENTIAL: "sk-ant-api03-FAKEPLACEHOLDERFAKE"},
        "unknown format": {agent.SUBSCRIPTION_CREDENTIAL: "FAKEPLACEHOLDER-not-a-token"},
        "API key also set": SUBSCRIPTION_ENV | {"ANTHROPIC_API_KEY": "FAKEPLACEHOLDER-key"},
        "auth token also set": SUBSCRIPTION_ENV | {"ANTHROPIC_AUTH_TOKEN": "FAKEPLACEHOLDER"},
        "other endpoint": SUBSCRIPTION_ENV | {"ANTHROPIC_BASE_URL": "http://fake.invalid"},
        "cloud provider": SUBSCRIPTION_ENV | {"CLAUDE_CODE_USE_BEDROCK": "1"},
        "API key descriptor": SUBSCRIPTION_ENV | {"CLAUDE_CODE_API_KEY_FILE_DESCRIPTOR": "3"},
    }
    for name, environ in cases.items():
        problems = agent.subscription_auth_problems(environ)
        assert problems, name
        joined = " ".join(problems)
        assert "FAKEPLACEHOLDER" not in joined, name  # values are never shown
        assert "fake.invalid" not in joined, name


def test_the_batch_command_is_claude_p_with_the_manual_sessions_settings(config, tmp_path, monkeypatch):
    for name in agent.FORBIDDEN_VARIABLES:
        monkeypatch.setenv(name, "FAKEPLACEHOLDER-must-never-be-passed")
    monkeypatch.setenv(agent.SUBSCRIPTION_CREDENTIAL, FAKE_TOKEN)
    prompt = "Synthetic prompt."
    manual = agent.claude_arguments(config, prompt)
    batch = agent.batch_claude_arguments(config, prompt)
    assert batch[:3] == ["claude", "-p", prompt]
    assert batch[3:6] == ["--output-format", "stream-json", "--verbose"]
    assert batch[6:] == manual[2:]  # identical model, effort, permission mode, and disallowed tools
    assert "--bare" not in batch
    assert not any("budget" in arg for arg in batch)
    container = agent.batch_container_arguments(config, "name", tmp_path / "ws", tmp_path / "cfg")
    assert "-it" not in container
    assert "-i" not in container
    assert "-t" not in container
    assert container == [
        a for a in agent.container_arguments(config, "name", tmp_path / "ws", tmp_path / "cfg") if a != "-it"
    ]
    joined = " ".join(container + batch)
    assert FAKE_TOKEN not in joined  # passed by name only
    assert "must-never-be-passed" not in joined
    for name in agent.FORBIDDEN_VARIABLES:
        assert name not in joined


# --------------------------------------------------------------------------------------
# The stream monitor: what stops a session at once
# --------------------------------------------------------------------------------------


def feed_all(config, lines):
    monitor = agent.StreamMonitor(config)
    for line in lines:
        if monitor.feed(line):
            break
    return monitor


def test_a_completed_session_is_recognised_and_cost_estimates_are_not_kept(config):
    monitor = feed_all(config, success_lines(config))
    assert monitor.completed
    assert monitor.stop_reason is None
    assert monitor.init["apiKeySource"] == "none"
    assert "total_cost_usd" not in json.dumps(monitor.summary())


@pytest.mark.parametrize(
    ("lines", "category"),
    [
        (lambda c: [init_event(c, apiKeySource="ANTHROPIC_API_KEY")], "authentication"),
        (lambda c: [init_event(c, apiKeySource="apiKeyHelper")], "authentication"),
        (lambda c: [init_event(c, model="claude-sonnet-5-5")], "configuration"),
        (lambda c: [init_event(c, permissionMode="default")], "configuration"),
        (lambda c: [init_event(c, claude_code_version="9.9.9")], "configuration"),
        (lambda c: [init_event(c, tools=["Bash", "WebFetch"])], "configuration"),
        (lambda c: [init_event(c), api_retry("authentication_failed", 401)], "authentication"),
        (lambda c: [init_event(c), api_retry("billing_error", 402)], "billing"),
        (lambda c: [init_event(c), api_retry("rate_limit", 429)], "usage_limit"),
        (lambda c: [init_event(c), rate_limit(status="rejected", overageStatus="rejected")], "usage_limit"),
        (lambda c: [init_event(c), rate_limit(isUsingOverage=True)], "extra_usage"),
        (lambda c: [init_event(c), rate_limit(overageStatus="allowed")], "extra_usage"),
        (lambda c: [init_event(c), rate_limit(overageStatus="allowed_warning")], "extra_usage"),
        (lambda c: [init_event(c), assistant_text("You are now using extra usage.")], "extra_usage"),
        (
            lambda c: [
                init_event(c),
                assistant_error("authentication_failed", "Failed to authenticate. API Error: 401"),
            ],
            "authentication",
        ),
    ],
)
def test_safety_stops(config, lines, category):
    monitor = feed_all(config, [*lines(config), assistant_text("never reached"), result_event()])
    assert monitor.stop_category == category
    assert monitor.result is None  # the monitor asked to stop before the end of the stream
    assert not monitor.completed


def test_transient_errors_and_usage_warnings_do_not_stop_a_session(config):
    lines = [
        init_event(config),
        api_retry("overloaded", 529),
        rate_limit(status="allowed_warning", overageStatus="rejected"),
        result_event(),
    ]
    monitor = feed_all(config, lines)
    assert monitor.stop_reason is None
    assert monitor.completed
    assert monitor.api_retries == [{"attempt": 1, "error_status": 529, "error": "overloaded"}]


@pytest.mark.parametrize(
    "ending",
    [
        [result_event(is_error=True, terminal_reason="api_error")],
        [result_event(terminal_reason="aborted_streaming")],
        [],  # no result at all
    ],
)
def test_an_unclear_ending_is_not_completed(config, ending):
    assert not feed_all(config, [init_event(config), *ending]).completed


# --------------------------------------------------------------------------------------
# The runner with a real (mocked) Claude process
# --------------------------------------------------------------------------------------


def fake_process(tmp_path, lines, **scenario):
    path = tmp_path / f"scenario-{len(list(tmp_path.glob('scenario-*')))}.json"
    path.write_text(json.dumps({"lines": lines, **scenario}))
    return [sys.executable, str(FIXTURES / "fake_claude.py"), str(path)]


def kill_process(stops):
    def stop(name, process, *, immediately):
        stops.append(immediately)
        process.kill()

    return stop


def test_runner_streams_a_completed_session_and_redacts_secrets(config, tmp_path):
    lines = [*success_lines(config)[:-1], assistant_text(f"echo {FAKE_TOKEN}"), result_event()]
    command = fake_process(tmp_path, lines, stderr=f"warning {FAKE_TOKEN}\n")
    monitor, stops = agent.StreamMonitor(config), []
    outcome = agent.run_noninteractive(
        command, 30, "n", tmp_path / "s.jsonl", tmp_path / "e.txt", monitor, stop=kill_process(stops)
    )
    assert outcome == agent.RunOutcome(exit_code=0, timed_out=False, aborted=None)
    assert monitor.completed
    assert stops == []
    assert FAKE_TOKEN not in (tmp_path / "s.jsonl").read_text()
    assert FAKE_TOKEN not in (tmp_path / "e.txt").read_text()
    assert "[REDACTED]" in (tmp_path / "s.jsonl").read_text()


def test_runner_stops_the_process_at_once_on_a_safety_stop(config, tmp_path):
    lines = [init_event(config), rate_limit(isUsingOverage=True), assistant_text("MARKER-AFTER-STOP"), result_event()]
    command = fake_process(tmp_path, lines, delay=0.3)
    monitor, stops = agent.StreamMonitor(config), []
    outcome = agent.run_noninteractive(
        command, 30, "n", tmp_path / "s.jsonl", tmp_path / "e.txt", monitor, stop=kill_process(stops)
    )
    assert outcome.aborted
    assert "overage" in outcome.aborted
    assert stops == [True]  # killed immediately, not a graceful stop
    assert "MARKER-AFTER-STOP" not in (tmp_path / "s.jsonl").read_text()


def test_runner_enforces_the_time_limit(config, tmp_path):
    command = fake_process(tmp_path, [init_event(config), assistant_text()], hang=60)
    monitor, stops = agent.StreamMonitor(config), []
    outcome = agent.run_noninteractive(
        command, 1.0, "n", tmp_path / "s.jsonl", tmp_path / "e.txt", monitor, stop=kill_process(stops)
    )
    assert outcome.timed_out
    assert outcome.aborted is None
    assert stops == [False]  # a graceful stop at the limit
    assert not monitor.completed


def test_runner_kills_a_process_that_ignores_the_graceful_stop(config, tmp_path, monkeypatch):
    monkeypatch.setattr(agent, "KILL_GRACE_SECONDS", 1.0)
    command = fake_process(tmp_path, [init_event(config)], hang=60)
    stops = []

    def stubborn(name, process, *, immediately):
        stops.append(immediately)
        if immediately:
            process.kill()

    outcome = agent.run_noninteractive(
        command, 0.5, "n", tmp_path / "s.jsonl", tmp_path / "e.txt", agent.StreamMonitor(config), stop=stubborn
    )
    assert outcome.timed_out
    assert stops == [False, True]


def test_runner_reports_a_failing_process(config, tmp_path):
    command = fake_process(tmp_path, [init_event(config), "not json at all"], exit_code=3)
    monitor = agent.StreamMonitor(config)
    outcome = agent.run_noninteractive(
        command, 30, "n", tmp_path / "s.jsonl", tmp_path / "e.txt", monitor, stop=kill_process([])
    )
    assert outcome.exit_code == 3
    assert monitor.unparsed_lines == 1


# --------------------------------------------------------------------------------------
# One trial: batch_session
# --------------------------------------------------------------------------------------


def make_trial(trials_root, trial, config):
    trial_dir = trials_root / str(trial)
    (trial_dir / "workspace").mkdir(parents=True)
    (trial_dir / "workspace" / "TASK.md").write_text("Synthetic task statement for tests.\n")
    (trial_dir / "prompt.txt").write_text("Synthetic prompt for tests.\n")
    digest = hashlib.sha256((trial_dir / "workspace" / "TASK.md").read_bytes()).hexdigest()
    write_json(
        trial_dir / "trial.json",
        {
            "trial_id": str(trial),
            "task": trial.task,
            "condition": trial.condition,
            "replicate": trial.replicate,
            "data_kind": trial.data_kind,
            "protocol_version": config.protocol_version,
            "workspace_files": {"TASK.md": digest},
            "validity": "pending",
        },
    )
    return trial_dir


def fake_prepare(trial, trials_root, config, data_kind):
    assert data_kind == trial.data_kind
    return make_trial(trials_root, trial, config)


class ScriptedRunner:
    """Stands in for run_noninteractive: feeds scripted lines to the real monitor."""

    def __init__(self, lines, *, exit_code=0, timed_out=False, transcript=True, error=None):
        self.lines, self.exit_code, self.timed_out = lines, exit_code, timed_out
        self.transcript, self.error = transcript, error
        self.calls: list[dict] = []

    def __call__(self, command, limit_s, name, stream_path, stderr_path, monitor):
        claude_config = Path(next(a.split(":")[0] for a in command if a.endswith(":/home/agent/.claude")))
        record = read_json(stream_path.parent / "trial.json")
        self.calls.append({"command": command, "limit": limit_s, "marked_started": bool(record.get("batch"))})
        if self.error is not None:
            raise self.error
        aborted = None
        with stream_path.open("w") as out:
            for line in self.lines:
                out.write(line + "\n")
                if reason := monitor.feed(line):
                    aborted = reason
                    break
        stderr_path.write_text("")
        if self.transcript:
            logs = claude_config / "projects" / "-workspace"
            logs.mkdir(parents=True)
            shutil.copyfile(FIXTURES / "session_log_synthetic.jsonl", logs / "session.jsonl")
        return agent.RunOutcome(exit_code=137 if aborted else self.exit_code, timed_out=self.timed_out, aborted=aborted)


class ProcessRunner:
    """The real streaming runner (run_noninteractive) driving the mocked Claude process."""

    def __init__(self, tmp_path, lines):
        self.tmp_path, self.lines, self.calls = tmp_path, lines, []

    def __call__(self, command, limit_s, name, stream_path, stderr_path, monitor):
        self.calls.append(command)
        claude_config = Path(next(a.split(":")[0] for a in command if a.endswith(":/home/agent/.claude")))
        logs = claude_config / "projects" / "-workspace"
        logs.mkdir(parents=True)
        shutil.copyfile(FIXTURES / "session_log_synthetic.jsonl", logs / "session.jsonl")
        process = fake_process(self.tmp_path, self.lines, stderr=f"stderr {FAKE_TOKEN}\n")
        return agent.run_noninteractive(
            process, limit_s, name, stream_path, stderr_path, monitor, stop=kill_process([])
        )


def run_one(config, tmp_path, runner, environ=SUBSCRIPTION_ENV):
    trial_dir = make_trial(tmp_path, TrialId("calibration", "A", "e01"), config)
    result = agent.batch_session(trial_dir, config, batch_id="test", runner=runner, environ=environ)
    return trial_dir, result, read_json(trial_dir / "trial.json")


def test_a_completed_session_is_valid_and_recorded_as_unattended(config, tmp_path):
    runner = ScriptedRunner(success_lines(config))
    _trial_dir, result, record = run_one(config, tmp_path, runner)
    assert runner.calls[0]["marked_started"]  # marked before the container starts
    assert runner.calls[0]["limit"] == 60 * config.agent["wall_clock_limit_minutes"]
    assert "Synthetic prompt for tests." in "".join(runner.calls[0]["command"])
    assert record["validity"] == "valid"
    assert result["mode"] == agent.BATCH_AGENT_MODE
    assert result["execution_mode"] == agent.EXECUTION_MODE_BATCH == agent.execution_mode(record)
    assert result["completion"] == "completed"
    assert result["continuation_messages"] == 0
    assert result["assistant_messages"] == 2  # read from the session log, as for manual sessions
    assert "total_cost_usd" not in json.dumps(record)


@pytest.mark.parametrize(
    ("runner", "validity", "completion"),
    [
        (lambda c: ScriptedRunner([init_event(c), api_retry("authentication_failed", 401)]), "invalid", "stopped"),
        (lambda c: ScriptedRunner([init_event(c), rate_limit(status="rejected")]), "invalid", "stopped"),
        (lambda c: ScriptedRunner([init_event(c), rate_limit(isUsingOverage=True)]), "invalid", "stopped"),
        (lambda c: ScriptedRunner([init_event(c, apiKeySource="ANTHROPIC_API_KEY")]), "invalid", "stopped"),
        (lambda c: ScriptedRunner([init_event(c), assistant_text()], timed_out=True), "valid", "timed_out"),
        (lambda c: ScriptedRunner([init_event(c), assistant_text()]), "needs_review", "uncertain"),
        (lambda c: ScriptedRunner(success_lines(c), exit_code=1), "needs_review", "uncertain"),
        (lambda c: ScriptedRunner([*success_lines(c), "garbled"]), "needs_review", "uncertain"),
        (lambda c: ScriptedRunner(success_lines(c), transcript=False), "needs_review", "completed"),
    ],
)
def test_session_outcomes_are_classified(config, tmp_path, runner, validity, completion):
    _, result, record = run_one(config, tmp_path, runner(config))
    assert (record["validity"], result["completion"]) == (validity, completion), record["validity_reason"]


def test_a_trial_is_never_started_twice_and_no_credential_file_is_kept(config, tmp_path):
    runner = ScriptedRunner(success_lines(config))
    trial_dir, _, _ = run_one(config, tmp_path, runner)
    (trial_dir / "claude-config" / ".credentials.json").write_text("{}")
    with pytest.raises(agent.AgentError, match="never run twice"):
        agent.batch_session(trial_dir, config, batch_id="again", runner=runner, environ=SUBSCRIPTION_ENV)
    assert len(runner.calls) == 1


def test_a_session_never_starts_with_an_api_key_present(config, tmp_path):
    runner = ScriptedRunner(success_lines(config))
    with pytest.raises(agent.AgentError, match="ANTHROPIC_API_KEY"):
        run_one(config, tmp_path, runner, environ=SUBSCRIPTION_ENV | {"ANTHROPIC_API_KEY": "FAKEPLACEHOLDER"})
    assert runner.calls == []


# --------------------------------------------------------------------------------------
# Whole batches
# --------------------------------------------------------------------------------------


class Harness:
    """A batch wired to fakes: temporary trials and results roots, mocked Claude, fake evaluation."""

    def __init__(self, config, tmp_path, runner, *, completed=7):
        self.config = config
        self.trials_root = tmp_path / "trials"
        self.results_root = tmp_path / "results"
        self.runner = runner
        self.evaluate_error: Exception | None = None
        self.collect_error: Exception | None = None
        self.evaluated: list[str] = []
        self.output: list[str] = []
        self.schedule = [item.trial_id for item in make_schedule(config)]
        for trial_id in self.schedule[:completed]:  # trials already collected and evaluated
            self.write_completed(TrialId.parse(trial_id))

    def write_completed(self, trial):
        folder = self.results_root / trial.data_kind / str(trial)
        folder.mkdir(parents=True)
        agent_record = {"mode": "manual-session", "timed_out": False}
        write_json(
            folder / "trial.json",
            {"trial_id": str(trial), "data_kind": trial.data_kind, "validity": "valid", "agent": agent_record},
        )
        write_json(folder / "evaluation.json", {"synthetic": True})

    def results_dir_for(self, kind):
        return self.results_root / kind

    def collect(self, trial_dir, results_root):
        if self.collect_error is not None:
            raise self.collect_error
        return collect(trial_dir, results_root)

    def evaluate(self, result_dir):
        if self.evaluate_error is not None:
            raise self.evaluate_error
        evaluation = {"hidden": {"summary": {"hidden_pass_rate": 1.0}}, "synthetic": True}
        write_json(result_dir / "evaluation.json", evaluation)
        update_record(result_dir, evaluated_at="synthetic")
        self.evaluated.append(result_dir.name)
        return evaluation

    def deps(self, *, environ=SUBSCRIPTION_ENV, environment=(), freeze=()):
        return BatchDeps(
            self.config,
            prepare=fake_prepare,
            session=functools.partial(agent.batch_session, runner=self.runner),
            collect=self.collect,
            evaluate=self.evaluate,
            check_environment=lambda: list(environment),
            freeze_mismatches=lambda: list(freeze),
            results_dir_for=self.results_dir_for,
            check_workspace=lambda workspace, expected: None,
            environ=environ,
        )

    def run(self, **kwargs):
        deps = kwargs.pop("deps", None) or self.deps()
        kwargs.setdefault("confirm_extra_usage_off", True)
        return run_batch(self.config, self.trials_root, deps=deps, out=self.output.append, **kwargs)

    def journal(self):
        path = self.trials_root / JOURNAL_NAME
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def events(self):
        return [entry["event"] for entry in self.journal()]

    def snapshot(self):
        return {
            str(p.relative_to(self.results_root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(self.results_root.rglob("*"))
            if p.is_file()
        }


def test_trials_run_in_exact_schedule_order_up_to_the_limit(config, tmp_path):
    harness = Harness(config, tmp_path, ScriptedRunner(success_lines(config)))
    completed_before = harness.snapshot()
    assert harness.run(limit=3) == 0
    expected = harness.schedule[7:10]
    assert harness.evaluated == expected
    assert [read_json(Path(c["command"][c["command"].index("-v") + 1].split(":")[0]).parent / "trial.json")["trial_id"]
            for c in harness.runner.calls] == expected  # fmt: skip
    for trial_id in expected:
        record = read_json(harness.results_root / "genuine" / trial_id / "trial.json")
        assert record["agent"]["execution_mode"] == agent.EXECUTION_MODE_BATCH
        assert (harness.results_root / "genuine" / trial_id / "agent-output" / "agent-stream.jsonl").is_file()
    after = harness.snapshot()
    assert {k: after[k] for k in completed_before} == completed_before  # existing results untouched
    assert harness.events()[0] == "batch_started"
    assert harness.events()[-1] == "batch_finished"
    assert harness.events().count("session_started") == 3
    assert not (harness.trials_root / LOCK_NAME).exists()


def test_a_second_batch_continues_where_the_first_stopped(config, tmp_path):
    harness = Harness(config, tmp_path, ScriptedRunner(success_lines(config)))
    harness.run(limit=2)
    harness.run(limit=2)
    assert harness.evaluated == harness.schedule[7:11]
    assert len(harness.runner.calls) == 4  # no trial ran twice


def test_dry_run_changes_nothing(config, tmp_path):
    harness = Harness(config, tmp_path, ScriptedRunner(success_lines(config)))
    before = harness.snapshot()
    assert harness.run(limit=5, dry_run=True, confirm_extra_usage_off=False) == 0
    assert harness.runner.calls == []
    assert not harness.trials_root.exists()
    assert harness.snapshot() == before
    text = "\n".join(harness.output)
    for trial_id in harness.schedule[7:12]:
        assert trial_id in text
    assert harness.schedule[12] not in text
    assert "would refuse: confirm that extra usage is off" in text


@pytest.mark.parametrize(
    ("kwargs", "deps_kwargs", "message"),
    [
        ({"confirm_extra_usage_off": False}, {}, "extra usage"),
        ({}, {"environ": {}}, "not set"),
        ({}, {"environ": SUBSCRIPTION_ENV | {"ANTHROPIC_API_KEY": "FAKEPLACEHOLDER"}}, "ANTHROPIC_API_KEY"),
        ({}, {"environ": {agent.SUBSCRIPTION_CREDENTIAL: "sk-ant-api03-FAKEPLACEHOLDER"}}, "API key"),
        ({}, {"freeze": ["changed: experiments/experiment.json"]}, "FREEZE.json"),
        ({}, {"environment": ["proxy container rc-trials-proxy not running"]}, "proxy"),
        ({"limit": 0}, {}, "--limit"),
        ({"limit": 61}, {}, "--limit"),
    ],
)
def test_the_batch_refuses_to_start(config, tmp_path, kwargs, deps_kwargs, message):
    harness = Harness(config, tmp_path, ScriptedRunner(success_lines(config)))
    with pytest.raises(BatchRefusedError, match=message) as refused:
        harness.run(deps=harness.deps(**deps_kwargs), **kwargs)
    assert "FAKEPLACEHOLDER" not in str(refused.value)
    assert harness.runner.calls == []
    assert not harness.trials_root.exists()


def test_only_one_batch_runs_at_a_time(config, tmp_path):
    harness = Harness(config, tmp_path, ScriptedRunner(success_lines(config)))
    harness.trials_root.mkdir()
    (harness.trials_root / LOCK_NAME).write_text('{"batch_id": "another"}')
    with pytest.raises(BatchRefusedError, match="another batch"):
        harness.run(limit=1)
    assert harness.runner.calls == []
    assert (harness.trials_root / LOCK_NAME).exists()  # never removed automatically


@pytest.mark.parametrize(
    "lines",
    [
        lambda c: [init_event(c), api_retry("authentication_failed", 401)],
        lambda c: [init_event(c), rate_limit(status="rejected")],
        lambda c: [init_event(c), rate_limit(overageStatus="allowed")],
        lambda c: [init_event(c), assistant_text()],  # no result: uncertain completion
    ],
)
def test_the_batch_stops_and_does_not_skip_ahead(config, tmp_path, lines):
    harness = Harness(config, tmp_path, ScriptedRunner(lines(config)))
    assert harness.run(limit=5) == 1
    first = harness.schedule[7]
    assert len(harness.runner.calls) == 1
    assert harness.evaluated == []
    assert not (harness.results_root / "genuine" / first).exists()  # not collected
    assert read_json(harness.trials_root / first / "trial.json")["validity"] in ("invalid", "needs_review")
    # The next batch refuses to continue past the trial that needs a decision.
    assert harness.run(limit=5) == 1
    assert len(harness.runner.calls) == 1
    assert "needs a decision" in harness.output[-1]


def test_a_timed_out_trial_is_collected_then_the_batch_stops_for_review(config, tmp_path):
    runner = ScriptedRunner([init_event(config), assistant_text()], timed_out=True)
    harness = Harness(config, tmp_path, runner)
    assert harness.run(limit=3) == 1
    assert harness.evaluated == [harness.schedule[7]]
    assert len(runner.calls) == 1
    assert "wall-clock limit" in harness.output[-1]
    # Running again continues with the next trial; the timed-out one is not rerun.
    runner.timed_out = False
    runner.lines = success_lines(config)
    assert harness.run(limit=1) == 0
    assert harness.evaluated == harness.schedule[7:9]


def test_failed_collection_stops_and_resumes_without_a_second_session(config, tmp_path):
    harness = Harness(config, tmp_path, ScriptedRunner(success_lines(config)))
    harness.collect_error = CollectionError("submission exceeds the size limit")
    assert harness.run(limit=2) == 1
    assert "collect_failed" in harness.events()
    assert len(harness.runner.calls) == 1
    harness.collect_error = None
    assert harness.run(limit=1) == 0
    assert harness.evaluated == harness.schedule[7:9]  # the first was collected on resume, then one new session
    assert len(harness.runner.calls) == 2


def test_failed_evaluation_stops_and_resumes_with_evaluation_only(config, tmp_path):
    harness = Harness(config, tmp_path, ScriptedRunner(success_lines(config)))
    harness.evaluate_error = RuntimeError("sandbox image missing")
    assert harness.run(limit=2) == 1
    first = harness.schedule[7]
    assert (harness.results_root / "genuine" / first / "trial.json").is_file()
    assert not (harness.results_root / "genuine" / first / "evaluation.json").exists()
    harness.evaluate_error = None
    steps = plan(config, harness.trials_root.resolve(), harness.deps(), 1)
    assert (steps[0].trial_id, steps[0].action) == (first, "evaluate")
    assert harness.run(limit=1) == 0
    assert harness.evaluated == harness.schedule[7:9]
    assert len(harness.runner.calls) == 2


def test_an_interrupted_trial_is_never_rerun(config, tmp_path):
    harness = Harness(config, tmp_path, ScriptedRunner(success_lines(config), error=KeyboardInterrupt()))
    assert harness.run(limit=3) == 130
    first = harness.schedule[7]
    record = read_json(harness.trials_root / first / "trial.json")
    assert record.get("batch")
    assert not record.get("agent")
    assert not (harness.trials_root / LOCK_NAME).exists()  # the lock is released
    assert harness.events()[-1] == "batch_finished"
    harness.runner.error = None
    assert harness.run(limit=3) == 1
    assert len(harness.runner.calls) == 1  # the interrupted trial was not started again
    assert "interrupted" in harness.output[-1]


def test_an_unexpected_failure_releases_the_lock_and_is_logged(config, tmp_path):
    harness = Harness(config, tmp_path, ScriptedRunner(success_lines(config), error=OSError("disk full")))
    with pytest.raises(OSError, match="disk full"):
        harness.run(limit=1)
    assert not (harness.trials_root / LOCK_NAME).exists()
    assert harness.journal()[-1]["reason"] == "unexpected error: OSError"


def test_completed_or_collected_trials_are_never_prepared_again(config, tmp_path):
    harness = Harness(config, tmp_path, ScriptedRunner(success_lines(config)), completed=8)
    # A trial dir that still exists for an already collected trial is ignored.
    make_trial(harness.trials_root, TrialId.parse(harness.schedule[7]), config)
    assert harness.run(limit=1) == 0
    assert harness.evaluated == [harness.schedule[8]]
    assert len(harness.runner.calls) == 1


def test_a_prepared_but_unstarted_trial_is_run_after_its_workspace_is_checked(config, tmp_path):
    harness = Harness(config, tmp_path, ScriptedRunner(success_lines(config)))
    make_trial(harness.trials_root, TrialId.parse(harness.schedule[7]), config)
    checked = []
    deps = harness.deps()
    deps.check_workspace = lambda workspace, expected: checked.append((workspace.parent.name, expected))
    assert harness.run(limit=1, deps=deps) == 0
    assert checked
    assert checked[0][0] == harness.schedule[7]

    def changed(workspace, expected):
        raise RuntimeError("extra file")

    make_trial(harness.trials_root, TrialId.parse(harness.schedule[8]), config)
    deps.check_workspace = changed
    assert harness.run(limit=1, deps=deps) == 1
    assert "workspace_check_failed" in harness.events()
    assert len(harness.runner.calls) == 1


def test_an_invalid_trial_moved_aside_is_rerun_at_most_twice(config, tmp_path):
    harness = Harness(config, tmp_path, ScriptedRunner([init_event(config), rate_limit(status="rejected")]))
    first = harness.schedule[7]
    for attempt in (1, 2, 3):
        assert harness.run(limit=1) == 1  # stopped: usage limit, invalid
        record = read_json(harness.trials_root / first / "trial.json")
        assert record["validity"] == "invalid"
        assert record["attempt"] == attempt
        aside = harness.trials_root / "invalid-attempts" / f"{first}-attempt{attempt}"
        aside.parent.mkdir(exist_ok=True)
        (harness.trials_root / first).rename(aside)  # the operator's documented step
    assert harness.run(limit=1) == 1
    assert len(harness.runner.calls) == 3  # no fourth attempt
    assert "at most two reruns" in harness.output[-1]


def test_a_collected_trial_that_is_not_valid_is_never_skipped(config, tmp_path):
    harness = Harness(config, tmp_path, ScriptedRunner(success_lines(config)))
    first = harness.schedule[7]
    harness.write_completed(TrialId.parse(first))
    update_record(harness.results_root / "genuine" / first, validity="invalid", validity_reason="usage limit")
    assert harness.run(limit=3) == 1
    assert harness.runner.calls == []
    assert "collected with validity 'invalid'" in harness.output[-1]


def test_engineering_validation_runs_stay_outside_the_schedule(config, tmp_path):
    harness = Harness(config, tmp_path, ScriptedRunner(success_lines(config)))
    before = harness.snapshot()
    assert harness.run(engineering="calibration--A") == 0
    assert harness.run(engineering="calibration--A") == 0
    engineering = harness.results_root / "engineering"
    assert sorted(p.name for p in engineering.iterdir()) == ["calibration--A--e01", "calibration--A--e02"]
    assert read_json(engineering / "calibration--A--e01" / "trial.json")["data_kind"] == "engineering"
    after = harness.snapshot()
    assert {k: v for k, v in after.items() if not k.startswith("engineering/")} == before
    steps = plan(config, harness.trials_root.resolve(), harness.deps(), 1)
    assert steps[0].trial_id == harness.schedule[7]  # the schedule did not move
    with pytest.raises(BatchRefusedError, match="single session"):
        harness.run(engineering="calibration--A", limit=2)
    with pytest.raises(BatchRefusedError, match="TASK--CONDITION"):
        harness.run(engineering="calibration")


def test_logs_and_records_never_contain_the_token(config, tmp_path):
    lines = [*success_lines(config)[:-1], assistant_text(f"leaked {FAKE_TOKEN}"), result_event()]
    scenarios = tmp_path / "scenarios"
    scenarios.mkdir()
    harness = Harness(config, tmp_path, ProcessRunner(scenarios, lines))
    assert harness.run(limit=2) == 0
    assert harness.evaluated == harness.schedule[7:9]
    for root in (harness.trials_root, harness.results_root):
        for path in root.rglob("*"):
            if path.is_file():
                assert FAKE_TOKEN not in path.read_text(errors="replace"), path


def test_the_cli_reports_a_refusal_without_starting_anything(monkeypatch, tmp_path, capsys):
    from rc_experiments import cli

    monkeypatch.delenv(agent.SUBSCRIPTION_CREDENTIAL, raising=False)
    code = cli.main(["batch", "--limit", "0", "--trials-root", str(tmp_path / "t")])
    assert code == 2
    assert "REFUSED" in capsys.readouterr().err
    assert not (tmp_path / "t").exists()


def test_ci_never_runs_a_batch():
    from rc_experiments.config import REPO_DIR

    for workflow in (REPO_DIR / ".github" / "workflows").glob("*.yml"):
        text = workflow.read_text(encoding="utf-8")
        for line in text.splitlines():
            if "rc-exp batch" in line:
                assert "--dry-run" in line, (workflow.name, line)


def test_the_real_process_runner_is_the_default():
    """Production uses the streaming runner and Docker stop, not a fake."""
    assert agent.batch_session.__kwdefaults__["runner"] is agent.run_noninteractive
    assert agent.run_noninteractive.__kwdefaults__["stop"] is agent.stop_container
    assert BatchDeps.__dataclass_fields__["session"].default is agent.batch_session
