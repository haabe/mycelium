#!/usr/bin/env python3
"""_hook_input.py — one reading of a tool call for every blocking hook.

WHY (2026-09-11, blind adversarial pass; dogfood evals/security/2026-09-11-*). Six PreToolUse
hooks each read the tool call their own way, and one reviewer got past all six with the same
handful of moves: a path with `..`, a symlink, or the other case on a case-insensitive disk; a
`file`, `path` or `notebook_path` key the hook did not read; a MultiEdit whose edits[] nobody
scanned; a Bash command with `./`, `$PWD`, an absolute path, a newline, a `cd`, or a writer the
regex did not know (perl -i, dd of=, ed, awk -i inplace, rsync); a list where a string was
expected, which crashed the helper into exit 1, which the harness reads as allow. Each hook was
fixable alone; six copies of the fix is how the next pass finds the seventh copy.

WHAT A HOOK GETS (stdlib only):
  read_input()                    -> dict, or BadInputError (callers deny on it)
  target_paths(ti)                -> [(key, path)] every path-shaped value the tool would write
  written_content(ti)             -> str everything the tool would put on disk, edits[] included
  resolve(path, project_dir)      -> Resolved(real, rel, inside, exists, size)
  bash_write_targets(cmd, dir)    -> BashScan(targets, opaque, mentions)
  is_guard_state(rel)             -> the off-switch file this path names, or None
  guard_state_check(...)          -> `ask` the human when a tool call writes an off-switch
  decision(kind, reason)          -> prints the PreToolUse JSON and exits 0
  fail_closed(name)               -> decorator: any exception is a deny that names it

GUARD STATE. upstream.json, manifest.yml, active-execution.json and the two ack files each
switch a blocking hook off, and the reviewer wrote every one of them from inside a tool call. A
deny would break the designed flows (the brownfield gate itself tells the agent to write the ack
after the user answers), so a write to guard state returns `ask`: the harness puts the call in
front of the human and the agent cannot answer for them. MYCELIUM_GUARD_STATE_EDIT=1 in the
harness process (not in an agent's Bash) skips the ask for a person running setup.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field

PATH_KEYS = ("file_path", "file", "path", "notebook_path", "source", "destination", "target")
CONTENT_KEYS = ("content", "new_string", "newText", "new_source", "text")
GUARD_STATE_REL = (
    ".claude/state/upstream.json",
    ".claude/manifest.yml",
    ".claude/state/active-execution.json",
    ".claude/state/discovery-skip-ack",
    ".claude/state/brownfield-ack",
)
_QUOTED_MIN = 2


class BadInputError(Exception):
    """The tool call is not the documented shape; the hook denies, never guesses."""


@dataclass
class Resolved:
    given: str
    real: str
    rel: str | None
    inside: bool
    exists: bool
    size: int
    key: str = ""


@dataclass
class BashScan:
    targets: list[Resolved] = field(default_factory=list)
    opaque: list[str] = field(default_factory=list)
    mentions: list[str] = field(default_factory=list)


# ---------------------------------------------------------------- input

def read_input(stream=None) -> dict:
    raw = (stream or sys.stdin).read()
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise BadInputError(f"stdin is not JSON ({type(exc).__name__})") from exc
    if not isinstance(data, dict):
        raise BadInputError("hook input is not an object")
    return data


def _text(value, key: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise BadInputError(f"tool_input.{key} is {type(value).__name__}, not a string")
    return value


def target_paths(tool_input) -> list[tuple[str, str]]:
    """(key, path) for every path-shaped field. A non-string path is BadInputError."""
    if not isinstance(tool_input, dict):
        raise BadInputError("tool_input is not an object")
    out = [(k, _text(tool_input.get(k), k)) for k in PATH_KEYS if k in tool_input]
    return [(k, v) for k, v in out if v]


def _edit_texts(edits) -> list[str]:
    if not isinstance(edits, list):
        raise BadInputError("tool_input.edits is not a list")
    out = []
    for i, e in enumerate(edits):
        if not isinstance(e, dict):
            raise BadInputError(f"tool_input.edits[{i}] is not an object")
        out.extend(_text(e.get(k), f"edits[{i}].{k}") for k in ("new_string", "newText") if k in e)
    return out


def written_content(tool_input) -> str:
    """Everything the tool would put on disk, joined; a list where a string belongs is BadInput."""
    if not isinstance(tool_input, dict):
        raise BadInputError("tool_input is not an object")
    parts = [_text(tool_input.get(k), k) for k in CONTENT_KEYS if k in tool_input]
    if "edits" in tool_input:
        parts.extend(_edit_texts(tool_input.get("edits")))
    return "\n".join(p for p in parts if p)


# ---------------------------------------------------------------- paths

_CASE_CACHE: dict[str, bool] = {}
_FOLD = False


def case_insensitive_fs(project_dir: str) -> bool:
    """One probe per project dir, no writes: is the other case of the path the same file?"""
    if project_dir in _CASE_CACHE:
        return _CASE_CACHE[project_dir]
    ans = False
    try:
        swapped = project_dir.swapcase()
        if swapped != project_dir and os.path.exists(swapped):
            ans = os.path.samefile(project_dir, swapped)
    except OSError:
        ans = False
    _CASE_CACHE[project_dir] = ans
    return ans


def _fold(s: str) -> str:
    return s.lower() if _FOLD else s


def _nearest_real(p: str) -> str:
    """realpath of the deepest existing ancestor, with the missing tail appended unchanged."""
    head, tail = p, []
    while head and head != "/" and not os.path.exists(head):
        head, last = os.path.split(head)
        tail.insert(0, last)
    base = os.path.realpath(head or "/")
    return os.path.join(base, *tail) if tail else base


def resolve(path: str, project_dir: str, key: str = "") -> Resolved:
    """Real location of `path` and whether it sits inside the project's real root."""
    global _FOLD  # noqa: PLW0603 — one probe per process, keyed on the project dir
    proj_real = os.path.realpath(os.path.abspath(project_dir))
    _FOLD = case_insensitive_fs(proj_real)
    p = os.path.expanduser(path)
    if not os.path.isabs(p):
        p = os.path.join(proj_real, p)
    p = os.path.abspath(p)
    exists = os.path.lexists(p)
    real = os.path.realpath(p) if exists else _nearest_real(p)
    root = _fold(proj_real)
    inside = _fold(real) == root or _fold(real).startswith(root + os.sep)
    rel = os.path.relpath(real, proj_real) if inside else None
    if rel == ".":
        rel = ""
    size = os.path.getsize(p) if exists and os.path.isfile(p) else 0
    return Resolved(given=path, real=real, rel=rel, inside=inside, exists=exists,
                    size=size, key=key)


