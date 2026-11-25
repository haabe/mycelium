"""Secrets are stopped at the commit and at the push (v0.323.0).

WHY THIS EXISTS. Until 0.323.0 Mycelium looked for secrets at the moment the agent WROTE a file,
with a short list of its own. Replayed 2026-10-12: an unquoted `KEY=value` passed, an env file was
treated like source code, and nothing ever looked at what was staged. The maintainer's direction:
"Don't let passwords into the repo", "Maybe a security scan in the pre-commit hook is enough?",
"using established scanners are the way to go ... better left to someone who knows it better".

WHAT IT DOES. Three moments, one scanner (gitleaks when it is installed):
  1. Before the agent's `git commit`: what is staged is scanned (and what `-a` or a named path
     would add). A finding refuses the commit. Since 0.337.2 this holds whatever hooks the
     repository has of its own: a hook or a pre-commit config that names a scanner does not
     stand in for this scan. Since 0.337.4 the whole command is read step by step: a `git add`
     before the commit is replayed into a scratch index and that is what is scanned, and a
     step Mycelium cannot account for before a commit or a push refuses the command (see
     "reading the whole command" below).
  2. After any shell command of the agent's: commits the command itself made, by any route, are
     scanned (`bash_state_guard.py` calls `made_commits` and `scan_commits`). Mycelium does not
     rewrite a commit; it says what it found, and a later `git push` is where it is stopped.
     A push the same command makes inside itself has gone by then (see `_GIT` below).
  3. Before the agent's `git push`: every commit that is on no remote and under a local branch,
     a tag, the checked-out commit or a commit the push names is scanned (branches only until
     0.337.4). A finding refuses the push.
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
MAX_SHOWN = 80      # characters of a step quoted in a refusal
#: Where a command starts: at the beginning, after a separator, an opening bracket or quote, or
#: a shell keyword; with variable assignments in front.
_START = r"(?:^|[;&|(`\n\"']|\$\(|\b(?:then|do|else)\s)\s*(?:\w+=\S+\s+)*"
#: A word that runs the command named after it. Its own options and values (`timeout 60`,
#: `sudo -u me`, `env A=b`) are whatever words stand between it and `git` in the same simple
#: command, so `sudo echo git push` is read as a push too: that errs toward scanning, and a scan
#: refuses only on a finding.
_WRAPPERS = ("sudo|doas|command|builtin|time|exec|nohup|env|timeout|nice|ionice|xargs|stdbuf|"
             "caffeinate|noglob|setsid|unbuffer|chronic")
#: `git commit` or `git push` where a command starts, with `git` by name or by path
#: (`/usr/bin/git`) and a wrapper word in front. The words inside a longer argument ("remember
#: to git commit") do not count.
#: WHAT THIS CANNOT READ, and no pattern can: a command that commits or pushes INSIDE itself (a
#: release script, a make target, `npm version`, a git alias). Such a commit is scanned after the
#: command (`made_commits`) and the person is told; such a push has gone before anything looked.
#: Until 0.337.3 the pattern also missed `git` by path and behind `env`, `timeout`, `nice` and
#: `xargs`, and the comment here said a missed form "is still scanned ... at the push", which
#: was not true of a missed push (blind read of 0.337.2, 2026-11-25, replayed).
_GIT = re.compile(
    _START + r"(?:(?:" + _WRAPPERS + r")\s+(?:[^\s;&|]+\s+)*?)?"
    r"(?:[^\s;&|\"'`]*/)?git((?:\s+(?:-[cC]\s+\S+|--[\w-]+(?:=\S+)?))*)\s+(commit|push)\b")
#: commit options that take the next word as their value, so that word is not a path or a flag
_TAKES_VALUE = {"-m", "-F", "-C", "-c", "-t", "--message", "--file", "--reuse-message",
                "--reedit-message", "--fixup", "--squash", "--author", "--date", "--template",
                "--cleanup", "--pathspec-from-file", "--trailer"}
#: reflog subjects that mean the command itself made a commit (a pull, a checkout, a reset or a
#: fast-forward merge moves the pointer to commits that arrived some other way)
_MADE = ("commit", "cherry-pick", "revert", "am", "rebase")


def _git(repo: str, *args: str, timeout: int = 15,
         index: str | None = None) -> subprocess.CompletedProcess:
    env = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}  # a hook never takes the index lock
    if index:
        env["GIT_INDEX_FILE"] = index  # a scratch copy: the repository's own index is not touched
    return subprocess.run(["git", "-C", repo, *args], text=True, capture_output=True, env=env,
                          timeout=timeout, check=False)


def repo_of(folder: str) -> str | None:
    """The top of the git repository `folder` is in, or None."""
    try:
        done = _git(folder, "rev-parse", "--show-toplevel")
    except (OSError, subprocess.SubprocessError):
        return None  # SPEAKS: no git, or no repository, means nothing can be committed from here
    return done.stdout.strip() if done.returncode == 0 and done.stdout.strip() else None


# ---------------------------------------------------------------- reading the whole command
#
# VOUCH OR REFUSE (since 0.337.4). The scan before a commit or a push looks at the repository as
# it is BEFORE the command runs. That says what the commit or push will take only when nothing
# earlier in the same command can change it. Until 0.337.4 the command was not read for that:
# `git add -A && git commit -m work && git push` was answered from an index the key was not in
# yet, and the key was committed and pushed with nothing having looked (blind read of 0.337.3,
# 2026-11-25, replayed). `if git commit ...; then`, `{ git commit ...; }` and `! git commit ...`
# were not read as commits at all.
#
# So the command is read step by step, and each step before a commit or a push is one of:
#   - a step Mycelium can account for: `cd <folder>`, a `git add` (replayed into a scratch index,
#     so what it would stage is scanned), an earlier `git commit` or `git push` (scanned itself),
#     a git command that stages nothing (`_QUIET_GIT`), a shell word that writes nothing
#     (`_QUIET`);
#   - anything else. Then Mycelium cannot say what the commit or push would take, and the command
#     is refused with nothing found: the agent runs the earlier steps first and the commit or
#     push in a command of its own, where it is scanned.
# The list is of what is ACCOUNTED FOR, and everything else refuses. The three holes found on
# 2026-11-25 were each a form that a list of what to catch had missed.

class UnreadableError(Exception):
    """The command's text could not be followed (an unclosed quote, bracket or here-document)."""


