"""G-V12 coverage proof for check_source_independence.py.

THE GAP IT CLOSES. G-D2 ("triangulate: 2+ independent evidence types") and G-D4
("2+ evidence sources per opportunity") are named guardrails carrying a declared
`NUDGE` level. Grep the repo for either and every hit is markdown — guardrails.md,
guardrails-discovery.md, guardrails-index.md. Nothing enforced them, for the
whole life of the framework.

Scenario-per-guardpost:
  happy — 2 sources, 2 distinct methods, established claim -> silence
  sad   — 1 source carrying `data-supported`               -> G-D2 finding
  sad   — 3 sources, all one method, established           -> G-D2 finding
  bad   — no provenance anywhere (empty population)        -> refuse, exit 1
  bad   — unparseable canvas                               -> exit 1, names it
  edge  — 1 source honestly labelled anecdotal/0.3         -> silence (compliant)
  edge  — multi-source but unclassified                    -> not judged, not a
          finding, and the coverage limit is stated rather than passed over
  edge  — the same defect in an OUT-OF-SCOPE canvas        -> ignored
  edge  — plain and --json reach the same verdict          -> parity
"""

import json
import subprocess
import sys

import pytest

SCRIPT = "check_source_independence.py"


def _canvas(tmp_path, filename="opportunities.yml", body=""):
    d = tmp_path / ".claude" / "canvas"
    d.mkdir(parents=True, exist_ok=True)
    (d / filename).write_text(body)
    return tmp_path


def _run(scripts_path, root, as_json=False):
    cmd = [sys.executable, str(scripts_path / SCRIPT), "--root", str(root)]
    if as_json:
        cmd.append("--json")
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _opp(sources, classes=None, etype="data-supported", conf=0.6, ident="opp-001"):
    """Build one opportunity with a provenance block.

    `source_classes` sits at the SAME indent as `evidence_sources` — both are
    keys of `provenance`. Getting that wrong put it beside `provenance` instead
    of inside it, and the happy-path test then passed while proving nothing,
    which is the exact defect this release is about.
    """
    src = "\n".join(f"        - {s}" for s in sources)
    cls = ""
    if classes is not None:
        cls = ("      source_classes:\n"
               + "\n".join(f"        - {c}" for c in classes) + "\n")
    return (
        "schema_version: 1\n"
        "opportunities:\n"
        f"  - id: {ident}\n"
        "    provenance:\n"
        f"      evidence_type: {etype}\n"
        f"      confidence: {conf}\n"
        "      evidence_sources:\n"
        f"{src}\n"
        f"{cls}"
    )


# ---------------------------------------------------------------- happy


def test_two_distinct_methods_passes(scripts_path, tmp_path):
    root = _canvas(tmp_path, body=_opp(
        ["interview with A", "analytics snapshot"],
        ["external_human", "external_data"],
    ))
    r = _run(scripts_path, root)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "no breadth violations" in r.stdout
    # PROVE THE CLASSIFICATION WAS ACTUALLY READ. Without this the test passes
    # identically when source_classes lands at the wrong indent and is never
    # parsed — which is how it was first written, and it was green.
    assert "declaring source_classes   : 1" in r.stdout
    assert "judgeable for triangulation: 1" in r.stdout


# ---------------------------------------------------------------- sad


def test_single_source_above_anecdotal_is_a_finding(scripts_path, tmp_path):
    """G-D2's own sentence: single-source evidence is anecdotal (0.3),
    regardless of how compelling it feels."""
    root = _canvas(tmp_path, body=_opp(["one blog post"], etype="data-supported"))
    r = _run(scripts_path, root)
    assert r.returncode == 1, r.stdout
    assert "G-D2" in r.stdout
    assert "single-source evidence is anecdotal" in r.stdout


def test_many_sources_one_method_is_a_finding(scripts_path, tmp_path):
    """The count says three; the coverage says one. Every source shares the
    method's blind spot, which is the whole of the practitioner's argument and
    the reason G-D2 says TYPES rather than sources."""
    root = _canvas(tmp_path, body=_opp(
        ["interview A", "interview B", "interview C"],
        ["external_human", "external_human", "external_human"],
    ))
    r = _run(scripts_path, root)
    assert r.returncode == 1, r.stdout
    assert "all `external_human`" in r.stdout
    assert "blind spot" in r.stdout


# ---------------------------------------------------------------- bad


