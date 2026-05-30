"""Shared manifest.yml parser used by framework_guard.py and parse_manifest.py.

Closes the parse_manifest DRY violation surfaced by the 2026-05-03
end-of-session code audit. Both consumer scripts previously had identical
parse_manifest() implementations — now they import from here.

The parser is stdlib-only (no PyYAML) and intentionally minimal: it handles
the specific structure of .claude/manifest.yml, not arbitrary YAML. If the
manifest grows new sub-structures (a new section or a new nesting depth),
update SECTION_KEY_MAP below and add a corresponding test in
.claude/tests/python/test_manifest_lib.py.
"""
from pathlib import Path

# Maps (section, subsection) tuples in manifest.yml to the output key.
# subsection is None for top-level lists like harness_framework or project_state.
# Adding a new manifest section: add an entry here and an output bucket
# in EMPTY_FRAMEWORK below.
SECTION_KEY_MAP = {
    ("framework", "top_level"): "top_level",
    ("framework", "directories"): "directories",
    ("framework", "single_files"): "single_files",
    ("framework", "version_source"): "version_source",
    ("harness_framework", None): "harness_framework",
    ("preserved_dir_readmes", None): "preserved_dir_readmes",
    ("evals", "replace"): "evals_replace",
    ("metrics_adapters", "framework"): "metrics_adapters_framework",
    ("project_state", None): "project_state",
}

EMPTY_FRAMEWORK = {key: [] for key in SECTION_KEY_MAP.values()}

# Manifest YAML uses 2-space indentation for sub-sections (see manifest.yml).
INDENT_TOP_LEVEL = 0
INDENT_SUBSECTION = 2

# List items begin with "- " (hyphen + single space).
LIST_ITEM_PREFIX = "- "
# Length of the list-item prefix — used to slice off the "- " before
# extracting the value.
LIST_ITEM_PREFIX_LEN = 2


def parse_manifest(manifest_path):
    """Extract framework file/directory lists from manifest.yml.

    Returns a dict with keys matching the manifest sections:
      top_level, directories, single_files, harness_framework,
      preserved_dir_readmes, evals_replace, metrics_adapters_framework,
      project_state

    Returns EMPTY_FRAMEWORK (all keys → empty lists) if manifest_path
    does not exist — fail-open semantics for the framework-guard hook.
    """
    framework = {key: [] for key in SECTION_KEY_MAP.values()}

    manifest_path = Path(manifest_path)
    if not manifest_path.exists():
        return framework

    section = None
    subsection = None
    list_items_seen = 0
    with open(manifest_path) as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")
            stripped = line.lstrip()
            if not stripped or stripped.startswith("#"):
                continue

            indent = len(line) - len(stripped)

            # Top-level section header (column 0): "framework:"
            if indent == INDENT_TOP_LEVEL and stripped.endswith(":"):
                section = stripped[:-1]
                subsection = None
                continue

            # Sub-section header (column 2): "  top_level:"
            if indent == INDENT_SUBSECTION and stripped.endswith(":"):
                subsection = stripped[:-1]
                continue

            # List item: "- value  # optional comment"
            if stripped.startswith(LIST_ITEM_PREFIX):
                list_items_seen += 1
                raw_value = stripped[LIST_ITEM_PREFIX_LEN:].split("#")[0].strip()
                value = raw_value.strip('"').strip("'")
                if not value:
                    continue
                key = SECTION_KEY_MAP.get((section, subsection))
                if key is not None:
                    framework[key].append(value)

    # Structural-drift guard: a manifest with list items that bucketed into
    # nothing means our indentation/section assumptions no longer match the
    # file (e.g. someone reindented manifest.yml to 4 spaces). Silently
    # returning empty lists would make framework_guard.py fail OPEN — every
    # protected path would become writable. Fail LOUD instead so CI/the hook
    # surfaces the drift rather than silently dropping protection.
    if list_items_seen > 0 and not any(framework.values()):
        raise ValueError(
            f"manifest parse yielded zero framework entries from "
            f"{list_items_seen} list item(s) in {manifest_path}: "
            "indentation or section structure has drifted from "
            "SECTION_KEY_MAP / INDENT_SUBSECTION assumptions."
        )

    return framework
