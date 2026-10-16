"""A record's `on` date reads the same however it was typed (v0.326.2).

`on` is a YAML 1.1 boolean, so a bare `on:` key loads as the key True, and an unquoted date loads as a
date object. The diamond-progress template showed a decision with a bare `on: <YYYY-MM-DD>`, and the
harms-check template showed `on: 2026-10-11` unquoted. Copied as shown, every decision rendered as
"date not recorded", the rule that refuses a changed decision date could not see the date, and a
recorded harms check read as no check at all. Found on the dogfood project 2026-10-16, when a script
raised KeyError 'on' on two decisions written from the template."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2] / "plugins" / "mycelium"
sys.path.insert(0, str(ROOT / "scripts"))
import render_diamonds as rd  # noqa: E402
import scale_locks as sl  # noqa: E402

# Typed the way the templates showed it, not written through yaml.safe_dump (which quotes `on`).
BARE = """
id: l3-x
scale: L3
name: Test
decisions:
- decision: set_target
  on: 2026-10-16
- decision: start_experiment
  on: '2026-10-17'
"""


def test_a_bare_on_key_and_an_unquoted_date_still_give_the_date():
    entries = yaml.safe_load(BARE)["decisions"]
    assert True in entries[0]  # the trap itself: YAML moved the date under the key True
    assert [sl.record_date(e) for e in entries] == ["2026-10-16", "2026-10-17"]


def test_a_quoted_key_still_reads_as_before():
    entry = yaml.safe_load("decision: close\n'on': '2026-10-18'\n")
    assert sl.record_date(entry) == "2026-10-18"


def test_a_decision_typed_bare_keeps_its_date_for_the_rewrite_check():
    had = yaml.safe_load(BARE)["decisions"]
    has = yaml.safe_load(BARE.replace("on: 2026-10-16", "on: 2026-10-01"))["decisions"]
    assert sl._decision_key(had[0]) == ("set_target", "2026-10-16")
    assert any("moved from 2026-10-16 to 2026-10-01" in line for line in sl._rewrites(had, has))


def test_the_render_shows_the_date_of_a_decision_typed_bare():
    view = rd.diamond_view(yaml.safe_load(BARE), ai=False)
    assert [r["on"] for r in view["recorded"]] == ["2026-10-16", "2026-10-17"]


def test_a_harms_check_typed_as_its_template_showed_is_a_recorded_verdict():
    record = yaml.safe_load("harms_check:\n  on: 2026-10-11\n  verdict: net-positive\n  note: checked\n")
    assert sl._harms_verdict(record) == "net-positive"


def test_no_template_shows_a_bare_on_key_any_more():
    bare = re.compile(r"^\s*on: ", re.MULTILINE)
    for skill in ("diamond-progress", "harms-check"):
        text = (ROOT / "skills" / skill / "SKILL.md").read_text()
        assert not bare.search(text), f"{skill}/SKILL.md shows a bare `on:` key"
