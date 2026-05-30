#!/usr/bin/env python3
"""Sync mechanically-derivable values into the files that quote them.

Two values are derived from a single source of truth and otherwise hand-copied
into several files (where they drift and get caught late by Validator Checks
6/7/10/30):

  - version:     canonical = the ``*Version X.Y.Z`` line in CLAUDE.md.
                 target     = plugins/mycelium/.claude-plugin/plugin.json#version
  - skill_count: canonical = number of plugins/mycelium/skills/*/SKILL.md files.
                 targets    = every "<N> skills" token in CLAUDE.md, README.md,
                              docs/skills/README.md, plugin.json, marketplace.json

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

VERSION_RE = re.compile(r"^\*Version (\d+\.\d+\.\d+)", re.MULTILINE)
PLUGIN_VERSION_RE = re.compile(r'("version":\s*")\d+\.\d+\.\d+(")')
SKILLS_TOKEN_RE = re.compile(r"\b\d+ skills\b")

# Files whose "<N> skills" tokens all refer to the total skill count.
SKILL_COUNT_FILES = [
    "CLAUDE.md",
    "README.md",
    "docs/skills/README.md",
    "plugins/mycelium/.claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
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


def _apply(root: Path, rel: str, pattern: re.Pattern, replacement: str) -> tuple[bool, str]:
    """Return (changed, new_text) for one file. Does not write."""
    path = root / rel
    old = path.read_text(encoding="utf-8")
    new = pattern.sub(replacement, old)
    return (new != old, new)


def sync(root: Path, check_only: bool) -> int:
    version = canonical_version(root)
    skill_count = canonical_skill_count(root)

    edits: list[tuple[str, str]] = []  # (rel_path, new_text)
    drifted: list[str] = []

    # version → plugin.json
    plugin_rel = "plugins/mycelium/.claude-plugin/plugin.json"
    changed, new = _apply(root, plugin_rel, PLUGIN_VERSION_RE, rf"\g<1>{version}\g<2>")
    if changed:
        drifted.append(f"{plugin_rel}: version → {version}")
        edits.append((plugin_rel, new))

    # skill_count → every "<N> skills" token
    for rel in SKILL_COUNT_FILES:
        changed, new = _apply(root, rel, SKILLS_TOKEN_RE, f"{skill_count} skills")
        if changed:
            drifted.append(f"{rel}: skill count → {skill_count}")
            edits.append((rel, new))

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

    # plugin.json may appear twice (version + skill count); merge by re-deriving.
    # Re-run sub on the latest content per file to fold both edits.
    merged: dict[str, str] = {}
    for rel, _ in edits:
        path = root / rel
        text = path.read_text(encoding="utf-8")
        text = PLUGIN_VERSION_RE.sub(rf"\g<1>{version}\g<2>", text)
        text = SKILLS_TOKEN_RE.sub(f"{skill_count} skills", text)
        merged[rel] = text
    for rel, text in merged.items():
        (root / rel).write_text(text, encoding="utf-8")
    print(f"Synced (version={version}, skills={skill_count}):")
    for d in drifted:
        print(f"  - {d}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="report drift, write nothing, exit 1 on drift")
    ap.add_argument("--root", default=str(REPO_ROOT), help="repo root (default: inferred from script location)")
    args = ap.parse_args(argv)
    return sync(Path(args.root), args.check)


if __name__ == "__main__":
    sys.exit(main())
