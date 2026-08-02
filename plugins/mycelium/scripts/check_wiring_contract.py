#!/usr/bin/env python3
"""Wiring contract — derive a project's own integration conventions, then hold it to them.

WHY (2026-07-26). `check_wiring.py` enforces Mycelium's *own* wiring rules, which
are hard-coded because Mycelium's structure is known. A project built WITH
Mycelium has different joins — a component must be imported by a parent, a route
must be registered, a migration must be listed — and the framework cannot ship a
catalogue of them. A sibling project solved this by hand-listing 4 component and 9
plugin integration points; that list is stale the moment someone adds the tenth,
which is the hand-enumerated scope this whole family of failures comes from.

So the rules are **derived from the repo's own majority convention** and carry the
evidence that produced them:

    - id: wc-002
      pattern: "scripts/*.py"
      obliges:
        - referenced_by: ["**/*"]
      detected_from: "18 of 20 files already satisfy this"
      confidence: 0.90

A rule asserted without observed support is a preference, not a contract. Rules
are REGENERATED, never hand-edited: if adding a file means remembering to add a
contract line, the contract has the disease it treats.

THE PROBLEM IS GENERAL, NOT LOCAL. Across 304,362 verified AI-authored commits in
6,275 repositories, "unused variables or parameters" is the second most frequent
issue class and "undefined variable or reference" — the writer/reader-disagreement
shape — is the most common runtime bug category. The mechanism is structural: a
model's limited context makes it unable to tell whether what it just generated is
used anywhere else, so plausible-but-unreferenced code is the expected output
rather than an aberration. And it accumulates: AI-authored code survives LONGER
than human-written code (53.9% vs 69.3% line death rate), so an orphan is less
likely than a human's to be cleaned up. Sediment, not churn.

Exit 0 clean, 1 on violations, 2 on usage error.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import sys
from pathlib import Path

try:
    from . import _text_lib
except ImportError:  # pragma: no cover - flat import from tests / direct run
    import _text_lib

# These scripts are run three ways: as `python3 .../scripts/x.py` from any cwd,
# imported as a package, and loaded by file path from tests. Only the first puts
# this directory on sys.path, so put it there explicitly before the sibling
# import — the alternative is a module that works until the way it is loaded
# changes, which is how this landed as a test-collection error the first time.
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from . import _scan_lib
except ImportError:  # invoked as a script, or loaded by file path
    import _scan_lib

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

CONTRACT_REL = ".claude/harness/wiring-contract.yml"

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".next", "vendor", "results",
    ".fixtures",  # exact-match missed the dotted form; see _scan_lib for the general fix
    # Fixture trees are deliberately synthetic mini-repos built to make a guard
    # fire. Governing them proposes rules about scaffolding and buries the real
    # findings; the detector offered five such rules on its first run here.
    "fixtures",
}

# A path-like token containing a glob, e.g. `tests/bash/test_*.sh` in a runner.
GLOB_TOKEN = re.compile(r"[\w./-]*\*[\w./*-]*")

# Extensions worth governing. Binary and data blobs have no "caller" in any
# meaningful sense, and including them would bury real findings under noise.
CODE_SUFFIXES = {
    ".py", ".sh", ".bash", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".go", ".rb", ".rs", ".java", ".kt", ".php", ".cs", ".swift",
}

# Same-directory files that exist to re-export their siblings.
BARREL_NAMES = ("index.ts", "index.tsx", "index.js", "index.ts", "__init__.py", "mod.rs")

# A group needs at least this many files before its convention is a convention
# rather than a coincidence.
MIN_GROUP = 3
# Fraction of a group that must already satisfy an obligation for it to be
# proposed. Below this it is an aspiration, and a contract full of aspirations
# fails on day one and gets deleted.
DEFAULT_THRESHOLD = 0.80
# Shorter tokens ("run", "app") match everywhere and carry no information.
MIN_TOKEN_LEN = 4
# Cap on the UNGOVERNED listing. The COUNT is always printed in full — only the
# listing is capped, and the remainder is stated.
MAX_LISTED = 15
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".ico", ".woff", ".woff2"}


class Violation:
    def __init__(self, rule_id: str, path: Path, detail: str):
        self.rule_id, self.path, self.detail = rule_id, path, detail

    def __str__(self) -> str:
        return f"  [{self.rule_id}] {self.path}\n      {self.detail}"


# ------------------------------------------------------------------ indexing

def _iter_files(root: Path) -> list[Path]:
    out = []
    ignored = _scan_lib.ignored_paths(root)
    for f in root.rglob("*"):
        if not f.is_file():
            continue
        if any(p in SKIP_DIRS for p in f.parts):
            continue
        if _scan_lib.is_ignored(f, ignored):
            continue
        out.append(f)
    return sorted(out)


def build_reference_index(
    root: Path,
    governed: list[Path],
    ignore: set[Path] | None = None,
) -> dict[Path, set[Path]]:
    """Map each governed file -> the set of files that reference it.

    Built by reading the repo ONCE and asking, per file, which governed names it
    mentions. The naive direction (for each governed file, search the repo) is
    O(files x repo) and unusable on anything real.
    """
    names: dict[str, list[Path]] = {}
    for g in governed:
        for token in {g.name, g.stem}:
            if len(token) >= MIN_TOKEN_LEN:
                names.setdefault(token, []).append(g)

    index: dict[Path, set[Path]] = {g: set() for g in governed}
    rel_of = {g: g.relative_to(root).as_posix() for g in governed}
    ignore = ignore or set()
    for f in _iter_files(root):
        # THE CONTRACT IS NOT A CALLER. It contains the very patterns it governs
        # (`scripts/*.py`), so counting it as a reference made every governed file
        # look wired and the guard passed a repo whose orphan it was pointed at.
        # A declaration that something should be called is not something calling it
        # — the same confusion as a doc claiming a script is "auto-updated".
        if f in ignore or f.suffix.lower() in BINARY_SUFFIXES:
            continue
        try:
            code = _text_lib.strip_comments(f.read_text(errors="replace"))
        except OSError:
            continue
        _add_name_refs(index, names, code, f)
        _add_glob_refs(index, rel_of, code, f)
    return index


def _add_name_refs(index, names, code: str, referrer: Path) -> None:
    """Direct references: the file's own name or stem appears in code."""
    for token, targets in names.items():
        if not _text_lib.references(code, token):
            continue
        for t in targets:
            if t != referrer:  # a file referencing its own name is not a caller
                index[t].add(referrer)


