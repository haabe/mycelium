#!/usr/bin/env python3
"""
Mycelium scope hold helper: keeps the agent's writes inside the folders a delivery cycle named.

WHERE THE FOLDERS LIVE (v0.324.0). On the delivery cycle's own record: an L4 in
`.claude/diamonds/active.yml` may carry `in_scope_paths`.

    in_scope_paths: [app/billing/, tests/billing/**]   # the agent is held to these
    in_scope_paths: []                                  # "no hold for this one", said on purpose
    (absent)                                            # nobody has decided

The hold is in force for a cycle that has committed to build and has not closed. With several
such cycles a write is inside when it is inside any of their lists. Nothing is stored beside the
record: the answer is read from it at the moment of the write.

WHY IT MOVED. Until 0.324.0 the folders were read from `.claude/state/active-execution.json`, and
no skill, script or hook wrote that file, so in a plugin install the hold was never on (a blind
reader of the installed plugin, dogfood 2026-10-11). A file is switched on by whoever remembers to
write it. The record is already written when delivery opens, so the switch sits there, and the
commitment to build is refused until the cycle says where it may write.

WHAT IT DOES ON A WRITE.
- A write under `.claude/` is never held.
- A write outside every list in force is put to the person (an ask), with the file named. Where
  nobody can be asked it is refused, and the refusal says the two ways a person can allow it.
- A write to the diamonds file that names, changes, empties or removes a delivery cycle's folders
  is put to the person the same way: where the agent may write is theirs to say.
- A write to the diamonds file that would commit a delivery cycle to build with nothing said about
  its folders is refused. A cycle that had committed before 0.324.0 is left as it is; session
  start says it is not held (`--notices`).
- THE OLD STATE FILE IS NO LONGER READ. While one exists, product writes are refused and the
  refusal says to move its folders to the cycle's record and delete it, so a hold someone set by
  hand is never dropped in silence (maintainer's ruling, 2026-10-13).

WHAT IT CANNOT SEE. A command that writes files itself (a scaffolder, a clone) names no target a
hook can read; the same limit the pages state for the build gate.

Called by hooks/scope-gate.sh:   python3 scope_check.py <old_state_file_path> <project_dir>
Called by hooks/session-start.sh: python3 scope_check.py --notices <project_dir>
Input (stdin): the PreToolUse hook JSON. Output: a hook decision as JSON on stdout, or nothing.
"""

import functools
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _hook_input as hi  # sibling module, after the path insert

RECORD_REL = ".claude/diamonds/active.yml"
OLD_STATE_REL = ".claude/state/active-execution.json"
FIELD = "in_scope_paths"
_ABSENT = object()
_GLOB = re.compile(r"[*?]")


@functools.lru_cache(maxsize=256)
def _compile_glob(pattern: str) -> "re.Pattern[str]":
    """Compile a path glob to a regex with path-segment semantics.

    Unlike fnmatch (where ``*`` matches ``/`` too — letting ``src/xyz/*`` leak
    into ``src/xyz/legacy/...``), here:
      - ``*``   matches within a single path segment (no ``/``)
      - ``?``   matches a single non-``/`` char
      - ``**``  matches across segments (any depth)
      - ``**/`` matches zero-or-more leading segments, so ``**/foo`` hits both
                top-level ``foo`` and nested ``a/b/foo``
    """
    out = []
    i = 0
    n = len(pattern)
    while i < n:
        c = pattern[i]
        if c == "*":
            if pattern[i + 1 : i + 2] == "*":
                if pattern[i + 2 : i + 3] == "/":
                    out.append("(?:.*/)?")  # **/  → zero-or-more dirs
                    i += 3
                else:
                    out.append(".*")  # **   → any depth
                    i += 2
            else:
                out.append("[^/]*")  # *    → single segment
                i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(c))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def _glob_match(path: str, pattern: str) -> bool:
    return bool(_compile_glob(pattern).match(path))


def inside(rel: str, pattern: str) -> bool:
    """Whether a project-relative path lies in what a cycle named: a folder (`app/billing/` or
    `app/billing`, itself and everything under it), a single file, or a glob."""
    rel = rel.removeprefix("./")
    pat = pattern.strip().removeprefix("./")
    if not pat:
        return False
    if _GLOB.search(pat):
        return _glob_match(rel, pat)
    stem = pat.rstrip("/")
    return rel == stem or rel.startswith(stem + "/")


def emit_allow():
    """Silent allow — just exit 0."""
    sys.exit(0)


def emit_deny(reason: str):
    """Emit a deny decision with a reason and exit 0."""
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    print(json.dumps(output))
    sys.exit(0)


