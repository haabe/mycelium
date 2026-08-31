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
    """Rot-mode 1. Every field the registry names must still scan as unwired."""
    m = _mod()
    rows, registry = m.scan(ROOT)
    assert registry, "registry should hold the baselined fields"
    unwired = {n for n, _, kinds in rows if not kinds}
    for name in registry:
        assert name in unwired, (
            f"{name} is recorded as having NO consumer, yet the scan found one — "
            "the registry is laundering its own contents")


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
