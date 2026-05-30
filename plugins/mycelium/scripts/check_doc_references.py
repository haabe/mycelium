#!/usr/bin/env python3
"""check_doc_references.py — static dead-link guard for Mycelium docs.

Why this exists: a 2026-05-30 reference-graph recon found broken doc references
that no check guarded — the AI System Card template was cited in four files but
never created (fixed v0.33.0), and dead `manifest.yml` entries lingered since the
legacy→plugin migration. The recon's first cut produced ~377 "dead reference"
hits that were ~95% false positives because it resolved every path against the
repo root and scanned loose path-tokens. This script does it correctly:

  1. It only follows **markdown links** — `[text](target)` — which are
     author-intended references. A broken one is a real bug, not noise.
  2. Each link is resolved **relative to the linking file's own directory**
     (so `../CONTRIBUTORS.md` from docs/receipts/ resolves correctly).
  3. The `.claude/`↔`plugins/mycelium/` dual-tree mapping is applied: a link to
     a `.claude/X` runtime-install path resolves if EITHER `plugins/mycelium/X`
     (canonical source) or the repo-root `.claude/X` dogfood tree contains it.

Out of scope by design (this is what generated the recon's false positives):
  - Bare path tokens in prose (not inside a markdown link).
  - Glob/templated targets (`*.yml`, `{{PLACEHOLDER}}`, `<path>`).
  - External links (http/https/mailto) and pure `#anchor` fragments.

Usage:
    check_doc_references.py [--root REPO_ROOT] [--json]

Exit codes:
    0 — no dead references
    1 — at least one dead reference (CI gate)
    2 — argument/setup error

Python stdlib only.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

# Files whose markdown links we follow. Globs are repo-root-relative.
SCAN_GLOBS = [
    "CLAUDE.md",
    "README.md",
    "AGENTS.md",
    "CONTRIBUTORS.md",
    "docs/**/*.md",
    "plugins/mycelium/**/*.md",
]

MD_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")

# A target we never try to resolve (placeholder/glob/external/anchor-only).
SKIP_PREFIXES = ("http://", "https://", "mailto:", "#", "<")

# Intentional non-navigable links: (src_rel, target) pairs that are illustrative
# examples rather than real references. Keep this list short and documented —
# every entry is a link a reader cannot follow, justified only because the doc's
# purpose is to *show* a link shape, not to *use* it.
ALLOWLIST = {
    # docs/contributing/style.md demonstrates good vs bad link phrasing with
    # literal ❌/✅ examples pointing at evaluate.md; they are typography
    # samples, not navigation from the contributing/ subdir.
    ("docs/contributing/style.md", "evaluate.md"),
}


def iter_scan_files(root: Path):
    seen = set()
    for g in SCAN_GLOBS:
        for p in root.glob(g):
            if p.is_file() and p not in seen:
                seen.add(p)
                yield p


def clean_target(raw: str) -> str:
    """Strip a markdown link target down to a filesystem path, or '' to skip."""
    t = raw.strip()
    # Markdown allows `(path "title")` — drop the optional title.
    if " " in t:
        t = t.split(" ", 1)[0]
    # Drop anchor / query fragments.
    t = t.split("#", 1)[0].split("?", 1)[0]
    return t.strip()


def is_skippable(target: str) -> bool:
    if not target:
        return True
    if target.startswith(SKIP_PREFIXES):
        return True
    # Glob or template placeholders are not concrete paths.
    if any(ch in target for ch in ("*", "{", "}", "<", ">")):
        return True
    # A real file/dir link in this repo always has a slash or a dot-extension.
    # A bare word like "path" (from a `see [filename](path)` style example) is
    # a placeholder, not a navigable target.
    return "/" not in target and "." not in target


def candidate_paths(src_file: Path, target: str, root: Path):
    """Yield candidate filesystem paths a link target could resolve to."""
    cands = []
    # 1. Relative to the linking file's own directory.
    cands.append(src_file.parent / target)
    # 2. Repo-root-relative (some docs link from root regardless of location).
    cands.append(root / target)
    # 3. Dual-tree mapping: .claude/X (runtime path) -> plugins/mycelium/X
    #    (canonical source). Apply to both the raw target and the dir-relative
    #    resolution, since either tree may legitimately hold it.
    norm = target
    # Collapse a leading ./ and resolve any ../ against the file dir first.
    rel_resolved = (src_file.parent / target)
    for base in {str(target), str(rel_resolved)}:
        idx = base.find(".claude/")
        if idx != -1:
            tail = base[idx + len(".claude/") :]
            cands.append(root / "plugins" / "mycelium" / tail)
            cands.append(root / ".claude" / tail)
    if norm.startswith(".claude/"):
        tail = norm[len(".claude/") :]
        cands.append(root / "plugins" / "mycelium" / tail)
    # 4. Runtime-equivalent resolution. Docs under plugins/mycelium/<sub> are
    #    written with relative paths correct for their *installed* location at
    #    .claude/<sub> (e.g. plugins/mycelium/domains/README.md links
    #    ../../CLAUDE.md, correct once installed to .claude/domains/). Resolve
    #    the target as if the file lived at root/.claude/<sub> too.
    try:
        rel_to_plugin = src_file.relative_to(root / "plugins" / "mycelium")
        runtime_parent = (root / ".claude" / rel_to_plugin).parent
        cands.append(runtime_parent / target)
    except ValueError:
        pass
    return cands


def resolves(src_file: Path, target: str, root: Path) -> bool:
    for c in candidate_paths(src_file, target, root):
        # Normalize `..` lexically (not via the filesystem): the repo-root
        # .claude/ tree is partial, so a candidate like
        # .claude/domains/../../CLAUDE.md must collapse to CLAUDE.md without
        # requiring .claude/domains/ to exist for the OS to walk `..`.
        normalized = Path(os.path.normpath(c))
        try:
            if normalized.exists():
                return True
        except OSError:
            continue
    return False


def scan(root: Path):
    dead = []  # list of (src_rel, target)
    files_scanned = 0
    links_checked = 0
    for f in iter_scan_files(root):
        files_scanned += 1
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in MD_LINK.finditer(text):
            target = clean_target(m.group(1))
            if is_skippable(target):
                continue
            src_rel = str(f.relative_to(root))
            if (src_rel, target) in ALLOWLIST:
                continue
            links_checked += 1
            if not resolves(f, target, root):
                dead.append((src_rel, m.group(1).strip()))
    return {
        "files_scanned": files_scanned,
        "links_checked": links_checked,
        "dead": dead,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="Static dead-link guard for Mycelium docs.")
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
        print(
            f"Doc references: scanned {report['files_scanned']} file(s), "
            f"checked {report['links_checked']} markdown link(s)."
        )
        if report["dead"]:
            print(f"\nDEAD references ({len(report['dead'])}):")
            for src, target in report["dead"]:
                print(f"  {src}\n      -> {target}")
        else:
            print("No dead references.")

    return 1 if report["dead"] else 0


if __name__ == "__main__":
    sys.exit(main())
