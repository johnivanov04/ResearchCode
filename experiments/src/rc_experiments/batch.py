"""Unattended batches of trials (protocol 1.5): ``rc-exp batch``.

A batch runs the remaining trials one after another, in the exact order of the randomised
schedule (``make_schedule``, the same order as ``rc-exp next``). Each trial uses the same
workspace preparation, prompt, container, model, effort, time limit, collection, and hidden
evaluation as a manual session; only the session itself is non-interactive
(:func:`rc_experiments.agent.batch_session`).

Safety rules:

* **Subscription only.** The batch refuses to start if the subscription token is missing,
  malformed, or ambiguous, if any API key or provider variable is set, or if the operator has
  not confirmed that extra usage is off. During a session, any sign of an API key, paid usage,
  a usage limit, or an authentication error stops the container at once.
* **Stop, never guess.** After any trial that is not a valid, completed session, after a
  timeout, and after any collection or evaluation error, the batch stops and says why. It
  never skips a trial: the schedule order is kept.
* **Never twice.** A trial is started at most once. Its record is marked before the container
  starts, so an interrupted trial is recognised and left for a human decision (protocol
  section 10). Results are never overwritten.
* **Resumable.** State is read from disk each time: a trial that ran but was not collected is
  collected, and a collected trial without an evaluation is evaluated, before new sessions.
* **One batch at a time** (a lock file), and an append-only journal of every step
  (``<trials-root>/batch-log.jsonl``). Neither ever contains credentials.

Engineering validation runs (``--engineering-validation TASK--CONDITION``) test the harness on
a real task outside the schedule. They get replicate ``eNN``, are stored under
``results/engineering/``, and are never analysed with pilot or confirmatory data.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import socket
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rc_experiments import agent as agent_module
from rc_experiments import pipeline, workspace
from rc_experiments.config import Config
from rc_experiments.trials import TrialId, make_schedule, now_utc, read_json, update_record

LOCK_NAME = ".rc-batch.lock"
JOURNAL_NAME = "batch-log.jsonl"
MAX_LIMIT = 60  # the whole schedule; a typo such as --limit 500 is refused
INVALID_ATTEMPTS = "invalid-attempts"  # where the operator moves invalid attempts (docs/RUNNING_TRIALS.md)
MAX_ATTEMPTS = 3  # protocol section 10: an invalid trial is rerun at most twice


def previous_attempts(trial_id: str, trials_root: Path) -> int:
    """Invalid attempts of this trial that the operator has moved aside."""
    folder = trials_root / INVALID_ATTEMPTS
    return len(list(folder.glob(f"{trial_id}-attempt*"))) if folder.is_dir() else 0


class BatchRefusedError(RuntimeError):
    """The batch did not start; nothing was run."""


class BatchStoppedError(RuntimeError):
    """The batch stopped after a step that needs a human decision."""


@dataclass
class BatchDeps:
    """Everything the batch does to the outside world (replaced by fakes in the tests)."""

    config: Config
    prepare: Callable[[TrialId, Path, Config, str], Path] = workspace.prepare
    session: Callable[..., dict[str, Any]] = agent_module.batch_session
    collect: Callable[[Path, Path], Path] = pipeline.collect
    evaluate: Callable[[Path], dict[str, Any]] | None = None
    check_environment: Callable[[], list[str]] | None = None
    freeze_mismatches: Callable[[], list[str]] | None = None
    results_dir_for: Callable[[str], Path] = pipeline.results_dir_for
    check_workspace: Callable[[Path, dict[str, str]], None] = workspace.check_workspace
    environ: Mapping[str, str] = field(default_factory=lambda: os.environ)

    def run_evaluate(self, result_dir: Path) -> dict[str, Any]:
        if self.evaluate is not None:
            return self.evaluate(result_dir)
        from rc_experiments.sandbox import DockerBackend

        return pipeline.evaluate_collected(result_dir, DockerBackend(self.config), self.config)

    def environment_problems(self) -> list[str]:
        if self.check_environment is not None:
            return self.check_environment()
        return agent_module.check_environment(self.config)

    def frozen_files_changed(self) -> list[str]:
        if self.freeze_mismatches is not None:
            return self.freeze_mismatches()
        from rc_experiments.freeze import verify_freeze

        return list(verify_freeze(require_private=True)["mismatches"])


# --------------------------------------------------------------------------------------
# Trial state, read from disk
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Step:
    trial_id: str
    kind: str
    order: int | None  # position in the schedule (None for engineering runs)
    state: str
    action: str  # "skip", "evaluate", "collect", "run", or "stop"
    detail: str = ""


def _collectable(record: Mapping[str, Any]) -> bool:
    """A finished session that may be collected without a human decision."""
    if record.get("validity") != "valid":
        return False
    agent = record.get("agent") or {}
    if agent_module.execution_mode(record) == agent_module.EXECUTION_MODE_INTERACTIVE:
        return True
    return agent.get("completion") in ("completed", "timed_out")


def trial_state(trial: TrialId, trials_root: Path, deps: BatchDeps, order: int | None = None) -> Step:
    kind = trial.data_kind
    trial_id = str(trial)
    result_dir = deps.results_dir_for(kind) / trial_id
    if (result_dir / "trial.json").is_file():
        validity = read_json(result_dir / "trial.json").get("validity")
        if validity != "valid":  # e.g. an invalid attempt that was collected but not yet moved aside
            return Step(
                trial_id, kind, order, "collected-not-valid", "stop",
                f"collected with validity {validity!r}; decide it or move it aside (docs/RUNNING_TRIALS.md)",
            )  # fmt: skip
        if (result_dir / "evaluation.json").is_file():
            return Step(trial_id, kind, order, "evaluated", "skip")
        return Step(trial_id, kind, order, "collected", "evaluate", "collected but not evaluated")
    trial_dir = trials_root / trial_id
    if not trial_dir.exists():
        attempts = previous_attempts(trial_id, trials_root)
        if attempts >= MAX_ATTEMPTS:
            return Step(
                trial_id, kind, order, "attempts-exhausted", "stop",
                f"{attempts} invalid attempts already; protocol section 10 allows at most two reruns",
            )  # fmt: skip
        return Step(trial_id, kind, order, "new", "run", f"attempt {attempts + 1}" if attempts else "")
    if not (trial_dir / "trial.json").is_file():
        return Step(trial_id, kind, order, "unknown", "stop", f"{trial_dir} exists without a trial record")
    record = read_json(trial_dir / "trial.json")
    if record.get("agent"):
        if _collectable(record):
            return Step(trial_id, kind, order, "finished", "collect", "session finished; not yet collected")
        return Step(
            trial_id, kind, order, "needs-decision", "stop",
            f"validity {record.get('validity')!r}: {record.get('validity_reason')}",
        )  # fmt: skip
    if record.get("batch") or (trial_dir / "claude-config").exists():
        return Step(
            trial_id, kind, order, "interrupted", "stop",
            "a session was started but never recorded (interrupted); see docs/RUNNING_TRIALS.md",
        )  # fmt: skip
    return Step(trial_id, kind, order, "prepared", "run", "workspace prepared; not started")


def plan(config: Config, trials_root: Path, deps: BatchDeps, limit: int) -> list[Step]:
    """The steps a batch would take, in schedule order, up to ``limit`` new sessions."""
    steps: list[Step] = []
    sessions = 0
    for item in make_schedule(config):
        step = trial_state(TrialId.parse(item.trial_id), trials_root, deps, item.order)
        if step.action == "skip":
            continue
        if step.action == "run":
            if sessions >= limit:
                break
            sessions += 1
        steps.append(step)
        if step.action == "stop":
            break
    return steps


def next_engineering_trial(task_and_condition: str, config: Config, trials_root: Path, deps: BatchDeps) -> TrialId:
    """The next unused engineering replicate (e01, e02, ...) for a task and condition."""
    match = re.fullmatch(r"([a-z0-9-]+)--([A-Z])", task_and_condition)
    if not match:
        raise BatchRefusedError("--engineering-validation expects TASK--CONDITION, for example calibration--A")
    task, condition = match.groups()
    config.task(task)
    config.condition(condition)
    used = set()
    for root in (deps.results_dir_for("engineering"), trials_root):
        for path in root.glob(f"{task}--{condition}--e[0-9][0-9]") if root.is_dir() else []:
            used.add(int(path.name[-2:]))
    return TrialId(task, condition, f"e{max(used, default=0) + 1:02d}")


# --------------------------------------------------------------------------------------
# Journal and lock
# --------------------------------------------------------------------------------------


class Journal:
    """Append-only JSON-lines log of every batch step (no credentials, ever)."""

    def __init__(self, path: Path, batch_id: str) -> None:
        self.path, self.batch_id = path, batch_id

    def write(self, event: str, **fields: Any) -> None:
        entry = {"time": now_utc(), "batch_id": self.batch_id, "event": event, **fields}
        line = pipeline.redact_secrets(json.dumps(entry, sort_keys=False, default=str))
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())


class BatchLock:
    def __init__(self, path: Path, batch_id: str) -> None:
        self.path, self.batch_id = path, batch_id

    def __enter__(self) -> BatchLock:
        try:
            descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            try:
                holder = self.path.read_text(encoding="utf-8").strip()
            except OSError:
                holder = "unreadable"
            raise BatchRefusedError(
                f"another batch holds {self.path} ({holder}). If no batch is running (for example after a "
                "crash), read the end of the batch log, then delete the lock file by hand"
            ) from None
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps({"batch_id": self.batch_id, "pid": os.getpid(), "host": socket.gethostname()}))
        return self

    def __exit__(self, *exc: object) -> None:
        self.path.unlink(missing_ok=True)


# --------------------------------------------------------------------------------------
# Running
# --------------------------------------------------------------------------------------


def preflight_problems(deps: BatchDeps, *, confirm_extra_usage_off: bool) -> list[str]:
    """Every reason not to start (empty if the batch may start). Never includes a credential."""
    problems = agent_module.subscription_auth_problems(deps.environ)
    if not confirm_extra_usage_off:
        problems.append(
            "confirm that extra usage is off (claude.ai, Settings > Usage) by passing --confirm-extra-usage-off"
        )
    mismatches = deps.frozen_files_changed()
    if mismatches:
        problems.append(f"{len(mismatches)} files differ from FREEZE.json: {mismatches[:3]}")
    problems += deps.environment_problems()
    return list(dict.fromkeys(problems))  # the token check appears in two lists; report it once


def _run_step(step: Step, trials_root: Path, deps: BatchDeps, journal: Journal, batch_id: str) -> str:
    """Carry out one step. Returns "session" when a new session ran, else "resumed"."""
    config = deps.config
    trial = TrialId.parse(step.trial_id)
    trial_dir = trials_root / step.trial_id
    results_root = deps.results_dir_for(step.kind)
    if step.action == "evaluate":
        journal.write("evaluate_started", trial_id=step.trial_id, resumed=True)
        _evaluate(results_root / step.trial_id, step, deps, journal)
        return "resumed"
    if step.action == "collect":
        result_dir = _collect(trial_dir, results_root, step, deps, journal)
        _evaluate(result_dir, step, deps, journal)
        _stop_after_timeout(read_json(result_dir / "trial.json"), step, journal)
        return "resumed"
    # A new session: check everything again right before it starts.
    problems = agent_module.subscription_auth_problems(deps.environ)
    problems += [f"files differ from FREEZE.json: {m}" for m in deps.frozen_files_changed()[:3]]
    problems += deps.environment_problems()
    if problems:
        journal.write("refused_before_session", trial_id=step.trial_id, problems=problems)
        raise BatchStoppedError(f"not starting {step.trial_id}: " + "; ".join(problems))
    if step.state == "new":
        deps.prepare(trial, trials_root, config, step.kind)
        journal.write("prepared", trial_id=step.trial_id)
    record = read_json(trial_dir / "trial.json")
    try:
        deps.check_workspace(trial_dir / "workspace", record["workspace_files"])
    except Exception as error:
        journal.write("workspace_check_failed", trial_id=step.trial_id, error=str(error))
        raise BatchStoppedError(f"{step.trial_id}: the prepared workspace changed ({error}); not starting") from error
    attempt = previous_attempts(step.trial_id, trials_root) + 1
    update_record(trial_dir, attempt=attempt)
    journal.write("session_started", trial_id=step.trial_id, order=step.order, kind=step.kind, attempt=attempt)
    try:
        agent = deps.session(trial_dir, config, batch_id=batch_id, environ=deps.environ)
    except agent_module.AgentError as error:
        journal.write("session_refused", trial_id=step.trial_id, error=str(error))
        raise BatchStoppedError(f"{step.trial_id}: {error}") from error
    record = read_json(trial_dir / "trial.json")
    journal.write(
        "session_finished",
        trial_id=step.trial_id,
        validity=record.get("validity"),
        validity_reason=record.get("validity_reason"),
        completion=agent.get("completion"),
        stop_category=agent.get("stop_category"),
        timed_out=agent.get("timed_out"),
        wall_clock_seconds=agent.get("wall_clock_seconds"),
        exit_code=agent.get("exit_code"),
    )
    if not _collectable(record):
        raise BatchStoppedError(
            f"{step.trial_id} is {record.get('validity')!r} ({record.get('validity_reason')}). It was not "
            f"collected. Review {trial_dir} and follow 'Validity and reruns' in docs/RUNNING_TRIALS.md"
        )
    result_dir = _collect(trial_dir, results_root, step, deps, journal)
    _evaluate(result_dir, step, deps, journal)
    _stop_after_timeout(record, step, journal)
    return "session"


def _collect(trial_dir: Path, results_root: Path, step: Step, deps: BatchDeps, journal: Journal) -> Path:
    try:
        result_dir = deps.collect(trial_dir, results_root)
    except Exception as error:
        journal.write("collect_failed", trial_id=step.trial_id, error=f"{type(error).__name__}: {error}")
        raise BatchStoppedError(f"collecting {step.trial_id} failed: {error}") from error
    journal.write("collected", trial_id=step.trial_id, result_dir=str(result_dir))
    return result_dir


def _evaluate(result_dir: Path, step: Step, deps: BatchDeps, journal: Journal) -> None:
    try:
        evaluation = deps.run_evaluate(result_dir)
    except Exception as error:
        journal.write("evaluate_failed", trial_id=step.trial_id, error=f"{type(error).__name__}: {error}")
        raise BatchStoppedError(
            f"evaluating {step.trial_id} failed: {error}. Fix the cause, then run the batch again: it evaluates "
            "collected trials before starting new sessions"
        ) from error
    summary = (evaluation.get("hidden") or {}).get("summary") or {}
    journal.write("evaluated", trial_id=step.trial_id, hidden_pass_rate=summary.get("hidden_pass_rate"))


def _stop_after_timeout(record: Mapping[str, Any], step: Step, journal: Journal) -> None:
    if (record.get("agent") or {}).get("timed_out"):
        journal.write("stopped_for_review", trial_id=step.trial_id, reason="wall-clock limit reached")
        raise BatchStoppedError(
            f"{step.trial_id} reached the wall-clock limit. It was collected and evaluated as a valid trial "
            "(protocol section 10); check its log before running the next batch"
        )


def run_batch(
    config: Config,
    trials_root: Path,
    *,
    limit: int = 1,
    dry_run: bool = False,
    confirm_extra_usage_off: bool = False,
    engineering: str | None = None,
    deps: BatchDeps | None = None,
    out: Callable[[str], None] = print,
) -> int:
    """Run (or, with ``dry_run``, only show) up to ``limit`` new sessions. Returns an exit code.

    0: the batch did what was asked; 1: it stopped for a human decision; 2: it refused to start.
    """
    deps = deps or BatchDeps(config)
    if not 1 <= limit <= MAX_LIMIT:
        raise BatchRefusedError(f"--limit must be between 1 and {MAX_LIMIT}")
    trials_root = trials_root.resolve()
    if engineering is not None and limit != 1:
        raise BatchRefusedError("an engineering validation run is a single session; do not combine it with --limit")

    def current_steps() -> list[Step]:
        if engineering is not None:
            return [trial_state(next_engineering_trial(engineering, config, trials_root, deps), trials_root, deps)]
        return plan(config, trials_root, deps, limit)

    problems = preflight_problems(deps, confirm_extra_usage_off=confirm_extra_usage_off)
    if dry_run:
        steps = current_steps()
        out(f"Dry run: nothing is started, prepared, or written. Up to {limit} new session(s).")
        for step in steps:
            where = f"order {step.order}" if step.order is not None else "engineering validation, outside the schedule"
            detail = f": {step.detail}" if step.detail else ""
            out(f"  {step.action:8s} {step.trial_id:28s} {where:10s} {step.state}{detail}")
        if not steps:
            out("  nothing to do: every scheduled trial has been collected and evaluated")
        out("Checks before a real batch:" if problems else "Checks before a real batch: all pass.")
        for problem in problems:
            out(f"  would refuse: {problem}")
        return 0
    if problems:
        raise BatchRefusedError("; ".join(problems))

    trials_root.mkdir(parents=True, exist_ok=True)
    batch_id = f"{now_utc().replace(':', '').replace('+00:00', 'Z')}-{secrets.token_hex(3)}"
    journal = Journal(trials_root / JOURNAL_NAME, batch_id)
    sessions = 0
    with BatchLock(trials_root / LOCK_NAME, batch_id):
        steps = current_steps()  # read under the lock, so no other batch can change the state
        if not steps:
            out("nothing to do: every scheduled trial has been collected and evaluated")
            return 0
        journal.write(
            "batch_started",
            limit=limit,
            engineering=engineering,
            protocol_version=config.protocol_version,
            planned=[(s.trial_id, s.action) for s in steps],
        )
        reason, code = "completed", 0
        try:
            for step in steps:
                if step.action == "stop":
                    journal.write("stopped_for_review", trial_id=step.trial_id, reason=step.detail)
                    raise BatchStoppedError(
                        f"{step.trial_id} needs a decision before the batch can continue: {step.detail}"
                    )
                out(f"{step.action}: {step.trial_id}")
                if _run_step(step, trials_root, deps, journal, batch_id) == "session":
                    sessions += 1
                    out(f"  done: {step.trial_id} ({sessions} of up to {limit} session(s))")
        except BatchStoppedError as stop:
            reason, code = str(stop), 1
            out(f"STOPPED: {stop}")
        except KeyboardInterrupt:
            reason, code = "interrupted by the operator", 130
            out("INTERRUPTED: the current trial, if any, is left for a human decision (it is never rerun)")
        except Exception as error:  # an unexpected failure stops the batch; it is logged first
            journal.write("batch_finished", sessions=sessions, reason=f"unexpected error: {type(error).__name__}")
            raise
        journal.write("batch_finished", sessions=sessions, reason=reason)
    return code
