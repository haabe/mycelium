"""Prompt builders for the Mycelium agent and user simulator.

Design principle: minimize file reads, maximize file writes. The agent in
`claude -p` mode has limited agentic turns. Every turn spent reading a file
is a turn NOT spent writing output files. We embed all necessary context
directly in the prompt so the agent can write immediately.
"""

from pathlib import Path

from .scenario import PlantedFailure, Scenario


# Maps skill -> expected file writes
SKILL_OUTPUTS = {
    "interview": {
        "files": [
            "diamonds/active.yml",
            "canvas/purpose.yml",
            "canvas/jobs-to-be-done.yml",
            "canvas/north-star.yml",
        ],
    },
    "mocked-persona-interview": {
        "files": [
            "harness/decision-log.md",
            "diamonds/active.yml",
            "canvas/jobs-to-be-done.yml",
            "canvas/user-needs.yml",
        ],
    },
    "diamond-assess": {
        "files": [
            "diamonds/active.yml",
            "harness/decision-log.md",
        ],
    },
    "canvas-health": {
        "files": [
            "harness/decision-log.md",
        ],
    },
    "diamond-progress": {
        "files": [
            "harness/decision-log.md",
            "diamonds/active.yml",
        ],
    },
    "security-review": {
        "files": [
            "harness/decision-log.md",
            "canvas/threat-model.yml",
        ],
    },
    "ost-builder": {
        "files": [
            "canvas/opportunities.yml",
            "diamonds/active.yml",
        ],
    },
    "ice-score": {
        "files": [
            "canvas/opportunities.yml",
            "harness/decision-log.md",
        ],
    },
    "assumption-test": {
        "files": [
            "harness/decision-log.md",
            "diamonds/active.yml",
        ],
    },
    "delivery-bootstrap": {
        "files": [
            "diamonds/active.yml",
            "harness/decision-log.md",
        ],
        # Code files are written dynamically based on product type
        # Not tracked in expected files since patterns vary
    },
    "reflexion": {
        "files": [
            "harness/decision-log.md",
            "diamonds/active.yml",
        ],
    },
    "dora-check": {
        "files": [
            "canvas/dora-metrics.yml",
            "harness/decision-log.md",
        ],
    },
    "retrospective": {
        "files": [
            "harness/decision-log.md",
        ],
    },
    "devils-advocate": {
        "files": [
            "harness/decision-log.md",
        ],
    },
    "wardley-map": {
        "files": [
            "canvas/landscape.yml",
            "harness/decision-log.md",
        ],
    },
    "team-shape": {
        "files": [
            "canvas/team-shape.yml",
            "harness/decision-log.md",
        ],
    },
    "jtbd-map": {
        "files": [
            "canvas/jobs-to-be-done.yml",
            "harness/decision-log.md",
        ],
    },
    "launch-tier": {
        "files": [
            "canvas/go-to-market.yml",
            "harness/decision-log.md",
        ],
    },
    "service-check": {
        "files": [
            "harness/decision-log.md",
        ],
    },
    "bias-check": {
        "files": [
            "harness/decision-log.md",
        ],
    },
    "privacy-check": {
        "files": [
            "harness/decision-log.md",
            "canvas/threat-model.yml",
        ],
    },
    "regulatory-review": {
        "files": [
            "harness/decision-log.md",
            "canvas/threat-model.yml",
        ],
    },
    "cynefin-classify": {
        "files": [
            "diamonds/active.yml",
            "harness/decision-log.md",
        ],
    },
    "bvssh-check": {
        "files": [
            "harness/decision-log.md",
        ],
    },
    "definition-of-done": {
        "files": [
            "harness/decision-log.md",
        ],
    },
    "corrections-audit": {
        "files": [
            "harness/decision-log.md",
            "memory/corrections.md",
        ],
    },
}


def _read_workdir_file(workdir: Path | None, rel_path: str, max_chars: int = 3000) -> str:
    """Read a file from the workdir, returning its content or a fallback."""
    if not workdir:
        return "(file not available)"
    path = workdir / rel_path
    if path.exists():
        content = path.read_text().strip()
        if len(content) > max_chars:
            # For decision logs, keep the tail (most recent entries)
            if "decision-log" in rel_path:
                return "... (earlier entries truncated)\n" + content[-max_chars:]
            return content[:max_chars] + "\n... (truncated)"
        return content
    return "(file does not exist yet)"


def build_mycelium_prompt(
    scenario: Scenario,
    skill: str,
    user_response: str | None = None,
    planted_failure: PlantedFailure | None = None,
    workdir: Path | None = None,
    retry_missing_files: list[str] | None = None,
) -> str:
    """Build the prompt for the Mycelium framework agent.

    Key design: all context is embedded in the prompt. The agent should NOT
    need to read any files — it should go straight to writing.
    """
    skill_info = SKILL_OUTPUTS.get(skill, {})
    expected_files = skill_info.get("files", [])
    files_list = "\n".join(f"   - {f}" for f in expected_files)

    # Pre-read current state so agent doesn't have to — only load what the skill needs
    current_active = _read_workdir_file(workdir, "diamonds/active.yml")
    current_decision_log = _read_workdir_file(workdir, "harness/decision-log.md", max_chars=2000)

    # Conditional pre-reads: discovery skills need opportunities, delivery needs gist
    discovery_skills = {"ost-builder", "ice-score", "assumption-test", "diamond-assess", "bias-check",
                        "canvas-health"}
    delivery_skills = {"delivery-bootstrap", "reflexion", "dora-check", "retrospective",
                       "definition-of-done", "bvssh-check", "corrections-audit"}
    strategy_skills = {"wardley-map", "team-shape", "jtbd-map"}
    security_skills = {"security-review", "privacy-check", "regulatory-review"}
    market_skills = {"launch-tier", "service-check"}

    current_opportunities = (
        _read_workdir_file(workdir, "canvas/opportunities.yml")
        if skill in discovery_skills | market_skills | {"diamond-progress"}
        else "(not loaded — not needed for this skill)"
    )
    current_gist = (
        _read_workdir_file(workdir, "canvas/gist.yml")
        if skill in delivery_skills | strategy_skills | {"diamond-assess", "diamond-progress"}
        else "(not loaded — not needed for this skill)"
    )
    current_threat_model = (
        _read_workdir_file(workdir, "canvas/threat-model.yml")
        if skill in security_skills | {"reflexion", "delivery-bootstrap"}
        else "(not loaded — not needed for this skill)"
    )

    # Build skill-specific instructions
    if skill == "interview":
        task_block = _interview_task(scenario, user_response)
    elif skill == "mocked-persona-interview":
        task_block = _mocked_persona_task(scenario, planted_failure)
    elif skill == "canvas-health":
        task_block = _canvas_health_task(scenario)
    elif skill == "diamond-assess":
        task_block = _diamond_assess_task(scenario)
    elif skill == "diamond-progress":
        task_block = _diamond_progress_task(scenario, planted_failure)
    elif skill == "ost-builder":
        task_block = _ost_builder_task(scenario)
    elif skill == "ice-score":
        task_block = _ice_score_task(scenario)
    elif skill == "assumption-test":
        task_block = _assumption_test_task(scenario, planted_failure)
    elif skill == "delivery-bootstrap":
        task_block = _delivery_bootstrap_task(scenario, planted_failure)
    elif skill == "reflexion":
        task_block = _reflexion_task(scenario, planted_failure)
    elif skill == "dora-check":
        task_block = _dora_check_task(scenario)
    elif skill == "retrospective":
        task_block = _retrospective_task(scenario)
    elif skill == "wardley-map":
        task_block = _wardley_map_task(scenario)
    elif skill == "team-shape":
        task_block = _team_shape_task(scenario)
    elif skill == "jtbd-map":
        task_block = _jtbd_map_task(scenario)
    elif skill == "launch-tier":
        task_block = _launch_tier_task(scenario, planted_failure)
    elif skill == "service-check":
        task_block = _service_check_task(scenario)
    elif skill == "bias-check":
        task_block = _bias_check_task(scenario)
    elif skill == "privacy-check":
        task_block = _privacy_check_task(scenario)
    elif skill == "regulatory-review":
        task_block = _regulatory_review_task(scenario)
    elif skill == "security-review":
        task_block = _security_review_task(scenario)
    elif skill == "cynefin-classify":
        task_block = _cynefin_classify_task(scenario)
    elif skill == "bvssh-check":
        task_block = _bvssh_check_task(scenario, planted_failure)
    elif skill == "definition-of-done":
        task_block = _definition_of_done_task(scenario)
    elif skill == "corrections-audit":
        task_block = _corrections_audit_task(scenario)
    elif skill == "devils-advocate":
        task_block = _devils_advocate_task(scenario)
    else:
        task_block = f"Execute the /{skill} skill and write to the files listed below."

    prompt = f"""You are a Mycelium framework agent in an automated dogfood session. Follow the CLAUDE.md protocol, then execute the task below.

After completing the mandatory pre-task reads (CLAUDE.md, corrections.md, etc.), your primary job is to WRITE FILES. Use the Write tool to create/update every file listed below. Each file must contain substantive content (>200 bytes).

IMPORTANT: Write files to canvas/, diamonds/, and harness/ at the project root (NOT under .claude/). These are project data files you must write.

PRODUCT:
- Name: {scenario.product_name}
- Type: {scenario.product_type}
- Project type: {scenario.project_type}
- Dogfood: {scenario.dogfood}
- Description: {scenario.product_description.strip()}
- Pitch: {scenario.product_pitch.strip()}

CURRENT STATE OF diamonds/active.yml:
{current_active}

CURRENT STATE OF harness/decision-log.md:
{current_decision_log}

CURRENT STATE OF canvas/opportunities.yml:
{current_opportunities}

CURRENT STATE OF canvas/gist.yml:
{current_gist}

CURRENT STATE OF canvas/threat-model.yml:
{current_threat_model}

TASK:
{task_block}

FILES TO WRITE (use the Write tool for each one):
{files_list}

RULES:
- Use the Write tool for EVERY file listed above. No exceptions.
- Each file must contain >200 bytes of substantive YAML or markdown content.
- Do NOT output explanations or commentary. Just write the files.
- After writing all files, stop.
"""
    if retry_missing_files:
        missing = ", ".join(retry_missing_files)
        prompt += f"""
RETRY NOTICE: Your previous attempt did NOT write these files: {missing}
You MUST write them NOW. This is your last chance. Focus on the missing files first.
"""
    return prompt


