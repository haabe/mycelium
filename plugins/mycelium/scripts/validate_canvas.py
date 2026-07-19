#!/usr/bin/env python3
"""
Mycelium canvas schema validator.

╔════════════════════════════════════════════════════════════════════╗
║ THIS SCRIPT IS CI-ONLY. IT IS NOT A RUNTIME HOOK.                  ║
║                                                                    ║
║ It requires PyYAML, jsonschema, and referencing — none of which    ║
║ are stdlib. Runtime hooks (.claude/hooks/*.sh) MUST NOT call this  ║
║ script. They use Python stdlib only.                               ║
║                                                                    ║
║ This script runs in:                                               ║
║   - .github/workflows/validate.yml (after pip install)             ║
║   - Local development (after `pip install -r requirements-ci.txt`) ║
║                                                                    ║
║ See .claude/state/README.md for the dependency philosophy:         ║
║   Runtime hooks: Python stdlib only, zero setup                    ║
║   CI validation: pip install full dependencies                     ║
╚════════════════════════════════════════════════════════════════════╝

Validates each .claude/canvas/*.yml file against its corresponding schema in
$CLAUDE_PLUGIN_ROOT/schemas/canvas/<basename>.schema.json (plugin form; falls back
to .claude/schemas/canvas/ in legacy form). Schemas not present are silently
skipped (canvas can have weaker schemas in early development; tighten over time).

Resolves trace.upstream / trace.downstream target_id references across all
canvas files. Detects DAG cycles in the trace graph using Kahn's algorithm.

Run from CI or via local install:
    pip install -r requirements-ci.txt
    python3 .claude/scripts/validate_canvas.py

Exit codes:
    0 = all canvases pass schema + ID resolution + cycle check
    1 = at least one validation failure (full report on stdout)
    2 = missing CI dependencies (PyYAML, jsonschema, or referencing)
"""

import json
import os
import sys
from collections import defaultdict, deque
from pathlib import Path

# Try imports — fail gracefully with clear message
try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install PyYAML")
    sys.exit(2)

try:
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012
except ImportError:
    print("ERROR: jsonschema not installed. Run: pip install jsonschema referencing")
    sys.exit(2)


# Path resolution — supports plugin form AND legacy form.
#
# Plugin form (post-v0.20.0): script is at $CLAUDE_PLUGIN_ROOT/scripts/X.py.
#   - Schema lives at $CLAUDE_PLUGIN_ROOT/schemas/canvas/.
#   - Canvas is project state at $CLAUDE_PROJECT_DIR/.claude/canvas/.
#
# Legacy form (pre-v0.20.0): script is at <repo>/.claude/scripts/X.py.
#   - Schema and canvas both under <repo>/.claude/.
#
# Env vars take precedence; fall back to relative-to-script auto-detect.

def _resolve_paths():
    """Return (CANVAS_DIR, SCHEMA_DIR) honoring env vars + auto-detect."""
    here = Path(__file__).resolve()
    plugin_root_candidate = here.parent.parent  # plugins/mycelium/
    legacy_repo_candidate = here.parent.parent.parent  # repo root in legacy

    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if plugin_root:
        schema_dir = Path(plugin_root) / "schemas" / "canvas"
    elif (plugin_root_candidate / "schemas" / "canvas").exists():
        schema_dir = plugin_root_candidate / "schemas" / "canvas"
    else:
        schema_dir = legacy_repo_candidate / ".claude" / "schemas" / "canvas"

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        canvas_dir = Path(project_dir) / ".claude" / "canvas"
    else:
        cwd_canvas = Path.cwd() / ".claude" / "canvas"
        legacy_canvas = legacy_repo_candidate / ".claude" / "canvas"
        canvas_dir = cwd_canvas if cwd_canvas.exists() else legacy_canvas

    return canvas_dir, schema_dir


CANVAS_DIR, SCHEMA_DIR = _resolve_paths()
COMMON_SCHEMA = SCHEMA_DIR / "_common.schema.json"


def load_yaml(path: Path):
    """Load a YAML file. Returns the parsed object or raises."""
    with open(path) as f:
        return yaml.safe_load(f)