_OPEN, _CLOSE = "\x00(", "\x00)"   # a subshell or a substitution opens and closes: `cd` is local
_HEREDOC = re.compile(r"<<(-?)\s*(['\"]?)([\w.+-]+)\2")
_KEYWORDS = {"if", "then", "else", "elif", "fi", "do", "done", "while", "until", "!", "{", "}",
             "time", "esac"}
_SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
#: shell words that write no file and stage nothing (when their output is not sent to a file)
_QUIET = {"echo", "printf", "true", ":", "pwd", "date", "cat", "ls", "sleep", "set", "test", "[",
          "[[", "head", "tail", "wc", "grep", "mkdir"}
#: programs that run the text they are given: on their input, from a file, or after `-c`/`-e`
_RUNS_TEXT = re.compile(r"(?:bash|sh|zsh|dash|ksh|fish|source|\.|python[\d.]*|perl|ruby|node|php)")
#: git commands that can change the files in the working tree, the ignore rules among them. A
#: `git add` after one may stage what the replay, made before the command runs, did not.
_MOVES = {"checkout", "switch", "merge", "rebase", "pull", "rm", "mv", "restore"}
#: git commands that run text they are given (`rebase --exec`, `bisect run`)
_GIT_RUNS_TEXT = {"rebase", "bisect", "submodule", "filter-branch", "for-each-repo"}
#: a commit or push at the start of a command inside a piece of text
_IN_TEXT = re.compile(r"(?:^|[;&|(\n\"'`!])\s*(?:\w+=\S+\s+)*git\s+(?:-[cC]\s+\S+\s+)*"
                      r"(commit|push)\b")
#: git commands that stage nothing, write no file and bring in no commit, whatever their words
_QUIET_GIT = {"status", "diff", "log", "show", "rev-parse", "describe", "ls-files", "shortlog",
              "blame", "rm", "mv"}
#: `GIT_` variables in front of a command that do not say which repository or index it uses
_GIT_ENV_OK = re.compile(r"GIT_(?:LFS_\w+|EDITOR|SEQUENCE_EDITOR|PAGER|TERMINAL_PROMPT|"
                         r"SSH_COMMAND|SSH|ASKPASS|AUTHOR_\w+|COMMITTER_\w+|TRACE\w*|CURL_VERBOSE|"
                         r"MERGE_AUTOEDIT)=")
_TO_A_FILE = re.compile(r">(?!&\d+(?![\w.])|&-|\s*/dev/null)")
_GLOB = re.compile(r"[*?\[\]{}~]")
_BACKGROUND = "\x00&"   # a lone `&`: what follows runs at the same time, in no known order
_PIPE = "\x00|"         # a pipe: both sides run at the same time
_WRAPPER_WORD = re.compile(r"-[a-zABE-RT-Z0-9]+|--[a-z-]+(=[\w.:-]+)?|[\w.:-]+|\w+=[\w.:,-]*")
#: `git commit` or `git push` anywhere in a command's text, a here-document's body included
_MENTION = re.compile(r"\bgit\b[^;&|\n]{0,200}?\b(commit|push)\b")
#: programs that print, search or post the text they are given and never run it
_TEXT_ONLY = {"rg", "ag", "ack", "grep", "sed", "gh", "echo", "printf", "cat", "tee", "jq",
              "chmod", "rm", "ls", "open", "code", "less", "head", "tail", "wc", "mkdir", "touch"}
#: `git -c <this>=...` settings that do not say which repository, work tree or index is used
_CONFIG_OK = re.compile(r"(?:user|color|advice|gpg|http|credential|push|pull|commit|core\.editor"
                        r"|core\.pager|init\.defaultBranch)[.=]", re.IGNORECASE)
#: `git add` options that stage nothing the replay would not stage
_ADD_FLAGS = {"--all", "--update", "--no-all", "--ignore-removal", "--no-ignore-removal",
              "--intent-to-add", "--verbose", "--ignore-errors", "--sparse", "--"}
