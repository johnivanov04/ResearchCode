"""Read and validate optical density measurements from a CSV file.

The file format and every validation rule are specified in section 2.1 of
``docs/spec-growth-curve.md``. In short: one row per reading, with columns ``well``,
``condition``, ``od600``, and exactly one time column whose name states the unit
(``time_h``, ``time_min``, or ``time_s``).

Invalid data is never dropped or repaired. Every problem found is collected, with its line
number, and reported together in one :class:`InputDataError`, so a researcher can fix the
file in one pass.
"""

import csv
import math
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

__all__ = [
    "REQUIRED_COLUMNS",
    "TIME_COLUMNS",
    "InputDataError",
    "Plate",
    "Well",
    "read_plate",
]

REQUIRED_COLUMNS = ("well", "condition", "od600")
# Accepted time columns and the factor that converts each to hours.
TIME_COLUMNS = {"time_h": 1.0, "time_min": 1.0 / 60.0, "time_s": 1.0 / 3600.0}
# Column names that suggest time but do not state a unit.
_AMBIGUOUS_TIME_COLUMNS = ("time", "t", "elapsed", "timepoint")
# Report at most this many problems; a badly malformed file would otherwise flood the screen.
MAX_REPORTED_PROBLEMS = 50


class InputDataError(ValueError):
    """The input file is not valid. ``problems`` lists every issue found."""

    def __init__(self, source: str, problems: list[str]) -> None:
        self.source = source
        self.problems = problems
        shown = problems[:MAX_REPORTED_PROBLEMS]
        lines = [f"{source}: {len(problems)} problem(s) in the input data:"]
        lines += [f"  - {problem}" for problem in shown]
        if len(problems) > len(shown):
            lines.append(f"  ... and {len(problems) - len(shown)} more")
        super().__init__("\n".join(lines))


@dataclass(frozen=True)
class Well:
    """Readings from one well, in time order.

    Attributes:
        well: Well identifier, as in the input file.
        condition: Experimental condition (or the blank label).
        time_h: Times in hours, strictly increasing.
        od600: OD600 values as read from the file (raw, or already blank-corrected).
        lines: Line numbers in the input file, for error messages and traceability.
    """

    well: str
    condition: str
    time_h: np.ndarray
    od600: np.ndarray
    lines: tuple[int, ...]


@dataclass(frozen=True)
class Plate:
    """All wells from one input file, in order of first appearance."""

    source_name: str
    time_column: str
    wells: tuple[Well, ...]
    ignored_columns: tuple[str, ...] = field(default=())

    def by_condition(self, condition: str) -> list[Well]:
        return [well for well in self.wells if well.condition == condition]

    @property
    def conditions(self) -> list[str]:
        """Conditions in order of first appearance."""
        return list(dict.fromkeys(well.condition for well in self.wells))


def _parse_number(text: str | None, column: str, line: int, problems: list[str]) -> float:
    """Parse a finite number, or record a problem and return NaN."""
    if text is None or not text.strip():
        problems.append(f"line {line}: {column} is missing")
        return math.nan
    try:
        value = float(text)
    except ValueError:
        problems.append(f"line {line}: {column} is not a number ({text.strip()!r})")
        return math.nan
    if not math.isfinite(value):
        problems.append(f"line {line}: {column} must be finite, got {text.strip()!r}")
        return math.nan
    return value


def _choose_time_column(fieldnames: list[str], problems: list[str]) -> str | None:
    present = [name for name in TIME_COLUMNS if name in fieldnames]
    if len(present) == 1:
        return present[0]
    if len(present) > 1:
        problems.append(
            f"more than one time column ({', '.join(present)}); keep exactly one so the "
            "unit is unambiguous"
        )
        return None
    ambiguous = [name for name in fieldnames if name.lower() in _AMBIGUOUS_TIME_COLUMNS]
    hint = (
        f"; column {ambiguous[0]!r} does not state its unit, rename it to time_h, "
        "time_min, or time_s"
        if ambiguous
        else ""
    )
    problems.append(f"missing time column (one of {', '.join(TIME_COLUMNS)}){hint}")
    return None