def load_schema(path: Path):
    """Load a JSON Schema file."""
    with open(path) as f:
        return json.load(f)


def build_registry():
    """Build a referencing.Registry that resolves $ref to _common.schema.json."""
    if not COMMON_SCHEMA.exists():
        return Registry()

    common = load_schema(COMMON_SCHEMA)
    common_resource = Resource.from_contents(common, default_specification=DRAFT202012)
    # Register under the $id, a relative URL, AND the diamonds-relative URI:
    # schemas/diamonds/*.schema.json carry $id .../schemas/diamonds/<name>, so
    # their relative "_common.schema.json" refs resolve against that base
    # (RFC 3986) — without the third registration those refs are Unresolvable.
    common_id = common.get("$id", "_common.schema.json")
    diamonds_relative = common_id.replace("/canvas/", "/diamonds/")
    return (
        Registry()
        .with_resource(uri=common_id, resource=common_resource)
        .with_resource(uri="_common.schema.json", resource=common_resource)
        .with_resource(uri=diamonds_relative, resource=common_resource)
    )


def validate_canvas_against_schema(canvas_path: Path, registry: Registry):
    """
    Validate one canvas file against its schema (if present).
    Returns list of error strings (empty if pass).
    """
    schema_path = SCHEMA_DIR / f"{canvas_path.stem}.schema.json"

    if not schema_path.exists():
        # No schema for this canvas yet — silently pass (early-development tolerance)
        return []

    try:
        canvas_data = load_yaml(canvas_path)
    except (yaml.YAMLError, OSError) as exc:
        return [f"YAML parse error in {canvas_path.name}: {exc}"]

    if canvas_data is None:
        # Empty file — allowed
        return []

    try:
        schema = load_schema(schema_path)
    except (json.JSONDecodeError, OSError) as exc:
        return [f"Schema parse error in {schema_path.name}: {exc}"]

    validator = Draft202012Validator(schema, registry=registry)
    errors = []
    for error in sorted(validator.iter_errors(canvas_data), key=lambda e: e.path):
        path = ".".join(str(p) for p in error.absolute_path) or "(root)"
        errors.append(f"{canvas_path.name} :: {path} :: {error.message}")

    return errors


def _walk_canvas(node, path_prefix, ctx):  # noqa: C901
    """Recursive descent over a canvas tree; collects ids, trace edges, file_ids.

    `ctx` is a dict with keys: stem, graph, all_ids, file_ids. Bundling state
    avoids loop-variable closure issues (B023) and keeps the signature clean.
    Complexity is intrinsic — node shapes are dict/list and trace blocks have
    upstream/target_id structure that has to be unpacked.
    """
    if isinstance(node, dict):
        node_id = node.get("id")
        if node_id and isinstance(node_id, str):
            ctx["all_ids"].add(f"{ctx['stem']}#{node_id}")
            ctx["file_ids"].append(node_id)

        trace_block = node.get("trace")
        if isinstance(trace_block, dict):
            upstream = trace_block.get("upstream") or []
            if isinstance(upstream, list):
                for edge in upstream:
                    if isinstance(edge, dict) and "target_id" in edge:
                        target = edge["target_id"]
                        source = node.get("id") or path_prefix
                        ctx["graph"][source].add(target)

        for k, v in node.items():
            if k != "trace":
                child_prefix = f"{path_prefix}.{k}" if path_prefix else k
                _walk_canvas(v, child_prefix, ctx)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            _walk_canvas(item, f"{path_prefix}[{i}]", ctx)