#: `git commit` long options that do not widen what the commit takes
_COMMIT_PLAIN = {"--amend", "--no-edit", "--edit", "--no-verify", "--verify", "--allow-empty",
                 "--allow-empty-message", "--signoff", "--no-signoff", "--quiet", "--verbose",
                 "--gpg-sign", "--no-gpg-sign", "--reset-author", "--dry-run", "--status",
                 "--no-status", "--no-post-rewrite", "--message", "--file", "--author", "--date",
                 "--cleanup", "--trailer", "--fixup", "--squash", "--reuse-message",
                 "--reedit-message", "--template", "--untracked-files", "--short", "--branch",
                 "--porcelain", "--long", "--null"}
_QUOTED = re.compile(r"'[^']*'|\"(?:\\.|[^\"\\])*\"")
_ASSIGN = re.compile(r"^\w+=")


def steps(command: str) -> list[str]:
    """The simple commands of a shell command, in the order they run, with `_OPEN` and `_CLOSE`
    around a subshell or a substitution. A substitution's own commands come before the command
    whose words they fill, and stand in its text as `$SUB`. A here-document's body is left out.
    Raises `UnreadableError` when the text cannot be followed."""
    out: list[str] = []
    _read(command, 0, out, None)
    return out


def _read(s: str, i: int, out: list[str], closer: str | None) -> int:  # noqa: C901, PLR0912, PLR0915 - one pass over shell text, a branch per kind of character
    buf: list[str] = []
    pending: list[tuple[str, bool]] = []
    n = len(s)

    def flush() -> None:
        part = "".join(buf).strip()
        buf.clear()
        if part:
            out.append(part)

    def nested(start: int, close: str) -> int:
        out.append(_OPEN)
        after = _read(s, start, out, close)
        out.append(_CLOSE)
        return after

    while i < n:
        c, two = s[i], s[i:i + 2]
        if c == "\\":
            if two != "\\\n":
                buf.append(two)
            i += 2
        elif two == "$'":
            j = i + 2
            while j < n and s[j] != "'":
                j += 2 if s[j] == "\\" else 1
            if j >= n:
                raise UnreadableError("an unclosed $'...' quote")
            # the shell turns \n into a line end inside $'...'; anything else it decodes is
            # left as typed, which keeps the word a single quoted word
            if re.search(r"\\[^nt\\']", s[i + 2:j]):
                raise UnreadableError("a $'...' quote with an escape this reader does not decode")
            text = s[i + 2:j].replace("\\n", "\n").replace("\\'", "").replace("'", "")
            buf.append("'" + text + "'")
            i = j + 1
        elif c == "'":
            j = s.find("'", i + 1)
            if j < 0:
                raise UnreadableError("an unclosed single quote")
            buf.append(s[i:j + 1])
            i = j + 1
        elif c == '"':
            buf.append('"')
            i += 1
            while i < n and s[i] != '"':
                if s[i] == "\\":
                    buf.append(s[i:i + 2])
                    i += 2
                elif s[i:i + 2] == "$(":
                    i = nested(i + 2, ")")
                    buf.append("$SUB")
                elif s[i] == "`":
                    i = nested(i + 1, "`")
                    buf.append("$SUB")
                else:
                    buf.append(s[i])
                    i += 1
            if i >= n:
                raise UnreadableError("an unclosed double quote")
            buf.append('"')
            i += 1
        elif c == "`":
            if closer == "`":
                flush()
                return i + 1
            i = nested(i + 1, "`")
            buf.append("$SUB")
        elif two == "$(":
            i = nested(i + 2, ")")
            buf.append("$SUB")
        elif two == "${":
            j = s.find("}", i)
            if j < 0 or "$(" in s[i:j] or "`" in s[i:j]:
                raise UnreadableError("a ${...} this reader does not follow")
            buf.append(s[i:j + 1])
            i = j + 1
        elif c == "#" and (not buf or buf[-1] in (" ", "\t")):
            while i < n and s[i] != "\n":
                i += 1
        elif s[i:i + 3] == "<<<":
            buf.append(" <<< ")
            i += 3
        elif two == "<<":
            m = _HEREDOC.match(s, i)
            if not m:
                raise UnreadableError("a here-document with no plain end word")
            pending.append((m.group(3), bool(m.group(2))))
            buf.append(" ")
            i = m.end()
        elif c == "\n":
            flush()
            i += 1
            for word, quoted in pending:
                body: list[str] = []
                while True:
                    if i >= n:
                        raise UnreadableError("a here-document that does not end")
                    j = s.find("\n", i)
                    line, i = (s[i:], n) if j < 0 else (s[i:j], j + 1)
                    if line.strip() == word:
                        break
                    body.append(line)
                if not quoted and ("$(" in "\n".join(body) or "`" in "\n".join(body)):
                    raise UnreadableError("a here-document that runs commands")
            pending.clear()
        elif c == "&" and (s[i - 1:i] == ">" or s[i + 1:i + 2] == ">"):
            buf.append(c)
            i += 1
        elif c in ";&|":
            flush()
            if c == "&" and two != "&&" and s[i - 1:i] not in ("&", "|"):
                out.append(_BACKGROUND)
            elif c == "|" and two != "||" and s[i - 1:i] != "|":
                out.append(_PIPE)
            i += 1
        elif c == "(" and s[i - 1:i] in ("<", ">"):
            i = nested(i + 1, ")")  # <(...) and >(...): its commands run, the word stays one word
            buf.append("$SUB")
        elif c == "(":
            flush()
            i = nested(i + 1, ")")
        elif c == ")":
            flush()
            if closer == ")":
                return i + 1
            i += 1  # the `)` of a `case` pattern
        else:
            buf.append(c)
            i += 1
    if closer is not None or pending:
        raise UnreadableError("a bracket or a here-document that does not close")
    flush()
    return i


