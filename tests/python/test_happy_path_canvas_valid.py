"""The happy path writes a canvas Mycelium's own validator accepts (v0.248.1).

The first E2E happy-path run (run 18, plugin 0.248.0) failed `validate_canvas.py` three ways within its
first session, on state written by Mycelium's own skills following their own instructions:
  - `created: 2026-09-24`, written unquoted as every author writes a date, loaded as a date object that
    the `iso_timestamp` string pattern rejected;
  - the interview's JTBD stub carried a provenance block without `evidence_type` and `evidence_sources`,
    which the jobs schema requires;
  - `/purpose-properties` recorded aspirations with `aspiration_reason` and no `binding`, which the
    purpose schema requires on every property.
Each is a skill instruction or a validator that disagreed with the schema. Pinned where each lives.
"""

from __future__ import annotations

import datetime
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "mycelium"
_spec = importlib.util.spec_from_file_location("validate_canvas", PLUGIN / "scripts" / "validate_canvas.py")
vc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vc)


def test_yaml_dates_are_read_as_iso_strings():
    doc = {"created": datetime.date(2026, 9, 24),
           "log": [{"at": datetime.datetime(2026, 9, 24, 8, 30, tzinfo=datetime.UTC)}],
           "n": 3}
    out = vc.iso_dates(doc)
    assert out == {"created": "2026-09-24", "log": [{"at": "2026-09-24T08:30:00+00:00"}], "n": 3}


def test_load_yaml_normalises_dates(tmp_path):
    f = tmp_path / "x.yml"
    f.write_text("created: 2026-09-24\n")
    assert vc.load_yaml(f) == {"created": "2026-09-24"}


def test_the_interview_writes_a_complete_jtbd_provenance():
    text = (PLUGIN / "skills" / "interview" / "SKILL.md").read_text(encoding="utf-8")
    assert "provenance: {evidence_type: speculation, evidence_sources:" in text


def test_purpose_properties_writes_binding_on_aspirations():
    text = (PLUGIN / "skills" / "purpose-properties" / "SKILL.md").read_text(encoding="utf-8")
    assert "record `binding: false` and `aspiration_reason`" in text