def collect_trace_graph(canvas_dir: Path | None = None):
    """Walk all canvas files; build trace graph + per-file id sets.

    Returns (graph, all_ids, errors). Errors include per-file ID uniqueness
    violations (corrections.md 2026-05-04 — G-V12 coverage proof in
    test_validate_canvas.py).

    Accepts optional canvas_dir (defaults to module-level CANVAS_DIR for
    backward compat with existing pytest fixtures).
    """
    if canvas_dir is None:
        canvas_dir = CANVAS_DIR

    graph = defaultdict(set)
    all_ids = set()
    errors = []

    if not canvas_dir.exists():
        return graph, all_ids, errors

    for canvas_path in sorted(canvas_dir.glob("*.yml")):
        try:
            data = load_yaml(canvas_path)
        except (yaml.YAMLError, OSError) as exc:
            # Best-effort: schema validator already reports bad YAML separately.
            print(
                f"  warn: skipping {canvas_path.name} during trace walk: {exc}",
                file=sys.stderr,
            )
            continue
        if data is None or not isinstance(data, dict):
            continue

        stem = canvas_path.stem
        all_ids.add(stem)

        # Per-file ID list — set would silently dedupe and miss collisions.
        file_ids: list[str] = []
        ctx = {"stem": stem, "graph": graph, "all_ids": all_ids, "file_ids": file_ids}
        _walk_canvas(data, stem, ctx)

        # Per-file ID uniqueness check.
        seen: dict[str, int] = {}
        for nid in file_ids:
            seen[nid] = seen.get(nid, 0) + 1
        duplicates = sorted(nid for nid, count in seen.items() if count > 1)
        errors.extend(
            f"{canvas_path.name} :: duplicate id '{dup}' "
            f"(appears {seen[dup]}x within file — ids must be unique per canvas)"
            for dup in duplicates
        )

    return graph, all_ids, errors


def resolve_trace_references(graph, all_ids):
    """Verify every target_id in the graph resolves to a known id.

    Target taxonomy (recognized prefixes for cross-canvas references):
        canvas_basename                          e.g. "opportunities"
        canvas_basename#entry_id                 e.g. "opportunities#opp-001"
        {decision-log,external,memory}#anything  external — assume valid

    Returns list of error strings.
    """
    external_namespaces = {"decision-log", "external", "memory"}
    errors = []
    for source, targets in graph.items():
        for target in targets:
            if "#" in target:
                base, _ = target.split("#", 1)
                if base in external_namespaces:
                    continue
                if target not in all_ids:
                    errors.append(
                        f"Trace edge from '{source}' references '{target}' "
                        f"— does not resolve to any known canvas entry",
                    )
            elif target not in all_ids and target not in external_namespaces:
                errors.append(
                    f"Trace edge from '{source}' references '{target}' "
                    f"— does not resolve to any canvas file",
                )
    return errors


def detect_cycles(graph):
    """
    Detect cycles in the trace graph using Kahn's algorithm.
    Returns list of error strings (empty if DAG).
    """
    in_degree = defaultdict(int)
    nodes = set(graph.keys())
    for targets in graph.values():
        for target in targets:
            in_degree[target] += 1
            nodes.add(target)

    queue = deque([n for n in nodes if in_degree[n] == 0])
    visited = 0

    while queue:
        node = queue.popleft()
        visited += 1
        for target in graph.get(node, []):
            in_degree[target] -= 1
            if in_degree[target] == 0:
                queue.append(target)

    if visited < len(nodes):
        # Find which nodes are in the cycle
        in_cycle = [n for n in nodes if in_degree[n] > 0]
        cycle_sample = ", ".join(sorted(in_cycle)[:10])
        return [f"Trace graph contains cycle(s) involving: {cycle_sample}"]
    return []


def validate_all_yaml_parses(canvas_dir: Path) -> list[str]:
    """Fail-loud YAML parse check on every canvas file.

    Returns list of error strings. Empty if all files parse cleanly.

    Closes cluster instance 14 of documented-rule-diverges-from-enforcement
    (validator silently skipped YAML parse failures): files without schemas
    previously passed silently at schema layer (line 135-137 returns []
    when no schema), and the trace walk warned-then-continued. Combined
    effect: broken YAML on a schemaless file ("Canvas validation: PASS").
    Witnessed 2026-05-23 on roadmap north-star.yml. This check runs first
    in main() and surfaces ALL parse errors before any other validation.
    """
    # Per-file isolation is required, not optional. Each canvas file needs
    # INDEPENDENT error handling so one parse failure doesn't crash the loop
    # AND the error must be attributed to the specific file. Moving the
    # try/except outside the loop would lose both properties. Performance
    # overhead is acceptable for the ~25-file canvas-dir scale.
    errors = []
    for canvas_path in sorted(canvas_dir.glob("*.yml")):
        try:
            with open(canvas_path) as f:
                yaml.safe_load(f)
        except yaml.YAMLError as exc:  # noqa: PERF203
            # Strip trailing newlines from yaml error messages for cleaner output
            errors.append(f"YAML parse error in {canvas_path.name}: {str(exc).strip()}")
        except OSError as exc:
            errors.append(f"Cannot read {canvas_path.name}: {exc}")
    return errors


