"""What counts as an assessment in the records the safety skills write. One definition, two readers.

WHY THIS FILE EXISTS (v0.331.0). Two scripts read the same records and asked different questions
of them with different code: `check_assessment_landed.py` asked whether an assessment landed at
all, and `scale_locks.py` let the Privacy gate pass on `last_assessed` plus an inventory without
opening the principles, while Service Quality and Explainability passed on a status word. The
skills that write these records define a complete one in their own text:

  privacy-check   all seven Privacy-by-Design principles get `assessment` and `evidence`, and
                  "Never stamp `last_assessed` in a run that does not also fill the principles";
  service-check   `principles[]` with `assessment`, `evidence` and `issues`, and `not-assessed`
                  "MUST NOT BE USED AS A DEFAULT"; the gate's pass criterion is all 15;
  xai-check       a `services[].xai` block with a verdict for each of its five stages.

So the bar here is each skill's own, not a new one. A record a reader can check is a principle
judged (an assessment other than the schema default) AND carrying evidence that says what was
observed. The question "did anything land" and the question "is the record complete" stay
different, and both are answered from the functions below, so the two readers cannot drift apart
again (the shape logged in the dogfood project as sibling-rule-carries-the-carve-out, widened to
sibling scripts 2026-10-28).
"""
from __future__ import annotations

NOT_ASSESSED = "not-assessed"

#: The seven keys privacy-check fills (Cavoukian), as its canvas section names them.
PRIVACY_PRINCIPLES = (
    "proactive_not_reactive", "privacy_as_default", "privacy_embedded", "full_functionality",
    "end_to_end_security", "visibility_transparency", "respect_for_users",
)

#: Downe's fifteen principles. The Service Quality gate's pass criterion is "Service evaluated
#: against all 15 Downe principles" at every scale it applies to (engine/theory-gates.md). The
#: lighter set service-check names for an L3 (1-4, 8, 10, 11) is an input to the Four Risks before
#: the L3 builds, not this gate's bar. A principle that does not apply is judged `n/a` with a line
#: of evidence saying why, which counts.
SERVICE_PRINCIPLES_ALL = tuple(range(1, 16))


def _text(value) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple)):
        return any(_text(v) for v in value)
    return False


def items(doc, key: str = "principles") -> list[tuple[str, dict]] | None:
    """`(id, item)` for each entry under `key`, from a mapping (key -> item) or a list of mappings
    with an `id`. None when the field is neither, so a shape nobody registered is not judged."""
    value = (doc or {}).get(key) if isinstance(doc, dict) else None
    if isinstance(value, dict):
        return [(str(k), v) for k, v in value.items() if isinstance(v, dict)]
    if isinstance(value, list):
        return [(str(v.get("id")), v) for v in value if isinstance(v, dict)]
    return None


def judged(item: dict, field: str = "assessment", default: str = NOT_ASSESSED) -> bool:
    """An assessment was made: the field holds something other than the schema default."""
    return str(item.get(field) or "").strip().lower() not in ("", default)


def judged_with_evidence(item: dict) -> bool:
    """Judged, and the `evidence` says what was observed: the record a later reader can check."""
    return judged(item) and _text(item.get("evidence"))


def missing(doc, wanted, key: str = "principles") -> list[str]:
    """The ids in `wanted` that are absent, unjudged, or judged with no evidence."""
    have = {i.strip(): it for i, it in (items(doc, key) or [])}
    return [str(w) for w in wanted if not judged_with_evidence(have.get(str(w), {}))]


def _verdict(block, key: str) -> bool:
    stage = block.get(key)
    return isinstance(stage, dict) and _text(stage.get("verdict"))


def xai_stages_missing(xai, scale: str = "L4") -> list[str]:
    """The xai-check stages a `services[].xai` block holds no verdict for, at the depth the scale
    asks (engine/theory-gates.md, gate 13): an L3 needs stage 1, the tier; an L4 or L5 every stage.
    Stage 5 (recourse) is required from the `limited` tier up, as the skill says; at `minimal` it is
    not asked."""
    if not isinstance(xai, dict):
        return ["the xai block"]
    out = []
    if not _text(xai.get("tier")):
        out.append("stage 1, `tier`")
    if scale not in ("L4", "L5"):
        return out
    if not xai.get("surfaces"):
        out.append("stage 2, `surfaces`")
    for stage, key in ((3, "fidelity"), (4, "system_card")):
        if not _verdict(xai, key):
            out.append(f"stage {stage}, `{key}.verdict`")
    tier = str(xai.get("tier") or "").strip().lower()
    if tier != "minimal" and not _verdict(xai, "recourse"):
        out.append("stage 5, `recourse.verdict`")
    return out
