#!/usr/bin/env python3
"""
Dogfood Report — reusable analysis of dogfood result files.

Usage:
    python report.py                          # all results
    python report.py --scenario coding        # filter by scenario name substring
    python report.py --last 10                # last N runs only
    python report.py --failures-only          # only show runs with failures
    python report.py --json                   # machine-readable output
"""

import argparse
import json
import glob
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"


def load_results(results_dir: Path = RESULTS_DIR) -> list[dict]:
    """Load all result files, flattening aggregates."""
    results = []
    for f in sorted(glob.glob(str(results_dir / "*.json"))):
        with open(f) as fh:
            data = json.load(fh)
        if isinstance(data, list):
            for item in data:
                item["_source_file"] = os.path.basename(f)
                results.append(item)
        elif isinstance(data, dict):
            data["_source_file"] = os.path.basename(f)
            results.append(data)
    return results


def analyze(results: list[dict]) -> dict:
    """Compute per-scenario and overall statistics."""
    scenarios = defaultdict(list)
    for r in results:
        name = r.get("scenario", r.get("_source_file", "unknown"))
        criteria = r.get("criteria", {})
        failed = criteria.get("failed", []) if isinstance(criteria, dict) else []
        passed = criteria.get("passed", []) if isinstance(criteria, dict) else []
        scenarios[name].append({
            "file": r.get("_source_file", ""),
            "score": r.get("score", 0),
            "passed_criteria": passed,
            "failed_criteria": failed,
            "rounds": r.get("rounds_used", 0),
            "time_s": r.get("time_seconds", 0),
            "tokens": r.get("token_usage", {}).get("total", 0) if isinstance(r.get("token_usage"), dict) else r.get("token_usage", 0),
            "timestamp": r.get("timestamp", ""),
        })

    stats = {}
    for name, runs in sorted(scenarios.items()):
        scores = [r["score"] for r in runs]
        full_pass = sum(1 for s in scores if s == 1.0)
        fail_counts = Counter()
        for r in runs:
            for f in r["failed_criteria"]:
                fail_counts[f] += 1
        stats[name] = {
            "runs": len(runs),
            "full_pass": full_pass,
            "pass_rate": full_pass / len(runs) if runs else 0,
            "avg_score": sum(scores) / len(scores) if scores else 0,
            "avg_time": sum(r["time_s"] for r in runs) / len(runs),
            "avg_tokens": sum(r["tokens"] for r in runs) / len(runs),
            "total_tokens": sum(r["tokens"] for r in runs),
            "failure_hotspots": dict(fail_counts),
            "recent": runs[-5:],
        }
    return stats


def print_report(stats: dict, failures_only: bool = False):
    """Print human-readable report."""
    total_runs = sum(s["runs"] for s in stats.values())
    total_100 = sum(s["full_pass"] for s in stats.values())
    total_tokens = sum(s["total_tokens"] for s in stats.values())

    print("=" * 70)
    print("DOGFOOD RESULTS REPORT")
    print("=" * 70)

    for name, s in sorted(stats.items(), key=lambda x: x[1]["pass_rate"]):
        if failures_only and s["pass_rate"] == 1.0:
            continue
        pct = s["pass_rate"] * 100
        print(f"\n{name}")
        print(f"  {s['runs']} runs | {s['full_pass']}/{s['runs']} at 100% ({pct:.0f}%) | "
              f"avg score: {s['avg_score']*100:.0f}% | avg time: {s['avg_time']:.0f}s")
        if s["failure_hotspots"]:
            hotspots = ", ".join(f"{k}: {v}/{s['runs']}" for k, v in
                                sorted(s["failure_hotspots"].items(), key=lambda x: -x[1]))
            print(f"  Failure hotspots: {hotspots}")
        for r in s["recent"]:
            failed = ", ".join(r["failed_criteria"]) or "-"
            print(f"    {r['file']}: {r['score']*100:.0f}% "
                  f"rounds={r['rounds']} failed=[{failed}]")

    print(f"\n{'=' * 70}")
    print(f"TOTALS: {total_runs} runs | {total_100}/{total_runs} at 100% "
          f"({total_100/total_runs*100:.0f}%) | {total_tokens:,.0f} tokens")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Dogfood result analysis")
    parser.add_argument("--scenario", help="Filter by scenario name substring")
    parser.add_argument("--last", type=int, help="Only last N runs")
    parser.add_argument("--failures-only", action="store_true", help="Only show scenarios with failures")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--dir", default=str(RESULTS_DIR), help="Results directory")
    args = parser.parse_args()

    results = load_results(Path(args.dir))
    if args.scenario:
        results = [r for r in results if args.scenario.lower() in r.get("scenario", "").lower()]
    if args.last:
        results = results[-args.last:]

    stats = analyze(results)

    if args.json:
        json.dump(stats, sys.stdout, indent=2, default=str)
        print()
    else:
        print_report(stats, failures_only=args.failures_only)


if __name__ == "__main__":
    main()
