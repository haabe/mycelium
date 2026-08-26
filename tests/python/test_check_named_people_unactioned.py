"""check_named_people_unactioned must BITE on the shape it was written for.

The live case: a results file named six public repos under "REAL EXTERNAL
CONTACT EVIDENCED" and sat eleven days with zero mentions in human-tasks.yml,
green in every gate the whole time. These assert the two directions plus the
empty-scan case, because a report-only check that cannot distinguish states is
decoration.
"""
import sys


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import check_named_people_unactioned

    return check_named_people_unactioned


FINDING = """
| repo | lag | evidence |
|---|---|---|
| `metapardo/Mobile-Services` | 1d | named participant |
| `alp82/aistack` | 192d | 9 interviewees |
"""


def _project(tmp_path, tasks_body):
    (tmp_path / ".claude" / "evals" / "results").mkdir(parents=True)
    (tmp_path / ".claude" / "canvas").mkdir(parents=True)
    (tmp_path / ".claude" / "evals" / "results" / "verification.md").write_text(FINDING)
    (tmp_path / ".claude" / "canvas" / "human-tasks.yml").write_text(tasks_body)
    return tmp_path


def test_named_but_never_actioned_is_reported(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    root = _project(tmp_path, "pending_tasks: []\n")
    mod.main(["--root", str(root)])
    out = capsys.readouterr().out
    assert "NAME PEOPLE AND HAVE NO TASK" in out
    assert "2 named, 0 in a task" in out


def test_actioned_names_are_not_reported(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    root = _project(tmp_path, "pending_tasks:\n  - id: ht-001\n    note: metapardo/Mobile-Services alp82/aistack\n")
    mod.main(["--root", str(root)])
    assert "every named person" in capsys.readouterr().out


def test_namespaced_paths_are_not_mistaken_for_people(scripts_path, tmp_path, capsys):
    """`search/code` is an API endpoint. It stopped this shipping as a gate."""
    mod = _import(scripts_path)
    root = _project(tmp_path, "pending_tasks: []\n")
    (root / ".claude" / "evals" / "results" / "verification.md").write_text(
        "We queried `search/code` and read `lib/runner.py`.\n"
    )
    mod.main(["--root", str(root)])
    assert "every named person" in capsys.readouterr().out


def test_zero_results_files_is_not_a_pass(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    (tmp_path / ".claude" / "evals" / "results").mkdir(parents=True)
    rc = mod.main(["--root", str(tmp_path)])
    assert rc == 1
    assert "UNKNOWN" in capsys.readouterr().out


def test_missing_results_dir_is_the_same_answer_as_an_empty_one(scripts_path, tmp_path, capsys):
    """It returned 0 here, and check_empty_input_honesty caught it before the push."""
    mod = _import(scripts_path)
    rc = mod.main(["--root", str(tmp_path)])
    assert rc == 1
    assert "UNKNOWN" in capsys.readouterr().out
