"""Tests for growth_analysis.provenance (run metadata)."""

import hashlib
import json
import math
import platform
import shutil
import subprocess
from importlib import metadata
from pathlib import Path

import pytest

from growth_analysis.provenance import (
    METADATA_FILENAME,
    collect_run_metadata,
    file_sha256,
    write_run_metadata,
)

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")


def run_git(repo: Path, *args: str) -> str:
    git = shutil.which("git")
    assert git is not None
    # Isolate from the user's global configuration (signing, hooks, identity).
    command = [
        git,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.invalid",
        "-c",
        "commit.gpgsign=false",
        "-c",
        "core.hooksPath=/dev/null",
        *args,
    ]
    return subprocess.run(  # noqa: S603
        command, cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()


# ---------------------------------------------------------------------------------------
# Checksums
# ---------------------------------------------------------------------------------------


def test_file_sha256_matches_known_digest(tmp_path):
    # SHA-256 of the bytes b"abc" is a published test vector (FIPS 180-2).
    path = tmp_path / "abc.txt"
    path.write_bytes(b"abc")
    assert file_sha256(path) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_file_sha256_reads_large_files_in_chunks(tmp_path):
    data = bytes(range(256)) * 10_000  # 2.56 MB, larger than one 1 MiB chunk
    path = tmp_path / "large.bin"
    path.write_bytes(data)
    assert file_sha256(path) == hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------------------
# Contents of the record
# ---------------------------------------------------------------------------------------


def test_records_environment_parameters_seed_and_inputs(tmp_path):
    data_file = tmp_path / "plate1.csv"
    data_file.write_text("time_h,od_blank_corrected\n0,0.1\n2,0.2\n")

    record = collect_run_metadata(
        {"window_points": 5, "min_r2": 0.98, "nested": {"unit": "h"}},
        seed=20240611,
        input_files=[data_file],
        project_dir=tmp_path,
    )

    assert record["schema_version"] == 1
    assert record["python"]["version"] == platform.python_version()
    assert record["platform"] == {"system": platform.system(), "machine": platform.machine()}
    assert record["random_seed"] == 20240611
    assert record["parameters"] == {"window_points": 5, "min_r2": 0.98, "nested": {"unit": "h"}}
    assert record["inputs"] == [
        {
            "name": "plate1.csv",
            "size_bytes": data_file.stat().st_size,
            "sha256": hashlib.sha256(data_file.read_bytes()).hexdigest(),
        }
    ]
    assert record["created_utc"].endswith("+00:00")


def test_records_this_package_version():
    record = collect_run_metadata({})
    assert record["packages"]["growth-analysis"] == metadata.version("growth-analysis")


def test_records_requested_packages_and_marks_missing_ones():
    record = collect_run_metadata({}, packages=["pytest", "surely-not-an-installed-package"])
    assert record["packages"]["pytest"] == metadata.version("pytest")
    assert record["packages"]["surely-not-an-installed-package"] is None


def test_records_lockfile_checksum_when_present(tmp_path):
    assert collect_run_metadata({}, project_dir=tmp_path)["lockfile_sha256"] is None
    lockfile = tmp_path / "uv.lock"
    lockfile.write_text("version = 1\n")
    record = collect_run_metadata({}, project_dir=tmp_path)
    assert record["lockfile_sha256"] == file_sha256(lockfile)


def test_record_is_json_and_contains_no_private_paths(tmp_path):
    data_dir = tmp_path / "private-directory-name"
    data_dir.mkdir()
    data_file = data_dir / "input.csv"
    data_file.write_text("x\n")

    text = json.dumps(collect_run_metadata({}, input_files=[data_file], project_dir=tmp_path))

    assert "private-directory-name" not in text
    assert str(tmp_path) not in text
    assert str(Path.home()) not in text
    if platform.node():
        assert platform.node() not in text  # host name


def test_parameters_are_copied_not_referenced():
    parameters = {"thresholds": [1, 2]}
    record = collect_run_metadata(parameters)
    parameters["thresholds"].append(3)
    assert record["parameters"] == {"thresholds": [1, 2]}


# ---------------------------------------------------------------------------------------
# Rejected inputs
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "parameters",
    [
        {"api_key": "x"},
        {"DB_PASSWORD": "x"},
        {"access_token": "x"},
        {"nested": {"client_secret": "x"}},
        {"runs": [{"credentials": "x"}]},
    ],
)
def test_rejects_parameter_names_that_look_like_credentials(parameters):
    with pytest.raises(ValueError, match="looks like a credential"):
        collect_run_metadata(parameters)


@pytest.mark.parametrize("value", [math.nan, math.inf])
def test_rejects_values_json_cannot_represent(value):
    with pytest.raises(ValueError, match="JSON"):
        collect_run_metadata({"threshold": value})


def test_rejects_non_serialisable_parameters():
    with pytest.raises(ValueError, match="JSON-serialisable"):
        collect_run_metadata({"path": Path("data")})


def test_rejects_non_string_parameter_keys():
    with pytest.raises(TypeError, match="keys must be strings"):
        collect_run_metadata({1: "a"})


@pytest.mark.parametrize("seed", [True, 1.5, "42"])
def test_rejects_non_integer_seeds(seed):
    with pytest.raises(TypeError, match="seed must be an int"):
        collect_run_metadata({}, seed=seed)


def test_missing_input_file_is_an_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        collect_run_metadata({}, input_files=[tmp_path / "missing.csv"])


# ---------------------------------------------------------------------------------------
# Git state
# ---------------------------------------------------------------------------------------


def test_git_is_none_outside_a_repository(tmp_path):
    # tmp_path is not inside a git repository on any normal system.
    assert collect_run_metadata({}, project_dir=tmp_path)["git"] is None


@needs_git
def test_records_commit_and_uncommitted_changes(tmp_path):
    run_git(tmp_path, "init", "--quiet")
    (tmp_path / "analysis.py").write_text("print('v1')\n")
    run_git(tmp_path, "add", "analysis.py")
    run_git(tmp_path, "commit", "--quiet", "-m", "first")
    commit = run_git(tmp_path, "rev-parse", "HEAD")

    clean = collect_run_metadata({}, project_dir=tmp_path)["git"]
    assert clean == {"commit": commit, "uncommitted_changes": False}

    (tmp_path / "analysis.py").write_text("print('v2')\n")
    dirty = collect_run_metadata({}, project_dir=tmp_path)["git"]
    assert dirty == {"commit": commit, "uncommitted_changes": True}


# ---------------------------------------------------------------------------------------
# Writing the file
# ---------------------------------------------------------------------------------------


def test_write_creates_directory_and_valid_json(tmp_path):
    out_dir = tmp_path / "results" / "run1"
    path = write_run_metadata(out_dir, {"alpha": 0.05}, seed=7)
    assert path == out_dir / METADATA_FILENAME
    written = json.loads(path.read_text(encoding="utf-8"))
    assert written["parameters"] == {"alpha": 0.05}
    assert written["random_seed"] == 7


def test_write_refuses_to_overwrite_by_default(tmp_path):
    write_run_metadata(tmp_path, {"run": 1})
    with pytest.raises(FileExistsError):
        write_run_metadata(tmp_path, {"run": 2})
    assert json.loads((tmp_path / METADATA_FILENAME).read_text())["parameters"] == {"run": 1}


def test_write_overwrites_when_asked(tmp_path):
    write_run_metadata(tmp_path, {"run": 1})
    write_run_metadata(tmp_path, {"run": 2}, overwrite=True)
    assert json.loads((tmp_path / METADATA_FILENAME).read_text())["parameters"] == {"run": 2}