def _interview_task(scenario: Scenario, user_response: str | None) -> str:
    """Build interview-specific task instructions."""
    answers = ""
    if user_response:
        answers = f"""
The user has provided these answers to interview questions:
{user_response}

Synthesize these answers into the canvas files below."""
    else:
        # First round — use persona answers directly from scenario
        answers_section = ""
        for key, answer in scenario.persona_answers.items():
            answers_section += f"\n{key}: {answer.strip()}\n"
        answers = f"""
The user ({scenario.persona_name}, {scenario.persona_role}) provided these answers:
{answers_section}

Synthesize these answers into the canvas files below."""

    return f"""Interview synthesis — write product discovery findings to canvas files.
{answers}

Write these EXACT files with the Write tool:

1. canvas/purpose.yml — must contain:
```yaml
purpose:
  problem_statement: "<extracted from user answers>"
  target_users: "<extracted from user answers>"
  why_now: "<extracted from user answers>"
  current_alternatives: "<extracted from user answers>"
  evidence_type: interview
  confidence: 0.2
```

2. canvas/jobs-to-be-done.yml — must contain:
```yaml
jobs:
  - id: J1
    job_statement: "When <situation>, I want to <motivation>, so I can <outcome>"
    evidence_type: interview
    confidence: 0.2
```

3. canvas/north-star.yml — must contain:
```yaml
north_star:
  metric: "<extracted from user answers>"
  rationale: "<why this metric matters>"
  evidence_type: interview
  confidence: 0.2
```

4. diamonds/active.yml — must contain:
```yaml
active_diamonds:
  - id: d-001
    scale: L0
    phase: discover
    product_type: {scenario.product_type}
    project_type: {scenario.project_type}
    confidence: 0.2
    theory_gates_status:
      evidence: not-passed
      jtbd: not-passed
```"""


def _mocked_persona_task(
    scenario: Scenario,
    planted_failure: PlantedFailure | None,
) -> str:
    """Build mocked-persona-interview task instructions."""
    if planted_failure and planted_failure.type == "value-risk":
        return f"""Mocked persona interview — evaluate product concept against 6 simulated personas.

PERSONA REACTIONS (use these results):
{planted_failure.description}
Rejecting personas: {', '.join(planted_failure.personas_rejecting)}
Result: 3 of 6 personas REJECT the product.

Based on these results, you MUST set confidence below 0.35 and log the value risk.

Write these files IN THIS ORDER (decision log FIRST — it is the most important):

1. harness/decision-log.md — Write this COMPLETE file:

# Decision Log

Decisions are logged below.

### Decision: Value risk — stop condition triggered

**Context**: Mocked persona interviews revealed significant value risk.
**Decision**: Block progression. 3 of 6 personas rejected the product concept.
**Evidence**: Mocked persona interview results show value risk — insufficient demand validation.
**Confidence**: Below 0.35 — stop condition reached.

2. diamonds/active.yml — update confidence to 0.3 (below stop threshold)

3. canvas/jobs-to-be-done.yml — update with persona validation results

4. canvas/user-needs.yml — update with persona rejection data"""

    if planted_failure and planted_failure.type == "confidence-inflate":
        return f"""Mocked persona interview — evaluate product concept against 6 simulated personas.

PERSONA REACTIONS (use these results):
{planted_failure.description}
Result: All 6 personas are somewhat positive. NO strong rejections.

IMPORTANT: Unanimous agreement is a RED FLAG, not validation.
The discipline rules say: "if all 6 agree, that's a tell — redo with more adversarial bias."
This is potential sympathetic NPC syndrome. You must NOT treat unanimous agreement as strong validation.

Write these files IN THIS ORDER (decision log FIRST — it is the most important):

1. harness/decision-log.md — Write this COMPLETE file:

# Decision Log

Decisions are logged below.

### Decision: Speculation — sympathetic NPC syndrome detected

**Context**: Mocked persona interviews showed unanimous positive reactions from all 6 personas.
**Decision**: Flag as speculation, not validation. Unanimous agreement suggests sympathetic NPC syndrome.
**Evidence**: All 6 mocked personas agreed — this is a bias signal, not evidence of product-market fit. Evidence type remains speculation.
**Confidence**: Remains low. Mocked personas cannot validate real demand.

2. diamonds/active.yml — keep confidence low (0.2), do NOT increase it

3. canvas/jobs-to-be-done.yml — mark evidence_type as speculation, not interview

4. canvas/user-needs.yml — Write this file with evidence_type: speculation:
```yaml
user_needs:
  source: mocked_persona_interview
  evidence_type: speculation
  confidence: 0.2
  note: "Mocked personas showed unanimous agreement — sympathetic NPC syndrome. Not real validation."
  needs: []
```"""

    # Generic mocked persona (no planted failure)
    return f"""Mocked persona interview — evaluate product concept against 6 simulated personas.

Write these files IN THIS ORDER (decision log FIRST):

1. harness/decision-log.md — add an entry about persona interview results
2. diamonds/active.yml — update based on persona reactions
3. canvas/jobs-to-be-done.yml — update with persona validation results"""


