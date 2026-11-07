# Specification: specific growth rate and doubling time from two readings

Status: implemented
Owner: replace with the person responsible for the scientific decisions
Implemented in: `src/scientific_starter/growth.py` (`specific_growth_rate`, `doubling_time`)
Tested in: `tests/test_growth.py`, `tests/test_growth_properties.py`

This is a completed example of `docs/SPEC_TEMPLATE.md`. It is intentionally small: it
covers two readings, not a full growth-curve analysis.

## 1. Scientific objective

Compute the specific growth rate mu of a bacterial culture between two optical density
readings taken during exponential growth, and the corresponding doubling time. These
summarise how fast the culture grows under the conditions tested.

## 2. Inputs

| Name   | Type  | Units         | Valid values                      | Notes                                         |
| ------ | ----- | ------------- | --------------------------------- | --------------------------------------------- |
| `od1`  | float | dimensionless | finite, > 0                       | Blank-corrected OD at `t1_h`                  |
| `od2`  | float | dimensionless | finite, > 0                       | Blank-corrected OD at `t2_h`                  |
| `t1_h` | float | hours         | finite                            | Any origin; may be negative                   |
| `t2_h` | float | hours         | finite, strictly greater than `t1_h` | Convert minutes or seconds to hours first |

Accepted number types: `int`, `float`, `fractions.Fraction`, `decimal.Decimal`, and NumPy
numeric scalars. `bool` is rejected even though Python treats it as an integer.

Input file format for the example command (`python -m scientific_starter.cli`): CSV, comma
delimiter, header row `time_h,od_blank_corrected`, exactly two data rows in time order.

## 3. Method and mathematical assumptions

1. mu = ln(od2 / od1) / (t2_h - t1_h), using the natural logarithm.
2. If mu > 0, the doubling time is Td = ln(2) / mu.

Assumptions:

