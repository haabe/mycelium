"""tests/python/test_check_ice_aggregate.py — the ICE aggregate guard.

THE RULE IT GUARDS CHANGED IN 0.319.0. From v0.238.0 to 0.318.x the guard made sure a stored
aggregate was the AVERAGE of its factors (Ellis; errata A1). Since 0.319.0 the documented
arithmetic is Gilad's, Impact x Confidence x Ease (errata A7), so a new or changed aggregate must
be the PRODUCT, and the averages already on a canvas are history.

WHY THESE ASSERTIONS. The guard has one arithmetic job and four ways to get it wrong in a way that
reads as success:

  1. Passing an average because it only knew one field-name shape. A real canvas carried SEVEN
     shapes; the abbreviated `i/c/e` form alone hid two aggregates from an ad-hoc scan written the
     same day. A checker blind to a shape reports that shape as clean.
  2. Failing the whole historical corpus, which forces the very backfill the design refuses. The
     baseline exists so a closed decision keeps the number it was actually made with: an average
     from 0.229.0 to 0.318.x, a product from before.
  3. Passing a block whose factors are absent. Nothing can be recomputed there, and reporting that
     as OK would turn "cannot be checked" into "checked and fine" — the distinction this project
     keeps finding as the expensive one.
  4. Reading a baseline written under the OLD rule as if it covered the new one. It lists products,
     which are now correct, and says nothing about the averages; treating it as adoption would
     either fail every average written in good faith or pass every new one.

The negative control is `test_bites_on_a_new_average`: if the guard cannot fail, the green it
prints on the dogfood canvas means nothing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"))

import check_ice_aggregate as mod

#: (8, 7, 8): the product is 448, the average 7.67. The same triple the 0.238.0 tests used, read
#: the other way round.
AVERAGED = {"impact": 8, "confidence": 7, "ease": 8, "score": 7.67}
MULTIPLIED = {"impact": 8, "confidence": 7, "ease": 8, "score": 448}


def _project(tmp_path: Path, opportunities: dict) -> Path:
    canvas = tmp_path / ".claude" / "canvas"
    canvas.mkdir(parents=True)
    (canvas / "opportunities.yml").write_text(yaml.safe_dump(opportunities), encoding="utf-8")
    return tmp_path


def _leaf(leaf_id: str, key: str, block: dict) -> dict:
    return {"opportunities": [{"id": "opp-1", "solutions": [{"id": leaf_id, key: block}]}]}


def _adopt(root: Path) -> None:
    """Take the baseline under the current rule, as a project does once."""
    assert mod.main(["--project-dir", str(root), "--write-baseline"]) == 0


def _baseline(root: Path) -> dict:
    return json.loads((root / ".claude" / "evals" / "ice-aggregate-baseline.json").read_text())


def _add_leaf(root: Path, leaf: dict) -> None:
    path = root / ".claude" / "canvas" / "opportunities.yml"
    doc = yaml.safe_load(path.read_text())
    doc["opportunities"][0]["solutions"].append(leaf)
    path.write_text(yaml.safe_dump(doc))


def _clean_adopted_project(tmp_path: Path) -> Path:
    """A project that took the baseline with nothing to record, then scores again."""
    root = _project(tmp_path, _leaf("sol-0", "ice", dict(MULTIPLIED)))
    _adopt(root)
    return root


def test_bites_on_a_new_average(tmp_path, capsys):
    """NEGATIVE CONTROL. A guard that cannot fail is not a guard."""
    root = _clean_adopted_project(tmp_path)
    _add_leaf(root, {"id": "sol-1", "ice": dict(AVERAGED)})
    assert mod.main(["--project-dir", str(root)]) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert "448" in out, "must show the product it should have been, not just that it is wrong"
    assert "sol-1" in out and "[new]" in out


def test_accepts_the_gilad_product(tmp_path):
    """The aggregate `/mycelium:ice-score` writes since 0.319.0 passes with no baseline at all."""
    root = _project(tmp_path, _leaf("sol-1", "ice", dict(MULTIPLIED)))
    assert mod.main(["--project-dir", str(root)]) == 0


def test_accepts_a_product_of_meter_values_at_the_precision_it_was_written(tmp_path):
    """Gilad's Confidence is a decimal (1.96 in his worked example), so the product is one too,
    and he says the decimal point does not matter. 4 x 1.96 x 2 = 15.68: every rounding of it is
    the product, and none of them may be reported as a mistake."""
    for stored in (15.68, 15.7, 16):
        root = _project(tmp_path / str(stored), _leaf(
            "sol-1", "ice", {"impact": 4, "confidence": 1.96, "ease": 2, "total": stored}))
        assert mod.main(["--project-dir", str(root)]) == 0, stored


def test_a_zero_impact_idea_totals_zero_and_that_is_the_product(tmp_path):
    """0 is a legal Impact in Gilad's range (0-10), and the product is then 0."""
    root = _project(tmp_path, _leaf(
        "sol-1", "ice", {"impact": 0, "confidence": 0.61, "ease": 6, "total": 0}))
    assert mod.main(["--project-dir", str(root)]) == 0


