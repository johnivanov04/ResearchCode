"""Analysis settings, with the defaults and valid ranges from ``docs/spec-growth-curve.md``.

Every setting that changes a result lives here, so the complete configuration of a run can
be printed, recorded in ``results.json`` and ``run_metadata.json``, and reproduced.
"""

import math
from dataclasses import asdict, dataclass
from typing import Any, Literal

__all__ = ["QUANTIFICATION_LIMIT_BLANK_SDS", "AnalysisConfig", "BlankMethod"]

BlankMethod = Literal["mean", "none"]

# Default for AnalysisConfig.blank_sd_multiple: the quantification limit is at least this many
# standard deviations of the blank readings. Three SDs is a common convention for *detecting*
# a signal; ten SDs is a common convention for *quantifying* one (noise about 10% of the
# value). Growth rates are slopes of ln(OD), and the noise in ln(OD) is roughly SD / OD, so
# readings close to the blank are very noisy on a log scale and the window search is drawn to
# them. scripts/method_study.py shows the resulting overestimate with three SDs on the
# synthetic sample plate (docs/spec-growth-curve.md, section 3.3).
QUANTIFICATION_LIMIT_BLANK_SDS = 10.0


@dataclass(frozen=True)
class AnalysisConfig:
    """Settings for one analysis run. See section 2.2 of the specification.

    Attributes:
        blank_method: ``"mean"`` subtracts the mean of all blank-well readings; ``"none"``
            means OD values are already blank-corrected.
        blank_label: Condition label that identifies blank (medium-only) wells.
        min_od: Lowest blank-corrected OD used in a fit.
        blank_sd_multiple: The quantification limit is the larger of ``min_od`` and this many
            standard deviations of the blank readings (see the comment on
            ``QUANTIFICATION_LIMIT_BLANK_SDS``).
        max_od: Optional upper limit of the instrument's linear range, as blank-corrected
            OD. ``None`` applies no upper limit.
        window_points: Number of consecutive readings in each sliding window (at least 3,
            so that every window fit has a residual degree of freedom).
        min_relative_rate: A window belongs to the exponential phase if its slope is at
            least this fraction of the steepest window's slope.
        min_fold_change: Smallest fold change in OD across the fitted interval for a
            result to count as growth (2.0 means at least one doubling).
        min_r_squared: Credibility threshold for the coefficient of determination.
        max_relative_se: Credibility threshold for SE(mu) / mu.
        reference_condition: Optional condition that other conditions are compared with.
    """

    blank_method: BlankMethod = "mean"
    blank_label: str = "blank"
    min_od: float = 0.005
    blank_sd_multiple: float = QUANTIFICATION_LIMIT_BLANK_SDS
    max_od: float | None = None
    window_points: int = 5
    min_relative_rate: float = 0.8
    min_fold_change: float = 2.0
    min_r_squared: float = 0.98
    max_relative_se: float = 0.10
    reference_condition: str | None = None

    def __post_init__(self) -> None:
        if self.blank_method not in ("mean", "none"):
            raise ValueError(f"blank_method must be 'mean' or 'none', got {self.blank_method!r}")
        if not self.blank_label.strip():
            raise ValueError("blank_label must not be empty")
        _require_finite("min_od", self.min_od)
        if self.min_od <= 0:
            raise ValueError(f"min_od must be > 0, got {self.min_od!r}")
        _require_finite("blank_sd_multiple", self.blank_sd_multiple)
        if self.blank_sd_multiple < 0:
            raise ValueError(f"blank_sd_multiple must be >= 0, got {self.blank_sd_multiple!r}")
        if self.max_od is not None:
            _require_finite("max_od", self.max_od)
            if self.max_od <= self.min_od:
                raise ValueError(f"max_od ({self.max_od!r}) must be greater than min_od")
        if isinstance(self.window_points, bool) or not isinstance(self.window_points, int):
            raise TypeError("window_points must be an integer")
        if self.window_points < 3:
            raise ValueError(f"window_points must be at least 3, got {self.window_points}")
        _require_finite("min_relative_rate", self.min_relative_rate)
        if not 0 < self.min_relative_rate <= 1:
            raise ValueError(f"min_relative_rate must be in (0, 1], got {self.min_relative_rate!r}")
        _require_finite("min_fold_change", self.min_fold_change)
        if self.min_fold_change <= 1:
            raise ValueError(f"min_fold_change must be > 1, got {self.min_fold_change!r}")
        _require_finite("min_r_squared", self.min_r_squared)
        if not 0 <= self.min_r_squared <= 1:
            raise ValueError(f"min_r_squared must be in [0, 1], got {self.min_r_squared!r}")
        _require_finite("max_relative_se", self.max_relative_se)
        if self.max_relative_se <= 0:
            raise ValueError(f"max_relative_se must be > 0, got {self.max_relative_se!r}")
        if self.reference_condition is not None and not self.reference_condition.strip():
            raise ValueError("reference_condition must not be empty")

    def to_dict(self) -> dict[str, Any]:
        """Return the settings as a JSON-serialisable dictionary."""
        return asdict(self)


def _require_finite(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"{name} must be a number, got {type(value).__name__}")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite, got {value!r}")
