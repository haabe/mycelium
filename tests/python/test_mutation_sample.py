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
