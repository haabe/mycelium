"""Shell commands that change canvas or diamond state are judged like edits are (v0.253.2).

E2E run 24: the builder rewrote `privacy-assessment.yml` through a shell command, the schema check
(a PostToolUse hook on Write/Edit/MultiEdit) never saw it, and the file stood invalid. Reading the
hook registrations then showed the larger hole: `scale-lock-gate.sh` is registered on the edit
tools only, so `sed -i`, a heredoc or a Python one-liner could open a diamond past its entry lock or
move it forward without its gates, and neither the locks, the ruling recorder nor the schema check
would run.

Two halves, one script:

  pre   (PreToolUse Bash) refuses a command whose write target is diamonds/active.yml itself: a
        redirect, `sed -i`, `tee` or `mv` naming the file. The remedy is the Edit or Write tool,
        where the scale-lock gate judges the change. Reads are never refused. Mycelium's own
        writers (`derive_closing_path.py`, which sets `closes_on`, and `migrate_phase.py`) are
        allowed. It also snapshots diamonds/active.yml and stamps the time, for the second half.
        Since v0.325.0 it no longer guesses at writes it cannot see (a script, a variable path):
        those are the comparison's, below.
  post  (PostToolUse Bash) looks at canvas and diamonds files changed since the stamp: each is
        checked against its schema, and a changed diamonds file is judged against the snapshot by
        the same verdict the write hook uses (`scale_locks.violations_between`), and its rulings
        recorded. What is found goes to the agent in the same turn. This catches the writes the
        first half cannot see, such as a path built in a variable.

It never undoes a change to the canvas, and undoes one to the diamonds file in one case only
(v0.324.0, below). Stdlib plus the sibling scripts;
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

Until 0.324.0 this was the one place the script undid anything, on the maintainer's ruling of
2026-10-11 ("Put it back and tell me"): left as written, the stop is off until someone notices. It
touches only those seven files, never code or canvas. Not put back: a change the person makes in
their own terminal (no hook sees it), a change made with `MYCELIUM_GUARD_STATE_EDIT=1` in the
person's own shell, and Mycelium's own upgrade script run on its own.

THE FOLDERS A DELIVERY CYCLE MAY WRITE TO ARE PUT BACK TOO (v0.324.0). The scope hold reads
`in_scope_paths` from the diamonds file, and a write that names, changes or removes it is put to
the person by `scope-gate.sh`, which like every gate can only ask about a write it can read. A
script whose command line names no file (`python3 tool.py`) could delete the record or take the
folders off it; afterwards nothing was said and the hold was gone. Found while building the hold,
by trying it in a scratch project; the bar the idea had been held to did not cover it.

  pre     keeps a copy of the diamonds file with the call's own snapshot.
  edited  (PostToolUse on the edit tools, from `diamond-state-audit.sh`) refreshes that copy in
          every snapshot still open, so a change the person said yes to while a command was
          running is not taken for the command's.
  post    compares what each delivery cycle names. If the command changed it, the WHOLE diamonds
          file is put back as that copy, and the person and the agent are told.

Maintainer's ruling 2026-10-13 ("Put it back, tell me"), with the cost said to him: anything else
the command changed in that file is undone with it. A shell command is not meant to write that
file at all (the first half refuses the ones it can read). Not put back: a record the command
created where there was none (it is said, and left), and the three cases above. What this does
not catch: a process the command leaves running that writes after the command has returned, and a
script written to rewrite the snapshot as well. It is a check on drift, not a sandbox.

ANY CHANGE A SHELL COMMAND MAKES TO THE DIAMONDS FILE IS PUT BACK (v0.325.0). Until then the
comparison above spoke only about the folders, and the first half judged the rest of the file by
the command's text, which failed both ways in one session (dogfood 2026-10-14). `python3
newbar.py values.yml`, a script that opened the diamonds file itself, replaced a whole definition
of done, and nothing was said or undone; the scale locks found nothing to object to, because a
changed bar breaks no lock. Minutes later a heredoc appending to another file was refused because
its text mentioned the path. So the file is judged, not the command:

  post    if the command changed the diamonds file at all, the file is put back as the copy, the
          command's version is kept under .claude/state/bash-guard/put-back/ and named, and the
          person and the agent are told which diamonds the command touched and what the scale
          locks would have said about it.

Not put back, besides the cases above: Mycelium's own writers run on their own, when the script
run is this plugin's own copy (by name alone, a script the agent wrote would pass), and a git
command that leaves the file as it is committed at HEAD (a pull, a checkout, a reset, a stash),
or that stops mid-merge, mid-rebase, mid-cherry-pick or mid-revert, unless the command itself
made a commit that changed the file. Those are history the person keeps, not a
write. What is put back although the person may want it: `git stash pop` of their own changes
(the popped version is the one kept, and named). What this does not catch, besides the two above:
a file committed by one command and restored from HEAD by the next.

MYCELIUM'S OWN WRITE WHILE A COMMAND RUNS IS NOT THE COMMAND'S (v0.325.1). Session start runs
`derive_closing_path.py --all --write` in the background, and the agent's first command can run
at the same time. On 0.325.0 that write was put back as the command's, and the person was told
the agent had changed the file without asking (dogfood 2026-10-15, on a read-only `git log`); the
script went on writing after the put-back, so the file matched neither version. Now the writer
applies its own edit to the copies taken before each running command, before it writes
(`own_writer_writes`), so the comparison sees only what the command did. A command that also
changed the file is put back as before, to a version that keeps the writer's change.
"""
from __future__ import annotations

