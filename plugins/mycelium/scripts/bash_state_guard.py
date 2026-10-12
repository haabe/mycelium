"""Shell commands that change canvas or diamond state are judged like edits are (v0.253.2).

E2E run 24: the builder rewrote `privacy-assessment.yml` through a shell command, the schema check
(a PostToolUse hook on Write/Edit/MultiEdit) never saw it, and the file stood invalid. Reading the
hook registrations then showed the larger hole: `scale-lock-gate.sh` is registered on the edit
tools only, so `sed -i`, a heredoc or a Python one-liner could open a diamond past its entry lock or
move it forward without its gates, and neither the locks, the ruling recorder nor the schema check
would run.

Two halves, one script:

  pre   (PreToolUse Bash) refuses a command that visibly writes diamonds/active.yml: a redirect,
        `sed -i`, `tee`, or a script that names the file and writes. The remedy is the Edit or
        Write tool, where the scale-lock gate judges the change. Reads are never refused. Mycelium's
        own writer (`derive_closing_path.py`, which sets `closes_on`) is allowed. It also snapshots
        diamonds/active.yml and stamps the time, for the second half.
  post  (PostToolUse Bash) looks at canvas and diamonds files changed since the stamp: each is
        checked against its schema, and a changed diamonds file is judged against the snapshot by
        the same verdict the write hook uses (`scale_locks.violations_between`), and its rulings
        recorded. What is found goes to the agent in the same turn. This catches the writes the
        first half cannot see, such as a path built in a variable.

It never undoes a change to the canvas or the diamonds file. Stdlib plus the sibling scripts;
without PyYAML the post half says once that it could not judge (canvas_write_check handles the
schema side the same way).

THE FILES THAT SWITCH A STOP OFF ARE PUT BACK (v0.321.1). `guard-state-gate.sh` asks the person
before a tool call writes one of them (`_hook_input.GUARD_STATE_REL`), and it can only ask about a
write target it can read. A shell write through a variable or a command substitution was allowed in
silence: a blind read of 0.321.0 found it by reading, and a replay through the released hook
confirmed it (`f=<the file>; echo ... > "$f"`: no question, exit 0). No reading of a command closes
that, because a path can be built any number of ways. So this script compares before and after
instead, as it already does for the diamonds file:

  pre   copies each of those files that exists and notes which do not, and notes which of them the
        command writes VISIBLY, because for those the person is asked (or the call is refused) by
        `guard-state-gate.sh` and a command that then runs was approved.
  post  compares. A file that was created, changed or removed by the command, and was not one the
        person was asked about, is put back as it was, and the person and the agent are told.

This is the one place the script undoes anything, on the maintainer's ruling of 2026-10-11 ("Put it
back and tell me"): left as written, the stop is off until someone notices. It touches only those
seven files, never code, canvas or diamonds. Not put back: a change the person makes in their own
terminal (no hook sees it), a change made with `MYCELIUM_GUARD_STATE_EDIT=1` in the person's own
shell, and Mycelium's own upgrade script run on its own.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import _hook_input as hi  # noqa: E402
import _state_dir  # noqa: E402
import settings_switches as ss  # noqa: E402

ACTIVE_REL = ".claude/diamonds/active.yml"
STATE_REL = Path(".claude") / "state" / "bash-guard"
# Mycelium's own writers of diamond state; migrate_phase.py since v0.303.0 (DL-1368 S3).
ALLOWED_WRITERS = ("derive_closing_path.py", "migrate_phase.py")
# v0.307.4 (control audit P7, DL-1370): one of them, run on its own. Until then the check was a
# substring of the whole command, so `cp new.yml active.yml  # then run migrate_phase.py` passed.
_OWN_WRITER = re.compile(
    r"\s*(?:\S*python3?(?:\.\d+)?\s+)?\"?[^\s;&|<>`$()\"]*?(?:"
    + "|".join(re.escape(w) for w in ALLOWED_WRITERS)
    + r")\"?(?:\s+[^;&|<>`$()\n]*)?\s*")
#: Mycelium's own writer of guard state (v0.321.1): the legacy upgrade copies the manifest.
GUARD_WRITERS = ("upgrade.sh",)
_OWN_GUARD_WRITER = re.compile(
    r"\s*(?:bash\s+|sh\s+)?\"?[^\s;&|<>`$()\"]*?(?:"
    + "|".join(re.escape(w) for w in GUARD_WRITERS)
    + r")\"?(?:\s+[^;&|<>`$()\n]*)?\s*")
GUARD_SNAP = "guard-state"
# v0.307.4 (P8): moving the file away removes every diamond's record, as `rm` does (refused).
_MOVES_ACTIVE = re.compile(r"\b(?:git\s+)?mv\b[^;&|\n]*diamonds/active\.yml")


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except (SystemExit, ImportError):  # SPEAKS: callers report that the check could not run
        return None
    return mod


def _without_comments(cmd: str) -> str:
    """The command with its shell comments removed, quotes respected (v0.307.4): a trailing
    `# ... migrate_phase.py` was read as `cp`'s destination, hiding the real one."""
    out, quote, prev = [], "", " "
    for line in cmd.splitlines(keepends=True):
        skipping = False
        for ch in line:
            if skipping:
                if ch == "\n":
                    out.append(ch)
                continue
            if quote:
                quote = "" if ch == quote else quote
            elif ch in "'\"":
                quote = ch
            elif ch == "#" and prev.isspace():
                skipping = True
                continue
            out.append(ch)
            prev = ch
        prev = " "
    return "".join(out)


