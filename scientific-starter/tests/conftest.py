"""Shared test configuration.

Hypothesis profiles: the default ("dev") is quick for local runs. CI sets
HYPOTHESIS_PROFILE=ci to try many more random examples on every push.
"""

import os

from hypothesis import settings

# deadline=None: these functions are fast, and timing limits cause flaky failures on
# busy CI machines without telling us anything about correctness.
settings.register_profile("dev", max_examples=200, deadline=None)
settings.register_profile("ci", max_examples=2000, deadline=None, print_blob=True)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))