import difflib
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
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
#: The copy of the diamonds file kept with each call's snapshot (v0.324.0).
RECORD_SNAP = "record.before"
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
    """Is diamonds/active.yml itself the target of a write in this command?

    v0.325.0: only a target that IS the file. Until then a command that named the file anywhere
    and also wrote somewhere unseen (a script, a variable path) was refused, which refused a heredoc
    that only mentioned the path while appending to another file, and still let through a script
    that named the file only inside itself. A write this cannot see is put back after the command
    (`_put_back_the_record`), so guessing here bought nothing but false refusals."""
    cmd = _without_comments(cmd)
    if _MOVES_ACTIVE.search(cmd):
        return True
    if _OWN_WRITER.fullmatch(cmd):
        return False
    scan = hi.bash_write_targets(cmd, project)
    return any(t.inside and t.rel == ACTIVE_REL for t in scan.targets)


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
            cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) else ""
            _snapshot_guard_state(project, state, cmd, _call_id(payload),
                                  Path(cwd) if cwd else project)
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


_ROOT_VARS = ("${CLAUDE_PLUGIN_ROOT}", "$CLAUDE_PLUGIN_ROOT")
_OWN_SCRIPT = re.compile(r"\"?([^\s;&|<>`$()\"]*?(?:"
                         + "|".join(re.escape(w) for w in ALLOWED_WRITERS) + r"))\"?")


def _runs_own_writer(cmd: str, base: Path) -> bool:
    """Is this command one of Mycelium's own writers of the diamonds file, run on its own, AND is
    the script it runs this plugin's own copy (v0.325.0)? By name alone, a script the agent wrote
    and called `derive_closing_path.py` would have been let through. `${CLAUDE_PLUGIN_ROOT}` is
    read as this plugin's folder, since some runtimes leave it in the command."""
    text = _without_comments(cmd)
    for var in _ROOT_VARS:
        text = text.replace(var, str(HERE.parent))
    m = _OWN_SCRIPT.search(text) if _OWN_WRITER.fullmatch(text) else None
    if m is None:
        return False
    script = Path(m.group(1)).expanduser()
    try:
        return (script if script.is_absolute() else base / script).resolve().parent == HERE
    except OSError:
        return False  # SPEAKS: not shown to be Mycelium's own, so its change is put back and told


