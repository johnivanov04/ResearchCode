"""Run hidden-case *inputs* against a submission and report what happened, as JSON.

This script runs inside the evaluation sandbox. It uses only the standard library (NumPy
is used if installed, to rebuild array inputs and to serialise NumPy results). It never
receives expected values: it only observes return values, exceptions, and files. The
host grades the observations (``rc_experiments.checks``).

Each case runs in its own child process with a time limit, in a fresh working directory,
so one crashing or hanging case cannot affect the others. The parent process never
imports the submission.

Usage (parent):  python -I -B probe_runner.py REQUEST.json --submission DIR [--timeout S]
Usage (child):   python -I -B probe_runner.py --child CASE.json RESULT.json --submission DIR
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import dataclasses
import importlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

RUNNER_VERSION = 1
MAX_RESULT_BYTES = 1_000_000
MAX_TEXT = 2_000
MAX_FILE_BYTES = 1_000_000

try:  # NumPy is optional for the runner itself.
    import numpy as _np
except ImportError:  # pragma: no cover - the sandbox image has NumPy
    _np = None


# ----------------------------------------------------------------------------------------
# Converting values in and out
# ----------------------------------------------------------------------------------------


def decode(value: Any) -> Any:
    """Turn tagged JSON values (tuples, arrays) into Python objects."""
    if isinstance(value, dict):
        if "__tuple__" in value:
            return tuple(decode(v) for v in value["__tuple__"])
        if "__ndarray__" in value:
            if _np is None:
                raise RuntimeError("NumPy is required for array inputs")
            return _np.array(value["__ndarray__"], dtype=float)
        return {k: decode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [decode(v) for v in value]
    return value


def snapshot(value: Any) -> Any:
    """A comparable copy of an argument, to detect whether the submission modified it."""
    if _np is not None and isinstance(value, _np.ndarray):
        return ("ndarray", value.tolist())
    if isinstance(value, dict):
        return ("dict", sorted((repr(k), snapshot(v)) for k, v in value.items()))
    if isinstance(value, list | tuple):
        return (type(value).__name__, [snapshot(v) for v in value])
    return ("value", repr(value))


def to_plain(obj: Any, depth: int = 0) -> Any:
    """Convert a result into JSON-compatible values without trusting its own methods much."""
    if depth > 20:
        return {"__repr__": "<too deep>"}
    if obj is None or isinstance(obj, bool | str):
        return obj
    if isinstance(obj, int):
        return int(obj)
    if isinstance(obj, float):
        return float(obj)
    if _np is not None:
        if isinstance(obj, _np.bool_):
            return bool(obj)
        if isinstance(obj, _np.integer):
            return int(obj)
        if isinstance(obj, _np.floating):
            return float(obj)
        if isinstance(obj, _np.ndarray):
            return to_plain(obj.tolist(), depth + 1)
    if isinstance(obj, Mapping):
        return {str(k): to_plain(v, depth + 1) for k, v in list(obj.items())[:1000]}
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: to_plain(getattr(obj, f.name), depth + 1) for f in dataclasses.fields(obj)}
    if isinstance(obj, list | tuple):
        return [to_plain(v, depth + 1) for v in obj[:100_000]]
    return {"__repr__": repr(obj)[:200], "__type__": type(obj).__name__}


def extract(obj: Any, fields: list[str] | None) -> Any:
    """Report the named fields of a mapping or object, or the whole value."""
    if fields is None:
        return to_plain(obj)
    result: dict[str, Any] = {}
    for name in fields:
        if isinstance(obj, Mapping) and name in obj:
            result[name] = to_plain(obj[name])
        elif not isinstance(obj, Mapping) and hasattr(obj, name):
            result[name] = to_plain(getattr(obj, name))
        else:
            result[name] = {"__missing__": True}
    return result


def exception_info(error: BaseException) -> dict[str, Any]:
    return {
        "types": [cls.__name__ for cls in type(error).__mro__],
        "message": str(error)[:MAX_TEXT],
    }


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


# ----------------------------------------------------------------------------------------
# Child: run one case
# ----------------------------------------------------------------------------------------


def run_call(module: Any, case: dict[str, Any]) -> dict[str, Any]:
    function = getattr(module, case["function"], None)
    if not callable(function):
        return {"status": "error", "detail": f"the module has no function {case['function']!r}"}
    pristine_args = decode(case["args"])
    pristine_kwargs = decode(case["kwargs"])
    before = snapshot((pristine_args, pristine_kwargs))
    values = []
    mutated = False
    for _ in range(max(1, int(case.get("repeat", 1)))):
        args = copy.deepcopy(pristine_args)
        kwargs = copy.deepcopy(pristine_kwargs)
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                result = function(*args, **kwargs)
            except Exception as error:
                return {"status": "raised", "exception": exception_info(error)}
        mutated = mutated or snapshot((args, kwargs)) != before
        values.append(extract(result, case.get("fields")))
    return {"status": "returned", "value": values[0], "values": values, "inputs_mutated": mutated}


def read_text(path: Path) -> str | None:
    if not path.is_file():
        return None
    data = path.read_bytes()[:MAX_FILE_BYTES]
    return data.decode("utf-8", errors="replace")


def run_cli_once(module: Any, case: dict[str, Any], argv_template: list[str]) -> dict[str, Any]:
    function = getattr(module, case["function"], None)
    if not callable(function):
        return {"status": "error", "detail": f"the module has no function {case['function']!r}"}
    workdir = Path(tempfile.mkdtemp(prefix="cli-", dir=Path.cwd()))
    for name, text in case.get("files", {}).items():
        (workdir / name).write_bytes(text.encode("utf-8"))
    before = {name: (workdir / name).read_bytes() for name in case["report"] if (workdir / name).is_file()}
    argv = [part.replace("{dir}", str(workdir)) for part in argv_template]
    stderr = io.StringIO()
    observation: dict[str, Any]
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
        try:
            code = function(argv)
            observation = {"status": "returned", "exit_code": code}
        except SystemExit as exit_:
            code = exit_.code
            if code is None:
                code = 0
            elif not isinstance(code, int):
                code = 1  # sys.exit("message") exits with status 1
            observation = {"status": "returned", "exit_code": code}
        except Exception as error:
            observation = {"status": "raised", "exception": exception_info(error)}
    if observation.get("status") == "returned" and not isinstance(observation["exit_code"], int | None):
        observation["exit_code"] = repr(observation["exit_code"])[:100]
    observation["stderr"] = stderr.getvalue()[:MAX_TEXT]
    observation["files_after"] = {name: read_text(workdir / name) for name in case["report"]}
    observation["unchanged"] = {
        name: (workdir / name).is_file() and (workdir / name).read_bytes() == data for name, data in before.items()
    }
    return observation


def run_cli(module: Any, case: dict[str, Any]) -> dict[str, Any]:
    if int(case.get("runs", 1)) == 1:
        return run_cli_once(module, case, case["argv"])
    first = run_cli_once(module, case, case["argv"])
    second = run_cli_once(module, case, case["argv_second"] or case["argv"])
    return {"status": "returned", "runs": [first, second]}


def child(case_path: str, result_path: str, submission: str) -> int:
    case = json.loads(Path(case_path).read_text(encoding="utf-8"))
    root = Path(submission)
    sys.path[0:0] = [str(root / "src"), str(root)]
    if case.get("metadata_dir"):
        sys.path.append(case["metadata_dir"])
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            module = importlib.import_module(case["module"])
    except BaseException as error:  # any import failure is an observation
        result: dict[str, Any] = {"status": "import_error", "exception": exception_info(error)}
    else:
        try:
            result = run_call(module, case) if case["kind"] == "call" else run_cli(module, case)
        except BaseException as error:  # e.g. SystemExit inside a call
            result = {"status": "crashed", "exception": exception_info(error)}
    text = json.dumps(result, allow_nan=True)
    if len(text) > MAX_RESULT_BYTES:
        text = json.dumps({"status": "error", "detail": "result too large"})
    Path(result_path).write_text(text, encoding="utf-8")
    return 0


# ----------------------------------------------------------------------------------------
# Parent: run every case in its own process
# ----------------------------------------------------------------------------------------


def package_versions() -> dict[str, str | None]:
    from importlib import metadata

    versions: dict[str, str | None] = {}
    for name in ("numpy", "scipy"):
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def parent(request_path: str, submission: str, timeout: float) -> int:
    request = json.loads(Path(request_path).read_text(encoding="utf-8"))
    observations = []
    scratch = Path(tempfile.mkdtemp(prefix="probe-"))
    metadata_dir = write_distribution_metadata(Path(submission), scratch / "metadata")
    for index, case in enumerate(request["cases"]):
        case_dir = scratch / f"case-{index:03d}"
        case_dir.mkdir()
        case_file = case_dir / "case.json"
        result_file = case_dir / "result.json"
        case_file.write_text(
            json.dumps(
                {"module": request["module"], "metadata_dir": str(metadata_dir) if metadata_dir else None, **case}
            ),
            encoding="utf-8",
        )
        log = case_dir / "output.log"
        started = time.monotonic()
        with log.open("wb") as sink:
            try:
                completed = subprocess.run(
                    [
                        sys.executable,
                        "-I",
                        "-B",
                        __file__,
                        "--child",
                        str(case_file),
                        str(result_file),
                        "--submission",
                        submission,
                    ],
                    cwd=case_dir,
                    stdin=subprocess.DEVNULL,
                    stdout=sink,
                    stderr=subprocess.STDOUT,
                    timeout=timeout,
                    check=False,
                )
                returncode: int | None = completed.returncode
            except subprocess.TimeoutExpired:
                returncode = None
        elapsed = time.monotonic() - started
        if returncode is None:
            observation: dict[str, Any] = {"status": "timeout", "detail": f"exceeded {timeout} s"}
        elif result_file.is_file() and result_file.stat().st_size <= MAX_RESULT_BYTES:
            try:
                observation = json.loads(result_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                observation = {"status": "error", "detail": "unreadable result"}
        else:
            tail = log.read_bytes()[-MAX_TEXT:].decode("utf-8", errors="replace") if log.is_file() else ""
            observation = {"status": "crashed", "detail": f"exit {returncode}: {tail}"}
        observation["id"] = case["id"]
        observation["seconds"] = round(elapsed, 3)
        observations.append(observation)
    report = {
        "runner_version": RUNNER_VERSION,
        "python": sys.version.split()[0],
        "packages": package_versions(),
        "observations": observations,
    }
    sys.stdout.write(json.dumps(report, allow_nan=True))
    sys.stdout.flush()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("request", nargs="?")
    parser.add_argument("--child", nargs=2, metavar=("CASE", "RESULT"))
    parser.add_argument("--submission", required=True)
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args(argv)
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    if args.child:
        return child(args.child[0], args.child[1], args.submission)
    if not args.request:
        parser.error("a request file is required")
    return parent(args.request, args.submission, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
