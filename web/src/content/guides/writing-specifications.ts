import type { Guide } from "./types";

export const writingSpecifications: Guide = {
  slug: "writing-specifications",
  title: "Write a specification before you prompt",
  summary:
    "Turn a vague request into a short, checkable specification so the assistant implements your method rather than a plausible guess.",
  stage: "Specify",
  readingMinutes: 12,
  audience: "Anyone about to ask an AI assistant to implement an analysis, model, or data pipeline.",
  outcomes: [
    "Recognise the decisions an assistant will make silently if you do not make them",
    "Write a one-page specification covering inputs, method, outputs, and validation",
    "Use the assistant to find gaps in your specification before any code exists",
  ],
  sections: [
    {
      id: "why",
      title: "Why the specification matters more with AI",
      blocks: [
        {
          type: "paragraph",
          text: "An AI coding assistant is very good at producing code that runs. It is much less reliable at knowing which of several reasonable choices your field, your instrument, or your experiment actually requires. When a request leaves a choice open, the assistant fills it with something plausible, and the result usually looks correct.",
        },
        {
          type: "paragraph",
          text: "Consider the request: \"Write a function that computes the growth rate from my plate reader data.\" To implement it, the assistant must decide, among other things:",
        },
        {
          type: "list",
          items: [
            "Whether optical density values are already blank-corrected, and if not, which wells are blanks",
            "Whether time is recorded in seconds, minutes, or hours",
            "Whether \"growth rate\" means the maximum specific growth rate, an average rate, or a fitted model parameter",
            "Which logarithm to use, and whether the rate is reported per hour or as a doubling time",
            "How to choose the exponential phase, and what to do with zero, negative, or missing readings",
          ],
        },
        {
          type: "paragraph",
          text: "Each of these choices can change the answer by a large factor, and none of them causes an error message. A specification is the place where you, the domain expert, make these decisions explicitly and in writing.",
        },
        {
          type: "callout",
          tone: "note",
          title: "A specification is not bureaucracy",
          text: "For a single analysis function, a useful specification fits on one page and takes 15 to 30 minutes to write. It also becomes the basis for your tests, your documentation, and the methods section of your paper.",
        },
      ],
    },
    {
      id: "anatomy",
      title: "The parts of a scientific specification",
      blocks: [
        {
          type: "paragraph",
          text: "Use the following headings. Leave a heading in place with \"Not applicable\" rather than deleting it, so that a reader can tell the question was considered.",
        },
        {
          type: "list",
          ordered: true,
          items: [
            "Purpose: one or two sentences on the scientific question this code answers.",
            "Inputs: file formats, column names, units, expected ranges, and what invalid input looks like.",
            "Method: the equations or algorithm, with a citation if it comes from the literature. State every parameter and its default.",
            "Outputs: names, units, data types, and file formats. Say how many significant figures are meaningful.",
            "Assumptions: what must be true about the data for the method to be valid.",
            "Edge cases and failure behaviour: what the code should do with empty input, missing values, or values outside the valid range. Prefer failing loudly over guessing.",
            "Validation: how you will know the implementation is correct, such as a known analytical answer, a published dataset, or an independent tool, with numerical tolerances.",
            "Out of scope: what the code should not do. This keeps the assistant from adding features you did not ask for.",
          ],
        },
      ],
    },
    {
      id: "example",
      title: "A worked example",
      blocks: [
        {
          type: "paragraph",
          text: "Below is a complete specification for one function in a bacterial growth analysis. It is deliberately short. Save it in your repository, for example as `docs/spec-growth-rate.md`, so it is versioned alongside the code.",
        },
        {
          type: "code",
          language: "markdown",
          title: "docs/spec-growth-rate.md",
          code: `# Specification: maximum specific growth rate

## Purpose
Estimate the maximum specific growth rate (mu_max, per hour) and doubling
time of a bacterial culture from a plate reader OD600 time series.

## Inputs
- time_h: 1-D array of sampling times in HOURS, strictly increasing.
- od: 1-D array of raw OD600 readings, same length as time_h.
- blank_od: float, mean OD600 of medium-only wells at the same wavelength.

## Method
1. Blank-correct: od_corr = od - blank_od.
2. Keep points with od_corr >= 0.005 (below this, noise dominates).
3. y = natural log (ln) of od_corr.
4. Slide a window of \`window\` consecutive points (default 5) along y and
   fit an ordinary least-squares line in each window.
5. mu_max = the largest slope among windows whose fit has R^2 >= 0.98.
6. doubling_time_h = ln(2) / mu_max.

## Outputs
- mu_max (float, 1/h), doubling_time_h (float, h),
  window_start_h and window_end_h (floats, h) for the selected window.

## Assumptions
- OD600 is in the instrument's linear range (verify per instrument).
- One culture per call; replicates are handled by the caller.

## Edge cases
- Arrays of different length, non-increasing time, or NaN values:
  raise ValueError with a message naming the problem.
- Fewer valid points than \`window\`, or no window meets the R^2
  threshold: raise ValueError. Never return 0 or NaN silently.

## Validation
- On synthetic exponential data N(t) = N0 * exp(0.8 * t) with blank 0.04
  added, recovers mu_max = 0.8 within relative tolerance 1e-6.
- On synthetic logistic data with r = 1.2, recovers mu_max within 2%.
- Doubling time equals ln(2) / mu_max exactly.

## Out of scope
- Plotting, file I/O, lag-time estimation, model fitting (Gompertz etc.).
- No new dependencies beyond NumPy.`,
        },
        {
          type: "paragraph",
          text: "Notice what this specification does. It fixes the units, the logarithm, and the definition of growth rate. It gives numerical thresholds that a reviewer can question. Most importantly, the validation section describes tests with known answers, which you can write before any implementation exists.",
        },
      ],
    },
    {
      id: "use-the-assistant",
      title: "Use the assistant to critique the specification",
      blocks: [
        {
          type: "paragraph",
          text: "Before asking for code, ask the assistant to find ambiguities. Assistants are often better at spotting unstated assumptions in a document than at avoiding them while writing code. Treat its answers as questions for you to decide, not as decisions.",
        },
        {
          type: "prompt",
          title: "Find gaps in a specification",
          prompt: `I am going to give you a specification for a scientific function.
Do not write any code yet.

Read the specification and list:
1. Every place where two competent programmers could reasonably
   implement it differently.
2. Any units, data types, or ranges that are not stated.
3. Inputs or edge cases the specification does not say how to handle.
4. Any scientific assumption that seems questionable, and why.

Format your answer as a numbered list of questions I need to answer.

Specification:
<paste your specification here>`,
          note: "Answer each question by editing the specification itself, not just the chat. The chat is lost; the file is versioned.",
        },
        {
          type: "prompt",
          title: "Implement against the specification",
          prompt: `Implement the function described in docs/spec-growth-rate.md.

Constraints:
- Follow the specification exactly. If something is ambiguous,
  stop and ask me instead of choosing.
- Do not add features listed under "Out of scope".
- Do not add dependencies other than those named in the specification.
- Include a docstring that states units for every argument and return value.
- Do not write or modify tests; I will provide them separately.

When you are done, list any place where you had to interpret the
specification, so I can review those decisions.`,
        },
      ],
    },
    {
      id: "pitfalls",
      title: "Common mistakes",
      blocks: [
        {
          type: "list",
          items: [
            "Describing the code instead of the science. \"Use pandas to load the CSV\" is less useful than \"time is in minutes since inoculation; convert to hours\".",
            "Omitting units. Unit errors are among the most common silent failures in scientific code.",
            "Writing validation criteria after seeing the output. Decide what the right answer looks like first.",
            "Letting the specification drift. When you change your mind during implementation, update the document in the same commit as the code.",
            "Specifying too much at once. Write and implement one function or module at a time.",
          ],
        },
        {
          type: "callout",
          tone: "warning",
          text: "If the assistant's implementation does something your specification did not mention, such as dropping rows with missing values or clipping negative numbers, treat it as a decision that needs your review. Silent data cleaning is a common source of irreproducible results.",
        },
      ],
    },
    {
      id: "checklist",
      title: "Checklist",
      blocks: [
        {
          type: "checklist",
          title: "Before you ask for code",
          items: [
            "The purpose is stated in terms of the scientific question.",
            "Every input and output has units, type, and expected range.",
            "The method names the equation or algorithm and cites a source if one exists.",
            "Every parameter has an explicit default and a reason for it.",
            "Behaviour for empty, missing, and out-of-range input is defined.",
            "At least one validation check has a known correct answer and a numerical tolerance.",
            "Out-of-scope features are listed.",
            "The specification is saved in the repository, not only in a chat window.",
          ],
        },
      ],
    },
  ],
};