- The culture grows exponentially between the two readings: N(t) = N0 * exp(mu * t).
- Optical density is proportional to cell density over the range of the two readings (the
  instrument's linear range).
- Both readings have had the same medium blank subtracted.
- Choosing two readings that lie in the exponential phase is done by the researcher. This
  function cannot detect lag or stationary phase.

Implementation note (numerical method, not a scientific choice): ln(od2 / od1) is computed
as `log1p((od2 - od1) / od1)` when the readings are within a factor of two of each other,
and as `log(od2) - log(od1)` otherwise. Both are mathematically equal to ln(od2 / od1).
This keeps the result accurate and its sign correct for any positive finite inputs; the
reasons are explained in the code and tested in section 8.

## 4. Output

| Name                   | Type  | Units | Meaning                                       |
| ---------------------- | ----- | ----- | --------------------------------------------- |
| `specific_growth_rate` | float | 1/h   | mu; positive for growth, negative for decline |
| `doubling_time`        | float | hours | ln(2) / mu, for mu > 0                         |

Special cases:

- `od2 == od1`: mu is exactly `0.0`.
- mu < 0 (OD decreased): the negative value is returned, not hidden or clipped. It may be
  real (death, lysis) or a measurement problem that a person should look at.
- `doubling_time(0.0)` returns `math.inf`: a population that does not grow never doubles.
  No tolerance is applied; deciding what counts as "no growth" in noisy data is a
  scientific decision for the analysis that calls this function.
- `doubling_time` of a negative rate raises `ValueError`. A halving time, if needed, must
  be computed explicitly as ln(2) / |mu| so that the choice is visible.

## 5. Known-answer examples

| Inputs (`od1`, `od2`, `t1_h`, `t2_h`) | Expected mu (1/h)         | Expected Td (h) | Source                         |
| ------------------------------------- | ------------------------- | --------------- | ------------------------------ |
| 0.1, 0.2, 0, 2                        | ln(2) / 2 = 0.34657359... | 2               | One doubling in 2 h            |
| 0.05, 0.5, 0, 1                       | ln(10) = 2.30258509...    | ln(2) / ln(10) | Ten-fold increase in 1 h      |
| 1, 8, 0, 3                            | ln(2) = 0.69314718...     | 1               | Three doublings in 3 h         |
| 0.1, 0.2, 10, 12                      | ln(2) / 2                 | 2               | Only the interval matters      |
| 0.4, 0.2, 0, 2                        | -ln(2) / 2                | undefined       | Halving in 2 h                 |
| 0.37, 0.37, 0, 5                      | 0                         | infinity        | No change                      |

All expected values follow directly from the formula in section 3.

## 6. Edge cases and invalid input

| Case                                              | Required behaviour                  |
| ------------------------------------------------- | ----------------------------------- |
| `od1` or `od2` is 0 or negative (including -0.0)  | `ValueError` ("must be > 0")       |
| Any input is NaN, +inf, or -inf                   | `ValueError` ("must be finite")    |
| Any input is not a real number, or is a `bool`    | `TypeError`                         |
| `t2_h == t1_h` or `t2_h < t1_h`                   | `ValueError` ("must be later")     |
| `t2_h - t1_h` overflows to infinity               | `ValueError`                        |
| Interval so short the rate is not a finite float  | `ValueError`                        |
| `od2` is the next representable float after `od1` | Correct sign and value, not 0       |
| Extremely small positive mu                       | `doubling_time` may return `inf`   |
| Time given in minutes instead of hours            | Cannot be detected: returns a rate per minute. The input is named `t1_h`/`t2_h` and documented to prevent this. |

## 7. Numerical tolerances

- Known-answer tests use a relative tolerance of 1e-12. The inputs (0.1, 0.2, ...) are not
  exactly representable in binary floating point, so results can differ from the exact
  value by a few units in the last place (about 1e-16 relative). 1e-12 leaves a large
  margin for different platforms while any formula error would be far larger. For example,
  the reference case gives Td = 2.0000000000000004, not exactly 2.
- Property tests derive their tolerance from how errors propagate through the calculation
  (a few times machine epsilon, scaled by the size of the logarithms and the interval),
  and compare against a 50-digit `decimal` reference rather than against the code itself.
- Scientific tolerance: not applicable to this function. Measurement precision (OD is
  typically reported to three decimals) is far coarser than the numerical error.

## 8. Properties that must always hold

For all valid inputs:

- Data generated from an exact exponential with rate mu gives back mu.
- The result agrees with a 50-digit reference calculation of ln(od2/od1) / (t2 - t1).
- Swapping the two readings negates the rate; the sign matches the direction of change.
- Multiplying both ODs by the same constant does not change the rate (units of OD do not
  matter).
- Shifting both times by the same amount does not change the rate.
- Rates over consecutive intervals combine into the rate over the whole interval as a
  time-weighted average.
- Doubling the OD over an interval T gives a doubling time of T.
- `doubling_time(mu) * mu == ln(2)`; a faster rate gives a shorter doubling time.

## 9. Reproducibility requirements

- Record the input file checksum and the parameters (time unit, OD column) with every
  result. The example command does this with `write_run_metadata`.
- Input files are read, never modified.
- No randomness is involved, so no seed is needed.

## 10. Out of scope

- Selecting the exponential phase, fitting more than two points, or estimating the
  maximum growth rate over a full curve.
- Blank subtraction, replicate handling, and unit conversion.
- Detecting non-linear instrument response at high OD.

## 11. Acceptance criteria

- [x] Every known-answer example in section 5 is an automated test, and passes.
- [x] Every edge case in section 6 is an automated test, and passes.
- [x] Every property in section 8 is a property-based test, and passes.
- [x] Inputs are validated as described in section 2; invalid input raises a clear error.
- [x] Units appear in names or docstrings of all inputs and outputs.
- [x] `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest` pass.
- [ ] A person responsible for the science has reviewed the method and the tests.