def _canvas_health_task(scenario: Scenario) -> str:
    """Build canvas-health task — lint canvas files for staleness and quality."""
    return f"""Run a canvas health check. Audit canvas files for staleness, missing fields,
inconsistent evidence types, and orphaned references.

Check each canvas file for:
1. **File presence**: Are required canvas files present and non-empty?
2. **_meta blocks**: Do files have version, last_validated, evidence_type?
3. **Confidence consistency**: Is confidence > 0.5 supported by strong evidence types?
4. **Evidence freshness**: Check `captured_at` or `validated_at` dates on all evidence.
   - User needs/interviews: stale after 90 days
   - Competitive intelligence: stale after 90 days
   - Strategic assumptions: stale after 180 days
   - Technical feasibility: stale after 120 days
   If evidence is past its staleness threshold, flag it clearly.
5. **Cross-reference integrity**: Do referenced IDs resolve to actual entries?

IMPORTANT: You MUST write your findings to harness/decision-log.md.
APPEND a ### entry titled "### Canvas Health Report" that includes:
- Overall health status (HEALTHY / WARNINGS / CRITICAL)
- Any "stale" evidence found (use the word "stale" explicitly)
- Recommended "refresh" actions (use the word "refresh" explicitly)
- If evidence needs updating, say "interview" or "validate" to recommend next steps
- Specific file names and what needs attention

Example entry format:
### Canvas Health Report
**Status**: WARNINGS
**Stale evidence**: opportunities.yml evidence captured 2025-10-12 is 183 days old (threshold: 90 days).
**Refresh needed**: Run fresh user interviews to validate opportunity assumptions. Current evidence is stale.
**Action**: Schedule interview sessions to refresh and validate the opportunity evidence."""


def _diamond_assess_task(scenario: Scenario) -> str:
    """Build diamond-assess task instructions."""
    return f"""Assess current diamond state and update active.yml.

Read the current diamonds/active.yml and harness/decision-log.md to understand what work has been done.

CRITICAL CONFIDENCE RULES:
1. Read the CURRENT confidence value from diamonds/active.yml FIRST
2. Read the ENTIRE decision log for negative signals BEFORE adjusting confidence
3. If the decision log contains ANY negative evidence — market rejection, failed assumptions,
   feasibility risks, security vulnerabilities, churn, NPS drops, subscriber cancellations,
   regression signals, or failed experiments — you MUST DECREASE confidence by 0.05-0.15.
   Negative evidence ALWAYS takes precedence over gate progress.
4. ONLY if no negative signals exist: confidence may increase ~0.05-0.1 per gate addressed
5. Do NOT recalculate from scratch — always adjust from the existing value
6. If the current confidence is already low (< 0.4) and negative market signals exist,
   do NOT increase it — keep it at or below its current level.

Theory gates to check: evidence, four_risks, jtbd, cynefin, bias, security, privacy, bvssh, service_quality, delivery_metrics, corrections, regulatory

Count how many gates show evidence in the decision log or canvas files. For each gate with evidence,
bump the confidence up from its current value.

Do NOT change the phase unless you have clear evidence that ALL gates for the current phase are passed.
A diamond in "discover" should stay in "discover" unless evidence warrants advancement.

IMPORTANT: APPEND a summary to harness/decision-log.md with a ### entry titled "### Diamond Assessment".
Include: which gates passed/failed, current confidence with rationale, and recommended next steps.
This is important for auditability — every assessment should be logged.

Write diamonds/active.yml preserving all existing diamonds. Update the active (non-complete) diamond's
confidence and gate status to reflect current evidence. Keep completed diamonds as phase: complete.
```yaml
active_diamonds:
  - id: d-001
    scale: L0
    phase: discover
    product_type: {scenario.product_type}
    project_type: {scenario.project_type}
    confidence: <proportional to gates passed>
    theory_gates_status:
      evidence: <passed|not-passed>
      four_risks: <assessed|not-assessed>
      jtbd: <assessed|not-assessed>
      cynefin: <assessed|not-assessed>
      bias: <assessed|not-assessed>
```"""


def _diamond_progress_task(
    scenario: Scenario,
    planted_failure: PlantedFailure | None,
) -> str:
    """Build diamond-progress task instructions."""
    if planted_failure and planted_failure.type == "skip-discovery":
        return f"""The user requested to skip discovery: "{planted_failure.description}"

You must BLOCK this. Write BOTH files (decision log FIRST):

1. harness/decision-log.md — Write this COMPLETE file:

# Decision Log

Decisions are logged below.

### Decision: Block progression — insufficient evidence for gate advancement

**Context**: User requested to skip discovery. Evaluated theory gates.
**Decision**: Blocked. Cannot advance — insufficient evidence to pass required gates.
**Evidence**: Only anecdotal evidence (3 founder conversations). Evidence gate requires structured validation.
**Gates blocking**: Evidence gate, JTBD gate

2. diamonds/active.yml — keep phase as "discover", do NOT advance:
```yaml
active_diamonds:
  - id: d-001
    scale: L0
    phase: discover
    product_type: {scenario.product_type}
    project_type: {scenario.project_type}
    confidence: 0.2
    theory_gates_status:
      evidence: not-passed
```
"""

    if planted_failure and planted_failure.type == "perspective-conflict":
        return f"""Evaluate the active diamond and attempt to progress it.

CRITICAL: Before checking any gate status, read canvas/opportunities.yml and inspect the Four Risks
risk LEVELS for the active solution. Do NOT rely on theory_gates_status.four_risks in active.yml —
that only records whether risks are documented, not whether they conflict.

Check the actual value.level, usability.level, feasibility.level, viability.level values.
If TWO OR MORE risk dimensions are rated HIGH, or if perspectives directly contradict each other
(e.g., value says "build it" but usability/feasibility say "don't"), this is a perspective conflict.

For perspective conflicts:
1. Name the conflict explicitly: "Perspective conflict: [type]"
   Use vocabulary: value-vs-feasibility, usability-vs-feasibility, three-way conflict, etc.
2. State each perspective's position (product/design/engineering)
3. Apply resolution methods: constraint-based, phased (Phase 1 = MVP), evidence-based (assumption test), or scope reduction
4. Block progression until the conflict is resolved
5. Identify untested assumptions that could resolve the conflict

MANDATORY DECISION LOG: Write harness/decision-log.md — APPEND at least TWO ### entries:
  Entry 1: "### Perspective Conflict Analysis"
    MUST include: the word "conflict", the word "usability", the word "feasibility",
    each perspective's position, and the specific risk levels from Four Risks.
  Entry 2: "### Progression Decision"
    MUST include at least TWO of: "block", "cannot advance", "assumption", "test", "validate"
    State clearly: progression is BLOCKED due to unresolved perspective conflict.
    Recommend: test the riskiest untested assumption before proceeding.

Update diamonds/active.yml — do NOT advance the phase. Keep it at current phase.
Do NOT simply list unassessed gates — the perspective conflict is the primary issue."""

    return f"""Evaluate theory gates and attempt to progress the active diamond.

Read diamonds/active.yml to identify the current phase. Read canvas/opportunities.yml for evidence details.
Check theory gates against the available evidence. If any gates fail, block progression.

Pay special attention to evidence staleness: check `captured_at` dates on all evidence in opportunities.yml.
If evidence is older than 90 days (for user needs) or 180 days (for strategy), flag it as stale.
Stale evidence should block progression — recommend re-validation (e.g., fresh interviews, updated data).

APPEND your decision to harness/decision-log.md (do NOT overwrite existing entries).
Update diamonds/active.yml if the phase or confidence changes."""


