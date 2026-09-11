#!/usr/bin/env python3
"""Autonomous-mode evidence-integrity guard (PreToolUse helper).

Enforces, as MECHANISM, the boundary that engine/autonomous-mode.md states as
prose: inside a DECLARED autonomous run, the running model must not write
fabricated or elevated evidence into the structured canvas. Motivated by opp-011
Stage A (2026-06-11): Haiku 4.5 fabricated `external_human` interview results,
flipped `validated`, and built a confidence delta on it -- without knowing it
had crossed the boundary. Prose did not transfer below Fable 5; this is the
enforcement.

Activation -- autonomous mode declared, on a hook-visible surface:
  - env MYCELIUM_AUTONOMOUS_RUN in {1,true,yes,on} (case-insensitive), OR
  - .claude/diamonds/active.yml has a top-level `autonomous: true`.
If neither -> not autonomous -> allow (a present human's judgment stands;
"a present human always outranks the flag").

Enforced files: .claude/canvas/*.yml, .claude/diamonds/*.yml and the
mycelium-state/ mirror equivalents -- the structured evidence ledger where these
tokens are schema assignments, not prose.

Forbidden assignments in the written content (an autonomous run cannot
legitimately produce any of these -- no human or world answered, only the
persona simulated):
  - source_class: external_human | external_data
  - validated: true
  - evidence_type: anecdotal | data-supported | test-validated | launch-validated
Permitted: internal_simulated / speculation / validated: false.

I/O contract (Claude Code PreToolUse):
  stdin: tool input JSON; argv[1]: project dir
  exit 0 silent                                  -> allow
  exit 0 + JSON permissionDecision=deny          -> block with UI message
Fail-open on unparseable input (a guard bug must never brick all writes).
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _hook_input as hi  # sibling module, after the path insert

FORBIDDEN = [
    (re.compile(r'(?m)^\s*["\']?source_class["\']?\s*:\s*["\']?external_human\b'),
     "source_class: external_human"),
    (re.compile(r'(?m)^\s*["\']?source_class["\']?\s*:\s*["\']?external_data\b'),
     "source_class: external_data"),
    (re.compile(r"(?mi)^\s*[\"']?validated[\"']?\s*:\s*[\"']?(true|yes|on)\b"),
     "validated: true"),
    (re.compile(r'(?mi)^\s*["\']?evidence_type["\']?\s*:\s*["\']?'
                r'(anecdotal|data-supported|test-validated|launch-validated)\b'),
     "evidence_type above speculation"),
]
_FORBIDDEN_VALUES = {
    "source_class": {"external_human", "external_data"},
    "evidence_type": {"anecdotal", "data-supported", "test-validated", "launch-validated"},
}

try:
    import yaml as _yaml
except ImportError:  # spoken below: the regex fallback names itself in the deny reason
    _yaml = None


def truthy(value):
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _autonomous_in_text(text: str) -> bool:
    if _yaml is not None:
        try:
            doc = _yaml.safe_load(text)
            if isinstance(doc, dict):
                return truthy(doc.get("autonomous", False))
        except _yaml.YAMLError:
            pass
    return bool(re.search(r"(?mi)^\s*[\"']?autonomous[\"']?\s*:\s*(true|yes|on)\b", text))


def autonomous_active(project_dir):
    if truthy(os.environ.get("MYCELIUM_AUTONOMOUS_RUN", "")):
        return True
    active = os.path.join(project_dir, ".claude", "diamonds", "active.yml")
    try:
        with open(active, encoding="utf-8") as handle:
            return _autonomous_in_text(handle.read())
    except OSError:
        return False


def extract(tool_input, tool_name):
    """Return (path, content_to_scan). Kept for callers; the guard itself scans the RESULT."""
    path = tool_input.get("file_path") or tool_input.get("path")
    if tool_name in ("Write", "mcp__filesystem__write_file"):
        return path, tool_input.get("content", "") or ""
    if tool_name == "Edit":
        return path, tool_input.get("new_string", "") or ""
    if tool_name == "MultiEdit":
        edits = tool_input.get("edits") or []
        return path, "\n".join(str(e.get("new_string", "")) for e in edits)
    if tool_name == "mcp__filesystem__edit_file":
        edits = tool_input.get("edits") or []
        return path, "\n".join(str(e.get("newText", "")) for e in edits)
    return path, (tool_input.get("content", "")
                  or tool_input.get("new_string", "") or "")


_LOOSE_FORBIDDEN = [
    (re.compile(r'source_class\s*[:=]\s*["\']?external_(human|data)\b'),
     "source_class: external_*"),
    (re.compile(r'validated\s*[:=]\s*["\']?(true|yes|on)\b', re.IGNORECASE), "validated: true"),
    (re.compile(r'evidence_type\s*[:=]\s*["\']?(anecdotal|data-supported|test-validated|'
                r'launch-validated)\b'), "evidence_type above speculation"),
]


def _apply_edits(tool_name, tool_input, on_disk: str) -> str:
    """The file AS IT WOULD BE after the tool call. An Edit's new_string alone hides the key it
    replaces the value of (2026-09-11, A12). Types are checked first: a list where a string
    belongs is refused, not stringified (A16)."""
    hi.written_content(tool_input)
    if tool_name in ("Write", "mcp__filesystem__write_file"):
        return str(tool_input.get("content", "") or "")
    text = on_disk
    if tool_name == "Edit":
        old, new = str(tool_input.get("old_string", "")), str(tool_input.get("new_string", ""))
        return text.replace(old, new) if old else text + "\n" + new
    edits = tool_input.get("edits") or []
    for e in edits:
        if not isinstance(e, dict):
            continue
        old = str(e.get("old_string", e.get("oldText", "")))
        new = str(e.get("new_string", e.get("newText", "")))
        text = text.replace(old, new) if old else text + "\n" + new
    return text


def _walk(node, hits: list) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            key = str(k).strip().lower()
            if key in _FORBIDDEN_VALUES and str(v).strip().lower() in _FORBIDDEN_VALUES[key]:
                hits.append("evidence_type above speculation" if key == "evidence_type"
                            else f"{key}: {str(v).strip()}")
            elif key == "validated" and (v is True or truthy(v)):
                hits.append("validated: true")
            _walk(v, hits)
    elif isinstance(node, list):
        for v in node:
            _walk(v, hits)


def forbidden_in(text: str) -> list:
    """Parsed when PyYAML is present (every spelling YAML allows), regex when it is not."""
    hits: list = []
    if _yaml is not None:
        try:
            for doc in _yaml.safe_load_all(text):
                _walk(doc, hits)
            return sorted(set(hits))
        except _yaml.YAMLError:
            pass  # unparseable YAML: fall through to the regex, which still sees the plain form
    return [label for rx, label in FORBIDDEN if rx.search(text)]


_CANVAS_DIRS = ("/.claude/canvas/", "/.claude/diamonds/",
                "/mycelium-state/canvas/", "/mycelium-state/diamonds/")


def _canvas_target(r) -> bool:
    """A canvas or diamonds YAML file, by REAL path, inside the project or not: an autonomous
    run fabricating evidence into some other project's canvas is still fabrication."""
    real = ("/" + r.real.replace("\\", "/")).lower()
    return any(d in real for d in _CANVAS_DIRS) and real.endswith((".yml", ".yaml"))


