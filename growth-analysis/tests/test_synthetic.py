"""Tests for the synthetic models and the bundled sample datasets."""

import csv
import math

import numpy as np
import pytest
from support import SAMPLE_DIR

from growth_analysis.synthetic import (
    SAMPLE_PLATE_FILENAME,
    WEBSITE_EXAMPLE_FILENAME,
    csv_text,
    exponential_od,
    logistic_od,
    main,
    sample_plate_rows,
    website_example_rows,
)


def test_exponential_model():
    t = np.array([0.0, 1.0, 2.0])
    np.testing.assert_allclose(exponential_od(t, 0.1, math.log(2)), [0.1, 0.2, 0.4], rtol=1e-15)


def test_logistic_model_limits_and_lag():
    # Before the lag N = N0; N(lag + t) solves the logistic equation; N -> K.
    t = np.array([0.0, 1.0, 2.0, 50.0])
    od = logistic_od(t, n0=0.01, k=1.0, r_per_h=1.0, lag_h=1.0)
    assert od[0] == pytest.approx(0.01, rel=1e-15)
    assert od[1] == pytest.approx(0.01, rel=1e-15)
    assert od[2] == pytest.approx(1.0 / (1.0 + 99.0 * math.exp(-1.0)), rel=1e-15)
    assert od[3] == pytest.approx(1.0, rel=1e-15)


def test_logistic_specific_growth_rate_is_r_times_one_minus_n_over_k():
    # Central difference of ln N against the analytic d ln N / dt = r (1 - N / K).
    r, k, n0, t, h = 1.2, 1.1, 0.01, 2.0, 1e-5
    ln = np.log(logistic_od(np.array([t - h, t + h]), n0, k, r))
    numeric = (ln[1] - ln[0]) / (2 * h)
    n = logistic_od(np.array([t]), n0, k, r)[0]
    assert numeric == pytest.approx(r * (1 - n / k), rel=1e-8)


@pytest.mark.parametrize(
    ("name", "rows"),
    [(SAMPLE_PLATE_FILENAME, sample_plate_rows), (WEBSITE_EXAMPLE_FILENAME, website_example_rows)],
)
def test_bundled_sample_files_match_their_generator(name, rows):
    # Regenerating from the documented seed must reproduce the committed file. Values are
    # rounded to 3 decimals; allow one unit in the last place in case a platform's exp or
    # normal sampler differs in the final bit at a rounding boundary.
    committed = list(csv.reader((SAMPLE_DIR / name).read_text(encoding="utf-8").splitlines()))
    regenerated = list(csv.reader(csv_text(rows()).splitlines()))
    assert committed[0] == regenerated[0] == ["well", "condition", "time_min", "od600"]
    assert len(committed) == len(regenerated)
    for old, new in zip(committed[1:], regenerated[1:], strict=True):
        assert old[:3] == new[:3]
        assert float(old[3]) == pytest.approx(float(new[3]), abs=0.0011)


def test_sample_plate_layout():
    rows = sample_plate_rows()
    wells = {(well, condition) for well, condition, _, _ in rows}
    assert {c for _, c in wells} == {"blank", "condition_A", "condition_B", "condition_C"}
    assert len(wells) == 12
    times = sorted({int(t) for _, _, t, _ in rows})
    assert times[0] == 0
    assert times[-1] == 960
    assert np.all(np.diff(times) == 15)


def test_website_example_matches_the_website_model():
    # web/src/lib/growth.ts: logistic r = 1.2/h, N0 = 0.01, K = 1.1, blank 0.045, every
    # 15 min for 12 h, Math.round(od * 1000) / 1000. Its own test compares the two directly.
    rows = [row for row in website_example_rows() if row[1] == "illustrative"]
    assert len(rows) == 49
    for _, _, time_min, od in rows:
        t = int(time_min) / 60
        expected = 0.045 + 1.1 / (1 + (1.1 - 0.01) / 0.01 * math.exp(-1.2 * t))
        assert float(od) == pytest.approx(expected, abs=0.0005 + 1e-12)


def test_generator_refuses_to_overwrite(tmp_path, capsys):
    assert main(["--output-dir", str(tmp_path)]) == 0
    assert main(["--output-dir", str(tmp_path)]) == 1
    assert "use --overwrite" in capsys.readouterr().err
    assert main(["--output-dir", str(tmp_path), "--overwrite"]) == 0
