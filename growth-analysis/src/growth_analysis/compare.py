"""Summaries of growth rates across replicate wells and conditions (section 3.5 of the spec).

Only credible ``growth`` results enter the statistics. Every other well is listed with its
status, so nothing disappears from the summary without a trace. The comparison is
descriptive: no significance tests are performed. Choosing and justifying a statistical
test (and the experimental unit for it) is a scientific decision left to the researcher.
"""

import math
import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from growth_analysis.exponential import CREDIBILITY_FLAGS, WellResult

__all__ = ["ConditionSummary", "summarise_conditions"]


@dataclass(frozen=True)
class ConditionSummary:
    """Descriptive statistics of credible growth rates for one condition (1/h, h)."""

    condition: str
    n_wells: int
    n_credible: int
    mean_growth_rate_per_h: float | None
    sd_growth_rate_per_h: float | None
    sem_growth_rate_per_h: float | None
    min_growth_rate_per_h: float | None
    max_growth_rate_per_h: float | None
    doubling_time_of_mean_rate_h: float | None
    ratio_to_reference: float | None
    status_counts: dict[str, int]
    wells_not_included: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "condition": self.condition,
            "n_wells": self.n_wells,
            "n_credible": self.n_credible,
            "mean_growth_rate_per_h": self.mean_growth_rate_per_h,
            "sd_growth_rate_per_h": self.sd_growth_rate_per_h,
            "sem_growth_rate_per_h": self.sem_growth_rate_per_h,
            "min_growth_rate_per_h": self.min_growth_rate_per_h,
            "max_growth_rate_per_h": self.max_growth_rate_per_h,
            "doubling_time_of_mean_rate_h": self.doubling_time_of_mean_rate_h,
            "ratio_to_reference": self.ratio_to_reference,
            "status_counts": dict(self.status_counts),
            "wells_not_included": dict(self.wells_not_included),
        }


def _reason_not_included(result: WellResult) -> str:
    if result.status != "growth":
        return result.status
    failed = [flag for flag in result.flags if flag in CREDIBILITY_FLAGS]
    return "not credible: " + ", ".join(failed)


def summarise_conditions(
    results: Sequence[WellResult], reference_condition: str | None = None
) -> list[ConditionSummary]:
    """Summarise well results by condition, in order of first appearance.

    Raises:
        ValueError: If ``reference_condition`` is given but no well has that condition.
    """
    conditions = list(dict.fromkeys(result.condition for result in results))
    if reference_condition is not None and reference_condition not in conditions:
        raise ValueError(
            f"reference condition {reference_condition!r} not found; conditions are: "
            f"{', '.join(conditions)}"
        )

    means: dict[str, float | None] = {}
    rows = []
    for condition in conditions:
        wells = [r for r in results if r.condition == condition]
        rates = [
            r.growth_rate_per_h for r in wells if r.credible and r.growth_rate_per_h is not None
        ]
        counts: dict[str, int] = {}
        for r in wells:
            counts[r.status] = counts.get(r.status, 0) + 1
        mean = statistics.fmean(rates) if rates else None
        sd = statistics.stdev(rates) if len(rates) >= 2 else None
        means[condition] = mean
        rows.append(
            {
                "condition": condition,
                "n_wells": len(wells),
                "n_credible": len(rates),
                "mean_growth_rate_per_h": mean,
                "sd_growth_rate_per_h": sd,
                "sem_growth_rate_per_h": sd / math.sqrt(len(rates)) if sd is not None else None,
                "min_growth_rate_per_h": min(rates) if rates else None,
                "max_growth_rate_per_h": max(rates) if rates else None,
                "doubling_time_of_mean_rate_h": (
                    math.log(2.0) / mean if mean is not None and mean > 0 else None
                ),
                "status_counts": counts,
                "wells_not_included": {
                    r.well: _reason_not_included(r) for r in wells if not r.credible
                },
            }
        )

    reference_mean = means.get(reference_condition) if reference_condition else None
    summaries = []
    for row in rows:
        mean = row["mean_growth_rate_per_h"]
        ratio = mean / reference_mean if mean is not None and reference_mean else None
        summaries.append(ConditionSummary(**row, ratio_to_reference=ratio))
    return summaries
