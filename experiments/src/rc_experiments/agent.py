"""Agent sessions for trials: subscription-based Claude Code sessions, or fixtures.

Protocols 1.1 to 1.4 ran every trial as a **manual, interactive Claude Code session**. From
protocol 1.5, the remaining trials run **unattended and non-interactively** (``claude -p``),
started by the operator with ``rc-exp batch`` (see ``batch.py``). Both modes use the same
container, prompt, model, effort, permission mode, tools, time limit, and subscription token,
and every trial records its execution mode. Nothing here starts a session unless the operator
runs ``rc-exp session``, ``rc-exp preflight``, or ``rc-exp batch``.

* :func:`session` opens Claude Code interactively in the agent container with only the trial
  workspace mounted, the trial's prompt already entered, the configured model and settings,
  and a new, empty Claude configuration directory (so no memory or history carries over
  between trials). After the session it reads the session log and records what happened.
* :func:`preflight` opens the same container with an empty directory and no prompt, so the
  operator can check the login (``/status``), the model (``/model``), and remaining usage
  (``/usage``) without starting a trial.
* :func:`batch_session` runs one trial with ``claude -p`` in the same container, streams Claude
  Code's output through :class:`StreamMonitor`, and stops the container at once on any sign
  of an API key, paid usage, a usage limit, an authentication error, or a configuration
  that differs from the protocol (protocol 1.5).
* :func:`run_fixture` writes trusted fixture code instead of running an agent (dry runs only).

Billing safety: the only credential ever passed into a container is ``CLAUDE_CODE_OAUTH_TOKEN``
(created with ``claude setup-token``, which uses the subscription). API keys, auth tokens,
alternative endpoints, and cloud-provider switches are never passed, even if they are set on
the host. Usage values are copied from Claude Code's own session log; nothing is estimated.
"""

from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any

from rc_experiments.config import Config
from rc_experiments.pipeline import redact_secrets
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


# Claude Code's global configuration in the agent image (docker/agent/Dockerfile). It only marks
# the first-run setup as complete: otherwise Claude Code 2.1.319 shows its login screen in every
# new container even when CLAUDE_CODE_OAUTH_TOKEN is set (anthropics/claude-code#46259).
AGENT_GLOBAL_CONFIG = f"{CONTAINER_HOME}/.claude.json"
AGENT_GLOBAL_CONFIG_CONTENT = {"hasCompletedOnboarding": True}


def agent_image_problem(image: str) -> str | None:
    """None if the agent image marks Claude Code's first-run setup complete, else what is wrong.

    An image built before protocol 1.4 lacks the file and shows the first-run login screen.
    The check starts a container with no network that only reads the file.
    """
    result = subprocess.run(
        ["docker", "run", "--rm", "--network", "none", "--cap-drop", "ALL",
         "--entrypoint", "cat", image, AGENT_GLOBAL_CONFIG],
        capture_output=True, text=True, timeout=120, check=False,
    )  # fmt: skip
    try:
        content = json.loads(result.stdout) if result.returncode == 0 else None
    except json.JSONDecodeError:
        content = None
    if content != AGENT_GLOBAL_CONFIG_CONTENT:
        return (
            f"agent image {image} does not mark Claude Code's first-run setup complete, so it would "
            "ask for a login despite the token; rebuild it with `rc-exp build-images`"
        )
    return None


def credential_problem(environ: Mapping[str, str] = os.environ) -> str | None:
    """None if the subscription token looks usable, else what is wrong. Never includes the value.

    A token copied from a terminal where it wrapped across lines can contain a space or a line
    break. Claude Code still accepts such a value as a token, and the server then rejects it.
    """
    value = environ.get(SUBSCRIPTION_CREDENTIAL, "")
    if not value:
        return f"{SUBSCRIPTION_CREDENTIAL} is not set: create it once with `claude setup-token` (subscription)"
    if any(character.isspace() for character in value):
        return (
            f"{SUBSCRIPTION_CREDENTIAL} contains whitespace (a space or line break, often from copying a "
            "token that wrapped across lines); set it again as one unbroken line (see docs/RUNNING_TRIALS.md)"
        )
    return None


