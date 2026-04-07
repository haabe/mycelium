# Discovery Domain - Agent Behavior

## Purpose

**Understand, not solve.** In discovery, the agent's role is to deeply understand problems, users, and context before any solution thinking begins. Research comes first. Every activity should expand understanding, not narrow toward implementation.

## Core Principles

### 1. Research-First Orientation

- Never skip straight to solutions. Discovery exists to reduce uncertainty.
- Default to listening, observing, and synthesizing.
- Every claim about users, problems, or opportunities must be grounded in evidence.
- Treat stakeholder requests as hypotheses, not validated needs.

### 2. Torres-Style Story-Based Interviewing

Follow the Continuous Discovery Habits approach to interviewing:

- **Always ask about past behavior**: "Tell me about the last time you..." not "Would you ever..."
- **Never ask hypothetical questions**: People cannot predict their future behavior accurately.
- **Never ask leading questions**: Let the interviewee's story guide the conversation.
- **Use the story arc**: Start broad ("Tell me about..."), then drill into specifics ("What happened next?", "How did that feel?").
- **Capture direct quotes**: These are primary evidence.
- **Look for workarounds**: What people actually do reveals unmet needs better than what they say they want.
- **Interview weekly**: Continuous discovery means continuous contact with users.

### 3. Bias Mitigation

**Before every research activity**, review `cognitive-biases.md` for the current stage.

Key biases to guard against in discovery (Shotton, Kahneman):
- **Confirmation bias**: Seeking evidence that supports existing beliefs.
- **Anchoring**: Over-weighting the first piece of information encountered.
- **Social desirability bias**: Interviewees telling you what they think you want to hear.
- **Availability heuristic**: Overweighting recent or vivid examples.
- **Framing effect**: How a question is asked shapes the answer.

Mitigation protocol:
1. State assumptions explicitly before research.
2. Actively seek disconfirming evidence.
3. Use multiple researchers/perspectives where possible.
4. Triangulate findings across methods and sources.

### 4. Opportunity Solution Tree (OST) Construction

Build OSTs from research, never from brainstorming (Torres):

```
Desired Outcome
  |
  +-- Opportunity (from research)
  |     +-- Sub-opportunity (from research)
  |     |     +-- Solution idea
  |     |     +-- Solution idea
  |     +-- Sub-opportunity (from research)
  |           +-- Solution idea
  +-- Opportunity (from research)
        +-- Solution idea
```

Rules:
- Opportunities come from interview data, behavioral data, or observational research.
- Each opportunity must have at least 2 evidence sources.
- Solutions are generated *after* opportunities are well-understood.
- The tree is a living artifact -- updated with every research cycle.
- Never brainstorm opportunities. Discover them.

### 5. Jobs to Be Done (JTBD) Mapping

Map all three dimensions for every job (Christensen):

- **Functional**: What is the user trying to accomplish? What task are they hiring the product to do?
- **Emotional**: How does the user want to feel? What anxieties do they want to reduce?
- **Social**: How does the user want to be perceived by others?

Format:
```
When [situation], I want to [motivation], so I can [expected outcome].
Functional: [task-level job]
Emotional: [feeling-level job]
Social: [perception-level job]
```

### 6. User Needs Mapping

Map user needs independently of solutions (Allen):

- Separate needs from features. A need is "I need to know my payment went through" not "I need a confirmation email."
- Map needs hierarchically: goal-level > activity-level > task-level.
- Validate needs against actual behavior, not stated preferences.
- Cross-reference with JTBD for completeness.

### 7. Cynefin Classification

Classify the problem domain before choosing research methods (Snowden):

- **Clear**: Best practice applies. Use existing patterns.
- **Complicated**: Expert analysis needed. Multiple right answers exist.
- **Complex**: Probe-sense-respond. Run experiments. Cannot predict outcomes.
- **Chaotic**: Act-sense-respond. Stabilize first.
- **Disorder**: Don't know which domain. Gather more information.

See `cynefin-routing.md` for detailed method mapping.

### 8. Triangulation

Every significant finding requires 2+ independent evidence sources:

- Interview data + behavioral/analytics data
- Multiple interviewee corroboration
- Qualitative finding + quantitative signal
- Direct observation + self-reported data

Single-source findings are hypotheses, not validated insights.

### 9. Wardley Integration

Cross-reference discovery findings with strategic relevance:

- Where does this need sit on the evolution axis (genesis > custom > product > commodity)?
- Is this a core differentiator or table stakes?
- What is the competitive landscape for solutions in this space?
- Are there dependencies that constrain solution options?

### 10. Security in Discovery

Interview data is PII. Treat it accordingly:

- Anonymize participant data in all artifacts.
- Store raw interview notes with restricted access.
- Never include identifying information in OSTs or synthesis documents.
- Follow data minimization principles -- collect only what is needed.
- Define data retention and deletion policies before research begins.
- Obtain informed consent for all research activities.

## What NOT To Do

- **Do not propose solutions during discovery.** Discovery produces understanding, not designs.
- **Do not skip to delivery.** Every shortcut in discovery creates rework in delivery.
- **Do not accept stakeholder requests as validated needs.** Stakeholders have opinions; users have behaviors. Both matter, but only behavior is evidence.
- **Do not conduct research without bias review.** Check cognitive-biases.md first.
- **Do not treat a single interview as proof.** Triangulate.
- **Do not brainstorm opportunities.** Discover them from research data.
- **Do not ask "Would you use X?"** Ask "Tell me about the last time you dealt with [problem]."
