#!/usr/bin/env python3
"""Content in key position, caught while the author still holds the reason.

THE WRITE-TIME HALF of the near-duplicate-keys row (the sweep half shipped in 0.212.0 as
`check_key_shape.py --stems`). Founder, 2026-09-02, on reading the scan-shaped proposal: a
post-hoc scan finds a collision AFTER the key exists, which forces a second decision nobody
wanted; a PreToolUse guard catches it while the author is still holding the reason and the
correct spelling is one keystroke away. The evidence is the pass that filed the parent row:
the session that removed 19 date-in-key names introduced `promoted_2026_09_02` inside the
same commit, caught only by a manual --strict run afterwards.

WHAT IT WATCHES. Write/Edit/MultiEdit into `.claude/canvas/**` and `.claude/diamonds/**`.
The text being written is scanned line by line for YAML keys (it is a fragment, so it is
NOT parsed as a document; an Edit's new_string is rarely valid YAML on its own). A key is
reported when

  1. its name carries a date or an entity id — `check_key_shape.DATE_IN_KEY` and
     `ENTITY_IN_KEY`, the same two regexes the sweep uses, so the guard and the sweep
     disagree on nothing; or
  2. its STEM (`check_key_shape.stem_of`) already exists in the target file under a
     different spelling — `reply-sent` beside `reply_sent`, `Status` beside `status` —
     and the exact spelling being written is not already in the file.

Bare date keys (`2026-06-11:`) are skipped on purpose: YAML reads them as dates, not
strings, so the sweep cannot see them either, and a guard that fires where the sweep is
blind would be a second rule wearing the first one's name.

WHAT IT DOES NOT DO. Advisory, never a block: the message names the plain spelling to use
and the `notes[]` form the convention prescribes, and the write goes ahead. The sweep stays
as the retrofit path for keys that were already there. It cannot see a heredoc (the shell
half of the absence guard exists for that reason; this guard has none yet, and the sweep
covers what the heredoc wrote). It reads the target file to find stem collisions, so a file
that does not exist or does not parse contributes no collisions, only the regex half.

Contract: exit 0 silent = nothing to say. exit 0 + JSON additionalContext = warn. Logs one
line per fire to `.claude/state/key-shape-guard-log.jsonl` through the absence guard's
writer, so the action rate and the re-write ratio are computable the same way.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from absence_claim_guard import _log, _payload_text
from check_key_shape import DATE_IN_KEY, ENTITY_IN_KEY, stem_of

_WATCHED_PATH = re.compile(r"/\.claude/(canvas|diamonds)/")

#: A YAML mapping key at the start of a line, optionally as a list item's first key.
#: Names only: letters, digits, underscore, hyphen. Prose inside a block scalar that
#: happens to start `word:` matches too; the two regexes and the collision test are what
#: keep that from firing, since prose seldom starts with a dated identifier.
_KEY_LINE = re.compile(r"^\s*(?:-\s+)?(?P<key>[A-Za-z_][A-Za-z0-9_-]*)\s*:(?:\s|$)")
_BARE_DATE = re.compile(r"^(19|20)\d{2}[_-]?\d{2}[_-]?\d{2}$")
_MAX_DEPTH = 12
_NAMED = 5

_MESSAGE = (
    "MYCELIUM KEY-SHAPE GUARD (advisory): this write puts content in key position.\n"
    "{quoted}\n"
    "  A date or an entity id in a key name is a sentence wearing a field's clothes: no "
    "schema can declare it, nothing can sort or age it, and a second spelling of a field "
    "that already exists is a field nothing will ever read as one. Keep the plain key and "
    "put the date or id in the value:\n"
    "    notes:\n      - date: {today}\n        kind: <plain_key>\n        note: ...\n"
    "  The write goes ahead. `check_key_shape.py --stems` finds what this missed."
)


_BLOCK_SCALAR = re.compile(r":\s*[|>][-+]?\s*(#.*)?$")
_OPENS_QUOTE = re.compile(r':\s*"(?:[^"\\]|\\.)*$')
_CLOSES_QUOTE = re.compile(r'(?:^|[^\\])"\s*$')


def keys_in(text: str) -> list[str]:
    """Key names in a YAML fragment, in order, duplicates kept.

    Lines inside a block scalar (`summary: >-` and everything indented deeper) or an
    unclosed double-quoted string are prose, not keys. The replay that calibrated this
    guard (60 dogfood commits, 2026-09-10..15) had four of seven spelling findings come
    from `Date:` and `CLASSIFICATION:` inside a task's prose. A fragment that starts
    mid-scalar cannot be told apart from keys; that residue is accepted.
    """
    out: list[str] = []
    scalar_indent: int | None = None
    in_quote = False
    for line in text.splitlines():
        if in_quote:
            in_quote = not _CLOSES_QUOTE.search(line)
            continue
        indent = len(line) - len(line.lstrip(" "))
        if scalar_indent is not None:
            if not line.strip() or indent > scalar_indent:
                continue
            scalar_indent = None
        m = _KEY_LINE.match(line)
        if not m:
            continue
        out.append(m.group("key"))
        if _BLOCK_SCALAR.search(line):
            scalar_indent = indent
        elif _OPENS_QUOTE.search(line):
            in_quote = True
    return out


def _file_spellings(path: str) -> dict[str, set[str]]:
    """stem -> spellings already in the target file; empty when unreadable or unparseable."""
    try:
        doc = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except Exception:                      # noqa: BLE001 — a missing/unparseable target has no collisions
        return {}
    out: dict[str, set[str]] = {}
    _walk(doc, out)
    return out


def _walk(node, out: dict[str, set[str]], depth: int = 0) -> None:
    if depth > _MAX_DEPTH:
        return
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(k, str):
                out.setdefault(stem_of(k), set()).add(k)
            _walk(v, out, depth + 1)
    elif isinstance(node, list):
        for v in node:
            _walk(v, out, depth + 1)


def findings(text: str, spellings: dict[str, set[str]] | None = None) -> list[str]:
    """One line per offending key in `text`. `spellings` is the target file's stem map."""
    spellings = spellings or {}
    out: list[str] = []
    seen: set[str] = set()
    for key in keys_in(text):
        if key in seen or _BARE_DATE.match(key):
            continue
        seen.add(key)
        if DATE_IN_KEY.search(key) or ENTITY_IN_KEY.search(key):
            plain = stem_of(key) or "<plain key>"
            out.append(f"`{key}:` carries a date or an entity id; the plain key is `{plain}`")
            continue
        # The plain spelling IS the recommendation: writing `posted` into a file that
        # holds `POSTED_2026_08_10` is the fix, not a second spelling of it.
        if key == stem_of(key):
            continue
        # Case-only variants are left to the sweep: in the calibration replay every
        # `Date:`/`CLASSIFICATION:` collision was prose in a fragment that began mid-scalar,
        # and a guard that fires on prose four times in five is read past by the fifth.
        others = {o for o in spellings.get(stem_of(key), set()) if o.lower() != key.lower()}
        if others and key not in spellings.get(stem_of(key), set()):
            have = ", ".join(f"`{o}`" for o in sorted(others)[:_NAMED])
            out.append(f"`{key}:` is a new spelling of a stem this file already writes as {have}")
    return out


def scan_for(payload: dict) -> list[str]:
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return []
    path = tool_input.get("file_path")
    if not isinstance(path, str) or not _WATCHED_PATH.search(path):
        return []
    text = _payload_text(str(payload.get("tool_name") or ""), tool_input)
    if not text.strip():
        return []
    return findings(text, _file_spellings(path))


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:                      # noqa: BLE001 — must never break a write
        return 0
    hits = scan_for(payload)
    if not hits:
        return 0
    quoted = "\n".join(f"    > {h}" for h in hits[:_NAMED])
    if len(hits) > _NAMED:
        quoted += f"\n    ... and {len(hits) - _NAMED} more in this write."
    tool_input = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    _log("key-shape-guard", len(hits), hits[0], hashlib.sha256(hits[0].encode()).hexdigest()[:10], {
        "file": os.path.basename(str(tool_input.get("file_path") or "")),
        "session": str(payload.get("session_id") or ""),
        "text": _payload_text(str(payload.get("tool_name") or ""), tool_input)})
    today = datetime.now(UTC).date().isoformat()
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": _MESSAGE.format(quoted=quoted, today=today)}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
