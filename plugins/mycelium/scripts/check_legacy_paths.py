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
  - PATTERN: `.claude/(engine|orchestration|schemas)/` only. These three dirs
    have NO legitimate user-runtime path in plugin form — they are always either
    repo source (`plugins/mycelium/...`) or plugin cache (`${CLAUDE_PLUGIN_ROOT}/...`).
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
LEGACY_RE = re.compile(r"\.claude/(engine|orchestration|schemas)/")

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
            # The CLAUDE.md `*Version ...` line is an embedded changelog record
            # (same rationale as allowlisting changelog.md): it legitimately
            # quotes moved paths when narrating a fix. Skip it — the routing
            # pointers elsewhere in CLAUDE.md are still scanned.
            if src_rel == "CLAUDE.md" and line.lstrip().startswith("*Version"):
                continue
            if LEGACY_RE.search(line):
                hits.append((src_rel, i, line.strip()[:120]))
    return {"files_scanned": files_scanned, "hits": hits}


def main(argv=None):
    p = argparse.ArgumentParser(description="Guard against stale .claude/{engine,orchestration,schemas}/ doc references.")
    p.add_argument("--root", default=None, help="Repo root (default: auto-detect).")
    p.add_argument("--json", action="store_true", help="Emit JSON.")
    args = p.parse_args(argv)

    if args.root:
        root = Path(args.root).resolve()
    else:
        # scripts live at <root>/plugins/mycelium/scripts/
        root = Path(__file__).resolve().parents[3]

    if not root.exists():
        print(f"error: root does not exist: {root}", file=sys.stderr)
        return 2

    report = scan(root)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Legacy paths: scanned {report['files_scanned']} doc file(s) "
              f"for stale .claude/{{engine,orchestration,schemas}}/ references.")
        if report["hits"]:
            print(f"\nSTALE references ({len(report['hits'])}) — these dirs moved to "
                  f"plugins/mycelium/ (repo) / ${{CLAUDE_PLUGIN_ROOT}}/ (installed):")
            for src, lineno, line in report["hits"]:
                print(f"  {src}:{lineno}\n      {line}")
            print("\nFix: repoint to plugins/mycelium/<dir>/ (docs) or a relative path "
                  "(plugin-internal files). If the reference intentionally documents the "
                  "legacy form, add the file to ALLOWLIST_FILES.")
        else:
            print("No stale legacy-path references.")

    return 1 if report["hits"] else 0


if __name__ == "__main__":
    sys.exit(main())
