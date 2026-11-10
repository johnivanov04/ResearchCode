"""Shared test configuration.

Hypothesis profiles: the default ("dev") is quick for local runs. CI sets
HYPOTHESIS_PROFILE=ci to try many more random examples on every push.
"""

import os
from collections.abc import Callable, Iterable
from pathlib import Path

import pytest
from hypothesis import settings
from support import Row, csv_text

# deadline=None: timing limits cause flaky failures on busy CI machines without telling us
# anything about correctness.
settings.register_profile("dev", max_examples=200, deadline=None)
settings.register_profile("ci", max_examples=2000, deadline=None, print_blob=True)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))


@pytest.fixture
def write_plate(tmp_path: Path) -> Callable[..., Path]:
    """Write rows (well, condition, time, od600) to a CSV file and return its path."""
    counter = iter(range(1_000_000))

    def write(rows: Iterable[Row], time_column: str = "time_h", name: str | None = None) -> Path:
        path = tmp_path / (name or f"plate_{next(counter)}.csv")
        path.write_text(csv_text(rows, time_column), encoding="utf-8")
        return path

    return write