PROXY_ALLOWLIST = Path(__file__).resolve().parents[2] / "docker" / "proxy" / "allowlist"


def proxy_allowlist_problem(container: str = PROXY_CONTAINER) -> str | None:
    """None if the running proxy filters with the repository's allowlist, else what is wrong.

    The allowlist is copied into the proxy image when it is built, so after the file changes an
    old image would keep the old rules until it is rebuilt and restarted.
    """
    result = subprocess.run(
        ["docker", "exec", container, "cat", "/etc/tinyproxy/allowlist"],
        capture_output=True, text=True, timeout=60, check=False,
    )  # fmt: skip
    if result.returncode != 0:
        return f"could not read the allowlist of proxy container {container}"
    if result.stdout.split() != PROXY_ALLOWLIST.read_text().split():
        return (
            f"proxy container {container} uses an outdated allowlist; rebuild and restart it with "
            "`rc-exp build-images`, then `rc-exp network down` and `rc-exp network up`"
        )
    return None


def check_environment(config: Config, *, need_credential: bool = True) -> list[str]:
    """Problems that prevent a session (empty list if ready)."""
    problems = []
    if not _docker_ok("image", "inspect", agent_image(config)):
        problems.append(f"agent image {agent_image(config)} not built (rc-exp build-images)")
    elif problem := agent_image_problem(agent_image(config)):
        problems.append(problem)
    if not _docker_ok("network", "inspect", NETWORK):
        problems.append(f"network {NETWORK} missing (rc-exp network up)")
    result = subprocess.run(
        ["docker", "inspect", "--format", "{{.State.Running}}", PROXY_CONTAINER],
        capture_output=True, text=True, timeout=60, check=False,
    )  # fmt: skip
    if result.stdout.strip() != "true":
        problems.append(f"proxy container {PROXY_CONTAINER} not running (rc-exp network up)")
    elif problem := proxy_allowlist_problem():
        problems.append(problem)
    if need_credential and (problem := credential_problem()):
        problems.append(problem)
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


# --------------------------------------------------------------------------------------
# Unattended, non-interactive sessions (protocol 1.5, `rc-exp batch`)
# --------------------------------------------------------------------------------------

EXECUTION_MODE_INTERACTIVE = "manual-interactive"  # protocols 1.1-1.4: `rc-exp session`
EXECUTION_MODE_BATCH = "unattended-noninteractive"  # protocol 1.5: `rc-exp batch` (`claude -p`)
BATCH_AGENT_MODE = "unattended-batch"  # value of agent["mode"] in a batch trial's record
_MODE_TO_EXECUTION = {"manual-session": EXECUTION_MODE_INTERACTIVE, BATCH_AGENT_MODE: EXECUTION_MODE_BATCH}

# Tokens from `claude setup-token` begin with this prefix (observed format); API keys with the
# second. Anything else is treated as ambiguous, and the batch refuses to start.
SUBSCRIPTION_TOKEN_PREFIX = "sk-ant-oat"  # noqa: S105 - a public prefix, not a secret
API_KEY_PREFIX = "sk-ant-api"
# Host variables that could select another credential, endpoint, or provider. None of them is
# ever passed into a container; for an unattended batch their mere presence is a refusal.
AMBIGUOUS_VARIABLE_PREFIXES = ("ANTHROPIC_", "CLAUDE_CODE_USE_", "CLAUDE_CODE_API_KEY")