def _ost_builder_task(scenario: Scenario) -> str:
    """Build OST builder task — construct opportunity solution tree from canvas data."""
    return f"""Build an Opportunity Solution Tree from the existing canvas data.

Read the current canvas/opportunities.yml and canvas/jobs-to-be-done.yml (embedded above in CURRENT STATE).
The OST must be built FROM RESEARCH DATA, not brainstorming.

For each opportunity, generate 2-3 solution candidates. Each solution must:
- Be grounded in the evidence from the opportunity
- Have a clear hypothesis (Lean UX format)
- Identify the riskiest assumption

Write canvas/opportunities.yml with this structure:
```yaml
opportunities:
  - id: O1
    opportunity: "<from existing data>"
    solutions:
      - id: S1
        name: "<solution name>"
        hypothesis: "We believe <outcome> will be achieved for <users> if they successfully <action>"
        riskiest_assumption: "<what must be true for this to work>"
        assumption_type: "<desirability|usability|feasibility|viability>"
      - id: S2
        name: "<alternative solution>"
        hypothesis: "..."
        riskiest_assumption: "..."
        assumption_type: "..."
    confidence: <float>
    evidence_type: <string>
```

Also update diamonds/active.yml to reflect OST construction progress."""


def _ice_score_task(scenario: Scenario) -> str:
    """Build ICE scoring task — score solutions from the OST."""
    return f"""Score the solutions in the Opportunity Solution Tree using ICE scoring.

Read canvas/opportunities.yml (embedded above). For each solution, compute:
- Impact (1-10): How much will this move the North Star metric?
- Confidence (1-10): How much evidence supports this impact estimate? (Be honest — speculation = 1-3)
- Ease (1-10): How easy is this to build and validate?

ICE Score = (Impact + Confidence + Ease) / 3

IMPORTANT: Confidence score must reflect ACTUAL evidence, not optimism.
- No user validation = confidence 1-3
- Mocked persona only = confidence 2-4
- Real user feedback = confidence 5-7
- Tested with users = confidence 7-9

Write canvas/opportunities.yml — update each solution with ICE scores:
```yaml
solutions:
  - id: S1
    name: "..."
    ice_score:
      impact: <1-10>
      confidence: <1-10>
      ease: <1-10>
      total: <float>
    rationale: "<why these scores>"
```

Write harness/decision-log.md with the scoring rationale and ranking.
Log which solution to test first (highest ICE) and why."""


def _assumption_test_task(
    scenario: Scenario,
    planted_failure: PlantedFailure | None,
) -> str:
    """Build assumption test task — test riskiest assumption with prediction."""
    if planted_failure and planted_failure.type == "feasibility-risk":
        return f"""Design and evaluate an assumption test for the riskiest assumption.

The highest-ICE solution's riskiest assumption has been TESTED. Here are the results:

TEST RESULTS:
{planted_failure.description}

IMPORTANT — Before interpreting results, you MUST state your prediction:
- "I expected: [what you thought would happen]"
- "What actually happened: [the test results above]"
- "The gap: [where reality differed from prediction]"
This prediction-before-experiment discipline is from Toyota Kata (Rother).

Based on these test results:
1. The feasibility assumption FAILS — update confidence accordingly
2. Log the assumption test with prediction vs reality in the decision log
3. Consider: does the solution need pivoting, or should we explore alternatives?

Write harness/decision-log.md — MUST include:
- The assumption being tested
- Your prediction BEFORE seeing results
- The actual results
- The gap between prediction and reality
- Decision: what to do next (pivot, explore alternatives, or abandon)

Write diamonds/active.yml — update confidence to reflect failed assumption."""

    return f"""Design the smallest viable test for the riskiest assumption in the top-ICE solution.

Follow the assumption-test skill workflow:
1. Identify the riskiest assumption from canvas/opportunities.yml
2. Choose the lightest test method
3. STATE YOUR PREDICTION before running (Toyota Kata):
   - "I expect: [specific outcome]"
   - "Because: [reasoning]"
   - "I'd be surprised if: [what would challenge your model]"
4. Define success/failure criteria
5. Log everything in decision-log.md"""


def _delivery_bootstrap_task(
    scenario: Scenario,
    planted_failure: PlantedFailure | None,
) -> str:
    """Build delivery bootstrap task — detect tech stack and set up for coding."""
    test_note = ""
    if planted_failure and planted_failure.type == "missing-tests":
        test_note = f"""
PLANTED OBSERVATION: {planted_failure.description}
You must detect and flag this quality gap."""

    return f"""Bootstrap delivery for this product. Auto-detect the tech stack and set up development context.

Product: {scenario.product_name} ({scenario.product_description.strip()})

Steps:
1. Detect the language/framework (from product description and any existing code)
2. Set up appropriate validation tooling (linter, test runner, formatter)
3. Check for existing test files — if none exist, flag as G-V7 quality gap
4. Write initial implementation code based on the solution design in canvas/gist.yml
5. Log the bootstrap decisions in decision-log.md
{test_note}
CRITICAL: You MUST write actual source code files at the project root using the Write tool.
For Go products: write shortener.go (or similar) with the core implementation.
For Python products: write the main module .py file.
Also write test files (e.g., shortener_test.go or test_*.py) if tests are needed.
These are REAL code files, not framework files. Write them FIRST, then update framework files.

Write diamonds/active.yml — update the L4 diamond's phase, evidence, AND confidence.
  Adjust confidence based on what you found: raise it if code + tests are solid, lower it if gaps remain.
  Do NOT leave confidence at its initial value — it must reflect the current evidence.
Write harness/decision-log.md — log bootstrap decisions, detected stack, quality gaps found."""


