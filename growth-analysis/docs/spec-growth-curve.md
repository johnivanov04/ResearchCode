# Specification: growth-curve analysis

Status: implemented
Owner: the ResearchCode project team (scientific decisions must be reviewed by a person)
Implemented in: `src/growth_analysis/` (`readings.py`, `blank.py`, `regression.py`,
`exponential.py`, `compare.py`, `cli.py`)
Tested in: `tests/`

This specification was written from `docs/SPEC_TEMPLATE.md` before the code. It refines
the example specification in the ResearchCode guide "Writing specifications" (steepest
five-point window with R² ≥ 0.98) for one documented reason, explained in section 3.3.

## 1. Scientific objective

For each culture (microplate well), estimate the **specific growth rate during exponential
growth**, μ (1/h), and the **doubling time**, Td = ln 2 / μ (h), from optical density
(OD600) readings over time, and summarise the estimates for each experimental condition.

μ is reported as the slope of a least-squares line through ln(blank-corrected OD) over the
exponential phase that the method identifies. It is an average rate over that interval.
For data that follow a logistic model, it is *not* the logistic model's intrinsic rate
parameter r, which is the limit of the growth rate at vanishing density; on such data the
estimate is always somewhat below r (section 5).

## 2. Inputs

### 2.1 Input file

A CSV file (UTF-8, comma-separated, header row) in long format: one row per reading.

| Column | Required | Type | Units | Valid values |
| ------ | -------- | ---- | ----- | ------------ |
| `well` | yes | text | — | Non-empty. Identifies one culture. |
| `condition` | yes | text | — | Non-empty. Wells with the same condition are replicates. Blank (medium-only) wells use the label `blank` (configurable). |
| exactly one of `time_h`, `time_min`, `time_s` | yes | number | hours, minutes, or seconds, as named | Finite. Converted to hours. |
| `od600` | yes | number | dimensionless (absorbance) | Finite. Raw instrument values unless `--blank-method none`. |

Other columns are allowed, ignored, and listed in `results.json`.

Validation (all problems are reported together, with line numbers; nothing is dropped):

- Missing required column, or no time column, or more than one time column (the unit would
  be ambiguous): error. A column named plainly `time` is rejected with a message asking
  for the unit.
- Empty cell, a value that is not a number, NaN, or infinity: error.
- A row with more or fewer fields than the header: error.
- The same well with two readings at the same time (duplicate measurement): error.
- Within a well, times not strictly increasing in file order: error.
- A well that appears under more than one condition: error.
- No sample (non-blank) wells: error.

### 2.2 Analysis settings

| Setting | Default | Valid values | Meaning |
| ------- | ------- | ------------ | ------- |
| `blank_method` | `mean` | `mean`, `none` | `mean`: subtract the mean of all blank-well readings. `none`: OD values are already blank-corrected. |
| `blank_label` | `blank` | non-empty text | Condition label of blank wells. |
| `min_od` | 0.005 | > 0 | Lowest blank-corrected OD used in a fit. |
| `blank_sd_multiple` | 10 | ≥ 0 | The quantification limit is at least this many blank standard deviations. |
| `max_od` | none | > `min_od` or none | Optional upper limit of the instrument's linear range (blank-corrected). |
| `window_points` | 5 | integer ≥ 3 | Points per sliding window. |
| `min_relative_rate` | 0.8 | 0 < q ≤ 1 | A window belongs to the exponential phase if its slope is at least q × the steepest slope. |
| `min_fold_change` | 2.0 | > 1 | Growth must be at least this fold change across the fitted interval (default: one doubling). |
| `min_r_squared` | 0.98 | 0 to 1 | Credibility threshold for the fit. |
| `max_relative_se` | 0.10 | > 0 | Credibility threshold for SE(μ) / μ. |

## 3. Method and mathematical assumptions

### 3.1 Blank correction and quantification limit

1. With `blank_method = mean`, the blank B is the mean of every reading from blank wells,
   and s_B their sample standard deviation (n − 1). Corrected OD: x = OD − B.
2. The quantification limit is L = max(`min_od`, `blank_sd_multiple` × s_B) when there are
   at least two blank readings, otherwise L = `min_od`. With `blank_method = none`,
   x = OD and L = `min_od`.
3. Readings with x < L are marked `below_quantification_limit`; readings with x > `max_od`
   are marked `above_max_od`. They are excluded from fitting, kept in `points.csv` with the
   reason, and counted in the results. Blank wells are not fitted.

Why ten standard deviations: three blank SDs is a common convention for *detecting* a
signal, ten for *quantifying* one (noise about 10% of the value). The method works on
ln x, whose noise is roughly s_B / x, so readings just above the blank are very noisy on a
log scale, and the search for the steepest window is drawn to them. On the synthetic
sample plate, three SDs gave mean estimates above the largest rate the logistic model
allows (section 3.3).

