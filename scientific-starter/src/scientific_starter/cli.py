"""Command-line entry point for the example analysis.

Reads two blank-corrected optical density readings from a CSV file, computes the
specific growth rate and doubling time, and writes the result together with run
metadata::

    uv run python -m scientific_starter.cli data/example/two_readings.csv --out results/example

The input CSV must have a header row with the columns ``time_h`` and
``od_blank_corrected`` and exactly two data rows, in time order. Use it as a pattern for
your own entry point: validate inputs at the boundary, call pure functions, and record
provenance next to every result.
"""

import argparse
import csv
import json
import math
import sys
from collections.abc import Sequence
from pathlib import Path

from scientific_starter.growth import doubling_time, specific_growth_rate
from scientific_starter.provenance import write_run_metadata

RESULT_FILENAME = "result.json"
REQUIRED_COLUMNS = ("time_h", "od_blank_corrected")


def read_two_readings(path: Path) -> tuple[tuple[float, float], tuple[float, float]]:
    """Read ``(time_h, od)`` for exactly two readings from a CSV file.

    Raises:
        ValueError: If columns are missing, there are not exactly two rows, or a value
            is not a number. Range checks (positive OD, increasing time) are done by
            :func:`~scientific_starter.growth.specific_growth_rate`.
    """
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = [name for name in REQUIRED_COLUMNS if name not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path.name}: missing column(s) {', '.join(missing)}")
        rows = list(reader)

    if len(rows) != 2:
        raise ValueError(f"{path.name}: expected exactly 2 data rows, found {len(rows)}")

    readings = []
    for line_number, row in enumerate(rows, start=2):
        try:
            readings.append((float(row["time_h"]), float(row["od_blank_corrected"])))
        except (TypeError, ValueError) as error:
            raise ValueError(f"{path.name}, line {line_number}: not a number ({error})") from error
    return readings[0], readings[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m scientific_starter.cli",
        description="Specific growth rate and doubling time from two OD readings.",
    )
    parser.add_argument("input", type=Path, help="CSV with columns time_h, od_blank_corrected")
    parser.add_argument("--out", type=Path, required=True, help="directory for results")
    parser.add_argument("--overwrite", action="store_true", help="replace results already in --out")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the example analysis. Returns a process exit code (0 on success)."""
    args = build_parser().parse_args(argv)

    try:
        (t1_h, od1), (t2_h, od2) = read_two_readings(args.input)
        rate_per_h = specific_growth_rate(od1, od2, t1_h, t2_h)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    # Only positive growth has a doubling time; see growth.doubling_time for the rules.
    doubling_h = doubling_time(rate_per_h) if rate_per_h > 0 else None
    if doubling_h is not None and not math.isfinite(doubling_h):
        doubling_h = None

    result = {
        "specific_growth_rate_per_h": rate_per_h,
        "doubling_time_h": doubling_h,
    }

    try:
        args.out.mkdir(parents=True, exist_ok=True)
        with (args.out / RESULT_FILENAME).open("w" if args.overwrite else "x") as handle:
            json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
        write_run_metadata(
            args.out,
            {"time_unit": "h", "od_column": "od_blank_corrected"},
            input_files=[args.input],
            overwrite=args.overwrite,
        )
    except FileExistsError as error:
        print(f"error: {error.filename} exists; use --overwrite to replace it", file=sys.stderr)
        return 1

    print(f"specific growth rate: {rate_per_h:.6g} per hour")
    if doubling_h is None:
        print("doubling time: not defined (no positive growth)")
    else:
        print(f"doubling time: {doubling_h:.6g} hours")
    print(f"wrote {args.out / RESULT_FILENAME} and run metadata")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