def _rows(handle: Iterator[str]) -> tuple[list[str], list[tuple[int, list[str]]]]:
    reader = csv.reader(handle)
    try:
        header = next(reader)
    except StopIteration:
        return [], []
    rows = []
    for fields in reader:
        if not fields or all(not value.strip() for value in fields):
            continue  # Blank lines carry no data; they are not measurements.
        rows.append((reader.line_num, fields))
    return [name.strip() for name in header], rows


def read_plate(path: str | Path) -> Plate:
    """Read and validate a plate CSV file.

    Args:
        path: CSV file in the format of section 2.1 of the specification.

    Returns:
        The validated plate, with times converted to hours.

    Raises:
        InputDataError: If anything in the file is invalid. Its message lists every
            problem with its line number.
        OSError: If the file cannot be read.
    """
    path = Path(path)
    # utf-8-sig also accepts the byte-order mark that spreadsheet programs often add.
    with path.open(newline="", encoding="utf-8-sig") as handle:
        header, rows = _rows(handle)

    problems: list[str] = []
    if not header:
        raise InputDataError(path.name, ["the file is empty (no header row)"])

    duplicates = sorted({name for name in header if header.count(name) > 1})
    if duplicates:
        problems.append(f"duplicate column name(s): {', '.join(duplicates)}")
    missing = [name for name in REQUIRED_COLUMNS if name not in header]
    if missing:
        problems.append(f"missing required column(s): {', '.join(missing)}")
    time_column = _choose_time_column(header, problems)
    if problems or time_column is None:
        raise InputDataError(path.name, problems)
    if not rows:
        raise InputDataError(path.name, ["the file has a header but no data rows"])
    to_hours = TIME_COLUMNS[time_column]
    index = {name: header.index(name) for name in (*REQUIRED_COLUMNS, time_column)}
    known = {*REQUIRED_COLUMNS, *TIME_COLUMNS}
    ignored = tuple(name for name in header if name not in known)

    # Group readings by well, keeping file order.
    grouped: dict[str, dict[str, list]] = {}
    for line, fields in rows:
        if len(fields) != len(header):
            problems.append(f"line {line}: expected {len(header)} fields, found {len(fields)}")
            continue
        well = fields[index["well"]].strip()
        condition = fields[index["condition"]].strip()
        if not well:
            problems.append(f"line {line}: well is missing")
        if not condition:
            problems.append(f"line {line}: condition is missing")
        time = _parse_number(fields[index[time_column]], time_column, line, problems)
        od = _parse_number(fields[index["od600"]], "od600", line, problems)
        if not well or not condition:
            continue
        entry = grouped.setdefault(well, {"conditions": [], "time": [], "od": [], "lines": []})
        entry["conditions"].append((line, condition))
        entry["time"].append(time)
        entry["od"].append(od)
        entry["lines"].append(line)

    wells = []
    for well, entry in grouped.items():
        conditions = dict.fromkeys(condition for _, condition in entry["conditions"])
        if len(conditions) > 1:
            problems.append(
                f"well {well!r} appears under more than one condition: "
                f"{', '.join(repr(c) for c in conditions)}"
            )
        _check_times(well, entry["time"], entry["lines"], problems)
        wells.append(
            Well(
                well=well,
                condition=next(iter(conditions)),
                time_h=np.asarray(entry["time"], dtype=float) * to_hours,
                od600=np.asarray(entry["od"], dtype=float),
                lines=tuple(entry["lines"]),
            )
        )

    if problems:
        raise InputDataError(path.name, problems)
    return Plate(
        source_name=path.name,
        time_column=time_column,
        wells=tuple(wells),
        ignored_columns=ignored,
    )


def _check_times(well: str, times: list[float], lines: list[int], problems: list[str]) -> None:
    """Report duplicate times and times that do not increase, within one well."""
    first_line_at: dict[float, int] = {}
    previous: tuple[float, int] | None = None
    for time, line in zip(times, lines, strict=True):
        if math.isnan(time):
            continue  # Already reported as unparseable.
        if time in first_line_at:
            problems.append(
                f"line {line}: duplicate measurement for well {well!r} at time {time:g} "
                f"(also on line {first_line_at[time]})"
            )
        else:
            first_line_at[time] = line
            if previous is not None and time < previous[0]:
                problems.append(
                    f"line {line}: time {time:g} for well {well!r} is earlier than "
                    f"{previous[0]:g} on line {previous[1]}; sort readings by time"
                )
        if previous is None or time > previous[0]:
            previous = (time, line)
