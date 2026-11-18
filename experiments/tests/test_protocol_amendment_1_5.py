"""Protocol 1.5 changes only how sessions are run; everything else is provably unchanged.

The version 1.4 protocol, configuration, and freeze record are kept verbatim in
``freeze-history/``. These tests check that the archive is the original (by the hashes in the
original freeze record), and that the amendment left the scientific design untouched: the
tasks, prompts, starter kit, hidden-evaluator hashes, scoring, sample sizes, schedule, and the
pre-registered analysis.
"""

from __future__ import annotations

import hashlib
import json
import re

import pytest

from rc_experiments.config import EXPERIMENTS_DIR, RESULTS_DIR, Config
from rc_experiments.freeze import FREEZE_PATH, combined_hash
from rc_experiments.trials import make_schedule

HISTORY = EXPERIMENTS_DIR / "freeze-history"
FREEZE_14 = json.loads((HISTORY / "FREEZE-1.4.json").read_text(encoding="utf-8"))
PROTOCOL_14 = (HISTORY / "PROTOCOL-1.4.md").read_text(encoding="utf-8")
PROTOCOL = (EXPERIMENTS_DIR / "docs" / "PROTOCOL.md").read_text(encoding="utf-8")
CONFIG_14 = Config.load(HISTORY / "experiment-1.4.json")
ORIGINAL_COMBINED = "b910a7b7afd0a1fd48d76e549eb01e0988f96b5d587eb22c159e846b00a9822c"
# Everything outside these paths was frozen in 1.4 and must still be byte-identical.
CHANGED_IN_1_5 = {
    "experiments/docs/PROTOCOL.md",
    "experiments/experiment.json",
    "experiments/src/rc_experiments/agent.py",
    "experiments/src/rc_experiments/analysis.py",
    "experiments/src/rc_experiments/batch.py",
    "experiments/src/rc_experiments/cli.py",
    "experiments/src/rc_experiments/evaluators.py",
    "experiments/src/rc_experiments/pipeline.py",
    "experiments/src/rc_experiments/trials.py",
    "experiments/src/rc_experiments/workspace.py",
}


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_the_archive_is_the_original_version_1_4():
    assert FREEZE_14["protocol_version"] == "1.4"
    assert FREEZE_14["combined_sha256"] == ORIGINAL_COMBINED
    assert combined_hash(FREEZE_14["files"]) == ORIGINAL_COMBINED
    assert _sha(HISTORY / "PROTOCOL-1.4.md") == FREEZE_14["files"]["experiments/docs/PROTOCOL.md"]
    assert _sha(HISTORY / "experiment-1.4.json") == FREEZE_14["files"]["experiments/experiment.json"]
    assert "Claude Code 2.1.319 in **interactive mode**" in PROTOCOL_14


def test_the_current_freeze_record_is_version_1_5_and_keeps_the_private_hashes():
    current = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    assert current["protocol_version"] == "1.5"
    assert current["combined_sha256"] != ORIGINAL_COMBINED
    assert current["private_evaluator"] == FREEZE_14["private_evaluator"]


def test_frozen_material_outside_the_session_harness_is_byte_identical():
    """Tasks, prompts, continuation message, starter kit, Docker files, lock, rubric: unchanged."""
    current = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))["files"]
    for path, digest in FREEZE_14["files"].items():
        if path not in CHANGED_IN_1_5:
            assert current.get(path) == digest, path
    assert set(current) - set(FREEZE_14["files"]) == {"experiments/src/rc_experiments/batch.py"}


def _sections(text):
    parts = re.split(r"^(## \d+\..*)$", text, flags=re.MULTILINE)
    return {parts[i].strip(): parts[i + 1] for i in range(1, len(parts) - 1, 2)}


@pytest.mark.parametrize(
    "heading",
    [
        "## 1. Research question and hypotheses",
        "## 3. Scientific programming tasks",
        "## 4. Requirements and scoring rubric",
        "## 5. Metrics",
        "## 6. Number of trials",
        "## 9. Randomisation and ordering",
        "## 11. Statistical analysis plan",
    ],
)
def test_the_scientific_sections_of_the_protocol_are_unchanged(heading):
    assert _sections(PROTOCOL)[heading] == _sections(PROTOCOL_14)[heading]


def test_the_configuration_changes_only_session_mode_and_billing_safeguards(config):
    before, after = CONFIG_14.raw, config.raw
    for key in ("research_question", "primary_hypothesis", "conditions", "tasks", "case_categories", "design"):
        assert after[key] == before[key], key
    for key in ("evaluation", "metrics", "analysis"):
        assert after[key] == before[key], key
    unchanged_agent = {k: v for k, v in before["agent"].items() if k != "session_mode"}
    assert {k: after["agent"][k] for k in unchanged_agent} == unchanged_agent
    assert set(after["agent"]) - set(before["agent"]) == {"session_mode_history", "noninteractive"}
    assert {k: after["billing"][k] for k in before["billing"]} == before["billing"]


def test_the_randomised_schedule_is_unchanged(config):
    assert make_schedule(config) == make_schedule(CONFIG_14)
    committed = json.loads((RESULTS_DIR / "schedule.json").read_text(encoding="utf-8"))
    assert [t["trial_id"] for t in committed["trials"]] == [t.trial_id for t in make_schedule(config)]


def test_the_amendment_is_recorded_transparently():
    table = PROTOCOL[PROTOCOL.index("## 13. Amendments") :]
    rows = [row for row in table.splitlines() if row.startswith("| 2026-")]
    first_row = next(row for row in rows if "**Version 1.5" in row)
    assert first_row.startswith("| 2026-11-16 | header, 2, 7, 7.1, 8, 10, 12 | **Version 1.5, during data collection")
    assert rows.index(first_row) == 1  # newest amendment first, after the pre-freeze drafting row
    for phrase in (
        "serial-dilution--B--r01",
        "b910a7b7afd0a1fd",
        "stays in the primary analysis",
        "Exploratory addition",
        "never `--bare`",
        "experiments/freeze-history/",
        "randomised schedule (section 9)",
        "pre-registered analysis (section 11)",
    ):
        assert phrase in first_row, phrase


def test_the_recorded_interactive_trials_match_the_local_results(config):
    """Where the (untracked) results are present, the configuration lists exactly the interactive trials."""
    listed = set(config.agent["session_mode_history"][0]["trials"])
    found = {}
    for kind in ("pilot", "genuine"):
        for record_path in (RESULTS_DIR / kind).glob("*/trial.json"):
            record = json.loads(record_path.read_text(encoding="utf-8"))
            found[record["trial_id"]] = record
    if not found:
        pytest.skip("no local trial results (they are not in the repository)")
    interactive = {t for t, r in found.items() if (r.get("agent") or {}).get("mode") == "manual-session"}
    assert interactive == listed
    for trial_id in listed:
        evaluation = json.loads((RESULTS_DIR / found[trial_id]["data_kind"] / trial_id / "evaluation.json").read_text())
        assert evaluation["freeze"]["combined_sha256"] == ORIGINAL_COMBINED
        assert found[trial_id]["protocol_version"] == "1.4"
