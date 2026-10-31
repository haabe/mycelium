#!/usr/bin/env python3
"""Declare Mycelium's hooks in a project's .vibe/hooks.toml (v0.332.0).

Usage, from the project:   python3 <plugin>/integrations/vibe/install_hooks.py [project-root]

Vibe 3.0 runs a hook only when a hooks.toml declares it: <project>/.vibe/hooks.toml (trusted folders
only) or ~/.vibe/hooks.toml. A plugin cannot install one itself (vibe_hook.py says why). This writes
two entries into the project's file, `mycelium-pre-tool` and `mycelium-post-tool`, each running
vibe_hook.py from THIS copy of the plugin by its absolute path, since a plugin cannot know where it
is installed (hooks/install-runtime-hooks.sh, which does the same for Cursor and Codex).

The pre_tool entry is `strict = true`: if the translator itself cannot run, Vibe refuses the call,
which is what the blocking hooks do in Claude Code when they cannot run (hooks/README.md, 0.322.1).

The project's own hooks stay as they are. Entries with the two Mycelium names are replaced, so a
re-run after moving or updating the plugin points them at the new copy. The result is parsed before
anything is written, and nothing is written if the file cannot be read as TOML, or if the result
would not hold exactly one of each Mycelium entry.

The project-level file, not ~/.vibe/hooks.toml: the user file would run Mycelium's hooks in every
project opened with Vibe. The hooks do nothing in a project without .claude/canvas or
.claude/diamonds, but the translator would still start on every tool call there.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path

try:
    import tomllib
except ImportError:  # Python 3.10 and older; Vibe itself needs 3.12
    tomllib = None

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
TRANSLATOR = PLUGIN_ROOT / "integrations" / "vibe" / "vibe_hook.py"
NAMES = ("mycelium-pre-tool", "mycelium-post-tool")
MARKER = "# Mycelium's hooks, written by"
RERUN = "# Re-run it after moving or updating Mycelium; it replaces these two entries only."
PRE_DESC = "Mycelium's gates (its Claude Code PreToolUse hooks), translated for Vibe"
POST_DESC = "Mycelium's after-call checks (its Claude Code PostToolUse hooks), translated for Vibe"
_TABLE = re.compile(r"^\s*\[\[\s*hooks\s*\]\]\s*(#.*)?$")


def _toml_str(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


def block(root: Path = PLUGIN_ROOT) -> str:
    translator = root / "integrations" / "vibe" / "vibe_hook.py"
    if "'" in str(translator):
        raise ValueError("the plugin path holds a single quote, which the hook command cannot "
                         f"carry: {translator}")
    cmd = f"python3 -I '{translator}'"
    return (
        f"{MARKER} {root / 'integrations' / 'vibe' / 'install_hooks.py'}.\n"
        f"{RERUN}\n"
        "[[hooks]]\n"
        f'name = "{NAMES[0]}"\n'
        'type = "pre_tool"\n'
        'match = "*"\n'
        "strict = true\n"
        "timeout = 60.0\n"
        f"command = {_toml_str(cmd + ' pre')}\n"
        f"description = {_toml_str(PRE_DESC)}\n"
        "\n"
        "[[hooks]]\n"
        f'name = "{NAMES[1]}"\n'
        'type = "post_tool"\n'
        'match = "*"\n'
        "timeout = 60.0\n"
        f"command = {_toml_str(cmd + ' post')}\n"
        f"description = {_toml_str(POST_DESC)}\n"
    )


def _segments(text: str) -> list[str]:
    """The file split before each [[hooks]] line; segment 0 is whatever precedes the first."""
    segs, cur = [], []
    for line in text.splitlines(keepends=True):
        if _TABLE.match(line) and cur:
            segs.append("".join(cur))
            cur = []
        cur.append(line)
    if cur:
        segs.append("".join(cur))
    return segs


def _is_ours(seg: str) -> bool:
    return bool(_TABLE.match(seg.splitlines()[0] if seg else "")) and any(
        re.search(rf'^\s*name\s*=\s*["\']{n}["\']\s*$', seg, re.MULTILINE) for n in NAMES)


def merged(existing: str, new_block: str) -> str:
    """`existing` without Mycelium's entries (and their comment), with `new_block` appended."""
    kept = []
    for seg in _segments(existing):
        if _is_ours(seg):
            continue
        # Drop our own comment lines wherever they ended up (the tail of the previous segment).
        kept.append("".join(ln for ln in seg.splitlines(keepends=True)
                            if not ln.startswith((MARKER, RERUN))))
    body = "".join(kept).rstrip()
    return (body + "\n\n" if body else "") + new_block


def check(text: str) -> str | None:
    """Why `text` is not a hooks file holding one of each Mycelium entry, or None."""
    if tomllib is None:
        return "Python 3.11 or later is needed to check the file (tomllib)"
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        return f"not valid TOML ({e})"
    hooks = doc.get("hooks")
    if not isinstance(hooks, list):
        return "no [[hooks]] list"
    names = [h.get("name") for h in hooks if isinstance(h, dict)]
    for n in NAMES:
        if names.count(n) != 1:
            return f"{names.count(n)} entries named {n}, not 1"
    return None


def install(project: Path, root: Path = PLUGIN_ROOT) -> tuple[Path, bool]:
    """Write the entries. Returns (path, changed). Raises ValueError with the reason on refusal."""
    needed = (root / "hooks" / "hooks.json", root / "integrations" / "vibe" / "vibe_hook.py")
    if not all(f.is_file() for f in needed):
        raise ValueError(f"{root} is not a Mycelium plugin folder "
                         "(no hooks/hooks.json or integrations/vibe/vibe_hook.py)")
    if not project.is_dir():
        raise ValueError(f"no such folder: {project}")
    target = project / ".vibe" / "hooks.toml"
    existing = target.read_text(encoding="utf-8") if target.is_file() else ""
    if existing.strip() and tomllib is not None:
        try:
            tomllib.loads(existing)
        except tomllib.TOMLDecodeError as e:
            raise ValueError(f"{target} is not valid TOML, so it was left alone ({e}). "
                             "Fix it, or add the "
                             "two entries by hand:\n\n" + block(root)) from e
    text = merged(existing, block(root))
    why = check(text)
    if why:
        raise ValueError(f"the merged file would be wrong ({why}), so {target} was left alone")
    if text == existing:
        return target, False
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=".hooks.toml.")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, target)
    return target, True


def main(argv: list[str]) -> int:
    project = Path(argv[1] if len(argv) > 1 else os.getcwd()).resolve()
    try:
        target, changed = install(project)
    except ValueError as e:
        print(f"Mycelium: {e}", file=sys.stderr)
        return 1
    print(f"Mycelium: {'wrote' if changed else 'already current:'} {target}")
    print("Vibe reads it only in a trusted folder: trust the project when Vibe asks "
          "(or pass --trust to vibe -p).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
