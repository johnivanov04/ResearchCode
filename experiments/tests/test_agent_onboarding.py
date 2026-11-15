"""The agent image skips Claude Code's first-run login, and `rc-exp check` catches a bad token.

Regression tests for the pre-pilot defect found on 2026-11-14 (protocol 1.4): every new agent
container showed Claude Code's first-run setup (theme, then "Select login method") although
CLAUDE_CODE_OAUTH_TOKEN reached the container. Claude Code 2.1.319 adds the login step to its
first-run setup whenever the setup has not been completed, even when a token is set
(anthropics/claude-code#46259). The agent image therefore marks the setup as complete.

Also covered: a token containing whitespace (from copying a wrapped line) is reported by
`rc-exp check` without its value. These tests use fake placeholder values only, never start
Claude Code, and make no network request.
"""

from __future__ import annotations

import json
import re
import subprocess
import uuid

import pytest

from rc_experiments import agent
from rc_experiments.config import EXPERIMENTS_DIR
from rc_experiments.sandbox import SANDBOX_IMAGE

AGENT_DOCKERFILE = EXPERIMENTS_DIR / "docker" / "agent" / "Dockerfile"
FAKE_TOKEN = "sk-ant-oat01-" + "FAKEPLACEHOLDER" * 6 + "QQQQQ"  # not a credential


def test_agent_image_marks_first_run_setup_complete_and_nothing_else():
    text = AGENT_DOCKERFILE.read_text()
    writes = re.findall(r"^RUN printf '(.*)\\n' > (\S+)$", text, re.MULTILINE)
    assert writes == [(json.dumps(agent.AGENT_GLOBAL_CONFIG_CONTENT), agent.AGENT_GLOBAL_CONFIG)]
    assert agent.AGENT_GLOBAL_CONFIG_CONTENT == {"hasCompletedOnboarding": True}
    # Written as the unprivileged user, after it exists, so Claude Code can update the file.
    assert text.index("USER agent") < text.index("RUN printf")
    # No other Claude Code configuration is baked into the image.
    assert text.count(".claude") == 1
    assert "settings.json" not in text
    assert "CLAUDE.md" not in text


def test_whitespace_in_the_token_is_reported_without_the_value(monkeypatch):
    wrapped = (FAKE_TOKEN[:79] + " " + FAKE_TOKEN[79:], FAKE_TOKEN[:60] + "\n" + FAKE_TOKEN[60:], FAKE_TOKEN + "\n")
    for broken in wrapped:
        monkeypatch.setenv(agent.SUBSCRIPTION_CREDENTIAL, broken)
        problem = agent.credential_problem()
        assert problem is not None
        assert "whitespace" in problem
        assert "FAKEPLACEHOLDER" not in problem
        assert "sk-ant" not in problem


def test_a_clean_token_passes_and_a_missing_one_is_reported(monkeypatch):
    monkeypatch.setenv(agent.SUBSCRIPTION_CREDENTIAL, FAKE_TOKEN)
    assert agent.credential_problem() is None
    monkeypatch.delenv(agent.SUBSCRIPTION_CREDENTIAL)
    assert "not set" in agent.credential_problem()


def test_check_environment_reports_a_broken_token(config, monkeypatch):
    monkeypatch.setattr(agent, "_docker_ok", lambda *args: True)
    monkeypatch.setattr(agent, "agent_image_problem", lambda image: None)
    monkeypatch.setattr(agent, "proxy_allowlist_problem", lambda *args: None)
    monkeypatch.setattr(
        agent.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout="true\n", stderr="")
    )
    monkeypatch.setenv(agent.SUBSCRIPTION_CREDENTIAL, FAKE_TOKEN)
    assert agent.check_environment(config) == []
    monkeypatch.setenv(agent.SUBSCRIPTION_CREDENTIAL, FAKE_TOKEN[:79] + " " + FAKE_TOKEN[79:])
    problems = agent.check_environment(config)
    assert len(problems) == 1
    assert "whitespace" in problems[0]
    assert agent.check_environment(config, need_credential=False) == []


# --------------------------------------------------------------------------------------
# Docker: the image check reads the file from a real image
# --------------------------------------------------------------------------------------


def _build(dockerfile: str, tag: str) -> None:
    subprocess.run(["docker", "build", "-q", "-t", tag, "-"], input=dockerfile, text=True,
                   capture_output=True, check=True, timeout=600)  # fmt: skip


@pytest.mark.docker
def test_an_outdated_agent_image_is_detected(docker_backend):
    """An image without the file (built before protocol 1.4), or with other content, is refused."""
    suffix = uuid.uuid4().hex[:8]
    base = f"FROM {SANDBOX_IMAGE}\nUSER root\nRUN mkdir -p {agent.CONTAINER_HOME}\n"
    write = "RUN printf '{}\\n' > " + agent.AGENT_GLOBAL_CONFIG + "\n"
    images = {
        "seeded": base + write.format(json.dumps(agent.AGENT_GLOBAL_CONFIG_CONTENT)),
        "missing": base,
        "different": base + write.format(json.dumps({"hasCompletedOnboarding": False})),
    }
    tags = {name: f"researchcode-agent-check:test-{name}-{suffix}" for name in images}
    try:
        for name, dockerfile in images.items():
            _build(dockerfile, tags[name])
        assert agent.agent_image_problem(tags["seeded"]) is None
        for name in ("missing", "different"):
            problem = agent.agent_image_problem(tags[name])
            assert problem is not None, name
            assert "rc-exp build-images" in problem
    finally:
        subprocess.run(["docker", "rmi", "-f", *tags.values()], capture_output=True, check=False)
