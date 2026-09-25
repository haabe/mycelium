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

It never undoes a change. Stdlib plus the sibling scripts; without PyYAML the post half says once
that it could not judge (canvas_write_check handles the schema side the same way).
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import _hook_input as hi  # noqa: E402

ACTIVE_REL = ".claude/diamonds/active.yml"
STATE_REL = Path(".claude") / "state" / "bash-guard"
ALLOWED_WRITERS = ("derive_closing_path.py",)  # Mycelium's own writers of diamond state


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except (SystemExit, ImportError):  # SPEAKS: callers report that the check could not run
        return None
    return mod


def writes_active(cmd: str, project: str) -> bool:
    """Does this command visibly write diamonds/active.yml?"""
    if any(w in cmd for w in ALLOWED_WRITERS):
        return False
    scan = hi.bash_write_targets(cmd, project)
    if any(t.inside and t.rel == ACTIVE_REL for t in scan.targets):
        return True
    names_it = "diamonds/active.yml" in cmd
    return names_it and bool(scan.opaque)


def pre(payload: dict, project: Path) -> int:
    ti = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    cmd = ti.get("command") if isinstance(ti.get("command"), str) else ""
    if writes_active(cmd, str(project)):
        print("Mycelium: refused. This shell command writes .claude/diamonds/active.yml, where "
              "the scale-lock gate cannot judge it: entry locks, phase-move gates and the ruling "
              "record only run on the Edit and Write tools. Make the change with Edit or Write "
              "(/mycelium:diamond-progress for a phase move). Reading the file is never refused.",
              file=sys.stderr)
        return 2
    state = project / STATE_REL
    active = project / ACTIVE_REL
    if (project / ".claude").is_dir():
        try:
            state.mkdir(parents=True, exist_ok=True)
            if active.exists():
                shutil.copyfile(active, state / "active.yml.before")
            else:
                (state / "active.yml.before").unlink(missing_ok=True)
            (state / "stamp").write_text(repr(time.time()))
        except OSError:
            return 0  # SPEAKS in post: with no stamp, post says it could not tell what changed
    return 0


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
        return sl.violations_between(str(project), before, active.read_text(encoding="utf-8"))
    except sl.UnreadableError as exc:
        return [f"diamonds/active.yml does not parse after the command: {exc}"]


def post(payload: dict, project: Path) -> int:
    state = project / STATE_REL
    try:
        since = float((state / "stamp").read_text())
    except (OSError, ValueError):
        return 0  # no stamp: pre did not run (not a Mycelium project, or an unwritable state dir)
    changed = _changed(project, since)
    if not changed:
        return 0
    problems = _schema_problems(changed)
    if project / ACTIVE_REL in changed:
        problems += _diamond_problems(project, state, str(payload.get("session_id") or ""))
    if problems:
        names = ", ".join(str(f.relative_to(project)) for f in changed)
        print(json.dumps({"decision": "block", "reason": (
            f"A shell command changed {names}, and the change breaks Mycelium's rules:\n"
            + "\n".join(f"  - {p}" for p in problems[:10])
            + "\nFix it now with the Edit or Write tool, where the gates run.")}))
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
