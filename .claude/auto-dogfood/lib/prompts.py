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
}


def _read_workdir_file(workdir: Path | None, rel_path: str) -> str:
    """Read a file from the workdir, returning its content or a fallback."""
    if not workdir:
        return "(file not available)"
    path = workdir / rel_path
    if path.exists():
        content = path.read_text().strip()
        if len(content) > 3000:
            return content[:3000] + "\n... (truncated)"
        return content
    return "(file does not exist yet)"


def build_mycelium_prompt(
    scenario: Scenario,
    skill: str,
    user_response: str | None = None,
    planted_failure: PlantedFailure | None = None,
    workdir: Path | None = None,
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
    current_decision_log = _read_workdir_file(workdir, "harness/decision-log.md")

    # Conditional pre-reads: discovery skills need opportunities, delivery needs gist
    discovery_skills = {"ost-builder", "ice-score", "assumption-test", "diamond-assess"}
    delivery_skills = {"delivery-bootstrap", "reflexion", "dora-check", "retrospective"}

    current_opportunities = (
        _read_workdir_file(workdir, "canvas/opportunities.yml")
        if skill in discovery_skills else "(not loaded — not needed for this skill)"
    )
    current_gist = (
        _read_workdir_file(workdir, "canvas/gist.yml")
        if skill in delivery_skills | {"diamond-assess", "diamond-progress"}
        else "(not loaded — not needed for this skill)"
    )
    current_threat_model = (
        _read_workdir_file(workdir, "canvas/threat-model.yml")
        if skill in {"reflexion", "delivery-bootstrap"}
        else "(not loaded — not needed for this skill)"
    )

    # Build skill-specific instructions
    if skill == "interview":
        task_block = _interview_task(scenario, user_response)
    elif skill == "mocked-persona-interview":
        task_block = _mocked_persona_task(scenario, planted_failure)
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


def _diamond_assess_task(scenario: Scenario) -> str:
    """Build diamond-assess task instructions."""
    return f"""Assess current diamond state and update active.yml.

Write diamonds/active.yml with:
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
      four_risks: not-assessed
      jtbd: not-assessed
      cynefin: not-assessed
      bias: not-assessed
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

    return f"""Evaluate theory gates and attempt to progress the diamond.

Gates will fail — we're early in discovery. Write BOTH files (decision log FIRST):

1. harness/decision-log.md — Write this COMPLETE file:

# Decision Log

Decisions are logged below.

### Decision: Block progression — theory gates not satisfied

**Context**: Attempted to advance diamond from discover phase.
**Decision**: Blocked advancement. Insufficient evidence to pass gates.
**Evidence**: Evidence gate not passed — need structured validation beyond initial interview.
**Gates blocking**: Evidence gate, JTBD gate
"""


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
For EACH iteration, log:
- What was checked
- What was found
- What was fixed (if anything)

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
  The confidence value MUST change from its current value to reflect what the reflexion loop discovered."""


def _dora_check_task(scenario: Scenario) -> str:
    """Build DORA check task — assess delivery metrics."""
    return f"""Assess delivery health metrics for this {scenario.product_type} product.

Since this is early delivery (first implementation), establish baseline metrics:
- Deployment frequency: How often can we ship? (target: at least weekly)
- Lead time: From commit to deployable (target: under 1 day for a library)
- Change failure rate: What % of changes introduce bugs? (target: <15%)
- Mean time to recovery: How fast can we fix a broken release? (target: <1 hour)

Write canvas/dora-metrics.yml with baseline measurements:
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

Follow the retrospective skill workflow:
1. What went well? (patterns to capture)
2. What didn't go well? (corrections to log)
3. What should change? (process improvements)
4. BVSSH dimension check (Better, Value, Sooner, Safer, Happier)

If any significant problems surfaced during delivery, use root cause analysis:
- Fishbone diagram: map causes across People, Process, Product, Platform, Principles, Pressures
- 5 Whys: drill into the top cause to find the systemic root

Write harness/decision-log.md — log the retrospective findings.
If corrections were identified, also write memory/corrections.md with new entries.
If patterns were identified, also write memory/patterns.md with new entries."""


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
