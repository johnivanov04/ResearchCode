"""The agent network's filtering proxy allows exactly the hosts the protocol lists.

Regression tests for the pre-pilot defect found on 2026-11-14: interactive Claude Code checks
``platform.claude.com`` (OAuth token exchange and refresh for claude.ai accounts) at startup, and
the proxy refused it. The Docker tests build the proxy image from the repository's files under a
test tag, so they always check the current allowlist, never a stale local image. They start a
throwaway proxy and internal network (unique names; the operator's own proxy is untouched) and
probe hosts from a client container behind it. No credentials are used and no model request is
made: a probe is a plain HTTPS request, and an HTTP status from the server only shows the tunnel
was allowed.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import uuid

import pytest

from rc_experiments import agent
from rc_experiments.config import EXPERIMENTS_DIR
from rc_experiments.sandbox import SANDBOX_IMAGE

PROXY_DIR = EXPERIMENTS_DIR / "docker" / "proxy"
ALLOWLIST = PROXY_DIR / "allowlist"

# Hosts that must remain unreachable from a trial: the repository and its raw files (where the
# public harness lives), GitHub's API and archives, browser sign-in pages the token workflow does
# not use, optional Claude Code services, package registries other than PyPI, and arbitrary sites.
MUST_BE_BLOCKED = (
    "github.com",
    "api.github.com",
    "codeload.github.com",
    "raw.githubusercontent.com",
    "objects.githubusercontent.com",
    "claude.ai",
    "claude.com",
    "code.claude.com",
    "mcp-proxy.anthropic.com",
    "downloads.claude.ai",
    "registry.npmjs.org",
    "www.google.com",
    "example.com",
    # Look-alikes: the filter must match whole host names only.
    "platform.claude.com.example.com",
    "evilplatform.claude.com",
    "api.anthropic.com.example.com",
)
MUST_BE_REACHABLE = ("api.anthropic.com", "platform.claude.com", "pypi.org", "files.pythonhosted.org")

PROBE = r"""
import json, sys, urllib.error, urllib.request
proxy = sys.argv[1]
results = {}
for host in sys.argv[2:]:
    handler = urllib.request.ProxyHandler({"https": proxy} if proxy != "none" else {})
    opener = urllib.request.build_opener(handler)
    try:
        opener.open(f"https://{host}/", timeout=20)
        results[host] = "reached"
    except urllib.error.HTTPError:
        results[host] = "reached"  # the server answered: the tunnel was allowed
    except Exception as error:  # proxy refusal, DNS failure, or no route
        results[host] = "blocked: " + str(getattr(error, "reason", error))[:120]
print(json.dumps(results))
"""


def allowlist_hosts() -> list[str]:
    hosts = []
    for line in ALLOWLIST.read_text().split():
        match = re.fullmatch(r"\^((?:[a-z0-9-]+\\\.)+[a-z]+)\$", line)
        assert match, f"allowlist entry {line!r} is not an anchored, exact host name"
        hosts.append(match.group(1).replace("\\.", "."))
    return hosts


def test_allowlist_is_exactly_the_configured_hosts(config):
    assert allowlist_hosts() == config.agent["network_allowlist"]
    assert set(MUST_BE_REACHABLE) == set(allowlist_hosts())
    for host in MUST_BE_BLOCKED:
        assert host not in allowlist_hosts()


def test_proxy_only_tunnels_https():
    conf = (PROXY_DIR / "tinyproxy.conf").read_text()
    assert "FilterDefaultDeny Yes" in conf
    assert "FilterURLs Off" in conf
    assert re.findall(r"^ConnectPort (\d+)$", conf, re.MULTILINE) == ["443"]


# --------------------------------------------------------------------------------------
# Docker integration: a real proxy built from the repository's files
# --------------------------------------------------------------------------------------


def _docker(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=600, check=check)


@pytest.fixture(scope="module")
def test_proxy(docker_backend):
    """A proxy built from docker/proxy (current files) on a fresh internal network."""
    digest = hashlib.sha256(b"".join(p.read_bytes() for p in sorted(PROXY_DIR.iterdir()) if p.is_file())).hexdigest()[
        :12
    ]
    image = f"researchcode-proxy:test-{digest}"
    if _docker("image", "inspect", image, check=False).returncode != 0:
        _docker("build", "-q", "-t", image, str(PROXY_DIR))
    suffix = uuid.uuid4().hex[:8]
    network, proxy = f"rc-test-net-{suffix}", f"rc-test-proxy-{suffix}"
    _docker("network", "create", "--internal", network)
    try:
        _docker("run", "-d", "--name", proxy, "--network", "bridge", image)
        _docker("network", "connect", network, proxy)
        yield {"network": network, "proxy": proxy, "url": f"http://{proxy}:8888"}
    finally:
        _docker("rm", "-f", proxy, check=False)
        _docker("network", "rm", network, check=False)


def probe(test_proxy, hosts, via_proxy=True) -> dict[str, str]:
    completed = _docker(
        "run", "--rm", "--network", test_proxy["network"], "--cap-drop", "ALL",
        SANDBOX_IMAGE, "python", "-c", PROBE, test_proxy["url"] if via_proxy else "none", *hosts,
    )  # fmt: skip
    return json.loads(completed.stdout.strip().splitlines()[-1])


@pytest.mark.docker
def test_authentication_and_model_hosts_are_reachable_through_the_proxy(test_proxy):
    results = probe(test_proxy, MUST_BE_REACHABLE)
    assert results == dict.fromkeys(MUST_BE_REACHABLE, "reached")


@pytest.mark.docker
def test_github_and_unapproved_hosts_are_refused_by_the_proxy(test_proxy):
    results = probe(test_proxy, MUST_BE_BLOCKED)
    for host, outcome in results.items():
        assert outcome.startswith("blocked"), (host, outcome)
        assert "403" in outcome, (host, outcome)  # refused by the proxy's filter, not by chance


@pytest.mark.docker
def test_there_is_no_route_around_the_proxy(test_proxy):
    results = probe(test_proxy, ("platform.claude.com", "github.com", "pypi.org"), via_proxy=False)
    assert all(outcome.startswith("blocked") for outcome in results.values()), results


@pytest.mark.docker
def test_a_stale_proxy_is_detected(test_proxy):
    """`rc-exp check` compares the running proxy's allowlist with the repository's file."""
    assert agent.proxy_allowlist_problem(test_proxy["proxy"]) is None
    _docker("exec", "-u", "0", test_proxy["proxy"], "sh", "-c",
            "sed -i '/platform/d' /etc/tinyproxy/allowlist")  # fmt: skip
    try:
        problem = agent.proxy_allowlist_problem(test_proxy["proxy"])
        assert problem is not None
        assert "rc-exp build-images" in problem
    finally:
        _docker("cp", str(ALLOWLIST), f"{test_proxy['proxy']}:/etc/tinyproxy/allowlist")