def validate_diamonds(canvas_dir: Path, registry: Registry) -> list[str]:
    """Fail-loud parse + schema check for the diamonds state directory.

    Coverage gap closed 2026-06-12: the dogfood repo's diamonds/active.yml sat
    committed-unparseable for >=3 days (unescaped interior double-quotes in a
    notes: scalar) with zero detection — diamonds/ was outside this script's
    canvas glob, active.yml had no schema, and every hook reading it degrades
    to defaults on parse failure (roadmap corrections.md 2026-06-12). This
    function gives the framework's most-read state file the same fail-loud
    parse guarantee as canvas files, plus schema validation for active.yml
    (schemas/diamonds/active.schema.json — pins scale/phase enums, confidence
    range, and the v0.43.0 definition_of_done shape).
    """
    diamonds_dir = canvas_dir.parent / "diamonds"
    if not diamonds_dir.is_dir():
        return []

    errors = []
    for path in sorted(diamonds_dir.glob("*.yml")):
        try:
            with open(path) as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            msg = str(exc).strip()
            errors.append(f"YAML parse error in diamonds/{path.name}: {msg}")
            continue
        except OSError as exc:
            errors.append(f"Cannot read diamonds/{path.name}: {exc}")
            continue

        schema_path = SCHEMA_DIR.parent / "diamonds" / f"{path.stem}.schema.json"
        if data is None or not schema_path.exists():
            continue
        try:
            schema = load_schema(schema_path)
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"Schema parse error in diamonds/{schema_path.name}: {exc}")
            continue
        validator = Draft202012Validator(schema, registry=registry)
        for error in sorted(validator.iter_errors(data), key=lambda e: e.path):
            epath = ".".join(str(p) for p in error.absolute_path) or "(root)"
            errors.append(f"diamonds/{path.name} :: {epath} :: {error.message}")
    return errors


def enum_consistency_errors(canvas_dir: Path) -> list[str]:
    """evidence_type / source_class values must be in their enum EVERYWHERE.

    The per-schema $ref only covers *declared* properties — provenance blocks
    (canvas) and the diamond record (evidence_type $ref added v0.57.3). Undeclared
    entry-level occurrences — a bare `evidence_type:` on a canvas entry outside a
    provenance block — slip past `additionalProperties`. This walk closes that
    surface across canvas + diamonds, present and future files, and flags the
    disjoint-set error class (a source_class value in an evidence_type field, and
    vice versa) with a targeted hint.

    Surfaced 2026-07-19: a source_class value (`internal_stakeholder`) in a
    diamond's `evidence_type` survived ~3 weeks of PASSes; the sibling canvas
    surface had the same latent gap. Enums are read from _common (single source).
    """
    if not COMMON_SCHEMA.exists():
        return []
    common = load_schema(COMMON_SCHEMA)
    ev_enum = set(common["$defs"]["evidence_type"]["enum"])
    sc_enum = set(common["$defs"]["source_class"]["enum"])

    files = sorted(canvas_dir.glob("*.yml"))
    diamonds_dir = canvas_dir.parent / "diamonds"
    if diamonds_dir.is_dir():
        files += sorted(diamonds_dir.glob("*.yml"))

    errors: list[str] = []

    def walk(node, where, rel):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "evidence_type" and isinstance(v, str) and v not in ev_enum:
                    hint = (" — that is a source_class value; did you mean source_class?"
                            if v in sc_enum else "")
                    errors.append(
                        f"{rel} :: {where}.evidence_type :: '{v}' is not in the "
                        f"evidence_type enum {sorted(ev_enum)}{hint}")
                elif k == "source_class" and isinstance(v, str) and v not in sc_enum:
                    hint = (" — that is an evidence_type value; did you mean evidence_type?"
                            if v in ev_enum else "")
                    errors.append(
                        f"{rel} :: {where}.source_class :: '{v}' is not in the "
                        f"source_class enum {sorted(sc_enum)}{hint}")
                walk(v, f"{where}.{k}" if where else k, rel)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                walk(item, f"{where}[{i}]", rel)

    for path in files:
        try:
            data = load_yaml(path)
        except Exception:
            # YAML parse errors are reported by validate_all_yaml_parses /
            # validate_diamonds; don't double-report here.
            continue
        rel = path.name if path.parent.name == "canvas" else f"diamonds/{path.name}"
        walk(data, "", rel)

    return errors


