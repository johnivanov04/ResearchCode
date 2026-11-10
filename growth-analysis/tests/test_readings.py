"""Tests for reading and validating plate CSV files (spec section 2.1)."""

import numpy as np
import pytest

from growth_analysis.readings import InputDataError, read_plate


def write(tmp_path, text, name="plate.csv", encoding="utf-8"):
    path = tmp_path / name
    path.write_text(text, encoding=encoding)
    return path


def problems_of(path):
    with pytest.raises(InputDataError) as info:
        read_plate(path)
    return info.value.problems


VALID = """well,condition,time_h,od600
A1,blank,0,0.04
B1,glucose,0,0.05
A1,blank,0.5,0.041
B1,glucose,0.5,0.07
"""


def test_reads_wells_in_order_with_their_readings(tmp_path):
    plate = read_plate(write(tmp_path, VALID))
    assert [w.well for w in plate.wells] == ["A1", "B1"]
    assert plate.conditions == ["blank", "glucose"]
    b1 = plate.wells[1]
    assert b1.condition == "glucose"
    np.testing.assert_array_equal(b1.time_h, [0.0, 0.5])
    np.testing.assert_array_equal(b1.od600, [0.05, 0.07])
    assert b1.lines == (3, 5)
    assert plate.time_column == "time_h"
    assert plate.source_name == "plate.csv"


@pytest.mark.parametrize(
    ("column", "values", "expected_h"),
    [
        ("time_h", ("0", "1.5"), [0.0, 1.5]),
        ("time_min", ("0", "90"), [0.0, 1.5]),
        ("time_s", ("0", "5400"), [0.0, 1.5]),
    ],
)
def test_time_is_converted_to_hours_from_the_unit_in_the_column_name(
    tmp_path, column, values, expected_h
):
    text = f"well,condition,{column},od600\nB1,x,{values[0]},0.1\nB1,x,{values[1]},0.2\n"
    plate = read_plate(write(tmp_path, text))
    np.testing.assert_allclose(plate.wells[0].time_h, expected_h, rtol=1e-15)


def test_byte_order_mark_from_spreadsheets_is_accepted(tmp_path):
    plate = read_plate(write(tmp_path, VALID, encoding="utf-8-sig"))
    assert plate.wells[0].well == "A1"


def test_extra_columns_are_ignored_and_reported(tmp_path):
    text = "well,condition,time_h,od600,temperature_c\nB1,x,0,0.1,37\nB1,x,1,0.2,37\n"
    plate = read_plate(write(tmp_path, text))
    assert plate.ignored_columns == ("temperature_c",)


def test_column_order_does_not_matter(tmp_path):
    text = "od600,time_h,condition,well\n0.1,0,x,B1\n0.2,1,x,B1\n"
    plate = read_plate(write(tmp_path, text))
    np.testing.assert_array_equal(plate.wells[0].od600, [0.1, 0.2])


def test_rows_interleaved_by_time_are_grouped_by_well(tmp_path):
    plate = read_plate(write(tmp_path, VALID))
    np.testing.assert_array_equal(plate.wells[0].od600, [0.04, 0.041])


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("well,condition,time_h", "missing required column(s): od600"),
        ("condition,time_h,od600", "missing required column(s): well"),
        ("well,condition,od600", "missing time column"),
        ("well,condition,time,od600", "'time' does not state its unit"),
        ("well,condition,time_h,time_min,od600", "more than one time column"),
        ("well,condition,time_h,od600,od600", "duplicate column name(s): od600"),
    ],
)
def test_header_problems(tmp_path, header, expected):
    problems = problems_of(write(tmp_path, header + "\n"))
    assert any(expected in problem for problem in problems), problems


