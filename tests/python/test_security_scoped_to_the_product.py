"""Security and privacy checks are scoped to what the product holds and does (v0.271.0).

Founder, 2026-09-26: "2fa and so on might not be applicable for all products." The E2E second world,
a bookkeeping service delivered by hand, was reviewed against the OWASP web checklist (CORS, SQL
parameters, security headers, multi-factor login); theory-gates.md said a purely offline service's
Security gate was N/A, which the lock cannot honour; and the product-type "conditioning" it cited
existed nowhere in the product-type profiles.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2] / "plugins" / "mycelium"


def _text(rel: str) -> str:
    return (ROOT / rel).read_text()


def test_the_review_records_its_scope_before_its_checklist():
    skill = _text("skills/security-review/SKILL.md")
    step0, checklist = skill.index("## Step 0: Scope"), skill.index("## Checklist (OWASP")
    assert step0 < checklist, "the scope comes first"
    for field in ("runs_code", "accounts", "personal_data", "money", "reach"):
        assert field in skill[step0:checklist], field
    assert "applies when `runs_code`" in skill, "the web checklist is scoped to code"
    assert "Authentication items (A07: sessions, passwords, multi-factor) | `accounts`" in skill
    assert "`n/a: <reason>`" in skill and "The threat model is never `n/a`" in skill
    assert "Documents and data handled by people" in skill, "a service has its own section"


def test_privacy_controls_are_proportional():
    skill = _text("skills/privacy-check/SKILL.md")
    assert "- [ ] Encryption at rest and in transit\n" not in skill
    assert "encryption where personal data is stored or sent electronically" in skill
    assert "holds no personal data, say so in the data inventory" in skill


def test_the_gate_text_matches_what_the_lock_enforces():
    gates = _text("engine/theory-gates.md")
    assert "If purely offline service, this gate is N/A" not in gates, "the lock cannot honour N/A"
    assert "the gate is never N/A" in gates
    assert "conditioned on product_type" not in _text("engine/confidence-thresholds.yml")


def test_the_scope_has_a_place_in_the_threat_model_schema():
    import json
    schema = json.loads(_text("schemas/canvas/threat-model.schema.json"))
    scope = schema["properties"]["scope"]["properties"]
    assert set(scope) == {"runs_code", "accounts", "personal_data", "money", "reach"}
    doc = yaml.safe_load("scope:\n  runs_code: false\n  accounts: false\n"
                         "  personal_data: client bank exports\n  money: true\n"
                         "  reach: three named clients\n")
    assert isinstance(doc["scope"]["runs_code"], bool)
