"""Evaluators: the genuine (private) evaluator and the public fixture evaluator.

* **Genuine evaluator.** The hidden cases with their expected values, the reference solutions,
  and the defective variants for the three experiment tasks. It is kept **outside this public
  repository**, in a private directory (default ``~/researchcode-private/phase4-evaluator``,
  or ``$RC_PRIVATE_EVALUATOR``), until data collection ends. Its SHA-256 hashes are committed
  in ``FREEZE.json``, so anyone can later verify that it did not change. Genuine and pilot
  trials can only be evaluated where it is present.
* **Fixture evaluator** (``rc_experiments.fixture_evaluator``). Two small, clearly labelled
  practice tasks with their own public cases, references, and defects. Public CI and dry runs
  use it to test the machinery; it never scores a genuine trial.

Both have the same interface, so every stage of the harness runs identically on either.
"""

from __future__ import annotations

import hashlib
import importlib
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from types import ModuleType

from rc_experiments.cases import Case
from rc_experiments.config import TASKS_DIR
from rc_experiments.mutation import Mutant

PRIVATE_ENV = "RC_PRIVATE_EVALUATOR"
DEFAULT_PRIVATE_ROOT = Path.home() / "researchcode-private" / "phase4-evaluator"
PRIVATE_PACKAGE = "rc_private_evaluator"


class EvaluatorUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class TaskEvaluator:
    task: str
    module: str
    task_dir: Path
    reference_path: Path
    _cases: Callable[[], list[Case]] = field(repr=False)
    _mutants: Callable[[], list[Mutant]] = field(repr=False)

    def cases(self) -> tuple[Case, ...]:
        return _cached_cases(self.task, self._cases)

    def mutants(self) -> list[Mutant]:
        return [m for m in self._mutants() if m.task == self.task]


@cache
def _cached_cases(task: str, build: Callable[[], list[Case]]) -> tuple[Case, ...]:
    cases = tuple(build())
    ids = [case.id for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate case ids in {task}")
    return cases


@dataclass(frozen=True)
class Evaluator:
    kind: str  # "genuine" or "fixture"
    root: Path
    tasks: dict[str, TaskEvaluator]

    def task(self, task_id: str) -> TaskEvaluator:
        try:
            return self.tasks[task_id]
        except KeyError:
            raise KeyError(f"the {self.kind} evaluator has no task {task_id!r}") from None

    @property
    def task_ids(self) -> list[str]:
        return list(self.tasks)

    def files(self) -> list[Path]:
        """Every file of the evaluator package (for hashing), excluding caches."""
        return sorted(p for p in self.root.rglob("*") if p.is_file() and "__pycache__" not in p.parts)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _build(kind: str, package: ModuleType, root: Path, task_root: Callable[[str], Path]) -> Evaluator:
    def mutants() -> list[Mutant]:
        return list(package.mutants.MUTANTS)

    tasks = {
        task_id: TaskEvaluator(
            task=task_id,
            module=module.MODULE,
            task_dir=task_root(task_id),
            reference_path=package.reference_path(task_id),
            _cases=module.cases,
            _mutants=mutants,
        )
        for task_id, module in package.TASK_MODULES.items()
    }
    return Evaluator(kind, root, tasks)


def private_root() -> Path:
    return Path(os.environ.get(PRIVATE_ENV) or DEFAULT_PRIVATE_ROOT).expanduser().resolve()


def private_available() -> bool:
    return (private_root() / PRIVATE_PACKAGE / "__init__.py").is_file()


@cache
def load_genuine() -> Evaluator:
    root = private_root()
    if not private_available():
        raise EvaluatorUnavailableError(
            f"the private genuine evaluator was not found at {root}. It is deliberately not in the public "
            f"repository; set {PRIVATE_ENV} to its location. Genuine and pilot trials cannot be prepared or "
            "evaluated without it."
        )
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    package = importlib.import_module(PRIVATE_PACKAGE)
    importlib.import_module(f"{PRIVATE_PACKAGE}.mutants")
    return _build("genuine", package, root / PRIVATE_PACKAGE, lambda task: TASKS_DIR / task)


@cache
def load_fixture() -> Evaluator:
    from rc_experiments import fixture_evaluator as package

    importlib.import_module("rc_experiments.fixture_evaluator.mutants")
    root = Path(package.__file__).resolve().parent
    return _build("fixture", package, root, lambda task: root / "tasks" / task)


def for_data_kind(kind: str) -> Evaluator:
    """Fixture trials use the fixture evaluator; genuine and pilot trials use the private evaluator."""
    return load_fixture() if kind == "fixture" else load_genuine()