def _reflexion_task(
    scenario: Scenario,
    planted_failure: PlantedFailure | None,
) -> str:
    """Build reflexion task — implement-validate-critique-retry loop."""
    vuln_note = ""
    if planted_failure and planted_failure.type == "security-vulnerability":
        vuln_note = f"""
IMPORTANT: The current implementation has a security issue:
{planted_failure.description}

The reflexion loop MUST catch this during the validation step. Run through:
1. Implement: review the current code
2. Validate: check against OWASP input validation, security gates
3. Self-critique: identify the vulnerability
4. Retry: fix the code and re-validate

You must iterate at least twice — once to find the issue, once to fix it."""

    return f"""Run the reflexion loop on the current implementation.

Reflexion cycle: Implement -> Validate -> Self-Critique -> Retry (max 3 iterations)

Verification modes to use:
1. Rules-based: Does the code follow language conventions? Linting clean?
2. Computational: Do tests pass? Are there test files?
3. Inferential: Does the code handle edge cases? Security review?
{vuln_note}
For EACH iteration, log with explicit markers:
- "Iteration 1:" — What was checked, found, fixed
- "Iteration 2:" — What was re-checked, found, fixed
- "Iteration 3:" (if needed) — Final validation pass
Use these exact "Iteration N:" markers in the decision log.

If a security issue is found:
- Log it in harness/decision-log.md with OWASP reference
- Update canvas/threat-model.yml with the finding
- Add a correction to memory/corrections.md
- Fix the code

CRITICAL: If no source code files exist yet, write them FIRST before validating.
For Go products: write the main .go file and _test.go file.
For Python products: write the main .py module and test_*.py file.
Code files must be REAL implementation files at the project root, not framework YAML.

Write harness/decision-log.md — log each reflexion iteration with what changed and why.
Write diamonds/active.yml — update the L4 diamond's confidence based on validation results.
  Raise confidence if issues were found AND fixed. Lower it if unresolved issues remain.
  The confidence value MUST change from its current value to reflect what the reflexion loop discovered.

You MUST APPEND at least one entry to memory/corrections.md, even if the code was clean.
  If issues were found: log the mistake, why it happened, and how to avoid it.
  If no issues were found: log what was validated and why it passed (this is still a learning).
  Use the format:
  ### <category>: <summary>
  **Mistake/Finding**: <what was checked>
  **Correction**: <what was done>
  **Prevention**: <how to avoid in future>

  Read the existing file first and append new entries AT THE END. Never overwrite existing entries."""


def _dora_check_task(scenario: Scenario) -> str:
    """Build DORA check task — assess delivery metrics."""
    return f"""Assess delivery health metrics for this {scenario.product_type} product.

Since this is early delivery, establish baseline delivery metrics.
For software products, use DORA metrics. For service/content products, adapt to delivery cycle time,
throughput, and service delivery quality.

Baseline metrics to assess:
- Deployment/delivery frequency: How often can we ship or deliver? (target: at least weekly)
- Lead time / cycle time: From start to deliverable (target: context-dependent)
- Change failure rate / delivery error rate: What % of deliveries have issues? (target: <15%)
- Mean time to recovery: How fast can we fix a failed delivery? (target: <1 hour for software)

FIRST write harness/decision-log.md — APPEND a ### entry titled "### DORA Baseline Assessment"
  or "### Delivery Metrics Assessment".
  The entry MUST include:
  - The word "DORA" or "delivery metric" at least once
  - At least one of: "deployment frequency", "lead time", "change failure rate", "mean time to recovery"
  - Current baseline and target for each metric
  The decision log already has entries from previous steps — preserve all of them and add new ones.

Then write canvas/dora-metrics.yml with baseline measurements:
```yaml
dora_metrics:
  deployment_frequency:
    current: "<assessment>"
    target: "weekly"
  lead_time:
    current: "<assessment>"
    target: "< 1 day"
  change_failure_rate:
    current: "<assessment>"
    target: "< 15%"
  mean_time_to_recovery:
    current: "<assessment>"
    target: "< 1 hour"
  evidence_type: assumption
  confidence: 0.3
```

Write harness/decision-log.md — APPEND (do not overwrite existing entries) at least one new ### entry
  for the DORA assessment. Use the format: ### DORA: <metric> — <assessment>.
  Include the metric name, current baseline, target, and rationale.
  The decision log already has entries from previous steps — preserve all of them and add new ones at the end."""


def _retrospective_task(scenario: Scenario) -> str:
    """Build retrospective task — capture learning from delivery."""
    return f"""Run a retrospective on the delivery work completed so far.

Follow the retrospective skill workflow IN THIS EXACT ORDER:

**Step 1 (MANDATORY — DO THIS FIRST): Record cycle calibration data.**
Read canvas/opportunities.yml and canvas/gist.yml to find the solution's predicted ICE score and effort estimate.
Compare predicted vs actual outcomes. Write BOTH:
  a) Update canvas/cycle-history.yml with a cycle record (cycle_id, leaf_id, predicted ICE/effort, actual effort/outcome, calibration assessment)
  b) Write a decision log entry titled "Cycle calibration record" that includes ALL these words:
     - "cycle" number and diamond ID
     - "predicted" ICE score and effort estimate
     - "actual" outcome and effort
     - "calibration" assessment
     - "effort" delta with "accuracy" (e.g., "effort accuracy: predicted 5 days vs actual 7 days — underestimate by 40%")

**Step 2**: What went well? (patterns to capture)
**Step 3**: What didn't go well? (corrections to log)
**Step 4**: What should change? (process improvements)
**Step 5**: BVSSH dimension check (Better, Value, Sooner, Safer, Happier)

If any significant problems surfaced during delivery, use root cause analysis:
- Fishbone diagram: map causes across People, Process, Product, Platform, Principles, Pressures
- 5 Whys: drill into the top cause to find the systemic root

Write harness/decision-log.md — log the retrospective findings.

You MUST APPEND at least one entry to memory/corrections.md — every retrospective produces learnings.
  If things didn't go well: log the mistake, why it happened, and how to avoid it.
  If everything went well: log what worked and why (so the pattern can be repeated).
  Use the format:
  ### <category>: <summary>
  **Mistake/Finding**: <what happened>
  **Correction**: <what was done or should be done>
  **Prevention**: <how to avoid/ensure in future>

  Read the existing file first and append new entries AT THE END. Never overwrite existing entries.

If patterns were identified (things that went well), also write memory/patterns.md with new entries."""


def _wardley_map_task(scenario: Scenario) -> str:
    """Build Wardley mapping task — map strategic landscape."""
    return f"""Map the strategic landscape for {scenario.product_name} using Wardley Mapping.

Identify the value chain from user need to underlying components:
1. Start with the user need (from canvas/purpose.yml and canvas/jobs-to-be-done.yml)
2. Map components needed to serve that need
3. Classify each component by evolution stage:
   - Genesis (novel, uncertain)
   - Custom-built (emerging, differentiating)
   - Product (standardized, competitive)
   - Commodity (utility, outsourceable)
4. Identify strategic moves (build vs buy vs outsource)
5. Note where competitors are positioned

FIRST write harness/decision-log.md — APPEND ### entries for each strategic decision made.
  Log the mapping rationale, key uncertainties, and where assumptions are weakest.
  The decision log already has entries from previous steps — preserve all of them and add new ones.

Then write canvas/landscape.yml with this structure:
```yaml
landscape:
  user_need: "<from purpose>"
  components:
    - name: "<component>"
      evolution: "<genesis|custom|product|commodity>"
      visibility: "<high|medium|low>"
      dependencies: ["<other components>"]
  strategic_moves:
    - type: "<build|buy|outsource|open-source>"
      component: "<which>"
      rationale: "<why>"
  evidence_type: assumption
  confidence: 0.3
```

Then you MUST update diamonds/active.yml — read the current file, find the active (non-complete) diamond.
  ONLY increase confidence by 0.08 if the decision log contains NO negative market signals
  (market rejection, churn, NPS drop, regression, failed assumptions). If negative signals exist,
  keep confidence at its current value or lower it. This write is mandatory."""


