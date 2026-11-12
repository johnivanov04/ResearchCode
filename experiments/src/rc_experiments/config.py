"""The experiment's configuration (``experiment.json``) and the project's directory layout."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any

# experiments/src/rc_experiments/config.py -> experiments/
EXPERIMENTS_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = EXPERIMENTS_DIR.parent
CONFIG_PATH = EXPERIMENTS_DIR / "experiment.json"
TASKS_DIR = EXPERIMENTS_DIR / "tasks"
CONDITIONS_DIR = EXPERIMENTS_DIR / "conditions"
RESULTS_DIR = EXPERIMENTS_DIR / "results"
STARTER_DIR = REPO_DIR / "scientific-starter"


@dataclass(frozen=True)
class Config:
    raw: dict[str, Any]

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> Config:
        return cls(json.loads(path.read_text(encoding="utf-8")))

    @property
    def protocol_version(self) -> str:
        return str(self.raw["protocol_version"])

    @cached_property
    def task_ids(self) -> list[str]:
        return [task["id"] for task in self.raw["tasks"]]

    @cached_property
    def condition_ids(self) -> list[str]:
        return [condition["id"] for condition in self.raw["conditions"]]

    def task(self, task_id: str) -> dict[str, Any]:
        for task in self.raw["tasks"]:
            if task["id"] == task_id:
                return task
        raise KeyError(f"unknown task {task_id!r}")

    def condition(self, condition_id: str) -> dict[str, Any]:
        for condition in self.raw["conditions"]:
            if condition["id"] == condition_id:
                return condition
        raise KeyError(f"unknown condition {condition_id!r}")

    @property
    def design(self) -> dict[str, Any]:
        return self.raw["design"]

    @property
    def agent(self) -> dict[str, Any]:
        return self.raw["agent"]

    @property
    def evaluation(self) -> dict[str, Any]:
        return self.raw["evaluation"]

    @property
    def analysis(self) -> dict[str, Any]:
        return self.raw["analysis"]

    @property
    def categories(self) -> list[str]:
        return list(self.raw["case_categories"])