def _add_glob_refs(index, rel_of, code: str, referrer: Path) -> None:
    """DISCOVERY-BASED INVOCATION.

    A runner doing `for t in tests/bash/test_*.sh` names none of its targets, so a
    by-name index reports 50 orphans that in fact run on every CI pass. Measured
    here at 42-of-50 — just above the proposal threshold, so the rule would have
    shipped and then failed on 8 files that were never broken. A guard whose first
    act is eight false accusations does not get a second run.
    """
    for gtok in set(GLOB_TOKEN.findall(code)):
        if "*" not in gtok or len(gtok) < MIN_TOKEN_LEN:
            continue
        for t, rel in rel_of.items():
            if t is referrer or index[t]:
                continue
            if fnmatch.fnmatch(rel, gtok) or fnmatch.fnmatch(rel, f"**/{gtok}"):
                index[t].add(referrer)


# ------------------------------------------------------------------ detection

def _group_key(path: Path, root: Path) -> str:
    rel = path.relative_to(root)
    parent = rel.parent.as_posix()
    return f"{parent}/*{path.suffix}" if parent != "." else f"*{path.suffix}"


def detect(root: Path, threshold: float = DEFAULT_THRESHOLD) -> dict:
    """Propose contract rules from what the repo already does.

    Only two obligation types exist, and that is deliberate. Every additional
    obligation kind is another thing to keep in step with reality; two general
    ones that are always checked beat nine specific ones that rot.
    """
    governed = [
        f for f in _iter_files(root)
        if f.suffix.lower() in CODE_SUFFIXES
    ]
    if not governed:
        return {"contracts": []}

    index = build_reference_index(root, governed, ignore=set(contract_paths(root)))

    groups: dict[str, list[Path]] = {}
    for f in governed:
        groups.setdefault(_group_key(f, root), []).append(f)

    contracts = []
    for i, (pattern, members) in enumerate(sorted(groups.items()), start=1):
        if len(members) < MIN_GROUP:
            continue
        obliges = []

        referenced = [m for m in members if index[m]]
        ratio = len(referenced) / len(members)
        if ratio >= threshold:
            obliges.append({"referenced_by": ["**/*"]})

        barrel = next(
            (b for b in BARREL_NAMES if (members[0].parent / b).is_file()),
            None,
        )
        if barrel:
            in_barrel = [
                m for m in members
                if _text_lib.references(
                    _text_lib.strip_comments(
                        (m.parent / barrel).read_text(errors="replace"),
                    ),
                    m.stem,
                )
            ]
            if len(in_barrel) / len(members) >= threshold:
                obliges.append({"sibling_reference": barrel})

        if not obliges:
            continue
        contracts.append({
            "id": f"wc-{i:03d}",
            "pattern": pattern,
            "obliges": obliges,
            "detected_from": f"{len(referenced)} of {len(members)} files already satisfy this",
            "confidence": round(ratio, 2),
        })
    return {"contracts": contracts}


