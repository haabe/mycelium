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
covers what the heredoc wrote). A Bash-matcher hook cannot see what a script writes either,
so `safe_replace.py`, the framework's own tool for scripted multi-file edits, runs this
check itself (`new_key_findings`, `message`) on every canvas or diamonds target it writes,
and warns on stderr the same way; the edit goes ahead there too. It reads the target file
to find stem collisions, so a file that does not exist or does not parse contributes no
collisions, only the regex half.

EVIDENCE SOURCES WITHOUT THEIR CLASSES (v0.336.0). The operating contract's HARD RULE says a
canvas write that adds `provenance.evidence_sources` adds the parallel `source_classes` array in
the same edit, and until 0.336.0 nothing checked it at write time: `check_source_class_fidelity.py`
reports unequal arrays at session start, after the reason for each class is gone. So the same
write is also read as the file it leaves: the target's text with the Edit or MultiEdit applied
(a Write is its content), parsed. A mapping with an `evidence_sources` list that this write
added or changed, and that carries fewer `source_classes` than sources, is named. Not named, as
the fidelity check does not: one class for every source, written as the singular `source_class`
or as a one-item `source_classes` list, and a block with `alignment_reviewed`. A write whose
result does not parse is not read for this; the session-start sweep still is. Advisory like the
rest: the write goes ahead.

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
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from absence_claim_guard import _log, _payload_text
from check_key_shape import carries_date_or_id, stem_of

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
    return key_findings(keys_in(text), spellings)


def new_key_findings(path: str, before: str, after: str) -> list[str]:
    """The findings for keys that `after` holds and `before` does not, for a whole-file edit
    of `path` (safe_replace.py). Empty when `path` is not under .claude/canvas or
    .claude/diamonds. A key already in the file is not this edit's to answer for, so it is
    left to the sweep; `path` is read for its existing spellings as the hook reads its target.
    """
    if not _WATCHED_PATH.search(path.replace(os.sep, "/")):
        return []
    had = set(keys_in(before))
    return key_findings([k for k in keys_in(after) if k not in had], _file_spellings(path))


def message(hits: list[str]) -> str:
    """The advisory text the hook gives, for `hits` (at most _NAMED quoted)."""
    quoted = "\n".join(f"    > {h}" for h in hits[:_NAMED])
    if len(hits) > _NAMED:
        quoted += f"\n    ... and {len(hits) - _NAMED} more in this write."
    today = datetime.now(timezone.utc).date().isoformat()
    return _MESSAGE.format(quoted=quoted, today=today)


def key_findings(keys: list[str], spellings: dict[str, set[str]] | None = None) -> list[str]:
    """One line per offending key name in `keys`, in order, each name once."""
    spellings = spellings or {}
    out: list[str] = []
    seen: set[str] = set()
    for key in keys:
        if key in seen or _BARE_DATE.match(key):
            continue
        seen.add(key)
        if carries_date_or_id(key):
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


_PROVENANCE_MESSAGE = (
    "MYCELIUM PROVENANCE CHECK (advisory): this write leaves evidence_sources without a "
    "source_classes entry for each.\n"
    "{quoted}\n"
    "  Evidence writes carry `source_classes` (HARD RULE, agent-operating-contract): add one "
    "class per source in this same edit, in the same order, while you know where each source "
    "came from. Do not infer a class from the source's text afterwards. Where every source is "
    "the same class, the singular `source_class` says so. The write goes ahead; "
    "`check_source_class_fidelity.py` reports what is still unequal."
)


def _after_text(tool_name: str, tool_input: dict, before: str) -> str | None:
    """The target file's text as this write leaves it; None when it cannot be worked out."""
    if tool_name == "Write":
        v = tool_input.get("content")
        return v if isinstance(v, str) else None
    edits = ([tool_input] if tool_name == "Edit" else tool_input.get("edits")
             if tool_name == "MultiEdit" else None)
    if not isinstance(edits, list):
        return None
    text = before
    for e in edits:
        old, new = (e.get("old_string"), e.get("new_string")) if isinstance(e, dict) else (0, 0)
        if not isinstance(old, str) or not isinstance(new, str) or old not in text:
            return None
        text = text.replace(old, new) if e.get("replace_all") else text.replace(old, new, 1)
    return text


def _blocks(node, ident: str = "", depth: int = 0) -> list[tuple[str, str, int, int]]:
    """(id, signature, sources, classes) for each mapping holding an `evidence_sources` list
    whose classes fall short of it, in the fidelity check's terms."""
    out: list[tuple[str, str, int, int]] = []
    if depth > _MAX_DEPTH:
        return out
    if isinstance(node, dict):
        ident = str(node.get("id") or ident)
        sources, classes = node.get("evidence_sources"), node.get("source_classes")
        if isinstance(sources, list):
            n = len(classes) if isinstance(classes, list) else 0
            one_class = node.get("source_class") is not None or n == 1
            if n < len(sources) and not one_class and not node.get("alignment_reviewed"):
                sig = json.dumps([sources, classes], sort_keys=True, default=str)
                out.append((ident or "a block", sig, len(sources), n))
        for v in node.values():
            out += _blocks(v, ident, depth + 1)
    elif isinstance(node, list):
        for v in node:
            out += _blocks(v, ident, depth + 1)
    return out


def provenance_findings(before: str, after: str) -> list[str]:
    """One line per provenance block short of classes that `after` holds and `before` did not
    (as the same sources and classes). Empty when `after` does not parse."""
    try:
        doc = yaml.safe_load(after)
    except yaml.YAMLError:
        return []  # the session-start sweep reads the file once it parses
    try:
        had = {sig for _, sig, _, _ in _blocks(yaml.safe_load(before) if before else None)}
    except yaml.YAMLError:
        had = set()
    return [f"{ident}: {n_src} evidence_sources, {n_cls} source_classes"
            for ident, sig, n_src, n_cls in _blocks(doc) if sig not in had]


def provenance_for(payload: dict) -> list[str]:
    """`provenance_findings` for a hook payload: a write into .claude/canvas or diamonds."""
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return []
    path = tool_input.get("file_path")
    if not isinstance(path, str) or not _WATCHED_PATH.search(path):
        return []
    try:
        before = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        before = ""  # a new file: everything in it is this write's
    after = _after_text(str(payload.get("tool_name") or ""), tool_input, before)
    return provenance_findings(before, after) if after is not None else []


def provenance_message(hits: list[str]) -> str:
    quoted = "\n".join(f"    > {h}" for h in hits[:_NAMED])
    if len(hits) > _NAMED:
        quoted += f"\n    ... and {len(hits) - _NAMED} more in this write."
    return _PROVENANCE_MESSAGE.format(quoted=quoted)


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
    if not isinstance(payload, dict):
        return 0
    hits, short = scan_for(payload), provenance_for(payload)
    if not hits and not short:
        return 0
    tool_input = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    first = (hits or short)[0]
    _log("key-shape-guard", len(hits) + len(short), first,
         hashlib.sha256(first.encode()).hexdigest()[:10], {
             "file": os.path.basename(str(tool_input.get("file_path") or "")),
             "session": str(payload.get("session_id") or ""),
             "text": _payload_text(str(payload.get("tool_name") or ""), tool_input)})
    said = [message(hits)] if hits else []
    if short:
        said.append(provenance_message(short))
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": "\n\n".join(said)}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
