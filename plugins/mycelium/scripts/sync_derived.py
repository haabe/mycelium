#!/usr/bin/env python3
"""Sync mechanically-derivable values into the files that quote them.

Two values are derived from a single source of truth and otherwise hand-copied
into several files (where they drift and get caught late by Validator Checks
6/7/10/30):

  - version:     canonical = the ``*Version X.Y.Z`` line in CLAUDE.md.
                 targets    = plugin.json#version and the ``**Version:**`` token
                              in docs/ai-system-card.md (the published AI System
                              Card is a disclosure artifact — a stale version on
                              it is a live honesty problem, not just untidy).
  - skill_count: canonical = number of plugins/mycelium/skills/*/SKILL.md files.
                 targets    = every "<N> skills" token in CLAUDE.md, README.md,
                              docs/skills/README.md, plugin.json, marketplace.json,
                              docs/ai-system-card.md

The CLAUDE.md *Version prose line and plugin descriptions stay hand-written;
this only rewrites the derived *tokens* inside them, never surrounding prose.

Modes:
  (default)   rewrite drifted tokens in place; print what changed.
  --check     report drift and exit 1 if any; write nothing (CI/pre-push use).

Manifest is deliberately NOT handled here: its framework/project_state/mixed
classification is a semantic judgement, not derivable from a directory walk —
auto-generating it would silently change what upgrade.sh replaces. Coverage of
the manifest is a validator concern (orphan detection), not a generator one.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

PLUGIN = "plugins/mycelium/.claude-plugin/plugin.json"
CARD = "docs/ai-system-card.md"

VERSION_RE = re.compile(r"^\*Version (\d+\.\d+\.\d+)", re.MULTILINE)
PLUGIN_VERSION_RE = re.compile(r'("version":\s*")\d+\.\d+\.\d+(")')
CARD_VERSION_RE = re.compile(r"(\*\*Version:\*\* )\d+\.\d+\.\d+")
SKILLS_TOKEN_RE = re.compile(r"\b\d+ skills\b")

# (rel_path, version pattern, replacement template) — each pattern only matches
# its own file's version form, so applying all of them to a file is safe.
VERSION_TARGETS = [
    (PLUGIN, PLUGIN_VERSION_RE, r"\g<1>{v}\g<2>"),
    (CARD, CARD_VERSION_RE, r"\g<1>{v}"),
]

# Files whose "<N> skills" tokens all refer to the total skill count.
SKILL_COUNT_FILES = [
    "CLAUDE.md",
    "README.md",
    "docs/skills/README.md",
    # added v0.40.4: by-category.md had a hardcoded skill count that drifted
    "docs/skills/by-category.md",
    PLUGIN,
    ".claude-plugin/marketplace.json",
    CARD,
    # SKILL.md files whose lone "<N> skills" token is the total count. Without
    # this sweep they restale (finding C, 2026-05-30: this file drifted to 44).
    "plugins/mycelium/skills/diamond-assess/SKILL.md",
]


def canonical_version(root: Path) -> str:
    text = (root / "CLAUDE.md").read_text(encoding="utf-8")
    m = VERSION_RE.search(text)
    if not m:
        raise ValueError("no '*Version X.Y.Z' line found in CLAUDE.md")
    return m.group(1)


def canonical_skill_count(root: Path) -> int:
    n = len(list((root / "plugins/mycelium/skills").glob("*/SKILL.md")))
    if n == 0:
        raise ValueError("zero SKILL.md files found under plugins/mycelium/skills/")
    return n


def _compute_drift(
    root: Path, version: str, skill_count: int,
) -> tuple[dict[str, str], list[str]]:
    """Fold both derive passes into (staged_text_by_rel, human-readable drift list)."""
    staged: dict[str, str] = {}  # rel_path → latest in-memory text (folds both passes)
    drifted: list[str] = []

    def current(rel: str) -> str:
        return staged.get(rel, (root / rel).read_text(encoding="utf-8"))

    # version → each target's own version token
    for rel, pattern, repl in VERSION_TARGETS:
        old = current(rel)
        new = pattern.sub(repl.format(v=version), old)
        if new != old:
            drifted.append(f"{rel}: version → {version}")
            staged[rel] = new

    # skill_count → every "<N> skills" token
    for rel in SKILL_COUNT_FILES:
        old = current(rel)
        new = SKILLS_TOKEN_RE.sub(f"{skill_count} skills", old)
        if new != old:
            drifted.append(f"{rel}: skill count → {skill_count}")
            staged[rel] = new

    return staged, drifted


def sync(root: Path, check_only: bool) -> int:
    version = canonical_version(root)
    skill_count = canonical_skill_count(root)
    staged, drifted = _compute_drift(root, version, skill_count)

    if check_only:
        if drifted:
            print(f"DRIFT (version={version}, skills={skill_count}):")
            for d in drifted:
                print(f"  - {d}")
            return 1
        print(f"OK: version={version}, skills={skill_count} — no drift.")
        return 0

    if not drifted:
        print(f"OK: version={version}, skills={skill_count} — nothing to sync.")
        return 0

    for rel, text in staged.items():
        (root / rel).write_text(text, encoding="utf-8")
    print(f"Synced (version={version}, skills={skill_count}):")
    for d in drifted:
        print(f"  - {d}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--check", action="store_true",
        help="report drift, write nothing, exit 1 on drift",
    )
    ap.add_argument(
        "--root", default=str(REPO_ROOT),
        help="repo root (default: inferred from script location)",
    )
    args = ap.parse_args(argv)
    return sync(Path(args.root), args.check)


if __name__ == "__main__":
    sys.exit(main())