# ---------------------------------------------------------------- enforcement

def _matches(path: Path, root: Path, pattern: str) -> bool:
    """Glob match with `**` meaning "any depth, including none".

    fnmatch has no `**`: it translates every `*` to `.*`, so the literal pattern
    `**/*` compiles to something requiring a slash and therefore does NOT match a
    root-level file. A caller sitting at the repo root was read as no caller at
    all — the guard's own default glob silently excluded the commonest call site
    in a small project.
    """
    rel = path.relative_to(root).as_posix()
    if pattern in ("**", "**/*", "*"):
        return True
    candidates = {pattern, f"**/{pattern}"}
    if pattern.startswith("**/"):
        candidates.add(pattern[3:])
    return any(fnmatch.fnmatch(rel, c) for c in candidates)


def contract_paths(root: Path) -> list[Path]:
    """Files that DECLARE wiring rather than perform it."""
    p = root / CONTRACT_REL
    return [p] if p.is_file() else []


def enforce(root: Path, contract: dict) -> tuple[list[Violation], list[Path]]:
    """Check every rule, and return what NO rule covered.

    The ungoverned list is not a footnote. A contract reporting zero violations
    across four rules while three hundred files match nothing is describing the
    health of a subset and implying the whole — the exact false green this file
    exists to prevent. Callers must surface it.
    """
    rules = contract.get("contracts") or []
    governed_files = [f for f in _iter_files(root) if f.suffix.lower() in CODE_SUFFIXES]
    index = build_reference_index(root, governed_files, ignore=set(contract_paths(root)))

    violations: list[Violation] = []
    covered: set[Path] = set()

    for rule in rules:
        rid = rule.get("id", "wc-???")
        pattern = rule.get("pattern", "")
        exempt = {e.get("path") for e in (rule.get("exemptions") or []) if isinstance(e, dict)}
        members = [f for f in governed_files if _matches(f, root, pattern)]
        for m in members:
            covered.add(m)
            if m.relative_to(root).as_posix() in exempt:
                continue
            for ob in rule.get("obliges") or []:
                if "referenced_by" in ob:
                    globs = ob["referenced_by"] or ["**/*"]
                    refs = [
                        r for r in index.get(m, set())
                        if any(_matches(r, root, g) for g in globs)
                    ]
                    if not refs:
                        violations.append(Violation(
                            rid, m.relative_to(root),
                            "nothing references this file from non-comment code. "
                            f"Rule requires a reference from {globs}.",
                        ))
                elif "sibling_reference" in ob:
                    barrel = m.parent / ob["sibling_reference"]
                    ok = barrel.is_file() and _text_lib.references(
                        _text_lib.strip_comments(barrel.read_text(errors="replace")),
                        m.stem,
                    )
                    if not ok:
                        violations.append(Violation(
                            rid, m.relative_to(root),
                            f"not referenced from sibling {ob['sibling_reference']}.",
                        ))

    ungoverned = [f for f in governed_files if f not in covered]
    return violations, ungoverned


