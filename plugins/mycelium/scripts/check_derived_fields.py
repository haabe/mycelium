#!/usr/bin/env python3
"""A canvas field that names its source is resolved from it; a stored copy beside it is compared.

THE DEFECT (dogfood 2026-09-02, register row canvas-has-no-derived-field-so-every-derivable-
value-is-stored-twice): the canvas schema had no notion of a DERIVED field, so every value
that could be computed was transcribed, and a value maintained by hand in two places
diverges. Measured drifts in one canvas: 56, 32, 27, 17 and 76 days; the block that carried
the sentence "a KPI block hand-copied from a snapshot directory will keep rotting until
something reads the directory instead" was itself 19 days stale when read. A correct
diagnosis in prose beside the field did not prevent one further cycle of the failure.

THE AFFORDANCE (0.218.0). Any mapping in a canvas or diamond file may carry `source_ref`,
a pointer in one of two forms:

    metrics/<source>#<dotted.path>            newest .claude/evals/metrics/<source>/*.json
    <file>.yml#<dotted.path>[|count[ k=v]]     a canvas, diamonds or harness file

A dotted path walks keys, list item ids, or list indexes; `|count` counts a list, and
`|count k=v` counts the items whose key equals the value. The mapping may also carry
`value` (or a literal under the same parent key) as a CACHE for readers that cannot
resolve; this script resolves the pointer and reports every cache that disagrees. A
pointer alone never rots, because nothing is stored to go stale. Nothing is written by
this script; /metrics-pull's never-auto-write rule is about evidence, and a pointer is not
evidence, but the write of a cache stays a human's, and the report says what it should be.

REFUSES TO GUESS. A pointer that does not resolve is reported as UNRESOLVED with the reason
(no snapshot directory, no such key, filter on a non-list), never treated as a match.

Exit codes: 0 report; 1 NOT A PASS when no canvas carries a `source_ref` (nothing resolved);
2 canvas dir missing.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

_REF = re.compile(r"^(?P<file>[A-Za-z0-9_./-]+)#(?P<path>[^|]*)"
                  r"(?:\|(?P<op>count)(?:\s+(?P<k>[A-Za-z0-9_.-]+)=(?P<v>.*))?)?$")
_MAX_DEPTH = 14
_DIRS = ("canvas", "diamonds", "harness")


def _load(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _is(item, seg: str) -> bool:
    """An item is named `seg` by its `id` or by any `*_id` key (cycle_id, leaf_id)."""
    return isinstance(item, dict) and any(
        str(v) == seg for k, v in item.items() if k == "id" or str(k).endswith("_id"))


def _step(node, seg: str):
    """One segment: a key, a list index, or an item id at this level or one list below."""
    if isinstance(node, dict):
        if seg in node:
            return node[seg], ""
        for v in node.values():
            if isinstance(v, list):
                hit = next((it for it in v if _is(it, seg)), None)
                if hit is not None:
                    return hit, ""
        return None, f"no key or id `{seg}`"
    if isinstance(node, list):
        if seg.isdigit() and int(seg) < len(node):
            return node[int(seg)], ""
        hit = next((it for it in node if _is(it, seg)), None)
        return (hit, "") if hit is not None else (None, f"no item id `{seg}`")
    return None, f"cannot descend into a scalar at `{seg}`"


def _walk_path(node, dotted: str):
    for seg in (s for s in dotted.strip(".").split(".") if s):
        node, why = _step(node, seg)
        if why:
            return None, why
    return node, ""


def _apply(node, op, k, v):
    if op != "count":
        return node, ""
    if not isinstance(node, list):
        return None, "count on a non-list"
    if k is None:
        return len(node), ""
    hits = sum(1 for it in node if isinstance(it, dict) and str(_walk_path(it, k)[0]) == v)
    return hits, ""


def resolve(ref: str, project: Path):
    """(value, reason): value is None with a reason when the pointer does not resolve."""
    m = _REF.match(ref.strip())
    if not m:
        return None, "malformed pointer"
    file, path = m.group("file"), m.group("path")
    op, k, v = m.group("op"), m.group("k"), m.group("v")
    try:
        if file.startswith("metrics/"):
            d = project / ".claude" / "evals" / "metrics" / file.split("/", 1)[1]
            snaps = sorted(d.glob("*.json")) if d.is_dir() else []
            if not snaps:
                return None, f"no snapshots under {d.relative_to(project)}"
            doc = json.loads(snaps[-1].read_text(encoding="utf-8"))
        else:
            cand = [project / ".claude" / sub / file for sub in _DIRS]
            hit = next((c for c in cand if c.is_file()), None)
            if hit is None:
                return None, f"no file {file} under .claude/{{{','.join(_DIRS)}}}"
            doc = _load(hit)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return None, f"unreadable source: {exc}"
    node, why = _walk_path(doc, path)
    if why:
        return None, why
    return _apply(node, op, k, v)


def _item_label(v, i: int) -> str:
    return str(v.get("id")) if isinstance(v, dict) and v.get("id") else str(i)


def _collect(node, canvas: str, label: str, out: list, depth: int = 0) -> None:
    if depth > _MAX_DEPTH:
        return
    if isinstance(node, dict):
        if isinstance(node.get("source_ref"), str):
            out.append((canvas, label, node["source_ref"], node.get("value")))
        for k, v in node.items():
            _collect(v, canvas, f"{label}.{k}" if label else str(k), out, depth + 1)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _collect(v, canvas, f"{label}[{_item_label(v, i)}]", out, depth + 1)


def pointers(project: Path):
    """(canvas, label, ref, cached) for every mapping carrying source_ref."""
    out: list = []
    for sub in _DIRS:
        for path in sorted((project / ".claude" / sub).glob("*.yml")):
            try:
                _collect(_load(path), f"{sub}/{path.name}", "", out)
            except (OSError, yaml.YAMLError):
                continue
    return out


def report(project: Path) -> int:
    rows = pointers(project)
    print("Derived fields (a field that names its source is read from it)")
    print("=" * 70)
    if not rows:
        print("  NOT A PASS: no mapping in canvas/, diamonds/ or harness/ carries `source_ref`;"
              " nothing was resolved.")
        return 1
    resolved = diverged = unresolved = 0
    for canvas, label, ref, cached in rows:
        value, why = resolve(ref, project)
        if why:
            unresolved += 1
            print(f"  UNRESOLVED [{canvas}] {label}: `{ref}` ({why})")
        elif cached is not None and cached != value:
            diverged += 1
            print(f"  DIVERGED   [{canvas}] {label}: cache {cached!r}, source says {value!r} "
                  f"(`{ref}`)")
        else:
            resolved += 1
            print(f"  ok         [{canvas}] {label} = {value!r}")
    print(f"\n  {len(rows)} pointer(s): {resolved} resolved, {diverged} DIVERGED, "
          f"{unresolved} unresolved.")
    if diverged:
        print("  A cache that disagrees with its source is the rot this pointer exists to end;\n"
              "  update the cache or drop it. Nothing is written here.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project-dir", default=".")
    args = ap.parse_args()
    project = Path(args.project_dir)
    if not (project / ".claude" / "canvas").is_dir():
        print(f"derived-fields: no canvas dir under {project}", file=sys.stderr)
        return 2
    return report(project)


if __name__ == "__main__":
    raise SystemExit(main())
