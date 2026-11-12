"""The code the hooks run must import and run under Python 3.9, the python3 macOS ships.

The hooks start their scripts with whatever `python3` is first on the builder's PATH, and most of
them send stderr to /dev/null. On a stock Mac that is /usr/bin/python3, 3.9. Before this test,
seven modules the hooks run failed at import there and the hook said nothing:
`shell_safety_guard.py` imported `itertools.pairwise` (3.10), and six more evaluated an `X | None`
annotation when a function was defined (3.10). Three call sites passed `zip(..., strict=True)`
(3.10) and three called `isinstance` with an `A | B` union (3.10); those fail only when the line
runs.

THE SET IS FOUND, NOT LISTED. `hook_reached()` starts from every script that a hook manifest
(hooks/hooks*.json), a hook script (hooks/*.sh) or an integration's installer names, and follows
what each one runs: a `.py`/`.sh` named in a shell script, a module a Python file imports, and a
`.py` named in a string a Python file holds (a script it starts). A new hook or a new import is
covered with no edit here.

Two halves. The static half runs everywhere (CI is 3.11+) and refuses, in that set, the 3.10+
constructs named above. The runtime half imports every module of the set under a Python older than
3.10 when this machine has one (/usr/bin/python3 on a Mac, or python3.9 on PATH), and is skipped,
saying why, when it has none. ruff's B905 and RUF007 ask for the 3.10 forms and are ignored in
ruff.toml for this reason.
"""

from __future__ import annotations

import ast
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[2] / "plugins" / "mycelium"
HOOKS, SCRIPTS = PLUGIN / "hooks", PLUGIN / "scripts"
_NAMED = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*\.(?:py|sh)\b")
_SH_IMPORT = re.compile(
    r"^\s*(?:from\s+([A-Za-z_]\w*)\s+import|import\s+([A-Za-z_]\w*(?:\s*,\s*[A-Za-z_]\w*)*))",
    re.MULTILINE)
# Third-party packages the scripts import. On a machine without them the scripts already say so
# and stop (validate_canvas.py exit 2, scale_locks.py exit 3); here they are stood in for, so the
# rest of each module is still imported. A NEW third-party import is not in this set and fails.
_THIRD_PARTY = ("yaml", "jsonschema", "referencing")


def _local(name: str, near: Path) -> Path | None:
    for folder in (SCRIPTS, HOOKS, near):
        if (folder / name).is_file():
            return folder / name
    return None


def _from_shell(path: Path) -> set[Path | None]:
    code = "\n".join(line for line in path.read_text(encoding="utf-8").splitlines()
                     if not line.lstrip().startswith("#"))
    found = {_local(m.group(0), path.parent) for m in _NAMED.finditer(code)}
    for m in _SH_IMPORT.finditer(code):
        for name in (m.group(1) or m.group(2) or "").split(","):
            found.add(_local(name.strip() + ".py", path.parent))
    return found


def _docstring_ids(tree: ast.AST) -> set[int]:
    ids = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) \
                and body and isinstance(body[0], ast.Expr) \
                and isinstance(body[0].value, ast.Constant):
            ids.add(id(body[0].value))
    return ids


def _from_python(path: Path) -> set[Path | None]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docs = _docstring_ids(tree)
    found: set[Path | None] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found |= {_local(a.name.split(".")[0] + ".py", path.parent) for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            found.add(_local(node.module.split(".")[0] + ".py", path.parent))
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) \
                and id(node) not in docs:
            found |= {_local(m.group(0), path.parent) for m in _NAMED.finditer(node.value)}
    return found


def hook_reached() -> list[Path]:
    """Every .py file a hook can run, directly or through what it runs."""
    seeds: set[Path | None] = set(HOOKS.glob("*.sh"))
    for manifest in HOOKS.glob("hooks*.json"):
        seeds |= {_local(Path(m.group(0)).name, HOOKS) for m in _NAMED.finditer(manifest.read_text())}
    seeds |= set((PLUGIN / "integrations").glob("*/install_hooks.py"))
    todo, seen = [p for p in seeds if p], set()
    while todo:
        path = todo.pop()
        if path in seen:
            continue
        seen.add(path)
        nxt = _from_python(path) if path.suffix == ".py" else _from_shell(path)
        todo += [p for p in nxt if p and p not in seen]
    return sorted(p for p in seen if p.suffix == ".py")