# ----------------------------------------------------------------------- CLI

def _load_contract(path: Path) -> dict | None:
    if not path.is_file():
        return None
    if yaml is None:  # pragma: no cover
        print("ERROR: PyYAML required to read the contract", file=sys.stderr)
        return None
    return yaml.safe_load(path.read_text()) or {}


def _run_detect(root: Path, threshold: float) -> int:
    proposal = detect(root, threshold)
    if yaml is None:  # pragma: no cover
        print("ERROR: PyYAML required", file=sys.stderr)
        return 2
    print("# DRAFT wiring contract — derived from this repo's own conventions.")
    print("# Review every rule before committing: a detected majority is evidence")
    print("# of a convention, not proof that the convention is correct.")
    print("# Regenerate rather than hand-edit when the structure changes.")
    print(yaml.safe_dump(proposal, sort_keys=False, allow_unicode=True))
    if not proposal["contracts"]:
        print("# No convention met the threshold. That is a finding, not a pass:",
              file=sys.stderr)
        print("# this repo has no majority wiring convention to enforce yet.",
              file=sys.stderr)
    return 0


def _report_ungoverned(ungoverned: list[Path], root: Path) -> None:
    if not ungoverned:
        return
    print(f"\n  UNGOVERNED: {len(ungoverned)} file(s) match no rule")
    for u in ungoverned[:MAX_LISTED]:
        print(f"    {u.relative_to(root)}")
    if len(ungoverned) > MAX_LISTED:
        print(f"    ... and {len(ungoverned) - MAX_LISTED} more")
    print("  Zero violations across a subset is not zero violations.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".")
    ap.add_argument("--contract", default=None, help=f"default {CONTRACT_REL}")
    ap.add_argument("--detect", action="store_true",
                    help="propose rules from the repo's own conventions; prints YAML")
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    ap.add_argument("--max-ungoverned", type=int, default=None,
                    help="fail when more than N files match no rule (default: report only)")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"ERROR: --root {root} is not a directory", file=sys.stderr)
        return 2

    if args.detect:
        return _run_detect(root, args.threshold)

    contract_path = Path(args.contract) if args.contract else root / CONTRACT_REL
    contract = _load_contract(contract_path)
    if contract is None:
        print(f"check_wiring_contract: no contract at {contract_path}")
        print("  Not a pass — nothing was verified. Generate a draft with:")
        print(f"    python3 {Path(__file__).name} --root . --detect > {CONTRACT_REL}")
        print("  then review it. A project with no declared wiring contract has no")
        print("  wiring guarantees; silence here is the absence this guard is for.")
        return 1

    violations, ungoverned = enforce(root, contract)

    print(f"check_wiring_contract: {len(contract.get('contracts') or [])} rule(s) "
          f"from {contract_path}")
    _report_ungoverned(ungoverned, root)

    if violations:
        print(f"\nFAIL: {len(violations)} wiring violation(s):\n")
        for v in violations:
            print(v)
        return 1

    if args.max_ungoverned is not None and len(ungoverned) > args.max_ungoverned:
        print(f"\nFAIL: {len(ungoverned)} ungoverned file(s) exceeds "
              f"--max-ungoverned {args.max_ungoverned}.")
        return 1

    print("\nPASS: every governed file satisfies its declared wiring obligations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
