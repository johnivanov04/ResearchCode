"""Agent sessions for trials: manual, subscription-based Claude Code sessions, or fixtures.

Protocol 1.1 runs every trial as a **manual, interactive Claude Code session** that uses the
experimenter's existing Claude Pro subscription. Nothing in this module calls a model by
itself: a session starts only when the operator runs ``rc-exp session`` and ends when the
operator exits Claude Code or the time limit stops the container.

* :func:`session` opens Claude Code interactively in the agent container with only the trial
  workspace mounted, the trial's prompt already entered, the configured model and settings,
  and a new, empty Claude configuration directory (so no memory or history carries over
  between trials). After the session it reads the session log and records what happened.
* :func:`preflight` opens the same container with an empty directory and no prompt, so the
  operator can check the login (``/status``), the model (``/model``), and remaining usage
  (``/usage``) without starting a trial.
* :func:`run_fixture` writes trusted fixture code instead of running an agent (dry runs only).

Billing safety: the only credential ever passed into a container is ``CLAUDE_CODE_OAUTH_TOKEN``
(created with ``claude setup-token``, which uses the subscription). API keys, auth tokens,
alternative endpoints, and cloud-provider switches are never passed, even if they are set on
the host. Usage values are copied from Claude Code's own session log; nothing is estimated.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from rc_experiments.config import Config
from rc_experiments.trials import now_utc, read_json, update_record

AGENT_IMAGE_PREFIX = "researchcode-agent"
NETWORK = "rc-trials-internal"
PROXY_CONTAINER = "rc-trials-proxy"
PROXY_URL = f"http://{PROXY_CONTAINER}:8888"
CONTAINER_HOME = "/home/agent"
# The only credential passed into an agent container: a subscription token from `claude setup-token`.
SUBSCRIPTION_CREDENTIAL = "CLAUDE_CODE_OAUTH_TOKEN"
# Never passed, even when set on the host: they would bill API usage or route requests elsewhere.
FORBIDDEN_VARIABLES = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_BASE_URL",
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
)
CONTINUE_MESSAGE_PATH = Path(__file__).resolve().parents[2] / "conditions" / "CONTINUE.md"


class AgentError(RuntimeError):
    pass


def agent_image(config: Config) -> str:
    return f"{AGENT_IMAGE_PREFIX}:{config.agent['tool_version']}"


def claude_arguments(config: Config, prompt: str | None) -> list[str]:
    """Interactive Claude Code (no -p/--print). The prompt, if given, is the first message."""
    agent = config.agent
    args = ["claude"]
    if prompt is not None:
        args.append(prompt)  # before the variadic --disallowed-tools option
    return [
        *args,
        "--model",
        agent["model"],
        "--effort",
        agent["effort"],
        "--permission-mode",
        agent["permission_mode"],
        "--disallowed-tools",
        ",".join(agent["disallowed_tools"]),
    ]


def container_arguments(config: Config, name: str, workspace: Path, claude_config: Path) -> list[str]:
    """``docker run`` for an interactive agent container. Credentials are passed by name only."""
    limits = config.agent["container"]
    args = [
        "docker", "run", "--rm", "-it", "--name", name,
        "--network", NETWORK,
        "--cpus", str(limits["cpus"]), "--memory", limits["memory"], "--pids-limit", str(limits["pids_limit"]),
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "-e", f"HTTPS_PROXY={PROXY_URL}", "-e", f"HTTP_PROXY={PROXY_URL}",
        "-e", "DISABLE_AUTOUPDATER=1", "-e", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1",
        "-v", f"{workspace.resolve()}:/workspace",
        "-v", f"{claude_config.resolve()}:{CONTAINER_HOME}/.claude",
        "-w", "/workspace",
    ]  # fmt: skip
    if os.environ.get(SUBSCRIPTION_CREDENTIAL):
        args += ["-e", SUBSCRIPTION_CREDENTIAL]
    return [*args, agent_image(config)]


def _docker_ok(*args: str) -> bool:
    result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=60, check=False)
    return result.returncode == 0


def check_environment(config: Config, *, need_credential: bool = True) -> list[str]:
    """Problems that prevent a session (empty list if ready)."""
    problems = []
    if not _docker_ok("image", "inspect", agent_image(config)):
        problems.append(f"agent image {agent_image(config)} not built (rc-exp build-images)")
    if not _docker_ok("network", "inspect", NETWORK):
        problems.append(f"network {NETWORK} missing (rc-exp network up)")
    result = subprocess.run(
        ["docker", "inspect", "--format", "{{.State.Running}}", PROXY_CONTAINER],
        capture_output=True, text=True, timeout=60, check=False,
    )  # fmt: skip
    if result.stdout.strip() != "true":
        problems.append(f"proxy container {PROXY_CONTAINER} not running (rc-exp network up)")
    if need_credential and not os.environ.get(SUBSCRIPTION_CREDENTIAL):
        problems.append(
            f"{SUBSCRIPTION_CREDENTIAL} is not set: create it once with `claude setup-token` (subscription)"
        )
    return problems


def forbidden_variables_set() -> list[str]:
    """Billing-related variables set on the host. They are never passed on; this is a warning."""
    return [name for name in FORBIDDEN_VARIABLES if os.environ.get(name)]


# --------------------------------------------------------------------------------------
# Session logs
# --------------------------------------------------------------------------------------


def session_logs(claude_config: Path) -> list[Path]:
    return sorted(p for p in (claude_config / "projects").rglob("*.jsonl") if p.is_file())


def parse_session_logs(paths: list[Path]) -> dict[str, Any]:
    """Summarise Claude Code's session logs (one line per event; values are as recorded).

    Assistant messages are logged once per content block, so usage is counted once per
    message id. Subagent (sidechain) messages are reported separately.
    """
    messages: dict[str, dict[str, Any]] = {}
    tool_uses: dict[str, int] = {}
    human_messages = 0
    timestamps: list[str] = []
    versions: set[str] = set()
    efforts: set[str] = set()
    extra_usage_notices = 0
    api_errors: list[str] = []
    for path in paths:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue
            if event.get("timestamp"):
                timestamps.append(str(event["timestamp"]))
            if "extra usage" in line.lower():
                extra_usage_notices += 1
            kind = event.get("type")
            if kind == "assistant" and (event.get("isApiErrorMessage") or event.get("error")):
                blocks = (event.get("message") or {}).get("content") or []
                text = " ".join(str(b.get("text", "")) for b in blocks if isinstance(b, dict))
                api_errors.append((text or str(event.get("error")))[:200])
                continue
            if kind == "assistant":
                message = event.get("message") or {}
                if event.get("version"):
                    versions.add(str(event["version"]))
                if event.get("effort") and not event.get("isSidechain"):
                    efforts.add(str(event["effort"]))
                key = str(message.get("id") or event.get("uuid"))
                entry = messages.setdefault(
                    key, {"sidechain": bool(event.get("isSidechain")), "model": None, "usage": {}}
                )
                entry["model"] = message.get("model") or entry["model"]
                if isinstance(message.get("usage"), dict):
                    entry["usage"] = message["usage"]
                for block in message.get("content") or []:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        name = str(block.get("name", "?"))
                        tool_uses[name] = tool_uses.get(name, 0) + 1
            elif kind == "user" and not event.get("isMeta") and not event.get("isSidechain"):
                content = (event.get("message") or {}).get("content")
                is_tool_result = isinstance(content, list) and any(
                    isinstance(b, dict) and b.get("type") == "tool_result" for b in content
                )
                if not is_tool_result and not event.get("toolUseResult"):
                    human_messages += 1

    def total(field: str, sidechain: bool | None = None) -> int | None:
        values = [
            m["usage"].get(field)
            for m in messages.values()
            if (sidechain is None or m["sidechain"] == sidechain) and isinstance(m["usage"].get(field), int)
        ]
        return sum(values) if values else None

    main_models = sorted({m["model"] for m in messages.values() if not m["sidechain"] and m["model"]})
    sub_models = sorted({m["model"] for m in messages.values() if m["sidechain"] and m["model"]})
    return {
        "session_log_files": len(paths),
        "assistant_messages": sum(1 for m in messages.values() if not m["sidechain"]) if messages else None,
        "subagent_messages": sum(1 for m in messages.values() if m["sidechain"]) if messages else None,
        "human_messages": human_messages if paths else None,
        "main_models": main_models,
        "subagent_models": sub_models,
        "tool_versions": sorted(versions),
        "efforts": sorted(efforts),
        "tool_use_counts": tool_uses,
        "input_tokens": total("input_tokens"),
        "output_tokens": total("output_tokens"),
        "cache_creation_input_tokens": total("cache_creation_input_tokens"),
        "cache_read_input_tokens": total("cache_read_input_tokens"),
        "first_event": min(timestamps) if timestamps else None,
        "last_event": max(timestamps) if timestamps else None,
        "extra_usage_notices": extra_usage_notices,
        "api_error_messages": api_errors,
        "usage_limit_messages": sum(1 for e in api_errors if "limit" in e.lower()),
    }


def classify_session(record: dict[str, Any], config: Config) -> tuple[str, str]:
    """Protocol section 10 (version 1.1), applied to a manual session."""
    agent, report = config.agent, record
    if report.get("operator_reported_extra_usage") or report.get("extra_usage_notices"):
        return "invalid", "extra usage (paid overage) was reported; the session must not continue on paid usage"
    if report.get("operator_reported_usage_limit") or report.get("usage_limit_messages"):
        return "invalid", "the subscription's usage limit interrupted the session (infrastructure); rerun later"
    if report.get("api_error_messages"):
        return "needs_review", f"Claude Code reported API errors: {report['api_error_messages'][:2]}"
    if not report.get("session_log_files"):
        return "needs_review", "no session log was found; check that the session ran"
    if report.get("main_models") and report["main_models"] != [agent["model"]]:
        return "invalid", f"the session used {report['main_models']}, not the configured model {agent['model']}"
    if report.get("efforts") and report["efforts"] != [agent["effort"]]:
        return "invalid", f"the session used effort {report['efforts']}, not {agent['effort']}"
    if report.get("tool_versions") and report["tool_versions"] != [agent["tool_version"]]:
        return "invalid", f"Claude Code {report['tool_versions']} was used, not {agent['tool_version']}"
    leaked = sorted(set(report.get("tool_use_counts") or {}) & set(agent["disallowed_tools"]))
    if leaked:
        return "invalid", f"disallowed tools were used: {', '.join(leaked)}"
    if (report.get("continuation_messages") or 0) > agent["max_continuation_messages"]:
        return "invalid", "more continuation messages than the protocol allows"
    if report.get("operator_other_input"):
        return "invalid", "the operator typed something other than the standard continuation message"
    if report.get("timed_out"):
        return "valid", "reached the wall-clock limit (a valid outcome)"
    return "valid", "session completed"


# --------------------------------------------------------------------------------------
# Sessions
# --------------------------------------------------------------------------------------


def _ask_yes_no(ask: Callable[[str], str], question: str) -> bool:
    while True:
        answer = ask(f"{question} [y/n] ").strip().lower()
        if answer in {"y", "yes", "n", "no"}:
            return answer.startswith("y")


def _ask_count(ask: Callable[[str], str], question: str) -> int:
    while True:
        answer = ask(f"{question} ").strip()
        if answer.isdigit():
            return int(answer)


def operator_report(ask: Callable[[str], str] = input) -> dict[str, Any]:
    """Questions the operator answers right after each session (recorded verbatim)."""
    return {
        "continuation_messages": _ask_count(
            ask, "How many times did you send the standard continuation message? (0-2)"
        ),
        "operator_other_input": _ask_yes_no(
            ask,
            "Did you type anything else into the session"
            " (other than answering Claude Code's startup dialogs and /exit)?",
        ),
        "operator_reported_usage_limit": _ask_yes_no(ask, "Did Claude Code stop because a usage limit was reached?"),
        "operator_reported_extra_usage": _ask_yes_no(ask, "Did Claude Code mention extra usage or paid credits?"),
        "operator_notes": ask("Anything else to record (optional, one line): ").strip(),
    }


def run_interactive(command: list[str], limit_s: float, name: str) -> tuple[int | None, bool]:
    """Run an interactive container, stopping it at the time limit. Returns (exit code, timed out)."""
    process = subprocess.Popen(command)
    try:
        return process.wait(timeout=limit_s), False
    except subprocess.TimeoutExpired:
        subprocess.run(["docker", "stop", "--time", "5", name], capture_output=True, timeout=60, check=False)
        return process.wait(timeout=120), True


def session(
    trial_dir: Path,
    config: Config,
    *,
    ask: Callable[[str], str] = input,
    runner: Callable[[list[str], float, str], tuple[int | None, bool]] = run_interactive,
) -> dict[str, Any]:
    """Run one trial as a manual Claude Code session (protocol 1.1)."""
    problems = check_environment(config)
    if problems:
        raise AgentError("; ".join(problems))
    record = read_json(trial_dir / "trial.json")
    if record.get("agent"):
        raise AgentError(f"{record['trial_id']} already has a session; start a new attempt instead")
    claude_config = trial_dir / "claude-config"
    claude_config.mkdir()  # fails if it exists: every trial starts with an empty configuration
    prompt = (trial_dir / "prompt.txt").read_text(encoding="utf-8")
    name = f"rc-session-{record['trial_id'].replace('--', '-')}-{int(time.time())}"
    command = container_arguments(config, name, trial_dir / "workspace", claude_config) + claude_arguments(
        config, prompt
    )
    limit_s = 60 * float(config.agent["wall_clock_limit_minutes"])
    started_at, started = now_utc(), time.monotonic()
    exit_code, timed_out = runner(command, limit_s, name)
    seconds = time.monotonic() - started
    credentials = claude_config / ".credentials.json"
    if credentials.exists():  # only if someone logged in inside the container; never keep it
        credentials.unlink()
    agent = {
        "mode": "manual-session",
        "image": agent_image(config),
        "configured_model": config.agent["model"],
        "configured_effort": config.agent["effort"],
        "started_at": started_at,
        "ended_at": now_utc(),
        "wall_clock_seconds": round(seconds, 1),
        "timed_out": timed_out,
        "exit_code": exit_code,
        **parse_session_logs(session_logs(claude_config)),
        **operator_report(ask),
    }
    validity, reason = classify_session(agent, config)
    update_record(trial_dir, agent=agent, validity=validity, validity_reason=reason)
    return agent


def preflight(
    config: Config, runner: Callable[[list[str], float, str], tuple[int | None, bool]] = run_interactive
) -> None:
    """Open Claude Code with no task and no prompt, to check login, model, and usage by hand."""
    problems = check_environment(config)
    if problems:
        raise AgentError("; ".join(problems))
    with tempfile.TemporaryDirectory(prefix="rc-preflight-") as tmp:
        workspace, claude_config = Path(tmp) / "empty", Path(tmp) / "claude-config"
        workspace.mkdir()
        claude_config.mkdir()
        name = f"rc-preflight-{int(time.time())}"
        runner(container_arguments(config, name, workspace, claude_config) + claude_arguments(config, None), 1800, name)
        shutil.rmtree(claude_config, ignore_errors=True)


def run_fixture(trial_dir: Path, files: dict[str, str]) -> dict[str, Any]:
    """Write trusted fixture files into the workspace in place of an agent session."""
    record = read_json(trial_dir / "trial.json")
    if record.get("data_kind") != "fixture":
        raise AgentError("fixture agents may only be used for trials prepared with data kind 'fixture'")
    workspace = trial_dir / "workspace"
    started = time.monotonic()
    for relative, text in files.items():
        target = workspace / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    agent = {
        "mode": "fixture",
        "configured_model": None,
        "started_at": now_utc(),
        "ended_at": now_utc(),
        "wall_clock_seconds": round(time.monotonic() - started, 3),
        "timed_out": False,
        "exit_code": 0,
        "assistant_messages": None,
        "human_messages": None,
        "output_tokens": None,
        "fixture_files": sorted(files),
    }
    update_record(trial_dir, agent=agent, validity="valid", validity_reason="fixture (not an experimental trial)")
    return agent
