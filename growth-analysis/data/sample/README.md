# Synthetic sample data

**Every value in this folder is synthetic.** The files were generated from mathematical
models with chosen parameters and seeded random noise by `src/growth_analysis/synthetic.py`.
They describe no real organism, strain, medium, or experiment, and must not be cited as
measurements. They exist so that you can try the analysis immediately and so that the
tests can compare results with known answers.

Regenerate both files (the tests check that they match):

```bash
uv run python -m growth_analysis.synthetic --output-dir data/sample --overwrite
```

## `synthetic_plate.csv`

A 12-well plate read every 15 minutes for 16 hours (time in minutes, `time_min`).

| Wells | Condition | Model | Parameters |
| ----- | --------- | ----- | ---------- |
| A1, A2, A3 | `blank` | constant | OD 0.040 |
| B2, B3, B4 | `condition_A` | logistic after a lag | N0 = 0.004, K = 1.0, r = 1.0 per hour, lag 2 h |
| C2, C3, C4 | `condition_B` | logistic after a lag | N0 = 0.010, K = 0.8, r = 0.6 per hour, lag 1 h |
| D2, D3, D4 | `condition_C` | constant (no growth) | N = 0.050 |

Raw OD = blank + N(t) × exp(e1) + e2, with e1 ~ Normal(0, 0.02) (multiplicative noise) and
e2 ~ Normal(0, 0.001) (additive noise), rounded to 3 decimals. Seed: `20261110`. The
condition names are deliberately neutral; they do not stand for real media or treatments.

What to expect from the analysis: r is the logistic model's intrinsic rate, the limit of
the growth rate at vanishing density. The specific growth rate of a logistic curve is
r (1 − N/K), so the rate measured over the exponential phase is somewhat below r. With
noise, individual wells scatter, and for condition_B the estimates are biased upward by
several percent on average (some wells even exceed r). See `docs/spec-growth-curve.md`,
sections 3.3 and 5, and `docs/method-study.md`.

## `synthetic_website_example.csv`

The illustrative well from the ResearchCode website's `/example` page (logistic,
r = 1.2 per hour, N0 = 0.01, K = 1.1, blank 0.045, every 15 minutes for 12 hours, rounded
to 3 decimals with JavaScript's `Math.round`), as well `B3`, plus a blank well `A1`
reading 0.045 throughout. The website's tests check that this file matches the data the
page shows.