def _is_git(word: str) -> bool:
    return word == "git" or word.endswith("/git")


def _lead(part: str) -> tuple[list[str], bool, bool] | None:
    """The step's words with shell keywords, variable assignments and a wrapper word taken off
    the front, whether its output goes to a file, and whether the front was bare (no variable
    set, no `env`, `sudo` or `doas`: those can change which ignore rules git reads). None when
    the front cannot be accounted
    for: a variable that says which repository or index git uses, `xargs` (it adds words of its
    own), or a wrapper option that could change folder or run text."""
    try:
        words = shlex.split(part)
    except ValueError:
        return None
    while words and words[0] in _KEYWORDS:
        words = words[1:]
    bare = True
    while words and _ASSIGN.match(words[0]):
        if words[0].startswith("GIT_") and not _GIT_ENV_OK.match(words[0]):
            return None  # GIT_INDEX_FILE, GIT_DIR: another index or repository
        words, bare = words[1:], False
    if words and os.path.basename(words[0]) in _WRAPPERS.split("|"):
        bare = bare and os.path.basename(words[0]) not in ("env", "sudo", "doas")
        at = next((k for k, w in enumerate(words)
                   if k and (_is_git(w) or _RUNS_TEXT.fullmatch(os.path.basename(w)))), None)
        if at is None or os.path.basename(words[0]) == "xargs":
            return None
        for w in words[1:at]:
            # between the wrapper and `git`: its plain options, numbers and harmless variables.
            # A folder (`env -C dir`), text to run (`env -S`), or a GIT_ variable is not that.
            if not _WRAPPER_WORD.fullmatch(w) or "dir" in w or "split" in w \
                    or (w.startswith("GIT_") and not _GIT_ENV_OK.match(w)):
                return None
        words = words[at:]
    return words, bool(_TO_A_FILE.search(_QUOTED.sub("Q", part))), bare


def _under(folder: str, raw: str) -> str | None:
    """The folder a `cd` or a `git -C` names, or None when the text does not spell out one that
    is there (a variable, a pattern, a folder that does not exist: the step then fails or lands
    somewhere else, and what follows runs where Mycelium cannot say)."""
    if "$" in raw or "`" in raw or raw == "-" or _GLOB.search(raw.lstrip("~")):
        return None
    path = os.path.expanduser(raw)
    path = os.path.normpath(path if os.path.isabs(path) else os.path.join(folder, path))
    return path if os.path.isdir(path) or not os.path.isdir(folder) else None


def _git_words(rest: list[str], folder: str) -> tuple[str, list[str], str] | None:
    """(subcommand, its words, folder) of a git command's words after `git`, or None when an
    option in front names another repository or setting this reader does not account for."""
    while rest and rest[0].startswith("-"):
        if rest[0] == "-C" and len(rest) > 1:
            folder = _under(folder, rest[1])
            if folder is None:
                return None
            rest = rest[2:]
        elif rest[0] == "-c" and len(rest) > 1 and _CONFIG_OK.match(rest[1]):
            rest = rest[2:]
        elif rest[0] in ("--no-pager", "-p", "-P", "--paginate", "--no-optional-locks",
                         "--literal-pathspecs", "--no-replace-objects"):
            rest = rest[1:]
        else:
            return None  # --git-dir, --work-tree, -c core.worktree=: another repository
    return (rest[0], rest[1:], folder) if rest else ("", [], folder)


