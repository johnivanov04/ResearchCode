# FIXTURE task: temperature conversion (practice task, not part of the experiment)

This public practice task exists only to test the ResearchCode experiment harness. It is
never given to an agent in a genuine trial.

Provide a module importable as **`fixture_temperature`** (a file or package, in this directory
or in `src/`) with `convert_temperature(value, from_unit, to_unit) -> float`. Units are `"C"`,
`"F"`, and `"K"`. Raise `ValueError` for unknown units, non-finite values, and temperatures
below absolute zero. A non-number may raise `ValueError` or `TypeError`.