def _snapshot_guard_state(project: Path, state: Path, cmd: str, call: str,
                          base: Path | None = None) -> None:
    base = base or project
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
    # v0.325.0: Mycelium's own writer of the diamonds file, run on its own, is not put back.
    own_writer = _runs_own_writer(cmd, base)
    # v0.322.6: which Mycelium switches each Claude Code settings file carries now (their keys and
    # values, not the files), and whether the person's override was on BEFORE the command. Read
    # afterwards it could have been set by the command itself, through the settings file.
    settings = {name: _switches_in(path) for name, path in _settings_files(project).items()}
    # v0.324.0: the diamonds file as it is now, for the folders a delivery cycle may write to.
    record = (project / ACTIVE_REL).is_file()
    if record:
        shutil.copyfile(project / ACTIVE_REL, snap / RECORD_SNAP)
    (snap / "index.json").write_text(json.dumps({
        "files": files, "asked": asked, "own": own, "own_writer": own_writer, "settings": settings,
        "override": hi.human_override(), "git": _git_before(project), "record": record}))


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
    `_put_back_settings` returns, `git`, where the commit pointer was before the command, and
    `record`, what `_put_back_the_record` did to the diamonds file."""
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
            extras["record"] = _put_back_the_record(project, state, call, index)
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


def _hold_lines(before: str | None, after: str | None) -> list[str]:
    """What the command changed in where delivery cycles may write, one line per cycle (v0.324.0).
    OSError when the scope hold's own script cannot be loaded."""
    sc = _load("scope_check")
    if sc is None:
        raise OSError("the scope hold's own script could not be loaded")
    return sc.changed_between(before, after)


_ID_LINE = re.compile(r"^(\s*)-\s+id:\s*['\"]?([^'\"\s#]+)")


def _owners(lines: list[str]) -> list[str]:
    """For each line, the id of the diamond entry it sits in: the `- id:` lines at the shallowest
    indentation in the file are the diamonds; a line above the first is the file's own."""
    found = [(len(m.group(1)), i, m.group(2)) for i, ln in enumerate(lines)
             if (m := _ID_LINE.match(ln))]
    top = min((d for d, _, _ in found), default=0)
    starts = {i: name for d, i, name in found if d == top}
    out, cur = [], "the top of the file"
    for i in range(len(lines)):
        cur = starts.get(i, cur)
        out.append(cur)
    return out


def _diamonds_touched(before: str, after: str) -> list[str]:
    """Which diamonds the command changed, in the order they appear, by the entry each changed
    line falls in. Read from the lines, not parsed, so it also answers for a file that no longer
    parses."""
    a, b = before.splitlines(), after.splitlines()
    oa, ob = _owners(a), _owners(b)
    out: list[str] = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        names = oa[i1:i2] + ob[j1:j2] or ([ob[j1]] if j1 < len(ob) else [oa[i1]] if i1 < len(oa)
                                          else ["the end of the file"])
        for n in names:
            if n not in out:
                out.append(n)
    return out


def _git_left_it(project: Path, index: dict, after: str | None) -> bool:
    """Did git, and not a write, leave the file as it is? True when the file now reads as it is
    committed at HEAD, or the repository is stopped mid-merge, mid-rebase, mid-cherry-pick or
    mid-revert; never when the command itself made a commit that changed the file."""
    git = index.get("git") if isinstance(index.get("git"), dict) else {}
    repo = git.get("repo")
    cs = _load("commit_scan") if repo and after is not None else None
    if cs is None:
        return False
    rel = Path(os.path.relpath(project / ACTIVE_REL, repo)).as_posix()
    try:
        for sha in cs.made_commits(repo, git.get("head") or "", git.get("reflog")):
            # sibling module in this plugin; its runner is the one place git is called from
            done = cs._git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "--root",  # noqa: SLF001
                           sha, "--", rel)
            if done.returncode != 0 or done.stdout.strip():
                return False
        for name in ("MERGE_HEAD", "REBASE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD"):
            where = cs._git(repo, "rev-parse", "--git-path", name)  # noqa: SLF001
            if where.returncode == 0 and Path(repo, where.stdout.strip()).exists():
                return True
        shown = cs._git(repo, "show", f"HEAD:{rel}")  # noqa: SLF001
    except (OSError, subprocess.SubprocessError):
        return False  # SPEAKS: an unreadable repository is no proof of git; the change is put back
    return shown.returncode == 0 and shown.stdout == after


def _would_have(project: Path, before: str | None, after: str | None) -> list[str]:
    """What the scale locks say about the command's version, for the agent to know what the change
    would also have broken. Nothing when either side is missing or cannot be read."""
    sl = _load("scale_locks")
    if sl is None or before is None or after is None:
        return []
    try:
        return list(sl.violations_between(str(project), before, after))[:5]
    except sl.UnreadableError as exc:
        return [f"the file does not parse as the command left it: {exc}"]


