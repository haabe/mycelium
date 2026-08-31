#!/usr/bin/env python3
"""Does every field that makes a machine-checkable promise have a consumer?

THE GAP THIS CLOSES (dogfood 2026-08-31). A field can be blessed by a schema, filled by a
skill, and read by NOTHING. It then looks populated to a human and is inert to the machine.
Measured that day: of 38 promise-shaped fields, SIX had no consumer of any kind — and one of
them, `unlocked_at`, was added hours earlier IN THE RELEASE THAT FIXED THIS CLASS. The defect
reproduces inside its own remediation, which is why it needs a gate rather than more care.

THE RULE, founder-set 2026-08-31, and it is about PURPOSE not mechanism:

    "If the field's purpose is considered, at any stage, by a writer, to be read as part of
     the pipeline, it is certainly wired. This also means if the field is to be rendered in
     a more humane form, like a mermaid chart."

So a RENDERER IS A CONSUMER exactly as a checker is. An earlier version of this measurement
scanned only scripts/ and hooks/ and therefore mis-scored `gate`, `started_at`,
`theory_gates_status` and `trigger` as unwired; they are consumed by the render fleet. The
question is never "does Python read it" but "did anyone intend it to be read, and does that
reader exist".

`human` IS A LEGAL ANSWER. A field written for a person to read is wired the moment that is
DECLARED. What this gate forbids is the undeclared case: a field nobody consumes and nobody
ever decided shouldn't be consumed.

WHAT IT CANNOT DO, stated first. It cannot tell intent from coincidence: a field name that
appears in a skill for an unrelated reason scores as consumed. It cannot check the consumer
does anything useful with the value. It is a REACHABILITY check, not a semantics check — the
weaker claim, and the one it can actually support.

RATCHET, not a cleanup sprint. Existing fields are baselined in
harness/field-consumers.yml; only a NEW promise-shaped field with no consumer fails. This is
the shape check_fail_open.py already uses in this repo, and it is the shape the feature-flag
literature converged on: a recurring ratchet, because a one-off audit regrows.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

#: A field whose NAME asserts something the machine could check: a date, a bar, a gate, a
#: state. Deliberately name-based — this runs over schemas, which carry no semantics.
PROMISE = re.compile(
    r"(_at$|_date$|^date$|criterion|threshold|deadline|horizon|expire|overdue|gate|blocking|"
    r"required|kill_|_by$|status|_state$|trigger|cadence|target|floor|ceiling|budget|sla|due)",
    re.IGNORECASE,
)

CONSUMER_KINDS = ("code", "render", "skill", "engine")

#: Recursion ceiling when walking a schema. Deep enough for every shipped schema, finite so a
#: self-referential $ref cannot hang the gate.
_MAX_SCHEMA_DEPTH = 8

#: Shortest token that counts as a shared word when hunting synonyms. Two characters and
#: below ("at", "by", "id") match everything and drown the signal.
_MIN_TOKEN = 2

#: A canvas key that is a FIELD rather than a narrative annotation: lower snake_case, no
#: date or entity id baked in, a sane length. Measured 2026-08-31 on the dogfood canvas:
#: of 84 undeclared promise-shaped keys, 65 were used exactly ONCE and were prose
#: annotations (`horizon_set_2026_08_28`), and 19 recurred and were real fields. Recurrence
#: is what separates the two, and without it this check would demand a consumer for 65
#: sentences and be muted within a day.
_LIVE_FIELD_RE = re.compile(r"^[a-z][a-z0-9_]{2,34}$")

#: Minimum uses before a live canvas key counts as a field at all.
_MIN_USES = 2

#: Where the per-project baseline lives. Canvas content is project-specific, so unlike
#: harness/field-consumers.yml (which ships with the framework and covers schema fields)
#: this one belongs to the consumer's own repo.
LIVE_BASELINE_REL = "harness/canvas-field-consumers.yml"


def _schema_fields(schema_dir: Path) -> dict[str, set[str]]:
    fields: dict[str, set[str]] = {}
    for sf in sorted(schema_dir.rglob("*.schema.json")):
        found: set[str] = set()
        try:
            _walk(json.loads(sf.read_text()), found)
        except (json.JSONDecodeError, OSError):
            continue  # a broken schema is validate_canvas's business, not this gate's
        for name in found:
            fields.setdefault(name, set()).add(sf.stem.replace(".schema", ""))
    return fields


def _walk(node, out: set[str], depth: int = 0) -> None:
    if depth > _MAX_SCHEMA_DEPTH or not isinstance(node, dict):
        return
    for key, val in node.items():
        if key == "properties" and isinstance(val, dict):
            for name, sub in val.items():
                out.add(name)
                _walk(sub, out, depth + 1)
        elif key in ("items", "$defs", "definitions", "dependentSchemas", "then", "else"):
            _walk(val, out, depth + 1)
        elif key in ("allOf", "anyOf", "oneOf") and isinstance(val, list):
            for sub in val:
                _walk(sub, out, depth + 1)
        elif isinstance(val, dict):
            _walk(val, out, depth + 1)


def _corpora(root: Path) -> dict[str, str]:
    def read(paths):
        return "\n".join(p.read_text(errors="ignore") for p in paths if p.is_file())

    skills = list((root / "skills").rglob("*.md"))
    return {
        "code": read([p for d in ("scripts", "hooks") for p in (root / d).rglob("*")
                      if p.suffix in {".py", ".sh"}]),
        "render": read([p for p in skills if "render" in str(p).lower()]),
        "skill": read([p for p in skills if "render" not in str(p).lower()]),
        # THE REGISTRY IS NOT A CONSUMER, and excluding it is load-bearing. On first run this
        # scan reported 38/38 wired the moment field-consumers.yml was written, because that
        # file names every unwired field and lives under harness/. A record that a field has
        # no reader was being counted as reading it — this defect class, inside the instrument
        # built to catch it, on the same day. Caught 2026-08-31 only because the number moved
        # from 5 to 0 with no code change.
        "engine": read([p for d in ("engine", "harness") for p in (root / d).rglob("*")
                        if p.suffix in {".md", ".yml", ".yaml"}
                        and p.name != "field-consumers.yml"]),
    }


def consumers_of(name: str, corpora: dict[str, str]) -> list[str]:
    """Which kinds of consumer mention this field. Quoted in code, word-bounded in prose."""
    hits = []
    if re.search(rf"[\"']{re.escape(name)}[\"']", corpora["code"]):
        hits.append("code")
    hits.extend(kind for kind in ("render", "skill", "engine")
                if re.search(rf"\b{re.escape(name)}\b", corpora[kind]))
    return hits


def scan(root: Path) -> tuple[list[tuple[str, list[str], list[str]]], dict]:
    fields = _schema_fields(root / "schemas")
    corpora = _corpora(root)
    rows = []
    for name, canvases in sorted(fields.items()):
        if not PROMISE.search(name):
            continue
        rows.append((name, sorted(canvases), consumers_of(name, corpora)))
    reg_path = root / "harness" / "field-consumers.yml"
    registry = {}
    if reg_path.exists():
        doc = yaml.safe_load(reg_path.read_text()) or {}
        for entry in doc.get("reviewed") or []:
            if isinstance(entry, dict) and entry.get("field"):
                registry[entry["field"]] = entry
    return rows, registry


def _existing_names(root: Path, canvas_dir: str | None) -> set[str]:
    """Every field name the framework already knows: declared, and actually written."""
    names = set(_schema_fields(root / "schemas"))
    if canvas_dir:
        for path in sorted(Path(canvas_dir).glob("*.yml")):
            try:
                _yaml_keys(yaml.safe_load(path.read_text()), names)
            except (yaml.YAMLError, OSError):
                continue
    return names


def _yaml_keys(node, out: set[str], depth: int = 0) -> None:
    if depth > _MAX_SCHEMA_DEPTH:
        return
    if isinstance(node, dict):
        for key, val in node.items():
            if isinstance(key, str):
                out.add(key)
            _yaml_keys(val, out, depth + 1)
    elif isinstance(node, list):
        for val in node:
            _yaml_keys(val, out, depth + 1)


def _report_similar(root: Path, name: str, canvas_dir: str | None) -> int:
    """Step (b) of the new-field rule, made mechanical rather than aspirational.

    SYNONYM PROLIFERATION IS THE MEASURED FAILURE, not a hypothetical one: `surfaced_by` was
    agent-invented and reached 42 uses alongside the existing provenance / source_class
    mechanism, with nobody reconciling the two. Two names for one idea means each consumer
    knows one of them and is wrong half the time.
    """
    known = _existing_names(root, canvas_dir)
    if name in known:
        print(f"`{name}` ALREADY EXISTS. Use it, or say why a second field is needed.")
        return 0
    close = difflib.get_close_matches(name, sorted(known), n=12, cutoff=0.6)
    tokens = {t for t in re.split(r"[_\-]", name.lower()) if len(t) > _MIN_TOKEN}
    shared = sorted({k for k in known
                     if tokens & {t for t in re.split(r"[_\-]", k.lower()) if len(t) > _MIN_TOKEN}}
                    - set(close))[:12]
    print(f"Existing names close to `{name}` ({len(known)} known):")
    if not close and not shared:
        print("  none — no near-duplicate found. Steps (a), (c) and (d) still apply.")
        return 0
    for match in close:
        print(f"  ~ {match}")
    for match in shared:
        print(f"  · {match}   (shares a word)")
    print("\n  If one of these means what you mean, USE IT. A second name for one idea means\n"
          "  every consumer must know both, and in practice each knows one.")
    return 0


def live_canvas_fields(canvas_dir: Path, root: Path) -> list[tuple[str, int, list[str]]]:
    """Promise-shaped keys the canvas actually contains, that no schema declares.

    THE HOLE THIS CLOSES. `scan()` reads SCHEMAS, so it only sees fields somebody declared.
    Every canvas schema sets `additionalProperties: true`, so a field can be written into the
    canvas and never declared anywhere: measured 2026-08-31, **2210 of 2494 live keys (88%)
    are declared by no schema**. `unlocked_at` was caught in three hours only because it
    happened to go through a schema; `kill_criterion.date` and the 19 fields this mode finds
    did not, and were invisible.

    Returns (name, use_count, consumer_kinds) for keys that are undeclared, field-shaped and
    used more than once — one-off keys are prose, see _LIVE_FIELD_RE.
    """
    declared = set(_schema_fields(root / "schemas"))
    counts: Counter[str] = Counter()
    for path in sorted(canvas_dir.glob("*.yml")):
        try:
            _count_keys(yaml.safe_load(path.read_text()), counts)
        except (yaml.YAMLError, OSError):
            continue
    corpora = _corpora(root)
    rows = []
    for name, uses in sorted(counts.items()):
        if name in declared or uses < _MIN_USES:
            continue
        if not _LIVE_FIELD_RE.match(name) or not PROMISE.search(name):
            continue
        rows.append((name, uses, consumers_of(name, corpora)))
    return rows


def _count_keys(node, counts: Counter, depth: int = 0) -> None:
    if depth > _MAX_SCHEMA_DEPTH + 4:
        return
    if isinstance(node, dict):
        for key, val in node.items():
            if isinstance(key, str):
                counts[key] += 1
            _count_keys(val, counts, depth + 1)
    elif isinstance(node, list):
        for val in node:
            _count_keys(val, counts, depth + 1)


def _run_live(root: Path, canvas_dir: Path, write_baseline: bool, strict: bool) -> int:
    if not canvas_dir.is_dir():
        print(f"Field-wiring (live): NOT A PASS — no canvas dir at {canvas_dir}.")
        return 1
    rows = live_canvas_fields(canvas_dir, root)
    base_path = canvas_dir.parent / LIVE_BASELINE_REL
    if write_baseline:
        base_path.parent.mkdir(parents=True, exist_ok=True)
        base_path.write_text(yaml.safe_dump(
            {"note": "Promise-shaped canvas keys that no schema declares and nothing consumes, "
                     "as of seeding. Present so the rule costs NEW writing rather than a "
                     "retro-fit of everything already written. Each should end up either "
                     "declared and wired, or recorded as human-only.",
             "fields": sorted(n for n, _, kinds in rows if not kinds)},
            sort_keys=False))
        print(f"Field-wiring (live): baseline seeded with "
              f"{len([1 for _, _, k in rows if not k])} field(s) at {base_path}")
        return 0
    baseline = set()
    if base_path.exists():
        doc = yaml.safe_load(base_path.read_text()) or {}
        baseline = set(doc.get("fields") or [])
    unwired = [(n, u) for n, u, kinds in rows if not kinds]
    new = [(n, u) for n, u in unwired if n not in baseline]
    print("Field-wiring scan, LIVE CANVAS (keys no schema declares)")
    print("=" * 60)
    if not rows:
        print("  NOT A PASS — no promise-shaped undeclared key found. Nothing was checked,\n"
              "  which is not the same as everything being wired.")
        return 1
    print(f"  {len(rows)} undeclared promise-shaped field(s) used >{_MIN_USES - 1}x; "
          f"{len(rows) - len(unwired)} have a consumer, {len(unwired)} do not "
          f"({len(baseline)} baselined, {len(new)} NEW)")
    for name, uses in new:
        print(f"    NEW  {name}  ({uses} uses)")
    if not new:
        print("\n  No NEW unconsumed field. One-off keys are excluded as prose: a key used once\n"
              "  is an annotation, not a field. See _LIVE_FIELD_RE.")
        return 0
    print("\n  Each needs the four-step new-field rule applied: is it necessary, does a similar\n"
          "  field already exist (--similar), declare it in the schema, and wire it or record it\n"
          "  as human-only. A field no schema declares is invisible to every other check here.")
    return 1 if strict else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 on a NEW promise-shaped field with no consumer and no ruling")
    ap.add_argument("--similar", metavar="NAME",
                    help="before inventing a field, list existing names close to NAME. Step (b) "
                         "of the four-step new-field rule in the agent operating contract.")
    ap.add_argument("--canvas-dir", default=None,
                    help="with --similar, also search the live canvas; with --live, the canvas "
                         "to scan")
    ap.add_argument("--live", action="store_true",
                    help="scan the LIVE CANVAS for promise-shaped keys no schema declares. "
                         "88%% of canvas keys are undeclared, and the schema scan is blind to "
                         "every one of them.")
    ap.add_argument("--write-baseline", action="store_true",
                    help="with --live: seed the per-project baseline once")
    args = ap.parse_args()
    root = Path(args.root)

    if args.similar:
        return _report_similar(root, args.similar, args.canvas_dir)

    if args.live:
        if not args.canvas_dir:
            print("Field-wiring (live): NOT A PASS — --live needs --canvas-dir.")
            return 1
        return _run_live(root, Path(args.canvas_dir), args.write_baseline, args.strict)

    rows, registry = scan(root)
    if not rows:
        # EMPTY INPUT IS A REFUSAL, NOT A PASS. Enforced by check_empty_input_honesty.py,
        # which failed this gate on its first full run: exit 0 over a tree with no schemas
        # means "I looked at nothing and everything is fine", the one answer never true.
        # A real install always ships schemas, so this fires only on a broken --root.
        print("Field-wiring scan: NOT A PASS — no schema declared a promise-shaped field.")
        print(f"  Nothing was verified. Check --root ({root}) points at the plugin dir.")
        return 1
    unwired = [(n, c) for n, c, k in rows if not k]
    new = [(n, c) for n, c in unwired if n not in registry]
    unruled = [n for n, _ in unwired
               if registry.get(n, {}).get("verdict") in (None, "UNRULED")]

    by_kind = {k: sum(1 for _, _, kinds in rows if kinds and kinds[0] == k)
               for k in CONSUMER_KINDS}
    print("Field-wiring scan (does a promise-shaped field have a consumer?)")
    print("=" * 60)
    print(f"  {len(rows)} promise-shaped field(s); "
          f"{len(rows) - len(unwired)} have a consumer, {len(unwired)} do not")
    print("  consumer kind of first hit: "
          + ", ".join(f"{k}={by_kind[k]}" for k in CONSUMER_KINDS))
    if unruled:
        print(f"\n  {len(unruled)} baselined field(s) still await a founder ruling: "
              + ", ".join(sorted(unruled)))
    if not new:
        print("\n  No NEW unwired field. This is NOT 'every field is used' — it is 'none has\n"
              "  appeared that nobody has ruled on'. A renderer counts as a consumer; so does\n"
              "  a declared human reader. What is forbidden is the undeclared case.")
        return 0
    print(f"\n  {len(new)} NEW promise-shaped field(s) with NO consumer:")
    for name, canvases in new:
        print(f"    {name}  ({', '.join(canvases)})")
    print("\n  Each needs one judgement, per the founder rule of 2026-08-31: if any writer\n"
          "  intends it to be read as part of the pipeline — INCLUDING being rendered into a\n"
          "  humane form such as a mermaid chart — then wire that consumer now, in this\n"
          "  commit. If it is for a person to read, record it as `consumer: human` and say so.\n"
          "  Record judgements in harness/field-consumers.yml under `reviewed:`.")
    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
