"""FIXTURE reference solution for the public practice task fixture-temperature (not part of the experiment)."""

from __future__ import annotations

import math
from numbers import Real
from typing import Any

ZERO_CELSIUS_K = 273.15
UNITS = ("C", "F", "K")


def _to_kelvin(value: float, unit: str) -> float:
    if unit == "C":
        return value + ZERO_CELSIUS_K
    if unit == "F":
        return (value - 32.0) * 5.0 / 9.0 + ZERO_CELSIUS_K
    return value


def _from_kelvin(kelvin: float, unit: str) -> float:
    if unit == "C":
        return kelvin - ZERO_CELSIUS_K
    if unit == "F":
        return (kelvin - ZERO_CELSIUS_K) * 9.0 / 5.0 + 32.0
    return kelvin


def convert_temperature(value: Any, from_unit: str, to_unit: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"value must be a number, got {value!r}")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("value must be finite")
    for unit in (from_unit, to_unit):
        if unit not in UNITS:
            raise ValueError(f"unknown unit {unit!r}; use one of {UNITS}")
    kelvin = _to_kelvin(number, from_unit)
    if kelvin < 0:
        raise ValueError("temperature below absolute zero")
    return _from_kelvin(kelvin, to_unit)
