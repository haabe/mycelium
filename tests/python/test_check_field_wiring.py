"""Coverage for check_field_wiring (2026-08-31).

THE GAP IT EXISTS FOR. A field blessed by a schema, filled by a skill, and read by nothing
looks populated to a human and is inert to the machine. Measured that day: 6 of 38
promise-shaped fields had no consumer, and `unlocked_at` was one of them — added HOURS
EARLIER in the release that fixed exactly this defect.

THE WAYS THIS GATE COULD ROT, one test each:

  1. THE REGISTRY LAUNDERS ITS OWN CONTENTS. field-consumers.yml names every unwired field
     and lives under harness/, which the scan reads. On its first run the gate reported
     38/38 wired the moment the registry was written — a record that a field has no reader
     counted as reading it. Caught only because the number moved with no code change.
  2. THE RATCHET NEVER FIRES. A gate that cannot fail is the thing this whole release is
     about, so a new unwired field must actually exit 1.
  3. A RENDERER STOPS COUNTING. The founder's rule is explicit that being drawn into "a more
     humane form, like a mermaid chart" is being read. Narrowing consumers back to code
     would re-flag four fields the framework legitimately renders.
"""
import importlib.util
import json
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "plugins/mycelium/scripts/check_field_wiring.py"
ROOT = SCRIPT.parent.parent


def _mod():
    spec = importlib.util.spec_from_file_location("cfw", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["cfw"] = m
    spec.loader.exec_module(m)
    return m


def test_the_registry_is_not_counted_as_a_consumer():
    """Rot-mode 1, narrowed 2026-08-31 when the first fields were actually WIRED.

    The invariant is not "every registry entry is unwired" — entries with `verdict: wired`
    now have real consumers, which is the point of the registry. The invariant is that
    naming a field in field-consumers.yml must not BY ITSELF make it look consumed. So the
    check applies to entries that claim no code consumer: human-only, UNRULED, DELETED.
    Those must still scan as unwired, or the record of a field having no reader is being
    counted as reading it.
    """
    m = _mod()
    rows, registry = m.scan(ROOT)
    assert registry, "registry should hold the baselined fields"
    unwired = {n for n, _, kinds in rows if not kinds}
    for name, entry in registry.items():
        if entry.get("verdict") in ("wired", "wired-via-contents", "DELETED"):
            continue
        assert name in unwired, (
            f"{name} is recorded as having NO consumer, yet the scan found one — "
            "the registry is laundering its own contents")


def test_a_wired_verdict_is_backed_by_an_actual_consumer():
    """The other direction, added with the first real wirings: a registry claiming a field
    is wired while nothing reads it would be a lie that reads as a green.

    `wired-via-contents` is deliberately NOT accepted here. That verdict exists for a container
    whose inner edges are traversed generically while its own name is read by nothing — and it
    was created because this test caught `technical_capabilities_required` claiming plain
    `wired` when no script contained the string. The tempting fix was to name the field in a
    script so the scanner would see it; that is gaming the instrument.
    """
    m = _mod()
    rows, registry = m.scan(ROOT)
    consumers = {n: kinds for n, _, kinds in rows}
    for name, entry in registry.items():
        if entry.get("verdict") != "wired":
            continue
        assert consumers.get(name), (
            f"{name} is recorded as wired, but the scan finds no consumer for it")


def test_a_renderer_counts_as_a_consumer():
    """Rot-mode 3. The founder's rule names the mermaid case explicitly."""
    m = _mod()
    rows, _ = m.scan(ROOT)
    kinds = {n: k for n, _, k in rows}
    assert "render" in kinds.get("theory_gates_status", []), \
        "theory_gates_status is drawn by the render fleet and must score as wired"


def test_a_new_unwired_promise_field_is_reported(tmp_path):
    """Rot-mode 2, on a synthetic tree so the real schemas are untouched."""
    m = _mod()
    root = tmp_path / "plug"
    for d in ("schemas/canvas", "scripts", "hooks", "skills", "engine", "harness"):
        (root / d).mkdir(parents=True)
    (root / "schemas/canvas/x.schema.json").write_text(json.dumps(
        {"type": "object", "properties": {"review_deadline": {"type": "string"}}}))
    rows, registry = m.scan(root)
    assert [n for n, _, k in rows if not k] == ["review_deadline"]
    assert registry == {}, "no registry in the synthetic tree, so the field is NEW"


def test_a_field_with_no_promise_in_its_name_is_not_demanded(tmp_path):
    """The gate must not demand a consumer for every descriptive field; a canvas is
    partly a human document and over-firing is how a check gets muted."""
    m = _mod()
    root = tmp_path / "plug"
    for d in ("schemas/canvas", "scripts", "hooks", "skills", "engine", "harness"):
        (root / d).mkdir(parents=True)
    (root / "schemas/canvas/x.schema.json").write_text(json.dumps(
        {"type": "object", "properties": {"narrative": {"type": "string"}}}))
    rows, _ = m.scan(root)
    assert rows == []


def test_empty_input_is_a_refusal_not_a_pass(tmp_path):
    """Rot-mode 4, and it was caught by another gate rather than by me.

    check_empty_input_honesty.py failed this script on its first full run: over a tree with
    no schemas it printed a clean summary and exited 0, which means "I looked at nothing and
    everything is fine" — the one answer that is never true. The anti-inertness gate was
    itself inert on empty input.
    """
    import subprocess
    root = tmp_path / "plug"
    (root / "schemas").mkdir(parents=True)
    for d in ("scripts", "hooks", "skills", "engine", "harness"):
        (root / d).mkdir(parents=True)
    r = subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), "--strict"],
                       capture_output=True, text=True, check=False)
    assert r.returncode == 1
    assert "NOT A PASS" in r.stdout