def test_empty_population_refuses(scripts_path, tmp_path):
    """No provenance anywhere must not read as compliance."""
    root = _canvas(tmp_path, body="schema_version: 1\nopportunities: []\n")
    r = _run(scripts_path, root)
    assert r.returncode == 1, r.stdout
    assert "NO BREADTH VERDICT AVAILABLE" in r.stdout


def test_unparseable_canvas_is_not_silence(scripts_path, tmp_path):
    """A corrupt canvas is the state most likely to hold the drift, and it must
    not be indistinguishable from an empty one."""
    root = _canvas(tmp_path, body="opportunities: [unclosed\n  - broken: :\n")
    r = _run(scripts_path, root)
    assert r.returncode == 1, r.stdout
    assert "UNPARSEABLE" in r.stdout
    assert "opportunities.yml" in r.stdout


# ---------------------------------------------------------------- edge


def test_single_source_honestly_labelled_is_compliant(scripts_path, tmp_path):
    """THE FALSE-POSITIVE THIS CHECK WAS ALMOST BUILT WITH.

    A naive G-D4 count check flagged 3 opportunities on the real canvas for
    having one source. All three were labelled `anecdotal` at 0.3 — which is
    exactly what G-D2 prescribes for single-source evidence. They were obeying
    the rule the check would have failed them for.
    """
    root = _canvas(tmp_path, body=_opp(
        ["one conversation"], etype="anecdotal", conf=0.3,
    ))
    r = _run(scripts_path, root)
    assert r.returncode == 0, r.stdout
    assert "no breadth violations" in r.stdout


def test_unclassified_sources_are_not_judged_and_say_so(scripts_path, tmp_path):
    """Unclassified defaults to internal_desk for ratio maths, which would make
    an unclassified 5-source claim look identical to real monoculture. Trusting
    that default produced 40 findings on the dogfood canvas and every one was an
    artefact. Not judged, not passed, and the limit is printed."""
    root = _canvas(tmp_path, body=_opp(
        ["interview A", "interview B", "interview C"], classes=None,
    ))
    r = _run(scripts_path, root)
    assert r.returncode == 0, r.stdout
    assert "triangulation could not be judged" in r.stdout
    assert "not a pass" in r.stdout


def test_out_of_scope_canvas_is_ignored(scripts_path, tmp_path):
    """G-D2 governs research findings and G-D4 the OST. Pointing this at
    landscape.yml produced 8 findings during construction, all competitor
    entries recorded once from one source, none of them what either guardrail is
    about. A guard that fires outside its scope gets muted."""
    root = _canvas(tmp_path, filename="landscape.yml",
                   body=_opp(["one blog post"], etype="data-supported",
                             ident="comp-001").replace("opportunities:", "competitors:"))
    r = _run(scripts_path, root)
    # Nothing in scope at all -> refusal, NOT a finding about landscape.yml
    assert r.returncode == 1, r.stdout
    assert "NO BREADTH VERDICT AVAILABLE" in r.stdout
    assert "comp-001" not in r.stdout


@pytest.mark.parametrize("body", [
    "schema_version: 1\nopportunities: []\n",                       # empty
    _opp(["one blog post"], etype="data-supported"),                # finding
    _opp(["a", "b"], ["external_human", "external_data"]),          # clean
])
def test_json_and_plain_agree(scripts_path, tmp_path, body):
    """THE SYSTEMIC v0.77.0 DEFECT: five scripts had their refuse-on-empty
    branch inside the `else` of `if args.json:`, so the surface a CI wrapper
    reads was more forgiving than the human one."""
    root = _canvas(tmp_path, body=body)
    plain = _run(scripts_path, root)
    js = _run(scripts_path, root, as_json=True)
    assert plain.returncode == js.returncode, (
        f"plain={plain.returncode} json={js.returncode}\n{plain.stdout}"
    )
    payload = json.loads(js.stdout)
    assert payload["exit_code"] == js.returncode


# ---------------------------------------------------------------- in-process
# The tests above drive the CLI as a subprocess, which is the right shape for
# exit codes and --json parity and the wrong shape for coverage: coverage.py
# cannot instrument a child interpreter, so the pre-push per-file floor read this
# script as 0% covered while eleven tests exercised it. These call the pure
# functions directly, so the floor measures what the suite actually reaches.


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import check_source_independence
    return check_source_independence


