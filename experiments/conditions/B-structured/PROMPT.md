Implement the Python module described in TASK.md in this directory. You can write and run code.

No one is available to answer questions during this session. If something is unclear, make a reasonable decision, note it, and continue. Finish the task in this session.

This directory is a copy of the ResearchCode scientific Python starter kit. Follow its workflow, described in AGENTS.md:

1. Write a specification for this task in docs/, based on docs/SPEC_TEMPLATE.md. Where AGENTS.md says to stop and ask a human, or to wait for agreement, record the question and your decision in the specification instead, then continue.
2. Write tests in tests/ before or alongside the implementation: known-answer tests whose expected values come from hand calculation or mathematics (never from running the code under test), edge-case and invalid-input tests, and property-based tests with Hypothesis where a relationship must always hold.
3. Implement the module under src/, keeping scientific calculations in small, pure functions, with units and assumptions documented.
4. Run `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest`, and fix every failure. Do not weaken tests to make them pass.
5. Finish with a short summary of your assumptions and any known limitations.

The starter kit's growth-rate example is unrelated to this task. You may remove or keep it.
