"""Run a submission's own pytest suite, optionally with its module replaced, and report per-test outcomes.

This script runs inside the evaluation sandbox and uses only the standard library (pytest
and Hypothesis are installed in the sandbox image for the submission's tests). It is used to
measure the quality of a submission's tests: they are run against the submission's own
code, against the reference solution, and against defective variants. The replacement
source never contains expected values.

Usage: python -I -B suite_runner.py PAYLOAD.json --submission DIR [--timeout S]
PAYLOAD: {"module": name, "replacement_source": str or null}
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

MAX_TEXT = 2_000


def find_module(root: Path, module: str) -> Path | None:
    """Where Python would import ``module`` from, given sys.path = [root/src, root]."""
    for base in (root / "src", root):
        package = base / module
        if package.is_dir():
            return package
        single = base / f"{module}.py"
        if single.is_file():
            return single
    return None


def replace_module(root: Path, module: str, source: str) -> bool:
    location = find_module(root, module)
    if location is None:
        return False
    if location.is_dir():
        shutil.rmtree(location)
        location.mkdir()
        (location / "__init__.py").write_text(source, encoding="utf-8")
    else:
        location.write_text(source, encoding="utf-8")
    return True


def parse_junit(path: Path) -> tuple[dict[str, str], dict[str, str | None]]:
    """Per-test outcomes and source files (the xunit1 report records each test's file)."""
    outcomes: dict[str, str] = {}
    files: dict[str, str | None] = {}
    if not path.is_file():
        return outcomes, files
    tree = ET.parse(path)  # noqa: S314 - file written by pytest in this sandbox, never fetched
    for case in tree.iter("testcase"):
        test_id = f"{case.get('classname', '')}::{case.get('name', '')}"
        tags = {child.tag for child in case}
        if "error" in tags:
            outcome = "error"
        elif "failure" in tags:
            outcome = "failed"
        elif "skipped" in tags:
            outcome = "skipped"
        else:
            outcome = "passed"
        # Parametrised tests can repeat an id only if pytest itself reports duplicates.
        outcomes[test_id] = outcome if test_id not in outcomes else "duplicate"
        files[test_id] = case.get("file")
    return outcomes, files


# ----------------------------------------------------------------------------------------
# Installed-package metadata (identical copy in probe_runner.py and suite_runner.py)
# ----------------------------------------------------------------------------------------


def write_distribution_metadata(root: Path, target: Path) -> Path | None:
    """Emulate an installed project: a .dist-info for the name and version in root/pyproject.toml.

    Projects normally run their code after `uv sync` or `pip install -e .`, which makes
    `importlib.metadata.version(<project>)` work. The sandbox imports code without installing
    it, so this records the declared name and version the same way. Returns the directory to
    put on sys.path, or None if the project declares no static name and version.
    """
    import re
    import tomllib

    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return None
    try:
        project = tomllib.loads(pyproject.read_text(encoding="utf-8")).get("project", {})
    except (tomllib.TOMLDecodeError, UnicodeDecodeError):
        return None
    name, version = project.get("name"), project.get("version")
    if not isinstance(name, str) or not isinstance(version, str):
        return None
    dist = target / f"{re.sub(r'[-_.]+', '_', name)}-{version}.dist-info"
    dist.mkdir(parents=True, exist_ok=True)
    lines = ["Metadata-Version: 2.1", f"Name: {name}", f"Version: {version}"]
    lines += [f"Requires-Dist: {r}" for r in project.get("dependencies", []) if isinstance(r, str)]
    (dist / "METADATA").write_text("\n".join(lines) + "\n", encoding="utf-8")
    modules = set()
    for base in (root / "src", root):
        if base.is_dir():
            modules.update(p.stem for p in base.glob("*.py"))
            modules.update(p.name for p in base.iterdir() if p.is_dir() and (p / "__init__.py").is_file())
    (dist / "top_level.txt").write_text("\n".join(sorted(modules)) + "\n", encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("payload")
    parser.add_argument("--submission", required=True)
    parser.add_argument("--timeout", type=float, default=300.0)
    args = parser.parse_args(argv)
    payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))

    work = Path(tempfile.mkdtemp(prefix="suite-")) / "work"
    shutil.copytree(args.submission, work, symlinks=True)
    report: dict[str, Any] = {"module": payload["module"], "replaced": False}
    if payload.get("replacement_source") is not None:
        if not replace_module(work, payload["module"], payload["replacement_source"]):
            report.update(status="module_not_found", tests={}, files={}, collected=0)
            sys.stdout.write(json.dumps(report))
            return 0
        report["replaced"] = True

    junit = work.parent / "junit.xml"
    metadata = write_distribution_metadata(work, work.parent / "metadata")
    env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),  # noqa: S108 - sandbox path
        "TMPDIR": os.environ.get("TMPDIR", "/tmp"),  # noqa: S108 - sandbox path
        "PYTHONPATH": os.pathsep.join([str(work / "src"), str(work)] + ([str(metadata)] if metadata else [])),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        f"--junitxml={junit}",
        "-o",
        "junit_family=xunit1",
    ]
    started = time.monotonic()
    try:
        completed = subprocess.run(command, cwd=work, env=env, capture_output=True, timeout=args.timeout, check=False)
    except subprocess.TimeoutExpired:
        report.update(status="timeout", tests={}, files={}, collected=0, seconds=round(time.monotonic() - started, 1))
        sys.stdout.write(json.dumps(report))
        return 0
    try:
        tests, files = parse_junit(junit)
    except ET.ParseError:
        tests, files = {}, {}
    output = completed.stdout.decode("utf-8", errors="replace")
    report.update(
        status="ran",
        exit_code=completed.returncode,
        tests=tests,
        files=files,
        collected=len(tests),
        seconds=round(time.monotonic() - started, 1),
        output_tail=output[-MAX_TEXT:],
    )
    sys.stdout.write(json.dumps(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
