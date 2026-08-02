#!/usr/bin/env python3
"""check_legacy_paths.py — static guard against post-migration legacy-path rot.

Why this exists: the legacy→plugin migration moved the framework's reference
content out of `.claude/` and into `plugins/mycelium/`. Documentation that still
tells a reader to "see `.claude/engine/X`" is a dead pointer — the dir no longer
exists in the repo, and in a plugin-form install it lives in the plugin cache
(`${CLAUDE_PLUGIN_ROOT}/...`), never in the user's `.claude/`.

The sibling `check_doc_references.py` cannot catch this class: by design it only
follows markdown links `[text](target)` (bare path tokens produced 95% false
positives). This rot lives in **code-spans and prose** (`` `.claude/engine/X` ``),
so it needs a separate, narrowly-scoped check. A 2026-06-18 audit found this rot
across docs/ + CLAUDE.md + engine/orchestration doc files, weeks after a link-only
sweep (v0.49.5) had passed clean.

Scope — deliberately narrow to keep false positives ~zero:
  - PATTERN: `.claude/(engine|orchestration|schemas|templates|scripts|domains|tests)/`
    plus the specific framework FILENAMES under `.claude/harness/` and `.claude/jit-tooling/`.
    Those two are split trees — framework docs moved to plugins/mycelium/, but decision-log.md,
    wiring-contract.yml, active-stack.yml and active-metrics.yml are project state and belong
    in .claude/. Matching the bare directory flags legitimate project-state references, which
    is why this is filename-scoped (found by running it, 2026-07-30).
    (`jit-tooling` and `harness` added 2026-07-30: both are framework trees that moved
    to plugins/mycelium/ in the same migration, and both were missing from this pattern,
    so the guard built for exactly this rot class was blind to them for ~3 months.)
    These dirs have NO legitimate user-runtime path in plugin form — they are
    always either repo source (`plugins/mycelium/...`) or plugin cache
    (`${CLAUDE_PLUGIN_ROOT}/...`).
    WIDENED 2026-07-26 (+templates, scripts, domains, tests): the original three
    left holes exactly where live rot was sitting. `/xai-check` told the agent to
    read `.claude/templates/ai-system-card.md` (packaged at
    `${CLAUDE_PLUGIN_ROOT}/templates/`), and `.claude/domains/` is the dead
    Pre-Task path the v0.58.0 plugin-form finding had already flagged — both
    invisible to a guard built for this exact class. A guard with holes where the
    bugs are reads green and is worse than none.
  - EXCLUDED from the pattern: `.claude/skills/` and `.claude/harness/`. Those DO
    have legitimate runtime references — skills are discovered from `.claude/skills/`
    after opencode vendoring; `.claude/harness/` holds user project state
    (decision-log). Policing them would false-positive on correct docs.
  - SCAN: doc files only (`.md`). Scripts (`.sh`/`.py`), the dual-tree
    `manifest.yml`/`surfaces.yml`, and other config legitimately reference the
    runtime `.claude/` tree and are out of scope.
  - ALLOWLIST: files that intentionally document the legacy install form.

Usage:
    check_legacy_paths.py [--root REPO_ROOT] [--json]

Exit codes:
    0 — no legacy-path rot
    1 — at least one stale reference (CI gate)
    2 — argument/setup error

Python stdlib only.
"""
import argparse
import json
import re
import sys
from pathlib import Path

# Doc files whose prose we police. Globs are repo-root-relative.
SCAN_GLOBS = [
    "CLAUDE.md",
    "README.md",
    "docs/**/*.md",
    "plugins/mycelium/**/*.md",
]

