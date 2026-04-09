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
    import jsonschema
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
    registry = Registry().with_resource(uri=common.get("$id", "_common.schema.json"), resource=common_resource)
    registry = registry.with_resource(uri="_common.schema.json", resource=common_resource)
    return registry


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
    except Exception as exc:
        return [f"YAML parse error in {canvas_path.name}: {exc}"]

    if canvas_data is None:
        # Empty file — allowed
        return []

    try:
        schema = load_schema(schema_path)
    except Exception as exc:
        return [f"Schema parse error in {schema_path.name}: {exc}"]

    validator = Draft202012Validator(schema, registry=registry)
    errors = []
    for error in sorted(validator.iter_errors(canvas_data), key=lambda e: e.path):
        path = ".".join(str(p) for p in error.absolute_path) or "(root)"
        errors.append(f"{canvas_path.name} :: {path} :: {error.message}")

    return errors


def collect_trace_graph():
    """
    Walk all canvas files, extract trace.upstream / trace.downstream entries,
    build a graph of (source_id -> target_ids). Returns (graph, all_ids, errors).
    """
    graph = defaultdict(set)
    all_ids = set()
    errors = []

    if not CANVAS_DIR.exists():
        return graph, all_ids, errors

    for canvas_path in sorted(CANVAS_DIR.glob("*.yml")):
        try:
            data = load_yaml(canvas_path)
        except Exception:
            continue
        if data is None or not isinstance(data, dict):
            continue

        canvas_id = canvas_path.stem
        all_ids.add(canvas_id)

        # Walk recursively looking for trace blocks
        def walk(node, path_prefix):
            if isinstance(node, dict):
                # Check for an id field that we can register
                node_id = node.get("id")
                if node_id and isinstance(node_id, str):
                    qualified = f"{canvas_path.stem}#{node_id}"
                    all_ids.add(qualified)

                # Check for a trace block
                trace_block = node.get("trace")
                if isinstance(trace_block, dict):
                    upstream = trace_block.get("upstream") or []
                    if isinstance(upstream, list):
                        for edge in upstream:
                            if isinstance(edge, dict) and "target_id" in edge:
                                target = edge["target_id"]
                                source = node.get("id") or path_prefix
                                graph[source].add(target)

                for k, v in node.items():
                    if k != "trace":
                        walk(v, f"{path_prefix}.{k}" if path_prefix else k)
            elif isinstance(node, list):
                for i, item in enumerate(node):
                    walk(item, f"{path_prefix}[{i}]")

        walk(data, canvas_path.stem)

    return graph, all_ids, errors


def resolve_trace_references(graph, all_ids):
    """
    Verify every target_id in the graph resolves to a known id.
    Returns list of error strings.
    """
    errors = []
    for source, targets in graph.items():
        for target in targets:
            # Targets can be:
            # - canvas_basename (e.g. "opportunities")
            # - canvas_basename#entry_id (e.g. "opportunities#opp-001")
            # - external (e.g. "decision-log#2026-04-09-pivot")
            # We can only validate the first two types here.
            if "#" in target:
                base, _ = target.split("#", 1)
                if base in {"decision-log", "external", "memory"}:
                    continue  # External reference — assume valid
                if target not in all_ids:
                    errors.append(
                        f"Trace edge from '{source}' references '{target}' which does not resolve to any known canvas entry"
                    )
            else:
                if target not in all_ids and target not in {"decision-log", "external", "memory"}:
                    errors.append(
                        f"Trace edge from '{source}' references '{target}' which does not resolve to any canvas file"
                    )
    return errors


def detect_cycles(graph):
    """
    Detect cycles in the trace graph using Kahn's algorithm.
    Returns list of error strings (empty if DAG).
    """
    in_degree = defaultdict(int)
    nodes = set(graph.keys())
    for source, targets in graph.items():
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
        return [f"Trace graph contains cycle(s) involving: {', '.join(sorted(in_cycle)[:10])}"]
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
    print(f"Canvas validation: PASS ({canvases_present} canvas files, {schemas_present} schemas, {len(all_ids)} traceable IDs)")
    sys.exit(0)


if __name__ == "__main__":
    main()
