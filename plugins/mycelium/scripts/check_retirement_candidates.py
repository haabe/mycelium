#!/usr/bin/env python3
"""The framework only grows. This is the report that says what could go.

THE GAP (dogfood 2026-09-07, register row the-framework-only-grows-and-nothing-flags-a-
mechanism-for-retirement). Every skill, hook, gate and check that ships stays: 61 skills and
23 CI gates at 0.180.4, none retired, and no mechanism reported another mechanism as unread
or unfired. `check_field_wiring.py` does this for canvas FIELDS (a field with no reader is
listed); this extends the same question to the mechanisms themselves, from the records the
framework already writes. The decision to retire stays with the maintainer. Nothing is
removed by this script.

THREE CLASSES, THREE KINDS OF EVIDENCE, stated so a row is not read as more than it is.

  * SKILLS. Fired = the project's own dated record names it (`/mycelium:<name>` or
    `/<name>` in decision-log.md or corrections.md, dated by the entry heading above the
    mention) or the read-log shows its SKILL.md being read. Read = another skill, an engine
    doc or a hook names it. No runtime writes a skill-invocation record, so a skill invoked
    and never written about is invisible here; that is a gap in the runtime, named in the
    output, not a pass.
  * HOOKS. Fired = the newest row or mtime of a state file the hook (or the helper it
    calls) writes under `.claude/state/`, found by reading the hook's own source. A hook
    that writes no record is UNMEASURABLE and listed as such: a mechanism nobody can
    measure is the row this report exists for, not a row to skip.
  * CHECKS. Fired = the gate set runs it on every push, or session-start runs it every
    session; neither leaves a project-side record, so the question for a check is who
    READS it. Read = a skill, engine doc or hook names it. A check whose only reader is the
    gate list has "no reader" and is a candidate: it runs, and its output reaches nobody.

A candidate is a mechanism with no fire inside the window AND no reader. The window is a
parameter (default 60 days) because the right one depends on the project's cadence, and the
report prints it beside every date so the reader can disagree.

Exit codes: 0 report printed; 1 nothing could be measured (`--strict` only); 2 no framework
root found, which is a precondition, not a pass.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

DEFAULT_WINDOW = 60
_STATE_FILE = re.compile(r"\.claude/state/([A-Za-z0-9._-]+\.jsonl?)")
_STATE_FILE_PY = re.compile(r'"state"\s*/\s*"([A-Za-z0-9._-]+\.jsonl?)"|"([a-z0-9-]+-log\.jsonl)"')
_HELPER = re.compile(r"scripts/([a-z_0-9]+\.py)")
_HEADING_DATE = re.compile(r"^#+ .*?(\d{4}-\d{2}-\d{2})", re.MULTILINE)
_ROW_DATE = re.compile(r'"(?:at|ts|timestamp)":\s*"(\d{4}-\d{2}-\d{2})')
_MAX_TAIL = 4096
_READERS_SHOWN = 3
#: hooks/*.json are the runtime manifests: a hook registered there is read by the runtime.
_READER_GLOBS = ("skills/*/SKILL.md", "engine/*.md", "hooks/*.sh", "hooks/*.json",
                 "harness/*.md", "orchestration/*.md")
_GATE_LIST = "scripts/local-gate-set.txt"
_SESSION_START = "hooks/session-start.sh"
_PROJECT_RECORD = (".claude/harness/decision-log.md", ".claude/memory/corrections.md",
                   ".claude/state")


# ------------------------------------------------------------------ framework inventory


def framework_root(explicit: str | None) -> Path | None:
    for cand in (explicit, os.environ.get("CLAUDE_PLUGIN_ROOT"),
                 str(Path(__file__).resolve().parents[1])):
        if cand and (Path(cand) / "skills").is_dir() and (Path(cand) / "hooks").is_dir():
            return Path(cand)
    return None


def inventory(root: Path) -> dict[str, list[str]]:
    return {
        "skill": sorted(p.parent.name for p in root.glob("skills/*/SKILL.md")),
        "hook": sorted(p.name for p in root.glob("hooks/*.sh")),
        "check": sorted(p.name for p in root.glob("scripts/check_*.py")),
    }


def _reader_corpus(root: Path) -> dict[str, str]:
    out = {}
    for g in _READER_GLOBS:
        for p in sorted(root.glob(g)):
            try:
                out[str(p.relative_to(root))] = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
    return out


def readers_of(name: str, kind: str, corpus: dict[str, str], own: str) -> list[str]:
    """Files in the framework that name this mechanism, excluding itself."""
    if kind == "skill":
        pat = re.compile(r"(?<![\w-])/(?:mycelium:)?" + re.escape(name) + r"(?![\w-])")
    else:
        pat = re.compile(re.escape(name))
    return sorted(f for f, text in corpus.items() if f != own and pat.search(text))


def hook_state_files(root: Path, hook: str) -> set[str]:
    """State files this hook, or a helper it invokes, writes: read from the sources."""
    files: set[str] = set()
    try:
        src = (root / "hooks" / hook).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return files
    files.update(_STATE_FILE.findall(src))
    for helper in set(_HELPER.findall(src)):
        try:
            hs = (root / "scripts" / helper).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        files.update(_STATE_FILE.findall(hs))
        files.update(a or b for a, b in _STATE_FILE_PY.findall(hs))
    return files


# ------------------------------------------------------------------ project evidence


def _last_date_in_state_file(path: Path) -> date | None:
    """Newest dated row (tail of a jsonl) or the mtime; None when the file is absent."""
    try:
        if not path.exists():
            return None
        if path.suffix == ".jsonl":
            with path.open("rb") as fh:
                fh.seek(0, os.SEEK_END)
                size = fh.tell()
                fh.seek(max(0, size - _MAX_TAIL))
                tail = fh.read().decode("utf-8", errors="replace")
            dates = _ROW_DATE.findall(tail)
            if dates:
                return date.fromisoformat(max(dates))
        return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).date()
    except (OSError, ValueError):
        return None


def skill_mentions(project: Path, skills: list[str]) -> dict[str, date]:
    """skill -> newest dated entry heading above a `/mycelium:<skill>` or `/<skill>` mention."""
    out: dict[str, date] = {}
    for rel in (".claude/harness/decision-log.md", ".claude/memory/corrections.md"):
        path = project / rel
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        current: date | None = None
        pats = {s: re.compile(r"(?<![\w-])/(?:mycelium:)?" + re.escape(s) + r"(?![\w-])")
                for s in skills}
        for line in text.splitlines():
            h = _HEADING_DATE.match(line)
            if h:
                # A mention on the heading line itself ("DL-1: ran /mycelium:x") counts
                # for that entry; the first cut skipped headings and missed every one.
                with contextlib.suppress(ValueError):
                    current = date.fromisoformat(h.group(1))
            if current is None or "/" not in line:
                continue
            for s, pat in pats.items():
                if pat.search(line) and (s not in out or out[s] < current):
                    out[s] = current
    return out


def skill_reads(project: Path, skills: list[str]) -> dict[str, date]:
    """skill -> newest read-log row whose path is inside that skill's directory."""
    out: dict[str, date] = {}
    path = project / ".claude/state/read-log.jsonl"
    if not path.exists():
        return out
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            fp, ts = str(row.get("file_path", "")), str(row.get("ts", ""))[:10]
            m = re.search(r"/skills/([a-z0-9-]+)/", fp)
            if not m or m.group(1) not in skills or not ts:
                continue
            try:
                d = date.fromisoformat(ts)
            except ValueError:
                continue
            if m.group(1) not in out or out[m.group(1)] < d:
                out[m.group(1)] = d
    except OSError:
        return out
    return out


