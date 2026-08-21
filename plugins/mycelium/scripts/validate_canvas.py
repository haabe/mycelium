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
            if len(sections) > 1:
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
