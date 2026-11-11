"""Tests for figures: they are produced, labelled, reproducible, and never overwrite."""

import numpy as np
import pytest
from support import make_well, no_blank

from growth_analysis.compare import summarise_conditions
from growth_analysis.config import AnalysisConfig
from growth_analysis.exponential import analyse_well
from growth_analysis.plotting import (
    condition_styles,
    figure_exponential_fits,
    figure_growth_curves,
    figure_growth_rate_comparison,
    figure_well,
    safe_filename,
    save_figure,
)

CONFIG = AnalysisConfig(blank_method="none", min_od=1e-6)


@pytest.fixture(scope="module")
def results():
    t = np.arange(0.0, 8.0, 0.25)
    growing = 0.01 * np.exp(0.8 * t)
    flat = np.full(t.size, 0.2)
    return [
        analyse_well(make_well(t, growing, "B1", "fast"), no_blank(), CONFIG),
        analyse_well(make_well(t, flat, "C1", "none"), no_blank(), CONFIG),
    ]


def texts(figure):
    found = []
    for ax in figure.axes:
        found += [ax.get_title(), ax.get_xlabel(), ax.get_ylabel()]
        found += [text.get_text() for text in ax.texts]
    found += [text.get_text() for text in figure.texts]
    found.append(figure.get_suptitle())
    return "\n".join(found)


def test_figures_have_units_and_results_in_their_labels(results):
    summaries = summarise_conditions(results)
    curves = texts(figure_growth_curves(results, no_blank(0.01)))
    assert "Time (h)" in curves
    assert "Blank-corrected OD600" in curves
    assert "log scale" in curves
    fits = texts(figure_exponential_fits(results, no_blank()))
    assert "B1 (fast)" in fits
    assert "0.8 h$^{-1}$" in fits
    assert "no growth detected" in fits
    comparison = texts(figure_growth_rate_comparison(results, summaries))
    assert r"Specific growth rate $\mu$ (h$^{-1}$)" in comparison
    assert "n = 1 credible / 1" in comparison
    single = texts(figure_well(results[0], no_blank(), "#0072B2", "o"))
    assert "Well B1 (fast)" in single


def test_saved_figures_are_identical_on_repeat(results, tmp_path):
    for fmt in ("png", "svg"):
        first = save_figure(
            figure_exponential_fits(results, no_blank()), tmp_path / "a", [fmt], overwrite=False
        )[0]
        second = save_figure(
            figure_exponential_fits(results, no_blank()), tmp_path / "b", [fmt], overwrite=False
        )[0]
        assert first.read_bytes() == second.read_bytes()


def test_save_refuses_to_overwrite_and_rejects_unknown_formats(results, tmp_path):
    figure = figure_growth_curves(results, no_blank())
    save_figure(figure, tmp_path / "f", ["png"], overwrite=False)
    with pytest.raises(FileExistsError):
        save_figure(figure, tmp_path / "f", ["png"], overwrite=False)
    save_figure(figure, tmp_path / "f", ["png"], overwrite=True)
    with pytest.raises(ValueError, match="unsupported figure format"):
        save_figure(figure, tmp_path / "g", ["jpg"], overwrite=False)


def test_condition_styles_follow_the_condition_not_its_position():
    first = condition_styles(["a", "b", "c"])
    again = condition_styles(["a", "b", "a", "c"])
    assert first == again
    assert len({colour for colour, _ in first.values()}) == 3
    assert len({marker for _, marker in first.values()}) == 3


@pytest.mark.parametrize(
    ("name", "expected"),
    [("A1", "A1"), ("plate 1/B2", "plate_1_B2"), ("../../etc", "etc"), ("..", "well")],
)
def test_safe_filename_cannot_escape_the_output_directory(name, expected):
    assert safe_filename(name) == expected
