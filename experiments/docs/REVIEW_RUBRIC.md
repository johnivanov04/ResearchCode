# Blinded maintainability review rubric

This rubric is used for the subjective secondary metric in the Phase 4 protocol (section 5.3).
It is applied to review packets made by `rc-exp review-packets`. Each packet contains only the
implementation module of one submission and is labelled with a random code. Review packets
in a random order. Do not try to infer the condition, and do not look at the blinding key,
hidden tests, scores, or transcripts before every packet is scored.

Score each criterion from 1 to 4 using the descriptions below. Record a one-sentence reason for
each score. Scores are reported separately from every objective metric and are never combined
with them.

## Criteria

### 1. Clarity of the scientific calculation

| Score | Description |
| --- | --- |
| 4 | Each formula is easy to find and matches the task statement; names say what quantities are |
| 3 | Formulas are findable, with minor naming or structure issues |
| 2 | Formulas are mixed with input handling or obscured by naming |
| 1 | It is hard to tell how results are computed |

### 2. Units and assumptions stated

| Score | Description |
| --- | --- |
| 4 | Units appear in names or docstrings throughout; assumptions and choices are written down |
| 3 | Most units and the main assumptions are stated |
| 2 | Some units or assumptions are stated, important ones are missing |
| 1 | Units and assumptions are not stated |

### 3. Input validation and error messages

| Score | Description |
| --- | --- |
| 4 | Invalid input is rejected at a clear boundary with messages that say what is wrong |
| 3 | Validation is present but scattered, or messages are vague |
| 2 | Validation is partial |
| 1 | Little or no validation |

### 4. Structure and readability

| Score | Description |
| --- | --- |
| 4 | Small functions with one purpose; no dead code; a reader new to the code can modify it safely |
| 3 | Reasonable structure with some long or repetitive parts |
| 2 | Long functions, duplication, or unused code make changes risky |
| 1 | Hard to follow or modify |

## Recording

Record scores in a CSV file with the columns `code`, `task`, `clarity`, `units_assumptions`,
`validation`, `structure`, and `notes`. Keep it separate from the blinding key until every
packet is scored. Then join the scores to trials with the key.

If a second reviewer is available, both score every packet independently. Agreement is reported
as the share of scores that are equal and the share within one point.