# The moved reference dirs with no legitimate plugin-form runtime path.
LEGACY_RE = re.compile(
    r"\.claude/(engine|orchestration|schemas|templates|scripts|domains|tests)/"
    # harness/ and jit-tooling/ are SPLIT trees: framework files moved to
    # plugins/mycelium/, but decision-log.md, wiring-contract.yml, active-stack.yml
    # and active-metrics.yml are project state and correctly live in .claude/.
    # So match the framework FILENAMES, never the bare directory.
    r"|\.claude/harness/(anti-patterns|behavioral-contract|cognitive-biases"
    r"|communication-rules|context-management|delegation-authority|design-principles"
    r"|engineering-principles|guardrails|guardrails-core|guardrails-delivery"
    r"|guardrails-discovery|guardrails-index|guardrails-market|security-trust"
    r"|theory-tensions)\.md"
    r"|\.claude/jit-tooling/(adoption-strategy|cicd-patterns|definition-of-done"
    r"|detector|metrics-detector|security-scanning|testing-strategy)\.md"
)

# Files that intentionally document the legacy install form (deprecated, removed
# at the version named in each project's deprecation notice). Relative to root.
ALLOWLIST_FILES = {
    "AGENTS.md",                                              # dual-form transition doc
    "docs/migration.md",                                     # legacy→plugin migration guide
    "docs/install-paths.md",                                 # documents both install forms
    "docs/changelog.md",                                     # frozen historical record
    "plugins/mycelium/skills/migrate-from-legacy/SKILL.md",  # names legacy dirs to delete
    # Receipts cases that document the migration/rot itself quote the moved
    # paths as their subject, not as live pointers. Allowlist per-case.
    "docs/receipts/cases/2026-06-18-legacy-path-rot-guard.md",
}


def iter_scan_files(root: Path):
    seen = set()
    for g in SCAN_GLOBS:
        for p in root.glob(g):
            if p.is_file() and p not in seen:
                seen.add(p)
                yield p


def scan(root: Path):
    hits = []  # (src_rel, lineno, line)
    files_scanned = 0
    for f in iter_scan_files(root):
        src_rel = str(f.relative_to(root))
        if src_rel in ALLOWLIST_FILES:
            continue
        files_scanned += 1
        for i, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            # An embedded `*Version ...` changelog line is a frozen historical
            # record (same rationale as allowlisting changelog.md): it
            # legitimately quotes moved paths when narrating a past fix. Skip it
            # — the routing pointers elsewhere in the same file are still
            # scanned. Generalised from a CLAUDE.md-only skip 2026-07-26, when
            # widening the dir list surfaced the identical construct in
            # engine/version-discipline.md; the rule was always about the line
            # shape, not about one file.
            if line.lstrip().startswith("*Version"):
                continue
            if LEGACY_RE.search(line):
                hits.append((src_rel, i, line.strip()[:120]))
    return {"files_scanned": files_scanned, "hits": hits}


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Guard against stale framework-dir references in .claude/ docs.",
    )
    p.add_argument("--root", default=None, help="Repo root (default: auto-detect).")
    p.add_argument("--json", action="store_true", help="Emit JSON.")
    args = p.parse_args(argv)

    # scripts live at <root>/plugins/mycelium/scripts/
    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[3]

    if not root.exists():
        print(f"error: root does not exist: {root}", file=sys.stderr)
        return 2

    report = scan(root)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Legacy paths: scanned {report['files_scanned']} doc file(s) "
              f"for stale .claude/{{engine,orchestration,schemas,templates,"
              f"scripts,domains,tests}}/ references.")
        if report["hits"]:
            print(f"\nSTALE references ({len(report['hits'])}) — these dirs moved to "
                  f"plugins/mycelium/ (repo) / ${{CLAUDE_PLUGIN_ROOT}}/ (installed):")
            for src, lineno, line in report["hits"]:
                print(f"  {src}:{lineno}\n      {line}")
            print("\nFix: repoint to plugins/mycelium/<dir>/ (docs) or a relative path "
                  "(plugin-internal files). If the reference intentionally documents the "
                  "legacy form, add the file to ALLOWLIST_FILES.")
        elif not report["files_scanned"]:
            print("NOT A PASS: 0 doc file(s) were scanned, so nothing was "
                  "verified. Either --root points somewhere with no docs, or the "
                  "file pattern has stopped matching this repo's layout.")
            return 1
        else:
            print(f"No stale legacy-path references across "
                  f"{report['files_scanned']} scanned file(s).")

    return 1 if report["hits"] else 0


if __name__ == "__main__":
    sys.exit(main())
