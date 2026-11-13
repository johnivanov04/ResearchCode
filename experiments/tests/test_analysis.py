"""The analysis follows the pre-registered plan and never mixes or mislabels data.

All values here are synthetic test inputs built in this file; they are not results.
"""

import json
import statistics

import pytest

from rc_experiments import analysis
from rc_experiments.analysis import AnalysisError, analyse, bootstrap_delta, delta, permutation_p


def cell_values(a_values, b_values, tasks=("t1", "t2")):
    return {t: {"A": list(a_values), "B": list(b_values)} for t in tasks}


def test_delta_is_the_mean_over_tasks_of_condition_differences():
    values = {"t1": {"A": [0.5, 0.7], "B": [0.9, 0.9]}, "t2": {"A": [1.0], "B": [0.8, 0.6]}}
    expected = statistics.fmean([0.9 - 0.6, 0.7 - 1.0])
    assert delta(values) == pytest.approx(expected)
    assert delta({"t1": {"A": [], "B": [1.0]}}) is None


def test_bootstrap_is_seeded_and_contains_the_estimate():
    values = cell_values([0.4, 0.5, 0.6, 0.55], [0.7, 0.8, 0.75, 0.9])
    first = bootstrap_delta(values, 2000, 0.95, 7)
    assert first == bootstrap_delta(values, 2000, 0.95, 7)
    assert first[0] <= delta(values) <= first[1]


def test_permutation_test_separates_clear_and_null_differences():
    assert permutation_p(cell_values([0.1] * 6, [0.9] * 6), 2000, 1) < 0.01
    assert permutation_p(cell_values([0.5, 0.6, 0.7] * 2, [0.5, 0.6, 0.7] * 2), 2000, 1) > 0.5


def write_trial(root, trial_id, task, condition, pass_rate, *, kind="fixture", validity="valid", freeze=True):
    trial_dir = root / trial_id
    trial_dir.mkdir(parents=True)
    record = {
        "trial_id": trial_id,
        "task": task,
        "condition": condition,
        "replicate": trial_id.rsplit("--", 1)[1],
        "data_kind": kind,
        "validity": validity,
        "validity_reason": "test",
        "agent": {"wall_clock_seconds": 600.0, "num_turns": None, "total_cost_usd_reported": None},
    }
    evaluation = {
        "freeze": {"matches": freeze},
        "hidden": {
            "evaluation_error": None,
            "summary": {
                "hidden_pass_rate": pass_rate,
                "category_balanced_pass_rate": pass_rate,
                "import_failed": False,
                "median_rel_error_known_answer": 0.0,
                "categories": {"known_answer": {"pass_rate": pass_rate}},
            },
        },
        "own_tests": {"mutation_score": 0.5, "tests_collected": 3, "all_own_tests_pass": True},
        "static": {
            "security_findings": 0,
            "lint_per_100_lines": 1.0,
            "unexpected_runtime_imports": [],
            "extra_declared_dependencies": [],
        },
    }
    (trial_dir / "trial.json").write_text(json.dumps(record))
    (trial_dir / "evaluation.json").write_text(json.dumps(evaluation))


def populate(root, config, kind="fixture", per_cell=2):
    for task in config.task_ids:
        for condition, rate in (("A", 0.6), ("B", 0.8)):
            for r in range(1, per_cell + 1):
                write_trial(root, f"{task}--{condition}--r{r:02d}", task, condition, rate + 0.01 * r, kind=kind)


def test_fixture_analysis_is_labelled_everywhere(tmp_path, config):
    populate(tmp_path / "results", config)
    result = analyse(tmp_path / "results", tmp_path / "out", config)
    assert result["label"] == analysis.FIXTURE_LABEL
    assert result["inference"]["permutation_p"] is None
    report = (tmp_path / "out" / "report.md").read_text()
    assert report.startswith(f"> **{analysis.FIXTURE_LABEL}.**")
    assert (tmp_path / "out" / "figures" / "hidden_pass_rate.png").stat().st_size > 1000
    assert result["primary"]["difference_B_minus_A"] == pytest.approx(0.2)


def test_genuine_data_below_the_minimum_is_descriptive_only(tmp_path, config):
    populate(tmp_path / "results", config, kind="genuine", per_cell=2)
    result = analyse(tmp_path / "results", tmp_path / "out", config)
    assert result["inference"]["inferential"] is False
    assert "descriptive only" in result["inference"]["note"]


def test_genuine_data_with_enough_trials_reports_the_permutation_test(tmp_path, config):
    populate(
        tmp_path / "results",
        config,
        kind="genuine",
        per_cell=config.design["minimum_valid_trials_per_cell_for_inference"],
    )
    result = analyse(tmp_path / "results", tmp_path / "out", config)
    assert result["inference"]["inferential"] is True
    assert 0 < result["inference"]["permutation_p"] <= 1


def test_refuses_to_mix_data_kinds(tmp_path, config):
    write_trial(tmp_path, "calibration--A--r01", "calibration", "A", 0.5, kind="fixture")
    write_trial(tmp_path, "calibration--B--r01", "calibration", "B", 0.5, kind="genuine")
    with pytest.raises(AnalysisError, match="mix"):
        analyse(tmp_path, tmp_path / "out", config)


def test_invalid_and_unfrozen_trials_are_excluded_with_reasons(tmp_path, config):
    populate(tmp_path / "results", config, kind="genuine")
    write_trial(
        tmp_path / "results", "calibration--A--r09", "calibration", "A", 0.0, kind="genuine", validity="invalid"
    )
    write_trial(tmp_path / "results", "calibration--B--r09", "calibration", "B", 1.0, kind="genuine", freeze=False)
    result = analyse(tmp_path / "results", tmp_path / "out", config)
    reasons = {e["trial_id"]: e["reason"] for e in result["excluded"]}
    assert "invalid" in reasons["calibration--A--r09"]
    assert "freeze" in reasons["calibration--B--r09"]
    assert result["trials_included"] == result["trials_found"] - 2


def test_never_overwrites_output(tmp_path, config):
    populate(tmp_path / "results", config)
    (tmp_path / "out").mkdir()
    (tmp_path / "out" / "existing.txt").write_text("keep")
    with pytest.raises(FileExistsError):
        analyse(tmp_path / "results", tmp_path / "out", config)


def test_reduced_samples_report_planned_against_achieved(tmp_path, config):
    """Protocol 1.1: fewer trials than planned are reported with their limitations, never extrapolated."""
    populate(tmp_path / "results", config, kind="genuine", per_cell=2)
    result = analyse(tmp_path / "results", tmp_path / "out", config)
    sample = result["sample_size"]
    planned = config.design["confirmatory_trials_per_cell"]
    assert sample["planned_total"] == planned * 6
    assert sample["achieved_total"] == 12
    assert all(cell["achieved"] == 2 and cell["planned"] == planned for cell in sample["cells"])
    assert sample["limitations"].startswith(f"Only 12 of {planned * 6} planned valid trials")
    report = (tmp_path / "out" / "report.md").read_text()
    assert "## Sample size: planned and achieved" in report
    assert "do not establish whether" in report
