#!/usr/bin/env python3
"""The activity logs in `.claude/state/` keep 90 days by default (v0.318.0).

WHY. Nothing trimmed them: every file read, every change, every guard fire stayed in the project
until the user deleted it. Anthropic's plugin directory review of v0.317.4 asked PRIVACY.md to say
how long each log is kept, and the founder ruled (2026-10-10) that they are trimmed by default,
for a number of days a flag can change.

WHAT IS TRIMMED. Activity logs only (`PRUNED` below): what the agent read and changed, guard and
hook fires, failures. A line is dropped when its `ts` or `at` is older than the limit; a line with
no readable date is kept, since its age is unknown. Decision records are never trimmed: rulings on
advisories (`advisory-ledger.jsonl`), reflexion dismissals, release and skip-ack uses, and the
next-item log. They are what a later session needs in order not to ask again.

THE REFLEXION COUNT SURVIVES. reconcile_reflexions.py reports fired minus decided. Dropping old
fired lines would shrink "fired" while the credits stayed, and hide new unanswered failures behind
old answered ones. So the number of non-suppressed lines dropped is added to the ledger's
`pruned_fired`, which the reconciler counts as fired.

THE FLAG. MYCELIUM_LOG_RETENTION_DAYS=<n> keeps n days; 0 (or off, never) keeps everything.
Anything else unreadable falls back to 90. session-start.sh runs this at most once a day
(`log-prune-last`).

Usage: prune_state_logs.py --state-dir DIR [--force]   Exit 0 always.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import fnmatch
import json
import os
import sys
import tempfile
from pathlib import Path

DEFAULT_DAYS = 90
ENV = "MYCELIUM_LOG_RETENTION_DAYS"
STAMP = "log-prune-last"
LEDGER = "reflexion-ledger.json"
PRUNED = ("read-log.jsonl", "change-log.jsonl", "diamond-state-audit.jsonl",
          "read-before-research-log.jsonl", "reflexion-log.jsonl", "discovery-trigger-log.jsonl",
          "*-guard-log.jsonl", "*-fires.jsonl", "gate-block-log.jsonl", "denied-calls.jsonl")


def retention_days(environ=os.environ) -> int:
    raw = str(environ.get(ENV, "")).strip().lower()
    if raw in ("0", "off", "never", "none"):
        return 0
    try:
        days = int(raw)
    except ValueError:
        return DEFAULT_DAYS
    return days if days > 0 else DEFAULT_DAYS


def _when(row: dict) -> _dt.datetime | None:
    for key in ("ts", "at"):
        raw = row.get(key)
        if not isinstance(raw, str) or not raw:
            continue
        try:
            when = _dt.datetime.fromisoformat(raw)
        except ValueError:
            continue
        return when if when.tzinfo else when.replace(tzinfo=_dt.UTC)
    return None


def prune_file(path: Path, cutoff: _dt.datetime) -> tuple[int, int]:
    """Drop lines dated before `cutoff`; return (dropped, of which not suppressed)."""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    except OSError:
        return 0, 0
    keep, dropped, counted = [], 0, 0
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            keep.append(line)
            continue
        when = _when(row) if isinstance(row, dict) else None
        if when is not None and when < cutoff:
            dropped += 1
            counted += 0 if row.get("suppressed") else 1
        else:
            keep.append(line)
    if dropped:
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.writelines(keep)
        os.replace(tmp, path)
    return dropped, counted


def _credit_pruned_reflexions(state_dir: Path, n: int) -> None:
    path = state_dir / LEDGER
    if n <= 0 or not path.is_file():
        return  # no ledger yet: the reconciler sets its baseline from what is left
    try:
        ledger = json.loads(path.read_text())
    except (OSError, ValueError):
        return
    ledger["pruned_fired"] = int(ledger.get("pruned_fired", 0)) + n
    path.write_text(json.dumps(ledger, indent=2) + "\n")


def _due(state_dir: Path, now: _dt.datetime) -> bool:
    try:
        last = _dt.datetime.fromtimestamp((state_dir / STAMP).stat().st_mtime, tz=_dt.UTC)
    except OSError:
        return True
    return now - last >= _dt.timedelta(days=1)


def prune(state_dir: Path, days: int, now: _dt.datetime | None = None, force: bool = False) -> dict:
    now = now or _dt.datetime.now(tz=_dt.UTC)
    if days <= 0 or not state_dir.is_dir() or not (force or _due(state_dir, now)):
        return {}
    cutoff = now - _dt.timedelta(days=days)
    report = {}
    for path in sorted(state_dir.glob("*.jsonl")):
        if not any(fnmatch.fnmatch(path.name, pat) for pat in PRUNED):
            continue
        dropped, counted = prune_file(path, cutoff)
        if dropped:
            report[path.name] = dropped
        if path.name == "reflexion-log.jsonl":
            _credit_pruned_reflexions(state_dir, counted)
    (state_dir / STAMP).touch()
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Trim the activity logs in .claude/state/.")
    ap.add_argument("--state-dir", required=True, type=Path)
    ap.add_argument("--force", action="store_true", help="ignore the once-a-day stamp")
    args = ap.parse_args(argv)
    try:
        report = prune(args.state_dir, retention_days(), force=args.force)
    except Exception:  # noqa: BLE001 — trimming a log never breaks a session start
        return 0
    for name, n in report.items():
        print(f"{name}: {n} line(s) older than {retention_days()} days removed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
