"""Command-line interface: ``growth-analyze``.

Analyse a plate CSV file and write results, figures, and run metadata::

    uv run growth-analyze --input data/sample/synthetic_plate.csv --output results/sample

Run ``uv run growth-analyze --help`` for every option. This module only handles the
boundary (arguments, files, messages); the science lives in the other modules.
"""

import argparse
import sys
from collections.abc import Sequence
from importlib import metadata
from pathlib import Path

from growth_analysis.analysis import analyse_plate
from growth_analysis.config import AnalysisConfig
from growth_analysis.plotting import FORMATS
from growth_analysis.provenance import write_run_metadata
from growth_analysis.readings import InputDataError, read_plate
from growth_analysis.report import ASSUMPTIONS, AnalysisOutput, write_outputs

__all__ = ["build_parser", "main"]

_DEFAULTS = AnalysisConfig()


def _version() -> str:
    try:
        return metadata.version("growth-analysis")
    except metadata.PackageNotFoundError:  # Running from source without installation.
        return "unknown"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="growth-analyze",
        description=(
            "Estimate specific growth rates and doubling times from optical density time "
            "courses. See docs/spec-growth-curve.md for the method."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {_version()}")
    io = parser.add_argument_group("input and output")
    io.add_argument(
        "--input",
        type=Path,
        required=True,
        help="CSV with columns well, condition, od600, and time_h, time_min, or time_s",
    )
    io.add_argument("--output", type=Path, required=True, help="directory for the results")
    io.add_argument(
        "--overwrite", action="store_true", help="replace existing result files in --output"
    )
    io.add_argument(
        "--plot-format",
        nargs="+",
        choices=FORMATS,
        default=list(FORMATS),
        help="figure file format(s)",
    )
    io.add_argument(
        "--no-well-figures",
        action="store_true",
        help="skip the per-well figures (useful for large plates)",
    )

    blank = parser.add_argument_group("blank correction")
    blank.add_argument(
        "--blank-method",
        choices=("mean", "none"),
        default=_DEFAULTS.blank_method,
        help="'mean' subtracts the mean of blank wells; 'none' if OD values are "
        "already blank-corrected",
    )
    blank.add_argument(
        "--blank-label",
        default=_DEFAULTS.blank_label,
        help="condition label of blank (medium-only) wells",
    )
    blank.add_argument(
        "--min-od",
        type=float,
        default=_DEFAULTS.min_od,
        help="lowest blank-corrected OD used in a fit",
    )
    blank.add_argument(
        "--blank-sd-multiple",
        type=float,
        default=_DEFAULTS.blank_sd_multiple,
        help="the quantification limit is the larger of --min-od and this many "
        "standard deviations of the blank readings",
    )
    blank.add_argument(
        "--max-od",
        type=float,
        default=_DEFAULTS.max_od,
        help="optional upper limit of the instrument's linear range (blank-corrected OD)",
    )

    fit = parser.add_argument_group("exponential phase and credibility")
    fit.add_argument(
        "--window-points",
        type=int,
        default=_DEFAULTS.window_points,
        help="readings per sliding window",
    )
    fit.add_argument(
        "--min-relative-rate",
        type=float,
        default=_DEFAULTS.min_relative_rate,
        help="windows with a slope at least this fraction of the steepest belong "
        "to the exponential phase",
    )
    fit.add_argument(
        "--min-fold-change",
        type=float,
        default=_DEFAULTS.min_fold_change,
        help="minimum fold change in OD across the exponential phase",
    )
    fit.add_argument(
        "--min-r-squared",
        type=float,
        default=_DEFAULTS.min_r_squared,
        help="minimum R^2 for a credible fit",
    )
    fit.add_argument(
        "--max-relative-se",
        type=float,
        default=_DEFAULTS.max_relative_se,
        help="maximum SE(mu)/mu for a credible fit",
    )
    fit.add_argument(
        "--reference-condition",
        default=None,
        help="condition that other conditions' mean rates are divided by",
    )
    return parser


def _config_from_args(args: argparse.Namespace) -> AnalysisConfig:
    return AnalysisConfig(
        blank_method=args.blank_method,
        blank_label=args.blank_label,
        min_od=args.min_od,
        blank_sd_multiple=args.blank_sd_multiple,
        max_od=args.max_od,
        window_points=args.window_points,
        min_relative_rate=args.min_relative_rate,
        min_fold_change=args.min_fold_change,
        min_r_squared=args.min_r_squared,
        max_relative_se=args.max_relative_se,
        reference_condition=args.reference_condition,
    )


def _print_summary(output: AnalysisOutput) -> None:
    print(f"Analysed {len(output.wells)} well(s) from {output.source_name}")
    blank = output.blank
    if blank.method == "mean":
        print(
            f"Blank: {blank.value:.4g} (mean of {blank.n_readings} readings from "
            f"{len(blank.wells)} well(s)); quantification limit {blank.quantification_limit:.3g}"
        )
    else:
        print(f"Blank: not subtracted; quantification limit {blank.quantification_limit:.3g}")
    print()
    print(f"{'well':<10} {'condition':<16} {'status':<18} {'mu (1/h)':>9} {'Td (h)':>8}  credible")
    for well in output.wells:
        rate = f"{well.growth_rate_per_h:.3f}" if well.growth_rate_per_h is not None else "-"
        td = f"{well.doubling_time_h:.2f}" if well.doubling_time_h is not None else "-"
        credible = "yes" if well.credible else "no"
        print(
            f"{well.well:<10} {well.condition:<16} {well.status:<18} {rate:>9} {td:>8}  {credible}"
        )
    print()
    for condition in output.conditions:
        if condition.mean_growth_rate_per_h is None:
            print(
                f"{condition.condition}: no credible growth rate "
                f"({condition.n_credible}/{condition.n_wells} wells)"
            )
            continue
        sd = (
            f" ± {condition.sd_growth_rate_per_h:.3f} (SD)"
            if condition.sd_growth_rate_per_h is not None
            else ""
        )
        print(
            f"{condition.condition}: mean mu {condition.mean_growth_rate_per_h:.3f}{sd} 1/h "
            f"from {condition.n_credible}/{condition.n_wells} credible wells"
        )
    if output.warnings:
        print()
        for warning in output.warnings:
            print(f"warning: {warning}")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the analysis. Returns 0 on success and 1 on an input or output error."""
    args = build_parser().parse_args(argv)
    try:
        config = _config_from_args(args)
        plate = read_plate(args.input)
        output = analyse_plate(plate, config)
        written = write_outputs(
            output,
            args.output,
            args.plot_format,
            per_well_figures=not args.no_well_figures,
            overwrite=args.overwrite,
        )
        written.append(
            write_run_metadata(
                args.output,
                {
                    "analysis": config.to_dict(),
                    "assumptions": list(ASSUMPTIONS),
                    "figure_formats": list(args.plot_format),
                    "per_well_figures": not args.no_well_figures,
                },
                input_files=[args.input],
                overwrite=args.overwrite,
            )
        )
    except FileExistsError as error:
        print(f"error: {error}; use --overwrite to replace them", file=sys.stderr)
        return 1
    except (InputDataError, ValueError, TypeError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    _print_summary(output)
    print()
    print(f"Wrote {len(written)} files to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
