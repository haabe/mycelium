"""Coverage tests for mutation_sample.py: sites come from code tokens only; a killed mutant and a
surviving mutant are both reported; the module is restored after every run; an empty root is
UNKNOWN. In-process with a fake runner, so no pytest subprocess is spawned."""

import random
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"


def _mod():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import mutation_sample
    return mutation_sample


SRC = '''"""docstring with a == b and not this"""
# comment: x >= y
def f(a, b):
    label = "a and b"  # string
    return 1 if a == b else 0
'''


def test_sites_skip_strings_comments_and_docstrings():
    m = _mod()
    sites = m.mutation_sites(SRC)
    lines = SRC.split("\n")
    touched = {lines[i][a:b] for i, a, b, _ in sites}
    assert touched == {"==", "return 1"}
    assert all(lines[i][:a].count('"') % 2 == 0 for i, a, b, _ in sites)
    assert all(not lines[i].strip().startswith(("#", '"""')) for i, a, b, _ in sites)


def test_killed_and_survived_are_both_reported_and_the_file_is_restored(tmp_path):
    m = _mod()
    src = tmp_path / "check_thing.py"
    src.write_text(SRC)
    test = tmp_path / "test_check_thing.py"
    test.write_text("")
    calls = []

    def runner(root, test_path):
        calls.append(src.read_text())
        return 1 if len(calls) % 2 else 0  # alternate: killed, survived, ...

    r = m.mutate_module(tmp_path, src, test, 4, random.Random(1), runner=runner)  # noqa: S311
    assert r["sites"] == 2, "the fixture offers `==` and `return 1`, nothing in strings or comments"
    assert r["mutants"] == 2 and r["killed"] == 1 and len(r["survived"]) == 1
    assert all(c != SRC for c in calls), "every run must see a mutated module"
    assert src.read_text() == SRC, "the module must be restored after every mutant"
    assert not list(tmp_path.glob("*.mutbak"))


def test_timeout_is_counted_not_dropped(tmp_path):
    m = _mod()
    src = tmp_path / "check_t.py"
    src.write_text(SRC)
    r = m.mutate_module(tmp_path, src, tmp_path / "t.py", 2, random.Random(1),  # noqa: S311
                        runner=lambda root, t: None)
    assert r["timeouts"] == 2 and r["killed"] == 0 and r["survived"] == []


def test_a_root_with_nothing_to_mutate_is_unknown(tmp_path, capsys):
    m = _mod()
    assert m.main(["--root", str(tmp_path)]) == 2
    assert "UNKNOWN" in capsys.readouterr().out


# ------------------------------------------------------------------ end to end on a throwaway module

FAKE_CHECK = "def verdict(a, b):\n    return 1 if a == b else 0\n"
FAKE_TEST = (
    "import sys, importlib\n"
    "sys.path.insert(0, sys.argv[0] and __import__('os').path.dirname(__file__) + '/../../plugins/mycelium/scripts')\n"
    "m = importlib.import_module('check_x')\n"
    "def test_equal():\n    assert m.verdict(1, 1) == 1\n"
    "def test_unequal():\n    assert m.verdict(1, 2) == 0\n"
)


def _fake_repo(tmp_path):
    (tmp_path / "plugins/mycelium/scripts").mkdir(parents=True)
    (tmp_path / "tests/python").mkdir(parents=True)
    (tmp_path / "plugins/mycelium/scripts/check_x.py").write_text(FAKE_CHECK)
    (tmp_path / "tests/python/test_check_x.py").write_text(FAKE_TEST)
    return tmp_path


def test_main_runs_the_real_pytest_runner_and_reports_a_score(tmp_path, capsys):
    m = _mod()
    root = _fake_repo(tmp_path)
    rc = m.main(["--root", str(root), "--modules", "1", "--mutants-per-module", "2", "--seed", "3"])
    out = capsys.readouterr().out
    assert rc == 0, out
    assert "mutation-sample: 1 module(s), 2 mutant(s)" in out and "score" in out
    assert (root / "plugins/mycelium/scripts/check_x.py").read_text() == FAKE_CHECK


def test_json_output_carries_modules_and_score(tmp_path, capsys):
    import json as _json
    m = _mod()
    root = _fake_repo(tmp_path)
    rc = m.main(["--root", str(root), "--modules", "1", "--mutants-per-module", "1", "--json"])
    payload = _json.loads(capsys.readouterr().out)
    assert rc == 0 and payload["mutants"] == 1 and payload["modules"][0]["module"] == "check_x.py"


def test_run_tests_returns_the_pytest_exit_code(tmp_path):
    m = _mod()
    root = _fake_repo(tmp_path)
    assert m.run_tests(root, root / "tests/python/test_check_x.py") == 0
    (root / "tests/python/test_check_x.py").write_text("def test_fails():\n    assert False\n")
    assert m.run_tests(root, root / "tests/python/test_check_x.py") != 0


def test_untokenizable_source_is_said_not_swallowed(capsys):
    m = _mod()
    sites = m.mutation_sites('x = "unterminated\nif a == b:\n    pass\n')
    assert "could not tokenize" in capsys.readouterr().out
    assert isinstance(sites, list)