def schemaless_canvas_warnings(canvas_dir: Path) -> list[str]:
    """Name every canvas file that has no schema — visibility, not failure.

    Previously schema-less files passed silently (early-development
    tolerance), which read as 'validated' when nothing was checked beyond
    YAML parse. The tolerance stays (warnings don't fail the run); the
    silence goes (gap analysis 2026-06-12, finding: 'unvalidated canvas
    files silently pass').
    """
    return [
        f"{canvas_path.name}: no schema — parse-checked only"
        for canvas_path in sorted(canvas_dir.glob("*.yml"))
        if not (SCHEMA_DIR / f"{canvas_path.stem}.schema.json").exists()
    ]


def main():
    # CLI: optional positional argv overrides canvas directory.
    # Previously the script defaulted to cwd + ignored positional argv —
    # confusing when invoked with a directory path that got silently dropped
    # (witnessed 2026-05-23: session-long "PASS" reports were against
    # framework canvas while user thought they were against roadmap canvas).
    canvas_dir = CANVAS_DIR
    if len(sys.argv) > 1:
        candidate = Path(sys.argv[1]).resolve()
        if not candidate.exists():
            print(f"Canvas directory not found: {candidate}", file=sys.stderr)
            sys.exit(2)
        canvas_dir = candidate

    all_errors = []

    if not canvas_dir.exists():
        print("Canvas directory not found:", canvas_dir)
        sys.exit(0)

    if not SCHEMA_DIR.exists():
        print("Schema directory not found:", SCHEMA_DIR)
        print("(no schemas to validate against — silently passing)")
        sys.exit(0)

    # Fail-loud YAML parse check (instance 14 fix, 2026-05-23). Must run
    # before schema validation + trace walk so YAML errors surface even on
    # schemaless files.
    all_errors.extend(validate_all_yaml_parses(canvas_dir))

    registry = build_registry()

    # Validate each canvas against its schema
    for canvas_path in sorted(canvas_dir.glob("*.yml")):
        errors = validate_canvas_against_schema(canvas_path, registry)
        all_errors.extend(errors)

    # Diamonds state dir: fail-loud parse + active.yml schema (2026-06-12)
    all_errors.extend(validate_diamonds(canvas_dir, registry))

    # Enum-consistency walk (2026-07-19): evidence_type/source_class values must
    # be in their enum EVERYWHERE they appear, including undeclared entry-level
    # occurrences that additionalProperties waves past per-schema $refs.
    all_errors.extend(enum_consistency_errors(canvas_dir))

    # Trace edge resolution + cycle detection
    graph, all_ids, collect_errors = collect_trace_graph(canvas_dir)
    all_errors.extend(collect_errors)
    all_errors.extend(resolve_trace_references(graph, all_ids))
    all_errors.extend(detect_cycles(graph))

    if all_errors:
        print(f"Canvas validation failed with {len(all_errors)} error(s):")
        for err in all_errors:
            print(f"  - {err}")
        sys.exit(1)

    # Schema-less files: warn (visible), never fail (early-development tolerance)
    warnings = schemaless_canvas_warnings(canvas_dir)
    for w in warnings:
        print(f"  WARN (no schema): {w}")

    schemas_present = len(list(SCHEMA_DIR.glob("*.schema.json"))) - 1  # exclude _common
    canvases_present = len(list(canvas_dir.glob("*.yml")))
    print(
        f"Canvas validation: PASS ({canvases_present} canvas files, "
        f"{schemas_present} schemas, {len(warnings)} schema-less, "
        f"{len(all_ids)} traceable IDs)",
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
