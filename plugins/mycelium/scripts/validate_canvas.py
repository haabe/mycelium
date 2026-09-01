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

import importlib.util
import json
import os
import re
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


def _collect_derived_from_edges(node: dict, path_prefix: str, ctx: dict) -> None:
    """Treat `derived_from` as a trace edge. Prose values are skipped on purpose.

    `derived_from` is also written as a sentence — tcr-006 carries "principle 3 + observed
    dogfood requirement (not yet in invariants ...)" — and turning that into a dangling
    reference error would train people to stop writing the field at all.
    """
    derived = node.get("derived_from")
    if derived is None:
        return
    source = node.get("id") or path_prefix
    candidates = derived if isinstance(derived, list) else [derived]
    for candidate in candidates:
        if isinstance(candidate, str) and ID_PREFIX_RE.match(candidate.strip()):
            ctx["graph"][source].add(candidate.strip())


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

        # `derived_from` IS A TRACE EDGE, and wiring the used name beats migrating to the
        # unused one. Measured 2026-08-31 on the dogfood canvas: `trace:` blocks appear ZERO
        # times across every canvas file, while `derived_from` appears 12 times — so the
        # canonical shape has never once been written, and the dangling-reference machinery
        # below has never had an edge to check. Agents reached for `derived_from` naturally;
        # nobody reached for `trace`. Treating it as an alias makes 12 real links checkable
        # today rather than after a migration to a shape with no adoption.
        #
        # ONLY ID-SHAPED VALUES BECOME EDGES. `derived_from` is also written as prose — e.g.
        # tcr-006 carries "principle 3 + observed dogfood requirement (not yet in invariants
        # ...)" — and turning a sentence into a dangling-reference error would train people
        # to stop writing the field. Prose is skipped, silently and on purpose.
        _collect_derived_from_edges(node, path_prefix, ctx)

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
                # A BARE ENTRY ID RESOLVES IF EXACTLY ONE CANVAS DEFINES IT. Added 2026-08-31
                # with the `derived_from` alias: those edges are written as bare ids
                # ("ai-002"), because the author knows the id and not which file holds it.
                # Requiring `purpose#ai-002` would have failed 12 real, correct links and
                # taught people to stop writing the field. AMBIGUITY IS STILL AN ERROR: if two
                # canvases define the same id the reference genuinely does not identify one,
                # and the message says which files collided.
                holders = sorted(k.split("#", 1)[0] for k in all_ids
                                 if "#" in k and k.split("#", 1)[1] == target)
                if len(holders) == 1:
                    continue
                if len(holders) > 1:
                    errors.append(
                        f"Trace edge from '{source}' references '{target}' — AMBIGUOUS, "
                        f"defined in {', '.join(holders)}. Qualify it as <canvas>#{target}.",
                    )
                    continue
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


def _duplicate_mapping_keys(text: str) -> list[str]:
    """Report every mapping that holds the same scalar key twice.

    `yaml.safe_load` CANNOT see this. On a duplicate key it keeps the last
    value and discards the earlier one, so the data is already gone by the
    time any schema or trace check runs — the file parses, it just no longer
    says what it said. Composing the node stream is the only layer where the
    duplicate is still visible.

    There is no benign case in a canvas file: the second key always destroys
    the first, so a duplicate is a silent deletion by definition.

    Two real instances, both found 2026-08-18 in the dogfood repo, both of
    which had passed validation, pre-push and CI: an appended touch landed
    between a list entry's `- date:` line and its own body, duplicating two
    keys and emptying both entries; and an older duplicate `tested:` made a
    SCORED assumption test read as `null` — never-run — to every instrument
    that consumed it.
    """
    dups = []

    def walk(node):
        if isinstance(node, yaml.MappingNode):
            seen = set()
            for key_node, value_node in node.value:
                if isinstance(key_node, yaml.ScalarNode):
                    if key_node.value in seen:
                        line_no = key_node.start_mark.line + 1
                        dups.append(f"line {line_no}: duplicate key '{key_node.value}'")
                    seen.add(key_node.value)
                walk(value_node)
        elif isinstance(node, yaml.SequenceNode):
            for child in node.value:
                walk(child)

    for doc in yaml.compose_all(text):
        if doc is not None:
            walk(doc)
    return dups


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
            text = canvas_path.read_text()
            yaml.safe_load(text)
            # Duplicate keys are a SEPARATE failure from a parse failure: the
            # file above parsed fine. Checked here rather than in a new script
            # so every consumer gets it from the validator they already run.
            errors.extend(
                f"Silent data loss in {canvas_path.name}: {dup} "
                f"(the second value destroys the first)"
                for dup in _duplicate_mapping_keys(text)
            )
        except yaml.YAMLError as exc:
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


def _ost_declared_roots(data: dict) -> tuple[list[str] | None, list[str]]:
    """Resolve the declared roots. Returns (root_ids, errors).

    root_ids is None for a single-root file, where `rolls_up_to` has nothing to
    resolve against. Split out of `ost_root_errors` to keep both halves under the
    repo's complexity ceiling: a check that polices canvas quality should meet the
    code policy rather than raise it for itself (same call as v0.91.0's scan split).
    """
    errors = []
    singular = data.get("desired_outcome")
    roots = data.get("desired_outcomes")

    if singular is not None and roots is not None:
        errors.append(
            "opportunities.yml :: declares BOTH desired_outcome and desired_outcomes "
            "-- pick one. Two competing declarations of the tree root leave every "
            "consumer to guess which wins."
        )

    if roots is None or not isinstance(roots, list):
        return None, errors  # shape of a malformed list is the schema's job

    ids: list[str] = []
    for i, root in enumerate(roots):
        if not isinstance(root, dict):
            continue
        rid = root.get("id")
        if not rid:
            continue
        if rid in ids:
            errors.append(
                f"opportunities.yml :: desired_outcomes.{i} :: duplicate root id "
                f"'{rid}' -- rolls_up_to could not resolve unambiguously."
            )
        else:
            ids.append(rid)
    return ids, errors


