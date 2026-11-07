export type WorkflowStage = {
  name: string;
  summary: string;
  you: string;
  assistant: string;
  artifact: string;
  guideSlug?: string;
};

/** The structured AI-assisted development workflow promoted by ResearchCode. */
export const workflowStages: readonly WorkflowStage[] = [
  {
    name: "Specify",
    summary: "Decide what correct means before any code exists.",
    you: "State inputs, units, method, edge cases, and how you will validate.",
    assistant: "Points out ambiguities and unstated assumptions.",
    artifact: "docs/spec.md",
    guideSlug: "writing-specifications",
  },
  {
    name: "Test",
    summary: "Encode known answers as automated checks.",
    you: "Choose expected values from theory or reference data.",
    assistant: "Drafts tests from the specification, not the code.",
    artifact: "tests/",
    guideSlug: "testing-generated-code",
  },
  {
    name: "Generate",
    summary: "Implement one small piece at a time.",
    you: "Ask for a focused change that satisfies the spec.",
    assistant: "Writes the implementation and flags interpretations.",
    artifact: "src/",
  },
  {
    name: "Review",
    summary: "Read the diff and run the checks.",
    you: "Inspect data handling, constants, and dependencies.",
    assistant: "Explains its change; tools lint and run tests.",
    artifact: "git commit",
    guideSlug: "reviewing-ai-changes",
  },
  {
    name: "Reproduce",
    summary: "Show that a clean machine gets the same answer.",
    you: "Pin the environment, record provenance, rerun from scratch.",
    assistant: "Audits for hidden state and hard-coded paths.",
    artifact: "uv.lock + CI",
    guideSlug: "reproducibility",
  },
];