def test_reads_the_abbreviated_factor_form(tmp_path, capsys):
    """`i/c/e` is not a synonym the checker may skip: it hid two real aggregates from a
    hand-written scan of the same canvas."""
    root = _clean_adopted_project(tmp_path)
    _add_leaf(root, {"id": "sol-1", "ice_score": {"i": 6, "c": 4, "e": 8, "total": 6}})
    assert mod.main(["--project-dir", str(root)]) == 1
    assert "192" in capsys.readouterr().out


@pytest.mark.parametrize("key", ["ice", "ice_score"])
def test_reads_both_block_keys(tmp_path, key):
    """Both keys are live on real canvases and mean different things (original vs blind
    re-derivation). The guard reads both and rewrites neither into the other."""
    root = _clean_adopted_project(tmp_path)
    _add_leaf(root, {"id": "sol-1", key: {"impact": 4, "confidence": 2, "ease": 9, "total": 5}})
    assert mod.main(["--project-dir", str(root)]) == 1


@pytest.mark.parametrize("agg_key", ["total", "score"])
def test_reads_both_aggregate_keys(tmp_path, agg_key):
    root = _clean_adopted_project(tmp_path)
    _add_leaf(root, {"id": "sol-1", "ice": {"impact": 4, "confidence": 2, "ease": 9, agg_key: 5}})
    assert mod.main(["--project-dir", str(root)]) == 1


def test_an_aggregate_that_is_neither_fails_when_new_and_says_so(tmp_path, capsys):
    """A hand-set number is not the product either. It is named as such, not as an average."""
    root = _clean_adopted_project(tmp_path)
    _add_leaf(root, {"id": "sol-1", "ice": {"impact": 4, "confidence": 2, "ease": 9, "total": 50}})
    assert mod.main(["--project-dir", str(root)]) == 1
    out = capsys.readouterr().out
    assert "neither" in out and "72" in out


def test_an_advisory_re_derivation_is_flagged_as_one(tmp_path, capsys):
    """A frozen review artifact marked `advisory: true` is read like any other block and labelled,
    so a reader can tell a blind re-derivation from the score a decision rested on."""
    root = _clean_adopted_project(tmp_path)
    _add_leaf(root, {"id": "sol-1", "ice": dict(AVERAGED, advisory=True)})
    assert mod.main(["--project-dir", str(root)]) == 1
    assert "[advisory re-derivation]" in capsys.readouterr().out


def test_missing_factors_are_unverifiable_not_passing(tmp_path, capsys):
    """An aggregate with no factors cannot be recomputed. Reporting it as OK would convert
    'cannot be checked' into 'checked and fine'."""
    root = _project(tmp_path, _leaf("sol-1", "ice", {"score": 144, "advisory": True}))
    rc = mod.main(["--project-dir", str(root)])
    out = capsys.readouterr().out
    assert rc == 0, "unverifiable is not a failure"
    assert "UNVERIFIABLE" in out
    assert "not a failure and not a pass" in out.lower()


