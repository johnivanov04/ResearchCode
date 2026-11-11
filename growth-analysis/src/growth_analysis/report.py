"""Write analysis results to an output directory (section 4 of the specification).

Every file this module would write is checked *before* anything is written: if any of them
already exists and ``overwrite`` is false, nothing is written at all. This prevents both
silent overwriting and a half-written mixture of old and new results.
"""

import csv
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from growth_analysis.blank import BlankSummary
from growth_analysis.compare import ConditionSummary
from growth_analysis.config import AnalysisConfig
from growth_analysis.exponential import WellResult
from growth_analysis.plotting import (
    condition_styles,
    figure_exponential_fits,
    figure_growth_curves,
    figure_growth_rate_comparison,
    figure_well,
    safe_filename,
    save_figure,
)
from growth_analysis.provenance import METADATA_FILENAME

__all__ = [
    "ASSUMPTIONS",
    "RESULTS_SCHEMA_VERSION",
    "AnalysisOutput",
    "planned_files",
    "write_outputs",
]

RESULTS_SCHEMA_VERSION = 1

ASSUMPTIONS = (
    "Blank-corrected OD600 is proportional to cell density within the fitted range.",
    "The blank is constant over time and the same for every sample well.",
    "Errors in ln(OD) are independent with constant variance (used for the standard error).",
    "Wells are independent replicates as labelled by their condition.",
    "Natural logarithms are used; time is in hours, rates in 1/h, doubling times in h.",
    "The reported growth rate is the least-squares slope of ln(OD) over the detected "
    "exponential phase: an average rate over that interval, not a model parameter such as a "
    "logistic intrinsic rate.",
)

WELL_COLUMNS = (
    "well",
    "condition",
    "status",
    "credible",
    "growth_rate_per_h",
    "growth_rate_se_per_h",
    "doubling_time_h",
    "r_squared",
    "n_points_in_phase",
    "phase_start_h",
    "phase_end_h",
    "fold_change_in_phase",
    "steepest_window_rate_per_h",
    "net_rate_per_h",
    "n_readings",
    "n_valid",
    "n_below_quantification_limit",
    "n_above_max_od",
    "flags",
)
CONDITION_COLUMNS = (
    "condition",
    "n_wells",
    "n_credible",
    "mean_growth_rate_per_h",
    "sd_growth_rate_per_h",
    "sem_growth_rate_per_h",
    "min_growth_rate_per_h",
    "max_growth_rate_per_h",
    "doubling_time_of_mean_rate_h",
    "ratio_to_reference",
    "wells_not_included",
)
POINT_COLUMNS = (
    "well",
    "condition",
    "time_h",
    "od600",
    "od_corrected",
    "used_in_fit",
    "exclusion_reason",
)


@dataclass(frozen=True)
class AnalysisOutput:
    """Everything produced by one analysis run, ready to be written."""

    source_name: str
    time_column: str
    ignored_columns: tuple[str, ...]
    config: AnalysisConfig
    blank: BlankSummary
    wells: tuple[WellResult, ...]
    conditions: tuple[ConditionSummary, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": RESULTS_SCHEMA_VERSION,
            "input": {
                "file": self.source_name,
                "time_column": self.time_column,
                "ignored_columns": list(self.ignored_columns),
            },
            "settings": self.config.to_dict(),
            "blank": self.blank.to_dict(),
            "assumptions": list(ASSUMPTIONS),
            "warnings": list(self.warnings),
            "wells": [well.summary_dict() for well in self.wells],
            "conditions": [condition.to_dict() for condition in self.conditions],
        }