def writes_active(cmd: str, project: str) -> bool:
    """Does this command visibly write diamonds/active.yml?"""
    cmd = _without_comments(cmd)
    if _MOVES_ACTIVE.search(cmd):
        return True
    if _OWN_WRITER.fullmatch(cmd):
        return False
    scan = hi.bash_write_targets(cmd, project)
    if any(t.inside and t.rel == ACTIVE_REL for t in scan.targets):
        return True
    names_it = "diamonds/active.yml" in cmd
    return names_it and any(_could_be_active(o) for o in scan.opaque)


_VARIABLE = re.compile(r"[$`()]")


def _could_be_active(opaque: str) -> bool:
    """Could this opaque write (`"redirect on $TMPDIR/hits.txt"`, or a writer with no visible
    target) land on active.yml? v0.318.1: any opaque write anywhere in a command that NAMED the file
    refused it, so `grep ... active.yml > $TMPDIR/hits.txt` was refused as a write (68 refusals in
    the dogfood transcripts, 2026-09-25..10-10; 13 of them released by this rule, none of those an
    unseen write). A last component that is a literal name other than active.yml cannot be it."""
    if " on " not in opaque:
        return True  # a writer with no visible target: unknown, keep refusing
    target = opaque.split(" on ", 1)[1].strip().strip("'\"").rstrip("/")
    base = target.rsplit("/", 1)[-1]
    return bool(_VARIABLE.search(base)) or base == "active.yml"


def pre(payload: dict, project: Path) -> int:
    ti = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    cmd = ti.get("command") if isinstance(ti.get("command"), str) else ""
    if writes_active(cmd, str(project)):
        print("Mycelium: refused. This shell command writes .claude/diamonds/active.yml, where "
              "the scale-lock gate cannot judge it: entry locks, decision gates and the ruling "
              "record only run on the Edit and Write tools. Make the change with Edit or Write "
              "(/mycelium:diamond-progress to record a decision). Reading the file is never "
              "refused.",
              file=sys.stderr)
        return 2
    state = project / STATE_REL
    active = project / ACTIVE_REL
    if (project / ".claude").is_dir():
        try:
            _state_dir.prepare_dir(state)
            if active.exists():
                shutil.copyfile(active, state / "active.yml.before")
            else:
                (state / "active.yml.before").unlink(missing_ok=True)
            _drop_old_snapshots(state)
            _snapshot_guard_state(project, state, cmd, _call_id(payload))
            (state / "stamp").write_text(repr(time.time()))
        except OSError:
            return 0  # SPEAKS in post: with no stamp, post says it could not tell what changed
    return 0


# ---------------------------------------------------------------- guard state, before and after

def _call_id(payload: dict) -> str:
    """A name for this tool call's snapshot. Claude Code gives each call an id, so two shell
    commands running at once do not read each other's "before"; a runtime that gives none shares
    one snapshot, as the diamonds half always has."""
    raw = str(payload.get("tool_use_id") or "")
    return re.sub(r"[^A-Za-z0-9_-]", "", raw)[:80] or "shared"


