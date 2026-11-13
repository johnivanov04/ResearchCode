"""`rc-exp`: command-line interface to the Phase 4 experiment harness (protocol 1.1).

No command calls a model by itself. Trials are run as manual Claude Code sessions through the
experimenter's Claude Pro subscription (`rc-exp session`), started and ended by the operator.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

from rc_experiments import agent as agent_module
from rc_experiments.analysis import analyse
from rc_experiments.blind import make_packets
from rc_experiments.config import EXPERIMENTS_DIR, RESULTS_DIR, Config
from rc_experiments.dryrun import dry_run
from rc_experiments.evaluators import load_fixture, load_genuine
from rc_experiments.freeze import verify_freeze, write_freeze
from rc_experiments.pipeline import collect, evaluate_collected, results_dir_for
from rc_experiments.sandbox import SANDBOX_IMAGE, DockerBackend, LocalBackend
from rc_experiments.trials import TrialId, make_schedule, read_json, schedule_document, update_record, write_json
from rc_experiments.validation import VALIDATION_PATH, validate_evaluator
from rc_experiments.workspace import prepare

DEFAULT_TRIALS_ROOT = Path.home() / "researchcode-trials"
SCHEDULE_PATH = RESULTS_DIR / "schedule.json"


def _backend(name: str, config: Config, *, trusted: bool = False):
    if name == "docker":
        return DockerBackend(config)
    return LocalBackend(trusted=trusted)


def _kind_for(trial: TrialId) -> str:
    return "pilot" if trial.is_pilot else "genuine"


def _require_freeze() -> None:
    result = verify_freeze(require_private=True)
    if result["mismatches"]:
        raise SystemExit(
            "files differ from FREEZE.json; genuine and pilot trials require the frozen protocol:\n  "
            + "\n  ".join(result["mismatches"][:20])
        )


def _warn_forbidden() -> None:
    found = agent_module.forbidden_variables_set()
    if found:
        print(
            f"warning: {', '.join(found)} set on this machine. They are never passed into trial containers "
            "(trials use only the subscription token), but unset them if you do not need them.",
            file=sys.stderr,
        )


def _done_trials() -> set[str]:
    done = set()
    for kind in ("pilot", "genuine"):
        for record in (RESULTS_DIR / kind).glob("*/trial.json"):
            done.add(record.parent.name)
    return done


def cmd_schedule(args: argparse.Namespace, config: Config) -> int:
    document = schedule_document(config)
    if args.write:
        write_json(SCHEDULE_PATH, document)
        print(f"wrote {SCHEDULE_PATH}")
    else:
        for item in document["trials"]:
            print(f"{item['order']:3d}  block {item['block']:2d}  {item['phase']:12s}  {item['trial_id']}")
    return 0


def cmd_next(args: argparse.Namespace, config: Config) -> int:
    done = _done_trials()
    for item in make_schedule(config):
        if item.trial_id not in done:
            print(f"next trial: {item.trial_id}  (order {item.order}, block {item.block}, {item.phase})")
            return 0
    print("every scheduled trial has been collected")
    return 0


def cmd_progress(args: argparse.Namespace, config: Config) -> int:
    rows = []
    for kind in ("pilot", "genuine"):
        for record_path in sorted((RESULTS_DIR / kind).glob("*/trial.json")):
            record = read_json(record_path)
            rows.append((kind, record["task"], record["condition"], record.get("validity")))
    valid = Counter((k, t, c) for k, t, c, v in rows if v == "valid")
    planned = {
        "pilot": config.design["pilot_trials_per_cell"],
        "genuine": config.design["confirmatory_trials_per_cell"],
    }
    for kind in ("pilot", "genuine"):
        print(f"{kind} (valid / planned per cell):")
        for task in config.task_ids:
            cells = "  ".join(f"{c}: {valid[(kind, task, c)]}/{planned[kind]}" for c in config.condition_ids)
            print(f"  {task:16s} {cells}")
    other = [r for r in rows if r[3] != "valid"]
    print(f"trials not valid (invalid or awaiting review): {len(other)}")
    return 0


def cmd_prepare(args: argparse.Namespace, config: Config) -> int:
    trial = TrialId.parse(args.trial)
    _require_freeze()
    trial_dir = prepare(trial, args.trials_root, config, _kind_for(trial))
    print(trial_dir)
    return 0


def cmd_preflight(args: argparse.Namespace, config: Config) -> int:
    _warn_forbidden()
    print(
        "Opening Claude Code with an empty directory and NO prompt (no trial). Check:\n"
        "  /status  -> logged in with your Claude subscription (not an API key or Console account)\n"
        f"  /model   -> {config.agent['model']} is available and selected\n"
        "  /usage   -> enough plan usage left for the next session(s)\n"
        "Then type /exit. Do not send any other message.\n"
    )
    agent_module.preflight(config)
    return 0


def cmd_session(args: argparse.Namespace, config: Config) -> int:
    _warn_forbidden()
    _require_freeze()
    trial = TrialId.parse(args.trial)
    trial_dir = args.trials_root / args.trial
    if not trial_dir.exists():
        trial_dir = prepare(trial, args.trials_root, config, _kind_for(trial))
        print(f"prepared {trial_dir}")
    continuation = agent_module.CONTINUE_MESSAGE_PATH.read_text(encoding="utf-8").strip()
    print(
        f"\nStarting {args.trial}: Claude Code opens with the trial prompt already entered.\n"
        "  1. Accept Claude Code's startup dialogs (theme, trusting /workspace, permission mode) if shown.\n"
        "  2. Do not type anything while the agent works.\n"
        "  3. If the agent stops to ask a question before finishing, send exactly this message\n"
        f"     (at most {config.agent['max_continuation_messages']} times):\n       {continuation}\n"
        "  4. When the agent says it has finished, type /exit.\n"
        f"  The container stops automatically after {config.agent['wall_clock_limit_minutes']} minutes.\n"
        "  If Claude Code reports a usage limit or extra usage, type /exit immediately.\n"
    )
    result = agent_module.session(trial_dir, config)
    record = read_json(trial_dir / "trial.json")
    print(
        json.dumps(
            {
                k: result.get(k)
                for k in ("wall_clock_seconds", "timed_out", "assistant_messages", "main_models", "output_tokens")
            },
            indent=2,
        )
    )
    print(f"validity: {record['validity']} ({record['validity_reason']})")
    if args.collect:
        result_dir = collect(trial_dir, results_dir_for(_kind_for(trial)))
        print(f"collected into {result_dir}")
        evaluation = evaluate_collected(result_dir, _backend("docker", config), config)
        print(f"hidden pass rate {evaluation['hidden']['summary']['hidden_pass_rate']:.3f}")
    return 0


def cmd_set_validity(args: argparse.Namespace, config: Config) -> int:
    for root in (
        args.trials_root / args.trial,
        RESULTS_DIR / "genuine" / args.trial,
        RESULTS_DIR / "pilot" / args.trial,
    ):
        if (root / "trial.json").is_file():
            update_record(root, validity=args.validity, validity_reason=args.reason)
            print(f"{root}: {args.validity} ({args.reason})")
    return 0


def cmd_collect(args: argparse.Namespace, config: Config) -> int:
    trial = TrialId.parse(args.trial)
    print(collect(args.trials_root / args.trial, results_dir_for(_kind_for(trial))))
    return 0


def cmd_evaluate(args: argparse.Namespace, config: Config) -> int:
    trial = TrialId.parse(args.trial)
    result_dir = results_dir_for(_kind_for(trial)) / args.trial
    evaluation = evaluate_collected(result_dir, _backend("docker", config), config)
    summary = evaluation["hidden"]["summary"]
    print(
        f"{args.trial}: hidden {summary['passed']}/{summary['cases']}; "
        f"mutation score {evaluation['own_tests']['mutation_score']}"
    )
    return 0


def cmd_analyze(args: argparse.Namespace, config: Config) -> int:
    root = args.results or (RESULTS_DIR / args.kind)
    out = args.out or (RESULTS_DIR / "analysis" / args.kind)
    result = analyse(root, out, config)
    print(f"{result['trials_included']} trials analysed ({result['data_kind']}); {result['inference']['note']}")
    print(f"report: {out / 'report.md'}")
    return 0


def cmd_validate_evaluator(args: argparse.Namespace, config: Config) -> int:
    backend = _backend(args.backend, config, trusted=True)  # references and mutants are trusted code
    evaluator = load_genuine() if args.evaluator == "genuine" else load_fixture()
    result = validate_evaluator(evaluator, backend, config)
    for task, summary in result["tasks"].items():
        print(
            f"{task}: {summary['cases']} cases; reference {summary['reference_pass_rate']:.0%}; "
            f"{summary['mutants_detected']}/{len(summary['mutants'])} defects detected"
        )
        for mutant in summary["mutants"]:
            print(f"    {mutant['name']:28s} {mutant['pass_rate']:.0%}  ({mutant['cases_failed']} cases failed)")
    if args.write:
        if evaluator.kind != "genuine":
            raise SystemExit("only the genuine evaluator's validation is written to the documentation")
        write_json(VALIDATION_PATH, result)
        print(f"wrote {VALIDATION_PATH}")
    if result["problems"]:
        print("PROBLEMS:\n  " + "\n  ".join(result["problems"]), file=sys.stderr)
        return 1
    return 0


def cmd_dry_run(args: argparse.Namespace, config: Config) -> int:
    backend = _backend(args.backend, config, trusted=True)  # fixtures are trusted code
    result = dry_run(args.out, backend, config, replicates=args.replicates, own_tests=not args.skip_own_tests)
    print(json.dumps(result, indent=2))
    return 0


def cmd_freeze(args: argparse.Namespace, config: Config) -> int:
    if args.check:
        result = verify_freeze(require_private=args.require_private)
        if result["mismatches"]:
            print("files differ from FREEZE.json:\n  " + "\n  ".join(result["mismatches"]))
            return 1
        scope = (
            "public and private" if result["private_checked"] else "public (private evaluator not present, not checked)"
        )
        print(f"all frozen {scope} files match FREEZE.json ({result['combined_sha256'][:16]})")
        return 0
    document = write_freeze(config.protocol_version, args.note)
    print(f"froze {len(document['files'])} files; combined SHA-256 {document['combined_sha256'][:16]}")
    return 0


def cmd_review_packets(args: argparse.Namespace, config: Config) -> int:
    print(make_packets(args.results or RESULTS_DIR / "genuine", args.out, args.key, config))
    return 0


def cmd_build_images(args: argparse.Namespace, config: Config) -> int:
    docker = EXPERIMENTS_DIR / "docker"
    builds = [(SANDBOX_IMAGE, docker / "sandbox")]
    if not args.sandbox_only:
        builds += [(agent_module.agent_image(config), docker / "agent"), ("researchcode-proxy:1", docker / "proxy")]
    for tag, context in builds:
        print(f"building {tag}")
        subprocess.run(["docker", "build", "-t", tag, str(context)], check=True)
    return 0


def cmd_network(args: argparse.Namespace, config: Config) -> int:
    def run(*arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["docker", *arguments], capture_output=True, text=True, check=False)

    if args.action == "up":
        run("network", "create", "--internal", agent_module.NETWORK)
        run("rm", "-f", agent_module.PROXY_CONTAINER)
        started = run(
            "run", "-d", "--name", agent_module.PROXY_CONTAINER, "--network", "bridge", "researchcode-proxy:1"
        )
        if started.returncode != 0:
            raise SystemExit(started.stderr)
        run("network", "connect", agent_module.NETWORK, agent_module.PROXY_CONTAINER)
        print(f"proxy {agent_module.PROXY_CONTAINER} running; agent network {agent_module.NETWORK} (internal)")
    else:
        run("rm", "-f", agent_module.PROXY_CONTAINER)
        run("network", "rm", agent_module.NETWORK)
        print("proxy and agent network removed")
    return 0


def cmd_check(args: argparse.Namespace, config: Config) -> int:
    _warn_forbidden()
    problems = agent_module.check_environment(config)
    freeze = verify_freeze(require_private=True)["mismatches"]
    if freeze:
        problems.append(f"{len(freeze)} files differ from FREEZE.json")
    print("ready for manual sessions" if not problems else "not ready:\n  " + "\n  ".join(problems))
    return 1 if problems else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rc-exp",
        description="ResearchCode Phase 4 experiment harness. No command calls a model by itself.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def trial_command(name: str, func, help_text: str) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("trial", help="trial id, e.g. calibration--A--p01")
        p.add_argument(
            "--trials-root",
            type=Path,
            default=DEFAULT_TRIALS_ROOT,
            help=f"directory for trial workspaces, outside the repository (default {DEFAULT_TRIALS_ROOT})",
        )
        p.set_defaults(func=func)
        return p

    p = sub.add_parser("schedule", help="print or write the randomised trial schedule")
    p.add_argument("--write", action="store_true", help=f"write {SCHEDULE_PATH.relative_to(EXPERIMENTS_DIR)}")
    p.set_defaults(func=cmd_schedule)
    sub.add_parser("next", help="show the next trial in the schedule").set_defaults(func=cmd_next)
    sub.add_parser("progress", help="valid trials collected per task and condition").set_defaults(func=cmd_progress)
    sub.add_parser("preflight", help="open Claude Code without a task to check login, model, and usage").set_defaults(
        func=cmd_preflight
    )
    trial_command("prepare", cmd_prepare, "create a clean workspace for a trial")
    p = trial_command("session", cmd_session, "run a trial as a manual Claude Code session (subscription)")
    p.add_argument("--collect", action="store_true", help="collect and evaluate the trial after the session")
    p = trial_command("set-validity", cmd_set_validity, "record the operator's validity decision (protocol section 10)")
    p.add_argument("validity", choices=["valid", "invalid"])
    p.add_argument("--reason", required=True)
    trial_command("collect", cmd_collect, "copy a finished trial into experiments/results")
    trial_command("evaluate", cmd_evaluate, "evaluate a collected trial in the Docker sandbox")

    p = sub.add_parser("analyze", help="summarise evaluated trials (protocol section 11)")
    p.add_argument("--kind", choices=["genuine", "pilot"], default="genuine")
    p.add_argument("--results", type=Path, help="results directory (default experiments/results/<kind>)")
    p.add_argument("--out", type=Path, help="output directory (default experiments/results/analysis/<kind>)")
    p.set_defaults(func=cmd_analyze)

    p = sub.add_parser("validate-evaluator", help="score references and defective variants")
    p.add_argument(
        "--evaluator",
        choices=["genuine", "fixture"],
        default="genuine",
        help="genuine (private; needs the private evaluator) or fixture (public practice tasks)",
    )
    p.add_argument("--backend", choices=["docker", "local"], default="docker")
    p.add_argument("--write", action="store_true", help=f"write {VALIDATION_PATH.relative_to(EXPERIMENTS_DIR)}")
    p.set_defaults(func=cmd_validate_evaluator)

    p = sub.add_parser("dry-run", help="end-to-end run with labelled fixtures instead of an agent")
    p.add_argument("--out", type=Path, required=True, help="output directory outside experiments/results")
    p.add_argument("--backend", choices=["docker", "local"], default="docker")
    p.add_argument("--replicates", type=int, default=2)
    p.add_argument("--skip-own-tests", action="store_true")
    p.set_defaults(func=cmd_dry_run)

    p = sub.add_parser("freeze", help="write or check FREEZE.json")
    p.add_argument("--check", action="store_true")
    p.add_argument("--require-private", action="store_true", help="fail if the private evaluator is absent")
    p.add_argument("--note", default="Frozen before any trial.")
    p.set_defaults(func=cmd_freeze)

    p = sub.add_parser("review-packets", help="blinded packets for the maintainability review")
    p.add_argument("--results", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--key", type=Path, required=True, help="where to store the blinding key (not given to reviewers)")
    p.set_defaults(func=cmd_review_packets)

    p = sub.add_parser("build-images", help="build the sandbox, agent, and proxy Docker images")
    p.add_argument("--sandbox-only", action="store_true")
    p.set_defaults(func=cmd_build_images)
    p = sub.add_parser("network", help="start or stop the filtering proxy and the internal agent network")
    p.add_argument("action", choices=["up", "down"])
    p.set_defaults(func=cmd_network)
    sub.add_parser("check", help="check that manual sessions can run").set_defaults(func=cmd_check)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args, Config.load()) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
