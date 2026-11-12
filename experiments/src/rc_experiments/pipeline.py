"""Collect a finished trial and evaluate it.

Results are stored per data kind, never mixed:

    experiments/results/genuine/<trial-id>/   confirmatory trials (committed)
    experiments/results/pilot/<trial-id>/     pilot trials (committed, never analysed with genuine data)
    <any directory outside results/>          fixture trials (dry runs; refused inside results/)

Each trial directory holds ``trial.json``, ``prompt.txt``, ``session-logs/`` (Claude Code's own
session logs, if any), ``submission/`` (the workspace as the agent left it, minus caches and
virtual environments), and ``evaluation.json``.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

from rc_experiments import static
from rc_experiments.config import RESULTS_DIR, Config
from rc_experiments.evaluators import for_data_kind
from rc_experiments.freeze import verify_freeze
from rc_experiments.grading import evaluate_hidden
from rc_experiments.sandbox import Backend
from rc_experiments.test_quality import evaluate_own_tests
from rc_experiments.trials import now_utc, read_json, update_record, write_json

MAX_SUBMISSION_BYTES = 20_000_000
MAX_SUBMISSION_FILES = 5_000
SKIP_NAMES = static.SKIP_DIRS | {".uv-cache", ".cache", ".mypy_cache", ".DS_Store"}


class CollectionError(RuntimeError):
    pass


# Credential-like strings are redacted from saved session logs (defence in depth: the harness
# never writes credentials into a session, but a log is published with the results).
_SECRET_PATTERNS = (
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"(?i)(authorization\W{0,3}bearer\s+)[A-Za-z0-9._\-]{16,}"),
    re.compile(r"(?i)((?:api[_-]?key|oauth[_-]?token|access[_-]?token)\W{0,3}[:=]\W{0,3})[A-Za-z0-9._\-]{16,}"),
)


def redact_secrets(text: str) -> str:
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(lambda m: (m.group(1) if m.groups() else "") + "[REDACTED]", text)
    return text


def results_dir_for(kind: str, fixture_root: Path | None = None) -> Path:
    if kind == "fixture":
        if fixture_root is None:
            raise ValueError("fixture results need an explicit directory outside experiments/results")
        if fixture_root.resolve().is_relative_to(RESULTS_DIR.resolve()):
            raise ValueError("fixture results may never be written inside experiments/results")
        return fixture_root
    if kind not in ("genuine", "pilot"):
        raise ValueError(f"unknown data kind {kind!r}")
    return RESULTS_DIR / kind


def _copy_tree(source: Path, target: Path, budget: dict[str, int], skipped: list[str]) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for item in sorted(source.iterdir()):
        relative = item.name
        if item.is_symlink():
            skipped.append(f"{item} (symbolic link)")
            continue
        if item.name in SKIP_NAMES or item.name.endswith(".egg-info"):
            continue
        if item.is_dir():
            _copy_tree(item, target / relative, budget, skipped)
        elif item.is_file():
            budget["files"] += 1
            budget["bytes"] += item.stat().st_size
            if budget["files"] > MAX_SUBMISSION_FILES or budget["bytes"] > MAX_SUBMISSION_BYTES:
                raise CollectionError("submission exceeds the size limit")
            shutil.copyfile(item, target / relative)


def collect(trial_dir: Path, results_root: Path) -> Path:
    """Copy the trial's record, transcript, and workspace into ``results_root/<trial-id>``."""
    record = read_json(trial_dir / "trial.json")
    if not record.get("agent"):
        raise CollectionError("the agent has not run for this trial")
    destination = results_root / record["trial_id"]
    if destination.exists():
        raise FileExistsError(f"{destination} already exists; results are never overwritten")
    destination.mkdir(parents=True)
    skipped: list[str] = []
    budget = {"files": 0, "bytes": 0}
    _copy_tree(trial_dir / "workspace", destination / "submission", budget, skipped)
    if (trial_dir / "prompt.txt").is_file():
        shutil.copyfile(trial_dir / "prompt.txt", destination / "prompt.txt")
    # Only Claude Code's session logs are kept from the trial's configuration directory: never
    # settings, caches, or credentials.
    logs = (
        sorted((trial_dir / "claude-config" / "projects").rglob("*.jsonl"))
        if (trial_dir / "claude-config").is_dir()
        else []
    )
    for index, log in enumerate(logs):
        if log.is_file() and not log.is_symlink():
            (destination / "session-logs").mkdir(exist_ok=True)
            text = log.read_text(encoding="utf-8", errors="replace")
            (destination / "session-logs" / f"{index:02d}-{log.name}").write_text(
                redact_secrets(text), encoding="utf-8"
            )
    record["collected_at"] = now_utc()
    record["submission"] = {"files": budget["files"], "bytes": budget["bytes"], "skipped": skipped}
    write_json(destination / "trial.json", record)
    return destination


def evaluate_collected(result_dir: Path, backend: Backend, config: Config, *, own_tests: bool = True) -> dict[str, Any]:
    """Evaluate a collected submission and write ``evaluation.json`` (never overwritten)."""
    record = read_json(result_dir / "trial.json")
    output = result_dir / "evaluation.json"
    if output.exists():
        raise FileExistsError(f"{output} already exists")
    if record["data_kind"] != "fixture" and backend.name != "docker":
        raise ValueError("generated submissions must be evaluated in the Docker sandbox")
    submission = result_dir / "submission"
    freeze = verify_freeze(require_private=record["data_kind"] != "fixture")
    task = for_data_kind(record["data_kind"]).task(record["task"])
    evaluation: dict[str, Any] = {
        "trial_id": record["trial_id"],
        "task": record["task"],
        "condition": record["condition"],
        "data_kind": record["data_kind"],
        "evaluated_at": now_utc(),
        "protocol_version": config.protocol_version,
        "freeze": {
            "matches": not freeze["mismatches"],
            "combined_sha256": freeze["combined_sha256"],
            "mismatches": freeze["mismatches"][:20],
        },
        "evaluator": "fixture" if record["data_kind"] == "fixture" else "genuine",
        "hidden": evaluate_hidden(task, submission, backend, config),
        "own_tests": evaluate_own_tests(task, submission, backend, config) if own_tests else None,
        "static": static.analyse(submission),
    }
    write_json(output, evaluation)
    update_record(result_dir, evaluated_at=evaluation["evaluated_at"])
    return evaluation
