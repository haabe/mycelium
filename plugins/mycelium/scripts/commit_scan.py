"""Secrets are stopped at the commit and at the push (v0.323.0).

WHY THIS EXISTS. Until 0.323.0 Mycelium looked for secrets at the moment the agent WROTE a file,
with a short list of its own. Replayed 2026-10-12: an unquoted `KEY=value` passed, an env file was
treated like source code, and nothing ever looked at what was staged. The maintainer's direction:
"Don't let passwords into the repo", "Maybe a security scan in the pre-commit hook is enough?",
"using established scanners are the way to go ... better left to someone who knows it better".

WHAT IT DOES. Three moments, one scanner (gitleaks when it is installed):
  1. Before the agent's `git commit`: what is staged is scanned (and what `-a` or a named path
     would add). A finding refuses the commit.
  2. After any shell command of the agent's: commits the command itself made, by any route, are
     scanned (`bash_state_guard.py` calls `made_commits` and `scan_commits`). Mycelium does not
     rewrite a commit; it says what it found, and the push is where it is stopped.
  3. Before the agent's `git push`: every commit on a local branch that is on no remote is
     scanned. A finding refuses the push.
With no scanner installed the same three moments run Mycelium's own short list
(`_secret_patterns.sh`) and the person is told once a session that it is the weaker check.

WHAT IT DOES NOT DO. It does not scan a write: since 0.323.0 the agent may write a key into a
file (an env file is where one belongs); it may not commit or push one. It does not see a commit
or push the person makes in their own terminal; `/mycelium:setup` offers a git hook for that. It
does not judge the scanner's own ways past a finding (`.gitleaksignore`, `.gitleaks.toml`, an
inline `gitleaks:allow`): those are the person's to write, and `_hook_input.py` asks before the
agent adds one.

A SCAN THAT CANNOT RUN IS A REFUSAL (the 0.319.1 rule). gitleaks answers 0 for clean, a code this
script chooses for "found", and anything else when the scan itself failed; the last is refused
with the scanner's own words, never passed.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _state_dir

FOUND = 42          # gitleaks' exit code for "found", set by --exit-code so an error stays distinct
TIMEOUT = 45        # seconds for one scan; past it the scan "could not run"
MAX_FALLBACK = 2_000_000   # characters of added lines the fallback list reads
MAX_NAMED = 8       # findings named in one refusal; the rest are counted
#: `git commit` or `git push` where a command starts: at the beginning, after a separator, an
#: opening bracket or quote, or a shell keyword; with variable assignments and a wrapper word in
#: front. The words inside a longer argument ("remember to git commit") do not count. A form this
#: misses is still scanned: after the command for a commit, and at the push.
_GIT = re.compile(
    r"(?:^|[;&|(`\n\"']|\$\(|\b(?:then|do|else)\s)\s*(?:\w+=\S+\s+)*"
    r"(?:(?:sudo|command|time|exec|nohup)\s+)*"
    r"git((?:\s+(?:-[cC]\s+\S+|--[\w-]+(?:=\S+)?))*)\s+(commit|push)\b")
_SEPARATOR = re.compile(r"\r?\n|&&|\|\||;|\|")
#: commit options that take the next word as their value, so that word is not a path or a flag
_TAKES_VALUE = {"-m", "-F", "-C", "-c", "-t", "--message", "--file", "--reuse-message",
                "--reedit-message", "--fixup", "--squash", "--author", "--date", "--template",
                "--cleanup", "--pathspec-from-file", "--trailer"}
#: reflog subjects that mean the command itself made a commit (a pull, a checkout, a reset or a
#: fast-forward merge moves the pointer to commits that arrived some other way)
_MADE = ("commit", "cherry-pick", "revert", "am", "rebase")


def _git(repo: str, *args: str, timeout: int = 15) -> subprocess.CompletedProcess:
    env = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}  # a hook never takes the index lock
    return subprocess.run(["git", "-C", repo, *args], text=True, capture_output=True, env=env,
                          timeout=timeout, check=False)


def repo_of(folder: str) -> str | None:
    """The top of the git repository `folder` is in, or None."""
    try:
        done = _git(folder, "rev-parse", "--show-toplevel")
    except (OSError, subprocess.SubprocessError):
        return None  # SPEAKS: no git, or no repository, means nothing can be committed from here
    return done.stdout.strip() if done.returncode == 0 and done.stdout.strip() else None


_CD = re.compile(r"(?:^|[;&|(\n])\s*cd\s+(\"[^\"]+\"|'[^']+'|[^\s;&|)]+)")
_DASH_C = re.compile(r"\s-C\s+(\"[^\"]+\"|'[^']+'|\S+)")


def where_it_runs(command: str, cwd: str) -> list[str]:
    """The folders the command's commits and pushes happen in: for each `git commit` or
    `git push`, every `cd` before it in order and a `git -C <folder>`, resolved against `cwd`. A
    folder the text does not spell out (a variable, a subshell's own `cd`) is not followed; the
    commit is then still scanned afterwards if it lands in the project's repository, and at its
    push."""
    out: list[str] = []
    for m in _GIT.finditer(command):
        folder = cwd
        for raw in _CD.findall(command[:m.start() + 1]) + _DASH_C.findall(m.group(1) or ""):
            path = os.path.expanduser(raw.strip("\"'"))
            folder = path if os.path.isabs(path) else os.path.join(folder, path)
        folder = os.path.normpath(folder)
        if folder not in out:
            out.append(folder)
    return out


def what_it_runs(command: str) -> dict:
    """What a shell command does with git that matters here: {"commit", "wider", "no_verify",
    "push"}. `wider` is a commit that takes more than the index: `-a`, `--all`, or a named path."""
    out = {"commit": False, "wider": False, "no_verify": False, "push": False}
    for m in _GIT.finditer(command):
        tail = _SEPARATOR.split(command[m.end():], maxsplit=1)[0]
        if m.group(2) == "push":
            out["push"] = True
            continue
        out["commit"] = True
        try:
            words = shlex.split(tail)
        except ValueError:
            out["wider"] = True  # an unbalanced quote: read the wider case, which scans more
            continue
        skip = False
        for w in words:
            if skip:
                skip = False
            elif w == "--":
                out["wider"] = True
                break
            elif w in _TAKES_VALUE:
                skip = True
            elif w.startswith("--"):
                out["wider"] |= w in ("--all", "--include", "--only")
                out["no_verify"] |= w == "--no-verify"
            elif w.startswith("-") and len(w) > 1:
                letters = w[1:].split("m", 1)[0] if "m" in w[1:] else w[1:]
                out["wider"] |= "a" in letters
                out["no_verify"] |= "n" in letters
                skip = w.endswith("m") or w[-1] in "FCct"
            else:
                out["wider"] = True  # a named path: the commit takes that path as it is on disk
    return out


# ---------------------------------------------------------------- the two scanners

def scanner() -> str | None:
    return shutil.which("gitleaks")


def _gitleaks(repo: str, args: list[str]) -> tuple[str, list[str]]:
    """("clean" | "found" | "error", lines). `found` lines are `file:line (rule)`, never a value."""
    handle, report = tempfile.mkstemp(prefix="mycelium-scan-", suffix=".json")
    os.close(handle)
    try:
        done = subprocess.run(
            [scanner() or "gitleaks", "git", "--no-banner", "--redact", "--exit-code", str(FOUND),
             "--report-format", "json", "--report-path", report, *args, repo],
            text=True, capture_output=True, timeout=TIMEOUT, check=False)
        if done.returncode == 0:
            return "clean", []
        if done.returncode != FOUND:
            said = (done.stderr or done.stdout).strip().splitlines()[-1:] or ["it said nothing"]
            return "error", [f"gitleaks exited {done.returncode}: {_plain(said[0])[:200]}"]
        with open(report, encoding="utf-8") as fh:
            found = json.load(fh)
    except subprocess.TimeoutExpired:
        return "error", [f"gitleaks did not finish in {TIMEOUT} seconds"]
    except (OSError, ValueError) as exc:
        return "error", [f"gitleaks could not be run or read ({type(exc).__name__})"]
    finally:
        Path(report).unlink(missing_ok=True)
    lines = sorted({f"{f.get('File')}:{f.get('StartLine')} ({f.get('RuleID')})"
                    for f in found if isinstance(f, dict)})
    return "found", lines or ["a finding it did not describe"]


def _plain(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def _own_list(repo: str, git_args: list[str]) -> tuple[str, list[str]]:
    """The fallback: Mycelium's own list over the lines a diff or a log ADDS."""
    try:
        done = _git(repo, *git_args, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return "error", [f"git did not finish in {TIMEOUT} seconds"]
    if done.returncode != 0:
        return "error", [f"git exited {done.returncode}: {done.stderr.strip()[:200]}"]
    added = "\n".join(ln[1:] for ln in done.stdout.splitlines()
                      if ln.startswith("+") and not ln.startswith("+++"))[:MAX_FALLBACK]
    try:
        ran = subprocess.run(["bash", str(Path(__file__).with_name("_secret_grep.sh"))],
                             input=added, text=True, capture_output=True, timeout=TIMEOUT,
                             check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return "error", [f"Mycelium's own list could not be run ({type(exc).__name__})"]
    if ran.returncode == 1:
        return "clean", []
    if ran.returncode == 0:
        return "found", [f"a line matching pattern {ran.stdout.strip()} of Mycelium's own list"]
    return "error", [f"Mycelium's own list could not run: {ran.stdout.strip()[:200]}"]


def scan_staged(repo: str, wider: bool) -> tuple[str, list[str]]:
    """What the commit would take: the index, and with `wider` the tracked files as on disk."""
    passes = [(["--pre-commit", "--staged"], ["diff", "--cached", "-U0", "--no-color"])]
    if wider:
        passes.append((["--pre-commit"], ["diff", "-U0", "--no-color"]))
    return _run(repo, passes)


def scan_unpushed(repo: str) -> tuple[str, list[str]]:
    """Every commit on a local branch that is on no remote."""
    return _run(repo, [(["--log-opts", "--branches --not --remotes"],
                        ["log", "-p", "-U0", "--no-color", "--branches", "--not", "--remotes"])])


def scan_commits(repo: str, shas: list[str]) -> tuple[str, list[str]]:
    """The named commits and nothing else."""
    return _run(repo, [(["--log-opts", "--no-walk " + " ".join(shas)],
                        ["show", "-U0", "--no-color", "--format=", *shas])])


def _run(repo: str, passes: list[tuple[list[str], list[str]]]) -> tuple[str, list[str]]:
    have = scanner() is not None
    lines: list[str] = []
    for leaks_args, git_args in passes:
        status, said = _gitleaks(repo, leaks_args) if have else _own_list(repo, git_args)
        if status == "error":
            return "error", said
        lines += said
    return ("found" if lines else "clean"), lines


# ---------------------------------------------------------------- commits a command made

def reflog_length(repo: str) -> int | None:
    try:
        done = _git(repo, "reflog", "show", "--format=%h", "HEAD")
    except (OSError, subprocess.SubprocessError):
        return None  # SPEAKS: `made_commits` falls back to comparing the commit pointer
    return len(done.stdout.split()) if done.returncode == 0 else None


def head_of(repo: str) -> str:
    try:
        done = _git(repo, "rev-parse", "--verify", "-q", "HEAD")
    except (OSError, subprocess.SubprocessError):
        return ""  # SPEAKS: an unreadable pointer reads as "no commit yet"
    return done.stdout.strip() if done.returncode == 0 else ""


def made_commits(repo: str, before_head: str, before_reflog: int | None) -> list[str]:
    """The commits made between a view taken earlier and now, newest first. Read from HEAD's
    reflog (a commit, an amend, a cherry-pick, a revert, a rebase step); a pull, a checkout or a
    reset moves the pointer to commits that arrived another way and is left out. Where there is
    no reflog to read, every commit on HEAD that is on no remote and was not under the old
    pointer."""
    now = head_of(repo)
    if not now or now == before_head:
        return []
    after = reflog_length(repo)
    if before_reflog is not None and after is not None and after > before_reflog:
        done = _git(repo, "reflog", "show", "--format=%H%x09%gs", "-n", str(after - before_reflog),
                    "HEAD")
        if done.returncode == 0:
            out = []
            for line in done.stdout.splitlines():
                sha, _, subject = line.partition("\t")
                if subject.split(":", 1)[0].split(" ", 1)[0] in _MADE and sha not in out:
                    out.append(sha)
            return out
    args = ["rev-list", now, "--not", "--remotes"] + ([before_head] if before_head else [])
    done = _git(repo, *args)
    return done.stdout.split() if done.returncode == 0 else [now]


# ---------------------------------------------------------------- the hook's answer

def _own_hook_scans(repo: str) -> bool:
    """The repository's own pre-commit hook already runs a scanner, so a commit that honours
    hooks is scanned by it and need not be scanned twice."""
    done = _git(repo, "rev-parse", "--git-path", "hooks/pre-commit")
    hook = Path(repo, done.stdout.strip()) if done.returncode == 0 and done.stdout.strip() else None
    for candidate in (hook, Path(repo, ".pre-commit-config.yaml")):
        try:
            if candidate and "gitleaks" in candidate.read_text(encoding="utf-8", errors="replace"):
                return True
        except OSError:
            continue  # SPEAKS: no such file means no such hook, so Mycelium scans
    return False


def _deny(reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "deny",
        "permissionDecisionReason": reason}}, ensure_ascii=False))


