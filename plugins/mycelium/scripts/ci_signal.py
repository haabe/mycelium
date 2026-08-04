#!/usr/bin/env python3
"""Bring CI's verdict back into the session that caused it.

THE GAP THIS CLOSES (dogfood 2026-08-03/04). The dogfood workflow went red at
13e3de47 and stayed red for THIRTEEN CONSECUTIVE PUSHES across two days. Every
run reported failure on push. The agent ran `gh run watch` on three upstream
PRs the same day — waiting out a 2m42s run each time — and never once on the
repo it was actually committing to.

The tempting diagnosis is discipline. The real one is architecture: the flow was
one-way. Local push -> CI runs -> the result lives on GitHub and never comes
back. The harness has five hook points (SessionStart, PreToolUse, PostToolUse,
Stop, UserPromptSubmit) and not one of them looked outward at whether the build
passed. On a pull request you are forced to look; on `main` nothing asks.

Worse, the roadmap's own CLAUDE.md described `decision-log.md` as "Decision
provenance + CI signal capture" — four CI mentions in ~5,000 lines, none from
the thirteen failures. A capability claimed in the file that orients every
session, and not built. That is the documented-not-operational error this
project audits others for, committed against itself.

NO PUSH TRACKING, AND THAT IS THE DESIGN. The obvious build records "a push
happened" via a PostToolUse matcher and checks it later, which means new session
state to create, invalidate and get wrong. Unnecessary: GitHub already knows. We
ask what the newest run for this branch concluded and compare its head SHA to
local HEAD. If they match, that run is OUR run. Nothing to remember.

The one piece of state is a dedupe + rate-limit stamp, so a red build is
reported ONCE rather than nagged every turn, and so a Stop hook firing on every
response does not make a network call every time. It follows the preflight
stamp's path convention (per-user, per-project, under TMPDIR) for the reason
recorded there: a world-predictable shared path was a real bug.

FAILS OPEN, ALWAYS. No gh, no auth, no network, no workflows, not a repo,
malformed JSON — all exit 0 in silence. A session that breaks because a build
status could not be fetched is worse than the gap this closes.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

#: Don't hit the network more than this often. Stop fires after every response;
#: a round-trip per turn would make the harness feel slow for a signal that
#: changes on the order of minutes.
_MIN_INTERVAL_S = 90

#: `gh` can hang on a bad network. Bound it hard — this runs in the user's turn.
_TIMEOUT_S = 8


def _stamp_path(project: Path) -> Path:
    uid = os.getuid() if hasattr(os, "getuid") else 0
    phash = hashlib.md5(str(project).encode()).hexdigest()[:12]  # noqa: S324
    tmp = os.environ.get("TMPDIR", "/tmp")  # noqa: S108
    return Path(tmp) / f"mycelium-ci-signal-{uid}-{phash}.json"


def _read_stamp(p: Path) -> dict:
    try:
        v = json.loads(p.read_text())
        return v if isinstance(v, dict) else {}
    except Exception:                                # noqa: BLE001
        return {}


def _write_stamp(p: Path, stamp: dict) -> None:
    with contextlib.suppress(Exception):             # a stamp is a nicety
        p.write_text(json.dumps(stamp))


def _run(args: list[str], cwd: Path) -> str | None:
    try:
        r = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                           timeout=_TIMEOUT_S, check=False)
    except Exception:                                # noqa: BLE001 — fail open
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def _repo_context(project: Path) -> tuple[str, str] | None:
    """(head_sha, branch), or None when there is nothing worth asking about.

    Cheapest bail-outs live here so the common case — a repo with no CI —
    costs no subprocess at all.
    """
    if not (project / ".github" / "workflows").is_dir():
        return None
    head = _run(["git", "rev-parse", "HEAD"], project)
    branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], project)
    if not head or not branch or branch == "HEAD":   # detached: no branch runs
        return None
    return head, branch


def _latest_run(project: Path, branch: str) -> dict | None:
    out = _run(["gh", "run", "list", "--branch", branch, "--limit", "1",
                "--json", "databaseId,conclusion,status,headSha,name"], project)
    if not out:
        return None
    try:
        runs = json.loads(out)
    except Exception:                                # noqa: BLE001
        return None
    if not isinstance(runs, list) or not runs or not isinstance(runs[0], dict):
        return None
    return runs[0]


def _is_our_failure(run: dict, head: str) -> bool:
    """A completed failure for the commit actually checked out.

    The SHA match is the load-bearing part. Reading the newest run WITHOUT it
    reports the previous commit's result — which is how this project reported
    "CI: success" for a push that had failed, on the same day the hook was
    written. A hook that misattributes runs teaches its reader to ignore it.
    """
    return (run.get("headSha") == head
            and run.get("status") == "completed"
            and run.get("conclusion") not in (None, "success", "skipped",
                                              "cancelled", "neutral"))


def check(project: Path, now: float | None = None,
          fresh_session: bool = False) -> str | None:
    """The message to surface, or None when there is nothing to say.

    `fresh_session` skips both the rate limit and the once-per-run dedupe. A new
    session is a new agent with no memory of what the last one was told, so
    suppressing a red build because a PREVIOUS session heard about it would
    reproduce the exact gap this closes — which is how thirteen pushes happened.
    """
    now = time.time() if now is None else now
    ctx = _repo_context(project)
    if ctx is None:
        return None
    head, branch = ctx

    stamp_file = _stamp_path(project)
    stamp = _read_stamp(stamp_file)
    if not fresh_session and \
            now - float(stamp.get("checked_at") or 0) < _MIN_INTERVAL_S:
        return None

    run = _latest_run(project, branch)
    stamp["checked_at"] = now
    _write_stamp(stamp_file, stamp)
    if run is None or not _is_our_failure(run, head):
        return None

    run_id = run.get("databaseId")
    if not fresh_session and run_id is not None \
            and run_id == stamp.get("reported_id"):
        return None                                  # said once already
    stamp["reported_id"] = run_id
    _write_stamp(stamp_file, stamp)

    return (
        f"MYCELIUM CI SIGNAL — the workflow for the commit you just pushed "
        f"FAILED.\n"
        f"  branch {branch} · run {run_id} · {run.get('name') or 'workflow'} · "
        f"conclusion {run.get('conclusion')}\n"
        f"  This is the run for HEAD ({head[:8]}) — your commit, not someone "
        f"else's.\n"
        f"  Read it before continuing: gh run view {run_id} --log-failed\n"
        f"  Said once per run, not per turn. On 2026-08-03/04 this project "
        f"pushed to a red build thirteen consecutive times because nothing "
        f"carried the result back into the session."
    )


def main() -> int:
    with contextlib.suppress(Exception):
        json.load(sys.stdin)          # drain the hook payload; unused
    project = Path(os.environ.get("CLAUDE_PROJECT_DIR") or ".").resolve()
    fresh = "--session-start" in sys.argv
    try:
        msg = check(project, fresh_session=fresh)
    except Exception as exc:                         # noqa: BLE001
        # NEVER BREAK THE SESSION — but never go quiet either. A broad catch
        # here would swallow any bug in check() and the hook would simply stop
        # firing, which is the EXACT failure it was built to fix: a mechanism
        # reporting nothing, read as healthy. So the crash is recorded where a
        # human can find it rather than only vanishing.
        stamp_file = _stamp_path(project)
        stamp = _read_stamp(stamp_file)
        stamp["last_error"] = f"{type(exc).__name__}: {exc}"[:300]
        stamp["last_error_at"] = time.time()
        _write_stamp(stamp_file, stamp)
        print(f"mycelium ci-signal: disabled itself after an internal error "
              f"({type(exc).__name__}); details in {stamp_file}", file=sys.stderr)
        return 0
    if not msg:
        return 0
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart" if fresh else "Stop",
        "additionalContext": msg}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