def test_baseline_suppresses_the_historical_corpus_only(tmp_path, capsys):
    """The averages written under the earlier rule must not force a rewrite; a NEW one must
    still bite."""
    root = _project(tmp_path, _leaf("sol-old", "ice", dict(AVERAGED)))
    _adopt(root)
    assert mod.main(["--project-dir", str(root)]) == 0, "baselined history is not a failure"

    # A second leaf appears after adoption. The baseline must not cover it.
    _add_leaf(root, {"id": "sol-new", "ice": {"impact": 5, "confidence": 8, "ease": 8, "score": 7}})
    capsys.readouterr()
    assert mod.main(["--project-dir", str(root)]) == 1
    out = capsys.readouterr().out
    assert "sol-new" in out
    assert "sol-old" not in out.split("FAIL")[1], "a baselined leaf must not be re-reported as new"


def test_a_baselined_aggregate_that_changes_is_no_longer_history(tmp_path, capsys):
    """The baseline holds the VALUE, not only the identifier. A leaf re-scored after the rule
    changed, and averaged again, is a new mistake wearing an old id."""
    root = _project(tmp_path, _leaf("sol-old", "ice", dict(AVERAGED)))
    _adopt(root)
    path = root / ".claude" / "canvas" / "opportunities.yml"
    doc = yaml.safe_load(path.read_text())
    doc["opportunities"][0]["solutions"][0]["ice"] = {
        "impact": 9, "confidence": 7, "ease": 8, "score": 8.0}
    path.write_text(yaml.safe_dump(doc))
    assert mod.main(["--project-dir", str(root)]) == 1
    out = capsys.readouterr().out
    assert "[changed; the baseline holds 7.67]" in out
    assert "504" in out


def test_a_baselined_aggregate_re_scored_as_a_product_shrinks_the_baseline(tmp_path, capsys):
    root = _project(tmp_path, _leaf("sol-old", "ice", dict(AVERAGED)))
    _adopt(root)
    path = root / ".claude" / "canvas" / "opportunities.yml"
    doc = yaml.safe_load(path.read_text())
    doc["opportunities"][0]["solutions"][0]["ice"] = {
        "impact": 8, "confidence": 3.5, "ease": 8, "score": 224}
    path.write_text(yaml.safe_dump(doc))
    assert mod.main(["--project-dir", str(root)]) == 0
    assert "1 since re-scored or removed" in capsys.readouterr().out


def test_baseline_records_identifiers_with_the_values_they_carried(tmp_path):
    root = _project(tmp_path, _leaf("sol-1", "ice", dict(AVERAGED)))
    _adopt(root)
    data = _baseline(root)
    assert data["not_product"] == {"opportunities.yml:sol-1:ice": [7.67]}
    assert data["rule"] == "product" and data["rule_since"] == "0.319.0"
    assert "never grow" in data["_comment"], "the baseline must state its own direction of travel"


def test_the_canvas_is_never_rewritten(tmp_path):
    """Neither a check run nor a baseline run touches canvas data. The average stays an average."""
    root = _project(tmp_path, _leaf("sol-1", "ice", dict(AVERAGED)))
    path = root / ".claude" / "canvas" / "opportunities.yml"
    before = path.read_bytes()
    mod.main(["--project-dir", str(root)])
    _adopt(root)
    mod.main(["--project-dir", str(root)])
    assert path.read_bytes() == before


# --- a project that took its baseline before 0.319.0 ------------------------------------------