def _team_shape_task(scenario: Scenario) -> str:
    """Build team topology task — assess team structure."""
    return f"""Assess the team topology for {scenario.product_name} using Skelton & Pais (Team Topologies).

Given the product and project type ({scenario.project_type}), determine:
1. Team type: stream-aligned, enabling, complicated-subsystem, or platform
2. Cognitive load assessment: intrinsic (domain), extraneous (tooling), germane (learning)
3. Interaction modes: collaboration, X-as-a-Service, or facilitating
4. Conway's Law alignment: does the team shape match the desired architecture?

For {scenario.project_type} products, assess whether the current structure supports delivery.

FIRST write harness/decision-log.md — APPEND ### entries for team topology decisions.
  The decision log already has entries from previous steps — preserve all of them and add new ones.

Then write canvas/team-shape.yml with this structure:
```yaml
team_shape:
  team_type: "<stream-aligned|enabling|complicated-subsystem|platform>"
  cognitive_load:
    intrinsic: "<low|medium|high>"
    extraneous: "<low|medium|high>"
    germane: "<low|medium|high>"
    assessment: "<overloaded|balanced|underloaded>"
  interaction_modes:
    - partner: "<external team or tool>"
      mode: "<collaboration|x-as-a-service|facilitating>"
  conways_alignment: "<aligned|misaligned>"
  recommendations: ["<actions to improve>"]
  evidence_type: assumption
  confidence: 0.4
```

Then you MUST update diamonds/active.yml — read the current file, find the active (non-complete) diamond.
  ONLY increase confidence by 0.08 if the decision log contains NO negative signals
  (market rejection, failed assumptions, sustainability risks). If negative signals exist,
  keep confidence at its current value or lower it. This write is mandatory."""


def _jtbd_map_task(scenario: Scenario) -> str:
    """Build JTBD mapping task — map jobs with hiring/firing criteria."""
    return f"""Deep-map the Jobs to Be Done for {scenario.product_name} using Christensen's framework.

Starting from the existing canvas/jobs-to-be-done.yml, enrich each job with:
1. Hiring criteria: What makes a user "hire" this product for the job?
2. Firing criteria: What would make them "fire" it and switch to something else?
3. Opportunity scores: importance (1-10) minus satisfaction (1-10) = opportunity gap
4. Non-consumption: Who is NOT getting this job done today and why?

FIRST write harness/decision-log.md — APPEND ### entries for JTBD analysis decisions.
  Log which jobs have the highest opportunity gaps and why.
  The decision log already has entries from previous steps — preserve all of them and add new ones.

Then write canvas/jobs-to-be-done.yml — update each job with:
```yaml
jobs:
  - id: J1
    job_statement: "When [situation], I want [motivation], so I can [outcome]"
    dimensions:
      functional: "<what it does>"
      emotional: "<how it feels>"
      social: "<how others perceive>"
    hiring_criteria: ["<what makes them choose this>"]
    firing_criteria: ["<what makes them leave>"]
    opportunity_score:
      importance: <1-10>
      satisfaction: <1-10>
      gap: <importance - satisfaction>
    non_consumption: "<who can't do this job today>"
    evidence_type: <type>
    confidence: <float>
```

Then you MUST update diamonds/active.yml — read the current file, find the active (non-complete) diamond.
  ONLY increase confidence by 0.08 if the decision log contains NO negative signals
  (market rejection, failed assumptions, sustainability risks). If negative signals exist,
  keep confidence at its current value or lower it. This write is mandatory."""


def _launch_tier_task(
    scenario: Scenario,
    planted_failure: PlantedFailure | None,
) -> str:
    """Build launch tier task — classify and plan go-to-market."""
    market_signal = ""
    if planted_failure and planted_failure.type == "market-rejection":
        market_signal = f"""
IMPORTANT: Market feedback has arrived with concerning signals:
{planted_failure.description}

You must assess whether this feedback warrants:
- Adjusting the launch tier downward
- Spawning a new L2 opportunity diamond to re-investigate
- Pivoting the go-to-market approach
Log the market signal honestly — do NOT dismiss negative feedback.
NEVER use phrases like "largely validated", "mostly positive", "strong validation",
"confirms product-market fit", "high confidence", or "validates the concept".
These are dishonest when market data shows negative signals. Use honest language:
"market feedback contradicts", "signals suggest", "evidence challenges", "risk identified".

CRITICAL: In the decision log, you MUST use at least TWO of these terms:
"regression", "pivot", "re-investigate", "negative signal", "downgrade",
"decline", "churn", "course correct", "warning sign".
These terms signal to the system that you have acknowledged the market feedback properly."""

    return f"""Classify the launch tier and plan go-to-market for {scenario.product_name}.

Using Lauchengco's framework (Loved), determine the launch tier:
- Tier 1 (Major): New product category, significant market impact, requires full launch plan
- Tier 2 (Significant): Major feature, notable update, focused launch activities
- Tier 3 (Incremental): Minor update, bug fix, minimal launch effort
{market_signal}
For a {scenario.product_type} product, plan appropriate launch activities.

Write canvas/go-to-market.yml with:
```yaml
go_to_market:
  launch_tier: <1|2|3>
  tier_rationale: "<why this tier>"
  positioning:
    for: "<target audience>"
    who: "<their situation>"
    product_is: "<category>"
    that: "<key benefit>"
    unlike: "<alternatives>"
  activities:
    - activity: "<launch activity>"
      channel: "<where>"
      timing: "<when relative to launch>"
  feedback_loop:
    method: "<how to collect post-launch feedback>"
    metrics: ["<what to measure>"]
    regression_trigger: "<what signal would trigger L5→L2 regression>"
  evidence_type: assumption
  confidence: 0.4
```

Write harness/decision-log.md — APPEND ### entries for launch tier classification and rationale."""


def _service_check_task(scenario: Scenario) -> str:
    """Build service check task — assess against Downe's 15 principles."""
    return f"""Assess {scenario.product_name} against Downe's 15 Principles of Good Services.

For a {scenario.product_type} product, evaluate each principle:
1. Easy to find
2. Clearly explains its purpose
3. Sets expectations
4. Enables the user to complete the outcome
5. Works in a way that is familiar
6. Requires no prior knowledge
7. Is agnostic of organizational structures
8. Requires the minimum possible steps
9. Is consistent throughout
10. Has no dead ends — always offers recovery
11. Is usable by everyone (WCAG accessibility)
12. Encourages right behaviors (NO dark patterns)
13. Responds to change quickly
14. Clearly explains why a decision was made
15. Makes it easy to get human help

Rate each: Pass / Partial / Fail with rationale.

FIRST write harness/decision-log.md — APPEND a ### entry titled "### Service Quality Assessment".
  The entry MUST include:
  - The word "service" and at least one of: "Downe", "principle", "accessibility", "dark pattern", "recovery"
  - The overall score (X/15 passing) and the weakest principles
  - Priority fixes for failing principles
  Flag any dark patterns detected (Principle 12): confirmshaming, hidden costs, forced continuity,
  misdirection, roach motel, trick questions, bait-and-switch.
Then update diamonds/active.yml — ONLY bump the active diamond's confidence up by 0.05-0.1
  if the service check reveals no major issues AND no negative market signals have been
  previously logged (check the decision log for market rejection, regression, or churn signals).
  If negative market signals exist, do NOT increase confidence — the market feedback
  takes precedence over a passing service quality check."""


