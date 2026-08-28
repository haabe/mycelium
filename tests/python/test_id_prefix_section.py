"""Coverage for validate_canvas.id_prefix_section_warnings (v0.118.2).

THE DEFECT IT EXISTS FOR. Two `comp-NNN` competitor entries were appended to
`out_of_scope` — a list that holds framework boundary/rationale entries — instead of
`components`, in a 6,000-line file where both lists take `- id:` items. It survived four
days and fooled the mechanism that was supposed to catch it: a weekly harvest check
greps the destination FILE for a detection token, the token matched, and the entry was
recorded as landed in the register it was not in.

An entry outside its register is invisible to every count and every render that reads
that list, while looking present to anything that greps the file.

Measured before shipping: across 25 real canvas files, every ID prefix already lived in
exactly one section. Zero false positives.

The three ways this check could rot, and the tests that stop them:

  1. IT NEVER FIRES. Reproduced here from the real shape — two sections, same prefix.
  2. IT COUNTS CROSS-REFERENCES AS DEFINITIONS. Canvases cite their own ids constantly
     in prose and in fields. If a mention registered as a definition, every mature canvas
     would look misfiled and the check would be muted within a week.
  3. IT FIRES ON UNRELATED PREFIXES SHARING A SECTION. Two different prefixes in one
     section is normal; one prefix across two sections is the defect.
"""
import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

SCRIPT = Path(__file__).resolve().parents[2] / "plugins/mycelium/scripts/validate_canvas.py"


def _mod():
    spec = importlib.util.spec_from_file_location("vc_ids", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["vc_ids"] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture
def canvas(tmp_path):
    d = tmp_path / "canvas"
    d.mkdir()
    return d


def _write(canvas, doc, name="landscape.yml"):
    (canvas / name).write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False))
    return canvas


def test_fires_when_one_prefix_spans_two_sections(canvas):
    """The 2026-08-20 defect, in its original shape."""
    _write(canvas, {
        "components": [{"id": "comp-001"}],
        "out_of_scope": [{"boundary": "a real scope exclusion"}, {"id": "comp-096"}],
    })
    out = _mod().id_prefix_section_warnings(canvas)
    assert len(out) == 1
    assert "comp-NNN" in out[0]
    # Both sections must be named, or the reader cannot tell which one is wrong.
    assert "components" in out[0] and "out_of_scope" in out[0]


def test_silent_when_the_entry_is_in_the_right_place(canvas):
    _write(canvas, {
        "components": [{"id": "comp-001"}, {"id": "comp-096"}],
        "out_of_scope": [{"boundary": "a real scope exclusion"}],
    })
    assert _mod().id_prefix_section_warnings(canvas) == []


def test_cross_references_are_not_definitions(canvas):
    """A canvas citing its own ids in prose must not read as a misfiling.

    This is the false-positive that would mute the check on any mature canvas.
    """
    _write(canvas, {
        "components": [{"id": "comp-001"}],
        "opportunities": [{
            "id": "opp-001",
            "notes": "supersedes comp-001 and relates to comp-002",
            "canvas_refs": ["landscape.yml#comp-001"],
        }],
    })
    assert _mod().id_prefix_section_warnings(canvas) == []


def test_different_prefixes_in_one_section_are_fine(canvas):
    _write(canvas, {"components": [{"id": "comp-001"}, {"id": "tool-002"}]})
    assert _mod().id_prefix_section_warnings(canvas) == []


def test_nested_definitions_count_toward_their_top_level_section(canvas):
    """Solutions nest under opportunities; the section is the top-level key."""
    _write(canvas, {
        "opportunities": [{"id": "opp-001", "solutions": [{"id": "sol-001"}]}],
        "archive": [{"id": "sol-002"}],
    })
    out = _mod().id_prefix_section_warnings(canvas)
    assert len(out) == 1
    assert "sol-NNN" in out[0]


def test_ids_without_a_numeric_suffix_are_ignored(canvas):
    """Named ids like `l0-purpose` are not prefix-numbered registers."""
    _write(canvas, {
        "active_diamonds": [{"id": "l0-purpose"}],
        "archived": [{"id": "l1-strategy"}],
    })
    assert _mod().id_prefix_section_warnings(canvas) == []