# Claude Code's API error kinds (2.1.319) that end a batch at once: the trial cannot continue
# on the subscription, or continuing could mean paid or misconfigured usage.
AUTHENTICATION_ERRORS = frozenset(
    {"authentication_failed", "oauth_org_not_allowed", "account_on_hold", "verification_required",
     "cloud_credential_error"}
)  # fmt: skip
BILLING_ERRORS = frozenset({"billing_error"})
LIMIT_ERRORS = frozenset({"rate_limit"})
CONFIGURATION_ERRORS = frozenset({"model_not_found", "invalid_request"})
# Rate-limit statuses: "rejected" means the plan's usage limit is reached. An overage status of
# "allowed" or "allowed_warning" means paid extra usage is available to this session.
OVERAGE_AVAILABLE = frozenset({"allowed", "allowed_warning"})


def execution_mode(record: Mapping[str, Any]) -> str | None:
    """How a trial's session was run, for records from every protocol version."""
    agent = record.get("agent") or {}
    return agent.get("execution_mode") or _MODE_TO_EXECUTION.get(agent.get("mode"))


def subscription_auth_problems(environ: Mapping[str, str] = os.environ) -> list[str]:
    """Reasons to refuse an unattended batch: only an unambiguous subscription token is accepted.

    Messages name variables, never their values.
    """
    problems = []
    if problem := credential_problem(environ):
        problems.append(problem)
    token = environ.get(SUBSCRIPTION_CREDENTIAL, "")
    if token.startswith(API_KEY_PREFIX):
        problems.append(f"{SUBSCRIPTION_CREDENTIAL} holds an API key, not a subscription token; refusing")
    elif token and not token.startswith(SUBSCRIPTION_TOKEN_PREFIX):
        problems.append(
            f"{SUBSCRIPTION_CREDENTIAL} does not look like a token from `claude setup-token`; refusing "
            "because the authentication method would be ambiguous"
        )
    ambiguous = sorted(
        name for name, value in environ.items() if value and name.startswith(AMBIGUOUS_VARIABLE_PREFIXES)
    )
    if ambiguous:
        problems.append(
            f"{', '.join(ambiguous)} set on this machine; unset {'it' if len(ambiguous) == 1 else 'them'} "
            "before an unattended batch (only the subscription token may be present)"
        )
    return problems


def batch_claude_arguments(config: Config, prompt: str) -> list[str]:
    """Non-interactive Claude Code (`-p`, never `--bare`) with the same settings as a manual session."""
    interactive = claude_arguments(config, prompt)
    if interactive[:2] != ["claude", prompt]:
        raise AgentError("unexpected interactive command layout")
    return ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose", *interactive[2:]]


def batch_container_arguments(config: Config, name: str, workspace: Path, claude_config: Path) -> list[str]:
    """The manual session's container, without a terminal: same image, limits, network, and token."""
    return [arg for arg in container_arguments(config, name, workspace, claude_config) if arg != "-it"]


