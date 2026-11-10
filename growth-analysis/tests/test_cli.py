"""End-to-end tests of the ``growth-analyze`` command (spec section 4)."""

import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pytest
from support import SAMPLE_DIR, well_rows

from growth_analysis.cli import main

SAMPLE_PLATE = SAMPLE_DIR / "synthetic_plate.csv"
EXACT = 1e-9

TABLES = (
    "results.json",
    "well_results.csv",
    "condition_summary.csv",
    "points.csv",
    "run_metadata.json",
)
OVERVIEW_FIGURES = ("growth_curves", "exponential_fits", "growth_rate_comparison")


def run(*args: str | Path) -> int:
    return main([str(arg) for arg in args])


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def files_under(directory: Path) -> set[str]:
    return {str(p.relative_to(directory)) for p in directory.rglob("*") if p.is_file()}


def exponential_plate(write_plate, rates):
    """Blank wells reading 0.05 and two wells per rate with OD = 0.05 + 0.01 exp(mu t)."""
    t = np.arange(0.0, 6.0 + 1e-9, 0.25)
    rows = well_rows("A1", "blank", t, np.full(t.size, 0.05))
    rows += well_rows("A2", "blank", t, np.full(t.size, 0.05))
    for i, mu in enumerate(rates):
        for replicate in (1, 2):
            rows += well_rows(f"R{i}_{replicate}", f"mu_{mu}", t, 0.05 + 0.01 * np.exp(mu * t))
    return write_plate(rows)


# --- the bundled synthetic sample plate ------------------------------------------------


@pytest.fixture(scope="module")
def sample_run(tmp_path_factory):
    out = tmp_path_factory.mktemp("sample") / "results"
    assert main(["--input", str(SAMPLE_PLATE), "--output", str(out)]) == 0
    return out


def test_sample_run_writes_every_documented_file(sample_run):
    wells = ["B2", "B3", "B4", "C2", "C3", "C4", "D2", "D3", "D4"]
    expected = set(TABLES)
    expected |= {f"figures/{stem}.{fmt}" for stem in OVERVIEW_FIGURES for fmt in ("png", "svg")}
    expected |= {f"figures/wells/{well}.{fmt}" for well in wells for fmt in ("png", "svg")}
    assert files_under(sample_run) == expected
    for path in sample_run.rglob("*.png"):
        assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    for path in sample_run.rglob("*.svg"):
        assert b"<svg" in path.read_bytes()[:2000]


def logistic_with_lag(t, n0, k, r, lag):
    return k / (1 + (k / n0 - 1) * math.exp(-r * max(t - lag, 0.0)))


@pytest.mark.parametrize(
    ("condition", "n0", "k", "r", "lag"),
    [("condition_A", 0.004, 1.0, 1.0, 2.0), ("condition_B", 0.010, 0.8, 0.6, 1.0)],
)
def test_sample_growth_rates_agree_with_the_generating_model(sample_run, condition, n0, k, r, lag):
    # The sample data were generated from logistic curves with these parameters (see
    # data/sample/README.md). With noise, each estimate must lie within 4 of its standard
    # errors of the noise-free bound r (1 - x_end / K) <= mu <= r (1 - x_start / K).
    results = json.loads((sample_run / "results.json").read_text())
    wells = [w for w in results["wells"] if w["condition"] == condition]
    assert len(wells) == 3
    for well in wells:
        assert well["status"] == "growth"
        assert well["credible"]
        x_start = logistic_with_lag(well["phase_start_h"], n0, k, r, lag)
        x_end = logistic_with_lag(well["phase_end_h"], n0, k, r, lag)
        margin = 4 * well["growth_rate_se_per_h"]
        assert r * (1 - x_end / k) - margin <= well["growth_rate_per_h"]
        assert well["growth_rate_per_h"] <= r * (1 - x_start / k) + margin


