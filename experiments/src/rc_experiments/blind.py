"""Blinded review packets for the subjective maintainability review (protocol section 5.3).

Each packet contains only the submission's implementation module (the file or package the
task requires), under a random code. The key that maps codes to trials is written to a
separate file that the reviewer must not see. Blinding is imperfect: style can reveal the
condition.
"""

from __future__ import annotations

import secrets
import shutil
from pathlib import Path
from typing import Any

from rc_experiments.config import EXPERIMENTS_DIR, Config
from rc_experiments.trials import read_json, write_json


def module_location(submission: Path, module: str) -> Path | None:
    for base in (submission / "src", submission):
        if (base / module).is_dir():
            return base / module
        if (base / f"{module}.py").is_file():
            return base / f"{module}.py"
    return None


def make_packets(results_root: Path, packets_dir: Path, key_path: Path, config: Config) -> dict[str, Any]:
    if packets_dir.exists() and any(packets_dir.iterdir()):
        raise FileExistsError(f"{packets_dir} is not empty")
    if key_path.resolve().is_relative_to(packets_dir.resolve()):
        raise ValueError("the blinding key must be stored outside the reviewer's packet directory")
    packets_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(EXPERIMENTS_DIR / "docs" / "REVIEW_RUBRIC.md", packets_dir / "REVIEW_RUBRIC.md")
    key: dict[str, str] = {}
    missing: list[str] = []
    for record_path in sorted(results_root.glob("*/trial.json")):
        record = read_json(record_path)
        module = config.task(record["task"])["module"]
        location = module_location(record_path.parent / "submission", module)
        if location is None:
            missing.append(record["trial_id"])
            continue
        code = secrets.token_hex(4)
        while code in key:
            code = secrets.token_hex(4)
        target = packets_dir / f"{code}-{record['task']}"
        if location.is_dir():
            shutil.copytree(
                location, target / location.name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"), symlinks=False
            )
        else:
            target.mkdir(parents=True)
            shutil.copyfile(location, target / location.name)
        key[code] = record["trial_id"]
    write_json(key_path, {"codes": key, "without_module": missing})
    return {"packets": len(key), "without_module": missing}
