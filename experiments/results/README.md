# Experiment results

**No trials have been run.** These folders will hold the genuine data of the Phase 4
experiment, written only by `rc-exp collect` and `rc-exp evaluate`, never by hand.

| Folder | Contents |
| --- | --- |
| `genuine/` | Confirmatory trials (`<task>--<condition>--rNN/`), analysed as pre-registered |
| `pilot/` | Pilot trials (`pNN`); published, but never part of the confirmatory analysis |
| `analysis/<kind>/` | Output of `rc-exp analyze` (report, tables, figures) |
| `schedule.json` | The randomised run order, generated from the seed in `experiment.json` |

Each trial folder contains `trial.json` (configuration, timing, and what Claude Code
reported), `transcript.jsonl` (the agent session), `submission/` (the workspace as the agent
left it, without caches or virtual environments), and `evaluation.json` (hidden-test,
own-test, and static results).

Fixture (dry-run) output is refused inside this folder, so it can never be mistaken for data.
