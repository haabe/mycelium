"""Check one canvas or diamonds file against its schema right after it is written (v0.250.0).

The E2E happy path (run 19, plugin 0.249.0) wrote `privacy-assessment.yml` with a root key the
schema rejects, and nothing said so until the harness ran `validate_canvas.py` at the end of the
turn. The post-write nudge had said "Schema exists ... validate with validate_canvas.py" once that
session; a reminder to run a check is not the check. This runs it on the file just written and
hands the exact errors back to the agent in the same turn, where fixing them costs one edit.

It reuses `validate_canvas.py`'s own schema functions, so there is one definition of valid.

DEPENDENCIES. `validate_canvas.py` needs PyYAML, jsonschema and referencing, and runtime hooks must
work without a pip install. So this check is OPTIONAL at runtime: with the dependencies present it
runs; without them it says once per session that it could not run, and names what to install. It
never blocks a write and never exits non-zero.

Output (PostToolUse): `{"decision": "block", "reason": ...}` when the file is invalid, which the
runtime shows to the agent; `hookSpecificOutput.additionalContext` for the could-not-run note.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MIN_PARTS = 3      # .claude/<canvas|diamonds>/<file>
MAX_SHOWN = 8      # errors listed in full before "... and N more"


def _target(data: dict) -> Path | None:
    ti = data.get("tool_input") if isinstance(data.get("tool_input"), dict) else {}
    raw = ti.get("file_path") or ti.get("path") or ti.get("destination") or ""
    if not raw:
        return None
    p = Path(raw)
    if not p.is_absolute():
        p = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()) / p
    parts = p.parts
    if p.suffix not in (".yml", ".yaml") or len(parts) < MIN_PARTS or parts[-3] != ".claude":
        return None
    return p if parts[-2] in ("canvas", "diamonds") else None


def _load_validator():
    """validate_canvas as a module, or the reason it could not be loaded."""
    spec = importlib.util.spec_from_file_location("validate_canvas", HERE / "validate_canvas.py")
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except SystemExit:  # its import guard exits 2 when a dependency is missing
        missing = [m for m in ("yaml", "jsonschema", "referencing")
                   if importlib.util.find_spec(m) is None]
        return None, "missing " + ", ".join(missing or ["a dependency"])
    return mod, ""


def errors_for(path: Path, vc) -> list[str]:
    """Schema errors for one file, from validate_canvas's own functions, and its duplicate keys.

    Duplicate keys since v0.273.1: YAML keeps the second value and drops the first without a word,
    so the file parses and matches its schema. The full validator reported it; this check, the one
    that runs as the file is written, did not. E2E service world run 4 wrote three duplicate keys
    into threat-model.yml, nothing told the builder, and the canvas stayed invalid."""
    try:
        dups = [f"Silent data loss in {path.name}: {d} (the second value destroys the first)"
                for d in vc.duplicate_mapping_keys(path.read_text(encoding="utf-8"))]
    except (OSError, ValueError, vc.yaml.YAMLError):
        dups = []  # SPEAKS: an unreadable or unparseable file is named by the schema check below
    registry = vc.build_registry()
    if path.parent.name == "canvas":
        return dups + vc.validate_canvas_against_schema(path, registry)
    found = vc.validate_diamonds(path.parent.parent / "canvas", registry)
    return dups + [e for e in found if f"diamonds/{path.name}" in e]


def _said_once(project: Path, session: str) -> bool:
    """True if the could-not-run note was already given this session (records it if not)."""
    if not session:
        return False
    ledger = project / ".claude" / "state" / "canvas-check-skipped"
    try:
        if ledger.exists() and session in ledger.read_text().split():
            return True
        ledger.parent.mkdir(parents=True, exist_ok=True)
        with ledger.open("a") as f:
            f.write(session + "\n")
    except OSError:
        return False
    return False


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if not isinstance(data, dict):
        return 0
    path = _target(data)
    if path is None or not path.exists():
        return 0
    vc, why = _load_validator()
    if vc is None:
        project = path.parent.parent.parent
        if not _said_once(project, str(data.get("session_id") or "")):
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": (
                    f"Canvas schema check did not run on {path.name} ({why}). "
                    "Install with: pip install PyYAML jsonschema referencing. "
                    "The file was written but has not been checked against its schema.")}}))
        return 0
    errors = errors_for(path, vc)
    if errors:
        shown = "\n".join(f"  - {e}" for e in errors[:MAX_SHOWN])
        more = f"\n  ... and {len(errors) - MAX_SHOWN} more" if len(errors) > MAX_SHOWN else ""
        print(json.dumps({"decision": "block", "reason": (
            f"{path.name} was written but fails its schema, so Mycelium's validator will reject "
            f"the canvas:\n{shown}{more}\n"
            "Fix the file now. If the content has no field in the schema, put it in the field the "
            "owning skill names, or record it in the decision log; do not add a new top-level "
            "key.")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