### 3.2 Exponential phase and growth rate

During exponential growth, OD(t) = OD₀ · exp(μt), so ln OD(t) = ln OD₀ + μt. For each well,
with the n valid readings (t_i, z_i = ln x_i) in time order and w = `window_points`:

1. If n < w: status `insufficient_data`.
2. Fit an ordinary least-squares line to every window of w consecutive valid readings.
   Let s_k be the slope of window k and s_max the largest (earliest if tied).
3. If s_max > 0: starting from the steepest window, extend to the left and right over
   adjacent windows while s_k ≥ q · s_max (q = `min_relative_rate`). The exponential phase
   is every reading in this contiguous run of windows.
4. Fit one least-squares line to all readings in the exponential phase. Its slope is μ,
   with standard error SE(μ) = sqrt(SSR / (m − 2) / Sxx) for m readings, and R² = 1 −
   SSR / SST.
5. If s_max > 0 and the fold change across the phase, exp(μ (t_end − t_start)), is at least
   `min_fold_change`: status `growth`, doubling time Td = ln 2 / μ.
6. Otherwise, the net rate (least-squares slope over all valid readings) decides: status
   `decline` if it is negative and the fitted net fold change over the whole time course is
   at most 1 / `min_fold_change`; otherwise `no_growth`. No growth rate or doubling time
   is reported; the net rate is.

### 3.3 Design study: why these defaults

`scripts/method_study.py` (output in `docs/method-study.md`) runs the implementation on
synthetic data with fixed seeds. Its findings:

- **The steepest window alone overestimates μ** on noisy data, because the maximum of many
  noisy slopes is biased upward: by about 3%, 9%, and 16% for noise standard deviations of
  0.01, 0.03, and 0.05 in ln OD (exponential curves, five-point windows, 15-minute
  readings). This is the guide's example method, so this specification departs from it.
- **Fitting one line through the whole region of near-maximal slope** averages over many
  more readings. With `min_relative_rate = 0.8` the overestimate was 0.0%, 0.2%, and 3.2%
  at the same noise levels; with 0.9 or 0.95 the region tracks the noisy maximum more
  closely and inherits much of its bias. 0.8 was therefore chosen.