def _ost_opportunity_root_errors(data: dict, ids: list[str] | None) -> list[str]:
    """Check each opportunity names a root that exists."""
    errors = []
    for i, opp in enumerate(data.get("opportunities") or []):
        if not isinstance(opp, dict):
            continue
        label = opp.get("name", "?")
        target = opp.get("rolls_up_to")

        if ids is None:
            if target:
                errors.append(
                    f"opportunities.yml :: opportunities.{i} ({label}) sets "
                    f"rolls_up_to='{target}' but the file declares no "
                    f"desired_outcomes -- the reference points at nothing."
                )
            continue

        if not target:
            errors.append(
                f"opportunities.yml :: opportunities.{i} ({label}) has no "
                f"rolls_up_to, and the file declares {len(ids)} roots "
                f"({', '.join(ids)}). An untagged opportunity in a multi-root "
                f"tree has no defined parent."
            )
        elif target not in ids:
            errors.append(
                f"opportunities.yml :: opportunities.{i} ({label}) rolls_up_to "
                f"'{target}', which is not a declared root. Declared: "
                f"{', '.join(ids) or '(none)'}."
            )
    return errors


def ost_root_errors(canvas_dir: Path) -> list[str]:
    """Every opportunity in a multi-root OST must name the root it serves.

    WHY THIS EXISTS. An OST rooted on a metric the project does not steer by
    will faithfully optimise the wrong thing: the tree stays busy while the
    stuck thing stays stuck. The dogfood project ran 29 open opportunities under
    a single root declaring `north_star_input_ref: off_north_star`, whose own
    note said user-surfaced opportunities belong in a separate tree — while five
    such opportunities sat in it, carrying real cohort-tester evidence.

    A SECOND FILE WAS THE OBVIOUS FIX AND IT IS WRONG TWICE. The ID references
    pointing into the canvas break (286 of them in the dogfood repo alone), and
    the new file is read by no script, gate or render — the built-not-wired
    defect this framework audits others for. So the split is logical: roots are
    declared together in `desired_outcomes`, and opportunities name theirs.

    Untagged opportunities in a multi-root file are an ERROR rather than a
    default-to-first, because defaulting is exactly how an opportunity ends up
    under a root nobody chose for it — the original problem, one layer down.
    """
    path = canvas_dir / "opportunities.yml"
    if not path.is_file():
        return []
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except (yaml.YAMLError, OSError):
        return []  # parse failures are reported by validate_all_yaml_parses
    if not isinstance(data, dict):
        return []

    ids, errors = _ost_declared_roots(data)
    return errors + _ost_opportunity_root_errors(data, ids)


