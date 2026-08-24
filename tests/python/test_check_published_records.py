"""Coverage proof for check_published_records.py — the published-record auditor.

The subject exists because a session published three artifacts to persistent
addresses and left every source in scratch that gets wiped. Its job is small and
its LIMIT is large: it validates records that exist and cannot see a publish that
recorded nothing. Both halves are asserted below, because a check whose limit is
only claimed in a docstring is a claim, not a property.

FAILURE DIRECTION FIRST. The tests that matter here are the ones that would go
red if the guard stopped biting: a dead source, a missing address, an empty tree
reported as a pass.
"""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "plugins/mycelium/scripts/check_published_records.py"


def _import(scripts_path):
    """In-process import for the LOGIC tests.

    The exit-code contract has to be exercised through the CLI, and those tests
    stay below. But a suite that ONLY shells out reports 0% coverage of a file
    it fully drives — the coverage floor caught exactly that here — and worse,
    a black-box suite cannot pin the classifier's behaviour per record. Both
    layers earn their place.
    """
    sys.path.insert(0, str(scripts_path))
    import check_published_records

    return check_published_records


def _run(root, *extra):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--project-dir", str(root), *extra],
        capture_output=True, text=True, timeout=60, check=False,
    )


def _canvas(root, body, name="opportunities.yml"):
    d = root / ".claude" / "canvas"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(body)
    return d


def _record(root, **over):
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "live.html").write_text("<html>")
    rec = {"address": "https://example.com/a", "source": "docs/live.html",
           "published_at": "2026-08-24"}
    rec.update(over)
    lines = "\n".join(f'        {k}: "{v}"' for k, v in rec.items() if v is not None)
    _canvas(root, f"opportunities:\n  - id: opp-001\n    published:\n      - kind: page\n{lines}\n")


# ---------------------------------------------------------------------------
# Failure direction — each of these goes red if the guard stops biting
# ---------------------------------------------------------------------------

def test_source_missing_from_disk_is_flagged(tmp_path):
    """THE FAILURE THAT ACTUALLY HAPPENED: the page is live, its source is gone."""
    _record(tmp_path, source="scratch/wiped.html")
    r = _run(tmp_path)
    assert r.returncode == 1
    assert "missing on disk" in r.stdout


def test_missing_address_is_flagged(tmp_path):
    _record(tmp_path, address=None)
    r = _run(tmp_path)
    assert r.returncode == 1
    assert "no `address`" in r.stdout


def test_non_url_address_is_flagged(tmp_path):
    _record(tmp_path, address="docs/live.html")
    r = _run(tmp_path)
    assert r.returncode == 1
    assert "not URL-shaped" in r.stdout


def test_missing_date_is_flagged(tmp_path):
    _record(tmp_path, published_at=None)
    r = _run(tmp_path)
    assert r.returncode == 1
    assert "no `published_at`" in r.stdout


def test_one_record_can_carry_several_problems(tmp_path):
    """Reporting only the first problem would send the user round the loop twice."""
    _canvas(tmp_path, "opportunities:\n  - id: opp-001\n    published:\n      - kind: page\n")
    r = _run(tmp_path, "--json")
    assert r.returncode == 1
    assert r.stdout.count('"at":') == 3


# ---------------------------------------------------------------------------
# Absent-input honesty — a green over nothing is the answer that is never true
# ---------------------------------------------------------------------------

def test_absent_canvas_dir_is_a_precondition_failure_not_a_pass(tmp_path):
    r = _run(tmp_path)
    assert r.returncode == 2
    assert "NOTHING WAS AUDITED" in r.stderr


def test_canvas_dir_with_no_files_is_also_a_precondition_failure(tmp_path):
    """An empty canvas dir is a broken tree, NOT a project that publishes nothing."""
    (tmp_path / ".claude" / "canvas").mkdir(parents=True)
    r = _run(tmp_path)
    assert r.returncode == 2
    assert "NOTHING WAS AUDITED" in r.stderr


def test_populated_canvas_with_no_published_records_is_na_not_a_pass(tmp_path):
    """N/A and PASS are different claims: 'nothing published' vs 'all publishes recorded'."""
    _canvas(tmp_path, "opportunities:\n  - id: opp-001\n    status: exploring\n")
    r = _run(tmp_path)
    assert r.returncode == 0
    assert "N/A" in r.stdout
    assert "no-published-records" in r.stdout


def test_unparseable_canvas_is_named_never_silently_empty(tmp_path):
    """A YAML error that reads as 'no records' is the fail-open shape, so it is reported."""
    _record(tmp_path)
    _canvas(tmp_path, "a: [\n", name="broken.yml")
    r = _run(tmp_path, "--json")
    assert "broken.yml" in r.stdout
    assert r.returncode == 0  # the good record is still valid; the skip is reported, not fatal


# ---------------------------------------------------------------------------
# The limit, asserted rather than merely documented
# ---------------------------------------------------------------------------

def test_a_publish_that_recorded_nothing_is_invisible_and_says_so(tmp_path):
    """THE `gates_fired` SHAPE. There is no producer to gate, so this check cannot
    see the commonest failure. Pinned here so nobody later reads its green as
    coverage — and so the N/A text keeps carrying the warning."""
    _canvas(tmp_path, "opportunities:\n  - id: opp-001\n    status: shipped\n")
    r = _run(tmp_path)
    assert r.returncode == 0
    assert "cannot see a publish that recorded nothing" in r.stdout


def test_records_are_found_wherever_they_are_nested(tmp_path):
    """Canvas shapes differ per file; the walker is structural, not path-bound."""
    _canvas(tmp_path, 'a:\n  b:\n    - c:\n        published:\n'
                      '          - address: "not-a-url"\n')
    r = _run(tmp_path)
    assert r.returncode == 1
    assert "a.b[0].c.published[0]" in r.stdout