def is_guard_state(rel: str | None) -> str | None:
    if rel is None:
        return None
    r = _fold(rel)
    return next((g for g in GUARD_STATE_REL if r == _fold(g)), None)


def human_override() -> bool:
    val = str(os.environ.get("MYCELIUM_GUARD_STATE_EDIT", "")).strip().lower()
    return val in ("1", "true", "yes")


# ---------------------------------------------------------------- bash

_TOK = r"(?:'[^']*'|\"[^\"]*\"|[^\s;&|<>()]+)"
_SEG_SPLIT = re.compile(r"(?:\r?\n|&&|\|\||;|\|(?!\|))")
_CD = re.compile(rf"^\s*cd\s+(?P<dir>{_TOK})")
_PATHISH = re.compile(_TOK)
_WRITERS = [
    (re.compile(rf">{{1,2}}\|?\s*(?P<t>{_TOK})"), "redirect"),
    (re.compile(rf"\btee\s+(?:-[a-z]+\s+)*(?P<t>{_TOK})"), "tee"),
    (re.compile(rf"\bsed\b.*?\s-[a-zA-Z]*i\b.*\s(?P<t>{_TOK})\s*$"), "sed -i"),
    (re.compile(rf"\bperl\b.*?\s-[a-zA-Z]*i\b.*\s(?P<t>{_TOK})\s*$"), "perl -i"),
    (re.compile(rf"\b(?:cp|mv|install|ln|rsync)\b.*\s(?P<t>{_TOK})\s*$"), "copy/move/link"),
    (re.compile(rf"\b(?:rm|touch|chmod|chown|truncate)\b(?:\s+-\S+)*\s+(?P<t>{_TOK})"),
     "rm/touch/chmod"),
    (re.compile(rf"\bdd\b.*\bof=(?P<t>{_TOK})"), "dd of="),
    (re.compile(rf"\bed\s+(?:-[a-z]+\s+)*(?P<t>{_TOK})"), "ed"),
    (re.compile(rf"\bg?awk\b.*-i\s*inplace.*\s(?P<t>{_TOK})\s*$"), "awk -i inplace"),
    (re.compile(r"\bopen\s*\(\s*(?P<t>'[^']*'|\"[^\"]*\")\s*,\s*['\"][wax]"), "python open()"),
    (re.compile(r"\bwrite_text\s*\("), "python write_text"),
]
_OPAQUE = re.compile(r"\$\(|`|\$\{?[A-Za-z_]")


