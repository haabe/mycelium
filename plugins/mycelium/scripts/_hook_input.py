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
import contextlib
import datetime as _dt
import json
import os
import re
import sys
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

PATH_KEYS = ("file_path", "file", "path", "notebook_path", "source", "destination", "target")
CONTENT_KEYS = ("content", "new_string", "newText", "new_source", "text")
GUARD_STATE_REL = (
    ".claude/state/upstream.json",
    ".claude/manifest.yml",
    ".claude/state/active-execution.json",
    ".claude/state/discovery-skip-ack",
    ".claude/state/delivery-skip-ack",
    ".claude/state/scale-lock-ack",
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
# A command word, never part of a flag or a longer word (v0.252.0): `\bln\b` matched the `ln` in
# `grep -ln`, so a read-only search counted as creating a link and the delivery gate refused it.
# A path prefix still matches (`/bin/rm`).
_CMD = r"(?<![-\w.])"
_WRITERS = [
    (re.compile(rf">{{1,2}}\|?\s*(?P<t>{_TOK})"), "redirect"),
    (re.compile(rf"{_CMD}tee\s+(?:-[a-z]+\s+)*(?P<t>{_TOK})"), "tee"),
    (re.compile(rf"{_CMD}sed\b.*?\s-[a-zA-Z]*i\b.*\s(?P<t>{_TOK})\s*$"), "sed -i"),
    (re.compile(rf"{_CMD}perl\b.*?\s-[a-zA-Z]*i\b.*\s(?P<t>{_TOK})\s*$"), "perl -i"),
    (re.compile(rf"{_CMD}(?:cp|mv|install|ln|rsync)\b.*\s(?P<t>{_TOK})\s*$"), "copy/move/link"),
    (re.compile(rf"{_CMD}(?:rm|touch|chmod|chown|truncate)\b(?:\s+-\S+)*\s+(?P<t>{_TOK})"),
     "rm/touch/chmod"),
    (re.compile(rf"{_CMD}dd\b.*\bof=(?P<t>{_TOK})"), "dd of="),
    (re.compile(rf"{_CMD}ed\s+(?:-[a-z]+\s+)*(?P<t>{_TOK})"), "ed"),
    (re.compile(rf"{_CMD}g?awk\b.*-i\s*inplace.*\s(?P<t>{_TOK})\s*$"), "awk -i inplace"),
    (re.compile(r"\bopen\s*\(\s*(?P<t>'[^']*'|\"[^\"]*\")\s*,\s*['\"][wax]"), "python open()"),
    # v0.286.1: a literal path in the call is a target, not an unknown. Codex CLI writes through
    # its shell, and on 0.158.0 with Mycelium's hooks trusted it created app/hello.py with
    # `python3 -c 'Path("app/hello.py").write_text(...)'`; the entry below only recorded "a write,
    # path unknown", which the discovery gate skips, so a new source file went through.
    # The quotes may arrive escaped: Codex records `/bin/zsh -lc "... Path(\"app/hello.py\") ..."`.
    (re.compile(r"\bPath\s*\(\s*\\?['\"](?P<t>[^'\"\\]+)\\?['\"]\s*\)\s*\.\s*write_(?:text|bytes)\s*\("),
     "python Path.write_text"),
    (re.compile(r"\bwriteFileSync\s*\(\s*\\?['\"](?P<t>[^'\"\\]+)\\?['\"]"), "node writeFileSync"),
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
    if _OPAQUE.search(t):
        # v0.318.1: a path holding a variable stays opaque. Joined and normalised, `$D/../x.py`
        # after `cd docs` became `docs/x.py`: the variable cancelled out, and the delivery gate
        # refused a file the command never writes (dogfood 2026-10-09, a scratchpad helper).
        return t
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
        # Outside the project: keep the ABSOLUTE directory, so what follows resolves outside and is
        # skipped. v0.251.0: the sentinel "__outside__" was joined into later paths as a folder
        # name, so `cd /other/repo && sed -i ... tests/x.py` became the in-project, nonexistent
        # `__outside__/tests/x.py`, and the delivery gate refused it as a new source file.
        return r.rel or "" if r.inside else r.real
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


#: Permission modes in which an `ask` reaches a person (v0.281.0). In any other mode nobody is
#: asked: E2E relay on 0.280.0 ran the builder with permissions bypassed, the `ask` went through,
#: and the agent wrote its own scale-lock override "My judgment call, my override". An unknown or
#: absent mode (another runtime) keeps the ask.
ASKS_A_HUMAN = ("default", "acceptEdits", "plan")
#: Runtimes whose hooks cannot ask (v0.286.0). Codex parses `permissionDecision: "ask"`, marks the
#: hook run failed and lets the tool call through, so an ask there is an allow. Its hook commands
#: carry MYCELIUM_RUNTIME=codex (hooks.codex.json and the plugin file derived from it).
CANNOT_ASK = ("codex",)


#: Since v0.318.0 a project with neither `.claude/canvas/` nor `.claude/diamonds/` is not a
#: Mycelium project and every hook exits at once (_hook_prelude.sh). Removing those folders is
#: therefore the widest off-switch there is, and is guard state too. Only REMOVAL counts: writing
#: or copying into them is ordinary work.
MARKER_DIRS_REL = (".claude", ".claude/canvas", ".claude/diamonds")
_REMOVES_MARKER = re.compile(
    rf"{_CMD}(?:rm|rmdir|mv)\b[^;&|\n]*?(?<![\w.-])(?:\./)?\.claude(?:/(?:canvas|diamonds))?/?(?=[\s'\"]|$)")


def _removed_marker(tool_name: str, tool_input, project_dir: str) -> str | None:
    """The marker folder a call removes, or None (v0.318.0)."""
    ti = tool_input if isinstance(tool_input, dict) else {}
    if tool_name == "Bash":
        m = _REMOVES_MARKER.search(str(ti.get("command") or ""))
        return m.group(0).split()[-1].strip("'\"") if m else None
    if tool_name.endswith("move_file") and ti.get("source"):
        r = resolve(str(ti["source"]), project_dir)
        rel = (r.rel or "").rstrip("/")
        return rel if r.inside and _fold(rel) in {_fold(m) for m in MARKER_DIRS_REL} else None
    return None


def _decide_guarded(name: str, what: str, permission_mode: str | None) -> None:
    """Ask the person, or refuse where nobody would be asked. `what` ends in "it" ("... it")."""
    mode = str(permission_mode or "")
    runtime = os.environ.get("MYCELIUM_RUNTIME", "")
    if runtime in CANNOT_ASK or (mode and mode not in ASKS_A_HUMAN):
        why = (f"This runtime ({runtime}) cannot ask a person" if runtime in CANNOT_ASK
               else f"In this permission mode ({mode}) nobody is asked")
        decision("deny", f"Mycelium {name}: {what} is a person's decision. {why}, so the agent "
                         "cannot do it. If you want it, do it yourself in your own terminal, or "
                         "set MYCELIUM_GUARD_STATE_EDIT=1 in your own shell.")
    decision("ask", f"Mycelium {name}: {what} is a person's decision, not the agent's. Approve if "
                    "you asked for it (for example, to remove Mycelium from this project).")


def guard_state_check(name: str, tool_name: str, tool_input, project_dir: str,
                      permission_mode: str | None = None) -> None:
    """Shared step: a write to guard state asks the human, or is refused where nobody would be
    asked. Returns when there is nothing to say."""
    if human_override():
        return
    marker = _removed_marker(tool_name, tool_input, project_dir)
    if marker:
        _decide_guarded(name, f"removing {marker} makes this project read as not using Mycelium, "
                              "which switches every Mycelium hook off; it", permission_mode)
    for r in _targets_of(tool_name, tool_input, project_dir):
        g = is_guard_state(r.rel)
        if not g:
            continue
        mode = str(permission_mode or "")
        runtime = os.environ.get("MYCELIUM_RUNTIME", "")
        if runtime in CANNOT_ASK or (mode and mode not in ASKS_A_HUMAN):
            why = (f"This runtime ({runtime}) cannot ask a person" if runtime in CANNOT_ASK
                   else f"In this permission mode ({mode}) nobody is asked")
            decision("deny", f"Mycelium {name}: {g} switches a blocking hook off, and only a "
                             f"person may write it. {why}, so the agent cannot write it. If you "
                             "want it, write it "
                             "yourself in your own terminal, or set MYCELIUM_GUARD_STATE_EDIT=1 in "
                             "your own shell for setup work.")
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


def discovery_state_code(project_dir: str) -> int:
    """0 engaged, 1 not engaged, 3 cannot check (v0.290.0): without PyYAML the diamonds file is
    not read, so a project with diamonds read as one with none, and the gate refused for a reason
    that was false."""
    if has_discovery_state(project_dir):
        return 0
    return 3 if _diamonds_unread(project_dir) else 1


def _diamonds_unread(project_dir: str) -> bool:
    """PyYAML is missing and the diamonds file holds entries: engagement cannot be judged."""
    try:
        import yaml  # noqa: F401, PLC0415 - only its absence matters here
    except ImportError:
        pass
    else:
        return False
    active = os.path.join(project_dir, ".claude", "diamonds", "active.yml")
    try:
        with open(active, encoding="utf-8") as fh:
            return re.search(r"^\s*-\s*id:\s*\S", fh.read(), re.MULTILINE) is not None
    except OSError:
        return False


def _line_for(r: Resolved) -> str:
    g = is_guard_state(r.rel)
    where = f"GUARD:{g}" if g else (r.rel if r.inside else f"OUTSIDE:{r.real}")
    return f"{where}\t{int(r.exists)}\t{r.size}"


def product_paths(project_dir: str) -> list[str] | None:
    """The project's `product_paths` from diamonds/active.yml: where its product's own files live,
    whatever their kind (v0.270.0). None when not declared; [] when declared as code only."""
    p = Path(project_dir) / ".claude" / "diamonds" / "active.yml"
    try:
        doc = _yaml().safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001 - SPEAKS: the scale lock reports an unreadable diamonds file
        return None
    paths = doc.get("product_paths") if isinstance(doc, dict) else None
    return [str(x) for x in paths if str(x).strip()] if isinstance(paths, list) else None


def in_product_paths(project_dir: str, rel: str) -> bool:
    """Whether a repo-relative path lies in a declared product path: a folder (`pilot/`), or a
    glob (`course/**/*.md`, `*.docx`). THE PRODUCT IS NOT ALWAYS CODE (v0.270.0): the E2E second
    world, a bookkeeping service, wrote its client agreement, intake checklist and price sheet
    under pilot/ with only an L0 in discover, and the delivery gate, which knew only code
    extensions and skipped every .md, never fired. A course's lessons and a publication's
    chapters are the same case."""
    return _in_declared(rel, product_paths(project_dir) or [])


def prototype_paths(project_dir: str) -> list[str]:
    """The project's declared `prototype_paths` (v0.291.0): throwaway discovery code, free to
    write and edit without a decision to build. Releasing it is still gated, by the release gate."""
    p = Path(project_dir) / ".claude" / "diamonds" / "active.yml"
    try:
        doc = _yaml().safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001 - errs toward gating: with none declared, nothing is exempt
        return []
    paths = doc.get("prototype_paths") if isinstance(doc, dict) else None
    return [str(x) for x in paths if str(x).strip()] if isinstance(paths, list) else []


def _in_declared(rel: str, patterns: list[str]) -> bool:
    """A repo-relative path lies under a declared folder (`pilot/`) or matches a glob."""
    rel = rel.removeprefix("./")
    for raw in patterns:
        pat = raw.strip().removeprefix("./")
        if pat.endswith("/"):
            if rel.startswith(pat):
                return True
        elif fnmatch(rel, pat) or rel.startswith(pat + "/"):
            return True
    return False


# ---------------------------------------------------------------- the delivery skip-ack (v0.293.0)

SKIP_ACK_REL = ".claude/state/delivery-skip-ack"
SKIP_ACK_USES_REL = ".claude/state/skip-ack-uses.jsonl"
SKIP_ACK_LEGACY_REL = ".claude/state/skip-ack-legacy-since"
SKIP_ACK_DAYS = 30
SKIP_ACK_LEGACY_DAYS = 14


def _today_date() -> _dt.date:
    """Mycelium's today: MYCELIUM_TODAY when set (a stated date, or a simulated world), else UTC,
    as scale_locks reads it."""
    raw = os.environ.get("MYCELIUM_TODAY", "").strip()
    utc_today = _dt.datetime.now(tz=_dt.UTC).date()
    try:
        return _dt.date.fromisoformat(raw[:10]) if raw else utc_today
    except ValueError:
        return utc_today


def _as_date(v) -> _dt.date | None:
    try:
        return _dt.date.fromisoformat(str(v)[:10]) if v else None
    except ValueError:
        return None


_SKIP_ACK_KEYS = ("recorded_at", "expires", "covers", "releases", "why")


def skip_ack_verdict(project_dir: str, kind: str, targets: list[str]) -> tuple[bool, str]:
    """Does the user's delivery skip-ack lift this gate (founder ruling DL-1364)? Returns
    (lifted, warning). The ack is scoped to the paths it names (`covers`), lifts a release only when
    it says `releases: true`, lasts SKIP_ACK_DAYS unless `expires` says otherwise, and every use is
    logged. Until v0.293.0 the mere existence of the file lifted the build and release gates for all
    future work, forever, and it was gitignored. An old bare file is honoured for
    SKIP_ACK_LEGACY_DAYS from the day this version first sees it, with a warning at each use."""
    path = Path(project_dir) / SKIP_ACK_REL
    if not path.exists():
        return False, ""
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        doc = _yaml().safe_load(text) if text.strip() else None
    except Exception:  # noqa: BLE001 - an unparseable ack is read as an old bare one, below
        doc = None
    today = _today_date()
    recorded = _as_date(doc.get("recorded_at")) if isinstance(doc, dict) else None
    structured = isinstance(doc, dict) and any(k in doc for k in _SKIP_ACK_KEYS)
    if structured and recorded is None:
        # v0.307.3 (control audit P4): a structured ack with no ISO `recorded_at` fell to the
        # legacy path, which lifts every gate, releases included; it lifts nothing until dated.
        return False, ("the delivery skip-ack has no `recorded_at` as YYYY-MM-DD, so it lifts "
                       "nothing; the user can add the date they wrote it (they write it, not the "
                       "agent)")
    if not isinstance(doc, dict) or recorded is None:
        return _legacy_ack(project_dir, kind, targets, today)
    expires = _as_date(doc.get("expires")) or recorded + _dt.timedelta(days=SKIP_ACK_DAYS)
    if today > expires:
        return False, (f"the delivery skip-ack expired on {expires}; ask the user whether to renew "
                       "it (they write it, not the agent)")
    if kind == "release":
        lifted = doc.get("releases") is True
    else:
        covers = [str(c) for c in (doc.get("covers") or []) if str(c).strip()]
        lifted = bool(targets) and all(_in_declared(t, covers) for t in targets)
    if lifted:
        _log_skip_ack(project_dir, kind, targets, legacy=False)
    return lifted, ""


def _legacy_ack(project_dir: str, kind: str, targets: list[str],
                today: _dt.date) -> tuple[bool, str]:
    since_path = Path(project_dir) / SKIP_ACK_LEGACY_REL
    since = _as_date(since_path.read_text().strip()) if since_path.exists() else None
    if since is None:
        since = today
        with contextlib.suppress(OSError):
            since_path.write_text(today.isoformat() + "\n")
    until = since + _dt.timedelta(days=SKIP_ACK_LEGACY_DAYS)
    how = ("re-record it as `recorded_at`, `expires`, `covers` (the paths it covers) and, only if "
           "releases are meant, `releases: true`, with the user's words in `why`")
    if today > until:
        return False, (f"the delivery skip-ack has no date or scope and its grace ended on "
                       f"{until}; "
                       f"it no longer lifts any gate. The user can {how}")
    _log_skip_ack(project_dir, kind, targets, legacy=True)
    return True, (f"the delivery skip-ack has no date or scope; it is honoured until {until} only. "
                  f"The user should {how}")


def _log_skip_ack(project_dir: str, kind: str, targets: list[str], *, legacy: bool) -> None:
    row = {"ts": _dt.datetime.now(tz=_dt.UTC).isoformat(timespec="seconds"), "gate": kind,
           "targets": targets[:10], "legacy": legacy}
    with contextlib.suppress(OSError), (Path(project_dir) / SKIP_ACK_USES_REL).open("a") as fh:
        fh.write(json.dumps(row) + "\n")


def _skip_ack_cli(project_dir: str, spec: list[str]) -> int:
    """--skip-ack KIND [REL...]: exit 0 and print any warning if the ack lifts this gate; else 1."""
    kind, targets = (spec[0] if spec else "build"), spec[1:]
    lifted, warning = skip_ack_verdict(project_dir, kind, targets)
    if warning:
        print(warning)
    return 0 if lifted else 1


def _path_query(args) -> int | None:
    """--product-file, --not-prototype and --skip-ack: answer and exit; None when none was asked."""
    if args.skip_ack is not None:
        return _skip_ack_cli(args.project_dir, args.skip_ack)
    if args.product_file is not None:
        hit = next((t for t in args.product_file if in_product_paths(args.project_dir, t)), None)
    elif args.not_prototype is not None:
        protos = prototype_paths(args.project_dir)
        hit = next((t for t in args.not_prototype if not _in_declared(t, protos)), None)
    else:
        return None
    if hit:
        print(hit)
    return 0 if hit else 1


def _yaml():
    """PyYAML, imported when a product path is asked about: the other hook modes need none."""
    import yaml  # noqa: PLC0415 - optional dependency, only this mode reads YAML
    return yaml


def _guard_state_hook(name: str, project_dir: str) -> int:
    """The guard-state gate for every project (v0.281.0). The three guards that asked were each
    conditional (autonomous runs, a scope, the framework's own repo), so in an ordinary project
    nothing guarded the ack files, though scale_locks' docstring said the agent "gets an ASK"."""
    @fail_closed(name)
    def run() -> int:
        data = read_input()
        guard_state_check(name, str(data.get("tool_name") or ""), data.get("tool_input") or {},
                          project_dir, data.get("permission_mode"))
        return 0
    return run()


def cli() -> int:
    """For shell hooks: tool name; one line per target (rel | OUTSIDE:real | GUARD:name |
    OPAQUE:label, tab, exists, tab, size); a `---CONTENT---` line; then the written content."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-dir", default=os.environ.get("CLAUDE_PROJECT_DIR", "."))
    ap.add_argument("--skip-ack", nargs="+", default=None, metavar="KIND",
                    help="build|release [REL...]: does the delivery skip-ack lift this gate? "
                         "exit 0 (lifted) or 1; prints any warning; reads no stdin")
    ap.add_argument("--discovery-state", action="store_true",
                    help="exit 0 if discovery has been engaged, 1 if not; reads no stdin")
    ap.add_argument("--purpose-state", action="store_true",
                    help="exit 0 if purpose.yml has a purpose statement, 1 if not; reads no stdin")
    ap.add_argument("--not-prototype", nargs="*", default=None, metavar="REL",
                    help="print the first REL NOT under the declared `prototype_paths`, exit 0; "
                         "exit 1 if every one is a prototype; reads no stdin")
    ap.add_argument("--product-file", nargs="*", default=None, metavar="REL",
                    help="print the first of these repo-relative paths that lies in the project's "
                         "`product_paths`, exit 0; exit 1 if none does; reads no stdin")
    ap.add_argument("--guard-state", metavar="HOOK_NAME", default=None,
                    help="PreToolUse payload on stdin: ask or deny a write to guard state")
    args = ap.parse_args()
    if args.guard_state:
        return _guard_state_hook(args.guard_state, args.project_dir)
    if args.purpose_state:
        return 0 if has_purpose(args.project_dir) else 1
    answered = _path_query(args)
    if answered is not None:
        return answered
    if args.discovery_state:
        return discovery_state_code(args.project_dir)
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
