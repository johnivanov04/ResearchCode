"""Static checks of a submission (never executes it).

* Ruff with a fixed rule set and ``--isolated``, so the submission's own configuration
  (which could silence rules) is ignored.
* Imports: top-level modules imported by non-test code that are neither standard library,
  NumPy, SciPy, nor the submission's own modules.
* Declared runtime dependencies (``pyproject.toml``, ``requirements*.txt``) and lock files.
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
import tomllib
from collections import Counter
from pathlib import Path
from typing import Any

# The starter kit's rule set (security rules included); fixed for every submission. E501 (line
# length) is ignored: line width is a formatting preference, and Ruff's isolated default (88)
# would penalise code that follows the starter kit's own setting (100).
RUFF_RULES = "E,W,F,I,B,A,S,UP,SIM,C4,PT,N,DTZ,PTH,NPY,PGH,T10,RUF"
RUFF_IGNORE = "E501"
ALLOWED_THIRD_PARTY = {"numpy", "scipy"}
LOCK_FILES = ("uv.lock", "poetry.lock", "pylock.toml", "Pipfile.lock")
SKIP_DIRS = {
    ".venv",
    "venv",
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".hypothesis",
    "node_modules",
    "dist",
    "build",
}
_REQUIREMENT_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def python_files(root: Path) -> list[Path]:
    files = []
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root)
        if any(part in SKIP_DIRS or part.endswith(".egg-info") for part in relative.parts[:-1]):
            continue
        if path.is_symlink() or not path.is_file():
            continue
        files.append(path)
    return files


def is_test_file(root: Path, path: Path) -> bool:
    relative = path.relative_to(root)
    name = relative.name
    return (
        any(part in {"tests", "test"} for part in relative.parts[:-1])
        or name.startswith("test_")
        or name.endswith("_test.py")
        or name == "conftest.py"
    )


def code_lines(path: Path) -> int:
    """Non-blank lines that are not comments."""
    count = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            count += 1
    return count


def run_ruff(root: Path, files: list[Path]) -> list[dict[str, Any]]:
    if not files:
        return []
    command = [
        sys.executable,
        "-m",
        "ruff",
        "check",
        "--isolated",
        "--no-cache",
        "--exit-zero",
        "--output-format",
        "json",
        "--target-version",
        "py312",
        "--select",
        RUFF_RULES,
        "--ignore",
        RUFF_IGNORE,
        *[str(f) for f in files],
    ]
    completed = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=300, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"ruff failed: {completed.stderr[-500:]}")
    findings = json.loads(completed.stdout or "[]")
    return [
        {
            "code": f.get("code") or "syntax-error",
            "file": str(Path(f["filename"]).resolve().relative_to(root.resolve())),
        }
        for f in findings
    ]


def local_module_names(root: Path) -> set[str]:
    names = set()
    for base in (root / "src", root):
        if base.is_dir():
            for item in base.iterdir():
                if item.suffix == ".py":
                    names.add(item.stem)
                elif item.is_dir() and not item.name.startswith("."):
                    names.add(item.name)
    return names


def imported_top_level(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return set()
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


def declared_dependencies(root: Path) -> list[str]:
    names: list[str] = []
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        try:
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            for requirement in data.get("project", {}).get("dependencies", []) or []:
                match = _REQUIREMENT_NAME.match(str(requirement))
                if match:
                    names.append(match.group(1).lower())
        except tomllib.TOMLDecodeError:
            names.append("<unparseable pyproject.toml>")
    for requirements in sorted(root.glob("requirements*.txt")):
        if "dev" in requirements.name or "test" in requirements.name:
            continue
        for line in requirements.read_text(encoding="utf-8", errors="replace").splitlines():
            match = _REQUIREMENT_NAME.match(line)
            if match and not line.strip().startswith(("#", "-")):
                names.append(match.group(1).lower())
    return sorted(set(names))


def analyse(root: Path) -> dict[str, Any]:
    files = python_files(root)
    source = [f for f in files if not is_test_file(root, f)]
    tests = [f for f in files if is_test_file(root, f)]
    source_lines = sum(code_lines(f) for f in source)
    findings = run_ruff(root, source)
    by_code = Counter(f["code"] for f in findings)
    security = {code: n for code, n in by_code.items() if code.startswith("S")}

    local = local_module_names(root)
    imports = set().union(*(imported_top_level(f) for f in source)) if source else set()
    third_party = sorted(
        name
        for name in imports
        if name not in sys.stdlib_module_names and name not in local and name not in ALLOWED_THIRD_PARTY
    )
    dependencies = declared_dependencies(root)
    return {
        "python_files": len(files),
        "source_files": len(source),
        "test_files": len(tests),
        "source_lines": source_lines,
        "test_lines": sum(code_lines(f) for f in tests),
        "ruff_findings": sum(by_code.values()),
        "ruff_findings_by_code": dict(sorted(by_code.items())),
        "lint_per_100_lines": (100 * sum(by_code.values()) / source_lines) if source_lines else None,
        "security_findings": sum(security.values()),
        "security_findings_by_code": dict(sorted(security.items())),
        "unexpected_runtime_imports": third_party,
        "declared_runtime_dependencies": dependencies,
        "extra_declared_dependencies": [d for d in dependencies if d not in ALLOWED_THIRD_PARTY],
        "lock_file_present": any((root / name).is_file() for name in LOCK_FILES),
    }