# ------------------------------------------------------------------ the report


def assess(root: Path, project: Path, window: int, today: date) -> dict:
    inv = inventory(root)
    corpus = _reader_corpus(root)
    gate_list = ""
    with contextlib.suppress(OSError):
        gate_list = (root / _GATE_LIST).read_text(encoding="utf-8", errors="replace")
    session_start = corpus.get(_SESSION_START, "")
    cutoff = today - timedelta(days=window)
    mentions = skill_mentions(project, inv["skill"])
    reads = skill_reads(project, inv["skill"])
    rows: list[dict] = []
    measurable = 0
    for kind, names in inv.items():
        for name in names:
            own = {"skill": f"skills/{name}/SKILL.md", "hook": f"hooks/{name}",
                   "check": f"scripts/{name}"}[kind]
            rd = readers_of(name, kind, corpus, own)
            last: date | None = None
            fired = "unmeasurable"
            if kind == "skill":
                cands = [d for d in (mentions.get(name), reads.get(name)) if d]
                last = max(cands) if cands else None
                fired = "project record" if last else "no record in the project"
                measurable += 1
            elif kind == "hook":
                files = hook_state_files(root, name)
                dates = [d for d in (_last_date_in_state_file(project / ".claude/state" / f)
                                     for f in sorted(files)) if d]
                if files:
                    last = max(dates) if dates else None
                    fired = ("state file " + ", ".join(sorted(files))) if dates else \
                        "writes " + ", ".join(sorted(files)) + ", none present"
                    measurable += 1
                else:
                    fired = "writes no record"
            else:
                in_gates = name in gate_list
                in_session = name in session_start
                fired = ("every push (gate set)" if in_gates else "") + \
                    (" + every session (session-start)" if in_session else "")
                fired = fired.strip(" +") or "no gate, no session-start"
                # The gate set fails a build and session-start prints into a session:
                # both are readers with teeth, so a check they carry is not a candidate.
                if in_gates:
                    rd = [_GATE_LIST, *rd]
                if in_session:
                    rd = [_SESSION_START, *rd]
                measurable += 1
            quiet = last is None or last < cutoff
            rows.append({"kind": kind, "name": name, "last": last, "fired": fired,
                         "readers": rd, "quiet": quiet,
                         "candidate": (quiet and not rd and fired != "writes no record")})
    return {"rows": rows, "window": window, "today": today, "cutoff": cutoff,
            "measurable": measurable}


