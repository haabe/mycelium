"""Run a hook's inline Python without the working directory on the import path (v0.322.4).

WHY THIS EXISTS. `python3 -c CODE` and `python3 - <<EOF` put the current directory FIRST on
`sys.path`. A hook runs with the project as its current directory, so `import json` inside a
hook's inline Python loaded `./json.py` when the project had one. Replayed 2026-10-12 on 0.322.3
with the plugin root set, as Claude Code runs the hooks: four hooks imported planted `json.py`,
`yaml.py` and `re.py` from a scratch project. So a repository could have its own code run by
Mycelium's hooks, on every prompt and every write, with nothing in its settings to show for it.

What was NOT shown: that an honest project's own `types.py` or `json.py` changes what a gate
decides. Replayed the same day on eight gates and on the build gate's two decisions with eight
such files: every decision was the same with and without them (the gates' deciding work runs as
script files, which never had the working directory on the path). What such a file does to the
hooks' smaller inline snippets (a log row, a reminder) was not tested.

A Python FILE gets its own folder on the path in place of the current directory, on every Python
version. So the hooks hand their inline code to this file. `_hook_prelude.sh` defines a `python3`
shell function that does the handing over; nothing at a call site changes.

  _safe_c.py CODE [ARG ...]      as `python3 -c CODE ARG ...`
  _safe_c.py --stdin [ARG ...]   as `python3 - ARG ...`, the code read from stdin

`sys.argv` is what `-c` and `-` would have given the code. This file's own folder is taken off the
path as well, so the code sees what `-c` gave it minus the working directory: a snippet that needs
one of Mycelium's modules adds that folder itself, as before. `PYTHONSAFEPATH=1`, which the
prelude also exports, does the same for Python 3.11 and later; this file is what covers the
Pythons before it (macOS ships 3.9).
"""

import os
import sys


def _clean_path() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    cwd = os.getcwd()
    sys.path[:] = [p for p in sys.path
                   if p not in ("", ".") and os.path.abspath(p) not in (here, cwd)]


def main() -> None:
    args = sys.argv[1:]
    if not args:
        sys.stderr.write("_safe_c.py: no code given\n")
        raise SystemExit(2)
    if args[0] == "--stdin":
        code, name, argv = sys.stdin.read(), "<stdin>", ["-", *args[1:]]
    else:
        code, name, argv = args[0], "<string>", ["-c", *args[1:]]
    _clean_path()
    sys.argv = argv
    exec(compile(code, name, "exec"), {"__name__": "__main__", "__builtins__": __builtins__})  # noqa: S102


if __name__ == "__main__":
    main()