REQUIRED_ARG_COUNT = 3  # script name + old state file (existence only) + project_dir


class RecordUnreadableError(Exception):
    """The diamonds file is there and cannot be read as a mapping."""


def _siblings():
    """scale_locks and settings_switches, imported when a record is read: the fast paths above
    need neither, and scale_locks is large."""
    import scale_locks  # noqa: PLC0415 - sibling, on the path since the insert at the top
    import settings_switches  # noqa: PLC0415
    return scale_locks, settings_switches


def _is_delivery_cycle(d: dict) -> bool:
    return str(d.get("scale") or "").strip().upper() == "L4" and bool(d.get("id"))


def _record(text: str) -> dict:
    import yaml  # noqa: PLC0415 - optional dependency, only needed once a record is read
    try:
        doc = yaml.safe_load(text) if text.strip() else {}
    except yaml.YAMLError as exc:
        raise RecordUnreadableError(type(exc).__name__) from exc
    if doc is None:
        return {}
    if not isinstance(doc, dict):
        raise RecordUnreadableError("it is not a mapping")
    return doc


def _rows(doc: dict, key: str) -> list[dict]:
    value = doc.get(key)
    return [d for d in value if isinstance(d, dict)] if isinstance(value, list) else []


def delivery_cycles(doc: dict) -> dict:
    """id -> (cycle, committed to build, still open) for every L4 in the active list."""
    sl, _ = _siblings()
    gone = {str(d.get("id")) for key in ("completed_diamonds", "archived_diamonds")
            for d in _rows(doc, key)}
    out = {}
    for d in _rows(doc, "active_diamonds"):
        if not _is_delivery_cycle(d):
            continue
        cid = str(d["id"])
        committed = any(x.get("decision") == "commit_to_build" for x in sl.decisions_of(d))
        still_open = (cid not in gone and sl.phase_of(d) not in sl.CLOSED
                      and str(d.get("state", "")).lower() not in sl.CLOSED)
        out[cid] = (d, committed, still_open)
    return out


def named(d: dict):
    """What a cycle names: its list, [] for "no hold", or _ABSENT when nothing is said."""
    if FIELD not in d:
        return _ABSENT
    raw = d.get(FIELD)
    return [str(p) for p in raw if str(p).strip()] if isinstance(raw, list) else []


def named_anywhere(doc: dict) -> dict:
    """id -> what the cycle names, for every L4 in the active, completed and archived lists. A
    cycle that moves between lists with its folders as they were has changed nothing: that is
    how a close is recorded, and a close is not a question about folders."""
    out = {}
    for key in ("active_diamonds", "completed_diamonds", "archived_diamonds"):
        for d in _rows(doc, key):
            if _is_delivery_cycle(d):
                out[str(d["id"])] = named(d)
    return out


def _shown(value) -> str:
    if value is _ABSENT:
        return "nothing said"
    return ", ".join(value) if value else "no hold"


def changed_between(before_text: str | None, after_text: str | None) -> list[str]:
    """What changed in where delivery cycles may write between two texts of the record,
    one line per cycle; None is a record that is not there. For the shell guard, which
    can only look after a command has run (bash_state_guard.py). Empty when nothing
    changed, and when either text cannot be read: an unreadable record refuses product
    writes on its own, and the shell guard says that it does not parse."""
    try:
        was = named_anywhere(_record(before_text or ""))
        now = named_anywhere(_record(after_text or ""))
    except RecordUnreadableError:
        return []  # SPEAKS: the hold refuses product writes over a record it cannot read
    out = []
    for cid in sorted(set(was) | set(now)):
        a, b = was.get(cid, _ABSENT), now.get(cid, _ABSENT)
        if a == b:
            continue
        left = (f"the command left {_shown(b)}" if cid in now
                else "and the command took the cycle out of the record")
        out.append(f"delivery cycle {cid}: was {_shown(a)}, {left}")
    return out


def in_force(doc: dict) -> list[tuple[str, list[str]]]:
    """(cycle id, its folders) for every cycle whose hold is on."""
    return [(cid, named(d)) for cid, (d, committed, still_open) in delivery_cycles(doc).items()
            if committed and still_open and named(d) is not _ABSENT and named(d)]


def _cannot_ask(mode: str | None) -> str:
    """Why nobody would be asked, or "" when a person is."""
    runtime = os.environ.get("MYCELIUM_RUNTIME", "")
    if runtime in hi.CANNOT_ASK:
        return f"This runtime ({runtime}) cannot ask a person"
    if mode and mode not in hi.ASKS_A_HUMAN:
        return f"In this permission mode ({mode}) nobody is asked"
    return ""