def _format(value: object) -> str:
    """CSV cell text: empty for missing values, shortest round-trip text for floats."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return repr(value)
    return str(value)


def _write_csv(path: Path, columns: Sequence[str], rows: Sequence[dict], mode: str) -> None:
    with path.open(mode, newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(columns)
        for row in rows:
            writer.writerow([_format(row.get(column)) for column in columns])


def planned_files(
    output: AnalysisOutput, out_dir: Path, formats: Sequence[str], *, per_well_figures: bool
) -> list[Path]:
    """Every file :func:`write_outputs` would write, including run metadata."""
    files = [
        out_dir / name
        for name in (
            "results.json",
            "well_results.csv",
            "condition_summary.csv",
            "points.csv",
            METADATA_FILENAME,
        )
    ]
    stems = ["growth_curves", "exponential_fits", "growth_rate_comparison"]
    figures = out_dir / "figures"
    files += [figures / f"{stem}.{fmt}" for stem in stems for fmt in formats]
    if per_well_figures:
        files += [
            figures / "wells" / f"{safe_filename(well.well)}.{fmt}"
            for well in output.wells
            for fmt in formats
        ]
    return files


def check_well_filenames(output: AnalysisOutput) -> None:
    """Raise ``ValueError`` if two well names map to the same figure file name."""
    seen: dict[str, str] = {}
    for well in output.wells:
        name = safe_filename(well.well)
        if name in seen:
            raise ValueError(
                f"wells {seen[name]!r} and {well.well!r} would share the figure file name "
                f"{name!r}; rename one of them or use --no-well-figures"
            )
        seen[name] = well.well


def write_outputs(
    output: AnalysisOutput,
    out_dir: Path,
    formats: Sequence[str],
    *,
    per_well_figures: bool,
    overwrite: bool,
) -> list[Path]:
    """Write results, tables, and figures (but not run metadata) and return their paths.

    Raises:
        FileExistsError: If ``overwrite`` is false and any output file (including
            ``run_metadata.json``) already exists. Nothing is written in that case.
    """
    if per_well_figures:
        check_well_filenames(output)
    planned = planned_files(output, out_dir, formats, per_well_figures=per_well_figures)
    if not overwrite:
        existing = [path for path in planned if path.exists()]
        if existing:
            raise FileExistsError(
                f"{len(existing)} output file(s) already exist, for example {existing[0]}"
            )

    mode = "w" if overwrite else "x"
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []

    results_path = out_dir / "results.json"
    with results_path.open(mode, encoding="utf-8") as handle:
        json.dump(output.to_dict(), handle, indent=2, allow_nan=False)
        handle.write("\n")
    written.append(results_path)

    well_rows = [{**w.summary_dict(), "flags": ";".join(w.flags)} for w in output.wells]
    _write_csv(out_dir / "well_results.csv", WELL_COLUMNS, well_rows, mode)
    condition_rows = [
        {
            **c.to_dict(),
            "wells_not_included": ";".join(
                f"{well}: {reason}" for well, reason in c.wells_not_included.items()
            ),
        }
        for c in output.conditions
    ]
    _write_csv(out_dir / "condition_summary.csv", CONDITION_COLUMNS, condition_rows, mode)
    point_rows = [
        {"well": w.well, "condition": w.condition, **vars(point)}
        for w in output.wells
        for point in w.points
    ]
    _write_csv(out_dir / "points.csv", POINT_COLUMNS, point_rows, mode)
    written += [
        out_dir / name for name in ("well_results.csv", "condition_summary.csv", "points.csv")
    ]

    figures = out_dir / "figures"
    figures.mkdir(exist_ok=True)
    wells = list(output.wells)
    written += save_figure(
        figure_growth_curves(wells, output.blank),
        figures / "growth_curves",
        formats,
        overwrite=overwrite,
    )
    written += save_figure(
        figure_exponential_fits(wells, output.blank),
        figures / "exponential_fits",
        formats,
        overwrite=overwrite,
    )
    written += save_figure(
        figure_growth_rate_comparison(wells, list(output.conditions)),
        figures / "growth_rate_comparison",
        formats,
        overwrite=overwrite,
    )
    if per_well_figures:
        (figures / "wells").mkdir(exist_ok=True)
        styles = condition_styles(w.condition for w in wells)
        for well in wells:
            colour, marker = styles[well.condition]
            written += save_figure(
                figure_well(well, output.blank, colour, marker),
                figures / "wells" / safe_filename(well.well),
                formats,
                overwrite=overwrite,
            )
    return written