def _keep(state: Path, call: str, text: str) -> str:
    """Keep the command's version of the file, so that putting it back loses nothing."""
    keep = state / "put-back"
    _state_dir.prepare_dir(keep)
    path = keep / f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{call}-active.yml"
    path.write_text(text, encoding="utf-8")
    return (STATE_REL / "put-back" / path.name).as_posix()


def _put_back_the_record(project: Path, state: Path, call: str, index: dict) -> dict:
    """What the command did to the diamonds file (v0.324.0 for the folders, v0.325.0 for all of it).

    Returns {} when it changed nothing that is put back, else `hold` (one line per delivery cycle
    whose folders changed), `touched` (the diamonds whose lines changed), `would` (what the scale
    locks say about the command's version), `kept` (where that version is kept), `removed` and
    `outcome`: "put back", or why not. The whole file is put back as the copy kept before the
    command, or as an edit tool last left it while the command ran. Nothing is compared for a
    snapshot written by an earlier version (it keeps no copy), for Mycelium's own writers run on
    their own, or when the person's override was on before the command; nothing is put back when
    git left the file as it is (`_git_left_it`). A file the command created where there was none
    is said only when it names folders, and left."""
    if ("record" not in index or index.get("own") or index.get("own_writer")
            or index.get("override", hi.human_override())):
        return {}
    active, copy = project / ACTIVE_REL, state / GUARD_SNAP / call / RECORD_SNAP
    try:
        before = (copy.read_text(encoding="utf-8", errors="replace") if index.get("record")
                  else None)
        after = active.read_text(encoding="utf-8", errors="replace") if active.is_file() else None
    except OSError as exc:  # SPEAKS: post tells the person and the agent it could not compare
        return {"unread": f"{ACTIVE_REL} or its copy from before the command could not be read "
                          f"({type(exc).__name__}), so whether the command changed it is not "
                          "known and nothing was put back"}
    if before == after or _git_left_it(project, index, after):
        return {}
    try:
        hold = _hold_lines(before, after)
    except OSError as exc:
        hold = [f"(WARNING: the folders could not be compared: {exc})"]
    if before is None:
        if not hold:
            return {}
        return {"hold": hold, "touched": [], "would": [], "kept": "", "removed": False,
                "outcome": "there was no diamonds file before the command, so nothing was put back"}
    rec = {"hold": hold, "touched": _diamonds_touched(before, after or ""),
           "would": _would_have(project, before, after), "kept": "", "removed": after is None,
           "outcome": "put back"}
    if after is not None:
        try:
            rec["kept"] = _keep(state, call, after)
        except OSError:
            rec["kept"] = ""  # SPEAKS: the told text says the command's version was not kept
    rec["outcome"] = _restore(active, copy, before)
    return rec


def _restore(active: Path, copy: Path, before: str) -> str:
    """Put the diamonds file back as it was; "put back", or why not."""
    try:
        if active.is_file():
            _replace_text(active, before)
        else:
            _state_dir.prepare_dir(active.parent)
            shutil.copyfile(copy, active)
    except OSError as exc:
        return (f"COULD NOT BE PUT BACK ({type(exc).__name__}); the diamonds file is as the "
                "command left it")
    return "put back"


def _record_told(rec: dict) -> str:
    if rec.get("unread"):
        return (f"After a shell command, {rec['unread']}. Look at the file before going on; it is "
                "written with the Edit or Write tool.")
    hold = rec.get("hold") or []
    if hold:
        told = ("A shell command changed where a delivery cycle may write, and you were not asked "
                "first: " + "; ".join(hold) + ". ")
    else:
        what = ", ".join(rec.get("touched") or []) or "its contents"
        told = f"A shell command changed {ACTIVE_REL} ({what}), and you were not asked first. "
    if rec["outcome"] == "put back":
        told += (f"Mycelium put {ACTIVE_REL} back as it was before the command"
                 + (", so the hold is as it was" if hold else "")
                 + "; anything else that command changed in that file is undone with it. ")
        if rec.get("kept"):
            told += f"The command's version is kept at {rec['kept']}. "
        elif not rec.get("removed"):
            told += "The command's version could not be kept. "
    else:
        told += f"Mycelium has not changed that file: {rec['outcome']}. "
    if rec.get("would"):
        told += "The scale locks would also have objected: " + "; ".join(rec["would"]) + ". "
    if hold:
        return told + ("Where the agent may write is yours to say. If you want the folders "
                       "changed, have the agent make the change with its edit tool, where you are "
                       "asked.")
    return told + ("The diamonds file is written with the Edit or Write tool, where the entry "
                   "locks, the decision gates and the questions put to you run. If the change is "
                   "wanted, have the agent make it that way (/mycelium:diamond-progress records a "
                   "decision).")


