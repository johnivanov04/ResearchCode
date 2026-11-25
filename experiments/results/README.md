# Experiment results

These folders hold the data of the Phase 4 experiment, written only by `rc-exp collect`,
`rc-exp evaluate`, and `rc-exp batch`, never by hand. Data collection and the pre-registered
analysis are complete. The trial records, invalid attempts, and analysis output in these folders
are **kept private** and are not in the public repository: a deviation from the protocol's
publication plan (sections 6 and 10), decided after unblinding and recorded in
`../docs/RESEARCH_LOG.md`. The aggregate results are public in `../docs/aggregate-results.json`
and `../docs/FINAL_REPORT.md`.

| Folder | Contents |
| --- | --- |
| `genuine/` | Confirmatory trials (`<task>--<condition>--rNN/`), analysed as pre-registered |
| `pilot/` | Pilot trials (`pNN`); never part of the confirmatory analysis. The protocol said they would be published separately; they are kept private |
| `engineering/` | Engineering validation runs (`eNN`, protocol 1.5): tests of the harness, outside the schedule, never analysed with pilot or confirmatory data |
| `analysis/<kind>/` | Output of `rc-exp analyze` (report, tables, figures) |
| `schedule.json` | The randomised run order, generated from the seed in `experiment.json` |

Each trial folder contains `trial.json` (configuration, timing, execution mode, and what
Claude Code reported), `session-logs/` (Claude Code's session log), `submission/` (the workspace
as the agent left it, without caches or virtual environments), and `evaluation.json`
(hidden-test, own-test, and static results). Trials run by `rc-exp batch` also have
`agent-output/` (Claude Code's streamed output, redacted).

Fixture (dry-run) output is refused inside this folder, so it can never be mistaken for data.