_INSTALL = ("To get the real check, install gitleaks (https://github.com/gitleaks/gitleaks; "
            "`brew install gitleaks` on macOS).")


def _weak_note(project_dir: str, session: str) -> None:
    """Once a session: say that no scanner is installed and the short list ran in its place."""
    marker = Path(project_dir, ".claude", "state", "commit-scan-weak-said")
    try:
        if marker.read_text(encoding="utf-8").strip() == (session or "-"):
            return
    except OSError:
        pass  # SPEAKS: no marker means it has not been said this session, so it is said now
    try:
        _state_dir.prepare_dir(marker.parent)  # the state folder, with its ignore file
        marker.write_text((session or "-") + "\n", encoding="utf-8")
    except OSError:
        pass  # SPEAKS: it is said again next time, which errs toward saying it
    told = ("Mycelium: no secret scanner is installed, so what is being committed or pushed was "
            "checked against Mycelium's own short list only. That list knows a few common shapes "
            "and misses many. " + _INSTALL)
    print(json.dumps({"systemMessage": told, "hookSpecificOutput": {
        "hookEventName": "PreToolUse", "additionalContext": told + " Tell the person once."}},
        ensure_ascii=False))


def _repos(command: str, cwd: str) -> list[str]:
    out: list[str] = []
    for folder in where_it_runs(command, cwd):
        repo = repo_of(folder)
        if repo and repo not in out:
            out.append(repo)
    return out