def step_kind(part: str, folder: str) -> tuple:  # noqa: C901, PLR0911, PLR0912
    """What one simple command is, run in `folder`: ("commit", folder, wider),
    ("push", folder, words), ("add", folder, words or None), ("cd", folder), ("run", script),
    ("fed",) for a program that runs text this reader cannot see whole (a shell or an interpreter
    reading its input or a file, a `-c` script with a variable in it), ("quiet",), ("moves",) for
    a quiet git step that can change the working tree, or ("unknown",). `words` of a `git add`
    are its arguments to
    replay; None means the shell widens them before git sees them (a pattern), so everything in
    the working tree that is not ignored is taken."""
    lead = _lead(part)
    if lead is None:
        return ("unknown",)
    words, to_a_file, bare = lead
    if not words:
        # a variable set as a step of its own (`HOME=/x; git add -A`) can change which ignore
        # rules a later `git add` reads, as a step that changes the working tree can
        return ("quiet",) if bare else ("moves",)
    verb, rest = words[0], words[1:]
    base = os.path.basename(verb)
    if verb == "cd":
        path = _under(folder, rest[0] if rest else "~") if len(rest) <= 1 else None
        return ("cd", path) if path else ("unknown",)
    if verb == "eval" or base in _SHELLS:
        at = next((k for k, w in enumerate(rest) if re.fullmatch(r"-\w*c", w)), None)
        script = " ".join(rest) if verb == "eval" else (
            rest[at + 1] if at is not None and at + 1 < len(rest) else None)
        # no `-c`: it reads a script file or its input (a here-document, a pipe). A script with
        # a variable or a substitution in it is text this reader does not have either.
        if script is None:
            return ("fed",) if _from_input(rest) else ("unknown",)
        return ("fed",) if "$" in script or "`" in script else ("run", script)
    if _RUNS_TEXT.fullmatch(base):
        inline = any(w in ("-c", "-e") for w in rest)
        return ("fed",) if not inline and _from_input(rest) else ("unknown",)
    if not _is_git(verb):
        return ("quiet",) if verb in _QUIET and not to_a_file else ("unknown",)
    read = _git_words(rest, folder)
    if read is None:
        return ("unknown",)
    sub, args, folder = read
    hidden = "$" in part or "`" in part   # a word the shell fills in when the command runs
    if sub == "commit":
        return ("commit", folder, _takes_more(args))
    if sub == "push":
        # a hidden word could name a commit that is on no branch (a stash), which the scan
        # before the command cannot look up
        return ("unknown",) if hidden else ("push", folder, args)
    if sub in ("add", "stage"):
        flags = [a for a in (args[:args.index("--")] if "--" in args else args)
                 if a.startswith("-")]
        if hidden or not bare or not all(
                f in _ADD_FLAGS or re.fullmatch(r"-[AuNv]+", f) for f in flags):
            return ("unknown",)  # --force and ignored files, a choice made while it runs, words
            #                      that are not in the text, or other ignore rules (`HOME=`, `env`)
        return ("add", folder, None if any(_GLOB.search(a) for a in args) else args)
    if to_a_file or any(a.startswith("--output") for a in args):
        return ("unknown",)
    if sub == "" or _quiet_git(sub, args, folder):
        new_branch = args[:1] and args[0] in ("-b", "-B", "-c", "-C", "--create")
        return ("moves",) if sub in _MOVES and not new_branch else ("quiet",)
    return ("unknown",)


def _from_input(rest: list[str]) -> bool:
    """A shell or an interpreter with these words reads its script from its input (a
    here-document, a pipe) and not from a file it names."""
    rest = [w for w in rest if not re.match(r"\d*[<>&]", w)]   # `2>&1`, `>/dev/null`, `<(...)`
    named = [w for w in rest if not w.startswith("-") or w == "-"]
    return "-s" in rest or not named or any(w in ("-", "/dev/stdin") for w in named)


def _quiet_git(sub: str, args: list[str], folder: str) -> bool:  # noqa: C901, PLR0911
    """A git step that stages nothing new, writes no file, and neither brings in a commit nor
    points a name at one from somewhere the scan before a push does not look (another clone, a
    stash, a commit on no branch)."""
    if sub in _QUIET_GIT:
        return True
    flags = [a for a in args if a.startswith("-")]
    named = [a for a in args if not a.startswith("-")]
    if sub in ("pull", "fetch"):
        # from a remote by its name: what arrives is on that remote
        return not named or named[0] in _names(folder, "remote")
    if sub in ("branch", "remote"):
        return not named or (sub == "branch" and set(flags) <= {"-d", "-D", "--delete"} and flags)
    if sub == "tag":
        # a tag on the commit that is checked out, which the push scan reads
        words = [a for k, a in enumerate(args) if not (k and args[k - 1] in ("-m", "--message"))]
        return {w for w in words if w.startswith("-")} <= {
            "-a", "-f", "-m", "--message", "--annotate", "--force"} \
            and len([w for w in words if not w.startswith("-")]) <= 1
    if sub == "switch":
        if len(named) == 1 and flags and set(flags) <= {"-c", "-C", "-q", "--quiet", "--create"}:
            return True  # a new branch where the checked-out commit is
        return len(args) == 1 and len(named) == 1 and _is_ref(folder, named[0], "heads")
    if sub == "checkout":
        if len(args) == len(("-b", "name")) and args[0] in ("-b", "-B"):
            return True
        return len(args) == 1 and len(named) == 1 and _is_ref(folder, named[0], "heads")
    if sub in ("merge", "rebase"):
        # onto or with a branch that is here or was fetched: its commits are scanned or remote
        return set(flags) <= {"--no-edit", "--ff-only", "--no-ff", "-q", "--quiet", "--autostash"} \
            and len(named) == 1 and (_is_ref(folder, named[0], "heads")
                                     or _is_ref(folder, named[0], "remotes"))
    if sub == "restore":
        return set(flags) <= {"--staged", "-S", "-q", "--quiet", "--"} and bool(
            {"--staged", "-S"} & set(flags))  # unstaging: the index goes back to what is committed
    if sub == "config":
        return len(named) == len(("key", "value")) and named[0] in ("user.name", "user.email") \
            and set(flags) <= {"--local", "--global"}
    return False


def _names(folder: str, *args: str) -> list[str]:
    try:
        done = _git(folder, *args)
    except (OSError, subprocess.SubprocessError):
        return []  # SPEAKS: nothing is known by name, so the step is not accounted for
    return done.stdout.split() if done.returncode == 0 else []


def _is_ref(folder: str, name: str, kind: str) -> bool:
    try:
        return _git(folder, "show-ref", "--verify", "-q", f"refs/{kind}/{name}").returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False  # SPEAKS: not known to be a branch, so the step is not accounted for