def deny(hits):
    reason = (
        "Mycelium autonomous-evidence-guard: BLOCKED -- a declared autonomous "
        "run cannot write " + ", ".join(hits) + " to the canvas. No human or "
        "external source answered in this run, so this evidence would be "
        "fabricated (opp-011 Stage A 2026-06-11: a sub-Fable-5 model fabricated "
        "external_human results and did not know it). Permitted: source_class: "
        "internal_simulated, evidence_type: speculation, validated: false. If a "
        "HUMAN is actually present, this run is NOT autonomous -- unset "
        "MYCELIUM_AUTONOMOUS_RUN and remove `autonomous: true` from "
        "diamonds/active.yml, then retry."
        + ("" if _yaml is not None else " (PyYAML absent: regex scan only.)")
    )
    hi.decision("deny", reason)


def _judge_file_write(tool_name, tool_input, r) -> None:
    on_disk = ""
    if r.exists:
        try:
            with open(r.real, encoding="utf-8", errors="replace") as fh:
                on_disk = fh.read()
        except OSError:
            on_disk = ""
    result = _apply_edits(tool_name, tool_input, on_disk)
    active_files = (".claude/diamonds/active.yml", "mycelium-state/diamonds/active.yml")
    if (r.rel or "").lower() in active_files \
            and _autonomous_in_text(on_disk) and not _autonomous_in_text(result):
        hi.decision("deny", "Mycelium autonomous-evidence-guard: BLOCKED -- this write removes "
                            "`autonomous: true` from diamonds/active.yml. An autonomous run "
                            "cannot un-declare itself; a person ends it (adversarial pass "
                            "2026-09-11, A15).")
    hits = forbidden_in(result)
    if hits:
        deny(hits)


@hi.fail_closed("autonomous-evidence-guard")
def main():
    project_dir = (sys.argv[1] if len(sys.argv) > 1
                   else os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
    data = hi.read_input()
    tool_name = str(data.get("tool_name") or "")
    tool_input = data.get("tool_input") or {}
    if not autonomous_active(project_dir):
        sys.exit(0)
    hi.guard_state_check("autonomous-evidence-guard", tool_name, tool_input, project_dir)
    if tool_name == "Bash":
        cmd = str(tool_input.get("command", "") or "")
        scan = hi.bash_write_targets(cmd, project_dir)
        if any(_canvas_target(t) for t in scan.targets) or scan.opaque:
            # a command is one line, so the anchored YAML regexes cannot see it: loose forms here
            hits = [label for rx, label in _LOOSE_FORBIDDEN if rx.search(cmd)]
            if hits or scan.opaque:
                opaque = "; ".join(scan.opaque[:2])
                deny(hits or [f"a canvas write the guard cannot read ({opaque})"])
        sys.exit(0)
    for k, pth in hi.target_paths(tool_input):
        r = hi.resolve(pth, project_dir, key=k)
        if _canvas_target(r):
            _judge_file_write(tool_name, tool_input, r)
    sys.exit(0)


if __name__ == "__main__":
    main()