def enum_consistency_errors(canvas_dir: Path) -> list[str]:  # noqa: C901
    # C901 (12 > 10) accepted, not deferred. This is ONE concern — the
    # evidence_type/source_class swap detector — whose branch count comes from
    # the polymorphic-field walk it must perform, not from doing several things.
    # It is also the most delicately-scoped function in the file: v0.57.4 shipped
    # it over-reaching (21 false positives on a real canvas) and v0.57.5 narrowed
    # it to a disjoint-set check. Splitting it for a complexity metric would risk
    # re-opening that correction chain for no behavioural gain. Revisit only if a
    # genuine second concern is added, which is the point at which the split is
    # real rather than cosmetic.
    """The evidence_type <-> source_class SWAP detector (disjoint-set check).

    evidence_type is POLYMORPHIC by design (canvas-guidance.yml): the Gilad
    ladder in diamonds + confidence-provenance, gathering-method (interview|
    survey|analytics|...) in `_meta` blocks, signal-type (market_signal|...) in
    market provenance, plus intentional extensions (llm_positioning_mirror,
    dogfood_result, stated-intent). So it is NOT enum-locked globally — doing so
    was the v0.57.4 over-fire (false positives on legitimate polymorphic values
    in real dogfood canvases). What IS always an error is the SWAP: the
    source_class value set is disjoint from every legitimate evidence_type
    vocabulary, so a source_class value in an evidence_type field (or a Gilad
    evidence_type value in a source_class field) is a category error regardless
    of context. Diamonds additionally carry the strict Gilad enum via schema
    $ref (v0.57.3, active.schema.json).

    Surfaced 2026-07-19 (i-productified + roadmap dogfood). Enums read from
    _common (single source).
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
                if k == "evidence_type" and isinstance(v, str) and v in sc_enum:
                    errors.append(
                        f"{rel} :: {where}.evidence_type :: '{v}' is a source_class "
                        f"value in an evidence_type field — did you mean source_class? "
                        f"(evidence_type is polymorphic, but source_class values are "
                        f"never valid there)")
                elif k == "source_class" and isinstance(v, str) and v in ev_enum:
                    errors.append(
                        f"{rel} :: {where}.source_class :: '{v}' is a Gilad "
                        f"evidence_type value in a source_class field — did you mean "
                        f"evidence_type?")
                walk(v, f"{where}.{k}" if where else k, rel)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                walk(item, f"{where}[{i}]", rel)

    for path in files:
        try:
            data = load_yaml(path)
        except (yaml.YAMLError, OSError):
            # Narrowed from `except Exception` (BLE001/S112). YAML parse errors
            # are reported by validate_all_yaml_parses / validate_diamonds;
            # don't double-report here. Naming the two reachable classes means a
            # genuine bug in this walk surfaces instead of being swallowed.
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


def canvas_population_state(canvas_dir: Path) -> tuple[str, list[Path], list[Path]]:
    """Classify what a canvas directory actually holds, before validating anything.

    Extracted from main() so the three empty-looking states stay distinguishable
    and separately testable. They mean opposite things and used to share an exit
    code (code review 2026-08-03):

      "fresh"     — no .yml and nothing authored. A `/mycelium:setup` project
                    that has not written its canvas yet. Legitimate: N/A, exit 0,
                    because the shipped pre-push hook gates on the DIRECTORY
                    existing and any non-zero would block the first push.
      "broken"    — no .yml but the directory DOES hold authored files. A rename
                    to `.yaml`, or a layout change that moved the canvas. Not an
                    early project: the glob stopped matching and every validation
                    downstream would report N/A over a canvas nobody checked.
      "populated" — at least one .yml to validate.

    `.gitkeep` and other dotfiles do not count as authored content; treating them
    as content would fail exactly the fresh-project push the N/A state protects.
    """
    canvas_yml = sorted(canvas_dir.glob("*.yml"))
    other_files = [
        f for f in sorted(canvas_dir.iterdir())
        if f.is_file() and not f.name.startswith(".") and f.suffix != ".yml"
    ]
    if canvas_yml:
        return "populated", canvas_yml, other_files
    return ("broken" if other_files else "fresh"), canvas_yml, other_files


def triage_canvas_or_exit(canvas_dir: Path) -> list[Path]:
    """Decide whether there is anything to validate, and exit if not.

    Extracted from main() 2026-08-03. Four of these five branches are exits
    added by this review, and leaving them inline pushed main() past the
    complexity ceiling — which is the linter noticing that 'work out whether
    to run' and 'run' had become one function. Returns the .yml files to
    validate; every other outcome terminates here with its own message.
    """
    # N/A vs REFUSAL vs PASS — three states, and v0.75.0 collapsed two of them
    # (code review 2026-08-03). It made a present-but-empty canvas exit 1 while
    # leaving an ABSENT canvas exiting 0, which is backwards: absent is the
    # strictly less-informed case. And the empty case broke consumers, because
    # /mycelium:setup creates `.claude/canvas/` containing only `.gitkeep`, while
    # the shipped git-pre-push-example.sh gates on the DIRECTORY existing — so
    # every push from a freshly set-up project was blocked until the user
    # hand-wrote a YAML file or discovered --no-verify.
    #
    # Both are now N/A: a project that has not written its canvas yet is in a
    # legitimate early state, not a defect. This is the same distinction Check 53
    # was corrected to make the same week — migration and validation pressure
    # apply to canvases that EXIST. N/A is not a pass, and the message says so.
    if not canvas_dir.exists():
        print(f"Canvas validation: N/A — no canvas directory at {canvas_dir}. "
              "Nothing was validated, and nothing was supposed to be.")
        sys.exit(0)

    # EMPTY-BY-BIRTH vs EMPTY-BY-BREAKAGE (code review 2026-08-03). The N/A above
    # was extended to "canvas dir holds no .yml" and that covered two states with
    # opposite meanings:
    #
    #   a fresh /mycelium:setup    -> the dir holds only .gitkeep. Legitimate.
    #   a layout change or rename  -> the dir holds FILES, none of them *.yml.
    #
    # .github/workflows/validate.yml runs this bare, so the second state printed
    # N/A and exited 0: rename the canvas to .yaml, or move it one level down,
    # and CI goes green over a canvas nobody validated. That is the exact
    # green-over-nothing shape v0.77.0 was spent removing.
    #
    # Distinguish them by whether the directory holds ANYTHING a human wrote.
    # See canvas_population_state for the three states and why they differ.
    state, canvas_yml, other_files = canvas_population_state(canvas_dir)
    if state == "broken":
        print(f"Canvas validation FAILED: {canvas_dir} holds "
              f"{len(other_files)} file(s) but none match *.yml — "
              f"{', '.join(f.name for f in other_files[:5])}. "
              "A canvas that stopped matching the glob is a broken layout, "
              "not an empty project: renaming to .yaml or moving the files "
              "would otherwise make every validation report N/A and pass.")
        sys.exit(1)
    if state == "fresh":
        print(f"Canvas validation: N/A — {canvas_dir} holds no .yml files yet "
              "(a fresh /mycelium:setup leaves it empty). Nothing was validated. "
              "This is NOT a pass over a populated canvas.")
        sys.exit(0)

    # NO SILENT PASS OVER A POPULATED CANVAS (code review 2026-08-03). This
    # printed "(no schemas to validate against — silently passing)" and exited 0.
    # It is reachable with a FULL canvas whenever CLAUDE_PLUGIN_ROOT points at a
    # stale plugin-cache path, and it made check_empty_input_honesty's exemption
    # for this script false: there WAS a state that verified nothing and claimed
    # a pass. A missing schema directory over real canvas files is a broken
    # installation, not an early project — the empty-canvas cases above have
    # already returned by this point, so this can only be the broken one.
    if not SCHEMA_DIR.exists():
        print(f"Canvas validation FAILED: schema directory not found at "
              f"{SCHEMA_DIR}, but {canvas_dir} holds {len(canvas_yml)} canvas "
              "file(s). Refusing to report a pass over files nothing validated. "
              "Check CLAUDE_PLUGIN_ROOT — a stale plugin-cache path reaches this "
              "state with a healthy canvas.", file=sys.stderr)
        sys.exit(1)

    return canvas_yml


ID_PREFIX_RE = re.compile(r"^([a-z][a-z0-9]*(?:-[a-z0-9]+)*?)-\d+$")


def _collect_id_prefixes(node, section, seen):
    """Record which top-level section each ID PREFIX is DEFINED under.

    Only entries carrying an `id` count. A cross-reference to an id inside prose or a
    field is not a definition and must not register, or every canvas that cites its
    own entries would look misfiled.
    """
    if isinstance(node, dict):
        ident = node.get("id")
        if isinstance(ident, str):
            match = ID_PREFIX_RE.match(ident)
            if match:
                seen.setdefault(match.group(1), set()).add(section)
        for value in node.values():
            _collect_id_prefixes(value, section, seen)
    elif isinstance(node, list):
        for value in node:
            _collect_id_prefixes(value, section, seen)


def purpose_stance_findings(canvas_dir):
    """WARN-tier: does any sub-element contradict the product's own why/how/what?

    Delegated to scripts/check_purpose_stance.py so the same logic serves the validator (advisory)
    and a transition gate (--strict). WARN AND NEVER FAIL here, deliberately: every project
    predating `purpose_properties` would otherwise break on a defect it did not introduce — the
    same consumer-breakage reasoning as the other WARN-tier checks in this file.
    """
    try:
        spec = importlib.util.spec_from_file_location(
            "_cps", Path(__file__).with_name("check_purpose_stance.py")
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.purpose_stance_findings(canvas_dir)
    except Exception:  # noqa: BLE001 — a broken advisory check must never fail a build
        return []


def purpose_why_findings(canvas_dir):
    """WARN-tier: does purpose.yml carry a `why` at all?

    THE GAP THIS CLOSES (dogfood 2026-08-31). `interview/SKILL.md` promises that a user who
    cannot yet name the change "proceeds, flagged for the deeper Phase-1 purpose questions".
    NOTHING DID THE FLAGGING: no script read `purpose["why"]` to test that it was present, and
    no hook did either. So "permissive at entry" was indistinguishable from "permanently empty,
    and nobody will ever say so" — the same shape as the staleness hash that could never
    mismatch, one level up.

    WARN AND NEVER FAIL. An absent `why` at first contact is legitimate: Sinek's own diagnosis
    is that people start from what they are building. It stops being legitimate once work is
    derived from it, and THAT case is a hard schema requirement (`dependentSchemas` in
    purpose.schema.json), not this advisory.
    """
    path = canvas_dir / "purpose.yml"
    if not path.exists():
        return []  # no purpose canvas at all is a different state, not this one
    try:
        doc = load_yaml(path) or {}
    except Exception:  # noqa: BLE001 — parse failures belong to the fail-loud pass
        return []
    why = doc.get("why") if isinstance(doc, dict) else "skip"
    if why == "skip" or (why.strip() if isinstance(why, str) else why):
        return []   # EMPTY COUNTS AS ABSENT: legacy-templated canvases carry `why: ""`
    return [
        ("purpose.yml has no `why`. That is allowed at entry — most people start from what "
         "they are building — but nothing else will remind you, so it is said here rather "
         "than left to a promise. Answer it with /mycelium:interview. Note that "
         "`purpose_properties` cannot be derived until it is present: binding properties "
         "taken from an absent purpose are taken from nothing.")
    ]


def technical_capability_findings(canvas_dir):
    """WARN-tier: does each required capability say what happens when it is absent?

    THE GAP (founder, 2026-08-31). `technical_capabilities_required` was recorded as wired
    because the `derived_from` links inside it had become trace edges. The founder pushed
    back: *"shouldn't the outer field be the one being wired? that's the data object being
    used?"* — and that is right. Traversing generic link attributes inside an object is not
    the same as anything reading the object for what it MEANS. This function reads it by
    name, for its meaning: a list of capabilities the framework requires from its substrate.

    WHAT IT CHECKS, and both are the same failure in different clothes — a dependency that
    is silent about its own absence:
      * a capability with no `fallback_if_absent` does not say what breaks without it;
      * a capability whose `substrate_status` omits a substrate its SIBLINGS record. The
        matrix is only useful if every row covers the same columns; a row missing one is a
        portability claim nobody made and nobody can check.

    WARN, never fail. The matrix is a judgement about other people's tools and will always
    be partly stale.
    """
    path = canvas_dir / "purpose.yml"
    if not path.exists():
        return []
    try:
        doc = load_yaml(path) or {}
    except Exception:  # noqa: BLE001 — parse failures belong to the fail-loud pass
        return []
    caps = doc.get("technical_capabilities_required") if isinstance(doc, dict) else None
    if not isinstance(caps, list) or not caps:
        return []

    out = []
    covered = {}
    for cap in caps:
        if not isinstance(cap, dict):
            continue
        cid = cap.get("id", "<no id>")
        if not cap.get("fallback_if_absent"):
            out.append(
                f"technical_capabilities_required {cid}: no `fallback_if_absent`. A required "
                f"capability that does not say what breaks without it is a silent dependency — "
                f"nothing downstream can tell a degraded run from a full one.")
        status = cap.get("substrate_status")
        covered[cid] = set(status) if isinstance(status, dict) else set()

    every_substrate = set().union(*covered.values()) if covered else set()
    for cid, subs in covered.items():
        missing = sorted(every_substrate - subs)
        if missing:
            out.append(
                f"technical_capabilities_required {cid}: `substrate_status` omits "
                f"{', '.join(missing)}, which sibling capabilities record. A row missing a "
                f"column is a portability claim nobody made and nobody can check.")
    return out


def has_pointer(node):
    """Is an evidence pointer recorded ANYWHERE in this task record?

    FIXED 2026-09-01. The first version looked in exactly two places — top-level keys and
    `touch_log[]` — and the convention in live use has three: `partial_findings[]` carries
    `evidence_logged_to` on ht-037, ht-038 and ht-059. All three were reported as gaps that
    their own data did not have. THE FALSE POSITIVES NAMED THE MISSING CONVENTION: the rule
    was never "a pointer in one of two blessed blocks", it is "a pointer recorded in the
    task record", and hardcoding the locations is what manufactured the finding. Walking the
    structure also means the next block someone invents is covered without another patch.
    """
    if isinstance(node, dict):
        return any("evidence_logged_to" in str(k) or has_pointer(v) for k, v in node.items())
    if isinstance(node, list):
        return any(has_pointer(v) for v in node)
    return False

def closed_with_discipline(task):
    """A fully-disciplined closure HAS answered "did it produce evidence?" — with a null.

    `_common.schema.json#/$defs/closure_discipline` makes `closure_basis` and
    `reopen_trigger` mandatory companions once a `closure_reason` is claimed. That trio is
    the project's existing mechanism for recording that nothing came of something, why, and
    what would make the judgement wrong. A task carrying all three has closed the loop this
    check exists to find open; demanding an evidence pointer as well would be asking it to
    point at evidence it is explicitly recording the absence of.

    ALL THREE ARE REQUIRED. A bare `closure_reason` is the un-disciplined case the schema
    already treats as incomplete, and accepting it here would let silence pass as an answer.
    """
    return all(isinstance(task.get(k), str) and task[k].strip()
               for k in ("closure_reason", "closure_basis", "reopen_trigger"))


def source_class_target_findings(canvas_dir):
    """WARN-tier: a task declared what evidence it would produce — did it say where it landed?

    THE GAP (founder ruling 2026-08-31: "wire it properly"). `source_class_target` sits on 20
    human-tasks — a clean enum value, `external_human`, declaring the KIND of evidence the task
    intends to produce. `check_source_class_fidelity.py` already reads `source_class`. The
    target was never connected to anything: the machinery existed and the field was one hop
    from it, unwired only by omission.

    WHAT IT CHECKS, and it is the loop from intent to outcome rather than the label itself: a
    COMPLETED task that declared a target evidence class should record where that evidence
    went. Measured at the ruling: 15 completed tasks carried the target and only 5 recorded a
    pointer. TEN DECLARED AN INTENDED EVIDENCE CLASS AND NEVER SAID WHETHER THEY PRODUCED IT —
    which makes the field an intention nobody can check, the shape this release series exists
    to remove.

    PENDING TASKS ARE NOT FLAGGED. A task still running has not produced its evidence yet, and
    warning about it would fire on every open task from the day it is created.

    WARN, never fail: the pointer is a convention, and some evidence legitimately lands
    somewhere this check cannot follow.
    """
    path = canvas_dir / "human-tasks.yml"
    if not path.exists():
        return []
    try:
        doc = load_yaml(path) or {}
    except Exception:  # noqa: BLE001 — parse failures belong to the fail-loud pass
        return []
    if not isinstance(doc, dict):
        return []

    out = []
    for task in doc.get("completed_tasks") or []:
        if not isinstance(task, dict) or "source_class_target" not in task:
            continue
        if has_pointer(task) or closed_with_discipline(task):
            continue
        out.append(
            f"{task.get('id', '<no id>')}: completed, and declared "
            f"`source_class_target: {task.get('source_class_target')}` — but records no "
            f"`evidence_logged_to`. The kind of evidence it intended to produce is stated; "
            f"whether it produced any is not, so the target cannot be checked against an "
            f"outcome.")
    return out


_DATE_IN_TEXT = re.compile(r"(20\d{2})[-_](\d{2})[-_](\d{2})")
_INSTRUCTION_KEY = re.compile(r"next_moves|next_steps|action_items", re.IGNORECASE)
# A key that says it is retired is not a stale instruction — it is an archived one. Measured
# 2026-09-01: without this, the check fires on `next_moves_SUPERSEDED_..._KEPT_FOR_THE_RECORD`,
# a field whose NAME declares it dead. Flagging that teaches authors that recording what an
# instruction replaced is punished, which is the opposite of the behaviour wanted.
_RETIRED_KEY = re.compile(
    r"superseded|archived|historic|kept_for_the_record|obsolete|old_", re.IGNORECASE)
_DATE_BEARING_SCALARS = ("updated_at", "completed_at", "reopened_at", "sent_at", "created_at")
_DATED_LISTS = ("touch_log", "partial_findings")


def _newest_dated_entry(record):
    """The newest date anywhere in this record, by the conventions projects actually use."""
    found = []
    for key, value in record.items():
        match = _DATE_IN_TEXT.search(key)          # dated keys: `foo_2026_08_14`
        if match:
            found.append("-".join(match.groups()))
        if key in _DATE_BEARING_SCALARS and isinstance(value, str):
            match = _DATE_IN_TEXT.search(value)
            if match:
                found.append("-".join(match.groups()))
        if key in _DATED_LISTS and isinstance(value, list):
            for entry in value:
                if isinstance(entry, dict) and isinstance(entry.get("date"), str):
                    match = _DATE_IN_TEXT.search(entry["date"])
                    if match:
                        found.append("-".join(match.groups()))
    return (max(found), len(found)) if found else (None, 0)


def stale_instruction_list_findings(canvas_dir):
    """WARN-tier: an instruction list that the record around it has moved past.

    THE GAP (dogfood report, 2026-09-01, user-caught). Asked who to contact about a live
    opportunity, an agent read a task's `next_moves` list and named the wrong person. The task's
    own body said otherwise IN CAPITALS, in a dated entry written nineteen days after the list.
    Three of the list's five items were dead.

    WHY NO EXISTING GUARD CATCHES IT, which is the whole reason it is worth a check. Nothing was
    inferred, nothing was absent, and nothing was unsourced — so the absence-claim guard, the
    read-before-research nudge and the citation checks all pass. The agent trusted a SUMMARY over
    the detail that superseded it, inside a file it had already read in full. Every shipped guard
    watches what an agent ASSERTS; this watches what it READS.

    AND THE CANVAS DESIGN PRODUCES IT. Entries are append-only and dated; an instruction list is
    neither. The record grows, the instruction list does not. `next_moves` is the worst field for
    this to land in, because a stale claim buried in prose gets weighed while a stale instruction
    gets executed.

    TWO SHAPES, AND THE SECOND IS THE COMMON ONE. Measured across the reporting project: two
    lists carried their own date, five carried none at all. An undated instruction list cannot be
    compared to anything, which is exactly how it goes stale invisibly — the same reasoning as
    "an empty list is a measurement; an absent field is not", one field over.

    NOT A LEXICAL CHECK. It compares dates and reads no prose, so it needs no natural-language
    understanding and cannot be fooled by wording. `next_moves` is not a framework field — no
    schema defines it — so this watches a SHAPE that projects invent rather than a term the
    framework owns.
    """
    out = []
    for path in sorted(Path(canvas_dir).glob("*.yml")):
        try:
            doc = load_yaml(path) or {}
        except Exception:  # noqa: BLE001,S112 — parse failures belong to the fail-loud pass,
            # which reports "YAML parse error in <file>" and exits 1 over the same file. This
            # advisory declines to speak precisely because that pass already has.
            continue
        if not isinstance(doc, dict):
            continue
        for records in (v for v in doc.values() if isinstance(v, list)):
            for record in records:
                if isinstance(record, dict):
                    out.extend(_instruction_findings(path.name, record))
    return out


def _instruction_findings(filename, record):
    newest, count = _newest_dated_entry(record)
    if not newest:
        return []   # nothing dated to compare against; silence is correct
    if closed_with_discipline(record):
        # A record closed with reason + basis + reopen_trigger has recorded that it is DONE, and a
        # reader acts on that closure rather than on a leftover instruction list. Reusing the rule
        # v0.160.0 established for evidence pointers instead of minting a second one.
        # MEASURED 2026-09-01: this removes the dogfood project's only finding — a completed task
        # carrying `candidate_next_moves_UNVERIFIED` — which was the check's sole false positive.
        # The failure this exists for happened on a LIVE task about a LIVE opportunity.
        return []
    rid = record.get("id") or record.get("cycle_id") or "<no id>"
    out = []
    for key in record:
        if not _INSTRUCTION_KEY.search(key) or _RETIRED_KEY.search(key):
            continue
        if key.endswith("_updated"):
            # `next_moves_updated` is the DATE MARKER for a list, not a list. Caught by its own
            # test: without this the marker matched the instruction pattern, carried no date in
            # its own name, and was reported as an undated instruction list — the check flagging
            # the very field supplied to satisfy it.
            continue
        match = _DATE_IN_TEXT.search(key)
        own = "-".join(match.groups()) if match else None
        if own is None:
            explicit = record.get(f"{key}_updated")
            if isinstance(explicit, str):
                match = _DATE_IN_TEXT.search(explicit)
                own = "-".join(match.groups()) if match else None
        if own is None:
            out.append(
                f"{filename}#{rid}: `{key}` carries no date, and the record around it holds "
                f"{count} dated entries (newest {newest}). An undated instruction list cannot be "
                f"checked against the record it summarises, which is how it goes stale unnoticed. "
                f"Date it (`{key}_updated`, or a date in the key) or fold it into a dated entry.")
        elif own < newest:
            out.append(
                f"{filename}#{rid}: `{key}` is dated {own} and the record has moved since — "
                f"newest dated entry {newest}. An instruction list older than the record it "
                f"summarises is something a reader in a hurry will execute. Re-read it against "
                f"the newer entries before acting on it, and rewrite or retire it.")
    return out


def _count_provenance(node):
    """(provenance blocks seen, how many carry a date) anywhere in this document.

    Recursive because the dogfood canvas nests provenance well below the top level; counting
    only top-level entries would report a denominator far smaller than the real one.
    """
    seen = ok = 0
    if isinstance(node, dict):
        prov = node.get("provenance")
        if isinstance(prov, dict):
            seen += 1
            stamp = str(prov.get("captured_at") or prov.get("validated_at") or "")
            ok += 1 if _DATE_IN_TEXT.search(stamp) else 0
        children = node.values()
    elif isinstance(node, list):
        children = node
    else:
        return 0, 0
    for child in children:
        child_seen, child_ok = _count_provenance(child)
        seen += child_seen
        ok += child_ok
    return seen, ok


def provenance_dating_findings(canvas_dir):
    """WARN-tier: ONE coverage line for how much provenance carries a date at all.

    THE FAILURE, found in the dogfood canvas 2026-09-01. Eleven landscape entries written over
    eleven days shipped with no `captured_at`. They were not STALE — they were UNCHECKABLE, which
    is worse, because a stale entry eventually trips a decay threshold and asks to be revisited
    while an undated one never does. `canvas-health` step 7 scans provenance blocks for a date and
    compares what it finds; an absent date is silently skipped, so the entries were invisible to
    the exact mechanism meant to catch them.

    WHY THIS IS ONE LINE AND NOT ONE PER ENTRY. Measured before shipping: 98 of 346 provenance
    blocks across a real 25-file canvas carry no date, 93 of them in a single file. A per-entry
    warning would fire ninety-odd times and teach its reader to skip the whole class — the failure
    `canvas-health` already recorded when a rule fired on 80% of a corpus. A ratio states the
    denominator and demands nothing, which is the honest instrument for a gap this size.

    It is deliberately NOT a schema requirement: `provenance` is shared by every canvas through
    `_common.schema.json`, so requiring `captured_at` there would fail files that have nothing to
    do with evidence decay.
    """
    total = dated = 0
    per_file = {}
    for path in sorted(Path(canvas_dir).glob("*.yml")):
        try:
            doc = load_yaml(path) or {}
        except Exception:  # noqa: BLE001,S112 — parse failures belong to the fail-loud pass,
            # which names the file and exits 1. This advisory declines because that pass spoke.
            continue
        seen, ok = _count_provenance(doc)
        total += seen
        dated += ok
        if seen - ok:
            per_file[path.name] = seen - ok

    if not total or not per_file:
        return []
    worst = ", ".join(f"{f} ({n})" for f, n in sorted(per_file.items(), key=lambda kv: -kv[1])[:3])
    return [(
        f"{dated} of {total} provenance blocks carry a `captured_at` or `validated_at` date; "
        f"{total - dated} carry neither. An undated block is not stale, it is UNCHECKABLE — every "
        f"decay threshold skips it silently, so it never asks to be revisited. Most affected: "
        f"{worst}. This is a ratio, not a to-do: date the ones whose age would change a decision."
    )]


def citation_register_findings(canvas_dir):
    """WARN-tier: does a canvas line repeat a claim the project already ruled against?

    Delegated to scripts/check_citations.py so one definition serves the validator, the
    canvas-health skill and any future gate — the same arrangement as cycle_record_findings.

    WHY THE VALIDATOR AND NOT THE PRE-PUSH GATE SET. The scan is an advisory reporter: over a
    project with no register it must refuse rather than pass (empty-input honesty), and the
    shipped pre-push hook treats any non-zero as failure — so gating on it would block every push
    from a project that has simply never written one. Here it reports and never fails, which gives
    it an automatic reader at push time without that cost.

    THE FAILURE IT EXISTS FOR (2026-09-01, twice in one session): a ruled-on citation written into
    two canvas files without the register being read, then a narrow register entry paraphrased into
    a broad one and acted on, rewriting four surfaces that were already correct.
    """
    try:
        spec = importlib.util.spec_from_file_location(
            "_cc", Path(__file__).with_name("check_citations.py")
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        findings, _, entries = mod.scan(Path(canvas_dir).parent.parent)
    except Exception:  # noqa: BLE001 — a broken advisory check must never fail a build
        return []
    if entries == -1:
        # A malformed register is LOUDER than an absent one: someone believed these rules were
        # live and every one of them is inert.
        return [(f"`.claude/harness/do-not-cite.yml` EXISTS but could not be parsed, so every "
                 f"rule in it is inert. {findings[0][2]['verbatim']}")]
    if not entries:
        return []   # no register is a not-configured state here; the standalone script says so
    return [
        f"{name}:{num} repeats a claim this project has ruled on ({entry.get('verdict', '?')}) — "
        f'matched "{token}". Register says, verbatim: '
        f"{' '.join((entry.get('verbatim') or '').split())}"
        for name, num, entry, token in findings
    ]


def print_advisory_warnings(canvas_dir):
    """Emit the WARN-tier findings that never fail a build.

    Extracted from main() so adding a new advisory check does not push main past the
    complexity limit — the shape that made the previous addition a lint failure rather
    than a review question.
    """
    for label, findings in (
        ("purpose stance", purpose_stance_findings(canvas_dir)),
        ("cycle record", cycle_record_findings(canvas_dir)),
        ("task list", task_list_findings(canvas_dir)),
        ("purpose why", purpose_why_findings(canvas_dir)),
        ("tech capability", technical_capability_findings(canvas_dir)),
        ("evidence target", source_class_target_findings(canvas_dir)),
        ("dpia", dpia_determination_findings(canvas_dir)),
        ("stale instruction", stale_instruction_list_findings(canvas_dir)),
        ("provenance dating", provenance_dating_findings(canvas_dir)),
        ("do-not-cite", citation_register_findings(canvas_dir)),
    ):
        for w in findings:
            print(f"  WARN ({label}): {w}")


def dpia_determination_findings(canvas_dir):
    """WARN-tier: a `dpia_required: true` must point at the DPIA it says is needed.

    WHY THIS FUNCTION EXISTS AT ALL. `dpia_required` sat in the shipped privacy-assessment
    template with NO CONSUMER — nothing read it, so the determination could say anything and
    nothing downstream would notice. It stayed invisible until the canvas was given a schema on
    2026-09-01, at which point check_field_wiring flagged it as promise-shaped-and-unread and
    blocked the push. The field's purpose is unambiguously to be read: it is a compliance
    determination, not a note. So it gets a consumer here, per the founder rule of 2026-08-31.

    WHAT IT CHECKS, AND WHERE THAT COMES FROM. engine/theory-gates.md L3 requires "DPIA completed
    for high-risk processing" and names the DPIA document among its required evidence. So a
    `true` that points at nothing is the gap: the canvas asserts a DPIA is needed while recording
    nothing that shows one exists. This is DERIVED, not invented — unlike the schema's
    rationale-when-false rule, which is labelled in privacy-assessment.schema.json as the schema
    author's own judgement.

    THE `false` CASE IS DELIBERATELY NOT HERE. privacy-assessment.schema.json already requires a
    rationale when the determination is false, and enforcing the same rule in two places is the
    defect this repo keeps finding in itself.

    WARN AND NEVER FAIL: whether the reference is adequate is a human call, and a project that has
    genuinely completed a DPIA may record it somewhere this cannot see.
    """
    path = canvas_dir / "privacy-assessment.yml"
    if not path.exists():
        return []
    try:
        doc = load_yaml(path) or {}
    except Exception:  # noqa: BLE001 — parse failures belong to the fail-loud pass
        return []
    if not isinstance(doc, dict) or doc.get("dpia_required") is not True:
        return []   # false/absent is the schema's business, not this check's
    # Any non-empty prose or reference anywhere in the DPIA fields counts as pointing at one.
    for key in ("dpia_rationale", "dpia_reference", "dpia_document"):
        val = doc.get(key)
        if isinstance(val, str) and val.strip():
            return []
    return [
        ("privacy-assessment.yml declares `dpia_required: true` but records nothing that points "
         "at the DPIA — no `dpia_rationale`, `dpia_reference` or `dpia_document`. "
         "engine/theory-gates.md L3 names the DPIA document as required evidence at this gate, so "
         "a bare `true` asserts the obligation without showing it was met. Run "
         "/mycelium:privacy-check, or record where the DPIA lives.")
    ]


def task_list_findings(canvas_dir):
    """WARN-tier: does a task's own `status` agree with the list it is filed in?

    THE DEFECT THIS EXISTS FOR, measured 2026-08-24 in the dogfood project: of 94 entries
    under `pending_tasks`, only **9 were pending**. 61 were `completed`, 7 `abandoned`, 1
    `cancelled`, 16 `in_progress`. One had been closed ten days earlier and was still being
    read as an open commitment.

    NOTHING CAUGHT IT, AND THE SCHEMA IS WHY. `pending_tasks.items.status` shares the full
    six-value enum, so a completed task inside the pending list is schema-VALID — the file
    passed validation for four months. The root cause is one layer further out: `/log-evidence`
    says to move a closed task to `completed_tasks`, that list did not exist in the canvas, so
    every closure set `status` in place instead. **An instruction whose destination does not
    exist does not fail; it silently does nothing**, which is the same shape as a specced field
    with no reader.

    WARN AND NEVER FAIL. The remedy is moving entries between lists, which is a judgement about
    someone's real commitments — and a hard failure would block every consumer on a defect the
    framework's own closure path created.
    """
    task_file = Path(canvas_dir) / "human-tasks.yml"
    if not task_file.exists():
        return []
    try:
        data = yaml.safe_load(task_file.read_text(encoding="utf-8")) or {}
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return []
    if not isinstance(data, dict):
        return []

    belongs = TASK_STATUS_HOMES
    findings, closed_seen = [], 0
    for list_name, allowed in belongs.items():
        misfiled = _misfiled_by_status(data.get(list_name), allowed)
        closed_seen += sum(len(v) for k, v in misfiled.items() if k in CLOSED_STATUSES)
        findings.extend(_misfile_finding(list_name, st, ids)
                        for st, ids in sorted(misfiled.items()))
    if closed_seen and not isinstance(data.get("completed_tasks"), list):
        findings.append(
            "closures exist but there is no `completed_tasks:` list to move them into — which "
            "is why they were left in place. /mycelium:log-evidence writes to that list; "
            "without it the instruction silently does nothing."
        )
    return findings


#: Statuses meaning the task is CLOSED. Used to decide whether a missing
#: `completed_tasks` list is the reason closures were left where they were.
CLOSED_STATUSES = ("completed", "abandoned", "cancelled", "stalled")

#: How many ids to name before summarising. Naming a few makes the WARN actionable;
#: naming 61 makes it scrollable-past, which is how a warning gets muted.
_IDS_SHOWN = 4


#: list name -> the statuses that BELONG in it. `pending_tasks` holds open work, so
#: `in_progress` is at home there; it is not a misfile.
#:
#: `waiting` and `watching` are OPEN states (v0.132.0) and belong there. Flagging them
#: would fire on the majority of a real project's open work: measured 2026-08-24,
#: 13 of 16 in_progress tasks were sent-and-awaiting and 3 of 9 pending were watches.
#:
#: Module-level since v0.141.0 because TWO checks need it and they had DISAGREED:
#: `id_prefix_section_warnings` warned that `ht-NNN` spans three sections while this
#: mapping, twenty lines away, declared all three to be its legitimate homes.
TASK_STATUS_HOMES = {
    "pending_tasks": {"pending", "in_progress", "waiting", "watching"},
    "completed_tasks": {"completed"},
    "closed_without_evidence": {"abandoned", "cancelled", "stalled"},
}

#: Section groups that ONE id prefix is SUPPOSED to span, because together they form a
#: single register split by lifecycle stage rather than by kind. An entry moving between
#: these is the closure path working, not a misfiling.
#:
#: Derived from TASK_STATUS_HOMES rather than written out again, so the two cannot drift.
LIFECYCLE_REGISTER_GROUPS = (frozenset(TASK_STATUS_HOMES),)

def _misfiled_by_status(entries, allowed):
    """{status: [ids]} for entries whose own status does not belong in this list."""
    out = {}
    if not isinstance(entries, list):
        return out
    for t in entries:
        if not isinstance(t, dict):
            continue
        status = str(t.get("status") or "").strip()
        if status and status not in allowed:
            out.setdefault(status, []).append(str(t.get("id") or "?"))
    return out


def _misfile_finding(list_name, status, ids):
    extra = len(ids) - _IDS_SHOWN
    shown = ", ".join(ids[:_IDS_SHOWN]) + (f", +{extra} more" if extra > 0 else "")
    return (
        f"{len(ids)} task(s) in `{list_name}` carry `status: {status}`, which belongs in "
        f"{_home_for(status)}. A closed task read as an open commitment is the defect; the "
        f"schema permits it because the status enum is shared. ({shown})"
    )


def _home_for(status):
    """The list a status belongs in, named so the WARN says where to move it."""
    if status == "completed":
        return "`completed_tasks`"
    if status in ("abandoned", "cancelled", "stalled"):
        return "`closed_without_evidence`"
    return "`pending_tasks`"


def cycle_record_findings(canvas_dir):
    """WARN-tier: do recorded cycles carry the fields the spec says feed framework-health?

    Delegated to scripts/check_cycle_recording.py so one definition serves the validator and
    any future gate — the same arrangement as purpose_stance_findings above.

    THIS DELIBERATELY DOES NOT INVOKE THE RELEASE-CADENCE HALF of that script. That half asks
    whether a cycle has been recorded recently, keyed on minor releases, and its unit is under
    review; running it here would put a green row on a dashboard over a stale log. Coverage has
    no threshold to get wrong.

    WARN AND NEVER FAIL, for the reason the other WARN-tier checks here give: measured across a
    real project, the fields are absent from every record, and failing on that would break every
    consumer for a defect they did not introduce.
    """
    cycle_file = Path(canvas_dir) / "cycle-history.yml"
    if not cycle_file.exists():
        return []
    try:
        spec = importlib.util.spec_from_file_location(
            "_ccr", Path(__file__).with_name("check_cycle_recording.py")
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.cycle_field_coverage(cycle_file)
    except Exception:  # noqa: BLE001 — a broken advisory check must never fail a build
        return []


def _is_lifecycle_split(sections):
    """True when these sections are one register split by stage, not two kinds sharing a prefix.

    Subset rather than equality: a project whose canvas has open tasks but has never closed
    one has entries in `pending_tasks` only, and a project mid-migration may not have all
    three lists. Requiring an exact match would fire on both.
    """
    return any(set(sections) <= group for group in LIFECYCLE_REGISTER_GROUPS)


def id_prefix_section_warnings(canvas_dir):
    """WARN-tier: an ID prefix should define entries in exactly ONE top-level section.

    Found 2026-08-21, four days late. Two `comp-NNN` competitor entries had been
    appended to `out_of_scope` — which holds framework boundary/rationale entries —
    instead of `components`, in a 6,000-line file where both lists take `- id:` items.
    Nothing noticed: the scout's weekly harvest check greps the destination FILE for a
    detection token, so the token matched and it recorded the entry as landed in the
    register it was not in. A competitor outside the competitor register is invisible
    to every count and every render that reads that list.

    Measured before shipping: across the 25 canvas files of the dogfood project, every
    ID prefix already lived in exactly one section. Zero false positives, so the check
    fires on the defect and nothing else.

    THAT MEASUREMENT WAS WRONG WITHIN TWO DAYS, and the correction is the reason
    `_is_lifecycle_split` exists (v0.141.0). `human-tasks.yml` defines `ht-NNN` under
    `pending_tasks`, `completed_tasks` AND `closed_without_evidence` — by design, and
    this same module's `TASK_STATUS_HOMES` says so explicitly. The check was therefore
    reporting the framework's own closure path as a misfiling, on every run, forever.
    A permanent warning is worse than no warning: it trains the reader to scroll past
    the line where a real misfiling would appear.

    The distinction that matters: `comp-NNN` in `components` and `out_of_scope` is two
    KINDS in one prefix, which is the defect. `ht-NNN` across three task lists is one
    kind at three LIFECYCLE STAGES, which is the register working.

    WARN and never fail, for the same reason as the other WARN-tier checks here:
    downstream projects may carry a legacy misfiling they did not introduce.
    """
    out = []
    for path in sorted(canvas_dir.glob("*.yml")):
        try:
            data = yaml.safe_load(path.read_text())
        except (yaml.YAMLError, OSError):
            continue  # reported by the fail-loud pass
        if not isinstance(data, dict):
            continue
        seen = {}
        for key, value in data.items():
            _collect_id_prefixes(value, key, seen)
        for prefix, sections in sorted(seen.items()):
            if len(sections) > 1 and not _is_lifecycle_split(sections):
                where = ", ".join(sorted(sections))
                out.append(
                    f"{path.name}: '{prefix}-NNN' entries are defined under "
                    f"{len(sections)} sections ({where}) — one is a misfiling, and an "
                    f"entry outside its register is invisible to every count that reads it"
                )
    return out


def open_task_criterion_warnings(canvas_dir):
    """WARN-tier: an OPEN human-task with no closure criterion cannot be closed on
    evidence, only abandoned by neglect.

    Found 2026-08-21 by a founder scanning the open list by eye, not by any check:
    five open tasks carried no `success_criteria`, no `pre_registered_outcomes`, no
    `scoring_rules` and no `stop_condition`, and two of those had no horizon either,
    so nothing would ever prompt a look at them. The same sweep closed three tasks
    whose outcomes had been recorded days earlier and left open regardless.

    WARN AND NEVER FAIL, deliberately. Downstream projects carry tasks created before
    this check existed, and a hard failure would break their CI for a defect they did
    not introduce — the same consumer-breakage reasoning applied to the empty-canvas
    case in this file. It surfaces the debt; it does not punish inheriting it.
    """
    tasks_path = canvas_dir / "human-tasks.yml"
    if not tasks_path.exists():
        return []
    try:
        data = yaml.safe_load(tasks_path.read_text()) or {}
    except (yaml.YAMLError, OSError):
        return []  # parse and read failures are already reported by the fail-loud pass
    prefixes = (
        "success_criteria", "pre_registered_outcomes", "scoring_rules",
        "stop_condition", "watch_trigger", "reopen_trigger",
    )
    out = []
    for task in data.get("pending_tasks") or []:
        if not isinstance(task, dict):
            continue
        if task.get("status") not in ("pending", "in_progress"):
            continue
        if any(str(k).startswith(prefixes) for k in task):
            continue
        tid = task.get("id", "<no id>")
        horizon = task.get("horizon")
        tail = "" if horizon else " AND no horizon, so nothing will prompt a look"
        out.append(
            f"{tid}: open with no closure criterion{tail} — it cannot be closed on "
            f"evidence, only abandoned"
        )
    return out


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

    canvas_yml = triage_canvas_or_exit(canvas_dir)

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
    all_errors.extend(ost_root_errors(canvas_dir))

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

    for w in open_task_criterion_warnings(canvas_dir):
        print(f"  WARN (uncloseable task): {w}")

    for w in id_prefix_section_warnings(canvas_dir):
        print(f"  WARN (misfiled entry): {w}")

    print_advisory_warnings(canvas_dir)

    schemas_present = len(list(SCHEMA_DIR.glob("*.schema.json"))) - 1  # exclude _common
    canvases_present = len(canvas_yml)
    # The empty-canvas N/A used to live HERE, and it said "Nothing was validated"
    # (code review 2026-08-03) — untrue by this point, because validate_diamonds
    # and enum_consistency_errors have already run and could have failed the
    # build above. It is decided before any of that now, where the claim is
    # accurate, so this tail only ever reports a real pass over real files.

    print(
        f"Canvas validation: PASS ({canvases_present} canvas files, "
        f"{schemas_present} schemas, {len(warnings)} schema-less, "
        f"{len(all_ids)} traceable IDs)",
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