def _takes_more(args: list[str]) -> bool:  # noqa: C901 - one branch per kind of word
    """A `git commit` with these words takes more than the index: `-a`, `--all`, `--include`,
    `--only`, a file of paths, a named path, or a long option this reader does not know (git
    accepts a long option cut short, so an unknown one may be any of those)."""
    skip = False
    for w in args:
        if skip:
            skip = False
        elif w == "--" or w.startswith("--pathspec"):
            return True
        elif w in _TAKES_VALUE:
            skip = True
        elif w.startswith("--"):
            if w.split("=", 1)[0] not in _COMMIT_PLAIN:
                return True
        elif w.startswith("-") and len(w) > 1:
            for at, letter in enumerate(w[1:], 1):
                if letter in "aiop":
                    return True
                if letter in "mFCct":       # the rest of the word, or the next word, is its value
                    skip = at == len(w) - 1
                    break
        else:
            return True
    return False


def read_command(command: str, cwd: str) -> dict:  # noqa: C901, PLR0915 - holds `walk`
    """What a shell command would commit and push, read step by step:
    {"commits": [(folder, wider, adds)], "pushes": [(folder, words)],
     "blocked": (verb, step, why) or None}.
    `adds` are the `git add` steps before that commit, as (folder, words or None). `blocked` is
    the first commit or push Mycelium cannot vouch for, and `why`: "before" (it comes after a
    step that is not accounted for), "own" (it is itself written in a way Mycelium cannot follow
    to a repository), "order" (a step runs at the same time, behind `&` or in the same pipe)."""
    out: dict = {"commits": [], "pushes": [], "blocked": None}
    state: dict = {"unknown": None, "adds": [], "background": False, "fed": False,
                   "piped": False, "in_pipe": False, "moved": False}

    def block(verb: str, step: str, why: str) -> None:
        out["blocked"] = out["blocked"] or (verb, step, why)

    def walk(parts: list[str], folder: str) -> None:  # noqa: C901, PLR0912 - a branch per kind of step
        folders = [folder]
        for part in parts:
            if part == _OPEN:
                folders.append(folders[-1])
            elif part == _CLOSE:
                if len(folders) > 1:
                    folders.pop()
            elif part == _BACKGROUND:
                state["background"] = True
            elif part == _PIPE:
                state["piped"] = True
            else:
                kind = step_kind(part, folders[-1])
                if kind[0] == "moves":
                    state["moved"] = True
                elif kind[0] == "add" and state["moved"]:
                    # the replay is made before the command runs, with the files and the
                    # ignore rules as they are then; the step in front may change both
                    kind = ("unknown",)
                if not all(w in _KEYWORDS for w in part.split()):
                    # `in_pipe`: a commit or push is in the pipe this step belongs to
                    state["in_pipe"], state["piped"] = state["in_pipe"] and state["piped"], False
                if kind[0] == "cd":
                    folders[-1] = kind[1]
                elif kind[0] == "run":
                    walk(steps(kind[1]), folders[-1])
                elif kind[0] == "add":
                    state["adds"].append((kind[1], kind[2]))
                elif kind[0] in ("unknown", "fed"):
                    verb = _git_verb_in(part, folders[-1])
                    if verb:
                        # a commit or push this reader does not follow: another index or
                        # repository is named, a word is filled in when the command runs, or
                        # `git` stands behind a program that runs it in a way the text does
                        # not show
                        block(verb, part, "own")
                    if state["in_pipe"]:
                        block("commit", part, "order")  # the pipe's stages run at the same time
                    state["fed"] |= kind[0] == "fed"
                    state["unknown"] = state["unknown"] or part
                elif kind[0] in ("commit", "push"):
                    state["in_pipe"] |= kind[0] == "commit"  # a push takes what is committed
                    if state["unknown"]:
                        block(kind[0], state["unknown"], "before")
                    elif kind[0] == "commit":
                        out["commits"].append((kind[1], kind[2], list(state["adds"])))
                    else:
                        out["pushes"].append((kind[1], kind[2]))

    walk(steps(command), cwd)
    if state["background"] and (out["commits"] or out["pushes"]):
        block("commit" if out["commits"] else "push", "&", "order")
    said = _MENTION.search(command)
    if state["fed"] and said:
        # a shell or an interpreter runs text this reader does not have whole (its input, a
        # file, a variable), and the command's text names a commit or a push: this reader does
        # not follow which text reaches which program
        block(said.group(1), "a program that runs text handed to it", "own")
    return out


