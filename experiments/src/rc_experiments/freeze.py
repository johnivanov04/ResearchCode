"""Freeze record: SHA-256 hashes of every file that defines the experiment.

``FREEZE.json`` has two parts:

* ``files``: public files (protocol, configuration, task statements, prompts, harness, fixture
  evaluator, Docker files, lock file, and the starter kit, which is the treatment);
* ``private_files``: the genuine evaluator (hidden cases, references, defective variants),
  which is kept outside the public repository. Publishing its hashes commits to its exact
  content without revealing it; when it is released after data collection, anyone can check
  that it matches.

Every evaluation records whether the files still match. Genuine and pilot trials require the
private files to be present and unchanged; public CI, which does not have them, checks the
public part and says that the private part was not checked.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

from rc_experiments.config import EXPERIMENTS_DIR, REPO_DIR
from rc_experiments.evaluators import PRIVATE_PACKAGE, private_available, private_root
from rc_experiments.trials import now_utc, read_json, write_json

FREEZE_PATH = EXPERIMENTS_DIR / "FREEZE.json"
# Directory pathspecs include everything below them. (Without git's glob magic, a pattern such as
# "dir/**/*" would silently skip files directly inside "dir"; a test guards against that.)
FROZEN_PATTERNS = (
    "experiments/docs/PROTOCOL.md",
    "experiments/docs/REVIEW_RUBRIC.md",
    "experiments/experiment.json",
    "experiments/tasks",
    "experiments/conditions",
    "experiments/src/rc_experiments",
    "experiments/docker",
    "experiments/uv.lock",
    "scientific-starter",
)


def frozen_files() -> list[str]:
    """Tracked or new (not ignored) public files matching the frozen patterns, as repository paths."""
    completed = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", *FROZEN_PATTERNS],
        cwd=REPO_DIR,
        capture_output=True,
        check=True,
    )
    paths = sorted({p for p in completed.stdout.decode().split("\0") if p})
    return [p for p in paths if (REPO_DIR / p).is_file()]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_hashes() -> dict[str, str]:
    return {path: _sha(REPO_DIR / path) for path in frozen_files()}


def private_file_hashes() -> dict[str, str] | None:
    """Hashes of the private evaluator package (paths relative to its root), or None if absent."""
    if not private_available():
        return None
    package = private_root() / PRIVATE_PACKAGE
    return {
        str(path.relative_to(private_root())): _sha(path)
        for path in sorted(package.rglob("*.py"))
        if "__pycache__" not in path.parts
    }


def combined_hash(hashes: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for path in sorted(hashes):
        digest.update(f"{path}\0{hashes[path]}\n".encode())
    return digest.hexdigest()


def write_freeze(protocol_version: str, note: str) -> dict[str, Any]:
    hashes = file_hashes()
    private = private_file_hashes()
    if private is None:
        raise RuntimeError("the private evaluator must be present to write the freeze record")
    document = {
        "protocol_version": protocol_version,
        "frozen_at": now_utc(),
        "note": note,
        "combined_sha256": combined_hash(hashes),
        "files": hashes,
        "private_evaluator": {
            "note": "Hashes of the genuine evaluator, which is kept outside the public repository until data "
            "collection ends. Paths are relative to the private evaluator's root.",
            "combined_sha256": combined_hash(private),
            "files": private,
        },
    }
    write_json(FREEZE_PATH, document)
    return document


def verify_freeze(path: Path = FREEZE_PATH, *, require_private: bool = False) -> dict[str, Any]:
    """Compare the current files with the freeze record.

    The private part is checked whenever the private evaluator is present. If it is absent, it is
    reported as unchecked, and as a mismatch only when ``require_private`` is set (genuine trials).
    """
    current = file_hashes()
    if not path.is_file():
        return {
            "combined_sha256": combined_hash(current),
            "mismatches": ["FREEZE.json missing"],
            "private_checked": False,
        }
    record = read_json(path)
    recorded: dict[str, str] = record["files"]
    mismatches = sorted(
        [f"changed: {p}" for p in recorded if p in current and current[p] != recorded[p]]
        + [f"missing: {p}" for p in recorded if p not in current]
        + [f"new: {p}" for p in current if p not in recorded]
    )
    private_recorded: dict[str, str] = record.get("private_evaluator", {}).get("files", {})
    private_current = private_file_hashes()
    if private_current is None:
        private_checked = False
        if require_private:
            mismatches.append("private evaluator not available, so it could not be checked")
    else:
        private_checked = True
        mismatches += sorted(
            [
                f"private changed: {p}"
                for p in private_recorded
                if p in private_current and private_current[p] != private_recorded[p]
            ]
            + [f"private missing: {p}" for p in private_recorded if p not in private_current]
            + [f"private new: {p}" for p in private_current if p not in private_recorded]
        )
    return {"combined_sha256": combined_hash(current), "mismatches": mismatches, "private_checked": private_checked}