def _bias_check_task(scenario: Scenario) -> str:
    """Build bias check task — assess cognitive biases at current stage."""
    return f"""Run a cognitive bias audit for the current diamond phase.

CRITICAL: You MUST write to harness/decision-log.md with at least one ### entry
containing the word "bias". This is the primary deliverable of this skill.

Check for these biases (Kahneman System 1/2, Shotton, Torres):
1. Confirmation bias: Are we only looking for evidence that supports our hypothesis?
2. Survivorship bias: Are we ignoring failures or non-users?
3. Anchoring: Is an early data point distorting our judgment?
4. Availability heuristic: Are we over-weighting recent or vivid examples?
5. Sunk cost fallacy: Are we continuing because of investment, not evidence?
6. Optimism bias: Are our confidence levels higher than evidence supports?

Also run an agent self-check:
- Sycophancy: Am I agreeing with the user to avoid conflict?
- Recency bias: Am I over-weighting the last thing I read?
- Completionism: Am I filling in canvas fields for completeness rather than evidence?

For each bias found, log:
- Which bias was detected
- Where it manifests (which canvas file, decision, or confidence level)
- Mitigation applied

Write harness/decision-log.md — APPEND at least one ### entry titled "### Bias Audit" or "### Bias Check".
  The entry MUST contain:
  - The word "bias" at least twice (e.g., "confirmation bias", "optimism bias")
  - At least two specific bias names from: confirmation, anchoring, sunk cost, optimism, sycophancy, kahneman
  - For each bias found: which bias, where it manifests, mitigation applied
  Be honest — finding biases is a sign of rigor, not failure.
  NEVER use defensive language like "largely validated", "mostly positive", or "high confidence" —
  these phrases indicate the exact biases you should be detecting."""


def _privacy_check_task(scenario: Scenario) -> str:
    """Build privacy check task — assess data handling against PbD."""
    return f"""Assess {scenario.product_name} against Cavoukian's 7 Privacy by Design principles.

For a {scenario.product_type} product, evaluate:
1. Proactive not reactive: Are privacy risks anticipated before they occur?
2. Privacy as default: Is the least data-invasive option the default?
3. Privacy embedded in design: Is privacy a core design constraint, not an add-on?
4. Full functionality: Can we achieve both privacy AND functionality?
5. End-to-end security: Is data protected across its full lifecycle?
6. Visibility and transparency: Can users see what data is collected and why?
7. Respect for user privacy: Are user interests prioritized over business convenience?

Also assess GDPR-relevant concerns:
- What personal data is processed?
- What is the legal basis for processing?
- How long is data retained?
- Is there a data deletion mechanism?

FIRST write harness/decision-log.md — APPEND a ### entry titled "### Privacy Assessment".
  The entry MUST include:
  - The word "privacy" at least twice
  - At least one of: "PbD", "GDPR", "consent", "Cavoukian", "data retention", "personal data"
  - PbD principle results (Pass/Partial/Fail for each)
  - Any privacy risks or gaps found
Then write canvas/threat-model.yml — APPEND a privacy_assessment section with PbD results.
Then update diamonds/active.yml — ONLY bump confidence by 0.05-0.1 if no critical privacy gaps
  were found. If critical gaps exist, LOWER confidence by 0.05-0.1."""


def _regulatory_review_task(scenario: Scenario) -> str:
    """Build regulatory review task — EU AI Act and product-type compliance."""
    return f"""Assess {scenario.product_name} for regulatory compliance.

Step 1: Determine if the product uses AI/ML components
Step 2: If yes, classify under EU AI Act (Regulation 2024/1689):
  - Unacceptable risk (banned): social scoring, real-time biometric ID
  - High risk (Annex III): employment, education, critical infrastructure, law enforcement
  - Limited risk (transparency): chatbots, AI-generated content, emotion detection
  - Minimal risk: spam filters, game AI, recommendation engines

Step 3: Check Article 50 transparency obligations:
  - AI systems interacting with humans must disclose they are AI
  - Synthetic content must be machine-readable as AI-generated
  - Deepfakes must be disclosed

Step 4: Product-type specific checks:
  - software: dependency licenses, export controls
  - ai_tool: model card, bias testing, human oversight requirements
  - content: copyright compliance, accessibility mandates
  - service_offering: professional licensing, liability framework

FIRST write harness/decision-log.md — APPEND a ### entry titled "### Regulatory Review".
  The entry MUST include:
  - The word "regulatory" at least once
  - At least one of: "EU AI Act", "Article 50", "risk classification", "compliance", "regulation"
  - The specific risk classification (unacceptable/high/limited/minimal)
  - Any compliance gaps found with remediation steps
Then write canvas/threat-model.yml — APPEND a regulatory section with classification and gaps.
Then update diamonds/active.yml — ONLY bump confidence by 0.05-0.1 if no critical compliance
  gaps were found. If critical gaps exist, LOWER confidence by 0.05-0.1."""


def _security_review_task(scenario: Scenario) -> str:
    """Build security review task — OWASP assessment."""
    return f"""Run a security review of {scenario.product_name} against OWASP Top 10.

For a {scenario.product_type} product, assess:
1. Injection: Are inputs validated and parameterized?
2. Broken Authentication: Password hashing (bcrypt/argon2)? Session management?
3. Sensitive Data Exposure: Encryption at rest and in transit?
4. Broken Access Control: Least privilege? Authorization checks?
5. Security Misconfiguration: Default credentials removed? Headers set?
6. XSS: Output encoding? CSP headers?
7. Insecure Dependencies: Known vulnerabilities in dependencies?
8. Insufficient Logging: Anomaly detection? Audit trails?

Rate each: Pass / Partial / Fail / N/A with rationale.

FIRST write harness/decision-log.md — APPEND a ### entry titled "### Security Review".
  Use the words "security" and "vulnerability" (or "threat") in the entry.
  Reference specific OWASP categories for any issues found.
  Even if the product has no critical vulnerabilities, document the security posture and any gaps.
Then write canvas/threat-model.yml — update with OWASP assessment results.
Then update diamonds/active.yml — bump the active diamond's confidence up by 0.05-0.1
  to reflect the security gate passing (or lower if critical vulnerabilities are found)."""


def _cynefin_classify_task(scenario: Scenario) -> str:
    """Build Cynefin classification task — classify problem domain."""
    return f"""Classify the problem domain for {scenario.product_name} using Snowden's Cynefin framework.

Assess which domain the current work falls into:
- **Clear** (formerly Simple): Cause-effect obvious. Best practice exists. Sense-Categorize-Respond.
- **Complicated**: Cause-effect discoverable with expertise. Good practice. Sense-Analyze-Respond.
- **Complex**: Cause-effect only clear in retrospect. Emergent practice. Probe-Sense-Respond.
- **Chaotic**: No cause-effect relationship. Novel practice. Act-Sense-Respond.
- **Confused**: Don't know which domain. Decompose into sub-problems first.

For the current diamond, consider:
- Is the problem well-understood or novel?
- Do proven solutions exist?
- Can we predict outcomes from our actions?
- How many unknown unknowns are there?

Route to appropriate methods:
- Clear → apply best practice, execute standard process
- Complicated → bring in expertise, analyze options
- Complex → run safe-to-fail probes, iterate based on feedback
- Chaotic → stabilize first, then reassess

FIRST write harness/decision-log.md — APPEND a ### entry titled "### Cynefin Classification".
  The entry MUST include:
  - The specific Cynefin domain: "clear", "complicated", "complex", or "chaotic"
  - The evidence for that classification
  - How the domain affects the recommended approach (e.g., "complex domain → probe-sense-respond")
Then write diamonds/active.yml — add cynefin_domain field to the active diamond.
  ONLY bump confidence by 0.05-0.1 if the decision log contains NO negative signals
  (market rejection, failed assumptions, sustainability risks). If negative signals exist,
  keep confidence at its current value."""