class StreamMonitor:
    """Reads Claude Code's stream-json output line by line and decides when to stop at once.

    ``feed`` returns a reason to stop the container immediately, or None. It keeps a summary
    of what Claude Code reported; values are copied, never estimated. ``total_cost_usd`` is not
    kept: under a subscription it is Claude Code's notional estimate, not a charge.
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self.init: dict[str, Any] | None = None
        self.result: dict[str, Any] | None = None
        self.events: dict[str, int] = {}
        self.unparsed_lines = 0
        self.api_retries: list[dict[str, Any]] = []
        self.api_errors: list[str] = []
        self.rate_limits: list[dict[str, Any]] = []
        self.stop_category: str | None = None
        self.stop_reason: str | None = None

    def _stop(self, category: str, reason: str) -> str:
        if self.stop_reason is None:
            self.stop_category, self.stop_reason = category, reason
        return reason

    def _error_kind(self, kind: Any, where: str) -> str | None:
        kind = str(kind)
        if kind in AUTHENTICATION_ERRORS:
            return self._stop("authentication", f"authentication error ({kind}) {where}")
        if kind in BILLING_ERRORS:
            return self._stop("billing", f"billing error ({kind}) {where}")
        if kind in LIMIT_ERRORS:
            return self._stop("usage_limit", f"rate or usage limit ({kind}) {where}")
        if kind in CONFIGURATION_ERRORS:
            return self._stop("configuration", f"request rejected ({kind}) {where}")
        return None

    def _check_init(self, event: dict[str, Any]) -> str | None:
        agent = self.config.agent
        tools = event.get("tools") or []
        self.init = {
            "apiKeySource": event.get("apiKeySource"),
            "model": event.get("model"),
            "permissionMode": event.get("permissionMode"),
            "claude_code_version": event.get("claude_code_version"),
            "tools": len(tools),
        }
        if event.get("apiKeySource") != "none":
            return self._stop(
                "authentication",
                f"Claude Code reports an API key source ({event.get('apiKeySource')!r}); only the subscription "
                "token is allowed",
            )
        if event.get("model") != agent["model"]:
            return self._stop("configuration", f"model {event.get('model')!r} is not {agent['model']!r}")
        if event.get("permissionMode") != agent["permission_mode"]:
            return self._stop("configuration", f"permission mode {event.get('permissionMode')!r} is not configured")
        if event.get("claude_code_version") != agent["tool_version"]:
            return self._stop("configuration", f"Claude Code {event.get('claude_code_version')!r} is not configured")
        leaked = sorted(set(tools) & set(agent["disallowed_tools"]))
        if leaked:
            return self._stop("configuration", f"disallowed tools are available: {', '.join(leaked)}")
        return None

    def feed(self, line: str) -> str | None:
        text = line.strip()
        if not text:
            return None
        if "extra usage" in text.lower():
            self.events["extra_usage_mention"] = self.events.get("extra_usage_mention", 0) + 1
            return self._stop("extra_usage", "Claude Code mentioned extra usage (paid usage beyond the plan)")
        try:
            event = json.loads(text)
        except json.JSONDecodeError:
            self.unparsed_lines += 1
            return None
        if not isinstance(event, dict):
            self.unparsed_lines += 1
            return None
        kind = f"{event.get('type')}/{event.get('subtype')}" if event.get("subtype") else str(event.get("type"))
        self.events[kind] = self.events.get(kind, 0) + 1
        if event.get("type") == "system" and event.get("subtype") == "init":
            return self._check_init(event)
        if event.get("type") == "system" and event.get("subtype") == "api_retry":
            self.api_retries.append({k: event.get(k) for k in ("attempt", "error_status", "error")})
            return self._error_kind(event.get("error"), "while retrying a request")
        if event.get("type") == "rate_limit_event":
            info = event.get("rate_limit_info") or {}
            self.rate_limits.append(
                {k: info.get(k) for k in ("status", "rateLimitType", "overageStatus", "isUsingOverage", "resetsAt")}
            )
            if info.get("isUsingOverage"):
                return self._stop("extra_usage", "the session is using paid overage (extra usage)")
            if info.get("overageStatus") in OVERAGE_AVAILABLE:
                return self._stop(
                    "extra_usage",
                    f"paid overage is available to this session (overage status {info.get('overageStatus')!r}); "
                    "turn off extra usage in the Claude account",
                )
            if info.get("status") == "rejected":
                return self._stop("usage_limit", "the subscription's usage limit was reached")
            return None
        if event.get("type") == "assistant" and (event.get("error") or event.get("is_api_error_message")):
            blocks = (event.get("message") or {}).get("content") or []
            message = " ".join(str(b.get("text", "")) for b in blocks if isinstance(b, dict))
            self.api_errors.append(f"{event.get('error')}: {message}"[:200])
            return self._error_kind(event.get("error"), "in Claude Code's reply")
        if event.get("type") == "result":
            self.result = {
                k: event.get(k)
                for k in ("subtype", "is_error", "terminal_reason", "num_turns", "duration_ms", "api_error_status")
            }
        return None

    @property
    def completed(self) -> bool:
        """Claude Code's own definition of a finished turn: a result without error that completed."""
        return bool(
            self.result is not None
            and self.result.get("is_error") is False
            and self.result.get("terminal_reason") == "completed"
        )

    def summary(self) -> dict[str, Any]:
        return {
            "init": self.init,
            "result": self.result,
            "event_counts": dict(sorted(self.events.items())),
            "unparsed_lines": self.unparsed_lines,
            "api_retries": self.api_retries,
            "api_errors": self.api_errors,
            "rate_limits": self.rate_limits,
            "stop_category": self.stop_category,
            "stop_reason": self.stop_reason,
        }