def test_valid_record_passes_and_states_its_denominator(tmp_path):
    _record(tmp_path)
    r = _run(tmp_path)
    assert r.returncode == 0
    assert "1 published record" in r.stdout


# ---------------------------------------------------------------------------
# In-process: the classifier and the walker, asserted directly
# ---------------------------------------------------------------------------

def test_classify_returns_every_problem_not_just_the_first(scripts_path, tmp_path):
    """One record, three defects. Reporting only the first sends the user round twice."""
    mod = _import(scripts_path)
    problems = mod._classify({}, tmp_path)
    assert len(problems) == 3


def test_classify_accepts_a_complete_record(scripts_path, tmp_path):
    mod = _import(scripts_path)
    (tmp_path / "r.html").write_text("<html>")
    rec = {"address": "https://x.test/a", "source": "r.html", "published_at": "2026-08-24"}
    assert mod._classify(rec, tmp_path) == []


def test_classify_rejects_a_non_mapping_record(scripts_path, tmp_path):
    """A bare string under `published:` is a shape error, not three field errors."""
    mod = _import(scripts_path)
    problems = mod._classify("https://x.test/a", tmp_path)
    assert len(problems) == 1
    assert "not a mapping" in problems[0]


def test_urlish_rejects_a_bare_path_and_accepts_https(scripts_path):
    mod = _import(scripts_path)
    assert mod.URLISH.match("https://x.test/a")
    assert not mod.URLISH.match("docs/live.html")


def test_walk_finds_records_at_any_depth(scripts_path):
    """Canvas files differ in shape, so the walker is structural rather than path-bound."""
    mod = _import(scripts_path)
    doc = {"a": {"b": [{"c": {"published": [{"address": "https://x.test"}]}}]}}
    found = list(mod._walk(doc))
    assert found == [("a.b[0].c.published", [{"address": "https://x.test"}])]


def test_walk_ignores_a_published_key_that_is_not_a_list(scripts_path):
    """`published: true` is a boolean flag in some canvases — not a record set."""
    mod = _import(scripts_path)
    assert list(mod._walk({"x": {"published": True}})) == []


def test_audit_returns_none_for_a_canvas_dir_with_no_files(scripts_path, tmp_path):
    """The precondition state, asserted at the function rather than the exit code."""
    mod = _import(scripts_path)
    (tmp_path / ".claude" / "canvas").mkdir(parents=True)
    assert mod.audit(tmp_path) is None


def test_audit_names_an_unparseable_file_and_keeps_going(scripts_path, tmp_path):
    """A YAML error must not silently reduce the population to zero."""
    mod = _import(scripts_path)
    d = tmp_path / ".claude" / "canvas"
    d.mkdir(parents=True)
    (d / "broken.yml").write_text("a: [\n")
    (d / "ok.yml").write_text('x:\n  published:\n    - address: "nope"\n')
    violations, records, skipped = mod.audit(tmp_path)
    assert records == 1
    assert len(skipped) == 1 and "broken.yml" in skipped[0]
    assert violations


# ---------------------------------------------------------------------------
# In-process main(): every output path, including the ones a black-box suite
# can only observe as an exit code
# ---------------------------------------------------------------------------

def test_main_precondition_writes_to_stderr_not_stdout(scripts_path, tmp_path, capsys):
    """A refusal on stdout can be swallowed by a caller grepping for a verdict."""
    mod = _import(scripts_path)
    assert mod.main(["--project-dir", str(tmp_path)]) == 2
    cap = capsys.readouterr()
    assert "NOTHING WAS AUDITED" in cap.err
    assert cap.out == ""


def test_main_precondition_json_is_machine_readable(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    assert mod.main(["--project-dir", str(tmp_path), "--json"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "precondition-failed"


def test_main_na_json_carries_the_limit(scripts_path, tmp_path, capsys):
    """The N/A payload must keep saying what it cannot see, in both renderings."""
    mod = _import(scripts_path)
    _canvas(tmp_path, "opportunities:\n  - id: opp-001\n")
    assert mod.main(["--project-dir", str(tmp_path), "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "n/a"
    assert "cannot see a publish that recorded nothing" in out["reason"]


def test_main_ok_json_status_is_ok(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    _record(tmp_path)
    assert mod.main(["--project-dir", str(tmp_path), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "ok"


def test_main_human_fail_names_the_file_the_path_and_the_remedy(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    _record(tmp_path, source="scratch/wiped.html")
    assert mod.main(["--project-dir", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "opportunities.yml" in out
    assert "published[0]" in out
    assert "render-conventions.md" in out


def test_main_human_pass_states_its_denominator(scripts_path, tmp_path, capsys):
    """'OK' over an unnamed population is the shape this repo audits everywhere."""
    mod = _import(scripts_path)
    _record(tmp_path)
    assert mod.main(["--project-dir", str(tmp_path)]) == 0
    assert "1 published record" in capsys.readouterr().out


def test_main_reports_skipped_files_on_stderr_even_when_passing(scripts_path, tmp_path, capsys):
    """An unparseable canvas is NAMED whatever the verdict — silence is the fail-open shape."""
    mod = _import(scripts_path)
    _record(tmp_path)
    _canvas(tmp_path, "a: [\n", name="broken.yml")
    assert mod.main(["--project-dir", str(tmp_path)]) == 0
    assert "broken.yml" in capsys.readouterr().err


def test_main_root_is_accepted_as_an_alias(scripts_path, tmp_path, capsys):
    """CI aims scripts with --root; a mismatch here reads as a silent pass."""
    mod = _import(scripts_path)
    _record(tmp_path)
    assert mod.main(["--root", str(tmp_path)]) == 0
    assert "OK" in capsys.readouterr().out
