#!/usr/bin/env python3
"""Lesson triggers: a lesson already on record, shown at the tool call it is about (v0.327.0).

WHY. A project's lessons live in its corrections log and memory files, and the agent
starts every session fresh. On the dogfood project 86 of 96 corrections over a month
repeated a lesson already written down, and the corrections file was opened in 12 of 71
sessions. Builders outside the project describe the same thing in their own posts: the
rule sat in CLAUDE.md or a memory file, and the agent made the mistake again. A replay of
those 86 repeats found that showing the matching lesson at the moment of the call would
have reached more of them than any other fix tried, at twice the hand-built checks.

WHAT IT DOES. Off unless `MYCELIUM_LESSON_TRIGGERS=on`. When on, before a tool call it
reads `.claude/memory/lesson-triggers.yml` in the project. Each entry is one lesson as a
RULE LINE (what to do instead) with a `match` on the call. The hook shows the matching
rule lines, at most three, and the call runs. An entry with `refuse: true` stops the call,
with its rule line as the reason; that is for a match that is itself the mistake.

MATCHING. `match.tools` lists the tools. Each other key applies to the tools that carry
it: `command` (Bash), `path` and `content` (Write, Edit, MultiEdit), `url` (WebFetch, the
URL; WebSearch, the query). Every key that applies to the call's tool must match, as a
Python regular expression, case-insensitive and multi-line; keys that do not apply are
ignored, and an entry with none that applies does not match. A pattern that does not
compile is skipped.

PRIVACY. Only the rule line is shown; it reaches the runtime vendor as part of the
session. `--check FILE` reports any rule line that carries a handle or an address, so a
line naming a person can be found before it is shown.

FIRE LOG. Called with `--with-detail`, a second line follows the JSON: the tool and the ids
of the lessons shown or refused, which the hook writes to its fire log (v0.327.1).

FAILS OPEN. Any error means no output: this runs before every matching call, and a
broken hook must not stop the agent's work. Listed `continue` in
hooks/pretooluse-on-failure.txt.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ENV = "MYCELIUM_LESSON_TRIGGERS"
TRIGGERS = Path(".claude/memory/lesson-triggers.yml")
MAX_SHOWN = 3
FLAGS = re.IGNORECASE | re.MULTILINE

#: Which call fields each match key reads, per tool.
_KEY_TOOLS = {
    "command": {"Bash"},
    "path": {"Write", "Edit", "MultiEdit"},
    "content": {"Write", "Edit", "MultiEdit"},
    "url": {"WebFetch", "WebSearch"},
}

#: A handle, an address or a profile path in a rule line: what `--check` reports.
_IDENTIFIER = re.compile(
    r"(?<![\w/])(u/[A-Za-z0-9_-]{3,}|@[A-Za-z0-9_][\w.-]*|[\w.+-]+@[\w-]+\.[\w.]+)")


def enabled(environ=os.environ) -> bool:
    return str(environ.get(ENV, "")).strip().lower() == "on"


def read_lessons(path: Path) -> tuple[list[dict], str | None]:
    """(lessons, problem). A missing file is no lessons and no problem. A file that exists and
    cannot be read or parsed is no lessons AND a problem, which the hook says out loud: switched
    on with a broken file, nothing would be shown, and silence would read as nothing matching."""
    if not path.is_file():
        return [], None
    try:
        import yaml  # noqa: PLC0415 -- only needed when switched on
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as e:  # noqa: BLE001 -- reported to the agent by main(), never raised
        return [], f"{type(e).__name__}: {str(e).splitlines()[0] if str(e) else ''}"
    lessons = data.get("lessons") if isinstance(data, dict) else None
    found = [x for x in lessons or [] if isinstance(x, dict) and isinstance(x.get("match"), dict)]
    return found, None


def load(path: Path) -> list[dict]:
    """The lessons in the file, or [] when it is missing or unreadable."""
    return read_lessons(path)[0]


def _text(value) -> str:
    return value if isinstance(value, str) else ""


def _edits_written(tool_input: dict) -> str:
    edits = tool_input.get("edits")
    if not isinstance(edits, list):
        return ""
    return "\n".join(_text(e.get("new_string")) for e in edits if isinstance(e, dict))


#: For each tool, how a match key's text is read from the call's input.
_FIELDS = {
    "Bash": lambda i: {"command": _text(i.get("command"))},
    "Write": lambda i: {"path": _text(i.get("file_path")), "content": _text(i.get("content"))},
    "Edit": lambda i: {"path": _text(i.get("file_path")), "content": _text(i.get("new_string"))},
    "MultiEdit": lambda i: {"path": _text(i.get("file_path")), "content": _edits_written(i)},
    "WebFetch": lambda i: {"url": _text(i.get("url"))},
    "WebSearch": lambda i: {"url": _text(i.get("query"))},
}


def call_fields(tool: str, tool_input: dict) -> dict[str, str]:
    """What a match key reads from this call; {} for a tool it does not read."""
    read = _FIELDS.get(tool)
    return read(tool_input) if read else {}


def matches(lesson: dict, tool: str, fields: dict[str, str]) -> bool:
    match = lesson["match"]
    tools = match.get("tools")
    if not isinstance(tools, list) or tool not in tools:
        return False
    applied = 0
    for key, tools_for_key in _KEY_TOOLS.items():
        pattern = match.get(key)
        if not isinstance(pattern, str) or tool not in tools_for_key:
            continue
        try:
            if not re.search(pattern, fields.get(key, ""), FLAGS):
                return False
        except re.error:
            return False
        applied += 1
    return applied > 0


def decide(lessons: list[dict], tool: str, tool_input: dict) -> tuple[list[dict], list[dict]]:
    """(refused, shown): the lessons this call meets."""
    fields = call_fields(tool, tool_input)
    if not fields:
        return [], []
    hit = [x for x in lessons if isinstance(x.get("rule"), str) and matches(x, tool, fields)]
    refused = [x for x in hit if x.get("refuse") is True]
    shown = [x for x in hit if x.get("refuse") is not True]
    return refused, shown


_REFUSED = ("MYCELIUM LESSON ON RECORD: REFUSED. This call repeats a mistake already recorded "
            "in this project. Do it the way the lesson says and run it again:\n")
_SHOWN = ("MYCELIUM LESSON ON RECORD (the call still runs). This call matches a lesson already "
          "recorded in this project:\n")


def put_forward(refused: list[dict], shown: list[dict]) -> tuple[list[dict], list[dict]]:
    """The lessons the agent is actually shown: at most MAX_SHOWN, refusals first."""
    refused = refused[:MAX_SHOWN]
    return refused, shown[:MAX_SHOWN - len(refused)]


def output(refused: list[dict], shown: list[dict]) -> dict | None:
    refused, shown = put_forward(refused, shown)
    if refused:
        lines = [f"  - {x['rule']}" for x in refused]
        lines += [f"  Also on record: {x['rule']}" for x in shown]
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                       "permissionDecision": "deny",
                                       "permissionDecisionReason": _REFUSED + "\n".join(lines)}}
    if shown:
        body = _SHOWN + "\n".join(f"  - {x['rule']}" for x in shown)
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": body}}
    return None


def fire_detail(tool: str, refused: list[dict], shown: list[dict]) -> str:
    """The fire log's detail (v0.327.1): the tool and the ids of the lessons put in front of the
    agent, never the call or the rule line. Without the ids a fire log can say a lesson was shown
    but not which, so nobody can tell whether the lesson behind a later repeat had been shown."""
    refused, shown = put_forward(refused, shown)
    parts = [f"tool={tool}"]
    for label, found in (("refused", refused), ("shown", shown)):
        if found:
            parts.append(f"{label}=" + ",".join(str(x.get("id") or "?") for x in found))
    return " ".join(parts)


def unreadable(problem: str) -> dict:
    body = (f"MYCELIUM LESSON TRIGGERS: {TRIGGERS} could not be read ({problem}), so no lesson is "
            "shown until it is fixed. `lesson_triggers.py --check` names the error.")
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": body}}


def project_dir(payload: dict) -> Path:
    root = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()
    return Path(str(root))


def check(path: Path) -> list[str]:
    """Rule lines that carry a handle or an address, as `id: line`."""
    return [f"{x.get('id', '?')}: {x['rule']}" for x in load(path)
            if isinstance(x.get("rule"), str) and _IDENTIFIER.search(x["rule"])]


def main(argv: list[str]) -> int:
    if argv[:1] == ["--check"] and argv[1:]:
        problem = read_lessons(Path(argv[1]))[1]
        if problem:
            print(f"cannot read {argv[1]}: {problem}")
            return 2
        found = check(Path(argv[1]))
        for line in found:
            print(f"rule line names a person or an address: {line}")
        return 1 if found else 0
    if not enabled():
        return 0
    try:
        payload = json.load(sys.stdin)
        tool = payload.get("tool_name")
        tool_input = payload.get("tool_input")
        if not isinstance(tool, str) or not isinstance(tool_input, dict):
            return 0
        lessons, problem = read_lessons(project_dir(payload) / TRIGGERS)
        if problem:
            result, detail = unreadable(problem), f"tool={tool} unreadable"
        else:
            found = decide(lessons, tool, tool_input)
            result, detail = output(*found), fire_detail(tool, *found)
    except Exception:  # noqa: BLE001 -- fails open
        return 0
    if result:
        print(json.dumps(result))
        if "--with-detail" in argv:  # the hook's second line: what goes in the fire log
            print(detail)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