def _unquote(tok: str) -> str:
    if len(tok) >= _QUOTED_MIN and tok[0] == tok[-1] and tok[0] in "'\"":
        return tok[1:-1]
    return tok


def _norm_token(tok: str, cwd_rel: str) -> str:
    """`./x`, `$PWD/x`, `${PWD}/x`, `$(pwd)/x` -> x, relative to the segment's cwd."""
    t = _unquote(tok)
    t = re.sub(r"^(?:\$\{?PWD\}?|\$\(pwd\))/", "", t)
    t = t.removeprefix("./")
    if not os.path.isabs(t) and cwd_rel:
        t = os.path.normpath(os.path.join(cwd_rel, t))
    return t


def _cd_target(seg: str, cwd_rel: str, project_dir: str) -> str | None:
    m = _CD.match(seg)
    if not m:
        return None
    d = _unquote(m.group("dir"))
    if os.path.isabs(d):
        r = resolve(d, project_dir)
        return r.rel or "" if r.inside else "__outside__"
    return os.path.normpath(os.path.join(cwd_rel, d)) if cwd_rel else d


def _scan_segment(seg: str, cwd_rel: str, project_dir: str, scan: BashScan) -> None:
    for tok in _PATHISH.findall(seg):
        # `f=CLAUDE.md` mentions CLAUDE.md; the assignment form is how a variable target is built
        for part in _unquote(tok).split("="):
            if "/" in part or "." in part:
                scan.mentions.append(_norm_token(part, cwd_rel))
    for rx, label in _WRITERS:
        for m in rx.finditer(seg):
            tgt = m.groupdict().get("t")
            if not tgt:
                scan.opaque.append(label)
                continue
            t = _norm_token(tgt, cwd_rel)
            if _OPAQUE.search(t):
                scan.opaque.append(f"{label} on {t}")
                continue
            scan.targets.append(resolve(t, project_dir, key=f"bash:{label}"))


def bash_write_targets(cmd: str, project_dir: str) -> BashScan:
    """Paths a shell command may write, per segment, with `cd` tracked along the chain."""
    scan = BashScan()
    cwd_rel = ""
    for raw in _SEG_SPLIT.split(cmd or ""):
        seg = raw.strip()
        if not seg:
            continue
        cd = _cd_target(seg, cwd_rel, project_dir)
        if cd is not None:
            cwd_rel = cd
            continue
        _scan_segment(seg, cwd_rel, project_dir, scan)
    return scan


# ---------------------------------------------------------------- output

def decision(kind: str, reason: str) -> None:
    """kind: deny | ask | allow. Prints the PreToolUse JSON and exits 0."""
    sys.stdout.reconfigure(errors="replace")
    if kind == "allow":
        sys.exit(0)
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": kind,
        "permissionDecisionReason": reason,
    }}, ensure_ascii=False))
    sys.exit(0)


def fail_closed(name: str):
    """Decorator: an exception inside a blocking hook is a deny that names it, never exit 1."""
    def wrap(fn):
        def run(*a, **k):
            try:
                return fn(*a, **k)
            except SystemExit:
                raise
            except BadInputError as exc:
                decision("deny", f"Mycelium {name}: refused, tool input is not the documented "
                                 f"shape ({exc}). A guard that cannot read the call does not "
                                 "guess.")
            except Exception as exc:  # noqa: BLE001 — the point: any crash is a deny
                decision("deny", f"Mycelium {name}: refused, the guard crashed "
                                 f"({type(exc).__name__}: {exc}). A crash used to be an allow.")
        return run
    return wrap


def _targets_of(tool_name: str, tool_input, project_dir: str) -> list[Resolved]:
    if tool_name == "Bash":
        cmd = str((tool_input or {}).get("command", "") or "")
        return bash_write_targets(cmd, project_dir).targets
    return [resolve(p, project_dir, key=k) for k, p in target_paths(tool_input)]


def guard_state_check(name: str, tool_name: str, tool_input, project_dir: str) -> None:
    """Shared step: a write to guard state asks the human. Returns when there is nothing to say."""
    if human_override():
        return
    for r in _targets_of(tool_name, tool_input, project_dir):
        g = is_guard_state(r.rel)
        if g:
            decision("ask", f"Mycelium {name}: {g} switches a blocking hook off, and this tool "
                            f"call writes it. A person decides that, not the agent (adversarial "
                            f"pass 2026-09-11). Approve if you asked for it; set "
                            f"MYCELIUM_GUARD_STATE_EDIT=1 in your own shell for setup work.")


_MIN_PURPOSE_WORDS = 3


