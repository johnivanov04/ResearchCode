"""Summarise evaluated trials as pre-registered (protocol section 11).

``analyse(results_root, out_dir)`` reads every ``trial.json`` + ``evaluation.json`` below
``results_root`` and writes ``analysis.json``, ``report.md``, and figures to ``out_dir``.

* All trials must have the same data kind. Fixture (dry-run) output is labelled on every
  table and figure as not being experimental results.
* Only valid trials are analysed; genuine trials must also match the freeze record. Every
  excluded trial is listed with its reason.
* The primary estimand is the mean over tasks of the difference in mean hidden pass rate
  (B - A). Its uncertainty is a stratified percentile bootstrap. The permutation test is
  reported only if every task x condition cell has enough valid trials; otherwise the
  results are explicitly descriptive.
* Secondary metrics are descriptive (means, medians, bootstrap intervals; no p-values).
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import numpy as np
from matplotlib.figure import Figure

from rc_experiments.config import Config
from rc_experiments.trials import now_utc, read_json, write_json

FIXTURE_LABEL = "FIXTURE DATA - NOT EXPERIMENTAL RESULTS"
PILOT_LABEL = "PILOT DATA - EXCLUDED FROM THE CONFIRMATORY ANALYSIS"
# Okabe-Ito colours (distinguishable with common colour-vision deficiencies); conditions are
# also distinguished by marker shape and labelled in every legend.
CONDITION_STYLE = {"A": {"color": "#D55E00", "marker": "o"}, "B": {"color": "#0072B2", "marker": "s"}}

SECONDARY: tuple[tuple[str, str, bool], ...] = (
    # (row key, label, higher is better)
    ("category_balanced_pass_rate", "Category-balanced hidden pass rate (sensitivity)", True),
    ("mutation_score", "Mutation score of own tests", True),
    ("median_rel_error", "Median relative error, known-answer cases", False),
    ("security_findings", "Static security findings", False),
    ("lint_per_100_lines", "Lint findings per 100 lines", False),
    ("extra_dependencies", "Undeclared or extra runtime dependencies", False),
    ("tests_collected", "Own tests collected", True),
    ("wall_clock_minutes", "Wall-clock minutes", False),
    ("assistant_messages", "Assistant messages (session log)", False),
    ("output_tokens", "Output tokens (session log)", False),
)


class AnalysisError(RuntimeError):
    pass


# --------------------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------------------


def trial_row(record: dict[str, Any], evaluation: dict[str, Any]) -> dict[str, Any]:
    hidden = evaluation["hidden"]["summary"]
    own = evaluation.get("own_tests") or {}
    static = evaluation["static"]
    agent = record.get("agent") or {}
    seconds = agent.get("wall_clock_seconds")
    return {
        "trial_id": record["trial_id"],
        "task": record["task"],
        "condition": record["condition"],
        "replicate": record["replicate"],
        "data_kind": record["data_kind"],
        "validity": record.get("validity"),
        "validity_reason": record.get("validity_reason"),
        "freeze_matches": evaluation["freeze"]["matches"],
        "evaluation_error": evaluation["hidden"].get("evaluation_error"),
        "hidden_pass_rate": hidden["hidden_pass_rate"],
        "category_balanced_pass_rate": hidden.get("category_balanced_pass_rate"),
        "category_pass_rates": {k: v["pass_rate"] for k, v in hidden["categories"].items()},
        "import_failed": hidden["import_failed"],
        "median_rel_error": hidden["median_rel_error_known_answer"],
        "mutation_score": own.get("mutation_score"),
        "tests_collected": own.get("tests_collected"),
        "all_own_tests_pass": own.get("all_own_tests_pass"),
        "security_findings": static["security_findings"],
        "lint_per_100_lines": static["lint_per_100_lines"],
        "extra_dependencies": len(
            set(static["unexpected_runtime_imports"]) | set(static["extra_declared_dependencies"])
        ),
        "wall_clock_minutes": seconds / 60 if isinstance(seconds, int | float) else None,
        "assistant_messages": agent.get("assistant_messages"),
        "human_messages": agent.get("human_messages"),
        "output_tokens": agent.get("output_tokens"),
    }


def load_rows(results_root: Path) -> list[dict[str, Any]]:
    rows = []
    for record_path in sorted(results_root.glob("*/trial.json")):
        evaluation_path = record_path.parent / "evaluation.json"
        if not evaluation_path.is_file():
            continue
        rows.append(trial_row(read_json(record_path), read_json(evaluation_path)))
    return rows


def split_included(rows: Sequence[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    included, excluded = [], []
    for row in rows:
        reason = None
        if row["validity"] != "valid":
            reason = f"validity {row['validity']!r}: {row['validity_reason']}"
        elif row["data_kind"] == "genuine" and not row["freeze_matches"]:
            reason = "evaluated with files that differ from the freeze record"
        elif row["evaluation_error"]:
            reason = f"evaluation error: {row['evaluation_error']}"
        if reason:
            excluded.append({"trial_id": row["trial_id"], "reason": reason})
        else:
            included.append(row)
    return included, excluded


# --------------------------------------------------------------------------------------
# Statistics
# --------------------------------------------------------------------------------------


def describe(values: Sequence[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0, "mean": None, "sd": None, "median": None, "min": None, "max": None}
    return {
        "n": len(values),
        "mean": statistics.fmean(values),
        "sd": statistics.stdev(values) if len(values) > 1 else None,
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
    }


def cells(
    rows: Sequence[dict[str, Any]], key: Callable[[dict[str, Any]], Any], tasks: Sequence[str]
) -> dict[str, dict[str, list[float]]]:
    """Values per task and condition, ignoring missing (None) values."""
    out: dict[str, dict[str, list[float]]] = {t: {"A": [], "B": []} for t in tasks}
    for row in rows:
        value = key(row)
        if value is not None and not (isinstance(value, float) and math.isnan(value)):
            out[row["task"]][row["condition"]].append(float(value))
    return out


def delta(cell_values: dict[str, dict[str, list[float]]]) -> float | None:
    """Mean over tasks of (mean B - mean A); None unless every task has values in both conditions."""
    diffs = []
    for by_condition in cell_values.values():
        if not by_condition["A"] or not by_condition["B"]:
            return None
        diffs.append(statistics.fmean(by_condition["B"]) - statistics.fmean(by_condition["A"]))
    return statistics.fmean(diffs) if diffs else None


def bootstrap_delta(
    cell_values: dict[str, dict[str, list[float]]], resamples: int, level: float, seed: int
) -> tuple[float, float] | None:
    """Percentile CI for ``delta``, resampling trials within each task x condition cell."""
    if delta(cell_values) is None:
        return None
    rng = np.random.default_rng(seed)
    diffs = np.zeros(resamples)
    for by_condition in cell_values.values():
        means = {}
        for condition in ("A", "B"):
            values = np.asarray(by_condition[condition])
            draws = rng.integers(0, values.size, size=(resamples, values.size))
            means[condition] = values[draws].mean(axis=1)
        diffs += means["B"] - means["A"]
    diffs /= len(cell_values)
    alpha = (1 - level) / 2
    return float(np.quantile(diffs, alpha)), float(np.quantile(diffs, 1 - alpha))


def permutation_p(cell_values: dict[str, dict[str, list[float]]], resamples: int, seed: int) -> float | None:
    """Two-sided stratified permutation test of delta = 0 (labels shuffled within each task)."""
    observed = delta(cell_values)
    if observed is None:
        return None
    rng = np.random.default_rng(seed)
    total = np.zeros(resamples)
    for by_condition in cell_values.values():
        pooled = np.asarray(by_condition["A"] + by_condition["B"])
        n_a = len(by_condition["A"])
        permuted = rng.permuted(np.tile(pooled, (resamples, 1)), axis=1)
        total += permuted[:, n_a:].mean(axis=1) - permuted[:, :n_a].mean(axis=1)
    total /= len(cell_values)
    extreme = np.sum(np.abs(total) >= abs(observed) - 1e-12)
    return float((extreme + 1) / (resamples + 1))


def condition_summary(
    cell_values: dict[str, dict[str, list[float]]], resamples: int, level: float, seed: int
) -> dict[str, Any]:
    per_task = {
        task: {c: describe(v) for c, v in by_condition.items()}
        | {
            "difference_B_minus_A": (statistics.fmean(by_condition["B"]) - statistics.fmean(by_condition["A"]))
            if by_condition["A"] and by_condition["B"]
            else None,
            "difference_ci": bootstrap_delta({task: by_condition}, resamples, level, seed),
        }
        for task, by_condition in cell_values.items()
    }
    pooled = {c: describe([v for by in cell_values.values() for v in by[c]]) for c in ("A", "B")}
    return {
        "per_task": per_task,
        "pooled": pooled,
        "difference_B_minus_A": delta(cell_values),
        "difference_ci": bootstrap_delta(cell_values, resamples, level, seed),
    }


# --------------------------------------------------------------------------------------
# Figures and report
# --------------------------------------------------------------------------------------


def _label(kind: str) -> str | None:
    return {"fixture": FIXTURE_LABEL, "pilot": PILOT_LABEL}.get(kind)


def dot_plot(
    cell_values: dict[str, dict[str, list[float]]],
    title: str,
    ylabel: str,
    kind: str,
    path: Path,
    ylim: tuple[float, float] | None = None,
) -> None:
    """Every trial as a dot, with the cell mean as a short line, per task and condition."""
    tasks = list(cell_values)
    figure = Figure(figsize=(7.5, 4.2), dpi=150)
    ax = figure.add_subplot()
    for t_index, task in enumerate(tasks):
        for offset, condition in ((-0.18, "A"), (0.18, "B")):
            values = cell_values[task][condition]
            style = CONDITION_STYLE[condition]
            x = t_index + offset
            spread = np.linspace(-0.07, 0.07, len(values)) if len(values) > 1 else np.zeros(len(values))
            ax.scatter(
                x + spread,
                values,
                s=26,
                color=style["color"],
                marker=style["marker"],
                alpha=0.85,
                edgecolors="white",
                linewidths=0.6,
                zorder=3,
                label=f"Condition {condition}" if t_index == 0 else None,
            )
            if values:
                mean = statistics.fmean(values)
                ax.hlines(mean, x - 0.12, x + 0.12, color="#1A1A1A", linewidth=2, zorder=4)
    ax.set_xticks(range(len(tasks)), tasks)
    ax.set_ylabel(ylabel)
    if ylim:
        ax.set_ylim(*ylim)
    ax.grid(axis="y", color="#DDDDDD", linewidth=0.6)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.legend(frameon=False, loc="lower right", title="Dots: trials; bars: means", title_fontsize=8, fontsize=8)
    label = _label(kind)
    ax.set_title(f"{title}\n{label}" if label else title, fontsize=10, color="#B00020" if label else "#1A1A1A")
    figure.tight_layout()
    figure.savefig(path, metadata={"Software": None})


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _ci(ci: tuple[float, float] | None) -> str:
    return "-" if ci is None else f"[{ci[0]:.3f}, {ci[1]:.3f}]"


def write_report(result: dict[str, Any], path: Path) -> None:
    kind = result["data_kind"]
    lines = []
    label = _label(kind)
    if label:
        lines += [f"> **{label}.**", ""]
    lines += [f"# Phase 4 analysis ({kind} data)", "", f"Generated {result['generated_at']} by `rc-exp analyze`.", ""]
    lines += [
        f"- Trials found: {result['trials_found']}; analysed: {result['trials_included']}; "
        f"excluded: {len(result['excluded'])}.",
        f"- Inference: {result['inference']['note']}",
        "",
        "## Sample size: planned and achieved",
        "",
        "| Task | Condition | Planned | Valid trials analysed |",
        "| --- | --- | --- | --- |",
        *[
            f"| {cell['task']} | {cell['condition']} | {cell['planned']} | {cell['achieved']} |"
            for cell in result["sample_size"]["cells"]
        ],
        "",
        result["sample_size"]["limitations"],
        "",
    ]
    primary = result["primary"]
    lines += [
        "## Primary metric: hidden pass rate",
        "",
        "| Task | A: n | A: mean | A: median | B: n | B: mean | B: median | B - A | 95% CI |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for task, cell in primary["per_task"].items():
        lines.append(
            f"| {task} | {cell['A']['n']} | {_fmt(cell['A']['mean'])} | {_fmt(cell['A']['median'])} | "
            f"{cell['B']['n']} | {_fmt(cell['B']['mean'])} | {_fmt(cell['B']['median'])} | "
            f"{_fmt(cell['difference_B_minus_A'])} | {_ci(cell['difference_ci'])} |"
        )
    lines += [
        "",
        f"Mean over tasks of (B - A): **{_fmt(primary['difference_B_minus_A'])}**, "
        f"95% bootstrap CI {_ci(primary['difference_ci'])}.",
        "",
    ]
    if result["inference"]["permutation_p"] is not None:
        lines += [f"Stratified permutation test (two-sided): p = {result['inference']['permutation_p']:.4f}.", ""]
    lines += [
        "## Hidden pass rate by case category",
        "",
        "| Category | A: mean | B: mean | B - A | 95% CI |",
        "| --- | --- | --- | --- | --- |",
    ]
    for category, summary in result["categories"].items():
        lines.append(
            f"| {category} | {_fmt(summary['pooled']['A']['mean'])} | {_fmt(summary['pooled']['B']['mean'])} "
            f"| {_fmt(summary['difference_B_minus_A'])} | {_ci(summary['difference_ci'])} |"
        )
    lines += [
        "",
        "## Secondary metrics (descriptive)",
        "",
        "| Metric | A: n | A: mean | A: median | B: n | B: mean | B: median | B - A | 95% CI |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for key, label_text, _ in SECONDARY:
        summary = result["secondary"][key]
        a, b = summary["pooled"]["A"], summary["pooled"]["B"]
        lines.append(
            f"| {label_text} | {a['n']} | {_fmt(a['mean'])} | {_fmt(a['median'])} | {b['n']} | "
            f"{_fmt(b['mean'])} | {_fmt(b['median'])} | {_fmt(summary['difference_B_minus_A'])} | "
            f"{_ci(summary['difference_ci'])} |"
        )
    lines += ["", "Missing values (metrics the tool did not report) are excluded, never estimated.", ""]
    if result["excluded"]:
        lines += ["## Excluded trials", "", "| Trial | Reason |", "| --- | --- |"]
        lines += [f"| {e['trial_id']} | {e['reason']} |" for e in result["excluded"]]
        lines.append("")
    lines += [
        "## Trials",
        "",
        "| Trial | Hidden pass rate | Import failed | Mutation score | Minutes |",
        "| --- | --- | --- | --- | --- |",
    ]
    lines += [
        f"| {r['trial_id']} | {_fmt(r['hidden_pass_rate'])} | {r['import_failed']} | "
        f"{_fmt(r['mutation_score'])} | {_fmt(r['wall_clock_minutes'], 1)} |"
        for r in result["rows"]
    ]
    if label:
        lines += ["", f"> **{label}.**"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------------------


def analyse(results_root: Path, out_dir: Path, config: Config) -> dict[str, Any]:
    rows = load_rows(results_root)
    if not rows:
        raise AnalysisError(f"no evaluated trials under {results_root}")
    kinds = {row["data_kind"] for row in rows}
    if len(kinds) != 1:
        raise AnalysisError(f"refusing to mix data kinds {sorted(kinds)}; analyse each separately")
    kind = kinds.pop()
    out_dir.mkdir(parents=True, exist_ok=True)
    if any(out_dir.iterdir()):
        raise FileExistsError(f"{out_dir} is not empty; analysis output is never overwritten")

    settings = config.analysis
    resamples, level, seed = settings["bootstrap_resamples"], settings["confidence_level"], settings["seed"]
    included, excluded = split_included(rows)
    # Fixture dry runs use the public practice tasks; genuine and pilot data use the experiment's tasks.
    tasks = sorted({row["task"] for row in rows}) if kind == "fixture" else config.task_ids
    primary_cells = cells(included, lambda r: r["hidden_pass_rate"], tasks)
    min_n = config.design["minimum_valid_trials_per_cell_for_inference"]
    smallest = min(len(v) for by in primary_cells.values() for v in by.values())
    inferential = kind == "genuine" and smallest >= min_n
    p_value = permutation_p(primary_cells, settings["permutation_resamples"], seed) if inferential else None
    if inferential:
        note = f"every cell has at least {min_n} valid trials; the pre-registered permutation test is reported"
    elif kind != "genuine":
        note = f"{kind} data: descriptive only, no hypothesis test"
    else:
        note = (
            f"the smallest cell has {smallest} valid trials (< {min_n}); results are descriptive only and "
            "no hypothesis test is reported"
        )

    planned = config.design["pilot_trials_per_cell" if kind == "pilot" else "confirmatory_trials_per_cell"]
    achieved = {(t, c): len(primary_cells[t][c]) for t in tasks for c in ("A", "B")}
    total_planned, total_achieved = planned * len(achieved), sum(achieved.values())
    if total_achieved < total_planned:
        limitations = (
            f"Only {total_achieved} of {total_planned} planned valid trials were analysed. With so few trials per "
            "cell, the intervals are wide, a real difference of moderate size can easily be missed, and an observed "
            "difference can arise by chance. The results describe these trials only and do not establish whether "
            "either workflow is more reliable."
        )
    else:
        limitations = (
            f"All {total_planned} planned valid trials were analysed. Ten trials per cell can show only large "
            "differences; the results apply to this agent, model, prompt pair, and task set."
        )
    result: dict[str, Any] = {
        "sample_size": {
            "planned_per_cell": planned,
            "cells": [{"task": t, "condition": c, "planned": planned, "achieved": n} for (t, c), n in achieved.items()],
            "planned_total": total_planned,
            "achieved_total": total_achieved,
            "limitations": limitations,
        },
        "data_kind": kind,
        "label": _label(kind),
        "generated_at": now_utc(),
        "protocol_version": config.protocol_version,
        "trials_found": len(rows),
        "trials_included": len(included),
        "excluded": excluded,
        "inference": {"inferential": inferential, "permutation_p": p_value, "alpha": settings["alpha"], "note": note},
        "primary": condition_summary(primary_cells, resamples, level, seed),
        "categories": {
            category: condition_summary(
                cells(included, lambda r, c=category: r["category_pass_rates"].get(c), tasks), resamples, level, seed
            )
            for category in config.categories
        },
        "secondary": {
            key: condition_summary(cells(included, lambda r, k=key: r[k], tasks), resamples, level, seed)
            for key, _, _ in SECONDARY
        },
        "rows": included,
    }
    write_json(out_dir / "analysis.json", result)
    write_report(result, out_dir / "report.md")
    figures = out_dir / "figures"
    figures.mkdir()
    dot_plot(
        primary_cells,
        "Hidden pass rate per trial",
        "Share of hidden cases passed",
        kind,
        figures / "hidden_pass_rate.png",
        (-0.02, 1.02),
    )
    dot_plot(
        cells(included, lambda r: r["mutation_score"], tasks),
        "Mutation score of each submission's own tests",
        "Share of known defects detected",
        kind,
        figures / "mutation_score.png",
        (-0.02, 1.02),
    )
    effort = cells(included, lambda r: r["wall_clock_minutes"], tasks)
    if any(v for by in effort.values() for v in by.values()):
        dot_plot(effort, "Wall-clock time per trial", "Minutes", kind, figures / "wall_clock_minutes.png")
    return result
