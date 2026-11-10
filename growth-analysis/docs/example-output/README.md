# Example output (synthetic data)

These folders contain the complete output of `growth-analyze` on the two synthetic sample
datasets in `data/sample/`. They are committed so that you can see what the tool
produces without running it, and the ResearchCode website shows some of these figures.
**The data are synthetic; nothing here is an experimental finding.**

They were produced with PNG figures only, to keep the repository small (the default
also writes SVG):

```bash
uv run growth-analyze --input data/sample/synthetic_plate.csv \
  --output docs/example-output/plate --plot-format png --overwrite
uv run growth-analyze --input data/sample/synthetic_website_example.csv \
  --output docs/example-output/website-example --plot-format png --overwrite
```

`tests/test_example_output.py` reruns these commands and checks that every number in the
tables still matches. If you change the method on purpose, rerun the commands, review the
differences, and commit the new outputs with the code change.

`run_metadata.json` records the run that produced the files exactly as it happened. It
shows the Git commit `bb3aedf` and `"uncommitted_changes": true`, because the outputs were
generated while the Phase 3 code was still uncommitted. So the recorded commit is the one
the work started from, **not** the code that produced the files; that code is the commit
that added these outputs. The record has deliberately not been edited to look like a clean
run: provenance should describe what actually happened. It is an example of the format,
not a released result. For results you intend to keep, commit first, then run, so that the
record shows `"uncommitted_changes": false`.
