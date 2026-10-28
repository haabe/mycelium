"""The release gate reads the record each safety skill writes, not a date or a status word (v0.331.0).

Until 0.330.1 the Privacy gate passed on `last_assessed` plus an inventory with every principle
unjudged, the case privacy-check warns against in its own text, and Service Quality and
Explainability passed on the status word while service-check and xai-check write a full record.
Each test below fails on 0.330.1 except the controls, which say what must keep passing: `n/a` on the
two gates that allow it, an AI-only gate on a product with no AI, and a complete record.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "plugins" / "mycelium" / "scripts" / "scale_locks.py"
_spec = importlib.util.spec_from_file_location("scale_locks", SCRIPT)
sl = importlib.util.module_from_spec(_spec)
sys.modules["scale_locks"] = sl
_spec.loader.exec_module(sl)

PRIVACY_KEYS = ("proactive_not_reactive", "privacy_as_default", "privacy_embedded",
                "full_functionality", "end_to_end_security", "visibility_transparency",
                "respect_for_users")


def _privacy(judged=PRIVACY_KEYS, evidence=True):
    return {"last_assessed": "2026-10-28", "data_inventory": [{"data_type": "email"}],
            "principles": {k: ({"assessment": "pass",
                                "evidence": "consent screen read in the app" if evidence else ""}
                               if k in judged else {"assessment": "not-assessed", "evidence": ""})
                           for k in PRIVACY_KEYS}}


def _principle(i, evidence=True):
    return {"id": i, "assessment": "partial", "evidence": "walked the sign-up flow" if evidence else ""}


def _xai(**over):
    block = {"tier": "limited", "surfaces": {"end_user": {"output": "pass"}},
             "fidelity": {"verdict": "not_applicable"}, "system_card": {"verdict": "partial"},
             "recourse": {"verdict": "pass"}}
    block.update(over)
    return block


def _project(tmp_path: Path, privacy=None, services=None, ai=False) -> str:
    c = tmp_path / ".claude"
    (c / "canvas").mkdir(parents=True, exist_ok=True)
    (c / "diamonds").mkdir(parents=True, exist_ok=True)
    (c / "diamonds" / "active.yml").write_text(yaml.safe_dump({"active_diamonds": []}))
    if privacy is not None:
        (c / "canvas" / "privacy-assessment.yml").write_text(yaml.safe_dump(privacy))
    if services is not None:
        (c / "canvas" / "services.yml").write_text(yaml.safe_dump(services))
    if ai:
        (c / "jit-tooling").mkdir(parents=True, exist_ok=True)
        (c / "jit-tooling" / "active-stack.yml").write_text(
            yaml.safe_dump({"ai_components": {"detected": True}}))
    return str(tmp_path)


def _diamond(scale, **gates):
    return {"id": f"{scale.lower()}-x", "scale": scale, "theory_gates_status": gates}


# --- Privacy: the seven principles, judged with evidence -----------------------------------------

def test_privacy_dated_with_an_inventory_and_no_principle_judged_is_not_a_record(tmp_path):
    st = sl.State(_project(tmp_path, privacy=_privacy(judged=())))
    msg = st.gate_missing(_diamond("L3", privacy="pass"), "privacy")
    assert msg and "principles" in msg


def test_privacy_with_a_principle_judged_but_no_evidence_is_not_a_record(tmp_path):
    st = sl.State(_project(tmp_path, privacy=_privacy(evidence=False)))
    assert st.gate_missing(_diamond("L3", privacy="pass"), "privacy")


def test_privacy_missing_one_of_the_seven_is_not_a_record_and_is_named(tmp_path):
    st = sl.State(_project(tmp_path, privacy=_privacy(judged=PRIVACY_KEYS[:6])))
    msg = st.gate_missing(_diamond("L3", privacy="pass"), "privacy")
    assert msg and "respect_for_users" in msg and "proactive_not_reactive" not in msg


def test_control_privacy_with_all_seven_judged_with_evidence_passes(tmp_path):
    st = sl.State(_project(tmp_path, privacy=_privacy()))
    assert st.gate_missing(_diamond("L3", privacy="pass"), "privacy") is None


# --- Service quality: the principles the scale names ----------------------------------------------

def test_service_pass_with_no_services_record_is_refused(tmp_path):
    st = sl.State(_project(tmp_path))
    msg = st.gate_missing(_diamond("L3", service_quality="pass"), "service_quality")
    assert msg and "services.yml" in msg


def test_service_pass_needs_all_fifteen_at_every_scale(tmp_path):
    """engine/theory-gates.md: "Service evaluated against all 15 Downe principles". The lighter L3
    set in service-check feeds the Four Risks before building; it is not this gate's bar."""
    light = [_principle(i) for i in (1, 2, 3, 4, 8, 10, 11)]
    st = sl.State(_project(tmp_path, services={"principles": light}))
    for scale in ("L3", "L4"):
        msg = st.gate_missing(_diamond(scale, service_quality="pass"), "service_quality")
        assert msg and "5" in msg and "15" in msg