def _git_verb_in(part: str, folder: str) -> str | None:  # noqa: C901, PLR0911, PLR0912
    """"commit" or "push" when a step that is not accounted for runs git with that subcommand
    somewhere in its words (`uv run git commit`, `find . -exec git push`), or hands a program a
    piece of text that does (`python3 -c "...git commit..."`, `ssh host 'git push'`). Not read
    that way: words given to a program that only prints or searches text (`_TEXT_ONLY`), to an
    interpreter that is running a script file, to `find` unless it runs a shell, and to a git
    command that does not run text."""
    try:
        words = shlex.split(part)
    except ValueError:
        words = part.split()
    while words and (words[0] in _KEYWORDS or _ASSIGN.match(words[0])):
        words = words[1:]
    for k, w in enumerate(words):
        if _is_git(w):
            read = _git_words(words[k + 1:], folder)
            if read is None:
                verb = next((v for v in words[k + 1:] if v in ("commit", "push")), None)
                if verb:
                    return verb
            elif read[0] in ("commit", "push"):
                return read[0]
            elif k == 0 and read[0] not in _GIT_RUNS_TEXT:
                return None
    first = os.path.basename(words[0]) if words else ""
    if first in _TEXT_ONLY:
        return None
    if _RUNS_TEXT.fullmatch(first) and first not in _SHELLS and not any(
            w in ("-c", "-e") for w in words):
        return None  # an interpreter running a file: its other words are the file's to read
    if first == "find" and not any(
            w in ("-exec", "-execdir", "-ok") and os.path.basename(nxt) in _SHELLS
            for w, nxt in zip(words, words[1:])):  # pairwise; zip(strict=) is Python 3.10
        return None
    # with a shell among the words (`uv run sh -c '...'`) the text is a script, where git need
    # not stand first (`if true; then git commit`, `exec git commit`, `/usr/bin/git commit`)
    looks = _MENTION if any(os.path.basename(w) in _SHELLS for w in words) else _IN_TEXT
    for w in words[1:]:
        hit = looks.search(w) if re.search(r"\s", w) else None
        if hit:
            return hit.group(1)
    return None


# ---------------------------------------------------------------- the two scanners

def scanner() -> str | None:
    return shutil.which("gitleaks")


def _gitleaks(repo: str, args: list[str], index: str | None = None) -> tuple[str, list[str]]:
    """("clean" | "found" | "error", lines). `found` lines are `file:line (rule)`, never a value."""
    handle, report = tempfile.mkstemp(prefix="mycelium-scan-", suffix=".json")
    os.close(handle)
    env = {**os.environ, "GIT_INDEX_FILE": index} if index else None
    try:
        done = subprocess.run(
            [scanner() or "gitleaks", "git", "--no-banner", "--redact", "--exit-code", str(FOUND),
             "--report-format", "json", "--report-path", report, *args, repo],
            text=True, capture_output=True, timeout=TIMEOUT, check=False, env=env)
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


def _own_list(repo: str, git_args: list[str], index: str | None = None) -> tuple[str, list[str]]:
    """The fallback: Mycelium's own list over the lines a diff or a log ADDS."""
    try:
        done = _git(repo, *git_args, timeout=TIMEOUT, index=index)
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


def scan_staged(repo: str, wider: bool,  # noqa: C901 - each way the replay can fail is named
                adds: list | None = None) -> tuple[str, list[str]]:
    """What the commit would take: the index, and with `wider` the tracked files as on disk.
    `adds` are the `git add` steps the same command runs before the commit, as
    (folder, words or None). They are replayed into a scratch copy of the index, which is then
    what is scanned; the repository's own index is not touched. (Replaying writes the same
    file contents into git's store that the command's own `git add` is about to write.)"""
    passes = [(["--pre-commit", "--staged"], ["diff", "--cached", "-U0", "--no-color"])]
    if wider:
        passes.append((["--pre-commit"], ["diff", "-U0", "--no-color"]))
    if not adds:
        return _run(repo, passes)
    handle, scratch = tempfile.mkstemp(prefix="mycelium-index-")
    os.close(handle)
    try:
        done = _git(repo, "rev-parse", "--path-format=absolute", "--git-path", "index")
        real = done.stdout.strip() if done.returncode == 0 else ""
        if real and os.path.exists(real):
            shutil.copyfile(real, scratch)
        else:
            os.unlink(scratch)  # no index yet: git makes the scratch one
        for folder, words in adds:
            done = None
            if words is not None and repo_of(folder) == repo:
                done = _git(folder, "add", *words, timeout=TIMEOUT, index=scratch)
            if done is None or done.returncode != 0:
                # not replayable as written: take everything that is not ignored, which is
                # at least what any `git add` without --force can stage
                done = _git(repo, "add", "-A", timeout=TIMEOUT, index=scratch)
            if done.returncode != 0:
                return "error", ["what `git add` would stage could not be worked out: "
                                 + _plain(done.stderr.strip())[:200]]
        return _run(repo, passes, scratch)
    except subprocess.TimeoutExpired:
        return "error", [f"working out what `git add` would stage took over {TIMEOUT} seconds"]
    except OSError as exc:
        return "error", [f"a scratch index could not be made ({type(exc).__name__})"]
    finally:
        for leftover in (scratch, scratch + ".lock"):
            Path(leftover).unlink(missing_ok=True)


def scan_unpushed(repo: str, words: list[str] | None = None) -> tuple[str, list[str]]:
    """Every commit that is on no remote and that a push could send: on a local branch, under a
    tag, under the commit that is checked out (it may be on no branch), and under whatever the
    push's own words name (`git push origin <this>:<there>`). `--mirror` adds every other name
    the repository has. Until 0.337.4 only local branches were read."""
    tips = ["HEAD"] if head_of(repo) else []
    for w in (words or []):
        src = w.lstrip("+").split(":", 1)[0]
        if src and not w.startswith("-"):
            done = _git(repo, "rev-parse", "--verify", "-q", src + "^{commit}")
            if done.returncode == 0 and done.stdout.strip() not in tips:
                tips.append(done.stdout.strip())
    names = ["--branches", "--tags"] + (["--all"] if "--mirror" in (words or []) else [])
    revs = names + tips + ["--not", "--remotes"]
    passes = [(["--log-opts", " ".join(revs)], ["log", "-p", "-U0", "--no-color", *revs])]
    for tip in tips[1:] if tips[:1] == ["HEAD"] else tips:
        # A named commit with two parents (a stash is one) holds lines that a walk of the log
        # shows under neither parent. Read it against its first parent.
        if len(_git(repo, "rev-list", "--parents", "-n", "1", tip).stdout.split()) > len("xy"):
            one = ["--no-walk", "--diff-merges=first-parent", tip]
            passes.append((["--log-opts", " ".join(one)],
                           ["show", "-U0", "--no-color", "--format=", *one[1:]]))
    return _run(repo, passes)