def _ask_or_refuse_outside(what: str, mode: str | None) -> None:
    """A write the hold does not let through unasked."""
    why = _cannot_ask(mode)
    if why:
        emit_deny(f"Mycelium scope hold: {what} {why}, so the write is refused. A person can allow "
                  "it two ways: say yes to this write in a session where they are asked, or change "
                  f"the folders the delivery cycle names (`{FIELD}` in {RECORD_REL}).")
    hi.decision("ask", f"Mycelium scope hold: {what} Approve to let this one write through. To "
                       "stop being asked, change the folders the delivery cycle names "
                       f"(`{FIELD}` in {RECORD_REL}).")


def _ask_or_refuse_folders(what: str, mode: str | None) -> None:
    """A write to the record that says where delivery work may write."""
    why = _cannot_ask(mode)
    if why:
        emit_deny(f"Mycelium scope hold: {what}. Where the agent may write is a person's decision. "
                  f"{why}, so the write is refused. Make the change yourself, or in a session "
                  "where you are asked.")
    hi.decision("ask", f"Mycelium scope hold: {what}. Approve if that is what you want.")


def _said(cid: str, now) -> str:
    """One changed cycle, said to the person."""
    if now is _ABSENT:
        return (f"this write takes the named folders off delivery cycle {cid}, which leaves "
                "nothing said about where it may write")
    if not now:
        return (f"this write says delivery cycle {cid} has no hold: the agent may write "
                "anywhere in the product while that work is open")
    return (f"this write names the folders delivery cycle {cid} may write to "
            f"({', '.join(now)}); the agent is held to them while that work is open")


def _judge_record_write(tool_input, project_dir: str, mode: str | None) -> None:
    """A write to the diamonds file: where a cycle may write is the person's to say, and a
    commitment to build with nothing said about it is refused."""
    if hi.human_override():
        return
    _, ss = _siblings()
    for key, path in hi.target_paths(tool_input):
        r = hi.resolve(path, project_dir, key=key)
        if r.rel != RECORD_REL or key == "source":
            continue
        try:
            with open(r.real, encoding="utf-8", errors="replace") as fh:
                before_text = fh.read()
        except OSError:
            before_text = ""  # SPEAKS: no record yet, so everything the write names is new

        def read_source(src: str) -> str:
            with open(hi.resolve(src, project_dir).real, encoding="utf-8", errors="replace") as fh:
                return fh.read()

        try:
            after_text = ss.proposed_text(tool_input, before_text, key, read_source)
            before_doc, after_doc = _record(before_text), _record(after_text)
        except (ss.CannotTellError, RecordUnreadableError):
            return  # SPEAKS: scale-lock-gate.sh judges a result it cannot read, and refuses it
        before, after = delivery_cycles(before_doc), delivery_cycles(after_doc)
        for cid, (d, committed, _open) in after.items():
            was = before.get(cid)
            if committed and not (was and was[1]) and named(d) is _ABSENT:
                emit_deny(f"Mycelium scope hold: this would commit delivery cycle {cid} to build "
                          "with nothing said about where it may write. Add the folders it will "
                          f"touch to the cycle (`{FIELD}: [folder/, other/]`), or an empty list "
                          f"(`{FIELD}: []`) for no hold on this one. Either is put to the person.")
        named_before, named_after = named_anywhere(before_doc), named_anywhere(after_doc)
        changed = sorted(cid for cid in set(named_before) | set(named_after)
                         if named_before.get(cid, _ABSENT) != named_after.get(cid, _ABSENT))
        if changed:
            what = "; ".join(_said(cid, named_after[cid]) if cid in named_after else
                             f"this write removes delivery cycle {cid} and the folders it named"
                             for cid in changed)
            _ask_or_refuse_folders(what, mode)


def _held(project_dir: str) -> list[tuple[str, list[str]]]:
    """The holds in force, read from the record now. Allows when there is no record; refuses
    when the record is there and cannot be read."""
    try:
        with open(os.path.join(project_dir, RECORD_REL), encoding="utf-8", errors="replace") as fh:
            return in_force(_record(fh.read()))
    except FileNotFoundError:
        return []  # SPEAKS: no diamonds file is a project with no delivery cycle to hold
    except (OSError, RecordUnreadableError) as exc:
        emit_deny(f"Mycelium scope hold: {RECORD_REL} cannot be read ({exc}), so Mycelium cannot "
                  "tell whether a delivery cycle holds this write. Repair that file first; writes "
                  "under .claude/ are not held.")
    return []


