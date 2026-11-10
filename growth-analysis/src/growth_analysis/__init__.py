"""Bacterial growth-curve analysis, built from the ResearchCode scientific starter.

The method is specified in ``docs/spec-growth-curve.md``. Most users run the command-line
tool ``growth-analyze``; the functions below are for use from Python.
"""

from growth_analysis.analysis import analyse_plate
from growth_analysis.config import AnalysisConfig
from growth_analysis.exponential import analyse_well, select_exponential_phase
from growth_analysis.provenance import write_run_metadata
from growth_analysis.readings import InputDataError, read_plate
from growth_analysis.regression import fit_line

__all__ = [
    "AnalysisConfig",
    "InputDataError",
    "analyse_plate",
    "analyse_well",
    "fit_line",
    "read_plate",
    "select_exponential_phase",
    "write_run_metadata",
]
