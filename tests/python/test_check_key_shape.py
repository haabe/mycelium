"""Coverage for check_key_shape (founder ruling 2026-08-31).

THE RULE. A canvas key carrying a date or entity id in its NAME is content in key position:
a sentence wearing a field's clothes. It is invisible to every field-level mechanism, no
schema can declare it, and a date in a key can only be grepped — which is why
`horizon_set_2026_08_28` can never go overdue while `horizon: 2026-08-28` can.

WAYS THIS COULD ROT:
  1. IT FAILS ON THE WHOLE POPULATION. 507 pre-existing keys were measured at the ruling.
     A gate that fails all of them on day one is a root canal for a floss problem (the
     founder's own opp-072 note) and gets bypassed. The baseline must absorb them.
  2. THE RATCHET NEVER FIRES, which is the defect this entire release is about.
  3. IT PASSES ON A MISSING CANVAS. Exit 0 over nothing means "I looked at nothing and
     everything is fine" — forbidden by check_empty_input_honesty.
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

import yaml

SCRIPT = Path(__file__).resolve().parents[2] / "plugins/mycelium/scripts/check_key_shape.py"


def _mod():
    spec = importlib.util.spec_from_file_location("cks", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["cks"] = m
    spec.loader.exec_module(m)
    return m


def _canvas(tmp_path, doc, name="x.yml"):
    d = tmp_path / ".claude" / "canvas"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(yaml.safe_dump(doc, sort_keys=False))
    return d


def test_a_date_in_a_key_name_is_found(tmp_path):
    m = _mod()
    d = _canvas(tmp_path, {"scope_correction_2026_08_27": "text"})
    assert m.scan(d) == [("x", "scope_correction_2026_08_27")]


def test_an_entity_id_in_a_key_name_is_found(tmp_path):
    m = _mod()
    d = _canvas(tmp_path, {"ht_010_status": "pending"})
    assert m.scan(d) == [("x", "ht_010_status")]


def test_a_date_in_a_value_is_not_flagged(tmp_path):
    """The whole point of the rule: this is the shape it is asking for."""
    m = _mod()
    d = _canvas(tmp_path, {"notes": [{"date": "2026-08-27", "note": "text"}]})
    assert m.scan(d) == []


def test_the_baseline_absorbs_the_existing_population(tmp_path):
    """Rot-mode 1. Seeding then running --strict must pass, or the rule is unadoptable."""
    d = _canvas(tmp_path, {"old_key_2026_08_01": "a", "another_2026_08_02": "b"})
    seed = subprocess.run([sys.executable, str(SCRIPT), "--canvas-dir", str(d),
                           "--write-baseline"], capture_output=True, text=True, check=False)
    assert seed.returncode == 0
    run = subprocess.run([sys.executable, str(SCRIPT), "--canvas-dir", str(d), "--strict"],
                         capture_output=True, text=True, check=False)
    assert run.returncode == 0, run.stdout


def test_a_new_key_fails_after_the_baseline_is_seeded(tmp_path):
    """Rot-mode 2. The ratchet must actually fire."""
    d = _canvas(tmp_path, {"old_key_2026_08_01": "a"})
    subprocess.run([sys.executable, str(SCRIPT), "--canvas-dir", str(d), "--write-baseline"],
                   capture_output=True, text=True, check=False)
    (d / "x.yml").write_text(yaml.safe_dump(
        {"old_key_2026_08_01": "a", "brand_new_2026_09_01": "b"}, sort_keys=False))
    run = subprocess.run([sys.executable, str(SCRIPT), "--canvas-dir", str(d), "--strict"],
                         capture_output=True, text=True, check=False)
    assert run.returncode == 1
    assert "brand_new_2026_09_01" in run.stdout


def test_a_missing_canvas_dir_is_a_refusal_not_a_pass(tmp_path):
    """Rot-mode 3."""
    run = subprocess.run([sys.executable, str(SCRIPT), "--canvas-dir",
                          str(tmp_path / "nope"), "--strict"],
                         capture_output=True, text=True, check=False)
    assert run.returncode == 1
    assert "NOT A PASS" in run.stdout


# --- main()'s reporting paths ------------------------------------------------


def _run(canvas_dir, *extra):
    return subprocess.run([sys.executable, str(SCRIPT), "--canvas-dir", str(canvas_dir),
                           *extra], capture_output=True, text=True, check=False)


def test_report_only_does_not_fail_without_strict(tmp_path):
    """Proportionality: 523 pre-existing keys cannot be a build failure on day one, so the
    default must report and exit 0. --strict is opt-in."""
    d = _canvas(tmp_path, {"thing_2026_08_27": "a"})
    r = _run(d)
    assert r.returncode == 0
    assert "1 NEW" in r.stdout


def test_the_remedy_shows_the_shape_it_wants(tmp_path):
    """A gate that says 'wrong' without showing 'right' gets worked around."""
    d = _canvas(tmp_path, {"thing_2026_08_27": "a"})
    out = _run(d).stdout
    assert "date:" in out and "note:" in out


def test_many_new_keys_are_summarised_rather_than_all_named(tmp_path):
    """A check that prints hundreds of lines is a check people scroll past."""
    d = _canvas(tmp_path, {f"item_{i}_2026_08_{(i % 28) + 1:02d}": "x" for i in range(40)})
    out = _run(d).stdout
    assert "and 15 more" in out


def test_the_baseline_note_explains_why_it_exists(tmp_path):
    """A baseline with no stated reason reads as tolerated debt, which ruff.toml forbids
    elsewhere in this repo for exactly that reason."""
    d = _canvas(tmp_path, {"thing_2026_08_27": "a"})
    _run(d, "--write-baseline")
    doc = yaml.safe_load((d.parent / "harness" / "key-shape-baseline.yml").read_text())
    assert "key position" in doc["note"]
    assert doc["keys"] == ["x:thing_2026_08_27"]


# --- in-process main(), so the coverage floor sees these paths ---------------


def _main(monkeypatch, canvas_dir, *extra):
    import contextlib
    import io
    m = _mod()
    monkeypatch.setattr(sys, "argv", ["check_key_shape.py", "--canvas-dir",
                                      str(canvas_dir), *extra])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = m.main()
    return rc, buf.getvalue()


def test_main_reports_but_does_not_fail_without_strict(tmp_path, monkeypatch):
    d = _canvas(tmp_path, {"thing_2026_08_27": "a"})
    rc, out = _main(monkeypatch, d)
    assert rc == 0
    assert "1 NEW" in out


def test_main_fails_under_strict_on_a_new_key(tmp_path, monkeypatch):
    d = _canvas(tmp_path, {"thing_2026_08_27": "a"})
    rc, out = _main(monkeypatch, d, "--strict")
    assert rc == 1
    assert "thing_2026_08_27" in out


def test_main_seeds_and_then_passes(tmp_path, monkeypatch):
    d = _canvas(tmp_path, {"thing_2026_08_27": "a"})
    rc, out = _main(monkeypatch, d, "--write-baseline")
    assert rc == 0 and "baseline seeded" in out
    rc, out = _main(monkeypatch, d, "--strict")
    assert rc == 0
    assert "No NEW content-in-key" in out


def test_main_refuses_on_a_missing_canvas(tmp_path, monkeypatch):
    rc, out = _main(monkeypatch, tmp_path / "nope", "--strict")
    assert rc == 1
    assert "NOT A PASS" in out


def test_main_truncates_a_long_list(tmp_path, monkeypatch):
    d = _canvas(tmp_path, {f"item_{i}_2026_08_{(i % 28) + 1:02d}": "x" for i in range(40)})
    _, out = _main(monkeypatch, d)
    assert "and 15 more" in out