def notices(project_dir: str) -> str:
    """What session start says about the hold: an old state file that is no longer read, and
    delivery cycles that committed before the hold existed and so name nothing."""
    out = []
    if os.path.exists(os.path.join(project_dir, OLD_STATE_REL)):
        out.append(f"SCOPE HOLD: {OLD_STATE_REL} is no longer read (since 0.324.0), and while it "
                   "exists the agent's product writes are refused. Move its folders to the "
                   f"delivery cycle in {RECORD_REL} (`{FIELD}:` on that cycle; you are asked) and "
                   "delete the file yourself.")
    try:
        with open(os.path.join(project_dir, RECORD_REL), encoding="utf-8", errors="replace") as fh:
            cycles = delivery_cycles(_record(fh.read()))
    except (OSError, RecordUnreadableError):
        return " ".join(out)  # SPEAKS: an unreadable diamonds file is session start's own notice
    unsaid = sorted(cid for cid, (d, committed, still_open) in cycles.items()
                    if committed and still_open and named(d) is _ABSENT)
    if unsaid:
        out.append(f"SCOPE HOLD: delivery cycle(s) {', '.join(unsaid)} committed to build with "
                   "nothing said about where the agent may write, so it is not held to any "
                   f"folder for that work. To hold it, add `{FIELD}: [folder/, ...]` to the cycle "
                   f"in {RECORD_REL}; to leave it free on purpose, add `{FIELD}: []`. Either is "
                   "put to the person.")
    return " ".join(out)


@hi.fail_closed("scope-gate")
def main():
    """Entry point. Paths are resolved to their REAL location (`..`, symlinks, case) before any
    list is consulted; every path key is read; shell write targets are judged too; guard-state
    writes ask the human; a crash denies. Each of those was a demonstrated bypass on
    2026-09-11 (dogfood evals/security)."""
    if len(sys.argv) < REQUIRED_ARG_COUNT:
        emit_deny("Mycelium scope-gate: scope_check.py invoked without required arguments. "
                  "This is a bug in the hook wrapper.")
    old_state_file, project_dir = sys.argv[1], sys.argv[2]
    hook_input = hi.read_input()
    tool_name = str(hook_input.get("tool_name") or "")
    tool_input = hook_input.get("tool_input") or {}
    mode = hook_input.get("permission_mode")
    hi.guard_state_check("scope-gate", tool_name, tool_input, project_dir, mode)
    if tool_name == "Bash":
        scan = hi.bash_write_targets(str(tool_input.get("command", "") or ""), project_dir)
        targets, opaque = scan.targets, scan.opaque
    else:
        _judge_record_write(tool_input, project_dir, mode)
        targets = [hi.resolve(pth, project_dir, key=k) for k, pth in hi.target_paths(tool_input)]
        opaque = []
    product = [r for r in targets
               if not ((r.rel or "").startswith(".claude/") or r.rel == ".claude")]
    if not product and not opaque:
        emit_allow()  # canvas, state, memory: not held
    if os.path.exists(old_state_file):
        emit_deny(f"Mycelium scope hold: {OLD_STATE_REL} is no longer read (since 0.324.0). The "
                  "folders a delivery cycle may write to now live on the cycle's own record. So "
                  "that a hold set by hand is not dropped in silence, product writes are refused "
                  f"while that file exists. Move its folders to the delivery cycle in {RECORD_REL} "
                  f"(`{FIELD}: [folder/, ...]` on that cycle; the person is asked), then the "
                  "person deletes the file. Writes under .claude/ are not held.")
    held = _held(project_dir)
    if not held:
        emit_allow()
    names = ", ".join(cid for cid, _ in held)
    lists = "; ".join(", ".join(paths) for _, paths in held)
    if opaque:
        _ask_or_refuse_outside(f"this command writes to a target the hold cannot read "
                               f"({'; '.join(opaque[:3])}) while delivery cycle {names} is held "
                               f"to {lists}.", mode)
    for r in product:
        if not r.inside:
            _ask_or_refuse_outside(f"'{r.given}' resolves to {r.real}, outside the project, "
                                   f"while delivery cycle {names} is held to {lists}.", mode)
        rel = r.rel or ""
        if not any(inside(rel, pattern) for _, paths in held for pattern in paths):
            _ask_or_refuse_outside(f"'{rel}' is outside the folders delivery cycle {names} named "
                                   f"({lists}).", mode)
    emit_allow()


if __name__ == "__main__":
    if len(sys.argv) == REQUIRED_ARG_COUNT and sys.argv[1] == "--notices":
        said = notices(sys.argv[2])
        if said:
            print(said)
        sys.exit(0)
    main()
