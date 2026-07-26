#!/usr/bin/env python3
"""check_coverage_floor.py — every shipped Python script must be tested.

`pytest --cov-fail-under` gates the TOTAL average, which a new untested script
can hide under (a single 0% file barely moves a 90% total). This gate is
PER-FILE: every `.py` under `plugins/mycelium/{scripts,integrations}` must appear
in the coverage report at >= the per-file floor. A new script with no test is
either absent from the report (never imported) or at 0% — both fail loudly.

This is the script-level analog of G-V12 / Check 37, which mandates a fixture
test for every validator CHECK. Here: a test for every shipped script. Added
2026-06-18 after `check_legacy_paths.py` shipped at 0% (v0.49.6) — the total
floor would not have caught it.

Reads `coverage.json` (produced by `pytest --cov-report=json`).

Usage:
    check_coverage_floor.py [--coverage-json PATH] [--floor N] [--root DIR]

Exit codes:
    0 — every shipped script meets the floor
    1 — at least one script untested / below floor (CI gate)
    2 — setup error (coverage json missing)

Python stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

# Shipped Python the framework runs. Globs are repo-root-relative.
TARGET_GLOBS = ["plugins/mycelium/scripts/*.py", "plugins/mycelium/integrations/**/*.py"]
EXCLUDE_NAMES = {"__init__.py"}
DEFAULT_FLOOR = 70.0


def iter_targets(root: Path):
    seen = set()
    for g in TARGET_GLOBS:
        for p in root.glob(g):
            if not p.is_file() or p.name in EXCLUDE_NAMES or "__pycache__" in p.parts:
                continue
            rel = p.relative_to(root).as_posix()
            if rel not in seen:
                seen.add(rel)
                yield rel


def evaluate(root: Path, cov_files: dict, floor: float):
    """Return (checked_count, violations) where violations is [(rel, pct_or_None)]."""
    by_rel, by_base = {}, {}
    for k, v in cov_files.items():
        pct = v.get("summary", {}).get("percent_covered", 0.0)
        by_rel[Path(k).as_posix()] = pct
        by_base.setdefault(Path(k).name, pct)
    violations, checked = [], 0
    for rel in iter_targets(root):
        checked += 1
        pct = by_rel.get(rel)
        if pct is None:
            pct = by_base.get(Path(rel).name)
        if pct is None:
            violations.append((rel, None))       # untested — never imported
        elif pct < floor:
            violations.append((rel, pct))         # under floor
    return checked, violations


def main(argv=None):
    ap = argparse.ArgumentParser(description="Per-file coverage floor for shipped scripts.")
    ap.add_argument("--coverage-json", default="coverage.json")
    ap.add_argument("--floor", type=float, default=DEFAULT_FLOOR)
    ap.add_argument("--root", default=None)
    args = ap.parse_args(argv)

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[3]
    cov_path = Path(args.coverage_json)
    if not cov_path.is_absolute():
        cov_path = root / cov_path
    if not cov_path.exists():
        print(f"error: coverage json not found at {cov_path} — run "
              f"`pytest --cov-report=json` first", file=sys.stderr)
        return 2

    cov_files = json.loads(cov_path.read_text()).get("files", {})
    checked, violations = evaluate(root, cov_files, args.floor)

    if violations:
        print(f"✗ Per-file coverage floor ({args.floor:.0f}%) not met:", file=sys.stderr)
        for rel, pct in violations:
            shown = "NO COVERAGE (untested — no test imports it)" if pct is None else f"{pct:.0f}%"
            print(f"    {rel}: {shown}", file=sys.stderr)
        print("\nEvery shipped script must have a test (script-level analog of G-V12). "
              "Add a tests/python/test_<name>.py exercising it.", file=sys.stderr)
        return 1

    print(f"✓ All {checked} shipped scripts ≥ {args.floor:.0f}% coverage.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
