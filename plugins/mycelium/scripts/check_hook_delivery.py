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

RETIRED LABELS (dogfood 2026-10-02). The harness records a hook by its label (its
statusMessage, or its command when it has none), and a release that renames or splits a hook
leaves the old label's cancellations in the window for up to --days days after the fix. Those
read as a live FAIL on the first line canvas-health tells its reader to report. A key whose
label is no longer in the current hooks manifest (`hooks/hooks.json` beside this script) is
a WARN marked `retired label`, with the date it was last seen and the date it leaves the window;
a cancelled CURRENT label of the contract hook is still a FAIL. Whenever a hook event has a
reported key, one more line gives the counts for that event's current labels, so the reader can
see whether what replaced the old label runs clean. When the manifest cannot be read, every
label is treated as current, which is the behaviour before this change.

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
DEFAULT_MANIFEST = Path(__file__).resolve().parent.parent / "hooks" / "hooks.json"


def current_labels(manifest: Path) -> dict[str, set[str]] | None:
    """Per hook event, every label the current manifest gives a hook: its statusMessage and its
    command (the harness records the statusMessage when there is one, else the command).

    None when the manifest is missing or unreadable: then no label can be called retired.
    """
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        out: dict[str, set[str]] = {}
        for event, groups in data["hooks"].items():
            labels = out.setdefault(event, set())
            for group in groups:
                for h in group.get("hooks", []):
                    labels.update(str(h[f]) for f in ("statusMessage", "command") if h.get(f))
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None
    return out


def is_retired(key: str, labels: dict[str, set[str]] | None) -> bool:
    """True when the key's label is in no current hook of its event (of any event, when the
    transcript did not name one). Never True when the manifest could not be read."""
    if labels is None:
        return False
    event, _, label = key.partition(" | ")
    event = event.split(":", 1)[0]  # a hookName fallback reads "SessionStart:startup"
    if event == "?":
        return not any(label in s for s in labels.values())
    return label not in labels.get(event, set())


def transcript_dir(project: Path, claude_home: Path) -> Path:
    slug = str(project.resolve()).replace("/", "-")
    return claude_home / "projects" / slug


def scan(tdir: Path, since: datetime) -> dict[str, dict]:
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
                        "last_seen": None,
                    },
                )
                _tally(row, d, a)
    return per


def _tally(row: dict, d: dict, a: dict) -> None:
    """Count one hook outcome into its row; keep the latest time seen and cancelled."""
    ts = d.get("timestamp") or ""
    if ts and (not row["last_seen"] or ts > row["last_seen"]):
        row["last_seen"] = ts
    kind = a["type"].split("_", 1)[1]
    if kind == "success":
        row["ok"] += 1
    elif kind == "cancelled":
        row["cancelled"] += 1
        if not row["last_cancelled"] or ts > row["last_cancelled"]:
            row["last_cancelled"] = ts
        row["timeout_ms"] = a.get("timeoutMs") or row["timeout_ms"]
    else:
        row["error"] += 1


def _retired_note(r: dict, days: int) -> str:
    seen = (r.get("last_seen") or "")[:10]
    leaves = ""
    try:
        when = datetime.fromisoformat(seen) + timedelta(days=days)
        leaves = f", and it leaves the {days}-day window on {when.date().isoformat()}"
    except ValueError:
        pass
    return (
        f" Retired label: no hook in the current hooks manifest carries it, so this is a hook "
        f"since renamed or split; last seen {seen or '?'}{leaves}. The counts for the current "
        f"labels of this hook are on the line that follows."
    )


def _problem_line(key: str, r: dict, days: int, retired: bool, contract_marker: str) -> tuple:
    contract_cancel = contract_marker in key and r["cancelled"]
    sev = "FAIL" if (contract_cancel and not retired) else "WARN"
    tag = " (retired label)" if retired else ""
    tmo = f", manifest timeout {r['timeout_ms'] / 1000:.0f}s" if r["timeout_ms"] else ""
    line = (
        f"hook-delivery {sev}{tag}: {key}: cancelled {r['cancelled']}, ok {r['ok']}, "
        f"error {r['error']} in the last {days} day(s); last cancelled "
        f"{(r['last_cancelled'] or '?')[:19]}{tmo}. A cancelled hook delivers NOTHING: "
        "its stdout is discarded by the harness."
    )
    if retired:
        line += _retired_note(r, days)
    return (SEV_FAIL if sev == "FAIL" else SEV_WARN), line