def test_sample_no_growth_control_and_condition_order(sample_run):
    results = json.loads((sample_run / "results.json").read_text())
    control = [w for w in results["wells"] if w["condition"] == "condition_C"]
    assert [w["status"] for w in control] == ["no_growth"] * 3
    means = {c["condition"]: c["mean_growth_rate_per_h"] for c in results["conditions"]}
    assert means["condition_A"] > means["condition_B"] > 0
    assert means["condition_C"] is None
    assert results["blank"]["wells"] == ["A1", "A2", "A3"]
    assert results["input"] == {
        "file": "synthetic_plate.csv",
        "time_column": "time_min",
        "ignored_columns": [],
    }
    assert len(results["assumptions"]) >= 5


def test_points_table_accounts_for_every_sample_reading(sample_run):
    points = read_csv(sample_run / "points.csv")
    with SAMPLE_PLATE.open(newline="", encoding="utf-8") as handle:
        sample_rows = [row for row in csv.DictReader(handle) if row["condition"] != "blank"]
    assert len(points) == len(sample_rows)
    reasons = {row["exclusion_reason"] for row in points}
    assert reasons <= {"", "below_quantification_limit"}
    wells = read_csv(sample_run / "well_results.csv")
    for well in wells:
        used = [p for p in points if p["well"] == well["well"] and p["used_in_fit"] == "true"]
        expected = int(well["n_points_in_phase"]) if well["status"] == "growth" else 0
        assert len(used) == expected


def test_run_metadata_records_inputs_settings_and_environment(sample_run):
    record = json.loads((sample_run / "run_metadata.json").read_text())
    sha = hashlib.sha256(SAMPLE_PLATE.read_bytes()).hexdigest()
    assert record["inputs"] == [
        {"name": "synthetic_plate.csv", "size_bytes": SAMPLE_PLATE.stat().st_size, "sha256": sha}
    ]
    assert record["parameters"]["analysis"]["window_points"] == 5
    assert record["parameters"]["analysis"]["blank_sd_multiple"] == 10.0
    assert record["parameters"]["assumptions"]
    for package in ("growth-analysis", "numpy", "matplotlib"):
        assert record["packages"][package]
    assert record["random_seed"] is None  # the analysis itself uses no randomness
    text = json.dumps(record)
    assert str(sample_run) not in text
    assert str(Path.home()) not in text


def test_sample_analysis_is_repeatable_byte_for_byte(sample_run, tmp_path):
    second = tmp_path / "second"
    assert run("--input", SAMPLE_PLATE, "--output", second) == 0
    for name in files_under(sample_run) - {"run_metadata.json"}:
        assert (sample_run / name).read_bytes() == (second / name).read_bytes(), name


# --- known answers through the whole pipeline ------------------------------------------


def test_cultures_with_distinct_known_rates(write_plate, tmp_path):
    rates = (0.3, 0.6, 0.9)
    plate = exponential_plate(write_plate, rates)
    out = tmp_path / "out"
    assert (
        run(
            "--input",
            plate,
            "--output",
            out,
            "--reference-condition",
            "mu_0.3",
            "--no-well-figures",
            "--plot-format",
            "svg",
        )
        == 0
    )
    results = json.loads((out / "results.json").read_text())
    for well in results["wells"]:
        mu = float(well["condition"].removeprefix("mu_"))
        assert well["status"] == "growth"
        assert well["growth_rate_per_h"] == pytest.approx(mu, rel=EXACT)
        assert well["doubling_time_h"] == pytest.approx(math.log(2) / mu, rel=EXACT)
    for condition in results["conditions"]:
        mu = float(condition["condition"].removeprefix("mu_"))
        assert condition["n_credible"] == 2
        assert condition["mean_growth_rate_per_h"] == pytest.approx(mu, rel=EXACT)
        assert condition["ratio_to_reference"] == pytest.approx(mu / 0.3, rel=EXACT)
    assert not (out / "figures" / "wells").exists()
    assert {p.suffix for p in (out / "figures").iterdir()} == {".svg"}