def _drop_old_snapshots(state: Path, older_than: float = 86400.0) -> None:
    """A snapshot whose post half never ran (the session ended mid-command) is removed after a
    day, so the folder does not grow. Nothing is put back from it: a day later it says nothing
    about who wrote what."""
    root = state / GUARD_SNAP
    if not root.is_dir():
        return
    now = time.time()
    for d in root.iterdir():
        try:
            if d.is_dir() and now - d.stat().st_mtime > older_than:
                shutil.rmtree(d, ignore_errors=True)
        except OSError:
            continue  # SPEAKS: nothing to say; an old snapshot that cannot be read is not used


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot_guard_state(project: Path, state: Path, cmd: str, call: str) -> None:
    snap = state / GUARD_SNAP / call
    shutil.rmtree(snap, ignore_errors=True)
    _state_dir.prepare_dir(snap)
    files = {}
    for i, rel in enumerate(hi.GUARD_STATE_REL):
        f = project / rel
        if f.is_file():
            shutil.copyfile(f, snap / f"{i}.before")
            files[rel] = {"existed": True, "sha": _digest(f), "copy": f"{i}.before"}
        else:
            files[rel] = {"existed": False}
    # The writes guard-state-gate.sh can read, and so asks the person about (or refuses).
    asked = sorted({g for r in hi.bash_write_targets(cmd, str(project)).targets
                    if (g := hi.is_guard_state(r.rel))})
    own = bool(_OWN_GUARD_WRITER.fullmatch(_without_comments(cmd)))
    # v0.322.6: which Mycelium switches each Claude Code settings file carries now (their keys and
    # values, not the files), and whether the person's override was on BEFORE the command. Read
    # afterwards it could have been set by the command itself, through the settings file.
    settings = {name: _switches_in(path) for name, path in _settings_files(project).items()}
    (snap / "index.json").write_text(json.dumps({
        "files": files, "asked": asked, "own": own, "settings": settings,
        "override": hi.human_override(), "git": _git_before(project)}))


def _git_before(project: Path) -> dict:
    """Where the repository's commit pointer is before the command (v0.323.0), so that commits
    the command makes can be scanned afterwards. Empty where there is no repository."""
    cs = _load("commit_scan")
    repo = cs.repo_of(str(project)) if cs else None
    if not repo:
        return {}
    return {"repo": repo, "head": cs.head_of(repo), "reflog": cs.reflog_length(repo)}


def _secrets_committed(git_before: dict) -> list[str]:
    """What the secret scan finds in commits the command itself made (commit_scan.py). Mycelium
    does not rewrite a commit: it says what it found, and the push is where it is refused."""
    cs = _load("commit_scan")
    repo = git_before.get("repo") if isinstance(git_before, dict) else None
    if not cs or not repo:
        return []
    shas = cs.made_commits(repo, git_before.get("head") or "", git_before.get("reflog"))
    if not shas:
        return []
    status, lines = cs.scan_commits(repo, shas[:50])
    short = ", ".join(s[:8] for s in shas[:5]) + (" and more" if len(shas) > 5 else "")  # noqa: PLR2004
    if status == "found":
        return [f"in {short}: " + "; ".join(lines[:8])]
    if status == "error":
        return [(f"the scan of {short} could not run ({'; '.join(lines)}), so nothing is known "
                 "about them")]
    return []


def _settings_files(project: Path) -> dict[str, Path]:
    """The settings files Claude Code reads for this project, by the name a person knows."""
    out = {rel: project / rel for rel in ss.SETTINGS_REL}
    user = Path(ss.user_settings_path())
    if user.resolve() not in {p.resolve() for p in out.values()}:
        out[ss.USER_SETTINGS_NAME] = user
    return out


