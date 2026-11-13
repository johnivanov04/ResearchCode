"""Protocol 1.1: nothing in the framework can call a model or incur charges by itself.

These are static guarantees about the code, the command line, and CI. They complement
test_schedule_and_agent.py, which checks that only the subscription token is ever passed.
"""

import json
import re
from pathlib import Path

from rc_experiments import cli
from rc_experiments.config import EXPERIMENTS_DIR, REPO_DIR

SOURCE = EXPERIMENTS_DIR / "src" / "rc_experiments"


def test_no_command_runs_claude_non_interactively():
    """`claude -p`/`--print` is the non-interactive mode; the harness never builds such a command."""
    for path in SOURCE.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r'"claude",\s*"-p"', text), path
        assert '"--print"' not in text, path
        assert "--max-budget-usd" not in text, path


def test_the_command_line_has_no_automated_agent_commands():
    commands = set(cli.build_parser()._subparsers._group_actions[0].choices)
    assert {"run-agent", "run-trial"}.isdisjoint(commands)
    assert {"session", "preflight", "next", "progress", "collect", "evaluate"} <= commands


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


def test_configuration_records_zero_additional_spending(config):
    billing = config.raw["billing"]
    assert billing["additional_spending_usd"] == 0
    assert billing["automated_model_calls"] is False
    assert billing["credential"] == "CLAUDE_CODE_OAUTH_TOKEN"
    assert "ANTHROPIC_API_KEY" in billing["forbidden_credentials"]
    assert config.agent["session_mode"] == "manual-interactive"
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
