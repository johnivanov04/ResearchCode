"""FIXTURE reference solution for the public practice task fixture-summary (not part of the experiment)."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any


def summarize(values: Sequence[float]) -> dict[str, Any]:
    numbers = [float(v) for v in values]
    if len(numbers) < 2:
        raise ValueError("at least two values are required")
    if not all(math.isfinite(v) for v in numbers):
        raise ValueError("values must be finite")
    return {"mean": statistics.fmean(numbers), "sd": statistics.stdev(numbers), "n": len(numbers)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.output.exists():
        print("error: output exists", file=sys.stderr)
        return 1
    try:
        with args.input.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if not rows or "value" not in rows[0]:
            raise ValueError("missing 'value' column")
        result = summarize([float(row["value"]) for row in rows])
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    args.output.write_text(json.dumps(result), encoding="utf-8")
    return 0
