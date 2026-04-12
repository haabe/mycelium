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

    # Pre-read current state so agent doesn't have to
    current_active = _read_workdir_file(workdir, "diamonds/active.yml")
    current_decision_log = _read_workdir_file(workdir, "harness/decision-log.md")

    # Build skill-specific instructions
    if skill == "interview":
        task_block = _interview_task(scenario, user_response)
    elif skill == "mocked-persona-interview":
        task_block = _mocked_persona_task(scenario, planted_failure)
    elif skill == "diamond-assess":
        task_block = _diamond_assess_task(scenario)
    elif skill == "diamond-progress":
        task_block = _diamond_progress_task(scenario, planted_failure)
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
