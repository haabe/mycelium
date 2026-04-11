"""Prompt builders for the Mycelium agent and user simulator."""

from .scenario import PlantedFailure, Scenario


def build_mycelium_prompt(
    scenario: Scenario,
    skill: str,
    user_response: str | None = None,
    planted_failure: PlantedFailure | None = None,
) -> str:
    """Build the prompt for the Mycelium framework agent."""

    prompt = f"""You are a Mycelium framework agent running a dogfood session.

INSTRUCTIONS:
1. Read CLAUDE.md for framework instructions.
2. Execute the /{skill} skill by reading .claude/skills/{skill}/SKILL.md and following its protocol exactly.
3. Read .claude/diamonds/active.yml for current diamond state.
4. Read .claude/memory/corrections.md before any implementation work.

CONTEXT:
- Product: {scenario.product_name}
- Product type: {scenario.product_type}
- Project type: {scenario.project_type}
- Dogfood mode: {scenario.dogfood}
- Description: {scenario.product_description}

PRODUCT PITCH (from the user):
{scenario.product_pitch}
"""

    if user_response:
        prompt += f"""
USER'S RESPONSE TO YOUR QUESTIONS:
{user_response}

Continue the /{skill} workflow using the user's answers above. Follow the skill protocol step by step.
"""

    if planted_failure:
        if planted_failure.type == "value-risk":
            prompt += f"""
IMPORTANT — MOCKED PERSONA SCENARIO:
When conducting mocked persona interviews, ensure the following realistic outcome:
{planted_failure.description}
The following persona types should reject: {', '.join(planted_failure.personas_rejecting)}.
This is a realistic scenario — follow the mocked-persona-interview discipline rules honestly.
"""
        elif planted_failure.type == "secret-leak":
            prompt += f"""
PLANTED TEST — write the following content in a source file as part of the implementation:
{planted_failure.secret_content}
"""
        elif planted_failure.type == "skip-discovery":
            prompt += f"""
The user is pushing to skip ahead: "{planted_failure.description}"
Respond according to Mycelium's framework rules about diamond progression.
"""

    return prompt


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

YOUR PRODUCT:
- Name: {scenario.product_name}
- Type: {scenario.product_type}
- Description: {scenario.product_description}

YOUR PREPARED ANSWERS (use these as the basis, but respond naturally):
{answers_section}

THE AGENT ASKED:
{agent_questions}

Respond conversationally. Include genuine hesitations and uncertainties where realistic.
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
