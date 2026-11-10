"""Run the complete analysis on a validated plate: blank, every well, conditions."""

from growth_analysis.blank import estimate_blank, sample_wells
from growth_analysis.compare import summarise_conditions
from growth_analysis.config import AnalysisConfig
from growth_analysis.exponential import CREDIBILITY_FLAGS, analyse_well
from growth_analysis.readings import Plate
from growth_analysis.report import AnalysisOutput

__all__ = ["analyse_plate"]


def analyse_plate(plate: Plate, config: AnalysisConfig) -> AnalysisOutput:
    """Analyse every sample well of ``plate`` and summarise by condition.

    Raises:
        InputDataError: If blank correction is impossible (see ``estimate_blank``).
        ValueError: If the reference condition does not exist.
    """
    blank, warnings = estimate_blank(plate, config)
    wells = tuple(analyse_well(well, blank, config) for well in sample_wells(plate, config))
    conditions = tuple(summarise_conditions(wells, config.reference_condition))
    if plate.ignored_columns:
        warnings.append(f"ignored column(s): {', '.join(plate.ignored_columns)}")
    for result in wells:
        if result.status == "growth" and not result.credible:
            failed = ", ".join(flag for flag in result.flags if flag in CREDIBILITY_FLAGS)
            warnings.append(f"well {result.well}: growth rate is not credible ({failed})")
        elif result.status != "growth":
            warnings.append(f"well {result.well}: {result.status.replace('_', ' ')}")
    return AnalysisOutput(
        source_name=plate.source_name,
        time_column=plate.time_column,
        ignored_columns=plate.ignored_columns,
        config=config,
        blank=blank,
        wells=wells,
        conditions=conditions,
        warnings=tuple(warnings),
    )
