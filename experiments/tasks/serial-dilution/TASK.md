# Task: serial dilutions and plate counts

A microbiology lab estimates the concentration of viable bacteria in a sample by serial
dilution and plating. It needs a small, reliable Python module for the calculations: unit
conversion, dilution factors, colony-forming units (CFU) per millilitre, and preparing a
dilution from a stock solution.

## Deliverable

A Python module importable as **`serial_dilution`**: either a file `serial_dilution.py` or a
package `serial_dilution/`, placed in this directory or in `src/` inside this directory. It
must provide the five functions below with exactly these names and parameters.

The module will be imported and called by an automated evaluator running **Python 3.12**
with only the **standard library, NumPy, and SciPy** installed. Do not depend on any other
package at run time. The functions must not read or write files, must not print
anything required for the result, and must not modify their arguments.

## Volume units

The accepted unit strings are exactly (case-sensitive):

| Unit string | Meaning | Millilitres |
| --- | --- | --- |
| `"L"` | litre | 1000 |
| `"mL"` | millilitre | 1 |
| `"uL"`, `"µL"`, `"μL"` | microlitre | 0.001 |
| `"nL"` | nanolitre | 0.000001 |

`"µL"` uses the micro sign (U+00B5) and `"μL"` uses the Greek small letter mu (U+03BC);
both appear in real files and both must be accepted. Any other unit string must raise
`ValueError`.

## General input rules

- Numeric inputs are Python `int` or `float` values (NumPy scalars are also allowed).
- Any NaN or infinite numeric input must raise `ValueError`.
- A value of the wrong type (for example a string where a number is required) must raise
  `ValueError` or `TypeError`.
- Do not round results.

## Functions

### 1. `convert_volume(value, from_unit, to_unit) -> float`

Convert a volume between units. `value` must be finite and ≥ 0 (zero is allowed); a
negative value raises `ValueError`.

### 2. `step_dilution_factor(transfer_volume, transfer_unit, diluent_volume, diluent_unit) -> float`

The dilution factor of one step, in which `transfer_volume` of a suspension is added to
`diluent_volume` of diluent:

    factor = (transfer volume + diluent volume) / transfer volume

with both volumes in the same unit. The two volumes may be given in different units. The
transfer volume must be > 0 and the diluent volume ≥ 0 (a diluent volume of zero gives a
factor of 1); otherwise raise `ValueError`.

Example: 100 µL into 900 µL gives a factor of 10 (a 1:10 dilution).

### 3. `cumulative_dilution_factors(steps) -> list[float]`

`steps` is a sequence of mappings, one per step of a serial dilution, in order. Each
mapping has the keys `"transfer_volume"`, `"transfer_unit"`, `"diluent_volume"`, and
`"diluent_unit"`, with the meanings in function 2. Return a list with one element per
step: the total dilution factor of the tube after that step, relative to the original
sample (the product of the step factors up to and including that step).

An empty sequence returns an empty list. A missing key, or any invalid value as defined
for function 2, raises `ValueError`.

### 4. `estimate_cfu_per_ml(plates, countable_range=(30, 300))`

Estimate the concentration of the **original** (undiluted) sample in CFU per mL from
colony counts on one or more plates.

`plates` is a non-empty sequence of mappings with the keys:

- `"colonies"`: the number of colonies counted, a non-negative `int`, or the string
  `"TNTC"` (too numerous to count);
- `"dilution_factor"`: the total dilution factor of the suspension that was plated,
  relative to the original sample (for example `1000` for a 10⁻³ dilution); it must be
  ≥ 1;
- `"plated_volume"` (> 0) and `"plated_unit"`: the volume spread on the plate.

`countable_range` is a pair `(low, high)` of integers with 0 ≤ low ≤ high. A plate is
**countable** if its colony count is an integer with low ≤ colonies ≤ high (both bounds
inclusive). `"TNTC"` plates are never countable.

Return a mapping (a `dict`, or an object with these attributes) with:

- `"cfu_per_ml"`: if at least one plate is countable,

      sum of colonies on countable plates
      / sum over countable plates of (plated volume in mL / dilution factor)

  Plates that are not countable are ignored. If no plate is countable, `None`.
- `"status"`: `"ok"` if at least one plate is countable, otherwise
  `"no_countable_plates"`.
- `"plates_used"`: the number of countable plates (an `int`).

Raise `ValueError` for an empty `plates`, a missing key, a negative or non-integer colony
count, any string other than `"TNTC"`, a dilution factor below 1, a plated volume ≤ 0, an
unknown unit, or an invalid `countable_range`.

Example: 150 colonies from 0.1 mL of a 10⁻⁴ dilution give 150 / (0.1 / 10 000) =
1.5 × 10⁷ CFU/mL.

### 5. `dilution_volumes(stock_concentration, target_concentration, final_volume, unit)`

How much stock and diluent to combine to make `final_volume` of a solution at
`target_concentration` from a stock at `stock_concentration` (C1·V1 = C2·V2). The two
concentrations are in the same (unspecified) unit; volumes are in `unit`.

Return a mapping (or an object with these attributes) with `"stock_volume"` and
`"diluent_volume"`, both in `unit`; they add up to `final_volume`.

Both concentrations must be > 0, the target must not exceed the stock (a target equal to
the stock gives a diluent volume of 0), and `final_volume` must be > 0. Otherwise raise
`ValueError`. An unknown unit raises `ValueError`.

## Public examples

`public_examples.json` lists example calls and their expected results. They are
illustrative, not a complete test of the requirements.
