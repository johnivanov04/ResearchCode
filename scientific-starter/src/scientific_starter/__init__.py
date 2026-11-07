"""Scientific starter package.

Replace this description, and the example modules, with your own analysis code.
Keep scientific calculations in small, pure functions (like those in ``growth.py``)
so that they are easy to test against known answers.
"""

from scientific_starter.growth import doubling_time, specific_growth_rate
from scientific_starter.provenance import write_run_metadata

__all__ = ["doubling_time", "specific_growth_rate", "write_run_metadata"]