- **The cost is a downward bias when growth slows gradually.** On noise-free logistic data
  (the website's curve) the estimate is 0.917 r, against 0.983 r for the steepest window.
  The estimate describes the exponential phase as a whole; it is not r.
- **Quantification limit.** The reference for bias is the method's own estimate on the
  same curve without noise (below r for logistic growth). On the sample plate model, three
  blank SDs overestimated that reference by 3.8% (condition A) and 10.1% (condition B; its
  mean of 1.009 r is above r, which a logistic curve cannot exceed). Ten SDs reduced this to
  0.7% and 7.4% and halved the spread for condition A.
- **Remaining bias.** For slow growth starting near the quantification limit (condition B:
  r = 0.6 per hour, readings every 15 minutes), the estimate is still about 7% too high on
  average under this noise model: the search for the steepest window still favours noisy
  windows at low OD. This is a known limitation, not yet corrected; candidate remedies
  (weighting readings by their noise, or a higher limit) need their own study.

These are properties of the method on these synthetic models only. The method has not been
validated on real experimental data, which can differ: look at the figures for every well.

### 3.4 Credibility

A fit can succeed mathematically without being a credible growth rate. A `growth` result
is **credible** only if all of these hold; each failure is recorded as a flag:

- R² ≥ `min_r_squared` (`low_r_squared`);
- SE(μ) / μ ≤ `max_relative_se` (`high_relative_se`);
- no excluded reading lies inside the exponential phase's time span
  (`excluded_reading_inside_phase`).

Informational flags, which do not affect credibility:

- `phase_starts_at_first_valid_reading`: lag phase not observed, or early growth below the
  quantification limit;
- `phase_ends_at_last_valid_reading`: growth had not slowed by the last valid reading.

### 3.5 Conditions

For each condition, summarise the credible `growth` wells: number, mean μ, sample standard
deviation (n − 1, when n ≥ 2), standard error of the mean, minimum, maximum, and the
doubling time of the mean rate, ln 2 / mean μ. Wells that are not credible or not in
`growth` status are listed with their status, never silently dropped. With a reference
condition, also report each condition's mean μ divided by the reference mean. No
significance tests are performed.

Assumptions (recorded in `results.json`):

- Blank-corrected OD600 is proportional to cell density within the fitted range.
- The blank is constant over time and the same for every sample well.
- Errors in ln OD are independent with constant variance (needed for SE(μ)).
- Wells are independent biological or technical replicates as labelled.
- Natural logarithms throughout; time in hours.

## 4. Output

| Output | Contents |
| ------ | -------- |
| `well_results.csv` | One row per sample well: status, credible, flags, μ (1/h), SE(μ), Td (h), R², readings in phase, phase start and end (h), fold change, steepest-window rate (diagnostic only), net rate, readings and exclusions. |
| `condition_summary.csv` | One row per condition: counts, mean, SD, SEM, min, max of μ; doubling time of the mean; ratio to the reference; wells not included. |
| `points.csv` | Every reading: well, condition, role, time (h), raw OD, corrected OD, whether used in the fit, and the reason if excluded. |
| `results.json` | All of the above plus settings, blank summary, assumptions, and warnings. |
| `figures/` | `growth_curves`, `exponential_fits`, `growth_rate_comparison`, and `wells/<well>` figures, as PNG and/or SVG. |
| `run_metadata.json` | Provenance record (see `provenance.py`). |

Existing output files are never replaced unless `--overwrite` is given; the check happens
before anything is written.

## 5. Known-answer examples

| Inputs | Expected output | How obtained |
| ------ | --------------- | ------------ |
| x(t) = 0.02 e^{0.7t}, t = 0, 0.5, …, 8 h, blank 0.05 added and blank wells reading 0.05 | μ = 0.7 1/h, Td = ln 2 / 0.7 h, all readings in the phase | Exactly linear in ln x; every window has the same slope. |
| x(t) = 0.8 e^{−0.3t}, t = 0…10 h | status `decline`, net rate −0.3 1/h | Exactly linear in ln x. |
| x(t) = 0.3 constant | status `no_growth`, net rate 0 | — |
| Logistic N(t) = K / (1 + (K/N₀ − 1) e^{−rt}) | r (1 − x_end / K) ≤ μ ≤ r (1 − x_start / K) < r | d ln N / dt = r (1 − N/K); a least-squares slope is a positively weighted average of pairwise secant slopes, each of which lies between the extreme derivatives (mean value theorem). |
| The website's illustrative well: logistic r = 1.2 1/h, N₀ = 0.01, K = 1.1, blank 0.045, every 15 min for 12 h, rounded to 3 decimals | The logistic bound above, widened by the largest possible effect of rounding on the slope (section 7) | As above. The estimate is not expected to equal 1.2. |

## 6. Edge cases and invalid input

| Case | Required behaviour |
| ---- | ------------------ |
| Fewer than `window_points` valid readings | `insufficient_data`; no rate. |
| Corrected OD below the quantification limit (including ≤ 0) | Excluded with reason; counted; plotted as excluded where possible. |
| No blank wells with `blank_method = mean` | Error suggesting `--blank-method none`. |
| Blank wells with `blank_method = none` | Not analysed; warning in the results. |
| Zero growth / decline | `no_growth` / `decline` with the net rate; no doubling time. |
| Growth below `min_fold_change` across the phase | `no_growth`. |
| Low R², high relative SE, gap inside the phase | `growth`, not credible, with flags. |
| Output files already exist | Error before writing anything, unless `--overwrite`. |

## 7. Numerical tolerances

- Exact exponential data: relative 1e-9. The least-squares slope on exactly linear data
  is exact up to a few hundred rounding errors (≈ 1e-13 relative); 1e-9 leaves room for
  differences between platforms' `log` and `exp`.
- Logistic bounds: no tolerance beyond 1e-12 relative for rounding; the bound is a theorem.
- Data rounded to 3 decimals: each corrected OD may be off by up to δ = 0.0005, so each
  ln x_i by up to e_i = −ln(1 − δ / x_i). The least-squares slope then moves by at most
  Σ |t_i − t̄| e_i / Σ (t_i − t̄)², computed for the selected readings.
- Noisy data with a fixed seed: the estimate must lie within 4 standard errors of the true
  rate (a fixed, conventional threshold; the SE ignores window-selection uncertainty).
- Bias study: over 200 seeded noisy exponential curves (SD 0.03 in ln OD), the mean
  estimate must be within 2% of the true rate and closer to it than the mean
  steepest-window slope (`tests/test_bias.py`).

## 8. Acceptance criteria

- [x] Every known-answer example in section 5 is a test.
- [x] Every case in section 6 is a test.
- [x] Property-based tests: invariance to scaling OD and shifting time, recovery of exact
      exponential growth, the logistic bound, never exceeding the logistic r.
- [x] Results, plots, and run metadata are written by the command-line tool and checked
      end to end on the sample data.