def _current_counts_line(event: str, per: dict[str, dict], labels, days: int) -> str:
    """One line with the counts of every current label of `event` seen in the window."""
    parts = [
        f"{key.partition(' | ')[2]}: ok {r['ok']}, cancelled {r['cancelled']}, error {r['error']}"
        for key, r in sorted(per.items())
        if key.partition(" | ")[0] == event and not is_retired(key, labels)
    ]
    body = "; ".join(parts) if parts else "none of them ran in the window"
    return f"hook-delivery current labels of {event} in the last {days} day(s): {body}"


def report(
    per: dict[str, dict],
    days: int,
    contract_marker: str,
    labels: dict[str, set[str]] | None = None,
) -> tuple[int, list[str]]:
    """`labels` is current_labels() of the hooks manifest; None treats every label as current."""
    if not per:
        return 0, [f"hook-delivery: no hook outcomes recorded in the last {days} day(s)"]
    lines: list[str] = []
    worst = 0
    events: list[str] = []
    for key, r in sorted(per.items(), key=lambda kv: -kv[1]["cancelled"]):
        if not r["cancelled"] and not r["error"]:
            continue
        sev, line = _problem_line(key, r, days, is_retired(key, labels), contract_marker)
        worst = max(worst, sev)
        lines.append(line)
        event = key.partition(" | ")[0]
        if event not in events:
            events.append(event)
    if not lines:
        total = sum(r["ok"] for r in per.values())
        return 0, [
            f"hook-delivery: OK — {total} hook run(s) in the last {days} day(s), none cancelled"
        ]
    if labels is not None:
        lines.extend(_current_counts_line(e, per, labels, days) for e in events)
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


RUNTIME_DIRS = {"codex": ".codex", "cursor": ".cursor"}


def runtime_manifests(project: Path) -> list[str]:
    """One line per non-Claude runtime the project is set up for, saying whether the
    Mycelium hook manifest is installed there (v0.213.0).

    Codex and Cursor get Mycelium's enforcement only if someone ran
    `install-runtime-hooks.sh <runtime>`, and skipping it was silent: an A/B on 2026-08-18
    showed the same model cutting two agent-contract files by 81% and 85% without the
    manifest and leaving them untouched with it. Nothing anywhere asked whether it was run.
    A runtime dir with no `hooks.json` is the finding; a runtime dir absent is not a
    project that uses that runtime, and says nothing.
    """
    out = []
    for runtime, rel in RUNTIME_DIRS.items():
        d = project / rel
        if not d.is_dir():
            continue
        if (d / "hooks.json").is_file():
            out.append(f"runtime-hooks: {rel}/hooks.json present — Mycelium enforcement installed "
                       f"for {runtime}")
        else:
            out.append(f"runtime-hooks: {rel}/ exists with NO hooks.json — Mycelium enforcement is "
                       f"not installed for {runtime}; the contract there is prose only. Run "
                       f"install-runtime-hooks.sh {runtime}")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Did the harness run our hooks, or cancel them?")
    ap.add_argument("--project-dir", type=Path, default=Path("."))
    ap.add_argument("--claude-home", type=Path, default=Path.home() / ".claude")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--contract-hook", default="SessionStart")
    ap.add_argument("--strict", action="store_true", help="exit 1 on FAIL")
    ap.add_argument(
        "--hooks-manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="the current hooks.json; a label absent from it is reported as a retired label",
    )
    args = ap.parse_args(argv)
    tdir = transcript_dir(args.project_dir, args.claude_home)
    if not tdir.is_dir():
        print(f"hook-delivery: N/A — no transcript directory at {tdir}; no record kept here")
        line = gate_blocks(args.project_dir, datetime.now(tz=UTC) - timedelta(days=args.days))
        print(line or "gate-block: no gate-block log under .claude/state (plugin older than "
              "0.204.0, or the gate has never blocked here; not the same thing)")
        return 0
    since = datetime.now(tz=UTC) - timedelta(days=args.days)
    labels = current_labels(args.hooks_manifest)
    worst, lines = report(scan(tdir, since), args.days, args.contract_hook, labels)
    for line in lines:
        print(line)
    print(gate_blocks(args.project_dir, since) or "gate-block: no gate-block log under "
          ".claude/state (plugin older than 0.204.0, or the gate has never blocked here; not "
          "the same thing)")
    for line in runtime_manifests(args.project_dir):
        print(line)
    return 1 if (args.strict and worst == SEV_FAIL) else 0


if __name__ == "__main__":
    sys.exit(main())