# --------------------------------------------------------------------------- the set itself

def test_the_set_is_found_from_the_hooks():
    names = {p.name for p in hook_reached()}
    # One from each way in: a manifest's hook script, a script that script names, an import of
    # that script, and the Vibe translator its installer names.
    assert {"shell_safety_guard.py", "_hook_input.py", "_secret_mask.py",
            "vibe_hook.py"} <= names
    assert len(names) >= 60


# --------------------------------------------------------------------------- static, everywhere

_TYPE_NAMES = {"int", "str", "float", "bool", "dict", "list", "tuple", "set", "frozenset",
               "bytes", "type", "object", "Path"}


def _typeish(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant) and node.value is None:
        return True
    if isinstance(node, ast.Name) and node.id in _TYPE_NAMES:
        return True
    if isinstance(node, ast.Subscript):
        return _typeish(node.value)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return _typeish(node.left) or _typeish(node.right)
    return False


def _annotation_ids(tree: ast.AST) -> set[int]:
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            a = node.args
            for arg in [*a.posonlyargs, *a.args, *a.kwonlyargs, a.vararg, a.kwarg]:
                if arg is not None and arg.annotation is not None:
                    ids |= {id(x) for x in ast.walk(arg.annotation)}
            if node.returns is not None:
                ids |= {id(x) for x in ast.walk(node.returns)}
        elif isinstance(node, ast.AnnAssign):
            ids |= {id(x) for x in ast.walk(node.annotation)}
    return ids


def _is_pairwise(node: ast.AST) -> bool:
    if isinstance(node, ast.ImportFrom):
        return node.module == "itertools" and any(a.name == "pairwise" for a in node.names)
    return (isinstance(node, ast.Attribute) and node.attr == "pairwise"
            and isinstance(node.value, ast.Name) and node.value.id == "itertools")


def findings(path: Path) -> list[str]:
    """The 3.10+ constructs in one file that fail under 3.9 when the line runs."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    future = any(isinstance(n, ast.ImportFrom) and n.module == "__future__"
                 and any(a.name == "annotations" for a in n.names) for n in tree.body)
    annotations = _annotation_ids(tree)
    out = []
    for node in ast.walk(tree):
        where = f"{path.name}:{getattr(node, 'lineno', 0)}"
        if _is_pairwise(node):
            out.append(f"{where}: itertools.pairwise (3.10)")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id == "zip" and any(k.arg == "strict" for k in node.keywords):
            out.append(f"{where}: zip(strict=) (3.10)")
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr) and _typeish(node) \
                and not (future and id(node) in annotations):
            out.append(f"{where}: `{ast.unparse(node)}` evaluated at runtime (3.10)")
    return out


def test_no_3_10_construct_in_code_the_hooks_run():
    found = [f for p in hook_reached() for f in findings(p)]
    assert not found, (
        "These fail under the Python 3.9 that macOS ships, where the hook discards the error. "
        "Use zip(a, a[1:]) for pairwise, an explicit length check for zip(strict=), a tuple for "
        "isinstance, and `from __future__ import annotations` for annotations:\n  "
        + "\n  ".join(found))


def test_the_static_scan_sees_each_form(tmp_path):
    """A control: each construct is caught, and the 3.9 spellings are not."""
    bad = tmp_path / "bad.py"
    bad.write_text("from itertools import pairwise\n"
                   "def f(x: int | None) -> str | None:\n"
                   "    return isinstance(x, int | float), list(zip(x, x, strict=True))\n")
    good = tmp_path / "good.py"
    good.write_text("from __future__ import annotations\n"
                    "def f(x: int | None) -> str | None:\n"
                    "    return isinstance(x, (int, float)), list(zip(x, x[1:])), 1 | 2\n")
    assert len(findings(bad)) == 5
    assert findings(good) == []


# --------------------------------------------------------------------------- runtime, under 3.9

def _old_python() -> str | None:
    """The oldest Python below 3.10 on this machine, if there is one."""
    best = None
    for cand in ("/usr/bin/python3", shutil.which("python3.9"), shutil.which("python3.8")):
        if not cand or not Path(cand).is_file():
            continue
        probe = subprocess.run([cand, "-c", "import sys; print(list(sys.version_info[:2]))"],
                               capture_output=True, text=True, check=False, timeout=30)
        if probe.returncode != 0:
            continue
        version = tuple(json.loads(probe.stdout))
        if version < (3, 10) and (best is None or version < best[0]):
            best = (version, cand)
    return best[1] if best else None


_DRIVER = r"""
import importlib, importlib.abc, importlib.machinery, json, sys, traceback, types
folders, third_party, names = json.loads(sys.argv[1]), set(json.loads(sys.argv[2])), sys.argv[3:]
sys.path[:0] = folders

