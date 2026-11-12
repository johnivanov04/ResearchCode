"""Prepare a clean, independent workspace for one trial, and check its isolation.

Layout of a trial directory (outside the repository):

    <trials-root>/<trial-id>/
        trial.json     record of the trial (never visible to the agent)
        prompt.txt     the exact prompt given to the agent
        workspace/     the ONLY directory the agent sees

The workspace receives the task statement and public examples, plus, in Condition B, the
tracked files of ``scientific-starter/``. Nothing else is copied, and the copy is checked
against every hidden file by content hash.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path
from typing import Any

from rc_experiments.config import EXPERIMENTS_DIR, REPO_DIR, STARTER_DIR, TASKS_DIR, Config
from rc_experiments.evaluators import load_fixture, load_genuine, private_available, private_root
from rc_experiments.trials import DATA_KINDS, TrialId, now_utc, write_json

TASK_FILES = ("TASK.md", "public_examples.json")
# Files whose presence in an ancestor directory would leak instructions into an agent session.
INSTRUCTION_FILES = ("CLAUDE.md", "AGENTS.md", "CLAUDE.local.md")


class IsolationError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hidden_hashes() -> dict[str, str]:
    """Content hashes of the private evaluator (when present), the fixture evaluator, and the harness."""
    hashes: dict[str, str] = {}
    roots = [EXPERIMENTS_DIR / "src"]
    if private_available():
        roots.append(private_root())
    for root in roots:
        for path in root.rglob("*"):
            # Empty files (such as py.typed markers) carry no information and are skipped, and task
            # statements are public material that workspaces are meant to receive.
            if (
                path.is_file()
                and "__pycache__" not in path.parts
                and ".git" not in path.parts
                and "tasks" not in path.relative_to(root).parts
                and path.stat().st_size > 0
            ):
                hashes[sha256(path)] = str(path)
    return hashes


def task_directory(task: str, config: Config) -> Path:
    """The public statement of a task: an experiment task, or a fixture practice task."""
    if task in config.task_ids:
        return TASKS_DIR / task
    fixture = load_fixture()
    if task in fixture.tasks:
        return fixture.task(task).task_dir
    raise KeyError(f"unknown task {task!r}")


def starter_files() -> list[Path]:
    """Tracked files of the starter kit (paths relative to the starter directory)."""
    completed = subprocess.run(
        ["git", "ls-files", "-z", "--", "scientific-starter"],
        cwd=REPO_DIR,
        capture_output=True,
        check=True,
    )
    paths = [Path(p) for p in completed.stdout.decode().split("\0") if p]
    return [p.relative_to("scientific-starter") for p in paths]


def starter_is_clean() -> bool:
    completed = subprocess.run(
        ["git", "status", "--porcelain", "--", "scientific-starter"],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip() == ""


def starter_tree() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD:scientific-starter"],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def check_ancestors(path: Path) -> None:
    """No instruction file or repository may sit above the trials root (matters for manual runs)."""
    for parent in path.resolve().parents:
        for name in INSTRUCTION_FILES:
            if (parent / name).exists():
                raise IsolationError(f"{parent / name} would be visible to an agent working below it")
        if (parent / ".claude" / "settings.json").exists() and parent != Path.home():
            raise IsolationError(f"{parent / '.claude'} would configure an agent working below it")
        if (parent / ".git").exists():
            raise IsolationError(f"{parent} is a Git repository; put the trials root outside it")


def prompt_text(condition: str, config: Config) -> str:
    return (EXPERIMENTS_DIR / config.condition(condition)["prompt_file"]).read_text(encoding="utf-8")


def check_workspace(workspace: Path, expected: dict[str, str]) -> None:
    """The workspace holds exactly the expected files, none of them hidden material."""
    hidden = hidden_hashes()
    found: dict[str, str] = {}
    for path in sorted(workspace.rglob("*")):
        if path.is_symlink():
            raise IsolationError(f"unexpected symbolic link {path}")
        if path.is_file():
            digest = sha256(path)
            if digest in hidden:
                raise IsolationError(f"{path} has the same content as hidden file {hidden[digest]}")
            found[str(path.relative_to(workspace))] = digest
    if found != expected:
        missing = sorted(set(expected) - set(found))
        extra = sorted(set(found) - set(expected))
        raise IsolationError(f"workspace contents differ from the plan (missing {missing}, extra {extra})")


def prepare(trial: TrialId, trials_root: Path, config: Config, data_kind: str) -> Path:
    """Create ``<trials_root>/<trial>/workspace`` for a trial and record it. Returns the trial directory."""
    if data_kind not in DATA_KINDS:
        raise ValueError(f"data kind must be one of {DATA_KINDS}")
    if (data_kind == "pilot") != trial.is_pilot and data_kind != "fixture":
        raise ValueError("pilot trials have replicates pNN and pilot data kind; confirmatory trials rNN")
    config.condition(trial.condition)
    if data_kind == "fixture":
        task_dir = task_directory(trial.task, config)
    else:
        config.task(trial.task)
        task_dir = TASKS_DIR / trial.task
        load_genuine()  # genuine and pilot trials need the private evaluator to be checked and scored
    trials_root = trials_root.resolve()
    if trials_root.is_relative_to(REPO_DIR.resolve()):
        raise IsolationError("the trials root must be outside the repository")
    check_ancestors(trials_root)

    trial_dir = trials_root / str(trial)
    if trial_dir.exists():
        raise FileExistsError(f"{trial_dir} already exists; each trial starts from a new workspace")
    workspace = trial_dir / "workspace"
    workspace.mkdir(parents=True)

    expected: dict[str, str] = {}
    for name in TASK_FILES:
        source = task_dir / name
        shutil.copyfile(source, workspace / name)
        expected[name] = sha256(source)
    starter: dict[str, Any] | None = None
    if config.condition(trial.condition)["slug"] == "structured":
        if data_kind != "fixture" and not starter_is_clean():
            raise IsolationError("scientific-starter/ has uncommitted changes; the treatment must be the committed kit")
        for relative in starter_files():
            target = workspace / relative
            if relative.as_posix() in expected:
                raise IsolationError(f"starter file {relative} would overwrite a task file")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(STARTER_DIR / relative, target)
            expected[relative.as_posix()] = sha256(STARTER_DIR / relative)
        starter = {"git_tree": starter_tree(), "files": len(expected) - len(TASK_FILES)}

    check_workspace(workspace, expected)
    prompt = prompt_text(trial.condition, config)
    (trial_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    write_json(
        trial_dir / "trial.json",
        {
            "trial_id": str(trial),
            "task": trial.task,
            "condition": trial.condition,
            "replicate": trial.replicate,
            "data_kind": data_kind,
            "protocol_version": config.protocol_version,
            "prepared_at": now_utc(),
            "workspace_files": expected,
            "starter": starter,
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "validity": "pending",
        },
    )
    return trial_dir
