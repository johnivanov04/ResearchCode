"""Nothing in the framework can incur charges, and only the operator starts sessions.

Protocol 1.1 made trials manual; protocol 1.5 adds unattended batches (`rc-exp batch`). These
are static guarantees about the code, the command line, the configuration, and CI. They
complement test_schedule_and_agent.py and test_batch.py, which check that only the
subscription token is ever passed and that a batch refuses any other credential.
"""

import json
import re
from pathlib import Path

from rc_experiments import cli
from rc_experiments.config import EXPERIMENTS_DIR, REPO_DIR

SOURCE = EXPERIMENTS_DIR / "src" / "rc_experiments"


def test_only_the_batch_runner_builds_a_non_interactive_command():
    """Protocol 1.5: `claude -p` is built in exactly one place, and never with --bare or a budget flag."""
    found = []
    for path in SOURCE.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        found += [path.name] * len(re.findall(r'"claude",\s*"-p"', text))
        assert '"--print"' not in text, path
        assert '"--bare"' not in text, path
        assert "--max-budget-usd" not in text, path
        assert "--dangerously-skip-permissions" not in text, path
    assert found == ["agent.py"]
    source = (SOURCE / "agent.py").read_text(encoding="utf-8")
    builder = source[source.index("def batch_claude_arguments") :]
    assert '"claude", "-p"' in builder[: builder.index("\ndef ")]


def test_the_command_line_has_no_automated_agent_commands():
    commands = set(cli.build_parser()._subparsers._group_actions[0].choices)
    assert {"run-agent", "run-trial"}.isdisjoint(commands)
    assert {"session", "preflight", "batch", "next", "progress", "collect", "evaluate"} <= commands


def test_no_api_credentials_are_read_or_forwarded():
    for path in SOURCE.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert 'os.environ.get("ANTHROPIC_API_KEY")' not in text, path
        assert '"-e", "ANTHROPIC_API_KEY"' not in text, path


def test_ci_never_uses_credentials_or_runs_sessions():
    for workflow in (REPO_DIR / ".github" / "workflows").glob("*.yml"):
        text = workflow.read_text(encoding="utf-8")
        assert "secrets." not in text, workflow.name
        # Billing variables may appear only with dummy values (the credential-isolation check).
        for line in text.splitlines():
            if re.match(r"\s*ANTHROPIC_[A-Z_]+:", line):
                assert "dummy" in line, (workflow.name, line)
        assert "CLAUDE_CODE_OAUTH_TOKEN" not in text, workflow.name
        assert "rc-exp session" not in text, workflow.name
        assert "rc-exp preflight" not in text, workflow.name
        assert "rc-exp batch --" not in text.replace("rc-exp batch --dry-run", ""), workflow.name


def test_configuration_records_zero_additional_spending(config):
    billing = config.raw["billing"]
    assert billing["additional_spending_usd"] == 0
    assert billing["automated_model_calls"] is False  # nothing calls a model unless the operator starts it
    assert billing["api_key_fallback"] is False
    assert billing["credential"] == "CLAUDE_CODE_OAUTH_TOKEN"
    assert "ANTHROPIC_API_KEY" in billing["forbidden_credentials"]
    assert config.agent["session_mode"] == "unattended-noninteractive"
    assert config.agent["noninteractive"]["bare_mode"] is False
    assert config.agent["noninteractive"]["continuation_messages"] == 0
    history = config.agent["session_mode_history"]
    assert history[0]["session_mode"] == "manual-interactive"
    assert history[0]["protocol_versions"] == "1.1-1.4"
    assert "serial-dilution--B--r01" in history[0]["trials"]
    assert "max_budget_usd_per_trial" not in config.agent
    assert "max_budget_usd_per_trial" not in json.dumps(config.raw)


def test_continuation_message_is_shared_and_neutral():
    text = (EXPERIMENTS_DIR / "conditions" / "CONTINUE.md").read_text(encoding="utf-8")
    assert text.startswith("No one is available to answer questions.")
    assert len(text.splitlines()) == 1


def test_agent_dockerfile_does_not_embed_credentials():
    text = (EXPERIMENTS_DIR / "docker" / "agent" / "Dockerfile").read_text(encoding="utf-8")
    assert "ANTHROPIC_API_KEY" not in text
    assert "OAUTH_TOKEN" not in text
    assert Path(EXPERIMENTS_DIR / ".gitignore").read_text().count(".env") >= 1
