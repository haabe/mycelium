"""tests/python/test_check_ice_aggregate.py — the ICE aggregate guard.

WHY THESE ASSERTIONS. The guard has one arithmetic job and three ways to get it wrong in a way that
reads as success:

  1. Passing a product because it only knew one field-name shape. A real canvas carried SEVEN
     shapes; the abbreviated `i/c/e` form alone hid two product-shaped aggregates from an ad-hoc
     scan written the same day. A checker blind to a shape reports that shape as clean.
  2. Failing the whole historical corpus, which forces the very backfill the design refuses. The
     baseline exists so a closed decision keeps the number it was actually made with.
  3. Passing a block whose factors are absent. Nothing can be recomputed there, and reporting that
     as OK would turn "cannot be checked" into "checked and fine" — the distinction this project
     keeps finding as the expensive one.

The negative control is `test_bites_on_a_new_product`: if the guard cannot fail, the green it prints
on the dogfood canvas means nothing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"))

import check_ice_aggregate as mod


def _project(tmp_path: Path, opportunities: dict) -> Path:
    canvas = tmp_path / ".claude" / "canvas"
    canvas.mkdir(parents=True)
    (canvas / "opportunities.yml").write_text(yaml.safe_dump(opportunities), encoding="utf-8")
    return tmp_path


def _leaf(leaf_id: str, key: str, block: dict) -> dict:
    return {"opportunities": [{"id": "opp-1", "solutions": [{"id": leaf_id, key: block}]}]}


def test_bites_on_a_new_product(tmp_path, capsys):
    """NEGATIVE CONTROL. A guard that cannot fail is not a guard."""
    root = _project(tmp_path, _leaf("sol-1", "ice",
                                    {"impact": 8, "confidence": 7, "ease": 8, "score": 448}))
    assert mod.main(["--project-dir", str(root)]) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert "7.67" in out, "must show the mean it should have been, not just that it is wrong"


def test_accepts_the_ellis_mean(tmp_path):
    root = _project(tmp_path, _leaf("sol-1", "ice",
                                    {"impact": 8, "confidence": 7, "ease": 8, "score": 7.67}))
    assert mod.main(["--project-dir", str(root)]) == 0


def test_reads_the_abbreviated_factor_form(tmp_path, capsys):
    """`i/c/e` is not a synonym the checker may skip: it hid two real product-shaped
    aggregates from a hand-written scan of the same canvas."""
    root = _project(tmp_path, _leaf("sol-1", "ice_score", {"i": 6, "c": 4, "e": 8, "total": 192}))
    assert mod.main(["--project-dir", str(root)]) == 1
    assert "192" in capsys.readouterr().out


@pytest.mark.parametrize("key", ["ice", "ice_score"])
def test_reads_both_block_keys(tmp_path, key):
    """Both keys are live on real canvases and mean different things (original vs blind
    re-derivation). The guard reads both and rewrites neither into the other."""
    root = _project(tmp_path, _leaf("sol-1", key,
                                    {"impact": 4, "confidence": 2, "ease": 8, "total": 64}))
    assert mod.main(["--project-dir", str(root)]) == 1


@pytest.mark.parametrize("agg_key", ["total", "score"])
def test_reads_both_aggregate_keys(tmp_path, agg_key):
    root = _project(tmp_path, _leaf("sol-1", "ice",
                                    {"impact": 4, "confidence": 2, "ease": 8, agg_key: 64}))
    assert mod.main(["--project-dir", str(root)]) == 1


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
    """The pre-errata corpus must not force a rewrite; a NEW product must still bite."""
    root = _project(tmp_path, _leaf("sol-old", "ice",
                                    {"impact": 8, "confidence": 7, "ease": 8, "score": 448}))
    assert mod.main(["--project-dir", str(root), "--write-baseline"]) == 0
    assert mod.main(["--project-dir", str(root)]) == 0, "baselined history is not a failure"

    # A second leaf appears after adoption. The baseline must not cover it.
    doc = yaml.safe_load((root / ".claude" / "canvas" / "opportunities.yml").read_text())
    doc["opportunities"][0]["solutions"].append(
        {"id": "sol-new", "ice": {"impact": 5, "confidence": 8, "ease": 8, "score": 320}})
    (root / ".claude" / "canvas" / "opportunities.yml").write_text(yaml.safe_dump(doc))

    assert mod.main(["--project-dir", str(root)]) == 1
    out = capsys.readouterr().out
    assert "sol-new" in out
    assert "sol-old" not in out.split("FAIL")[1], "a baselined leaf must not be re-reported as new"


def test_baseline_records_identifiers_not_values(tmp_path):
    root = _project(tmp_path, _leaf("sol-1", "ice",
                                    {"impact": 8, "confidence": 7, "ease": 8, "score": 448}))
    mod.main(["--project-dir", str(root), "--write-baseline"])
    data = json.loads((root / ".claude" / "evals" / "ice-aggregate-baseline.json").read_text())
    assert data["product_shaped"] == ["opportunities.yml:sol-1:ice"]
    assert "never grow" in data["_comment"], "the baseline must state its own direction of travel"


def test_no_canvas_is_reported_as_not_scanned(tmp_path, capsys):
    """Silence on an empty scan is how a check reads green in a project it never looked at."""
    assert mod.main(["--project-dir", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "N/A" in out
    assert "not a pass" in out
