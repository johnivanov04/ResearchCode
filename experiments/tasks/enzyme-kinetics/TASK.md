# Task: Michaelis–Menten kinetics and a CSV tool

A biochemistry lab measures initial reaction rates at several substrate concentrations
and estimates the Michaelis–Menten parameters of an enzyme. It needs a small, reliable
Python module with a fitting function and a command-line tool that turns a CSV file of
measurements into a JSON result.

## Deliverable

A Python module importable as **`enzyme_kinetics`**: either a file `enzyme_kinetics.py` or a
package `enzyme_kinetics/`, placed in this directory or in `src/` inside this directory. It
must provide the two functions below with exactly these names and parameters.

The module will be imported and called by an automated evaluator running **Python 3.12**
with only the **standard library, NumPy, and SciPy** installed. Do not depend on any other
package at run time.

## Model and method

The Michaelis–Menten model gives the initial rate v at substrate concentration S as

    v = Vmax · S / (Km + S)

Estimate Vmax and Km by **unweighted nonlinear least squares on the untransformed rates**:
choose the values that minimise Σ (vᵢ − Vmax·Sᵢ / (Km + Sᵢ))². Linearisations
(Lineweaver–Burk, Eadie–Hofstee, Hanes–Woolf) give different, biased estimates and are
not acceptable as the result, although they may be used as starting values.

Standard errors: with n data points, residual variance s² = SSR / (n − 2) at the optimum,
and J the n × 2 Jacobian of the model with respect to (Vmax, Km) at the optimum, the
covariance matrix of the estimates is s² · (Jᵀ J)⁻¹. The standard errors are the square
roots of its diagonal.

## Functions

### 1. `fit_michaelis_menten(substrate_uM, rates)`

`substrate_uM` (substrate concentrations in micromolar) and `rates` are sequences (lists,
tuples, or 1-D NumPy arrays) of equal length containing finite numbers. Substrate
concentrations must be ≥ 0, and there must be at least 3 distinct positive substrate
concentrations. Rates may be zero or slightly negative (measurement noise). Repeated
substrate concentrations (replicates) are allowed; each point counts separately.

Return a mapping (a `dict`, or an object with these attributes) with:

| Field | Meaning |
| --- | --- |
| `"vmax"` | Vmax, in the units of the rates |
| `"km_uM"` | Km, in µM |
| `"vmax_se"` | standard error of Vmax |
| `"km_se_uM"` | standard error of Km, in µM |
| `"n"` | number of data points used (an `int`) |

Raise `ValueError` for invalid input (unequal lengths, NaN or infinite values, negative
concentrations, too few distinct positive concentrations). Also raise `ValueError` if the
data do not determine the parameters: if there is no least-squares optimum with
Vmax > 0 and 0 < Km ≤ 100 × (the largest substrate concentration). For example, rates
that are exactly proportional to S never level off, so Km is not determined. Do not return
numbers in that case.

The function must not read or write files and must not modify its arguments.

### 2. `main(argv) -> int`

A command-line entry point. `argv` is the list of arguments **without** the program name,
for example `["--input", "rates.csv", "--output", "fit.json"]`. Both options are
required. (If you also make the module runnable with `python -m enzyme_kinetics`, it
should call `main(sys.argv[1:])`.)

**Input file.** A CSV file encoded in UTF-8, possibly starting with a byte-order mark
(spreadsheet programs often add one). The first row is a header. The header must contain a
column named `rate` and **exactly one** of `substrate_uM` (micromolar) or `substrate_mM`
(millimolar); other columns are ignored. Each following row is one measurement. Rows that
are completely empty are ignored. Every other row must have a valid number in the rate
and substrate columns.

**Output file.** On success, write a JSON object with the keys `"vmax"`, `"km_uM"`,
`"vmax_se"`, `"km_se_uM"`, and `"n"`, as returned by `fit_michaelis_menten` after converting
the substrate concentrations to µM (1 mM = 1000 µM). Km and its standard error are always
reported in µM. Return 0.

**Errors.** If the input file is missing, unreadable, or invalid (missing columns, both or
neither substrate column, a non-numeric or empty value in a required column, too few
points), or if the fit raises `ValueError`, print a message to standard error and return
a non-zero exit status. In every error case, **do not create the output file**.

**Never overwrite.** If the output file already exists, return a non-zero exit status
and leave the existing file unchanged.

## Public examples

`public_examples.json` lists example inputs and their expected results. They are
illustrative, not a complete test of the requirements.