def test_already_corrected_data_with_blank_method_none(write_plate, tmp_path):
    t = np.arange(0.0, 5.0, 0.25)
    plate = write_plate(well_rows("B1", "x", t, 0.02 * np.exp(0.5 * t)))
    out = tmp_path / "out"
    assert (
        run("--input", plate, "--output", out, "--blank-method", "none", "--no-well-figures") == 0
    )
    well = json.loads((out / "results.json").read_text())["wells"][0]
    assert well["growth_rate_per_h"] == pytest.approx(0.5, rel=EXACT)


# --- safety: never overwrite, never write partial results ------------------------------


def test_refuses_to_overwrite_and_leaves_existing_results_untouched(write_plate, tmp_path, capsys):
    plate = exponential_plate(write_plate, (0.5,))
    out = tmp_path / "out"
    assert run("--input", plate, "--output", out, "--no-well-figures") == 0
    before = {name: (out / name).read_bytes() for name in files_under(out)}
    assert run("--input", plate, "--output", out, "--no-well-figures") == 1
    assert "use --overwrite" in capsys.readouterr().err
    assert {name: (out / name).read_bytes() for name in files_under(out)} == before


def test_one_existing_output_file_blocks_the_whole_run(write_plate, tmp_path):
    plate = exponential_plate(write_plate, (0.5,))
    out = tmp_path / "out"
    (out / "figures").mkdir(parents=True)
    (out / "figures" / "growth_curves.png").write_bytes(b"older result")
    assert run("--input", plate, "--output", out, "--no-well-figures") == 1
    assert files_under(out) == {"figures/growth_curves.png"}


def test_overwrite_replaces_results(write_plate, tmp_path):
    plate = exponential_plate(write_plate, (0.5,))
    out = tmp_path / "out"
    assert run("--input", plate, "--output", out, "--no-well-figures") == 0
    assert run("--input", plate, "--output", out, "--no-well-figures", "--overwrite") == 0


# --- errors are reported, nothing is written -------------------------------------------


def test_invalid_input_reports_problems_and_writes_nothing(tmp_path, capsys):
    plate = tmp_path / "bad.csv"
    plate.write_text("well,condition,time_h,od600\nB1,x,0,0.1\nB1,x,0,0.2\nB1,x,1,\n")
    out = tmp_path / "out"
    assert run("--input", plate, "--output", out) == 1
    err = capsys.readouterr().err
    assert "2 problem(s)" in err
    assert "duplicate measurement" in err
    assert "od600 is missing" in err
    assert not out.exists()


@pytest.mark.parametrize(
    ("extra", "message"),
    [
        (("--window-points", "2"), "window_points must be at least 3"),
        (("--min-relative-rate", "0"), "min_relative_rate"),
        (("--reference-condition", "nope"), "reference condition 'nope' not found"),
        (("--blank-label", "medium"), "no blank wells"),
    ],
)
def test_invalid_settings_are_reported(write_plate, tmp_path, capsys, extra, message):
    plate = exponential_plate(write_plate, (0.5,))
    out = tmp_path / "out"
    assert run("--input", plate, "--output", out, *extra) == 1
    assert message in capsys.readouterr().err
    assert not out.exists()


def test_missing_input_file(tmp_path, capsys):
    assert run("--input", tmp_path / "missing.csv", "--output", tmp_path / "out") == 1
    assert "missing.csv" in capsys.readouterr().err


def test_well_names_that_collide_as_file_names_are_rejected(write_plate, tmp_path, capsys):
    t = np.arange(0.0, 3.0, 0.25)
    rows = well_rows("A 1", "x", t, 0.02 * np.exp(t)) + well_rows("A_1", "x", t, 0.02 * np.exp(t))
    plate = write_plate(rows)
    assert run("--input", plate, "--output", tmp_path / "out", "--blank-method", "none") == 1
    assert "share the figure file name" in capsys.readouterr().err


def test_help_and_version_exit_cleanly(capsys):
    with pytest.raises(SystemExit) as info:
        main(["--version"])
    assert info.value.code == 0
    assert capsys.readouterr().out.startswith("growth-analyze ")