def _print(result: dict) -> None:
    rows, cutoff = result["rows"], result["cutoff"]
    print(f"Retirement candidates (window {result['window']} days, since {cutoff}; "
          f"as of {result['today']})")
    print("=" * 78)
    cands = [r for r in rows if r["candidate"]]
    unmeas = [r for r in rows if r["fired"] == "writes no record"]
    print(f"  {len(rows)} mechanisms: "
          + ", ".join(f"{k} {sum(1 for r in rows if r['kind'] == k)}"
                      for k in ("skill", "hook", "check")))
    print(f"  {len(cands)} candidate(s): no fire in the window and no reader.")
    print(f"  {len(unmeas)} hook(s) write no record and cannot be measured.\n")
    for r in cands:
        print(f"  {r['kind']:5} {r['name']:44} last {r['last'] or 'never'!s:10}  "
              f"fired: {r['fired']}; no reader")
    if cands:
        print()
    if unmeas:
        print("  Unmeasurable (writes no record; the first fix is a record, not retirement):")
        for r in unmeas:
            print(f"    hook  {r['name']}")
        print()
    quiet_read = [r for r in rows if r["quiet"] and r["readers"] and r["kind"] != "check"]
    if quiet_read:
        print(f"  Quiet but read ({len(quiet_read)}): no fire in the window, "
              f"named by another mechanism. Not candidates; listed so a reader can disagree.")
        for r in quiet_read:
            shown = ", ".join(r["readers"][:_READERS_SHOWN])
            more = len(r["readers"]) - _READERS_SHOWN
            print(f"    {r['kind']:5} {r['name']:44} last {r['last'] or 'never'!s:10}  "
                  f"read by {shown}" + (f" +{more}" if more > 0 else ""))
        print()
    print("THE DECISION STAYS WITH THE MAINTAINER. A candidate is a mechanism with no evidence")
    print("of use in this project's record; a skill can be invoked without being written")
    print("about, and no runtime records that. Retire by release, with the row's evidence")
    print("in the changelog, never by this script.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project-dir", default=".")
    ap.add_argument("--framework-root", default=None)
    ap.add_argument("--window-days", type=int, default=DEFAULT_WINDOW)
    ap.add_argument("--today", default=None)
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 when nothing could be measured")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    root = framework_root(args.framework_root)
    if root is None:
        print("check_retirement_candidates: no framework root (needs skills/ and hooks/); "
              "pass --framework-root or set CLAUDE_PLUGIN_ROOT", file=sys.stderr)
        return 2
    today = date.fromisoformat(args.today) if args.today else datetime.now(UTC).date()
    project = Path(args.project_dir)
    if not any((project / rel).exists() for rel in _PROJECT_RECORD):
        print("NOT A PASS: the project has no decision log, corrections file or state "
              "directory, so there is no record to measure a mechanism's use against.")
        return 1
    result = assess(root, project, args.window_days, today)
    if not result["rows"]:
        print("NOT A PASS: the framework root holds no skills, hooks or checks; nothing "
              "was assessed.")
        return 1
    if args.json:
        print(json.dumps({**result, "today": str(today), "cutoff": str(result["cutoff"]),
                          "rows": [{**r, "last": str(r["last"]) if r["last"] else None}
                                   for r in result["rows"]]}, indent=2))
    else:
        _print(result)
    if args.strict and not result["measurable"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
