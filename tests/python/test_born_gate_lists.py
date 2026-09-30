"""The list a diamond is born with agrees with the per-transition matrix (v0.297.0, stage 3a).

An L5 was born without the Privacy and Service Quality its own moves require (ruling f, v0.292.0),
and the matrix required Delivery Metrics at L5 after 0.235.0 had removed it from the list. Nothing
compared the two sources.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "plugins" / "mycelium" / "scripts"))
import check_gate_set_drift as drift  # noqa: E402
import scale_locks as sl  # noqa: E402


def test_every_born_list_agrees_with_the_matrix():
    assert drift.born_drift(ROOT, drift.machinery(ROOT)) == []


def test_a_gate_a_transition_requires_is_on_the_list():
    born = drift.machinery(ROOT)
    born["L5"] = born["L5"] - {"privacy"}
    out = drift.born_drift(ROOT, born)
    assert len(out) == 1 and "[L5]" in out[0] and "privacy" in out[0]


def test_a_gate_on_the_list_is_required_somewhere_or_is_a_nudge():
    born = drift.machinery(ROOT)
    born["L5"] = born["L5"] | {"delivery_metrics"}
    out = drift.born_drift(ROOT, born)
    assert len(out) == 1 and "delivery_metrics" in out[0] and "not a NUDGE gate" in out[0]
    born = drift.machinery(ROOT)
    assert {"landscape", "capacity"} <= born["L1"], "the NUDGE gates L1 is born with"


def test_delivery_metrics_is_not_an_l5_gate():
    """Its definition says L3-L4; 0.235.0: a market diamond has no deploys of its own."""
    assert "delivery_metrics" not in sl.transition_gates("L5", "deliver->complete")
    assert "delivery_metrics" in sl.transition_gates("L4", "deliver->complete")


def test_explainability_is_not_required_at_birth():
    """It applies only with AI components, so no list carries it."""
    assert all("explainability" not in g for g in drift.machinery(ROOT).values())
    assert drift.born_drift(ROOT, drift.machinery(ROOT)) == []
