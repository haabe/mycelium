#!/usr/bin/env python3
"""Ingest CI warnings/failures into warnings-log.md for self-learning.

Reads validate-template.sh / upgrade.sh stdout (from stdin or a file via -f),
extracts WARN/FAIL lines, classifies them against known signatures from
the plugin's engine/warning-handbook.md, and updates .claude/memory/warnings-log.md
with per-class records (first_seen, last_seen, count, sample, status).

This is the substrate for the existing self-learning machinery (corrections.md
+ /corrections-audit + recurring-≥3 graduation) to operate on framework-state
debt as well as agent-introduced failures. CI warnings are not noise; they're
classified, recurring patterns the validators were carefully written to catch.

Per G-V12: ships with a coverage proof (test_ingest_warnings.py) covering each
known signature pattern + the unclassified path.

Usage:
    bash .claude/tests/validate-template.sh 2>&1 | python3 \
        .claude/scripts/ingest_warnings.py
    python3 .claude/scripts/ingest_warnings.py -f /path/to/ci-output.txt
    python3 .claude/scripts/ingest_warnings.py --dry-run < ci-output.txt
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Path resolution — supports plugin form AND legacy form.
# Plugin form: $CLAUDE_PROJECT_DIR/.claude/memory/warnings-log.md (project state) +
#              $CLAUDE_PLUGIN_ROOT/engine/warning-handbook.md (plugin reference).
# Legacy form: <repo>/.claude/{memory,engine}/...

def _resolve_paths():
    here = Path(__file__).resolve()
    plugin_root_candidate = here.parent.parent
    legacy_repo_candidate = here.parent.parent.parent

    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if plugin_root:
        handbook = Path(plugin_root) / "engine" / "warning-handbook.md"
    elif (plugin_root_candidate / "engine" / "warning-handbook.md").exists():
        handbook = plugin_root_candidate / "engine" / "warning-handbook.md"
    else:
        handbook = legacy_repo_candidate / ".claude" / "engine" / "warning-handbook.md"

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        warnings_log = Path(project_dir) / ".claude" / "memory" / "warnings-log.md"
    else:
        cwd_log = Path.cwd() / ".claude" / "memory" / "warnings-log.md"
        legacy_log = legacy_repo_candidate / ".claude" / "memory" / "warnings-log.md"
        if (Path.cwd() / ".claude" / "memory").exists():
            warnings_log = cwd_log
        else:
            warnings_log = legacy_log

    return warnings_log, handbook


WARNINGS_LOG, HANDBOOK = _resolve_paths()

# Known warning-class signatures. Each tuple is (class_name, signature_regex).
# Order matters: first match wins. Add new classes to warning-handbook.md
# AND to this list together — the script's classification is only as good as
# its signature inventory.
KNOWN_SIGNATURES: list[tuple[str, str]] = [
    ("hardcoded_top_level_literal",
     r"upgrade\.sh contains \d+ hardcoded top-level filename literal"),
    ("hardcoded_directory_literal",
     r"upgrade\.sh contains \d+ hardcoded framework-directory literal"),
    ("user_content_skill_unclassified",
     r"new skill\(s\) show strong user-content-handling signal"),
    ("wrapping_convention_missing",
     r"Curated at-risk skill missing|does not acknowledge the wrapping convention"),
    ("canvas_in_update_mapping_missing",
     r"Canvas file \S+ not in canvas-update mapping"),
    ("ruff_total_above_baseline",
     r"ruff: \d+ total errors across all"),
    ("validation_failed",
     r"VALIDATION FAILED"),
    ("dirty_state_pre_upgrade",
     r"Uncommitted changes detected\. Commit or stash first"),
    ("framework_dev_without_l4_dod",
     r"framework changes shipped without L4 delivery discipline"),
]

LINE_PATTERN = re.compile(r"^\s*(WARN|FAIL):\s*(.+)$")


def classify(message: str) -> str:
    """Return the warning-class name for a message, or 'unclassified'."""
    for class_name, pattern in KNOWN_SIGNATURES:
        if re.search(pattern, message):
            return class_name
    return "unclassified"


def parse_ci_output(text: str) -> list[dict]:
    """Extract WARN/FAIL records from CI stdout."""
    records = []
    for line in text.splitlines():
        m = LINE_PATTERN.match(line)
        if not m:
            continue
        severity, msg = m.group(1), m.group(2).strip()
        records.append({
            "severity": severity,
            "message": msg,
            "class": classify(msg),
        })
    return records


def aggregate(records: list[dict]) -> dict[str, dict]:
    """Group by class. Returns {class_name: {count, severity, sample}}."""
    out: dict[str, dict] = {}
    for r in records:
        c = r["class"]
        if c not in out:
            out[c] = {"count": 0, "severity": r["severity"], "sample": r["message"]}
        out[c]["count"] += 1
        # Promote severity: FAIL > WARN
        if r["severity"] == "FAIL":
            out[c]["severity"] = "FAIL"
    return out


def parse_existing_log(path: Path) -> dict[str, dict]:
    """Parse the per-class blocks from an existing warnings-log.md.

    Each class block looks like:

        ## <class_name>
        - **First seen**: <date>
        - **Last seen**: <date>
        - **Count**: <N>
        - **Severity**: WARN|FAIL
        - **Sample**: <quoted text>
        - **Status**: open|closed|accepted-as-baseline

    Returns {class_name: {first_seen, last_seen, count, severity, sample, status}}.
    Tolerates missing fields (returns whatever was found).
    """
    if not path.exists():
        return {}

    out: dict[str, dict] = {}
    current = None
    for raw in path.read_text().splitlines():
        line = raw.rstrip()
        if line.startswith("## ") and not line.startswith("## TL;DR"):
            current = line[3:].strip()
            out[current] = {}
            continue
        if current is None or not line.startswith("- **"):
            continue
        m = re.match(r"- \*\*([\w ]+)\*\*:\s*(.*)$", line)
        if m:
            field = m.group(1).strip().lower().replace(" ", "_")
            value = m.group(2).strip().strip('"').strip("'")
            out[current][field] = value
    return out


def merge(
    existing: dict[str, dict],
    current: dict[str, dict],
    today: str,
) -> dict[str, dict]:
    """Merge a fresh CI run into the existing log. Keep history, update counts."""
    merged = dict(existing)
    for class_name, fresh in current.items():
        prev = merged.get(class_name, {})
        merged[class_name] = {
            "first_seen": prev.get("first_seen") or today,
            "last_seen": today,
            "count": int(prev.get("count", 0)) + fresh["count"],
            "severity": fresh["severity"],
            "sample": fresh["sample"],
            "status": prev.get("status", "open"),
        }
    return merged


def render(merged: dict[str, dict]) -> str:
    """Render the warnings-log.md content."""
    lines = [
        "# Warnings Log",
        "",
        "*CI signal capture for the self-learning loop. Auto-updated by "
        "`ingest_warnings.py` in the Mycelium plugin. Each class lists when it was "
        "first/last seen and how often. Best-practice fixes live in the plugin's "
        "`engine/warning-handbook.md`.*",
        "",
        "## TL;DR",
        "",
        f"*Auto-rendered. {len(merged)} known warning class(es) tracked. "
        "When a class's count rises across runs without a status change, that's a "
        "graduation signal — extend the harness one layer up rather than fixing "
        "the symptom (Lopopolo reframe).*",
        "",
    ]
    # Sort: open / FAIL first (highest priority), then by count desc
    status_rank = {"open": 0, "accepted-as-baseline": 1, "closed": 2}
    severity_rank = {"FAIL": 0, "WARN": 1}

    def sort_key(item):
        name, rec = item
        status = rec.get("status", "open")
        severity = rec.get("severity", "WARN")
        count = int(rec.get("count", 0))
        return (
            status_rank.get(status, 0),
            severity_rank.get(severity, 1),
            -count,
            name,
        )

    for name, rec in sorted(merged.items(), key=sort_key):
        lines.extend([
            f"## {name}",
            "",
            f"- **First seen**: {rec.get('first_seen', '?')}",
            f"- **Last seen**: {rec.get('last_seen', '?')}",
            f"- **Count**: {rec.get('count', 0)}",
            f"- **Severity**: {rec.get('severity', 'WARN')}",
            f"- **Sample**: \"{rec.get('sample', '')}\"",
            f"- **Status**: {rec.get('status', 'open')}",
            f"- **Best practice**: see warning-handbook.md#{name.replace('_', '-')}",
            "",
        ])
    return "\n".join(lines).rstrip() + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "-f", "--file", type=Path,
        help="Read CI output from file (default: stdin)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print result, do not write log",
    )
    parser.add_argument(
        "--log-path", type=Path, default=WARNINGS_LOG,
        help="Override path to warnings-log.md (testing)",
    )
    args = parser.parse_args()

    text = args.file.read_text() if args.file else sys.stdin.read()
    records = parse_ci_output(text)
    if not records:
        print("ingest_warnings: no WARN/FAIL lines found", file=sys.stderr)
        sys.exit(0)

    current = aggregate(records)
    existing = parse_existing_log(args.log_path)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    merged = merge(existing, current, today)
    rendered = render(merged)

    # Surface unclassified entries (handbook gap signal)
    if "unclassified" in current:
        n = current["unclassified"]["count"]
        print(
            f"ingest_warnings: {n} unclassified WARN/FAIL line(s) — "
            "consider adding signature(s) to KNOWN_SIGNATURES + "
            "an entry to warning-handbook.md.",
            file=sys.stderr,
        )

    if args.dry_run:
        print(rendered)
        return

    args.log_path.parent.mkdir(parents=True, exist_ok=True)
    args.log_path.write_text(rendered)
    print(
        f"ingest_warnings: wrote {args.log_path} ({len(merged)} classes)",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