def _checks(does: dict, repos: list[str]) -> list[tuple[str, str, tuple[str, list[str]]]]:
    checks = []
    for repo in repos:
        if does["commit"] and not (_own_hook_scans(repo) and not does["no_verify"]):
            checks.append(("commit", f"what this commit would take ({repo})",
                           scan_staged(repo, does["wider"])))
        if does["push"]:
            checks.append(("push", f"commits that are on no remote yet ({repo})",
                           scan_unpushed(repo)))
    return checks


def pre(payload: dict, project_dir: str) -> int:
    """PreToolUse on a shell command. Prints a deny, a once-a-session note, or nothing."""
    ti = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    command = ti.get("command") if isinstance(ti.get("command"), str) else ""
    does = what_it_runs(command)
    repos = _repos(command, str(payload.get("cwd") or project_dir))
    if not (does["commit"] or does["push"]) or not repos:
        return 0
    which = "gitleaks" if scanner() else "Mycelium's own short list (no scanner is installed)"
    for verb, what, (status, lines) in _checks(does, repos):
        if status == "error":
            _deny(f"Mycelium commit scan: the secret scan could not run, so this {verb} is "
                  f"refused. Nothing was found; the scan itself failed: {'; '.join(lines)}. A scan "
                  "that cannot look cannot say there is no secret. Tell the person: they can "
                  f"{verb} from their own terminal, or fix what stopped the scan.")
            return 0
        if status == "found":
            _deny(f"Mycelium commit scan: {which} found something that looks like a secret in "
                  f"{what}: {'; '.join(lines[:MAX_NAMED])}"
                  f"{' and more' if len(lines) > MAX_NAMED else ''}. The {verb} is refused. "
                  "Take the value out of what is committed (an ignored env file or a secrets "
                  "manager is where it belongs), and if it was ever real, tell the person it "
                  "should be replaced. If it is a false alarm, the person can wave it through "
                  "themselves; the agent cannot.")
            return 0
    if not scanner():
        _weak_note(project_dir, str(payload.get("session_id") or ""))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    project = args[args.index("--project-dir") + 1] if "--project-dir" in args else os.getcwd()
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        payload = {}
    if "--pre" in args:
        try:
            return pre(payload if isinstance(payload, dict) else {}, project)
        except Exception as exc:  # noqa: BLE001 - a scan that cannot run refuses, whatever broke
            _deny("Mycelium commit scan: the secret scan could not run, so this command is "
                  f"refused ({type(exc).__name__}). Tell the person.")
            return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
