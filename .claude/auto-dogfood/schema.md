# Auto-Dogfood Scenario Schema

Full-session dogfood scenarios extend the eval scenario format (`.claude/evals/schema.md`)
with multi-turn orchestration, user persona simulation, and planted failure conditions.

## Scenario Families

Each scenario belongs to a family that defines what class of agent behavior it tests. Families make coverage gaps visible — if a family has zero scenarios, that's an untested failure mode.

*Inspired by: greyhaven-ai/autocontext's 11 scenario families — a taxonomy of "what kinds of things can go wrong."*

| Family | Tests | Mycelium Mechanism | Current Scenarios |
|--------|-------|--------------------|-------------------|
| `guardrail` | Does the agent stop when it should? | Anti-patterns, guardrails | sw-web-team-skip-discovery, ai-agent-solo-confidence-inflate, sw-solo-hollow-bvssh |
| `gate` | Do theory gates fire correctly? | Theory gates, confidence | ai-tool-solo-theory-gates, sw-solo-evidence-decay, sw-solo-shallow-cynefin |
| `lifecycle` | Does diamond progression work end-to-end? | Diamond phases, transitions | sw-api-solo-happy-path, sw-solo-lifecycle-cycle-recording, sw-solo-perspective-conflict |
| `delivery` | Do completion gates validate properly? | DoD, BVSSH, DORA | sw-api-solo-deliver-complete, sw-lib-solo-coding-quality, sw-cli-solo-happy-full |
| `product_type` | Do non-software product types work? | Canvas routing, product_type | content-solo-l5-market, ai-tool-solo-value-risk, service-team-multiscale-l2-l4, course-solo-value-risk |
| `value_risk` | Does the agent detect value-risk failures? | Four risks, JTBD | sw-cli-solo-value-risk, ai-tool-solo-value-risk, course-solo-value-risk |
| `strategy` | Do L0/L1 scales work? | Wardley, North Star, Team Topologies | saas-solo-l1-strategy |
| `exploration` | Does OST/ICE pipeline work? | OST builder, ICE scoring | sw-tool-solo-ost-exploration |
| `onboarding` | Can a new user get value in 10 minutes? | /interview, cold-start | *NONE — gap* |
| `mid_project` | Does the agent handle contradictory evidence? | Canvas with pre-populated conflicts | *NONE — gap* |
| `determinism` | Does the same scenario produce consistent results? | Repeated runs, flake rate | *NONE — gap* |

Three families have zero scenarios — these are known coverage gaps (see LEARNING-STRATEGY.md §Known Issues).

## Scenario YAML Format

```yaml
name: "Human-readable scenario name"
category: dogfood
type: full-session
difficulty: easy | medium | hard
family: guardrail | gate | lifecycle | delivery | product_type | value_risk | strategy | exploration | onboarding | mid_project | determinism

# Product definition — what the simulated user is building
product:
  name: "Product name"
  type: software | content_course | content_publication | content_media | ai_tool | service_offering
  description: |
    One-paragraph product description.
  pitch: |
    What the simulated user says when asked about their product.
    Written in first person, conversational tone.

# User persona — who is building the product
persona:
  name: "First name"
  role: "Role description"
  style: "Communication style and personality"
  knowledge: "Domain expertise and background"
  answers:
    purpose: |
      Answer to "What problem does this solve?"
    users: |
      Answer to "Who are your users?"
    north_star: |
      Answer to "What's your north star metric?"
    landscape: |
      Answer to "Who else solves this?"
    current_state: |
      Answer to "What's been tried?"
    # Additional answers as needed by the journey

# Project classification
project_type: solo_hobby | solo_product | team_startup | team_enterprise
dogfood: true | false

# Planted failure conditions
planted_failures:
  - type: value-risk | skip-discovery | secret-leak | confidence-inflate | scope-creep | bias-unchecked | regression-ignore
    trigger: skill-name    # Which skill triggers this failure
    description: |
      What the failure looks like and why the framework should catch it.
    # Type-specific fields:
    personas_rejecting: []    # For value-risk
    secret_content: ""        # For secret-leak
    skip_target: ""           # For skip-discovery

# Ordered journey through skills
journey:
  - skill: interview
    rounds: 2              # How many orchestrator rounds this step needs
  - skill: diamond-assess
  - skill: diamond-progress
    expect_blocked: true   # Framework should block this
  - skill: mocked-persona-interview
    planted_failure: value-risk
  - skill: diamond-assess

# What constitutes a passing scenario
success_criteria:
  # Canvas state checks
  - canvas_populated: [purpose.yml, jobs-to-be-done.yml]
  - canvas_evidence_type:
      file: user-needs.yml
      expected: speculation

  # Diamond state checks
  - diamond_created: {scale: L0, phase: discover}
  - diamond_not_advanced: true
  - confidence_decreased: true

  # Gate enforcement checks
  - progression_blocked: {reason: "insufficient evidence"}

  # Decision log checks
  - decision_log_contains: ["stop condition", "value risk"]
  - decision_log_honest: true     # No softening language

  # Hook correctness
  - hooks_no_errors: true

  # Classification
  - classification_correct:
      product_type: software
      project_type: solo_product

# Resource limits
budget:
  max_rounds: 12           # Orchestrator rounds (not agent iterations)
  max_time_seconds: 600    # Total wall clock time
  model_overrides:
    mycelium_agent: sonnet  # Model for the framework agent
    user_simulator: haiku   # Model for the user persona
```

## Success Criteria Types

| Criterion | Description | How Checked |
|-----------|-------------|-------------|
| `canvas_populated` | Named canvas files exist and have content | File size > 200 bytes |
| `canvas_evidence_type` | Canvas file contains expected evidence_type | YAML parse + field check |
| `diamond_created` | Diamond exists at given scale/phase | Parse active.yml |
| `diamond_not_advanced` | Diamond stayed in expected phase | Phase != "complete" |
| `confidence_decreased` | Confidence went down after failure | Compare before/after |
| `progression_blocked` | Diamond-progress was blocked | Decision log or response text |
| `decision_log_contains` | Decision log has specific keywords | Text search |
| `decision_log_honest` | No softening language after failure | Forbidden phrase check |
| `classification_correct` | Product/project type set correctly | Parse active.yml |
| `hooks_no_errors` | No hook script errors during session | Exit code tracking |
| `theory_gates_initialized` | All applicable gates set to pending | Parse active.yml |

## Result JSON Format

```json
{
  "scenario": "sw-cli-solo-value-risk",
  "timestamp": "2026-04-12T10:00:00Z",
  "passed": true,
  "score": 0.91,
  "criteria": {
    "passed": ["canvas_populated", "confidence_decreased", "..."],
    "failed": ["theory_gates_initialized"]
  },
  "rounds_used": 8,
  "time_seconds": 340,
  "token_usage": {
    "mycelium_agent": 45000,
    "user_simulator": 12000,
    "total": 57000
  },
  "observations": [
    {"round": 1, "skill": "interview", "checks": {"...": "..."}}
  ],
  "findings": {
    "bugs": [],
    "gaps": ["theory_gates_status only partially initialized"],
    "mishaps": []
  }
}
```