def _switches_in(path: Path) -> dict:
    try:
        return ss.switches(path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return {}  # SPEAKS: a settings file that is not there, or cannot be read, sets no switch


def _replace_text(path: Path, text: str) -> None:
    """Write `text` over `path` in one step, keeping the file's permissions."""
    tmp = path.with_name(path.name + ".mycelium-tmp")
    tmp.write_text(text, encoding="utf-8")
    try:
        shutil.copymode(path, tmp)
        os.replace(tmp, path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise


def _put_back_settings(project: Path, index: dict) -> tuple[list[str], list[str]]:
    """What the command did to the Mycelium switches in a Claude Code settings file (v0.322.6).

    Returns (undone, reported). A switch the command set that was not set before is taken out
    again and everything else in the file is kept; the maintainer's ruling for the file in the
    home folder, 2026-10-12: "Undo that line, tell me". The plugin switched off in
    `enabledPlugins` is reported and left alone, because Claude Code's own plugin commands write
    that key and the person may have run one while the command was going."""
    undone, reported = [], []
    was = index.get("settings")
    if not isinstance(was, dict) or index.get("override", hi.human_override()):
        return undone, reported
    for name, path in _settings_files(project).items():
        before = was.get(name)
        if not isinstance(before, dict):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue  # SPEAKS: no file after the command means no switch is set in it
        now = ss.switches(text)
        new = ss.newly_set(before, now)
        theirs = [k for k in new if k.startswith(ss.WRITTEN_BY_THE_RUNTIME)]
        mine = [k for k in new if k not in theirs]
        if theirs:
            reported.append(f"{name} now carries {ss.describe(theirs, now)}")
        if not mine:
            continue
        fixed = ss.without(text, before, mine)
        failed = "the file is not a JSON object" if fixed is None else ""
        if fixed is not None:
            try:
                _replace_text(path, fixed)
            except OSError as exc:
                failed = type(exc).__name__
        undone.append(f"{ss.describe(mine, now)} in {name} " + (
            f"(COULD NOT BE TAKEN OUT: {failed}; the file is as the command left it)" if failed
            else "(taken out again; the rest of the file is as the command left it)"))
    return undone, reported


def _put_back_guard_state(project: Path, state: Path, call: str,
                          extras: dict | None = None) -> list[str]:
    """Undo what the command did to a file that switches a stop off, unless the person was asked.
    Returns one line per file put back; a file it could not put back is named as such. `extras`,
    when given, receives what else the snapshot held: `settings`, the two lists
    `_put_back_settings` returns, and `git`, where the commit pointer was before the command."""
    snap = state / GUARD_SNAP / call
    if not (snap / "index.json").is_file():
        return []  # no snapshot for this call: its before half did not run, so nothing to compare
    try:
        index = json.loads((snap / "index.json").read_text())
    except (OSError, ValueError) as exc:
        shutil.rmtree(snap, ignore_errors=True)
        return [("(WARNING: the record of how those files looked before the command could not be "
                 f"read, {type(exc).__name__}, so nothing was compared and nothing was put back)")]
    out = []
    try:
        if extras is not None and isinstance(index, dict):
            extras["settings"] = _put_back_settings(project, index)
            extras["git"] = index.get("git") if isinstance(index.get("git"), dict) else {}
        # The override as it was BEFORE the command (v0.322.6); a snapshot from an older version
        # has no such note and falls back to the environment now.
        if index.get("own") or index.get("override", hi.human_override()):
            return []
        for rel, was in index.get("files", {}).items():
            if rel in index.get("asked", []):
                continue
            f = project / rel
            now = f.is_file()
            if was.get("existed") == now and (not now or _digest(f) == was.get("sha")):
                continue
            try:
                if was.get("existed"):
                    _state_dir.prepare_dir(f.parent)
                    shutil.copyfile(snap / was["copy"], f)
                    out.append(f"{rel} (restored to what it held before the command)")
                else:
                    f.unlink()
                    out.append(f"{rel} (the command created it; removed)")
            except OSError as exc:
                out.append(f"{rel} (COULD NOT BE PUT BACK: {type(exc).__name__}; it is as the "
                           "command left it)")
    finally:
        shutil.rmtree(snap, ignore_errors=True)
    return out


def _changed(project: Path, since: float) -> list[Path]:
    out = []
    for pat in (".claude/canvas/*.yml", ".claude/diamonds/*.yml"):
        out += [f for f in project.glob(pat) if f.is_file() and f.stat().st_mtime > since]
    return sorted(out)


def _schema_problems(changed: list[Path]) -> list[str]:
    cwc = _load("canvas_write_check")
    # sibling module in this plugin; its loader is the one place the validator import is handled
    vc = cwc._load_validator()[0] if cwc else None  # noqa: SLF001
    if vc is None:
        return ["schema not checked: PyYAML/jsonschema are not installed"]
    return [e for f in changed for e in cwc.errors_for(f, vc)]


def _diamond_problems(project: Path, state: Path, session: str) -> list[str]:
    active = project / ACTIVE_REL
    before_f = state / "active.yml.before"
    before = before_f.read_text(encoding="utf-8") if before_f.exists() else ""
    sl = _load("scale_locks")
    dr = _load("diamond_rulings")
    if dr is not None:
        dr.record(project, session)
    if sl is None:
        return ["diamonds/active.yml changed and the scale locks could not be loaded"]
    try:
        after = active.read_text(encoding="utf-8")
        out = sl.violations_between(str(project), before, after)
    except sl.UnreadableError as exc:
        return [f"diamonds/active.yml does not parse after the command: {exc}"]
    # v0.307.4 (control audit P6): the L5 floor and the personal-data confirmation ran only on the
    # edit tools, where the person is asked. A shell write cannot ask after the fact; it is told.
    moved, personal = sl.launch_moves(before, after), sl.new_person_exposures(before, after)
    if moved:
        out.append(f"it moved {', '.join(moved)} (L5) into delivery or completion, which the "
                   "L5 human-approval floor leaves to the person: put it back, and make the move "
                   "with Edit or Write, where the person is asked")
    if personal:
        out.append(f"it recorded an exposure with personal or sensitive data "
                   f"({', '.join(personal)}), which the person confirms (ruling g): take it out, "
                   "and record it with Edit or "
                   "Write, where the person is asked")
    return out


def post(payload: dict, project: Path) -> int:
    state = project / STATE_REL
    try:
        since = float((state / "stamp").read_text())
    except (OSError, ValueError):
        return 0  # no stamp: pre did not run (not a Mycelium project, or an unwritable state dir)
    extras: dict = {}
    put_back = _put_back_guard_state(project, state, _call_id(payload), extras)
    undone, reported = extras.get("settings") or ([], [])
    committed = _secrets_committed(extras.get("git") or {})
    changed = _changed(project, since)
    problems = _schema_problems(changed) if changed else []
    if changed and project / ACTIVE_REL in changed:
        problems += _diamond_problems(project, state, str(payload.get("session_id") or ""))
    reasons, out = [], {}
    if put_back:
        told = ("A shell command changed a file that switches one of Mycelium's stops off, and "
                "you were not asked first: " + "; ".join(put_back) + ". Mycelium put it back, so "
                "the stop is as it was. If you want that file changed, write it yourself in your "
                "own terminal, or have the agent write it with a plain command that names the "
                "file, so that you are asked.")
        out["systemMessage"] = "Mycelium: " + told
        reasons.append(told + " Do not try another way of writing it: tell the person what "
                       "happened and let them decide.")
    if undone or reported:
        told = []
        if undone:
            told.append(
                "A shell command set a Mycelium switch in a Claude Code settings file, and you "
                "were not asked first: " + "; ".join(undone) + ". Such a switch turns a stop off "
                "or changes how the hooks decide. If you want it set, write it yourself, or have "
                "the agent make the change with its edit tool, where you are asked.")
        if reported:
            told.append(
                "While a shell command ran, " + "; ".join(reported) + ", which switches the "
                "Mycelium plugin off. Mycelium has not changed it: Claude Code's own plugin "
                "commands write that key, and you may have run one. If you did not, set it back "
                "to true.")
        out["systemMessage"] = " ".join(
            x for x in (out.get("systemMessage"), "Mycelium: " + " ".join(told)) if x)
        reasons.append(" ".join(told) + " Do not try another way of setting it: tell the person "
                       "what happened and let them decide.")
    if committed:
        told = ("A commit this command made holds something that looks like a secret: "
                + "; ".join(committed) + ". Mycelium has not changed the commit, and will refuse "
                "to push it. A new commit on top does not take the value out of history: the "
                "commit has to be amended or redone. If the value was ever real it should be "
                "replaced. A false alarm is yours to wave through.")
        out["systemMessage"] = " ".join(
            x for x in (out.get("systemMessage"), "Mycelium: " + told) if x)
        reasons.append(told + " Do not push. Tell the person what happened and let them decide.")
    if problems:
        names = ", ".join(str(f.relative_to(project)) for f in changed)
        reasons.append(
            f"A shell command changed {names}, and the change breaks Mycelium's rules:\n"
            + "\n".join(f"  - {p}" for p in problems[:10])
            + "\nFix it now with the Edit or Write tool, where the gates run.")
    if reasons:
        print(json.dumps({"decision": "block", "reason": "\n\n".join(reasons), **out}))
    return 0


def main(argv: list[str] | None = None) -> int:
    mode = (argv or sys.argv[1:] or [""])[0]
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0  # the runtime refuses a malformed payload before any command runs
    if not isinstance(payload, dict) or mode not in ("pre", "post"):
        return 0
    project = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
    return pre(payload, project) if mode == "pre" else post(payload, project)


if __name__ == "__main__":
    sys.exit(main())
