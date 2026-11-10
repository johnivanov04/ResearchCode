# Instructions for Claude Code

The project's rules for all AI coding assistants are in `AGENTS.md` and are imported here,
so there is a single source of truth. Edit `AGENTS.md`, not this file.

@AGENTS.md

## Claude Code specifics

- `.claude/settings.json` disables automatic commit and pull request attribution. Keep it.
- When asked to implement something, first restate the relevant part of the specification
  and list your assumptions, then make the change, then run the three checks in rule 6.
