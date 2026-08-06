#!/usr/bin/env python3
"""check_surface_registry.py — verify each declared reader actually reads its surface.

THE CLUSTER THIS CLOSES (`right-content-wrong-surface`, criterion met 2026-07-26):

    The artifact is produced correctly and on time. It is written to a surface
    no downstream mechanism reads. Nothing is lost to the human eye; everything
    is lost to the machinery. The failure is invisible by construction, because
    a reader who opens the surface where the content DID land sees a complete,
    well-reasoned artifact and concludes the loop closed.

    Three instances, in three different artifact pairs:
      1. BVSSH assessments -> decision-log, never the canvas the hook reads (x3)
      2. A release lesson -> changelog, never corrections.md
      3. Upstream candidates -> a chronological log, read by no mechanism at all

    The first two got point-checks. The criterion said a third instance in a
    different pair graduates this to a GENERAL mechanism rather than a third
    point-check. This is that mechanism.

WHAT IT CHECKS — the wiring claim, not the content
    For every row in `engine/surface-registry.yml` that declares an
    authoritative surface and at least one reader, confirm each reader file
    exists AND textually references that surface. A declared reader that does
    not mention the file it supposedly reads is a loop that cannot close, which
    is this cluster one level up: the REGISTRY would be right-content on a
    wrong-surface.

WHAT IT DELIBERATELY DOES NOT CHECK
    Whether content actually landed in a given instance. That is per-artifact
    and belongs to the point-checks (`check_bvssh_reconcile.py`,
    `check_cluster_reconcile.py`, Check 48). Trying to do it generically would
    require knowing each artifact's shape, which is how a general mechanism
    turns back into three special cases wearing one name.

ROWS WITH NO SURFACE ARE REPORTED, NOT SKIPPED
    `authoritative_surface: null` is legal and is reported as an OPEN row. The
    registry's most important entry is currently the one with no surface at all
    (upstream candidates, 17 known items, no reader). A checker that quietly
    passed over null rows would hide exactly the case the cluster exists for —
    and would be an absence read as a pass, anti-pattern #9.

    Open rows do NOT fail the check. They are a known, recorded gap with a
    decision attached, not a regression. They fail only under --strict, which
    exists so a project that has closed all its rows can keep them closed.

ABSENT-INPUT DISCIPLINE (anti-pattern #9)
    - No registry file      -> exit 0, SKIP. Not every project has one.
    - Registry unparseable  -> exit 2, LOUD. A malformed registry must never
      read as an empty one.
    - Registry parses to no rows -> exit 0 with the `registry-empty` token,
      because "no rows" and "I could not find the rows" must differ.

Usage:
    check_surface_registry.py [--plugin-root DIR] [--strict] [--json]

Exit codes:
    0 — every declared reader references its surface
    1 — a broken wiring claim (or, with --strict, an open row)
    2 — argument/input error, or the registry could not be read

Python stdlib + PyYAML.
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - dependency is framework-wide
    print("check_surface_registry: PyYAML is required", file=sys.stderr)
    sys.exit(2)

REGISTRY_REL = Path("engine") / "surface-registry.yml"


def load_registry(plugin_root: Path):
    """Return the parsed row list. Raises RuntimeError on a malformed file."""
    path = plugin_root / REGISTRY_REL
    if not path.is_file():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RuntimeError(f"{REGISTRY_REL} is not parseable YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise TypeError(f"{REGISTRY_REL} did not parse to a mapping")
    rows = data.get("surfaces")
    if rows is None:
        return []
    if not isinstance(rows, list):
        raise TypeError(f"{REGISTRY_REL}#surfaces is not a list")
    return rows


def _reader_path(repo_root: Path, reader: str) -> Path:
    """Registry reader paths are repo-relative (they name plugins/... or docs/...)."""
    return repo_root / reader


def evaluate(plugin_root: Path, repo_root: Path):
    """Return (findings, open_rows, checked_count). Pure."""
    rows = load_registry(plugin_root)
    if rows is None:
        return None, None, None

    findings = []
    open_rows = []
    checked = 0

    for row in rows:
        if not isinstance(row, dict):
            findings.append({"row": "<malformed>", "problem": "row is not a mapping"})
            continue
        name = str(row.get("artifact_class", "<unnamed>"))
        surface = row.get("authoritative_surface")
        readers = row.get("read_by") or []

        if not surface:
            open_rows.append({
                "artifact_class": name,
                "reason": "no authoritative surface declared",
            })
            continue

        if not readers:
            open_rows.append({
                "artifact_class": name,
                "reason": f"surface {surface} declared but no reader",
            })
            continue

        # The surface is named in the registry as a project-relative path
        # (".claude/canvas/..."). Readers reference it however they reference
        # it — a full path, or the bare filename in a plugin-root-relative
        # context. Match on the basename, which is what survives both forms.
        needle = Path(str(surface)).name

        for reader in readers:
            checked += 1
            rpath = _reader_path(repo_root, str(reader))
            if not rpath.is_file():
                findings.append({
                    "artifact_class": name,
                    "reader": str(reader),
                    "surface": str(surface),
                    "problem": "declared reader does not exist",
                })
                continue
            text = rpath.read_text(encoding="utf-8", errors="replace")
            if needle not in text:
                findings.append({
                    "artifact_class": name,
                    "reader": str(reader),
                    "surface": str(surface),
                    "problem": (
                        f"declared reader never mentions {needle} — the wiring claim "
                        f"is false, so this loop cannot close"
                    ),
                })

    return findings, open_rows, checked


def _print_human(findings, open_rows, checked, *, strict, failed):
    """Render findings and open rows for a terminal reader."""
    for f in findings:
        who = f.get("reader", "")
        print(
            f"check_surface_registry: FAIL — [{f.get('artifact_class')}] "
            f"{who}: {f['problem']}"
        )
    for o in open_rows:
        label = "FAIL" if strict else "OPEN"
        print(f"check_surface_registry: {label} — [{o['artifact_class']}] {o['reason']}")
    if not failed:
        print(
            f"check_surface_registry: OK — {checked} reader/surface wiring claim(s) verified, "
            f"{len(open_rows)} row(s) open and recorded as such."
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify every declared reader in the surface registry reads its surface."
    )
    parser.add_argument(
        "--plugin-root", default=None,
        help="plugin root holding engine/surface-registry.yml (default: derived from __file__)",
    )
    parser.add_argument(
        "--root", default=None,
        help=(
            "repo root; the plugin root is derived as <root>/plugins/mycelium. Exists so "
            "check_empty_input_honesty.py can aim this at an empty tree -- without it that "
            "guard reports this script as untestable and its empty-input behaviour goes "
            "unverified, which is the anti-pattern #9 shape one level up."
        ),
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="also fail on rows with no authoritative surface or no reader",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    if args.plugin_root:
        plugin_root = Path(args.plugin_root).resolve()
    elif args.root:
        plugin_root = (Path(args.root) / "plugins" / "mycelium").resolve()
    else:
        plugin_root = Path(__file__).resolve().parent.parent
    if not plugin_root.is_dir():
        print(f"check_surface_registry: not a directory: {plugin_root}", file=sys.stderr)
        return 2

    # Readers are named repo-relative (plugins/mycelium/hooks/...), so resolve
    # them against the repo root, two levels above the plugin root.
    repo_root = plugin_root.parent.parent

    try:
        findings, open_rows, checked = evaluate(plugin_root, repo_root)
    except (RuntimeError, TypeError) as exc:
        print(f"check_surface_registry: ERROR — {exc}", file=sys.stderr)
        return 2

    if findings is None:
        # PRECONDITION FAILURE, not a pass. The first version returned 0 here on
        # the reasoning that "not every project has a registry" -- the same shape
        # as check_bvssh_reconcile's honest skip. check_empty_input_honesty.py
        # rejected it, and correctly: the registry SHIPS WITH THE PLUGIN, so its
        # absence means the plugin tree is broken or misrooted, not that this
        # project opted out. Exiting 0 there would be a check that verified
        # nothing and read green forever -- anti-pattern #9, in the guard built
        # to close anti-pattern #9's sibling cluster.
        msg = (
            f"cannot verify: no {REGISTRY_REL} under {plugin_root}. This file ships with "
            f"the plugin, so its absence means the tree is broken or --plugin-root is wrong. "
            f"NOTHING WAS VERIFIED."
        )
        if args.json:
            print(json.dumps({"status": "precondition-failed", "reason": msg}))
        else:
            print(f"check_surface_registry: ERROR — {msg}", file=sys.stderr)
        return 2

    if not findings and not open_rows and checked == 0:
        msg = "registry-empty — surface registry parsed with zero rows"
        print(json.dumps({"status": "ok", "detail": msg}) if args.json
              else f"check_surface_registry: OK — {msg}")
        return 0

    failed = bool(findings) or (args.strict and bool(open_rows))

    if args.json:
        print(json.dumps({
            "status": "broken" if failed else "ok",
            "findings": findings,
            "open_rows": open_rows,
            "readers_checked": checked,
        }, indent=2))
        return 1 if failed else 0

    _print_human(findings, open_rows, checked, strict=args.strict, failed=failed)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