def test_unparseable_file_is_skipped_not_crashed(canvas):
    (canvas / "landscape.yml").write_text("components: [oops\n")
    assert _mod().id_prefix_section_warnings(canvas) == []


def test_every_offending_file_is_reported(canvas):
    _write(canvas, {"a": [{"id": "x-001"}], "b": [{"id": "x-002"}]}, name="one.yml")
    _write(canvas, {"c": [{"id": "y-001"}], "d": [{"id": "y-002"}]}, name="two.yml")
    out = _mod().id_prefix_section_warnings(canvas)
    assert len(out) == 2
    assert {"one.yml", "two.yml"} == {w.split(":")[0] for w in out}


# ---------------------------------------------------------------------------
# ROT MODE 4, found in dogfood 2026-08-28 and not anticipated by the three above:
# THE CHECK FIRES ON A REGISTER THAT IS SPLIT BY LIFECYCLE STAGE BY DESIGN.
#
# `human-tasks.yml` defines `ht-NNN` under `pending_tasks`, `completed_tasks` AND
# `closed_without_evidence`. That is the closure path working, and this same module's
# TASK_STATUS_HOMES declares all three to be legitimate homes — so the validator was
# contradicting itself twenty lines apart, on every run, forever.
#
# The docstring's "zero false positives, measured across 25 real canvas files" was
# already false when written: the dogfood canvas had all three lists populated. It was
# measured on prefixes, and `ht` was not among the ones inspected.
#
# The distinction these tests pin: `comp-NNN` in `components` + `out_of_scope` is two
# KINDS sharing a prefix (the defect). `ht-NNN` across three task lists is one KIND at
# three STAGES (the register).
# ---------------------------------------------------------------------------

def test_task_lists_are_one_register_not_a_misfiling(canvas):
    """The false positive: all three task lists populated, which is a healthy canvas."""
    _write(canvas, {
        "pending_tasks": [{"id": "ht-098", "status": "watching"}],
        "completed_tasks": [{"id": "ht-080", "status": "completed"}],
        "closed_without_evidence": [{"id": "ht-010", "status": "abandoned"}],
    }, name="human-tasks.yml")
    assert _mod().id_prefix_section_warnings(canvas) == []


def test_two_of_the_three_task_lists_is_also_fine(canvas):
    """Subset, not equality: a project that has never abandoned a task has two lists."""
    _write(canvas, {
        "pending_tasks": [{"id": "ht-001", "status": "pending"}],
        "completed_tasks": [{"id": "ht-002", "status": "completed"}],
    }, name="human-tasks.yml")
    assert _mod().id_prefix_section_warnings(canvas) == []


def test_a_task_list_plus_a_foreign_section_still_fires(canvas):
    """The exemption is the declared group, NOT 'anything touching a task list'.

    Without this, the fix would silently exempt a genuine misfiling that happened to
    involve one task list — which is how a narrow exemption becomes a blanket one.
    """
    _write(canvas, {
        "pending_tasks": [{"id": "ht-001", "status": "pending"}],
        "archived_experiments": [{"id": "ht-999", "status": "pending"}],
    }, name="human-tasks.yml")
    out = _mod().id_prefix_section_warnings(canvas)
    assert len(out) == 1 and "archived_experiments" in out[0]


def test_the_original_defect_still_fires_after_the_exemption(canvas):
    """Regression guard: the fix must not cost the check the thing it was built for."""
    _write(canvas, {
        "components": [{"id": "comp-001"}],
        "out_of_scope": [{"id": "comp-096"}],
    })
    assert len(_mod().id_prefix_section_warnings(canvas)) == 1


def test_lifecycle_groups_derive_from_the_status_homes(canvas):
    """One source of truth. If someone adds a fourth task list to TASK_STATUS_HOMES and
    the exemption does not follow, this check starts crying wolf again."""
    m = _mod()
    assert (frozenset(m.TASK_STATUS_HOMES),) == m.LIFECYCLE_REGISTER_GROUPS
