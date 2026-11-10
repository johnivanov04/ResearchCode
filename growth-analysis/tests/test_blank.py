"""Tests for blank correction and the quantification limit (spec section 3.1)."""

import statistics

import pytest
from support import csv_text

from growth_analysis.blank import estimate_blank, sample_wells
from growth_analysis.config import AnalysisConfig
from growth_analysis.readings import InputDataError, read_plate

BLANK_READINGS = {"A1": (0.040, 0.042, 0.041), "A2": (0.039, 0.043, 0.040)}


def plate_with_blanks(tmp_path, blank_label="blank"):
    rows = []
    for well, values in BLANK_READINGS.items():
        rows += [(well, blank_label, float(t), v) for t, v in enumerate(values)]
    rows += [("B1", "x", float(t), v) for t, v in enumerate((0.05, 0.08, 0.12))]
    path = tmp_path / "plate.csv"
    path.write_text(csv_text(rows), encoding="utf-8")
    return read_plate(path)


def test_mean_blank_and_sample_standard_deviation(tmp_path):
    readings = [v for values in BLANK_READINGS.values() for v in values]
    blank, warnings = estimate_blank(plate_with_blanks(tmp_path), AnalysisConfig(min_od=1e-6))
    assert blank.method == "mean"
    assert blank.wells == ("A1", "A2")
    assert blank.n_readings == 6
    assert blank.value == pytest.approx(statistics.fmean(readings), rel=1e-15)
    assert blank.sd == pytest.approx(statistics.stdev(readings), rel=1e-12)
    assert blank.min_reading == 0.039
    assert blank.max_reading == 0.043
    # Quantification limit: ten blank standard deviations, as min_od is smaller.
    assert blank.quantification_limit == pytest.approx(10 * statistics.stdev(readings), rel=1e-12)
    assert warnings == []


def test_min_od_is_used_when_larger_than_the_blank_based_limit(tmp_path):
    blank, _ = estimate_blank(plate_with_blanks(tmp_path), AnalysisConfig(min_od=0.5))
    assert blank.quantification_limit == 0.5


def test_blank_sd_multiple_is_configurable(tmp_path):
    readings = [v for values in BLANK_READINGS.values() for v in values]
    config = AnalysisConfig(min_od=1e-6, blank_sd_multiple=3.0)
    blank, _ = estimate_blank(plate_with_blanks(tmp_path), config)
    assert blank.quantification_limit == pytest.approx(3 * statistics.stdev(readings), rel=1e-12)


def test_custom_blank_label(tmp_path):
    plate = plate_with_blanks(tmp_path, blank_label="medium_only")
    blank, _ = estimate_blank(plate, AnalysisConfig(blank_label="medium_only"))
    assert blank.wells == ("A1", "A2")
    assert [w.well for w in sample_wells(plate, AnalysisConfig(blank_label="medium_only"))] == [
        "B1"
    ]


def test_missing_blank_wells_is_an_error_that_suggests_the_fix(write_plate):
    plate = read_plate(write_plate([("B1", "x", 0.0, 0.1), ("B1", "x", 1.0, 0.2)]))
    with pytest.raises(InputDataError, match="blank_method 'none'"):
        estimate_blank(plate, AnalysisConfig())


def test_a_plate_of_only_blanks_is_an_error(write_plate):
    plate = read_plate(write_plate([("A1", "blank", 0.0, 0.04), ("A1", "blank", 1.0, 0.04)]))
    with pytest.raises(InputDataError, match="no sample wells"):
        estimate_blank(plate, AnalysisConfig())


def test_blank_method_none_subtracts_nothing_and_warns_about_blank_wells(tmp_path):
    blank, warnings = estimate_blank(
        plate_with_blanks(tmp_path), AnalysisConfig(blank_method="none", min_od=0.002)
    )
    assert blank.value == 0.0
    assert blank.quantification_limit == 0.002
    assert blank.sd is None
    assert len(warnings) == 1
    assert "not subtracted" in warnings[0]


def test_single_blank_reading_warns_that_its_variability_is_unknown(write_plate):
    plate = read_plate(
        write_plate([("A1", "blank", 0.0, 0.04), ("B1", "x", 0.0, 0.1), ("B1", "x", 1.0, 0.2)])
    )
    blank, warnings = estimate_blank(plate, AnalysisConfig())
    assert blank.sd is None
    assert blank.quantification_limit == AnalysisConfig().min_od
    assert "only one blank reading" in warnings[0]


@pytest.mark.parametrize(
    ("settings", "error"),
    [
        ({"blank_method": "median"}, ValueError),
        ({"blank_label": " "}, ValueError),
        ({"min_od": 0.0}, ValueError),
        ({"min_od": float("nan")}, ValueError),
        ({"blank_sd_multiple": -1.0}, ValueError),
        ({"max_od": 0.001}, ValueError),
        ({"window_points": 2}, ValueError),
        ({"window_points": 5.0}, TypeError),
        ({"window_points": True}, TypeError),
        ({"min_relative_rate": 0.0}, ValueError),
        ({"min_relative_rate": 1.5}, ValueError),
        ({"min_fold_change": 1.0}, ValueError),
        ({"min_r_squared": 1.1}, ValueError),
        ({"max_relative_se": 0.0}, ValueError),
        ({"reference_condition": ""}, ValueError),
        ({"min_od": "0.01"}, TypeError),
    ],
)
def test_invalid_settings_are_rejected(settings, error):
    with pytest.raises(error):
        AnalysisConfig(**settings)