def test_empty_file_and_header_without_data(tmp_path):
    assert problems_of(write(tmp_path, "", "empty.csv")) == ["the file is empty (no header row)"]
    problems = problems_of(write(tmp_path, "well,condition,time_h,od600\n", "header.csv"))
    assert problems == ["the file has a header but no data rows"]


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ("B1,x,0,", "line 3: od600 is missing"),
        ("B1,x,,0.1", "line 3: time_h is missing"),
        ("B1,x,0,OVRFLW", "line 3: od600 is not a number ('OVRFLW')"),
        ("B1,x,0,nan", "line 3: od600 must be finite"),
        ("B1,x,inf,0.1", "line 3: time_h must be finite"),
        ("B1,x,0,-inf", "line 3: od600 must be finite"),
        (",x,0,0.1", "line 3: well is missing"),
        ("B1, ,0,0.1", "line 3: condition is missing"),
        ("B1,x,0", "line 3: expected 4 fields, found 3"),
        ("B1,x,0,0.1,extra", "line 3: expected 4 fields, found 5"),
    ],
)
def test_invalid_values_are_reported_with_line_numbers(tmp_path, row, expected):
    text = f"well,condition,time_h,od600\nB2,x,0,0.1\n{row}\n"
    problems = problems_of(write(tmp_path, text))
    assert len(problems) == 1
    assert problems[0].startswith(expected), problems


def test_duplicate_measurement_is_an_error(tmp_path):
    text = "well,condition,time_h,od600\nB1,x,0,0.1\nB1,x,1,0.2\nB1,x,1,0.21\n"
    problems = problems_of(write(tmp_path, text))
    assert problems == ["line 4: duplicate measurement for well 'B1' at time 1 (also on line 3)"]


def test_duplicate_detected_after_unit_conversion_of_the_same_value(tmp_path):
    text = "well,condition,time_min,od600\nB1,x,30,0.1\nB1,x,30.0,0.2\n"
    assert "duplicate measurement" in problems_of(write(tmp_path, text))[0]


def test_times_out_of_order_within_a_well_are_an_error(tmp_path):
    text = "well,condition,time_h,od600\nB1,x,0,0.1\nB1,x,2,0.3\nB1,x,1,0.2\n"
    problems = problems_of(write(tmp_path, text))
    assert problems == [
        "line 4: time 1 for well 'B1' is earlier than 2 on line 3; sort readings by time"
    ]


def test_a_well_cannot_belong_to_two_conditions(tmp_path):
    text = "well,condition,time_h,od600\nB1,x,0,0.1\nB1,y,1,0.2\n"
    problems = problems_of(write(tmp_path, text))
    assert problems == ["well 'B1' appears under more than one condition: 'x', 'y'"]


def test_all_problems_are_reported_together(tmp_path):
    text = "well,condition,time_h,od600\nB1,x,0,abc\nB1,x,1,\nB2,x,0,nan\n"
    problems = problems_of(write(tmp_path, text))
    assert len(problems) == 3
    message = str(InputDataError("plate.csv", problems))
    assert "3 problem(s)" in message
    assert "line 2" in message
    assert "line 4" in message


def test_very_long_problem_lists_are_truncated_in_the_message():
    message = str(InputDataError("f.csv", [f"problem {i}" for i in range(60)]))
    assert "problem 49" in message
    assert "problem 50" not in message
    assert "and 10 more" in message


def test_blank_lines_are_skipped_but_line_numbers_stay_correct(tmp_path):
    text = "well,condition,time_h,od600\nB1,x,0,0.1\n\nB1,x,1,abc\n"
    assert problems_of(write(tmp_path, text)) == ["line 4: od600 is not a number ('abc')"]


def test_negative_and_zero_od_are_accepted_here_and_judged_by_the_analysis(tmp_path):
    # Values at or below the blank are valid measurements; the analysis excludes them from
    # fitting with a recorded reason rather than the reader rejecting the file.
    text = "well,condition,time_h,od600\nB1,x,0,0\nB1,x,1,-0.002\n"
    plate = read_plate(write(tmp_path, text))
    np.testing.assert_array_equal(plate.wells[0].od600, [0.0, -0.002])


def test_missing_file_raises_os_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_plate(tmp_path / "does-not-exist.csv")
