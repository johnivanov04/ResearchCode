"""End-to-end dry run with labelled fixtures: every pipeline stage, no AI model, no results."""

import json

import pytest

from rc_experiments.analysis import FIXTURE_LABEL
from rc_experiments.config import RESULTS_DIR
from rc_experiments.dryrun import dry_run
from rc_experiments.evaluators import load_fixture
from rc_experiments.pipeline import results_dir_for


def test_fixture_results_cannot_be_written_into_the_results_directory():
    with pytest.raises(ValueError, match="never"):
        results_dir_for("fixture", RESULTS_DIR / "genuine")


def test_end_to_end_dry_run(tmp_path, local_backend, config):
    summary = dry_run(tmp_path / "dry", local_backend, config, replicates=1, own_tests=False)
    assert summary["label"] == FIXTURE_LABEL
    results = sorted((tmp_path / "dry" / "results").iterdir())
    assert len(results) == len(load_fixture().task_ids) * len(config.condition_ids)
    for trial in results:
        record = json.loads((trial / "trial.json").read_text())
        evaluation = json.loads((trial / "evaluation.json").read_text())
        assert record["data_kind"] == evaluation["data_kind"] == "fixture"
        assert record["agent"]["mode"] == "fixture"
        assert record["task"].startswith("fixture-")  # public practice tasks only
        assert evaluation["evaluator"] == "fixture"
        assert (trial / "submission" / "TASK.md").is_file()
        # Replicate 1 uses a defective variant, so it must lose at least one hidden case.
        assert evaluation["hidden"]["summary"]["hidden_pass_rate"] < 1.0
    analysis = json.loads((tmp_path / "dry" / "analysis" / "analysis.json").read_text())
    assert analysis["data_kind"] == "fixture"
    assert analysis["label"] == FIXTURE_LABEL
    assert (tmp_path / "dry" / "analysis" / "report.md").read_text().startswith(f"> **{FIXTURE_LABEL}.**")