class _AnyMeta(type):
    def __getattr__(cls, name):
        return cls

class _Any(Exception, metaclass=_AnyMeta):
    def __init__(self, *a, **k):
        pass
    def __call__(self, *a, **k):
        return _Any()
    def __getattr__(self, name):
        return _Any

class _StandIn(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def find_spec(self, name, path, target=None):
        if name.split(".")[0] in third_party:
            return importlib.machinery.ModuleSpec(name, self, is_package=True)
        return None
    def create_module(self, spec):
        m = types.ModuleType(spec.name)
        m.__path__ = []
        m.__getattr__ = lambda attr: _Any
        return m
    def exec_module(self, module):
        pass

sys.meta_path.append(_StandIn())   # last: a package that IS installed is used as it is
bad = {}
for name in names:
    try:
        importlib.import_module(name)
    except BaseException:
        bad[name] = traceback.format_exc()[-400:]
print("RESULT " + json.dumps(bad))
"""

OLD = _old_python()


@pytest.mark.skipif(OLD is None, reason="no Python older than 3.10 on this machine "
                                        "(/usr/bin/python3, python3.9, python3.8); the static "
                                        "test above is the guard here")
def test_every_hook_reached_module_imports_under_python_3_9(tmp_path):
    modules = hook_reached()
    folders = sorted({str(p.parent) for p in modules})
    done = subprocess.run([OLD, "-I", "-c", _DRIVER, json.dumps(folders),
                           json.dumps(_THIRD_PARTY), *[p.stem for p in modules]],
                          capture_output=True, text=True, check=False, timeout=300,
                          cwd=tmp_path, stdin=subprocess.DEVNULL)
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stderr[-800:]
    bad = json.loads(lines[-1][len("RESULT "):])
    assert not bad, f"{len(bad)} of {len(modules)} modules fail to import under {OLD}:\n" + \
        "\n".join(f"{k}: {v.strip().splitlines()[-1]}" for k, v in bad.items())


@pytest.mark.skipif(OLD is None, reason="no Python older than 3.10 on this machine")
def test_the_shell_safety_hook_speaks_under_python_3_9(tmp_path):
    """One hook end to end with the old interpreter first on PATH. Until this release the guard
    failed at `from itertools import pairwise`, so the hook printed nothing on a stock Mac."""
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "python3").symlink_to(OLD)
    (tmp_path / ".claude" / "canvas").mkdir(parents=True)
    payload = json.dumps({"tool_name": "Bash", "hook_event_name": "PreToolUse",
                          "tool_input": {"command": "ls | head; echo $?"}, "session_id": "s"})
    env = {"PATH": f"{tmp_path / 'bin'}:/usr/bin:/bin:/usr/sbin:/sbin", "HOME": str(tmp_path),
           "CLAUDE_PLUGIN_ROOT": str(PLUGIN), "CLAUDE_PROJECT_DIR": str(tmp_path)}
    done = subprocess.run(["bash", str(HOOKS / "shell-safety-guard.sh")], input=payload,
                          capture_output=True, text=True, env=env, check=False, timeout=120)
    assert done.returncode == 0
    assert "SHELL-SAFETY WARNING" in done.stdout
