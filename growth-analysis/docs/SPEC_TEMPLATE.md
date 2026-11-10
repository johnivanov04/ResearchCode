# Specification: <name of the function or analysis step>

<!--
How to use this template
- Copy it to docs/spec-<short-name>.md, one file per function or analysis step.
- Fill it in BEFORE asking an AI assistant (or anyone) to write the code.
- Keep it short: one page is usually enough. Delete hints like this one.
- Commit it with the code. If the behaviour changes, change the specification first.
- A completed example is in docs/spec-growth-curve.md.
-->

Status: draft | agreed | implemented
Owner: <the person responsible for the scientific decisions>
Implemented in: `src/<package>/<module>.py` (`<function name>`)
Tested in: `tests/<test file>.py`

## 1. Scientific objective

<!-- One or two sentences: what quantity is computed, and why it matters for the research
question. Name the quantity precisely; "growth rate" can mean several different things. -->

## 2. Inputs

<!-- For every input: name, type, units, valid range, and where it comes from. State
whether values are raw or already processed (for example, blank-corrected). -->

| Name | Type | Units | Valid values | Notes |
| ---- | ---- | ----- | ------------ | ----- |
|      |      |       |              |       |

Input file format (if any): <columns, header row, delimiter, units of each column, missing-value marker>

## 3. Method and mathematical assumptions

<!-- The formula or algorithm, step by step. List every assumption the method relies on
(for example: exponential growth, OD proportional to cell density, independent errors).
Say which logarithm base, which units, and which conventions are used. -->

1.
2.

Assumptions:

-

## 4. Output

<!-- Name, type, units, and meaning of every output. Say what is returned in special
cases (no result, zero, negative values) and what is raised as an error. -->

| Name | Type | Units | Meaning |
| ---- | ---- | ----- | ------- |
|      |      |       |         |

## 5. Known-answer examples

<!-- Inputs with exact expected outputs that you worked out independently (by hand, from
the formula, or from published reference values). These become the first tests.
Never take an expected value from running the code you are testing. -->

| Inputs | Expected output | How the expected value was obtained |
| ------ | --------------- | ----------------------------------- |
|        |                 |                                     |

## 6. Edge cases and invalid input

<!-- For each case, the required behaviour: a specific value, or a specific error.
Think about: zero, negative, NaN, infinity, empty input, a single point, equal values,
unsorted or duplicated times, wrong units, and extremely large or small values. -->

| Case | Required behaviour |
| ---- | ------------------ |
|      |                    |

## 7. Numerical tolerances

<!-- How close is close enough, and why. Separate floating-point rounding (about 1e-16
relative for double precision) from scientific or measurement tolerance (often much
larger). Never loosen a tolerance just to make a failing test pass. -->

- Floating-point comparisons in tests: <relative and/or absolute tolerance, with reason>
- Scientific tolerance: <for example, agreement with a reference method within 2%>

## 8. Properties that must always hold

<!-- Relationships true for every valid input. These become property-based tests. For
example: scaling all inputs by a constant does not change the result; swapping two
readings changes the sign; the result does not depend on the time origin. -->

-

## 9. Reproducibility requirements

<!-- What must be recorded with every result so it can be regenerated: parameters,
random seeds, input checksums, software versions. Which inputs are read-only. -->

-

## 10. Out of scope

<!-- What this function deliberately does NOT do, so nobody (human or AI) adds it
silently. -->

-

## 11. Acceptance criteria

<!-- The checklist a reviewer uses to decide the implementation is done. -->

- [ ] Every known-answer example in section 5 is an automated test, and passes.
- [ ] Every edge case in section 6 is an automated test, and passes.
- [ ] Every property in section 8 is a property-based test, and passes.
- [ ] Inputs are validated as described in section 2; invalid input raises a clear error.
- [ ] Units appear in names or docstrings of all inputs and outputs.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest` pass.
- [ ] A person responsible for the science has reviewed the method and the tests.
