"""The Docker sandbox isolates generated code (requires Docker and the sandbox image).

A deliberately hostile fixture tries to use the network, write outside /tmp, read the
host, and escalate; the observations must show every attempt failing.
"""

import pytest

from rc_experiments.cases import call
from rc_experiments.evaluators import load_fixture
from rc_experiments.grading import evaluate_hidden
from rc_experiments.sandbox import LocalBackend, SandboxError

pytestmark = pytest.mark.docker

HOSTILE = """
import os, socket, pathlib

def network():
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=3).close()
        return "connected"
    except OSError as error:
        return "blocked: " + type(error).__name__

def dns():
    try:
        socket.getaddrinfo("pypi.org", 443)
        return "resolved"
    except OSError:
        return "blocked"

def write(path):
    try:
        pathlib.Path(path).write_text("x")
        return "written"
    except OSError as error:
        return "refused: " + type(error).__name__

def identity():
    return [os.getuid(), os.getgid()]

def visible_home():
    return sorted(p.name for p in pathlib.Path("/").iterdir())

def capabilities():
    for line in open("/proc/self/status"):
        if line.startswith("CapEff"):
            return line.split()[1]
    return None

def memory_hog():
    blocks = []
    while True:
        blocks.append(bytearray(100_000_000))
"""


def observe(backend, submission, requests, timeout=10.0):
    cases = [{"id": f"c{i}", **r} for i, r in enumerate(requests)]
    result = backend.run(
        "probe_runner.py", submission, {"module": "hostile", "cases": cases}, ["--timeout", str(timeout)], 600
    )
    assert result.error is None, result.error
    return result.report["observations"]


def test_hostile_code_is_contained(docker_backend, make_submission):
    submission = make_submission({"hostile.py": HOSTILE})
    requests = [
        call("network"),
        call("dns"),
        call("write", "/submission/hostile.py"),
        call("write", "/etc/evil"),
        call("write", "/tmp/allowed.txt"),  # noqa: S108 - a path inside the container
        call("identity"),
        call("capabilities"),
        call("memory_hog"),
    ]
    net, dns, sub, root, tmp, ident, caps, hog = observe(docker_backend, submission, requests, timeout=30)
    assert net["value"].startswith("blocked")
    assert dns["value"] == "blocked"
    assert sub["value"].startswith("refused")
    assert root["value"].startswith("refused")
    assert tmp["value"] == "written"  # the size-limited /tmp is the only writable place
    assert ident["value"] == [65534, 65534]
    assert int(caps["value"], 16) == 0
    assert hog["status"] in {"crashed", "timeout"}
    assert (submission / "hostile.py").read_text() == HOSTILE  # the original was never touched


@pytest.mark.parametrize("task", load_fixture().task_ids)
def test_fixture_references_pass_in_the_sandbox(docker_backend, config, make_submission, task):
    """Public CI uses the FIXTURE evaluator; the genuine references are tested privately."""
    evaluator = load_fixture().task(task)
    submission = make_submission({f"{evaluator.module}.py": evaluator.reference_path.read_text(encoding="utf-8")})
    evaluation = evaluate_hidden(evaluator, submission, docker_backend, config)
    assert evaluation["evaluation_error"] is None
    assert evaluation["runner"]["packages"] == {"numpy": "2.5.4", "scipy": "1.18.1"}
    assert evaluation["summary"]["hidden_pass_rate"] == 1.0


def test_local_backend_refuses_untrusted_use():
    with pytest.raises(SandboxError):
        LocalBackend(trusted=False)
