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
.claude/schemas/canvas/<basename>.schema.json. Schemas not present are silently
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


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CANVAS_DIR = REPO_ROOT / ".claude" / "canvas"
SCHEMA_DIR = REPO_ROOT / ".claude" / "schemas" / "canvas"
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
    # Register under both the $id and a relative URL so schemas can $ref it
    common_id = common.get("$id", "_common.schema.json")
    return (
        Registry()
        .with_resource(uri=common_id, resource=common_resource)
        .with_resource(uri="_common.schema.json", resource=common_resource)
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


def collect_trace_graph():
    """Walk all canvas files; build trace graph + per-file id sets.

    Returns (graph, all_ids, errors). Errors include per-file ID uniqueness
    violations (corrections.md 2026-05-04 — G-V12 coverage proof in
    test_validate_canvas.py).
    """
    graph = defaultdict(set)
    all_ids = set()
    errors = []

    if not CANVAS_DIR.exists():
        return graph, all_ids, errors

    for canvas_path in sorted(CANVAS_DIR.glob("*.yml")):
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


def main():
    all_errors = []

    if not CANVAS_DIR.exists():
        print("Canvas directory not found:", CANVAS_DIR)
        sys.exit(0)

    if not SCHEMA_DIR.exists():
        print("Schema directory not found:", SCHEMA_DIR)
        print("(no schemas to validate against — silently passing)")
        sys.exit(0)

    registry = build_registry()

    # Validate each canvas against its schema
    for canvas_path in sorted(CANVAS_DIR.glob("*.yml")):
        errors = validate_canvas_against_schema(canvas_path, registry)
        all_errors.extend(errors)

    # Trace edge resolution + cycle detection
    graph, all_ids, collect_errors = collect_trace_graph()
    all_errors.extend(collect_errors)
    all_errors.extend(resolve_trace_references(graph, all_ids))
    all_errors.extend(detect_cycles(graph))

    if all_errors:
        print(f"Canvas validation failed with {len(all_errors)} error(s):")
        for err in all_errors:
            print(f"  - {err}")
        sys.exit(1)

    schemas_present = len(list(SCHEMA_DIR.glob("*.schema.json"))) - 1  # exclude _common
    canvases_present = len(list(CANVAS_DIR.glob("*.yml")))
    print(
        f"Canvas validation: PASS ({canvases_present} canvas files, "
        f"{schemas_present} schemas, {len(all_ids)} traceable IDs)",
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
