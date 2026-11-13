"""Run code from a submission in isolation and collect the runner's JSON report.

Two backends:

* :class:`DockerBackend` is required for generated (untrusted) code. Each run uses a new
  container with no network, a read-only file system, a non-root user, all Linux
  capabilities dropped, ``no-new-privileges``, and CPU, memory, process, and time limits.
  The submission is mounted read-only; the only writable place is a size-limited ``/tmp``.
  Nothing written in the container survives it.
* :class:`LocalBackend` runs on the host with only a time limit. It exists for *trusted*
  code (reference solutions, defective variants, and test fixtures written by the
  experimenters) and refuses to run unless the caller says the code is trusted.

Both backends copy the submission into a fresh temporary directory first, so a run can
never modify the collected submission.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from rc_experiments.config import Config

SCRIPTS_DIR = Path(__file__).resolve().parent / "sandbox_scripts"
MAX_REPORT_BYTES = 50_000_000
SANDBOX_IMAGE = "researchcode-eval-sandbox:1"


class SandboxError(RuntimeError):
    """The sandbox itself failed (not the submission)."""


@dataclass(frozen=True)
class RunResult:
    report: dict[str, Any] | None
    error: str | None
    backend: str
    image_id: str | None = None


class Backend(Protocol):
    name: str

    def run(
        self, script: str, submission: Path, payload: Mapping[str, Any], args: list[str], timeout: float
    ) -> RunResult:
        """Run ``sandbox_scripts/<script>`` on a copy of ``submission`` with ``payload`` as JSON input."""
        ...


def _parse_report(stdout: bytes) -> dict[str, Any]:
    if len(stdout) > MAX_REPORT_BYTES:
        raise SandboxError("report too large")
    text = stdout.decode("utf-8", errors="replace").strip()
    if not text:
        raise SandboxError("the runner produced no report")
    report = json.loads(text.splitlines()[-1])
    if not isinstance(report, dict):
        raise SandboxError("malformed report")
    return report


def copy_submission(source: Path, destination: Path) -> None:
    """Copy regular files and directories only; symbolic links are skipped, never followed."""
    destination.mkdir(parents=True, exist_ok=True)
    for item in sorted(source.iterdir()):
        if item.is_symlink():
            continue
        target = destination / item.name
        if item.is_dir():
            copy_submission(item, target)
        elif item.is_file():
            shutil.copyfile(item, target)


class LocalBackend:
    """Host execution for trusted code only (no isolation beyond a time limit)."""

    name = "local-trusted"

    def __init__(self, *, trusted: bool) -> None:
        if not trusted:
            raise SandboxError(
                "the local backend runs code on the host without isolation; use it only for "
                "trusted reference, mutant, or fixture code (trusted=True). Use DockerBackend "
                "for generated submissions."
            )

    def run(
        self, script: str, submission: Path, payload: Mapping[str, Any], args: list[str], timeout: float
    ) -> RunResult:
        with tempfile.TemporaryDirectory(prefix="rc-local-") as tmp:
            root = Path(tmp)
            copy_submission(submission, root / "submission")
            (root / "payload.json").write_text(json.dumps(payload, allow_nan=True), encoding="utf-8")
            command = [
                sys.executable,
                "-I",
                "-B",
                str(SCRIPTS_DIR / script),
                str(root / "payload.json"),
                "--submission",
                str(root / "submission"),
                *args,
            ]
            try:
                completed = subprocess.run(command, cwd=root, capture_output=True, timeout=timeout, check=False)
            except subprocess.TimeoutExpired:
                return RunResult(None, f"timed out after {timeout} s", self.name)
            try:
                return RunResult(_parse_report(completed.stdout), None, self.name)
            except (SandboxError, json.JSONDecodeError) as error:
                stderr = completed.stderr.decode("utf-8", errors="replace")[-2000:]
                return RunResult(None, f"{error}; stderr: {stderr}", self.name)


def docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        result = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def image_id(image: str) -> str | None:
    result = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{.Id}}", image],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    return result.stdout.strip() or None if result.returncode == 0 else None


class DockerBackend:
    """One new, locked-down container per run."""

    name = "docker"

    def __init__(self, config: Config, image: str = SANDBOX_IMAGE) -> None:
        if not docker_available():
            raise SandboxError("Docker is not available; it is required to evaluate generated code")
        self.image = image
        self.image_id = image_id(image)
        if self.image_id is None:
            raise SandboxError(f"sandbox image {image!r} not found; build it with `rc-exp build-images`")
        self.limits = config.evaluation["sandbox"]

    def command(self, name: str, root: Path, script: str, args: list[str]) -> list[str]:
        limits = self.limits
        return [
            "docker",
            "run",
            "--rm",
            "--name",
            name,
            "--network",
            "none",
            "--read-only",
            "--tmpfs",
            f"/tmp:rw,noexec,nosuid,nodev,size={limits['tmpfs_size']}",  # noqa: S108 - container path
            "--memory",
            limits["memory"],
            "--memory-swap",
            limits["memory"],
            "--cpus",
            str(limits["cpus"]),
            "--pids-limit",
            str(limits["pids_limit"]),
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--user",
            "65534:65534",
            "-e",
            "HOME=/tmp",
            "-e",
            "TMPDIR=/tmp",
            "-e",
            "PYTHONDONTWRITEBYTECODE=1",
            "-v",
            f"{root / 'submission'}:/submission:ro",
            "-v",
            f"{SCRIPTS_DIR}:/runner:ro",
            "-v",
            f"{root / 'payload.json'}:/input/payload.json:ro",
            self.image,
            "python",
            "-I",
            "-B",
            f"/runner/{script}",
            "/input/payload.json",
            "--submission",
            "/submission",
            *args,
        ]

    def run(
        self, script: str, submission: Path, payload: Mapping[str, Any], args: list[str], timeout: float
    ) -> RunResult:
        name = f"rc-eval-{uuid.uuid4().hex[:12]}"
        with tempfile.TemporaryDirectory(prefix="rc-docker-") as tmp:
            root = Path(tmp)
            copy_submission(submission, root / "submission")
            (root / "payload.json").write_text(json.dumps(payload, allow_nan=True), encoding="utf-8")
            command = self.command(name, root, script, args)
            try:
                completed = subprocess.run(command, capture_output=True, timeout=timeout, check=False)
            except subprocess.TimeoutExpired:
                subprocess.run(["docker", "kill", name], capture_output=True, timeout=60, check=False)
                return RunResult(None, f"container timed out after {timeout} s", self.name, self.image_id)
            try:
                return RunResult(_parse_report(completed.stdout), None, self.name, self.image_id)
            except (SandboxError, json.JSONDecodeError) as error:
                stderr = completed.stderr.decode("utf-8", errors="replace")[-2000:]
                return RunResult(
                    None, f"{error}; exit {completed.returncode}; stderr: {stderr}", self.name, self.image_id
                )