def _pre_rule_project(tmp_path: Path) -> Path:
    """What a consumer of 0.238.0 to 0.318.x has on disk: products from before 0.229.0 (in the
    old baseline), averages written since (correct until this release, in no baseline)."""
    root = _project(tmp_path, {"opportunities": [{"id": "opp-1", "solutions": [
        {"id": "sol-old-product", "ice": dict(MULTIPLIED)},
        {"id": "sol-old-average", "ice": dict(AVERAGED)},
    ]}]})
    evals = root / ".claude" / "evals"
    evals.mkdir(parents=True)
    (evals / "ice-aggregate-baseline.json").write_text(json.dumps({
        "_comment": "written by 0.238.0",
        "product_shaped": ["opportunities.yml:sol-old-product:ice"]}))
    return root


def test_averages_from_the_earlier_rule_are_never_failed(tmp_path, capsys):
    """On the first run after the upgrade the averages cannot be told from new ones, and the
    guard says so: exit 2, not the FAIL verdict, and never a pass."""
    root = _pre_rule_project(tmp_path)
    assert mod.main(["--project-dir", str(root)]) == 2
    out = capsys.readouterr().out
    assert "CANNOT ASSESS" in out
    assert "FAIL:" not in out, "history is not given the FAIL verdict"
    assert "THIS IS NOT A PASS" in out
    assert "sol-old-average" in out
    assert "sol-old-product" not in out, "a product is the documented arithmetic now"
    assert "Do NOT re-score" in out
    assert "--write-baseline" in out


def test_rebaselining_after_the_upgrade_keeps_the_old_record_and_then_bites(tmp_path, capsys):
    root = _pre_rule_project(tmp_path)
    _adopt(root)
    data = _baseline(root)
    assert data["not_product"] == {"opportunities.yml:sol-old-average:ice": [7.67]}
    assert data["product_shaped"] == ["opportunities.yml:sol-old-product:ice"], (
        "the 0.238.0 list is a record of that adoption; it is carried over, not dropped")
    assert mod.main(["--project-dir", str(root)]) == 0

    _add_leaf(root, {"id": "sol-new", "ice": {"impact": 5, "confidence": 8, "ease": 8, "score": 7}})
    capsys.readouterr()
    assert mod.main(["--project-dir", str(root)]) == 1
    out = capsys.readouterr().out
    assert "sol-new" in out.split("FAIL")[1]
    assert "sol-old-average" not in out.split("FAIL")[1]


def test_no_baseline_and_an_average_cannot_be_assessed(tmp_path, capsys):
    """With no baseline at all the guard cannot date the average either. It names both readings
    (history: baseline once; new: fix the score first) and passes neither."""
    root = _project(tmp_path, _leaf("sol-1", "ice", dict(AVERAGED)))
    assert mod.main(["--project-dir", str(root)]) == 2
    out = capsys.readouterr().out
    assert "no baseline exists" in out
    assert "fix that score first" in out


def test_an_unreadable_baseline_is_named_not_treated_as_empty(tmp_path, capsys):
    root = _project(tmp_path, _leaf("sol-1", "ice", dict(AVERAGED)))
    evals = root / ".claude" / "evals"
    evals.mkdir(parents=True)
    (evals / "ice-aggregate-baseline.json").write_text("{not json")
    assert mod.main(["--project-dir", str(root)]) == 2
    assert "could not be read" in capsys.readouterr().out


def test_growing_an_existing_baseline_is_said_out_loud(tmp_path, capsys):
    """`--write-baseline` a second time records whatever is there. It may; it must not do so
    quietly, because adding a new mistake to the baseline is the one wrong use of the flag."""
    root = _project(tmp_path, _leaf("sol-old", "ice", dict(AVERAGED)))
    _adopt(root)
    _add_leaf(root, {"id": "sol-new", "ice": {"impact": 5, "confidence": 8, "ease": 8, "score": 7}})
    capsys.readouterr()
    _adopt(root)
    out = capsys.readouterr().out
    assert "GREW by 1" in out and "sol-new" in out
    assert "sol-old" not in out.split("GREW")[1]


def test_no_canvas_is_reported_as_not_scanned(tmp_path, capsys):
    """Silence on an empty scan is how a check reads green in a project it never looked at."""
    assert mod.main(["--project-dir", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "N/A" in out
    assert "not a pass" in out