def _purpose_has_words(doc, text: str) -> bool:
    """A purpose statement with at least three words, at top level (`why:`) or nested under
    `purpose:` (`statement:`, `why:`); regex fallback when PyYAML is absent."""
    if isinstance(doc, dict):
        cands = [doc.get("why", "")]
        purpose = doc.get("purpose")
        if isinstance(purpose, dict):
            cands += [purpose.get("statement", ""), purpose.get("why", "")]
        return any(isinstance(c, str) and len(c.split()) >= _MIN_PURPOSE_WORDS for c in cands)
    m = re.search(r"(?m)^\s*(?:why|statement):\s*(.+)$", text)
    return bool(m and len(m.group(1).split()) >= _MIN_PURPOSE_WORDS)


def has_purpose(project_dir: str) -> bool:
    """purpose.yml carries a purpose statement with words in it. Separate from has_discovery_state,
    which a diamond alone satisfies: an end-to-end dogfood run (v0.244.0) had diamonds and no
    purpose, because /mycelium:start was interrupted, and nothing noticed."""
    try:
        import yaml  # noqa: PLC0415 — optional; _purpose_has_words has a regex fallback
    except ImportError:
        yaml = None
    path = os.path.join(project_dir, ".claude", "canvas", "purpose.yml")
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return False
    try:
        doc = yaml.safe_load(text) if yaml else None
    except ValueError:
        doc = None
    return _purpose_has_words(doc, text)


def has_discovery_state(project_dir: str) -> bool:
    """A populated purpose.yml (a `why` with words in it) or an active diamond with an id.
    2026-09-11: sixty-one spaces in purpose.yml and a one-line `- id: fake` both passed the
    byte-count and grep the gates used; a parse is what a fake has to satisfy now."""
    try:
        import yaml  # noqa: PLC0415 — optional; the regex fallback below runs without it
    except ImportError:
        yaml = None
    root = os.path.join(project_dir, ".claude")
    purpose = os.path.join(root, "canvas", "purpose.yml")
    active = os.path.join(root, "diamonds", "active.yml")
    try:
        with open(purpose, encoding="utf-8") as fh:
            text = fh.read()
        doc = yaml.safe_load(text) if yaml else None
        if _purpose_has_words(doc, text):
            return True
    except (OSError, ValueError, AttributeError):
        pass
    if yaml is not None:
        try:
            with open(active, encoding="utf-8") as fh:
                doc = yaml.safe_load(fh.read())
            diamonds = (doc or {}).get("active_diamonds") if isinstance(doc, dict) else None
            if isinstance(diamonds, list) and any(
                isinstance(d, dict) and d.get("id") for d in diamonds
            ):
                return True
        except (OSError, ValueError, AttributeError):
            pass
    return False


def _line_for(r: Resolved) -> str:
    g = is_guard_state(r.rel)
    where = f"GUARD:{g}" if g else (r.rel if r.inside else f"OUTSIDE:{r.real}")
    return f"{where}\t{int(r.exists)}\t{r.size}"


def cli() -> int:
    """For shell hooks: tool name; one line per target (rel | OUTSIDE:real | GUARD:name |
    OPAQUE:label, tab, exists, tab, size); a `---CONTENT---` line; then the written content."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-dir", default=os.environ.get("CLAUDE_PROJECT_DIR", "."))
    ap.add_argument("--discovery-state", action="store_true",
                    help="exit 0 if discovery has been engaged, 1 if not; reads no stdin")
    ap.add_argument("--purpose-state", action="store_true",
                    help="exit 0 if purpose.yml has a purpose statement, 1 if not; reads no stdin")
    args = ap.parse_args()
    if args.purpose_state:
        return 0 if has_purpose(args.project_dir) else 1
    if args.discovery_state:
        return 0 if has_discovery_state(args.project_dir) else 1
    data = read_input()
    tool = str(data.get("tool_name") or "")
    ti = data.get("tool_input") or {}
    print(tool)
    if tool == "Bash":
        cmd = str(ti.get("command", "") or "") if isinstance(ti, dict) else ""
        scan = bash_write_targets(cmd, args.project_dir)
        for r in scan.targets:
            print(_line_for(r))
        for o in scan.opaque:
            print(f"OPAQUE:{o}\t0\t0")
        print("---CONTENT---")
        sys.stdout.write(cmd)
        return 0
    for k, p in target_paths(ti):
        print(_line_for(resolve(p, args.project_dir, key=k)))
    print("---CONTENT---")
    sys.stdout.write(written_content(ti))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(cli())
    except BadInputError as exc:
        print(f"BADINPUT:{exc}")
        sys.exit(3)
