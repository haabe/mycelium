"""Coverage tests for check_source_class_fidelity.py — does the label match its source?

Locks in the defect (dogfood 2026-08-08, on a direct founder question). A sweep of 25
canvas files found ten founder-sourced evidence entries: five correctly
`internal_stakeholder`, FIVE claiming `external_human` — the field that means a human
OUTSIDE the project said it. In three of the five the record's own prose already said
otherwise ("[anecdotal, non-arms-length]"; a sibling `source_class: internal_desk` whose
comment read "NO external human has..."), so a human-readable comment and a
machine-readable field disagreed inside one block.

It is not cosmetic: `check_source_independence.py` counts distinct `source_class` values
as method diversity, so a mislabelled founder manufactures corroboration that does not
exist.

`test_founder_labelled_external_is_caught` is the negative control — the exact shape
that shipped undetected. `test_pointer_to_real_outside_person_is_not_flagged` and
`test_founder_word_inside_an_external_source_is_not_flagged` are the precision half:
this check is anchored so that "founder-relayed", "non-founder" and "solo-founder"
inside a genuinely external source do NOT fire, because a false positive here costs a
maintainer an argument with a correct record.
"""
import sys

import yaml


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import check_source_class_fidelity

    return check_source_class_fidelity


def _canvas(project, sources, classes, ident="opp-001", fname="opportunities.yml"):
    """Write one canvas file carrying a single provenance block."""
    canvas = project / ".claude" / "canvas"
    canvas.mkdir(parents=True, exist_ok=True)
    doc = {
        "opportunities": [
            {
                "id": ident,
                "provenance": {
                    "evidence_sources": sources,
                    "source_classes": classes,
                },
            }
        ]
    }
    (canvas / fname).write_text(yaml.safe_dump(doc, allow_unicode=True))
    return canvas


def _run(mod, *argv):
    old = sys.argv
    sys.argv = ["check_source_class_fidelity", *argv]
    try:
        return mod.main()
    finally:
        sys.argv = old


# --- the defect this shipped for -------------------------------------------

def test_founder_labelled_external_is_caught(scripts_path, tmp_path, capsys):
    """THE NEGATIVE CONTROL: the exact five-instance shape found in dogfood."""
    mod = _import(scripts_path)
    _canvas(
        tmp_path,
        ["Founder lived experience 2026-06-01 — verbatim: 'I never felt the urge'"],
        ["external_human"],
    )
    assert _run(mod, "--root", str(tmp_path)) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert "project-own-voice" in out
    assert "OUTSIDE this project" in out
    # the consequence is spelled out, not just the violation
    assert "check_source_independence" in out


def test_self_labelled_tag_contradiction_is_caught(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    _canvas(
        tmp_path,
        ["[artifact_forensics] decision-log 2026-07-07: broadcast 0/19 vs 6/6"],
        ["external_human"],
    )
    assert _run(mod, "--root", str(tmp_path)) == 1
    assert "self-label-contradiction" in capsys.readouterr().out


def test_dogfood_run_labelled_external_is_caught(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    _canvas(
        tmp_path,
        ["MECHANICAL INSTANCE 2 (auto-dogfood run 20260728-041114, verdict gap-proven)"],
        ["external_human"],
    )
    assert _run(mod, "--root", str(tmp_path)) == 1
    assert "not-a-person" in capsys.readouterr().out


def test_misaligned_arrays_are_caught(scripts_path, tmp_path, capsys):
    """Unequal lengths make every pairing meaningless — a precondition failure."""
    mod = _import(scripts_path)
    _canvas(tmp_path, ["a", "b", "c"], ["internal_desk"])
    assert _run(mod, "--root", str(tmp_path)) == 1
    out = capsys.readouterr().out
    assert "[alignment]" in out
    assert "3 evidence_sources vs 1 source_classes" in out


# --- precision: these must NOT fire ----------------------------------------

def test_founder_word_inside_an_external_source_is_not_flagged(scripts_path, tmp_path):
    """`founder-relayed`, `non-founder`, `solo-founder` all appear in real external
    sources. The detector is anchored at the start for exactly this reason."""
    mod = _import(scripts_path)
    _canvas(
        tmp_path,
        [
            "Drew Hoskins, LinkedIn DM 2026-08-01 (ht-003) — verbatim, founder-relayed",
            "Frida (ht-058), the first non-founder instance, arms-length interview",
            "Carta Solo Founders Report 2025: solo founders 23.7% to 36.3%",
        ],
        ["external_human", "external_human", "external_human"],
    )
    assert _run(mod, "--root", str(tmp_path)) == 0


def test_correctly_classed_founder_source_is_not_flagged(scripts_path, tmp_path):
    """The check polices `external_human` only. A founder source correctly labelled
    internal_stakeholder is the fixed state and must stay green."""
    mod = _import(scripts_path)
    _canvas(
        tmp_path,
        ["Founder lived experience 2026-06-01 — verbatim"],
        ["internal_stakeholder"],
    )
    assert _run(mod, "--root", str(tmp_path)) == 0


def test_ordinary_external_human_passes(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    _canvas(
        tmp_path,
        ["u/SagunBuilds, r/buildinpublic 2026-08-08 (ht-070) — answered in ~8 hours"],
        ["external_human"],
    )
    assert _run(mod, "--root", str(tmp_path)) == 0
    assert "OK" in capsys.readouterr().out


# --- empty-input honesty ---------------------------------------------------

def test_no_canvas_dir_refuses_rather_than_passing(scripts_path, tmp_path, capsys):
    """check_empty_input_honesty.py requires this: exit 0 on empty input would mean
    'I looked at nothing and everything is fine', which is never true."""
    mod = _import(scripts_path)
    assert _run(mod, "--root", str(tmp_path)) == 1
    assert "NOT A PASS" in capsys.readouterr().err


def test_unparseable_canvas_is_a_finding_not_a_skip(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    canvas = tmp_path / ".claude" / "canvas"
    canvas.mkdir(parents=True)
    (canvas / "broken.yml").write_text("this: [is: not: valid: yaml")
    assert _run(mod, "--root", str(tmp_path)) == 1
    assert "NOT A PASS" in capsys.readouterr().err


def test_missing_root_is_a_precondition_error(scripts_path, tmp_path):
    mod = _import(scripts_path)
    assert _run(mod, "--root", str(tmp_path / "nope")) == 2


def test_json_mode_reports_status(scripts_path, tmp_path, capsys):
    import json

    mod = _import(scripts_path)
    _canvas(tmp_path, ["Founder lived experience"], ["external_human"])
    assert _run(mod, "--root", str(tmp_path), "--json") == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "violations"
    assert payload["violations"][0]["detector"] == "project-own-voice"


def test_project_dir_alias_works(scripts_path, tmp_path):
    """session-start.sh passes --project-dir; sibling checks disagree on the flag."""
    mod = _import(scripts_path)
    _canvas(tmp_path, ["Founder lived experience"], ["external_human"])
    assert _run(mod, "--project-dir", str(tmp_path)) == 1
