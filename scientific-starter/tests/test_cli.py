"""End-to-end tests for the example command-line entry point."""

import json
import math
from pathlib import Path

import pytest

from scientific_starter.cli import RESULT_FILENAME, main
from scientific_starter.provenance import METADATA_FILENAME, file_sha256

EXAMPLE_CSV = Path(__file__).resolve().parents[1] / "data" / "example" / "two_readings.csv"


def write_csv(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_example_data_gives_the_specified_answer(tmp_path, capsys):
    out_dir = tmp_path / "results"
    assert main([str(EXAMPLE_CSV), "--out", str(out_dir)]) == 0

    result = json.loads((out_dir / RESULT_FILENAME).read_text())
    assert result["specific_growth_rate_per_h"] == pytest.approx(math.log(2) / 2, rel=1e-12)
    assert result["doubling_time_h"] == pytest.approx(2.0, rel=1e-12)

    record = json.loads((out_dir / METADATA_FILENAME).read_text())
    assert record["inputs"][0]["name"] == "two_readings.csv"
    assert record["inputs"][0]["sha256"] == file_sha256(EXAMPLE_CSV)
    assert record["parameters"]["time_unit"] == "h"

    output = capsys.readouterr().out
    assert "0.346574 per hour" in output
    assert "doubling time: 2 hours" in output


def test_declining_culture_has_no_doubling_time(tmp_path, capsys):
    csv_path = write_csv(tmp_path / "in.csv", "time_h,od_blank_corrected\n0,0.4\n1,0.2\n")
    assert main([str(csv_path), "--out", str(tmp_path / "out")]) == 0
    result = json.loads((tmp_path / "out" / RESULT_FILENAME).read_text())
    assert result["specific_growth_rate_per_h"] == pytest.approx(-math.log(2), rel=1e-12)
    assert result["doubling_time_h"] is None
    assert "not defined" in capsys.readouterr().out


def test_refuses_to_overwrite_results(tmp_path, capsys):
    out_dir = tmp_path / "out"
    assert main([str(EXAMPLE_CSV), "--out", str(out_dir)]) == 0
    assert main([str(EXAMPLE_CSV), "--out", str(out_dir)]) == 1
    assert "use --overwrite" in capsys.readouterr().err
    assert main([str(EXAMPLE_CSV), "--out", str(out_dir), "--overwrite"]) == 0


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        ("time_h,od\n0,0.1\n2,0.2\n", "missing column(s) od_blank_corrected"),
        ("time_h,od_blank_corrected\n0,0.1\n", "expected exactly 2 data rows, found 1"),
        ("time_h,od_blank_corrected\n0,0.1\n1,0.2\n2,0.4\n", "expected exactly 2 data rows"),
        ("time_h,od_blank_corrected\n0,0.1\n2,high\n", "line 3: not a number"),
        ("time_h,od_blank_corrected\n0,0.1\n2,\n", "line 3: not a number"),
        ("time_h,od_blank_corrected\n0,0.0\n2,0.2\n", "od1 must be > 0"),
        ("time_h,od_blank_corrected\n2,0.1\n0,0.2\n", "t2_h must be later than t1_h"),
        ("time_h,od_blank_corrected\n0,nan\n2,0.2\n", "od1 must be finite"),
    ],
)
def test_reports_invalid_input_without_writing_results(tmp_path, capsys, contents, message):
    csv_path = write_csv(tmp_path / "bad.csv", contents)
    out_dir = tmp_path / "out"
    assert main([str(csv_path), "--out", str(out_dir)]) == 1
    assert message in capsys.readouterr().err
    assert not out_dir.exists()


def test_missing_input_file_is_reported(tmp_path, capsys):
    assert main([str(tmp_path / "missing.csv"), "--out", str(tmp_path / "out")]) == 1
    assert "error:" in capsys.readouterr().err
