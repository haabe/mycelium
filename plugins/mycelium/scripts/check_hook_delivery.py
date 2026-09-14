#!/usr/bin/env python3
"""check_hook_delivery.py — did the harness actually run our hooks, or cancel them?

WHY THIS EXISTS (dogfood, 2026-09-10, the worst finding in the project's record). The plugin's
hooks.json had carried `"timeout": 5` on the SessionStart hook since 2026-05-09, while the hook
grew to some twenty checks and about eighteen seconds on the dogfood canvas. Claude Code's own
default for a command hook is ten minutes; the manifest overrode it. Read off the harness's
transcripts, which record every hook outcome: 32 of 33 session starts between 2026-08-09 and
2026-09-10 were `hook_cancelled` at 5.0 s. The operating contract and every advisory the hook
computes reached no
agent on that repo for a month. Every test of the hook passed, because tests run the script, not the
harness. Nothing in the framework read the one place the outcome was written: the transcript.

WHAT IT DOES. Finds this project's transcript directory (`~/.claude/projects/<cwd with / -> ->`),
scans the transcripts modified in the last N days for hook outcome attachments, and reports, per
hook (by its statusMessage, which is what the harness records as `command`), how many runs
succeeded, how many were cancelled, the last cancellation and its timeout. FAIL when the hook that
delivers the contract (SessionStart) was cancelled in the window; WARN for any other cancellation;
N/A, spoken, when there is no transcript directory (a runtime that keeps none, or a fresh machine).

WHAT IT DOES NOT DO. It cannot make a cancelled hook deliver. It runs at the NEXT session start,
inside the hook it audits, which is why the hook now carries an in-hook deadline so that next start
survives. It reads the harness's record; it does not parse anything a human wrote.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

HOOK_ATTACHMENTS = ("hook_cancelled", "hook_success", "hook_error")
SEV_WARN, SEV_FAIL = 1, 2


def transcript_dir(project: Path, claude_home: Path) -> Path:
    slug = str(project.resolve()).replace("/", "-")
    return claude_home / "projects" / slug


def scan(tdir: Path, since: datetime) -> dict[str, dict]:  # noqa: C901 — one pass, three outcomes
    """Per hook command: ok / cancelled / error counts, last cancellation time and timeout."""
    per: dict[str, dict] = {}
    for f in sorted(tdir.glob("*.jsonl")):
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=UTC)
        except OSError:
            continue
        if mtime < since:
            continue
        try:
            fh = f.open(encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                if '"hook_' not in line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                a = d.get("attachment")
                if not isinstance(a, dict) or a.get("type") not in HOOK_ATTACHMENTS:
                    continue
                key = (
                    f"{a.get('hookEvent') or a.get('hookName') or '?'} | {a.get('command') or '?'}"
                )
                row = per.setdefault(
                    key,
                    {
                        "ok": 0,
                        "cancelled": 0,
                        "error": 0,
                        "last_cancelled": None,
                        "timeout_ms": None,
                    },
                )
                kind = a["type"].split("_", 1)[1]
                if kind == "success":
                    row["ok"] += 1
                elif kind == "cancelled":
                    row["cancelled"] += 1
                    ts = d.get("timestamp") or ""
                    if not row["last_cancelled"] or ts > row["last_cancelled"]:
                        row["last_cancelled"] = ts
                    row["timeout_ms"] = a.get("timeoutMs") or row["timeout_ms"]
                else:
                    row["error"] += 1
    return per


def report(per: dict[str, dict], days: int, contract_marker: str) -> tuple[int, list[str]]:
    lines = []
    if not per:
        return 0, [f"hook-delivery: no hook outcomes recorded in the last {days} day(s)"]
    worst = 0
    for key, r in sorted(per.items(), key=lambda kv: -kv[1]["cancelled"]):
        if not r["cancelled"] and not r["error"]:
            continue
        sev = "FAIL" if (contract_marker in key and r["cancelled"]) else "WARN"
        worst = max(worst, SEV_FAIL if sev == "FAIL" else SEV_WARN)
        tmo = f", manifest timeout {r['timeout_ms'] / 1000:.0f}s" if r["timeout_ms"] else ""
        lines.append(
            f"hook-delivery {sev}: {key}: cancelled {r['cancelled']}, ok {r['ok']}, "
            f"error {r['error']} in the last {days} day(s); last cancelled "
            f"{(r['last_cancelled'] or '?')[:19]}{tmo}. A cancelled hook delivers NOTHING: "
            "its stdout is discarded by the harness."
        )
    if not lines:
        total = sum(r["ok"] for r in per.values())
        lines.append(
            f"hook-delivery: OK — {total} hook run(s) in the last {days} day(s), none cancelled"
        )
    return worst, lines


GATE_BLOCK_LOG = Path(".claude/state/gate-block-log.jsonl")


def gate_blocks(project: Path, since: datetime) -> str | None:
    """One line on gate.sh blocks in the window, from the log gate.sh writes since 0.204.0.

    None when the project has no log: a project on a plugin older than 0.204.0, or one where
    the gate has never blocked, and the two cannot be told apart from here — so the line says
    "no gate-block log", not "no blocks".
    """
    path = project / GATE_BLOCK_LOG
    if not path.is_file():
        return None
    blocks = 0
    sessions: set[str] = set()
    reasons: dict[str, int] = {}
    unreadable = 0
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            e = json.loads(raw)
            ts = datetime.fromisoformat(str(e["ts"]))
        except (ValueError, KeyError, TypeError):
            unreadable += 1
            continue
        if ts < since:
            continue
        blocks += 1
        sessions.add(str(e.get("session_id") or "?"))
        r = str(e.get("reason") or "?")
        reasons[r] = reasons.get(r, 0) + 1
    detail = ", ".join(f"{k} {v}" for k, v in sorted(reasons.items()))
    note = f"; {unreadable} unreadable line(s) skipped" if unreadable else ""
    days = max(1, (datetime.now(tz=UTC) - since).days)
    return (f"gate-block: {blocks} block(s) in {len(sessions)} session(s) over {days} day(s)"
            f"{' (' + detail + ')' if detail else ''}{note}. This is the cost side of the "
            f"gate; opp-072 asks whether it exceeds what the gate caught.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Did the harness run our hooks, or cancel them?")
    ap.add_argument("--project-dir", type=Path, default=Path("."))
    ap.add_argument("--claude-home", type=Path, default=Path.home() / ".claude")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--contract-hook", default="SessionStart")
    ap.add_argument("--strict", action="store_true", help="exit 1 on FAIL")
    args = ap.parse_args(argv)
    tdir = transcript_dir(args.project_dir, args.claude_home)
    if not tdir.is_dir():
        print(f"hook-delivery: N/A — no transcript directory at {tdir}; no record kept here")
        line = gate_blocks(args.project_dir, datetime.now(tz=UTC) - timedelta(days=args.days))
        print(line or "gate-block: no gate-block log under .claude/state (plugin older than "
              "0.204.0, or the gate has never blocked here; not the same thing)")
        return 0
    since = datetime.now(tz=UTC) - timedelta(days=args.days)
    worst, lines = report(scan(tdir, since), args.days, args.contract_hook)
    for line in lines:
        print(line)
    print(gate_blocks(args.project_dir, since) or "gate-block: no gate-block log under "
          ".claude/state (plugin older than 0.204.0, or the gate has never blocked here; not "
          "the same thing)")
    return 1 if (args.strict and worst == SEV_FAIL) else 0


if __name__ == "__main__":
    sys.exit(main())