def test_scan_counts_classification_coverage(scripts_path, tmp_path):
    mod = _import(scripts_path)
    root = _canvas(tmp_path, body=_opp(["a", "b"], ["external_human", "external_data"]))
    result = mod.scan(root)
    assert result["provenance_objects"] == 1
    assert result["fully_classified"] == 1
    assert result["diversity_judgeable"] == 1
    assert result["findings"] == []


def test_scan_treats_partial_classification_as_unjudgeable(scripts_path, tmp_path):
    """Two sources, ONE class listed. Not fully classified, so rule 2 cannot run —
    and it must not be silently completed with the internal_desk default."""
    mod = _import(scripts_path)
    root = _canvas(tmp_path, body=_opp(["a", "b"], ["external_human"]))
    result = mod.scan(root)
    assert result["fully_classified"] == 0
    assert result["diversity_judgeable"] == 0
    assert result["findings"] == []


def test_overclaim_helper_matches_g_d2s_own_numbers(scripts_path):
    mod = _import(scripts_path)
    assert mod._overclaims_on_one_source({"evidence_type": "data-supported"})
    assert mod._overclaims_on_one_source({"confidence": 0.5})
    assert not mod._overclaims_on_one_source({"evidence_type": "anecdotal",
                                              "confidence": 0.3})
    assert not mod._overclaims_on_one_source({"evidence_type": "speculation"})


def test_established_helper(scripts_path):
    mod = _import(scripts_path)
    assert mod._is_established({"confidence": 0.6})
    assert mod._is_established({"evidence_type": "test-validated"})
    assert not mod._is_established({"evidence_type": "anecdotal", "confidence": 0.4})


def test_verdict_refuses_before_choosing_an_output_format(scripts_path):
    """The v0.77.0 defect was a refusal branch living inside `else: if args.json`.
    Computing the verdict once, ahead of any renderer, is what prevents it."""
    mod = _import(scripts_path)
    code, headline = mod.verdict({
        "root": ".", "scope": ["opportunities.yml"], "provenance_objects": 0,
        "fully_classified": 0, "diversity_judgeable": 0, "findings": [],
        "unparseable": [],
    })
    assert code == 1
    assert mod.NO_VERDICT_MARKER in headline


def test_verdict_reports_unparseable_ahead_of_everything(scripts_path):
    mod = _import(scripts_path)
    code, headline = mod.verdict({
        "root": ".", "scope": [], "provenance_objects": 5, "fully_classified": 5,
        "diversity_judgeable": 5, "findings": [], "unparseable": ["x.yml: boom"],
    })
    assert code == 1
    assert "UNPARSEABLE" in headline


def _main(mod, monkeypatch, root, as_json=False):
    argv = ["check_source_independence.py", "--root", str(root)]
    if as_json:
        argv.append("--json")
    monkeypatch.setattr(sys, "argv", argv)
    return mod.main()


def test_main_renders_a_finding_and_the_coverage_note(scripts_path, tmp_path,
                                                      monkeypatch, capsys):
    """Covers the human renderer: headline, denominators, the finding, and the
    unclassified footnote that must not read as a violation."""
    mod = _import(scripts_path)
    root = _canvas(tmp_path, body=_opp(["only source"], etype="data-supported"))
    code = _main(mod, monkeypatch, root)
    out = capsys.readouterr().out
    assert code == 1
    assert "Evidence breadth (G-D2/G-D4)" in out
    assert "provenance objects" in out
    assert "[G-D2]" in out
    assert "not a pass" in out


def test_main_json_renderer_carries_the_same_exit_code(scripts_path, tmp_path,
                                                       monkeypatch, capsys):
    mod = _import(scripts_path)
    root = _canvas(tmp_path, body=_opp(["a", "b"],
                                       ["external_human", "external_data"]))
    code = _main(mod, monkeypatch, root, as_json=True)
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["exit_code"] == 0
    assert payload["fully_classified"] == 1


def test_main_without_a_canvas_directory_refuses(scripts_path, tmp_path,
                                                 monkeypatch, capsys):
    """No .claude/canvas at all. Absent is the least-informed state and must not
    be the most forgiving one."""
    mod = _import(scripts_path)
    code = _main(mod, monkeypatch, tmp_path)
    out = capsys.readouterr().out
    assert code == 1
    assert mod.NO_VERDICT_MARKER in out