def test_control_a_principle_judged_na_with_a_reason_counts(tmp_path):
    rows = [_principle(i) for i in range(1, 15)]
    rows.append({"id": 15, "assessment": "n/a", "evidence": "no staff behind a CLI to reach"})
    st = sl.State(_project(tmp_path, services={"principles": rows}))
    assert st.gate_missing(_diamond("L4", service_quality="pass"), "service_quality") is None


def test_service_principle_judged_without_evidence_does_not_count(tmp_path):
    rows = [_principle(i, evidence=(i != 10)) for i in range(1, 16)]
    st = sl.State(_project(tmp_path, services={"principles": rows}))
    msg = st.gate_missing(_diamond("L4", service_quality="pass"), "service_quality")
    assert msg and "10" in msg


def test_control_service_na_needs_no_record(tmp_path):
    st = sl.State(_project(tmp_path))
    assert st.gate_missing(_diamond("L4", service_quality="n/a"), "service_quality") is None


def test_control_service_all_fifteen_judged_passes_at_l4(tmp_path):
    st = sl.State(_project(tmp_path, services={"principles": [_principle(i) for i in range(1, 16)]}))
    assert st.gate_missing(_diamond("L4", service_quality="pass"), "service_quality") is None


# --- Explainability: a verdict per xai-check stage, only with AI components -----------------------

def test_explainability_pass_with_ai_and_no_xai_block_is_refused(tmp_path):
    st = sl.State(_project(tmp_path, services={"services": [{"id": "svc-1"}]}, ai=True))
    msg = st.gate_missing(_diamond("L4", explainability="pass"), "explainability")
    assert msg and "xai" in msg


def test_explainability_block_missing_a_stage_is_refused(tmp_path):
    svc = {"services": [{"id": "svc-1", "xai": _xai(system_card={})}]}
    st = sl.State(_project(tmp_path, services=svc, ai=True))
    msg = st.gate_missing(_diamond("L4", explainability="pass"), "explainability")
    assert msg and "system_card" in msg


def test_explainability_at_l3_needs_the_tier_and_no_later_stage(tmp_path):
    """engine/theory-gates.md gate 13: an L3 runs stage 1; every stage is an L4's."""
    only_tier = {"services": [{"id": "svc-1", "xai": {"tier": "limited"}}]}
    st = sl.State(_project(tmp_path, services=only_tier, ai=True))
    assert st.gate_missing(_diamond("L3", explainability="pass"), "explainability") is None
    assert st.gate_missing(_diamond("L4", explainability="pass"), "explainability")
    no_tier = sl.State(_project(tmp_path / "b", services={"services": [{"id": "s", "xai": {
        "surfaces": {"end_user": {"output": "pass"}}}}]}, ai=True))
    assert no_tier.gate_missing(_diamond("L3", explainability="pass"), "explainability")


def test_control_explainability_minimal_tier_needs_no_recourse(tmp_path):
    svc = {"services": [{"id": "svc-1", "xai": _xai(tier="minimal", recourse=None)}]}
    st = sl.State(_project(tmp_path, services=svc, ai=True))
    assert st.gate_missing(_diamond("L4", explainability="pass"), "explainability") is None


def test_control_explainability_on_a_product_with_no_ai_is_not_asked(tmp_path):
    st = sl.State(_project(tmp_path))
    assert st.gate_missing(_diamond("L4", explainability="pass"), "explainability") is None


# --- The exposure records read the same rule ------------------------------------------------------

def test_exposure_with_a_service_pass_and_no_record_does_not_cover_a_release(tmp_path):
    st = sl.State(_project(tmp_path, privacy=_privacy()))
    exposure = {"recorded_at": "2026-10-28", "audience": "five named testers",
                "channel": "a link", "data_class": "none", "until": "2099-01-01",
                "consent": "asked in person",
                "gates": {"security": "n/a", "privacy": "pass", "service_quality": "pass",
                          "regulatory": "pass"}}
    miss = sl._record_problems(st, _diamond("L3"), exposure, "2026-10-28")
    assert any("service_quality" in m and "services.yml" in m for m in miss)
