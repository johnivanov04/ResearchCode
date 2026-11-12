"""The probe runner observes submissions robustly: crashes, hangs, odd return types, mutation."""

import pytest

from rc_experiments.cases import as_tuple, call, cli, ndarray

FIXTURE_MODULE = """
import dataclasses, os, sys, time
import numpy as np

@dataclasses.dataclass
class Result:
    value: float
    flag: bool

class Attributes:
    def __init__(self):
        self.value = 2.5

def numpy_types():
    return {"f": np.float64(1.5), "i": np.int64(3), "b": np.bool_(True), "a": np.array([1.0, 2.0])}

def dataclass_result():
    return Result(1.25, False)

def attribute_result():
    return Attributes()

def raises_value_error(x):
    raise ValueError("bad input")

def hangs():
    while True:
        time.sleep(0.05)

def hard_exit():
    os._exit(3)

def calls_sys_exit():
    sys.exit(2)

def prints_noise():
    print("noise on stdout")
    return 1.0

def mutates(items):
    items.append(99)
    return len(items)

def kinds(a, b, c):
    return [type(a).__name__, type(b).__name__, type(c).__name__]

def counter(state={"n": 0}):
    state["n"] += 1
    return state["n"]

def main(argv):
    out = argv[argv.index("--output") + 1]
    if os.path.exists(out):
        return 1
    with open(out, "w") as handle:
        handle.write('{"ok": true}')
    return 0
"""


def probe(backend, submission, requests, timeout=5.0):
    cases = [{"id": f"c{i}", **r} for i, r in enumerate(requests)]
    result = backend.run(
        "probe_runner.py", submission, {"module": "fixture_mod", "cases": cases}, ["--timeout", str(timeout)], 300
    )
    assert result.error is None, result.error
    return result.report["observations"]


@pytest.fixture
def submission(make_submission):
    return make_submission({"fixture_mod.py": FIXTURE_MODULE})


def test_serialises_numpy_dataclass_and_attribute_results(local_backend, submission):
    np_obs, dc_obs, attr_obs = probe(
        local_backend,
        submission,
        [call("numpy_types"), call("dataclass_result"), call("attribute_result", fields=["value", "missing"])],
    )
    assert np_obs["value"] == {"f": 1.5, "i": 3, "b": True, "a": [1.0, 2.0]}
    assert dc_obs["value"] == {"value": 1.25, "flag": False}
    assert attr_obs["value"] == {"value": 2.5, "missing": {"__missing__": True}}


def test_records_exceptions_hangs_and_crashes_per_case(local_backend, submission):
    observations = probe(
        local_backend,
        submission,
        [
            call("raises_value_error", 1),
            call("hangs"),
            call("hard_exit"),
            call("calls_sys_exit"),
            call("prints_noise"),
            call("no_such_function"),
        ],
        timeout=2.0,
    )
    raised, hung, exited, sys_exit, noisy, missing = observations
    assert raised["status"] == "raised"
    assert raised["exception"]["types"][:2] == ["ValueError", "Exception"]
    assert hung["status"] == "timeout"
    assert exited["status"] == "crashed"
    assert sys_exit["status"] == "crashed"
    assert noisy == noisy | {"status": "returned", "value": 1.0}
    assert missing["status"] == "error"


def test_detects_mutated_arguments_and_rebuilds_tagged_inputs(local_backend, submission):
    mutated, kinds = probe(
        local_backend, submission, [call("mutates", [1, 2]), call("kinds", ndarray([1.0]), as_tuple([1, 2]), [1])]
    )
    assert mutated["inputs_mutated"] is True
    assert kinds["value"] == ["ndarray", "tuple", "list"]


def test_repeated_calls_and_isolated_processes(local_backend, submission):
    repeated, fresh = probe(local_backend, submission, [call("counter", repeat=2), call("counter")])
    assert repeated["values"] == [1, 2]  # state carried over within one process is visible
    assert fresh["value"] == 1  # but every case starts in a new process


def test_cli_cases_report_files_and_overwrite_protection(local_backend, submission):
    run = ["--output", "{dir}/out.json"]
    fresh, existing = probe(
        local_backend,
        submission,
        [cli(run, {}, report=["out.json"]), cli(run, {"out.json": "keep"}, report=["out.json"])],
    )
    assert fresh["exit_code"] == 0
    assert fresh["files_after"]["out.json"] == '{"ok": true}'
    assert existing["exit_code"] == 1
    assert existing["unchanged"] == {"out.json": True}


def test_import_failure_is_reported_for_every_case(local_backend, make_submission):
    broken = make_submission({"fixture_mod.py": "raise RuntimeError('broken at import')\n"})
    observations = probe(local_backend, broken, [call("anything"), call("other")])
    assert [o["status"] for o in observations] == ["import_error", "import_error"]


def test_module_found_in_src_package(local_backend, make_submission):
    package = make_submission({"src/fixture_mod/__init__.py": "def answer():\n    return 42\n"})
    (observation,) = probe(local_backend, package, [call("answer")])
    assert observation["value"] == 42


def test_installed_metadata_is_emulated_from_pyproject(local_backend, make_submission):
    project = make_submission(
        {
            "pyproject.toml": '[project]\nname = "fixture-project"\nversion = "1.2.3"\n',
            "src/fixture_mod/__init__.py": "from importlib import metadata\n"
            "VERSION = metadata.version('fixture-project')\n"
            "def version():\n    return VERSION\n",
        }
    )
    (observation,) = probe(local_backend, project, [call("version")])
    assert observation["value"] == "1.2.3"


def test_metadata_helper_is_identical_in_both_runners():
    from rc_experiments.sandbox import SCRIPTS_DIR

    def helper(name):
        text = (SCRIPTS_DIR / name).read_text(encoding="utf-8")
        start = text.index("def write_distribution_metadata")
        return text[start : text.index("\n\n\n", start)]

    assert helper("probe_runner.py") == helper("suite_runner.py")
