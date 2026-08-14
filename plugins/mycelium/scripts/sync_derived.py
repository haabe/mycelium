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

AMBIGUITY (added v0.110.3, after this script tried to corrupt a true sentence)
The skill-count sweep rests on an assumption stated in SKILL_COUNT_FILES: that in
those files, EVERY "<N> skills" token means the total. That assumption is not
self-evident and it has been violated in practice — a CLAUDE.md version note
reading "shipped in 22 skills" (22 of them, not the total) would have been
rewritten to "60 skills" and made false, silently, by a passing gate.

The script cannot tell a stale total from a different quantity, so it no longer
guesses. When a file holds more than one DISTINCT "<N> skills" value, it refuses
to rewrite that file, names every token with its line number, and exits non-zero
in both modes. Authors who deliberately need a non-total number mark that line
with the LITERAL_MARKER below; marked tokens are never rewritten and never count
toward ambiguity.

Modes:
  (default)   rewrite drifted tokens in place; print what changed.
  --check     report drift and exit 1 if any; write nothing (CI/pre-push use).

Exit codes:
  0  no drift, or drift written successfully
  1  drift found in --check mode
  2  ambiguous skill-count tokens — a human must resolve; nothing was written

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
SKILLS_TOKEN_RE = re.compile(r"\b(\d+) skills\b")

# A line carrying this marker holds a "<N> skills" number that is NOT the total.
# Its tokens are never rewritten and never count toward ambiguity. Use it when the
# number is a genuine quantity — "the ID-scan block ships in 22 skills" — rather
# than a stale copy of the total.
LITERAL_MARKER = "skills-literal"

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
    # added v0.66.4: these carried hardcoded counts that no sweep covered and had
    # drifted to 58 while disk was 60. Same failure the v0.40.4 comment above
    # describes — the fix each time was one more file, so this list is the
    # mechanism and anything holding a skill total belongs in it.
    "docs/context-surface.md",
    "docs/architecture.md",
    "docs/integrations/opencode.md",
    "docs/integrations/codex.md",
    "docs/integrations/cursor.md",
    "docs/README.md",
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


def _rewrite_skill_tokens(text: str, skill_count: int) -> tuple[str, list[str], list[str]]:
    """Rewrite "<N> skills" tokens line-wise.

    Returns (new_text, changed_descriptions, ambiguity_descriptions).

    Lines carrying LITERAL_MARKER are passed through untouched and excluded from
    the distinct-value tally, so a deliberate non-total number neither gets
    corrupted nor blocks the sweep. Everything else is measured first: if the
    file holds more than one distinct value, NOTHING in it is rewritten and the
    caller is handed the evidence to show a human.
    """
    lines = text.split("\n")
    seen: dict[str, list[int]] = {}  # token value → 1-indexed line numbers
    for i, line in enumerate(lines, 1):
        if LITERAL_MARKER in line:
            continue
        for m in SKILLS_TOKEN_RE.finditer(line):
            seen.setdefault(m.group(1), []).append(i)

    if len(seen) > 1:
        amb = [
            f'line {n}: "{lines[n - 1].strip()[:100]}"'
            for val in sorted(seen, key=int)
            for n in seen[val]
        ]
        return text, [], amb

    changed: list[str] = []
    out: list[str] = []
    for i, line in enumerate(lines, 1):
        if LITERAL_MARKER in line:
            out.append(line)
            continue
        new_line = SKILLS_TOKEN_RE.sub(f"{skill_count} skills", line)
        if new_line != line:
            changed.append(f"line {i}")
        out.append(new_line)
    return "\n".join(out), changed, []


def _compute_drift(
    root: Path, version: str, skill_count: int,
) -> tuple[dict[str, str], list[str], list[str]]:
    """Fold both derive passes into (staged_text_by_rel, drift list, ambiguity list)."""
    staged: dict[str, str] = {}  # rel_path → latest in-memory text (folds both passes)
    drifted: list[str] = []
    ambiguous: list[str] = []

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
        # Skip files this repo/checkout does not have. A consuming project runs
        # this script against its own tree and will not carry Mycelium's own docs
        # (docs/integrations/*, docs/architecture.md, ...), so a missing entry is
        # normal rather than an error. Added 2026-07-30 when extending the list
        # surfaced the crash — the loop had assumed every target exists.
        if rel not in staged and not (root / rel).exists():
            continue
        old = current(rel)
        new, changed, amb = _rewrite_skill_tokens(old, skill_count)
        if amb:
            ambiguous.append(
                f"{rel}: {len(amb)} '<N> skills' tokens with differing values — "
                f"cannot tell a stale total from a real quantity:\n      "
                + "\n      ".join(amb)
            )
            continue
        if new != old:
            drifted.append(f"{rel}: skill count → {skill_count} ({', '.join(changed)})")
            staged[rel] = new

    return staged, drifted, ambiguous


def sync(root: Path, check_only: bool) -> int:
    version = canonical_version(root)
    skill_count = canonical_skill_count(root)
    staged, drifted, ambiguous = _compute_drift(root, version, skill_count)

    # Ambiguity outranks drift and blocks BOTH modes. Rewriting a file whose
    # tokens disagree is how a true sentence gets turned into a false one by a
    # gate that then reports success.
    if ambiguous:
        print(f"AMBIGUOUS (version={version}, skills={skill_count}) — nothing written:")
        for a in ambiguous:
            print(f"  - {a}")
        print(
            f"\n  Resolve by hand. If a number is genuinely NOT the total, mark its line\n"
            f"  with '{LITERAL_MARKER}' (e.g. an HTML comment) and it will be left alone."
        )
        return 2

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