KILL_GRACE_SECONDS = 120


@dataclass
class RunOutcome:
    exit_code: int | None
    timed_out: bool
    aborted: str | None  # the StreamMonitor's reason, if the container was stopped early


def stop_container(name: str, process: subprocess.Popen[str], *, immediately: bool) -> None:
    """Stop a trial container: at once (`docker kill`) on a safety stop, or gracefully at the time limit."""
    command = ["docker", "kill", name] if immediately else ["docker", "stop", "--time", "5", name]
    subprocess.run(command, capture_output=True, timeout=60, check=False)


def _pump_lines(stream: IO[str], lines: queue.Queue[str | None]) -> None:
    for line in stream:
        lines.put(line)
    lines.put(None)


def run_noninteractive(
    command: list[str],
    limit_s: float,
    name: str,
    stream_path: Path,
    stderr_path: Path,
    monitor: StreamMonitor,
    *,
    stop: Callable[..., None] = stop_container,
    clock: Callable[[], float] = time.monotonic,
) -> RunOutcome:
    """Run a non-interactive container, saving its output (redacted) and enforcing every stop rule.

    A safety stop kills the container at once; the time limit stops it gracefully. If it is
    still running ``KILL_GRACE_SECONDS`` after either, it is killed again, with its client.
    """
    deadline = clock() + limit_s
    timed_out, aborted = False, None
    stop_requested: float | None = None
    with stderr_path.open("w", encoding="utf-8") as stderr, stream_path.open("w", encoding="utf-8") as out:
        process = subprocess.Popen(
            command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=stderr, text=True,
            encoding="utf-8", errors="replace",
        )  # fmt: skip
        if process.stdout is None:
            raise AgentError("the container's output could not be read")
        lines: queue.Queue[str | None] = queue.Queue()
        reader = threading.Thread(target=_pump_lines, args=(process.stdout, lines), daemon=True)
        reader.start()
        try:
            while True:
                try:
                    line = lines.get(timeout=0.5)
                except queue.Empty:
                    line = ""
                if line is None:
                    break
                if line:
                    out.write(redact_secrets(line if line.endswith("\n") else line + "\n"))
                    out.flush()
                    reason = monitor.feed(line)
                    if reason and aborted is None:
                        aborted, stop_requested = reason, clock()
                        stop(name, process, immediately=True)
                if not timed_out and aborted is None and clock() > deadline:
                    timed_out, stop_requested = True, clock()
                    stop(name, process, immediately=False)
                elif stop_requested is not None and clock() > stop_requested + KILL_GRACE_SECONDS:
                    if process.poll() is None:
                        stop(name, process, immediately=True)
                        process.kill()
                    stop_requested = None
            exit_code = process.wait(timeout=120)
        except BaseException:
            stop(name, process, immediately=True)
            process.kill()
            process.wait(timeout=30)
            raise
        finally:
            reader.join(timeout=10)
            process.stdout.close()
    stderr_path.write_text(redact_secrets(stderr_path.read_text(encoding="utf-8", errors="replace")))
    return RunOutcome(exit_code=exit_code, timed_out=timed_out, aborted=aborted)


def classify_batch_session(agent: dict[str, Any], config: Config) -> tuple[str, str]:
    """Protocol section 10 applied to an unattended session (version 1.5).

    A safety stop is an infrastructure or configuration failure (invalid). An unclear ending
    needs a human decision (needs_review). Otherwise the manual-session rules apply unchanged.
    """
    category, reason = agent.get("stop_category"), agent.get("stop_reason")
    if category in ("extra_usage", "usage_limit", "authentication", "billing", "configuration"):
        return "invalid", f"stopped by the batch runner: {reason}"
    validity, why = classify_session(agent, config)
    if validity != "valid":
        return validity, why
    if agent.get("timed_out"):
        return validity, why  # reaching the wall-clock limit is a valid outcome (section 10)
    if agent.get("completion") != "completed":
        return "needs_review", f"the session's end is uncertain ({agent.get('completion_detail')})"
    return "valid", "session completed (unattended, non-interactive)"


