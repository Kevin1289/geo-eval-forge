"""``geoeval`` command-line interface.

    geoeval validate                 # schema-check every task
    geoeval run [--offline|--live]   # grade the candidate library -> results.json
        [--adapter vertex --model M] #   ...and add a live model baseline row
    geoeval judge [--adapter ...]    # LLM-as-judge calibration (reports agreement)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import loader, runner, score
from .models import Candidate

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "results" / "results.json"
GEOJSON_DIR = ROOT / "results" / "geojson"


def cmd_validate(_args) -> int:
    schema_ok, errors = 0, []
    from jsonschema import Draft202012Validator
    validator = Draft202012Validator(loader.load_schema())
    for d in loader.task_dirs():
        data = json.loads((d / "task.json").read_text())
        errs = sorted(validator.iter_errors(data), key=lambda e: e.path)
        if errs:
            errors.append((d.name, [e.message for e in errs]))
        else:
            schema_ok += 1
    print(f"validated {schema_ok} task(s)")
    for name, msgs in errors:
        print(f"  ✗ {name}:")
        for m in msgs:
            print(f"      {m}")
    return 1 if errors else 0


def cmd_run(args) -> int:
    mode = "live" if args.live else "offline"
    client = None
    model_label = None
    if args.adapter:
        kwargs = {}
        if args.adapter == "replay":
            kwargs = {"path": args.replay_file or "", "response_field": "response"}
        elif args.adapter == "vertex" and args.model:
            kwargs = {"model": args.model}
        from .adapters import get_adapter
        client = get_adapter(args.adapter, **kwargs)
        model_label = f"{args.adapter}:{args.model or 'default'}"

    graded = []
    for task, candidates in loader.load_all():
        for cand in candidates:
            verdict = runner.run_live(task, cand) if args.live else runner.run_offline(task, cand)
            graded.append((task, cand, verdict))
        if client is not None:
            try:
                produced = runner.produce_model(task, client)
                verdict = runner.grade_produced(task, produced)
            except Exception as exc:  # noqa: BLE001
                produced, verdict = None, runner.Verdict(
                    False, 0.0, f"model error: {type(exc).__name__}: {exc}", None, None)
            graded.append((task, Candidate(name=model_label, label="model", produced=produced), verdict))

    results = score.build_results(graded, mode + (f"+{model_label}" if model_label else ""))
    map_index = score.emit_map_geojson(graded, GEOJSON_DIR)
    out = Path(args.out)
    score.write_results(results, out, map_index)

    _print_summary(results)
    print(f"\nwrote {out}  ({len(map_index)} map layer(s) in {GEOJSON_DIR})")

    if args.check:
        return _invariant_check(graded)
    return 0


def cmd_judge(args) -> int:
    from .judge import run_judge
    client = None
    if args.adapter and args.adapter != "replay":
        from .adapters import get_adapter
        client = get_adapter(args.adapter, **({"model": args.model} if args.model else {}))
    report = run_judge(client)
    print(f"LLM-as-judge calibration: {report['n_labels']} labels, "
          f"human agreement = {report['human_agreement']}")
    for it in report["by_item"]:
        flag = "✓" if it["agree"] else "✗"
        print(f"  {flag} {it['id']}: judge={it['judge']} human={it['human']}")
    # patch results.json if present so the dashboard shows the measured agreement
    out = Path(args.out)
    if out.exists():
        data = json.loads(out.read_text())
        data["judge"] = {k: report[k] for k in ("calibrated", "n_labels", "human_agreement")}
        out.write_text(json.dumps(data, indent=2))
        print(f"updated judge panel in {out}")
    return 0


def cmd_export(args) -> int:
    from .export import write
    out_dir = Path(args.out)
    n_rec, n_pairs = write(out_dir)
    print(f"wrote {n_rec} records          -> {out_dir / 'records.jsonl'}")
    print(f"wrote {n_pairs} preference pairs -> {out_dir / 'preference_pairs.jsonl'}")
    return 0


def _print_summary(results: dict) -> None:
    print(f"\n{results['suite']}  [{results['mode']}]  "
          f"{len(results['tasks'])} tasks, categories: {', '.join(results['categories'])}")
    print("\nLeaderboard:")
    print(f"  {'model':<18}{'overall':>9}{'rejection':>11}")
    for row in results["leaderboard"]:
        ov = "—" if row["overall"] is None else f"{row['overall'] * 100:.0f}%"
        rj = "—" if row["rejection_accuracy"] is None else f"{row['rejection_accuracy'] * 100:.0f}%"
        print(f"  {row['model']:<18}{ov:>9}{rj:>11}")
    if results["failure_taxonomy"]:
        print("\nFailure taxonomy (wrong candidates caught):")
        for f in results["failure_taxonomy"]:
            print(f"  - {f['failure_class']} ×{f['count']}  (e.g. {f['example_task']})")


def _invariant_check(graded) -> int:
    """CI invariant: every 'correct' candidate must pass; every 'wrong' must fail."""
    violations = []
    for task, cand, verdict in graded:
        if cand.label == "correct" and not verdict.passed:
            violations.append(f"CORRECT candidate failed: {task.id}/{cand.name} — {verdict.detail}")
        if cand.label == "wrong" and verdict.passed:
            violations.append(f"WRONG candidate passed: {task.id}/{cand.name} — {verdict.detail}")
    if violations:
        print("\nINVARIANT VIOLATIONS:")
        for v in violations:
            print(f"  ✗ {v}")
        return 1
    print("\n✓ invariants hold: all correct candidates pass, all wrong candidates fail")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="geoeval", description="GeoAI benchmark + eval harness")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("validate", help="schema-check every task")
    sp.set_defaults(func=cmd_validate)

    sp = sub.add_parser("run", help="grade candidates -> results.json")
    g = sp.add_mutually_exclusive_group()
    g.add_argument("--offline", action="store_true", help="grade recorded outputs (default)")
    g.add_argument("--live", action="store_true", help="execute solutions against the live stack")
    sp.add_argument("--adapter", choices=["replay", "vertex"], help="also run a live model baseline")
    sp.add_argument("--model", help="model name for the adapter")
    sp.add_argument("--replay-file", help="JSONL of recorded model responses (replay adapter)")
    sp.add_argument("--out", default=str(DEFAULT_OUT), help="results.json path")
    sp.add_argument("--check", action="store_true", help="exit non-zero if invariants are violated")
    sp.set_defaults(func=cmd_run)

    sp = sub.add_parser("judge", help="LLM-as-judge calibration (reports human agreement)")
    sp.add_argument("--adapter", choices=["replay", "vertex"], default="replay")
    sp.add_argument("--model", help="model name for the adapter")
    sp.add_argument("--out", default=str(DEFAULT_OUT), help="results.json to patch with the agreement")
    sp.set_defaults(func=cmd_judge)

    sp = sub.add_parser("export", help="export AI-training data (records + preference pairs) as JSONL")
    sp.add_argument("--out", default=str(ROOT / "dataset"), help="output directory")
    sp.set_defaults(func=cmd_export)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
