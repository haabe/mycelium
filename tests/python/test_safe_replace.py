"""G-V12 coverage proof for safe_replace.py.

THE GAP IT CLOSES. "Assert the replacement landed" was the standing rule, and
following it produced a worse failure than ignoring it: a script patching two
files with a shared anchor wrote the first, raised on the second, and left the
tree half-edited. The bug is ORDERING — `write; assert` turns a bad assertion
into a partial edit, which is strictly worse than no assertion, because the tree
is now in a state nobody described.

The load-bearing property is therefore NOT "it replaces text". It is **when any
anchor fails, nothing is written** — and that is what most of these assert.

Scenario-per-guardpost:
  happy — every anchor matches                  -> every file written
  happy — several edits to one file compose     -> validated against staged text
  sad   — one anchor of several fails           -> NOTHING written, all problems named
  sad   — count mismatch (the guessed-count bug)-> NOTHING written
  bad   — a target file does not exist          -> NOTHING written
  bad   — malformed spec                        -> exit 2
  edge  — count 0 asserts an anchor is ABSENT
  edge  — --dry-run validates and writes nothing
"""

import json
import subprocess
import sys

import pytest


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import safe_replace
    return safe_replace


def _files(tmp_path, **contents):
    for name, text in contents.items():
        (tmp_path / name).write_text(text)
    return tmp_path


# ---------------------------------------------------------------- happy


def test_all_anchors_match_writes_everything(scripts_path, tmp_path):
    mod = _import(scripts_path)
    _files(tmp_path, a="hello foo\n", b="baz here\n")
    written = mod.apply_edits([
        {"path": str(tmp_path / "a"), "old": "foo", "new": "bar"},
        {"path": str(tmp_path / "b"), "old": "baz", "new": "qux"},
    ])
    assert len(written) == 2
    assert (tmp_path / "a").read_text() == "hello bar\n"
    assert (tmp_path / "b").read_text() == "qux here\n"


def test_several_edits_to_one_file_compose(scripts_path, tmp_path):
    """The second edit must be validated against the text the FIRST leaves, not
    against the original — otherwise a valid pair is rejected, or worse, an
    anchor that only exists after the first edit is called missing."""
    mod = _import(scripts_path)
    _files(tmp_path, a="one two\n")
    mod.apply_edits([
        {"path": str(tmp_path / "a"), "old": "one", "new": "three"},
        {"path": str(tmp_path / "a"), "old": "three two", "new": "final"},
    ])
    assert (tmp_path / "a").read_text() == "final\n"


# ---------------------------------------------------------------- sad


def test_one_bad_anchor_writes_nothing(scripts_path, tmp_path):
    """THE PROPERTY THIS EXISTS FOR. The real incident: file one patched, file
    two raised, tree left half-edited."""
    mod = _import(scripts_path)
    _files(tmp_path, a="hello foo\n", b="unrelated\n")
    with pytest.raises(mod.AnchorError) as exc:
        mod.apply_edits([
            {"path": str(tmp_path / "a"), "old": "foo", "new": "bar"},
            {"path": str(tmp_path / "b"), "old": "NOT PRESENT", "new": "x"},
        ])
    assert "NOTHING was written" in str(exc.value)
    assert (tmp_path / "a").read_text() == "hello foo\n", "file one was modified"
    assert (tmp_path / "b").read_text() == "unrelated\n"


def test_count_mismatch_writes_nothing_and_reports_both_numbers(scripts_path, tmp_path):
    """The guessed-count bug: `== 3` when it was 2, three times in one session."""
    mod = _import(scripts_path)
    _files(tmp_path, a="x x\n")
    with pytest.raises(mod.AnchorError) as exc:
        mod.apply_edits([{"path": str(tmp_path / "a"), "old": "x",
                          "new": "y", "count": 3}])
    msg = str(exc.value)
    assert "occurs 2 time(s), expected 3" in msg
    assert (tmp_path / "a").read_text() == "x x\n"


def test_every_problem_is_reported_not_just_the_first(scripts_path, tmp_path):
    """Fail-fast would make the caller rediscover one anchor per run, which is
    the guessing game this replaces."""
    mod = _import(scripts_path)
    _files(tmp_path, a="aaa\n", b="bbb\n")
    with pytest.raises(mod.AnchorError) as exc:
        mod.apply_edits([
            {"path": str(tmp_path / "a"), "old": "nope1", "new": "x"},
            {"path": str(tmp_path / "b"), "old": "nope2", "new": "y"},
        ])
    assert "nope1" in str(exc.value) and "nope2" in str(exc.value)
    assert "2 anchor problem(s)" in str(exc.value)


# ---------------------------------------------------------------- bad


def test_missing_file_writes_nothing(scripts_path, tmp_path):
    mod = _import(scripts_path)
    _files(tmp_path, a="hello\n")
    with pytest.raises(mod.AnchorError) as exc:
        mod.apply_edits([
            {"path": str(tmp_path / "a"), "old": "hello", "new": "bye"},
            {"path": str(tmp_path / "gone"), "old": "x", "new": "y"},
        ])
    assert "does not exist" in str(exc.value)
    assert (tmp_path / "a").read_text() == "hello\n"