def scan_commits(repo: str, shas: list[str]) -> tuple[str, list[str]]:
    """The named commits and nothing else."""
    return _run(repo, [(["--log-opts", "--no-walk " + " ".join(shas)],
                        ["show", "-U0", "--no-color", "--format=", *shas])])


def _run(repo: str, passes: list[tuple[list[str], list[str]]],
         index: str | None = None) -> tuple[str, list[str]]:
    have = scanner() is not None
    lines: list[str] = []
    for leaks_args, git_args in passes:
        status, said = (_gitleaks(repo, leaks_args, index) if have
                        else _own_list(repo, git_args, index))
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


def _read_checks(reading: dict):
    """The scans a command read step by step calls for, one at a time (a finding stops there).
    EVERY COMMIT OF THE AGENT'S IS SCANNED HERE (since 0.337.2). From 0.323.0 the scan was
    skipped when the repository's `hooks/pre-commit` or `.pre-commit-config.yaml` held the word
    "gitleaks", on the reasoning that the repository's own hook would scan. Neither file showed
    that a hook was installed or ran, and the agent may write both unasked, so one line of text
    switched the scan off (blind read of 0.337.1, 2026-11-25, replayed)."""
    pushed: list[tuple] = []
    for folder, wider, adds in reading["commits"]:
        repo = repo_of(folder)
        if repo:
            mine = [(f, words) for f, words in adds if repo_of(f) == repo]
            what = "what this commit would take" + (", with what its `git add` stages" if mine
                                                    else "")
            yield "commit", f"{what} ({repo})", scan_staged(repo, wider, mine)
    for folder, words in reading["pushes"]:
        repo = repo_of(folder)
        if repo and (repo, tuple(words)) not in pushed:
            pushed.append((repo, tuple(words)))
            yield ("push", f"commits that are on no remote yet ({repo})",
                   scan_unpushed(repo, words))


def pre(payload: dict, project_dir: str) -> int:  # noqa: PLR0911 - one return per answer
    """PreToolUse on a shell command. Prints a deny, a once-a-session note, or nothing."""
    ti = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    command = ti.get("command") if isinstance(ti.get("command"), str) else ""
    cwd = str(payload.get("cwd") or project_dir)
    try:
        reading = read_command(command, cwd)
    except UnreadableError as exc:
        if _MENTION.search(command):
            _deny("Mycelium commit scan: this command commits or pushes, and Mycelium could not "
                  f"follow its text ({exc}), so it cannot say what would be taken. Nothing was "
                  "found; the command is refused. Run the commit or the push as a plain command "
                  "of its own.")
        return 0
    if reading["blocked"]:
        verb, step, why = reading["blocked"]
        shown = step if len(step) <= MAX_SHOWN else step[:MAX_SHOWN - 3] + "..."
        if why == "own":
            _deny(f"Mycelium commit scan: this command would {verb}, and Mycelium cannot follow "
                  f"how from `{shown}`: git is run by another program or from text handed to "
                  "one, or another repository or index is named, or named through a variable. "
                  "So it cannot scan what would be taken. Nothing was found; the command is "
                  f"refused. Run the {verb} as a plain `git {verb}` in a command of its own, "
                  "from the repository's folder or with `git -C <folder>` spelled out.")
            return 0
        if why == "order":
            _deny("Mycelium commit scan: this command commits or pushes while another step "
                  f"runs at the same time (`{shown}`, behind `&` or in the same pipe), so the "
                  "order things happen in is not known and Mycelium cannot say what would be "
                  "taken. Nothing was found; the command is refused. Run the commit or the "
                  "push in a command of its own.")
            return 0
        _deny(f"Mycelium commit scan: this command runs `{shown}` before its `git {verb}`, and "
              f"Mycelium cannot tell beforehand what that step leaves to be "
              f"{'committed' if verb == 'commit' else 'pushed'}. Nothing was found; the command "
              "is refused so that nothing unscanned gets through. Run the earlier steps first, "
              f"then the {verb} in a command of its own, where it is scanned. `cd`, `git add`, "
              "`git commit` and `git push` can share one command.")
        return 0
    # Until 0.337.4 the words `git commit` inside an argument (`sed -n '/git commit/p' f`) set
    # off a scan of the index, and a finding there refused a command that commits nothing.
    checks = _read_checks(reading)
    which = "gitleaks" if scanner() else "Mycelium's own short list (no scanner is installed)"
    scanned = False
    for verb, what, (status, lines) in checks:
        scanned = True
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
    if scanned and not scanner():
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
