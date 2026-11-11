"""Blank correction and quantification limit (section 3.1 of ``docs/spec-growth-curve.md``).

Blank (medium-only) wells measure the optical density of everything except the cells:
medium, plastic, and the instrument's offset. Subtracting it is essential before taking
logarithms, because a constant background flattens ln(OD) and lowers the apparent growth
rate.
"""

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from growth_analysis.config import AnalysisConfig
from growth_analysis.readings import InputDataError, Plate, Well

__all__ = ["BlankSummary", "estimate_blank", "sample_wells"]


@dataclass(frozen=True)
class BlankSummary:
    """The blank value subtracted from every sample reading, and how it was obtained.

    Attributes:
        method: ``"mean"`` or ``"none"``.
        label: Condition label of blank wells.
        wells: Blank well identifiers.
        n_readings: Number of blank readings used.
        value: OD subtracted from every sample reading (0.0 for ``"none"``).
        sd: Sample standard deviation of the blank readings, or ``None`` if fewer than two.
        min_reading, max_reading: Range of the blank readings, or ``None``.
        quantification_limit: Lowest blank-corrected OD used in a fit.
    """

    method: str
    label: str
    wells: tuple[str, ...]
    n_readings: int
    value: float
    sd: float | None
    min_reading: float | None
    max_reading: float | None
    quantification_limit: float

    def to_dict(self) -> dict[str, Any]:
        record = asdict(self)
        record["wells"] = list(self.wells)
        return record


def sample_wells(plate: Plate, config: AnalysisConfig) -> list[Well]:
    """Wells that are analysed: every well whose condition is not the blank label."""
    return [well for well in plate.wells if well.condition != config.blank_label]


def estimate_blank(plate: Plate, config: AnalysisConfig) -> tuple[BlankSummary, list[str]]:
    """Estimate the blank and quantification limit for a plate.

    Returns:
        The blank summary, and a list of warnings for the results file.

    Raises:
        InputDataError: If there are no sample wells, or ``blank_method`` is ``"mean"`` and
            there are no blank wells.
    """
    warnings: list[str] = []
    blanks = plate.by_condition(config.blank_label)
    if not sample_wells(plate, config):
        raise InputDataError(
            plate.source_name,
            [f"no sample wells: every well has the blank label {config.blank_label!r}"],
        )

    if config.blank_method == "none":
        if blanks:
            warnings.append(
                f"{len(blanks)} blank well(s) labelled {config.blank_label!r} were not "
                "subtracted because blank_method is 'none' (values treated as already "
                "blank-corrected); they are not analysed"
            )
        return (
            BlankSummary(
                method="none",
                label=config.blank_label,
                wells=tuple(well.well for well in blanks),
                n_readings=0,
                value=0.0,
                sd=None,
                min_reading=None,
                max_reading=None,
                quantification_limit=config.min_od,
            ),
            warnings,
        )

    if not blanks:
        raise InputDataError(
            plate.source_name,
            [
                f"no blank wells (condition {config.blank_label!r}) to subtract; add blank "
                "wells, set the blank label, or use blank_method 'none' if the OD values are "
                "already blank-corrected"
            ],
        )

    readings = np.concatenate([well.od600 for well in blanks])
    value = float(np.mean(readings))
    sd = float(np.std(readings, ddof=1)) if readings.size >= 2 else None
    quantification_limit = config.min_od
    if sd is not None:
        quantification_limit = max(config.min_od, config.blank_sd_multiple * sd)
    if readings.size < 2:
        warnings.append(
            "only one blank reading: its variability is unknown, so the quantification limit is "
            "min_od alone"
        )
    return (
        BlankSummary(
            method="mean",
            label=config.blank_label,
            wells=tuple(well.well for well in blanks),
            n_readings=int(readings.size),
            value=value,
            sd=sd,
            min_reading=float(np.min(readings)),
            max_reading=float(np.max(readings)),
            quantification_limit=quantification_limit,
        ),
        warnings,
    )