def test_missing_keys_are_reported(scripts_path, tmp_path):
    mod = _import(scripts_path)
    with pytest.raises(mod.AnchorError) as exc:
        mod.apply_edits([{"path": str(tmp_path / "a")}])
    assert "missing old, new" in str(exc.value)


@pytest.mark.parametrize(("spec", "code"), [
    ("not json", 2),
    ('{"not": "a list"}', 2),
])
def test_cli_rejects_malformed_spec(scripts_path, spec, code):
    r = subprocess.run([sys.executable, str(scripts_path / "safe_replace.py")],
                       input=spec, capture_output=True, text=True, check=False)
    assert r.returncode == code, r.stdout + r.stderr


def test_cli_exits_1_and_writes_nothing_on_a_bad_anchor(scripts_path, tmp_path):
    _files(tmp_path, a="hello\n")
    spec = json.dumps([{"path": str(tmp_path / "a"), "old": "nope", "new": "x"}])
    r = subprocess.run([sys.executable, str(scripts_path / "safe_replace.py")],
                       input=spec, capture_output=True, text=True, check=False)
    assert r.returncode == 1
    assert "NOTHING was written" in r.stderr
    assert (tmp_path / "a").read_text() == "hello\n"


# ---------------------------------------------------------------- edge


def test_count_zero_asserts_absence(scripts_path, tmp_path):
    """A precondition edit: 'this string must NOT be here'. Useful for proving a
    prior migration completed before layering the next one on top."""
    mod = _import(scripts_path)
    _files(tmp_path, a="clean\n")
    mod.apply_edits([{"path": str(tmp_path / "a"), "old": "legacy",
                      "new": "", "count": 0}])
    assert (tmp_path / "a").read_text() == "clean\n"
    with pytest.raises(mod.AnchorError):
        mod.apply_edits([{"path": str(tmp_path / "a"), "old": "clean",
                          "new": "", "count": 0}])


def test_dry_run_validates_and_writes_nothing(scripts_path, tmp_path):
    mod = _import(scripts_path)
    _files(tmp_path, a="hello foo\n")
    written = mod.apply_edits(
        [{"path": str(tmp_path / "a"), "old": "foo", "new": "bar"}], dry_run=True)
    assert written == [tmp_path / "a"]
    assert (tmp_path / "a").read_text() == "hello foo\n"


def test_negative_count_is_rejected(scripts_path, tmp_path):
    mod = _import(scripts_path)
    _files(tmp_path, a="x\n")
    with pytest.raises(mod.AnchorError) as exc:
        mod.apply_edits([{"path": str(tmp_path / "a"), "old": "x",
                          "new": "y", "count": -1}])
    assert "non-negative" in str(exc.value)


# ---------------------------------------------------------------- in-process CLI
# Same reason as the sibling suite: subprocess invocation proves the CLI contract
# and measures no coverage.


def test_main_applies_a_spec_from_stdin(scripts_path, tmp_path, monkeypatch, capsys):
    import io
    mod = _import(scripts_path)
    _files(tmp_path, a="hello foo\n")
    spec = json.dumps([{"path": str(tmp_path / "a"), "old": "foo", "new": "bar"}])
    monkeypatch.setattr(sys, "stdin", io.StringIO(spec))
    assert mod.main([]) == 0
    assert (tmp_path / "a").read_text() == "hello bar\n"
    assert "1 edit(s) validated" in capsys.readouterr().out


def test_main_dry_run_reports_without_writing(scripts_path, tmp_path,
                                              monkeypatch, capsys):
    import io
    mod = _import(scripts_path)
    _files(tmp_path, a="hello foo\n")
    spec = json.dumps([{"path": str(tmp_path / "a"), "old": "foo", "new": "bar"}])
    monkeypatch.setattr(sys, "stdin", io.StringIO(spec))
    assert mod.main(["--dry-run"]) == 0
    assert (tmp_path / "a").read_text() == "hello foo\n"
    assert "would write" in capsys.readouterr().out


def test_main_reads_a_spec_file(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    _files(tmp_path, a="hello foo\n")
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps(
        [{"path": str(tmp_path / "a"), "old": "foo", "new": "bar"}]))
    assert mod.main(["--spec", str(spec)]) == 0
    assert (tmp_path / "a").read_text() == "hello bar\n"
    capsys.readouterr()


def test_main_returns_1_on_bad_anchor_and_writes_nothing(scripts_path, tmp_path,
                                                         monkeypatch, capsys):
    import io
    mod = _import(scripts_path)
    _files(tmp_path, a="hello\n")
    spec = json.dumps([{"path": str(tmp_path / "a"), "old": "nope", "new": "x"}])
    monkeypatch.setattr(sys, "stdin", io.StringIO(spec))
    assert mod.main([]) == 1
    assert (tmp_path / "a").read_text() == "hello\n"
    assert "NOTHING was written" in capsys.readouterr().err
