# FIXTURE task: summary statistics (practice task, not part of the experiment)

This public practice task exists only to test the ResearchCode experiment harness. It is
never given to an agent in a genuine trial.

Provide a module importable as **`fixture_summary`** with:

- `summarize(values)`, which returns a mapping with `"mean"`, `"sd"` (sample standard deviation,
  dividing by n − 1), and `"n"`. Raise `ValueError` for fewer than two values or non-finite
  values.
- `main(argv) -> int`, which reads `--input` (a CSV file with a `value` column) and writes the
  summary as JSON to `--output`. Return non-zero, without writing output, on any error or if
  the output file already exists.
