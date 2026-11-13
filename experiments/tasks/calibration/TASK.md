# Task: calibration curve and inverse prediction

An analytical lab measures standards of known concentration on an instrument (for
example absorbance in a colorimetric assay), fits a straight calibration line, and then
estimates the concentrations of unknown samples from their instrument responses. It
needs a small, reliable Python module that does this with honest uncertainty.

## Deliverable

A Python module importable as **`calibration`**: either a file `calibration.py` or a package
`calibration/`, placed in this directory or in `src/` inside this directory. It must
provide the two functions below with exactly these names and parameters.

The module will be imported and called by an automated evaluator running **Python 3.12**
with only the **standard library, NumPy, and SciPy** installed. Do not depend on any other
package at run time. The functions must not read or write files and must not modify
their arguments.

## Definitions

The standards are n pairs (xᵢ, yᵢ): xᵢ is a known concentration and yᵢ the measured
response. Fit the line y = a + b·x by ordinary least squares (unweighted), with
intercept a and slope b. Then:

- x̄ and ȳ are the means of the xᵢ and yᵢ; Sxx = Σ (xᵢ − x̄)².
- SSR = Σ (yᵢ − a − b·xᵢ)² is the residual sum of squares, and SST = Σ (yᵢ − ȳ)².
- The residual standard deviation is s = √(SSR / (n − 2)).
- R² = 1 − SSR / SST.
- The limit of detection is LOD = 3.3 · s / b and the limit of quantification is
  LOQ = 10 · s / b, both in concentration units.

For an unknown sample measured m times with mean response ȳ₀ (m ≥ 1):

- the estimated concentration is x₀ = (ȳ₀ − a) / b;
- its standard error is

      SE(x₀) = (s / b) · √( 1/m + 1/n + (ȳ₀ − ȳ)² / (b² · Sxx) )

- the confidence interval at confidence level C is x₀ ± t · SE(x₀), where t is the
  (1 + C)/2 quantile of Student's t distribution with n − 2 degrees of freedom.

Use numerically stable computations: concentrations may have a large offset relative to
their spread.

## Input rules

- `concentrations` and `responses` are sequences (lists, tuples, or 1-D NumPy arrays) of
  equal length n ≥ 3 containing finite numbers. Concentrations must be ≥ 0, and at least
  two concentrations must differ. Replicate standards (repeated concentrations) are
  allowed and each counts as a separate point.
- The fitted slope must be positive (the response increases with concentration);
  otherwise raise `ValueError`.
- Any violation raises `ValueError`. This includes NaN or infinite values, unequal
  lengths, too few points, and negative concentrations.

## Functions

### 1. `fit_calibration(concentrations, responses)`

Return a mapping (a `dict`, or an object with these attributes) with:

| Field | Meaning |
| --- | --- |
| `"slope"` | b |
| `"intercept"` | a |
| `"r_squared"` | R² |
| `"residual_sd"` | s |
| `"n"` | number of standards (an `int`) |
| `"lod"` | 3.3 · s / b |
| `"loq"` | 10 · s / b |

### 2. `inverse_predict(concentrations, responses, unknown_responses, confidence=0.95)`

Fit the calibration line to the standards as in function 1 (same validation), then
estimate the concentration of one unknown sample from its replicate responses
`unknown_responses` (a non-empty sequence of finite numbers). `confidence` must satisfy
0 < confidence < 1.

Return a mapping (or an object with these attributes) with:

| Field | Meaning |
| --- | --- |
| `"concentration"` | x₀. Report it as computed, even if it is negative; do not clip it. |
| `"standard_error"` | SE(x₀) |
| `"ci_low"`, `"ci_high"` | the confidence interval x₀ ∓ t · SE(x₀) |
| `"extrapolated"` | `True` if x₀ is below the smallest or above the largest standard concentration, else `False` (a `bool`) |
| `"below_lod"` | `True` if x₀ < LOD, else `False` (a `bool`) |

Raise `ValueError` for invalid standards (as in function 1), an empty or non-finite
`unknown_responses`, or an invalid `confidence`.

## Public examples

`public_examples.json` lists example calls and their expected results. They are
illustrative, not a complete test of the requirements.
