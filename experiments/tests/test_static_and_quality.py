"""Static checks, and the mutation-based measure of a submission's own tests (public FIXTURE tasks).

Includes the regression tests for protocol 1.2: the starter kit's inherited tests are not
counted as the submission's tests and cannot affect its mutation score.
"""

import pytest

from rc_experiments import static
from rc_experiments.config import STARTER_DIR
from rc_experiments.dryrun import FIXTURE_TESTS
from rc_experiments.evaluators import load_fixture
from rc_experiments.test_quality import evaluate_own_tests, starter_file_hashes
from rc_experiments.workspace import starter_files

FIXTURE = load_fixture()

RISKY = """import pickle
import subprocess

import requests


def run(command):
    return subprocess.run(command, shell=True)


def load(blob):
    return pickle.loads(blob)
"""


def test_static_checks_ignore_the_submissions_own_ruff_configuration(make_submission):
    submission = make_submission(
        {
            "pyproject.toml": '[project]\nname = "x"\nversion = "0"\ndependencies = ["requests>=2", "numpy"]\n'
            '[tool.ruff.lint]\nignore = ["S"]\n',
            "src/risky/__init__.py": RISKY,
            "tests/test_risky.py": "def test_nothing():\n    assert True\n",
            "uv.lock": "version = 1\n",
        }
    )
    result = static.analyse(submission)
    # pickle.loads on input (S301) and subprocess with shell=True (S602), despite ignore = ["S"].
    assert {"S301", "S602"} <= set(result["security_findings_by_code"])
    assert result["unexpected_runtime_imports"] == ["requests"]
    assert result["extra_declared_dependencies"] == ["requests"]
    assert result["lock_file_present"] is True
    assert result["test_files"] == 1
    assert result["source_files"] == 1


def test_line_length_is_not_counted(make_submission):
    long_line = "VALUE = " + " + ".join(["1"] * 60) + "\n"
    result = static.analyse(make_submission({"m.py": long_line}))
    assert "E501" not in result["ruff_findings_by_code"]


@pytest.mark.parametrize("task", FIXTURE.task_ids)
def test_mutation_score_counts_only_valid_tests(task, local_backend, config, make_submission):
    evaluator = FIXTURE.task(task)
    submission = make_submission(
        {
            f"src/{evaluator.module}/__init__.py": evaluator.reference_path.read_text(encoding="utf-8"),
            f"tests/test_{evaluator.module}.py": FIXTURE_TESTS[task],
        }
    )
    result = evaluate_own_tests(evaluator, submission, local_backend, config)
    assert result["tests_collected"] == 2
    assert result["tests_inherited"] == 0
    assert result["all_own_tests_pass"] is False  # the deliberately wrong test fails
    assert result["valid_tests"] == 1  # ... and is excluded as invalid
    assert len(result["mutants"]) == len(evaluator.mutants())
    # Worked out by hand: 212 F -> 100 C catches the wrong Fahrenheit offset only (the 273 K offset
    # cancels in that direction); the mean of
    # [1, 2, 3, 4] catches none of the summary defects (SD, overwriting, NaN check).
    expected = {"fixture-temperature": 1 / 3, "fixture-summary": 0.0}[task]
    assert result["mutation_score"] == pytest.approx(expected)


def test_no_tests_means_a_mutation_score_of_zero(local_backend, config, make_submission):
    evaluator = FIXTURE.task("fixture-temperature")
    submission = make_submission({"fixture_temperature.py": evaluator.reference_path.read_text(encoding="utf-8")})
    result = evaluate_own_tests(evaluator, submission, local_backend, config)
    assert result["tests_collected"] == 0
    assert result["mutation_score"] == 0


# --------------------------------------------------------------------------------------
# Protocol 1.2: inherited starter-kit tests
# --------------------------------------------------------------------------------------


def starter_copy() -> dict[str, str]:
    """The tracked starter-kit files, as a Condition B workspace receives them."""
    return {p.as_posix(): (STARTER_DIR / p).read_text(encoding="utf-8") for p in starter_files()}


@pytest.fixture(scope="module")
def inherited_only(local_backend, config, tmp_path_factory):
    """The starter kit plus a task module, but no task tests (agent wrote none)."""
    evaluator = FIXTURE.task("fixture-temperature")
    root = tmp_path_factory.mktemp("inherited-only")
    files = starter_copy() | {
        "src/fixture_temperature/__init__.py": evaluator.reference_path.read_text(encoding="utf-8")
    }
    for relative, text in files.items():
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_text(text, encoding="utf-8")
    return evaluate_own_tests(evaluator, root, local_backend, config)


def test_inherited_starter_tests_are_not_counted(inherited_only):
    # The starter kit's own suite (137 tests, including doctests) runs, but none of it counts.
    assert inherited_only["tests_collected_total"] == 137
    assert inherited_only["tests_inherited"] == 137
    assert inherited_only["tests_collected"] == 0
    assert inherited_only["tests_passed_on_own_code"] == 0
    assert inherited_only["all_own_tests_pass"] is False


def test_inherited_tests_cannot_raise_the_mutation_score(inherited_only):
    assert inherited_only["valid_tests"] == 0
    assert inherited_only["mutation_score"] == 0


def test_task_tests_next_to_the_starter_kit_are_counted(local_backend, config, make_submission):
    evaluator = FIXTURE.task("fixture-temperature")
    files = starter_copy() | {
        "src/fixture_temperature/__init__.py": evaluator.reference_path.read_text(encoding="utf-8"),
        "tests/test_task.py": FIXTURE_TESTS["fixture-temperature"],
    }
    result = evaluate_own_tests(evaluator, make_submission(files), local_backend, config)
    assert result["tests_inherited"] == 137
    assert result["tests_collected"] == 2  # only the two task tests
    assert result["valid_tests"] == 1
    assert result["mutation_score"] == pytest.approx(1 / 3)  # identical to the run without the starter kit


def test_an_adapted_starter_test_file_counts_as_the_agents_own(local_backend, config, make_submission):
    evaluator = FIXTURE.task("fixture-temperature")
    files = starter_copy() | {
        "src/fixture_temperature/__init__.py": evaluator.reference_path.read_text(encoding="utf-8")
    }
    files["tests/test_growth.py"] += "\n\ndef test_added_by_the_agent():\n    assert 1 + 1 == 2\n"
    result = evaluate_own_tests(evaluator, make_submission(files), local_backend, config)
    adapted = sum(1 for line in files["tests/test_growth.py"].splitlines() if line.startswith("def test_"))
    assert result["tests_collected"] >= adapted  # every test in the changed file counts (parametrised ones expand)
    assert result["tests_inherited"] == result["tests_collected_total"] - result["tests_collected"]


def test_starter_hashes_cover_the_whole_kit():
    assert len(starter_file_hashes()) >= 20
