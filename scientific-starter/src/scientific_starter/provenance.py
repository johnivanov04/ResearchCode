"""Record how a result was produced, next to the result itself.

Call :func:`write_run_metadata` whenever your analysis writes results. It saves a small
``run_metadata.json`` file containing:

* when the run happened (UTC),
* the Python version and operating system family,
* versions of this package and its runtime dependencies (plus any you name),
* a SHA-256 checksum of ``uv.lock``, which pins the whole environment,
* the git commit, and whether there were uncommitted changes,
* the random seed, if your analysis uses randomness,
* the analysis parameters you pass in,
* the file name, size, and SHA-256 checksum of each input file.

Deliberately NOT recorded, to avoid leaking private information: the computer's host
name, your user name, absolute file paths, environment variables, and git remote URLs
(which can contain access tokens). Parameter names that look like credentials are
rejected. This is a safety net, not a guarantee: never pass secrets as parameters.
"""

import hashlib
import json
import platform
import re
import shutil
import subprocess
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any

__all__ = [
    "METADATA_FILENAME",
    "collect_run_metadata",
    "file_sha256",
    "write_run_metadata",
]

METADATA_FILENAME = "run_metadata.json"
SCHEMA_VERSION = 1

# Parameter names containing any of these fragments are rejected as likely credentials.
_SENSITIVE_KEY_FRAGMENTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "credential",
    "private_key",
)

_IMPORT_NAME = __name__.partition(".")[0]


def file_sha256(path: str | Path) -> str:
    """Return the SHA-256 checksum of a file as a hexadecimal string.

    The file is read in chunks, so large data files do not need to fit in memory.
    """
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _distribution_name() -> str | None:
    """Name of the installed distribution that provides this package, if any."""
    candidates = [*metadata.packages_distributions().get(_IMPORT_NAME, []), _IMPORT_NAME]
    # Editable installs (the default with `uv sync`) do not list the package's files, so
    # fall back to the import name; uv_build requires it to match the project name.
    for candidate in candidates:
        try:
            return metadata.distribution(candidate).metadata["Name"]
        except metadata.PackageNotFoundError:
            continue
    return None


def _runtime_requirement_names(distribution: str) -> list[str]:
    """Names of the declared runtime dependencies of ``distribution`` (extras excluded)."""
    names = []
    for requirement in metadata.requires(distribution) or []:
        if "extra ==" in requirement:
            continue
        match = re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*", requirement)
        if match:
            names.append(match.group(0))
    return names


def _package_versions(extra_packages: Iterable[str]) -> dict[str, str | None]:
    """Installed versions of this package, its runtime dependencies, and ``extra_packages``.

    A package that is not installed is recorded as ``None`` rather than raising, so that
    the record shows it was looked for.
    """
    names: list[str] = []
    distribution = _distribution_name()
    if distribution is not None:
        names.append(distribution)
        names.extend(_runtime_requirement_names(distribution))
    names.extend(extra_packages)

    versions: dict[str, str | None] = {}
    for name in names:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def _git_state(project_dir: Path) -> dict[str, Any] | None:
    """Current commit and dirty flag, or ``None`` if git or the repository is unavailable."""
    git = shutil.which("git")
    if git is None:
        return None

    def run(*args: str) -> str:
        # Fixed arguments and a resolved executable path; no shell and no user input.
        result = subprocess.run(  # noqa: S603
            [git, *args], cwd=project_dir, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()

    try:
        commit = run("rev-parse", "HEAD")
        status = run("status", "--porcelain")
    except (subprocess.CalledProcessError, OSError):
        return None
    return {"commit": commit, "uncommitted_changes": bool(status)}


def _check_parameters(value: Any, path: str = "parameters") -> None:
    """Reject non-string keys and keys that look like credentials, recursively."""
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path} keys must be strings, got {key!r}")
            lowered = key.lower()
            if any(fragment in lowered for fragment in _SENSITIVE_KEY_FRAGMENTS):
                raise ValueError(
                    f"{path}[{key!r}] looks like a credential; never record secrets in run metadata"
                )
            _check_parameters(item, f"{path}[{key!r}]")
    elif isinstance(value, list | tuple):
        for index, item in enumerate(value):
            _check_parameters(item, f"{path}[{index}]")


def collect_run_metadata(
    parameters: Mapping[str, Any],
    *,
    seed: int | None = None,
    input_files: Iterable[str | Path] = (),
    packages: Iterable[str] = (),
    project_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Return a JSON-serialisable record of how a result is being produced.

    Args:
        parameters: Analysis parameters, such as thresholds, units, or window sizes.
            Values must be JSON-serialisable (strings, numbers, booleans, None, lists,
            and dictionaries with string keys). NaN and infinity are rejected because
            standard JSON cannot represent them.
        seed: The random seed used by the analysis, or ``None`` if it uses no randomness.
        input_files: Input data files. Each is recorded by file name, size, and SHA-256
            checksum; the directory is not recorded.
        packages: Extra distribution names whose versions should be recorded, in
            addition to this package and its runtime dependencies.
        project_dir: Directory used to find ``uv.lock`` and the git repository.
            Defaults to the current working directory.

    Raises:
        TypeError: If ``seed`` is not an int or ``None``, or a parameter key is not a string.
        ValueError: If a parameter name looks like a credential, or parameters are not
            valid JSON.
        FileNotFoundError: If an input file does not exist.
    """
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
        raise TypeError(f"seed must be an int or None, got {type(seed).__name__}")

    _check_parameters(parameters)
    try:
        parameters_copy = json.loads(json.dumps(dict(parameters), allow_nan=False))
    except TypeError as error:
        raise ValueError(f"parameters must be JSON-serialisable: {error}") from error

    root = Path.cwd() if project_dir is None else Path(project_dir)
    lockfile = root / "uv.lock"

    inputs = []
    for item in input_files:
        path = Path(item)
        inputs.append(
            {
                "name": path.name,
                "size_bytes": path.stat().st_size,
                "sha256": file_sha256(path),
            }
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "created_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
        },
        "platform": {"system": platform.system(), "machine": platform.machine()},
        "packages": _package_versions(packages),
        "lockfile_sha256": file_sha256(lockfile) if lockfile.is_file() else None,
        "git": _git_state(root),
        "random_seed": seed,
        "parameters": parameters_copy,
        "inputs": inputs,
    }


def write_run_metadata(
    out_dir: str | Path,
    parameters: Mapping[str, Any],
    *,
    overwrite: bool = False,
    **kwargs: Any,
) -> Path:
    """Collect run metadata and write it to ``out_dir / run_metadata.json``.

    Accepts the same keyword arguments as :func:`collect_run_metadata`. Creates
    ``out_dir`` if needed. By default refuses to replace an existing metadata file, so
    that rerunning an analysis cannot silently overwrite the record of an earlier run.

    Returns:
        The path of the written file.

    Raises:
        FileExistsError: If the file exists and ``overwrite`` is false.
    """
    record = collect_run_metadata(parameters, **kwargs)
    directory = Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / METADATA_FILENAME
    with target.open("w" if overwrite else "x", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    return target