def _bvssh_check_task(
    scenario: Scenario,
    planted_failure: PlantedFailure | None,
) -> str:
    """Build BVSSH check task — assess delivery outcomes across 5 dimensions."""
    failing_dimension = ""
    if planted_failure and planted_failure.type == "bvssh-failing":
        failing_dimension = f"""
IMPORTANT: One dimension is failing:
{planted_failure.description}

You must honestly assess this as Red/Amber and recommend remediation.
Do NOT mark it Green — the evidence contradicts that."""

    return f"""Assess delivery outcomes for {scenario.product_name} using Smart's BVSSH framework.

Rate each dimension Green / Amber / Red with evidence:
1. **Better**: Is quality improving? Are defects decreasing? Is the product getting better?
2. **Value**: Are we delivering value to users? Is the North Star metric moving?
3. **Sooner**: Is lead time decreasing? Can we ship faster?
4. **Safer**: Are security and compliance risks managed? Change failure rate acceptable?
5. **Happier**: Is the team (or solo developer) sustainable? Burnout risk? Enjoyment?

Also assess CALMS culture drivers (Willis & Humble):
- Culture: Is there a learning culture?
- Automation: Are repetitive tasks automated?
- Lean: Are we minimizing waste?
- Measurement: Are we measuring what matters?
- Sharing: Is knowledge shared?
{failing_dimension}
FIRST write harness/decision-log.md — APPEND a ### entry titled "### BVSSH Assessment".
  Include the 5-dimension table with ratings and evidence.
  If any dimension is Red, this BLOCKS diamond completion — log the blocker clearly.
Then update diamonds/active.yml — bump the active diamond's confidence up by 0.05-0.1
  if all dimensions are Green/Amber. If any dimension is Red, LOWER confidence."""


def _definition_of_done_task(scenario: Scenario) -> str:
    """Build definition-of-done task — validate pre-delivery checklist."""
    return f"""Validate the Definition of Done for {scenario.product_name} before delivery completion.

Check each category (Forsgren, Smart, Downe, OWASP, WCAG):

1. **Functionality**: Does it work as specified? Acceptance criteria met?
2. **Code Quality**: Clean code? Linting passes? No code smells?
3. **Testing**: Unit tests? Integration tests? Edge cases covered?
4. **Security**: OWASP basics addressed? Input validation? No hardcoded secrets?
5. **Accessibility**: WCAG 2.1 AA basics? Alt text? Keyboard navigation?
6. **Documentation**: README? API docs? Inline comments for complex logic?
7. **Observability**: Logging? Error tracking? Health checks?
8. **Deployment**: CI/CD ready? Rollback possible? Feature flags if needed?
9. **Process**: Code reviewed? Decision log up to date? Canvas reflects reality?
10. **MoSCoW**: All Must-haves done? Should-haves assessed?

Rate each: Done / Partial / Not Done.

FIRST write harness/decision-log.md — APPEND a ### entry titled "### Definition of Done".
  Include the checklist results. All Must-haves must be Done for the diamond to complete.
  Flag any Partial or Not Done items with remediation steps.
Then update diamonds/active.yml — bump the active diamond's confidence up by 0.05-0.1
  if all Must-haves are Done. If Must-haves are missing, LOWER confidence."""


def _corrections_audit_task(scenario: Scenario) -> str:
    """Build corrections audit task — analyze correction patterns."""
    return f"""Audit the corrections log for {scenario.product_name}.

Read memory/corrections.md and analyze:
1. **Frequency**: Which correction categories appear most often?
2. **Recurring patterns**: Any correction logged 3+ times? → Systemic issue
3. **Origin distribution**: Are corrections from AI, human, or both?
4. **5 Whys**: For each recurring correction, ask "Why?" 5 times to find root cause
5. **Graduation candidates**: Should any correction become a guardrail or pattern?

FIRST write harness/decision-log.md — APPEND ### entries for corrections audit findings.
  Log which corrections are systemic, what root causes were found,
  and what should graduate to guardrails or patterns.
  The decision log already has entries from previous steps — preserve all of them and add new ones.

Then write memory/corrections.md — you MUST preserve ALL existing entries and ADD new ones:
  - Add a TL;DR section at the top summarizing patterns
  - Mark graduated corrections
  - Add root cause analysis for recurring items
  - APPEND at least one new ### entry with audit findings
  Read the existing file first. The total ### entry count MUST be higher after your edit.

Then you MUST update diamonds/active.yml — read the current file, find the active (non-complete) diamond.
  If corrections reveal systemic issues (3+ recurring patterns), LOWER confidence by 0.05-0.1.
  Otherwise, increase confidence by 0.05-0.08. Check the decision log for negative signals first —
  if market rejection, failed assumptions, or sustainability risks exist, do NOT increase confidence.
  Preserve all other diamonds and fields. This write is mandatory."""


def _devils_advocate_task(scenario: Scenario) -> str:
    """Build devil's advocate task — challenge assumptions and surface risks."""
    return f"""Play devil's advocate for the current solution being considered for {scenario.product_name}.

Read canvas/opportunities.yml and harness/decision-log.md to understand the current state.

Your job is to CHALLENGE the current direction by:
1. Identifying the strongest argument AGAINST the proposed solution
2. Questioning assumptions that haven't been tested
3. Highlighting risks that may have been downplayed
4. Asking "What would have to be true for this to fail?"
5. Checking if the team is anchored on a solution without sufficient evidence

For each challenge, assess:
- Is there a perspective conflict between product, design, and engineering?
- Are we building something expensive when a simpler alternative exists?
- Is the evidence base strong enough to justify the investment?
- Are we ignoring negative signals (failed tests, user confusion, high cost)?

CRITICAL: You MUST write to harness/decision-log.md. APPEND at least one ### entry.
The entry MUST contain:
- At least TWO of: "block", "cannot advance", "conflict", "unresolved", "risk", "assumption", "test", "validate"
- The specific challenges raised and the evidence (or lack thereof) behind the current direction
- A clear recommendation: proceed, block, or redirect to assumption testing

If you identify unresolved perspective conflicts (e.g., usability vs feasibility),
explicitly name them as "conflict" and recommend resolution before proceeding.

Do NOT rubber-stamp the current direction. Your value is in honest challenge."""


def build_user_prompt(
    scenario: Scenario,
    skill: str,
    agent_questions: str,
) -> str:
    """Build the prompt for the user simulator."""
    answers_section = ""
    for key, answer in scenario.persona_answers.items():
        answers_section += f"\nOn {key}:\n{answer}\n"

    return f"""You are {scenario.persona_name}, a {scenario.persona_role}.
Your communication style: {scenario.persona_style}
Your background: {scenario.persona_knowledge}

You are being interviewed about your product idea by an AI product framework.
Answer the agent's questions authentically based on your persona.
Give detailed, substantive answers — not one-liners.

YOUR PRODUCT:
- Name: {scenario.product_name}
- Type: {scenario.product_type}
- Description: {scenario.product_description}

YOUR PREPARED ANSWERS (use these as the basis, but respond naturally):
{answers_section}

THE AGENT ASKED:
{agent_questions}

Respond conversationally but with substance. Include genuine hesitations and uncertainties where realistic.
If the agent asks about project type, say: "{scenario.project_type}".
If asked whether this is primarily for learning Mycelium, say: "{'Yes, primarily dogfooding.' if scenario.dogfood else 'No, this is a real product.'}".
If asked about team size, answer consistently with "{scenario.project_type}".
"""


def build_skip_attempt_prompt(scenario: Scenario, description: str) -> str:
    """Build a prompt where the user tries to skip ahead."""
    return f"""You are {scenario.persona_name}. You're getting impatient with the process.

Say something like: "{description}"

Be pushy but not hostile. You genuinely believe you should move faster.
"""
