import type { Guide } from "./types";

export const testingGeneratedCode: Guide = {
  slug: "testing-generated-code",
  title: "Test AI-generated scientific code",
  summary:
    "Code that runs is not code that is correct. Use known answers, invariants, and edge cases to catch the errors that never raise an exception.",
  stage: "Test",
  readingMinutes: 15,
  audience: "Researchers who use AI assistants to write analysis code in Python and want evidence that it is right.",
  outcomes: [
    "Write known-answer, property, and edge-case tests with pytest and NumPy",
    "Choose numerical tolerances deliberately instead of comparing floats with ==",
    "Keep tests independent of the implementation so they can actually catch mistakes",
  ],
  sections: [
    {
      id: "why",
      title: "Why generated code needs tests you trust",
      blocks: [
        {
          type: "paragraph",
          text: "The most damaging bugs in scientific code produce a number that looks reasonable. A growth rate reported per minute instead of per hour, a base-10 logarithm used where the natural logarithm was intended, or a filter that silently drops the first time point will not crash your program. They will change your conclusions.",
        },
        {
          type: "paragraph",
          text: "AI assistants make these mistakes for the same reasons people do, but they make them faster and present the result with confidence. There is a second, subtler risk: if the same assistant writes both the code and the tests in one step, the tests often encode the code's assumptions. A test that was derived from the implementation's output can only confirm that the implementation does what it does.",
        },
        {
          type: "callout",
          tone: "note",
          title: "The principle",
          text: "The expected value in a test should come from mathematics, physics, a published result, or an independent tool. It should never come from running the code under test and copying the answer.",
        },
      ],
    },
    {
      id: "known-answers",
      title: "Known-answer tests",
      blocks: [
        {
          type: "paragraph",
          text: "Construct an input for which you can calculate the correct output by hand or analytically. For growth curves, generate data from an exponential model with a known rate. If the function cannot recover a rate you put in, it will not recover the rate in your experiment either.",
        },
        {
          type: "code",
          language: "python",
          title: "tests/test_rates.py",
          code: `import numpy as np
import pytest

from growth.rates import max_specific_growth_rate

BLANK = 0.04  # OD600 of medium-only wells


def exponential_od(mu_per_h, time_h, n0=0.02):
    """Raw OD600 readings for ideal exponential growth plus a constant blank."""
    return BLANK + n0 * np.exp(mu_per_h * time_h)


def test_recovers_known_rate_from_exponential_data():
    time_h = np.arange(0.0, 6.0, 0.25)
    od = exponential_od(0.8, time_h)

    result = max_specific_growth_rate(time_h, od, blank_od=BLANK)

    np.testing.assert_allclose(result.mu_max, 0.8, rtol=1e-6)


def test_doubling_time_is_ln2_over_rate():
    time_h = np.arange(0.0, 6.0, 0.25)
    result = max_specific_growth_rate(
        time_h, exponential_od(0.8, time_h), blank_od=BLANK
    )

    assert result.doubling_time_h == pytest.approx(np.log(2) / 0.8, rel=1e-6)`,
          caption: "The expected value 0.8 is an input to the test, not an output copied from the code.",
        },
        {
          type: "paragraph",
          text: "Good sources of known answers include analytical solutions, conservation laws, limiting cases (for example, zero concentration or infinite time), small examples worked by hand, and published reference datasets with reported results.",
        },
      ],
    },
    {
      id: "properties",
      title: "Property and invariant tests",
      blocks: [
        {
          type: "paragraph",
          text: "Some correct behaviours hold for many inputs at once. Testing them catches errors that a single known-answer test can miss. For a growth rate estimated from the slope of ln(OD):",
        },
        {
          type: "list",
          items: [
            "Multiplying the blank-corrected signal by a constant must not change the rate, because it only shifts ln(OD).",
            "Shifting every time point by a constant must not change the rate.",
            "For ideal exponential data, keeping only every second time point must not change the rate.",
          ],
        },
        {
          type: "code",
          language: "python",
          title: "tests/test_rates.py (continued)",
          code: `@pytest.mark.parametrize("scale", [0.5, 2.0, 10.0])
def test_rate_is_invariant_to_signal_scale(scale):
    time_h = np.arange(0.0, 6.0, 0.25)
    od = BLANK + scale * 0.02 * np.exp(0.8 * time_h)

    result = max_specific_growth_rate(time_h, od, blank_od=BLANK)

    np.testing.assert_allclose(result.mu_max, 0.8, rtol=1e-6)


@pytest.mark.parametrize("offset_h", [0.0, 1.5, 24.0])
def test_rate_is_invariant_to_time_offset(offset_h):
    time_h = np.arange(0.0, 6.0, 0.25)
    od = exponential_od(0.8, time_h)

    result = max_specific_growth_rate(time_h + offset_h, od, blank_od=BLANK)

    np.testing.assert_allclose(result.mu_max, 0.8, rtol=1e-6)`,
        },
      ],
    },
    {
      id: "edge-cases",
      title: "Edge cases and failure behaviour",
      blocks: [
        {
          type: "paragraph",
          text: "Your specification should say what happens with bad input. Test that the code fails loudly. A function that returns `0.0` or `nan` for unusable data will eventually end up in a results table.",
        },
        {
          type: "code",
          language: "python",
          title: "tests/test_rates.py (continued)",
          code: `def test_rejects_missing_values():
    time_h = np.arange(0.0, 6.0, 0.25)
    od = exponential_od(0.8, time_h)
    od[3] = np.nan

    with pytest.raises(ValueError, match="NaN"):
        max_specific_growth_rate(time_h, od, blank_od=BLANK)


def test_rejects_too_few_points():
    time_h = np.array([0.0, 0.25, 0.5])

    with pytest.raises(ValueError):
        max_specific_growth_rate(time_h, exponential_od(0.8, time_h), blank_od=BLANK)


def test_rejects_unsorted_time():
    time_h = np.array([0.0, 0.5, 0.25, 0.75, 1.0, 1.25])

    with pytest.raises(ValueError, match="increasing"):
        max_specific_growth_rate(time_h, exponential_od(0.8, time_h), blank_od=BLANK)`,
        },
        {
          type: "paragraph",
          text: "Ask the assistant to brainstorm edge cases, then decide yourself which ones matter scientifically. Typical candidates are empty arrays, a single data point, missing values, zero or negative values before a logarithm, duplicated time points, extreme magnitudes, and inputs of mismatched length.",
        },
      ],
    },
    {
      id: "tolerances",
      title: "Choose tolerances deliberately",
      blocks: [
        {
          type: "paragraph",
          text: "Floating-point results are rarely exactly equal to the mathematical answer, so never compare them with `==`. Use `np.testing.assert_allclose` or `pytest.approx`, and choose the tolerance for a reason.",
        },
        {
          type: "list",
          items: [
            "Noise-free synthetic data with an exact method: a tight relative tolerance such as `rtol=1e-6` is appropriate. A looser tolerance can hide a real bug.",
            "Methods with inherent approximation, such as a sliding window on a logistic curve: derive or measure how close the method can get, and document why the tolerance is what it is.",
            "Values that should be zero: relative tolerance is meaningless near zero, so set `atol` explicitly.",
            "Stochastic code: fix a seed with `np.random.default_rng(seed)` for exact regression tests, and test statistical properties across many seeds separately.",
          ],
        },
        {
          type: "callout",
          tone: "warning",
          title: "Do not let tolerances drift",
          text: "When a test fails, an assistant may suggest loosening the tolerance until it passes. Treat that as a scientific decision. If the method really is less precise than you assumed, record why in a comment next to the tolerance.",
        },
      ],
    },
    {
      id: "independence",
      title: "Keep tests independent of the implementation",
      blocks: [
        {
          type: "list",
          ordered: true,
          items: [
            "Write tests from the specification, before or separately from the implementation. If an assistant helps, start a fresh session and give it only the specification.",
            "Review every expected value. Ask: where did this number come from?",
            "Check that the tests can fail. Deliberately break the implementation, for example replace `np.log` with `np.log10`, and confirm that at least one test fails. Then revert.",
            "Do not let the assistant modify tests to make them pass. If you allow it to edit test files, review those changes with extra care.",
            "Add regression tests only after validation. Once results on a real dataset have been checked independently, save a small reference output so future changes cannot alter it unnoticed.",
          ],
        },
        {
          type: "prompt",
          title: "Write tests from a specification only",
          prompt: `You are helping me write pytest tests for a scientific function.
You will see the specification, but not the implementation.

Write tests that:
1. Use synthetic inputs where the correct answer is known analytically.
   Show the derivation of each expected value in a comment.
2. Check invariants implied by the specification (for example,
   scaling or shifting inputs).
3. Check every edge case and failure behaviour the specification lists.

Rules:
- Use np.testing.assert_allclose or pytest.approx for floats, and
  justify each tolerance in a comment.
- Do not invent behaviour that the specification does not define.
  If you think a case is missing from the specification, list it
  separately as a question instead of writing a test for it.

Specification:
<paste specification>`,
        },
        {
          type: "prompt",
          title: "Diagnose a failing test without editing it",
          prompt: `The test below fails. Do not modify the test.

1. Explain, step by step, what the test expects and why.
2. Explain what the implementation actually does with this input.
3. Identify whether the bug is in the implementation, or whether
   the test contradicts the specification. Quote the relevant line
   of the specification.
4. Propose the smallest change to the implementation that fixes it.

<paste test, error output, and implementation>`,
        },
      ],
    },
    {
      id: "running",
      title: "Run the tests every time",
      blocks: [
        {
          type: "paragraph",
          text: "Tests only help if they run. Run them locally before every commit and automatically on every push. The ResearchCode starter kit includes a GitHub Actions workflow that does this on every push and pull request.",
        },
        {
          type: "code",
          language: "bash",
          title: "terminal",
          code: `uv run pytest            # run the whole suite
uv run pytest -x -q      # stop at the first failure, minimal output
uv run pytest -k rate    # run only tests whose names contain "rate"`,
        },
      ],
    },
    {
      id: "checklist",
      title: "Checklist",
      blocks: [
        {
          type: "checklist",
          title: "Before you trust a generated function",
          items: [
            "At least one test uses input with an analytically known answer.",
            "Every expected value can be traced to mathematics, the literature, or an independent tool.",
            "Invariants implied by the science are tested.",
            "Invalid input raises a clear error rather than returning a number.",
            "Every floating-point comparison has a justified tolerance.",
            "You broke the code on purpose and saw a test fail.",
            "The assistant did not write the tests by reading the implementation.",
            "Tests run automatically on every push.",
          ],
        },
      ],
    },
  ],
};