def _settings_told(undone: list[str], reported: list[str]) -> str:
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
    return " ".join(told)


def edited(payload: dict, project: Path) -> int:
    """An edit tool wrote the diamonds file (PostToolUse, from diamond-state-audit.sh). Every
    snapshot still open takes the file as it is now for its "before": that write went through
    the gates, and the person was asked where they are asked, so a shell command that is
    still running must not be held to have made it."""
    try:
        targets = hi.target_paths(payload.get("tool_input"))
    except hi.BadInputError:
        return 0  # SPEAKS: the gates refuse a call they cannot read before it runs
    if not any(hi.resolve(path, str(project), key=key).rel == ACTIVE_REL
               for key, path in targets):
        return 0
    root, active = project / STATE_REL / GUARD_SNAP, project / ACTIVE_REL
    if not root.is_dir() or not active.is_file():
        return 0
    for snap in root.iterdir():
        try:
            index = json.loads((snap / "index.json").read_text())
            if not isinstance(index, dict) or "record" not in index:
                continue
            shutil.copyfile(active, snap / RECORD_SNAP)
            if not index["record"]:
                index["record"] = True
                (snap / "index.json").write_text(json.dumps(index))
        except (OSError, ValueError):
            continue  # SPEAKS: that snapshot's own post half says when it cannot be read
    return 0


def own_writer_writes(project: Path, change) -> None:
    """Mycelium's own writer is about to write the diamonds file (v0.325.1). `change` is its edit
    as a function of the file's text; it is applied to every copy taken before a command still
    running, so the comparison after that command sees this write in both versions and judges
    only what the command did. Called by `derive_closing_path.py`, which session start runs in the
    background while the agent's first command may be running (dogfood 2026-10-15: a `git log`
    was told it had changed the file, and the write was put back mid-run, leaving the file as
    neither version). The edit is applied, not the file copied: a command that changed the file
    and then ran the writer would otherwise have its own change taken as the writer's. Called
    BEFORE the write, so a comparison that falls between the two puts back a file that already
    holds this change."""
    state = project / STATE_REL
    copies = [state / "active.yml.before"]
    if (state / GUARD_SNAP).is_dir():
        copies += [snap / RECORD_SNAP for snap in (state / GUARD_SNAP).iterdir()]
    for copy in copies:
        try:
            if not copy.is_file():
                continue
            text = copy.read_text(encoding="utf-8")
            new = change(text)
            if new != text:
                _replace_text(copy, new)
        except (OSError, ValueError):
            continue  # SPEAKS: that command's post half puts this write back and says so


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
    record = extras.get("record") or {}
    changed = _changed(project, since)
    if record.get("outcome") == "put back":
        # The file is as it was, written by this script just now: nothing of the command's
        # is left in it to judge.
        changed = [f for f in changed if f != project / ACTIVE_REL]
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
    if record:
        told = _record_told(record)
        out["systemMessage"] = " ".join(
            x for x in (out.get("systemMessage"), "Mycelium: " + told) if x)
        reasons.append(told + " Do not try another way of writing it: tell the person what "
                       "happened and let them decide.")
    if undone or reported:
        told = _settings_told(undone, reported)
        out["systemMessage"] = " ".join(
            x for x in (out.get("systemMessage"), "Mycelium: " + told) if x)
        reasons.append(told + " Do not try another way of setting it: tell the person "
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
    if not isinstance(payload, dict) or mode not in ("pre", "post", "edited"):
        return 0
    project = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
    return {"pre": pre, "post": post, "edited": edited}[mode](payload, project)


if __name__ == "__main__":
    sys.exit(main())
