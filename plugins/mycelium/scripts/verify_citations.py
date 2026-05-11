#!/usr/bin/env python3
"""verify_citations.py — cross-reference agent citations against read evidence.

Mycelium agents are required by CLAUDE.md to cite the trigger when suggesting a
skill, recommending an approach, or making a non-trivial move, using the format
`(per: <source>)`. The source can be a file path, a corrections.md entry, a
canvas field, a theory gate name, a pattern, or a prior decision-log entry.

This script attacks anti-pattern #7 Level 3 (consistency-as-evidence —
fabricated underlying inputs) by checking whether file-shaped citations in
agent output have corresponding Read tool calls in the session's read-log.

Scope discipline:
- Only checks file-SHAPED citations (paths containing dots, slashes, or
  recognizable file extensions). Concept-shaped citations ("per L2 gate",
  "per Torres CDH") are out of scope — they're not verifiable against
  tool-call logs.
- Reports observability, not enforcement. A citation without a matching read
  is a SIGNAL, not a verdict — the agent may legitimately recall cached
  context from earlier in the session before this hook started logging, or
  reference content provided via system reminder.
- Designed for manual invocation initially. Automatic Stop-hook integration
  is deferred until false-positive rate is measured.

Usage:
    # Verify citations in stdin against current session's read-log:
    cat agent_output.txt | verify_citations.py

    # Verify against a specific session log:
    verify_citations.py --read-log /path/to/read-log.jsonl < text.txt

    # JSON output (for piping):
    verify_citations.py --json < text.txt

    # Filter to a specific session_id:
    verify_citations.py --session-id <id> < text.txt

Exit codes:
    0 — script ran cleanly (regardless of findings)
    2 — argument or input error

Python stdlib only.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


# Citation pattern: `(per: <source>)` where <source> can span multiple words
# but ends before the closing paren. Captured non-greedy.
CITATION_RE = re.compile(r"\(per:\s+([^)]+?)\)", re.IGNORECASE)

# File-shape heuristic: contains a slash, OR contains a dot followed by a
# known extension. Rejects pure-concept citations like "L2 Discover gate".
FILE_EXT_RE = re.compile(
    r"\.(md|yml|yaml|json|py|sh|toml|jsonl|txt|csv|html|js|ts|tsx|jsx|css|sql)\b",
    re.IGNORECASE,
)


def looks_like_file_path(source: str) -> bool:
    """Heuristic for whether a citation source is file-shaped.

    True when:
      - Contains a forward slash (/) — indicates path structure
      - Or contains a recognized file extension

    Strips off any trailing fragment-style anchors (#section) and inline
    parenthetical commentary before testing.
    """
    s = source.strip()
    # Strip trailing `#anchor` for shape detection (keep for matching)
    s_for_shape = s.split("#", 1)[0]
    if "/" in s_for_shape:
        return True
    if FILE_EXT_RE.search(s_for_shape):
        return True
    return False


def extract_citations(text: str):
    """Yield {source, file_shaped} for each (per: ...) citation in text."""
    seen = set()
    for match in CITATION_RE.finditer(text):
        raw = match.group(1).strip()
        # De-duplicate identical citations
        if raw in seen:
            continue
        seen.add(raw)
        yield {
            "source": raw,
            "file_shaped": looks_like_file_path(raw),
        }


def load_read_log(read_log_path: Path, session_id_filter: str | None = None):
    """Load read-log entries, optionally filtered by session_id."""
    entries = []
    if not read_log_path.exists():
        return entries
    try:
        with open(read_log_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if session_id_filter and entry.get("session_id") != session_id_filter:
                    continue
                entries.append(entry)
    except Exception:
        pass  # fail-open: an unreadable log produces an empty result
    return entries


def normalize_path(p: str) -> str:
    """Normalize for matching: absolute -> basename + relative tail.

    Citations typically use repo-relative paths (`landscape.yml`, `.claude/canvas/X.yml`)
    while Read tool logs absolute paths (`/Users/.../landscape.yml`). Match by
    the trailing path component(s) — anchor matching to suffix match so that
    `landscape.yml` matches `/Users/.../canvas/landscape.yml`.
    """
    # Strip any anchor / fragment from citation
    p = p.split("#", 1)[0].strip()
    # Strip leading ./ if present
    if p.startswith("./"):
        p = p[2:]
    return p


def cited_path_matches_read(citation: str, read_path: str) -> bool:
    """True if a citation path is satisfied by an actual read path.

    Uses suffix matching: citation `landscape.yml` matches any read whose path
    ends with `/landscape.yml` (or equals `landscape.yml` for cwd-relative reads).
    Citation `.claude/canvas/landscape.yml` matches reads ending with that
    exact suffix.

    Anchors (#section) on the citation side are stripped before matching —
    the read log records the file, not the section.
    """
    cite_norm = normalize_path(citation)
    if not cite_norm:
        return False
    # Exact match
    if read_path == cite_norm:
        return True
    # Suffix match: read_path ends with /<cite_norm>
    if read_path.endswith("/" + cite_norm):
        return True
    # Also match if read_path ends with cite_norm and cite_norm starts with .
    # (handles .claude/... style citations against absolute paths)
    if cite_norm.startswith(".") and read_path.endswith(cite_norm):
        return True
    return False


def verify(text: str, read_entries: list) -> dict:
    """Cross-reference citations from text against read-log entries.

    Returns a structured report:
      - total_citations
      - file_shaped_citations
      - concept_shaped_citations
      - verified (file-shaped citations with matching reads)
      - unverified (file-shaped citations without matching reads — anti-pattern #7 candidates)
      - unverifiable (concept-shaped citations — out of scope by design)
    """
    citations = list(extract_citations(text))
    read_paths = [e.get("file_path", "") for e in read_entries if e.get("file_path")]

    verified = []
    unverified = []
    unverifiable = []

    for c in citations:
        if not c["file_shaped"]:
            unverifiable.append(c["source"])
            continue
        matched = any(cited_path_matches_read(c["source"], rp) for rp in read_paths)
        if matched:
            verified.append(c["source"])
        else:
            unverified.append(c["source"])

    return {
        "total_citations": len(citations),
        "file_shaped": len(verified) + len(unverified),
        "concept_shaped": len(unverifiable),
        "verified": verified,
        "unverified": unverified,
        "unverifiable": unverifiable,
        "reads_in_session": len(read_paths),
    }


def format_human(report: dict) -> str:
    """Human-readable report."""
    lines = []
    lines.append(f"Citation verification: {report['total_citations']} citation(s) found")
    lines.append(f"  File-shaped: {report['file_shaped']} ({len(report['verified'])} verified, {len(report['unverified'])} unverified)")
    lines.append(f"  Concept-shaped (out of scope): {report['concept_shaped']}")
    lines.append(f"  Reads in session log: {report['reads_in_session']}")
    if report["unverified"]:
        lines.append("")
        lines.append("Unverified file-citations (anti-pattern #7 Level 3 candidates):")
        for u in report["unverified"]:
            lines.append(f"  - (per: {u})")
        lines.append("")
        lines.append("Note: unverified ≠ fabricated. Possible legitimate reasons:")
        lines.append("  - File was read before the read-log hook was installed (pre-v0.23.8 session)")
        lines.append("  - File content was provided via system reminder, not Read tool")
        lines.append("  - Reference is to a concept that happens to share the file name")
        lines.append("  - Read happened in a different session and is being recalled from memory")
        lines.append("Treat as a signal worth investigating, not a verdict.")
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(
        description="Cross-reference agent (per: <source>) citations against read-log evidence."
    )
    p.add_argument(
        "--read-log",
        default=None,
        help="Path to read-log.jsonl. Defaults to $CLAUDE_PROJECT_DIR/.claude/state/read-log.jsonl (or ./.claude/state/read-log.jsonl).",
    )
    p.add_argument(
        "--session-id",
        default=None,
        help="If set, only consider read-log entries with this session_id.",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Emit report as JSON.",
    )
    p.add_argument(
        "--input",
        default=None,
        help="Read text from this file instead of stdin.",
    )
    args = p.parse_args()

    # Resolve read-log path
    if args.read_log:
        read_log_path = Path(args.read_log)
    else:
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
        read_log_path = Path(project_dir) / ".claude" / "state" / "read-log.jsonl"

    # Read input
    if args.input:
        with open(args.input, "r") as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    read_entries = load_read_log(read_log_path, args.session_id)
    report = verify(text, read_entries)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(format_human(report))


if __name__ == "__main__":
    main()