# --- main()'s reporting paths, which the scan-level tests never reach ---------


def _run(root, *extra):
    import subprocess
    return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), *extra],
                          capture_output=True, text=True, check=False)


def _tree(tmp_path, schema_props, registry=None):
    root = tmp_path / "plug"
    for d in ("schemas/canvas", "scripts", "hooks", "skills", "engine", "harness"):
        (root / d).mkdir(parents=True, exist_ok=True)
    (root / "schemas/canvas/x.schema.json").write_text(
        json.dumps({"type": "object", "properties": schema_props}))
    if registry is not None:
        import yaml
        (root / "harness/field-consumers.yml").write_text(yaml.safe_dump(registry))
    return root


def test_a_new_unwired_field_fails_under_strict_and_names_itself(tmp_path):
    root = _tree(tmp_path, {"review_deadline": {"type": "string"}})
    r = _run(root, "--strict")
    assert r.returncode == 1
    assert "review_deadline" in r.stdout
    assert "mermaid" in r.stdout, "the remedy must restate the founder's rule"


def test_the_same_field_passes_once_it_carries_a_ruling(tmp_path):
    root = _tree(tmp_path, {"review_deadline": {"type": "string"}},
                 registry={"reviewed": [{"field": "review_deadline", "consumer": "human",
                                         "verdict": "human-only"}]})
    r = _run(root, "--strict")
    assert r.returncode == 0
    assert "No NEW unwired field" in r.stdout


def test_an_unruled_baseline_entry_is_reported_every_run(tmp_path):
    """A verdict of UNRULED must not fail, and must not go quiet either — that is how a
    deferral becomes the permanent state."""
    root = _tree(tmp_path, {"review_deadline": {"type": "string"}},
                 registry={"reviewed": [{"field": "review_deadline", "verdict": "UNRULED"}]})
    r = _run(root, "--strict")
    assert r.returncode == 0
    assert "await a founder ruling" in r.stdout
    assert "review_deadline" in r.stdout


def test_a_wired_field_is_counted_by_the_kind_of_consumer(tmp_path):
    root = _tree(tmp_path, {"review_deadline": {"type": "string"}})
    (root / "scripts" / "reader.py").write_text('x = data["review_deadline"]\n')
    r = _run(root, "--strict")
    assert r.returncode == 0
    assert "code=1" in r.stdout


# --- in-process main(), so the coverage floor actually sees these paths -------
# The subprocess tests above prove the CLI contract but are invisible to coverage,
# which traces only the test process. Both matter: the CLI is what CI runs.


def _main(monkeypatch, root, *extra):
    import contextlib
    import io
    m = _mod()
    monkeypatch.setattr(sys, "argv", ["check_field_wiring.py", "--root", str(root), *extra])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = m.main()
    return rc, buf.getvalue()


def test_main_reports_a_new_unwired_field(tmp_path, monkeypatch):
    root = _tree(tmp_path, {"review_deadline": {"type": "string"}})
    rc, out = _main(monkeypatch, root, "--strict")
    assert rc == 1
    assert "review_deadline" in out


def test_main_passes_with_a_ruling(tmp_path, monkeypatch):
    root = _tree(tmp_path, {"review_deadline": {"type": "string"}},
                 registry={"reviewed": [{"field": "review_deadline", "verdict": "human-only"}]})
    rc, out = _main(monkeypatch, root, "--strict")
    assert rc == 0
    assert "No NEW unwired field" in out


def test_main_refuses_on_an_empty_tree(tmp_path, monkeypatch):
    root = tmp_path / "bare"
    for d in ("schemas", "scripts", "hooks", "skills", "engine", "harness"):
        (root / d).mkdir(parents=True)
    rc, out = _main(monkeypatch, root, "--strict")
    assert rc == 1
    assert "NOT A PASS" in out


def test_main_reports_unruled_entries(tmp_path, monkeypatch):
    root = _tree(tmp_path, {"review_deadline": {"type": "string"}},
                 registry={"reviewed": [{"field": "review_deadline", "verdict": "UNRULED"}]})
    rc, out = _main(monkeypatch, root, "--strict")
    assert rc == 0
    assert "await a founder ruling" in out


# --- --similar: step (b) of the four-step new-field rule ---------------------
# Synonym proliferation is measured, not hypothetical: `surfaced_by` was agent-invented and
# reached 42 uses beside the existing provenance / source_class mechanism, unreconciled.


def test_similar_reports_an_exact_existing_name(tmp_path, monkeypatch):
    root = _tree(tmp_path, {"kill_criterion": {"type": "string"}})
    rc, out = _main(monkeypatch, root, "--similar", "kill_criterion")
    assert rc == 0
    assert "ALREADY EXISTS" in out


def test_similar_finds_a_near_duplicate_name(tmp_path, monkeypatch):
    """The case the rule exists for: inventing a synonym for something already present."""
    root = _tree(tmp_path, {"surfaced_by": {"type": "string"},
                            "decided_by": {"type": "string"}})
    rc, out = _main(monkeypatch, root, "--similar", "raised_by")
    assert rc == 0
    assert "surfaced_by" in out or "decided_by" in out


def test_similar_says_so_plainly_when_a_name_is_genuinely_new(tmp_path, monkeypatch):
    """A check that never clears anything trains people to ignore it."""
    root = _tree(tmp_path, {"kill_criterion": {"type": "string"}})
    rc, out = _main(monkeypatch, root, "--similar", "quantum_flux")
    assert rc == 0
    assert "none" in out
    assert "(a), (c) and (d) still apply" in out