def batch_session(
    trial_dir: Path,
    config: Config,
    *,
    batch_id: str,
    runner: Callable[..., RunOutcome] = run_noninteractive,
    environ: Mapping[str, str] = os.environ,
) -> dict[str, Any]:
    """Run one prepared trial unattended (`claude -p`) and record what happened (protocol 1.5).

    The record is marked as started before the container starts, so an interrupted batch is
    never mistaken for a trial that has not run. The trial is never started twice.
    """
    if problems := subscription_auth_problems(environ):
        raise AgentError("; ".join(problems))
    record = read_json(trial_dir / "trial.json")
    if record.get("agent") or record.get("batch"):
        raise AgentError(f"{record['trial_id']} has already been started; it is never run twice")
    claude_config = trial_dir / "claude-config"
    if claude_config.exists():
        raise AgentError(f"{record['trial_id']} has a Claude configuration from an earlier start; not rerun")
    prompt = (trial_dir / "prompt.txt").read_text(encoding="utf-8")
    name = f"rc-batch-{record['trial_id'].replace('--', '-')}-{int(time.time())}"
    started_at, started = now_utc(), time.monotonic()
    update_record(trial_dir, batch={"batch_id": batch_id, "container": name, "started_at": started_at})
    claude_config.mkdir()
    command = batch_container_arguments(config, name, trial_dir / "workspace", claude_config)
    command += batch_claude_arguments(config, prompt)
    monitor = StreamMonitor(config)
    limit_s = 60 * float(config.agent["wall_clock_limit_minutes"])
    outcome = runner(command, limit_s, name, trial_dir / "agent-stream.jsonl", trial_dir / "agent-stderr.txt", monitor)
    seconds = time.monotonic() - started
    credentials = claude_config / ".credentials.json"
    if credentials.exists():  # never created by a token session; never kept
        credentials.unlink()
    if outcome.aborted:
        completion, detail = "stopped", outcome.aborted
    elif outcome.timed_out:
        completion, detail = "timed_out", f"stopped at the {config.agent['wall_clock_limit_minutes']}-minute limit"
    elif monitor.completed and outcome.exit_code == 0 and not monitor.unparsed_lines:
        completion, detail = "completed", "Claude Code reported a completed turn without error"
    else:
        completion = "uncertain"
        detail = (
            f"exit code {outcome.exit_code}; result {monitor.result}; {monitor.unparsed_lines} unparsed output lines"
        )
    agent = {
        "mode": BATCH_AGENT_MODE,
        "execution_mode": EXECUTION_MODE_BATCH,
        "batch_id": batch_id,
        "image": agent_image(config),
        "configured_model": config.agent["model"],
        "configured_effort": config.agent["effort"],
        "started_at": started_at,
        "ended_at": now_utc(),
        "wall_clock_seconds": round(seconds, 1),
        "timed_out": outcome.timed_out,
        "exit_code": outcome.exit_code,
        "completion": completion,
        "completion_detail": detail,
        "stop_category": monitor.stop_category,
        "stop_reason": monitor.stop_reason,
        "stream": monitor.summary(),
        **parse_session_logs(session_logs(claude_config)),
        # No operator takes part: no continuation message and no other input (protocol 1.5).
        "continuation_messages": 0,
        "operator_other_input": False,
        "operator_reported_usage_limit": None,
        "operator_reported_extra_usage": None,
        "operator_notes": "",
    }
    validity, reason = classify_batch_session(agent, config)
    update_record(trial_dir, agent=agent, validity=validity, validity_reason=reason)
    return agent


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
