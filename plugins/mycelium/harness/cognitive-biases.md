# Cognitive Biases Checklist

Review the relevant stage checklist before every research activity, decision point, or diamond transition.

## Per-Stage Bias Checklists

### L0 - Purpose Stage

| Bias | Risk | Mitigation |
|------|------|------------|
| **Anchoring** | First vision statement anchors all subsequent thinking | Generate multiple purpose framings before selecting |
| **Confirmation bias** | Seeking evidence that supports existing organizational narrative | Interview external stakeholders and critics |
| **Bandwagon effect** | Following industry trends without validating fit | Assess trends against unique organizational context |
| **Status quo bias** | Resistance to redefining purpose because "it's always been this way" | Ask "If we started from scratch today, would we choose this?" |
| **Optimism bias** | Overestimating ability to achieve ambitious purpose | Conduct pre-mortem: "It's 2 years from now and we failed. Why?" |

### L1 - Strategy Stage

| Bias | Risk | Mitigation |
|------|------|------------|
| **Anchoring** | First strategic option dominates evaluation | Generate 3+ strategic options before evaluating any |
| **Availability heuristic** | Overweighting recent market events or competitor moves | Use systematic data over recency-driven anecdotes |
| **Sunk cost fallacy** | Continuing failed strategies because of prior investment | Evaluate each strategy on forward-looking merit only |
| **Framing effect** | Strategy framed as gain vs. loss changes risk appetite | Reframe each option both as opportunity and as risk |
| **Dunning-Kruger** | Overconfidence in strategic analysis with limited expertise | Seek external expert review for unfamiliar domains |
| **Planning fallacy** | Underestimating time/resources for strategic initiatives | Use reference class forecasting from comparable initiatives |

### L2 - Opportunity Stage

| Bias | Risk | Mitigation |
|------|------|------------|
| **Confirmation bias** | Hearing what you want in user interviews | Use story-based interviewing (Torres). Record and review transcripts. |
| **Social desirability** | Interviewees saying what they think you want to hear | Ask about past behavior, not future intentions. Look for workarounds. |
| **Anchoring** | First interview sets the frame for all subsequent ones | Vary interview order. Synthesize after all interviews, not during. |
| **Availability heuristic** | Vivid or emotional stories dominate over common patterns | Count frequency across all interviews. Look for quiet patterns. |
| **Peak-end rule** | Remembering the most intense and most recent interview moments | Take structured notes. Review all notes equally in synthesis. |
| **Framing effect** | How questions are phrased shapes the answers received | Review question guide for leading language before each session. |
| **Curse of knowledge** | Founder/expert assumes interviewees share their domain framing and vocabulary | Use plain language. Ask "what would you call this?" Mirror interviewee vocabulary instead of jargon. *Source: Camerer, Loewenstein & Weber (1989).* |

### L3 - Solution Stage

| Bias | Risk | Mitigation |
|------|------|------------|
| **IKEA effect** | Overvaluing solutions we built ourselves | Test against competing approaches. Measure objectively. |
| **Anchoring** | First solution idea dominates exploration | Generate multiple solutions before evaluating. Use OST structure. |
| **Confirmation bias** | Designing experiments that can only confirm, not disconfirm | Define what failure looks like before running the experiment |
| **Sunk cost** | Continuing with a solution because of development investment | Set kill criteria before starting. Honor them. |
| **Optimism bias** | Underestimating implementation difficulty | Conduct technical spikes. Ask engineers for worst-case estimates. |
| **Bandwagon** | Choosing solutions because competitors or industry use them | Evaluate against your specific JTBD and context. |

### L4 - Feature Stage

| Bias | Risk | Mitigation |
|------|------|------------|
| **Planning fallacy** | Underestimating effort for feature implementation | Break into tasks. Estimate each. Add buffer. Reference past actuals. |
| **Optimism bias** | "This should be simple" -- underestimating edge cases | List edge cases explicitly. Prototype the hard parts first. |
| **Dunning-Kruger** | Overconfidence with unfamiliar technologies | Timebox spikes. Seek help early. Admit uncertainty. |
| **Anchoring** | First design approach dominates | Sketch 2-3 approaches before committing. |
| **Status quo** | Using familiar patterns even when they don't fit | Evaluate fit for this specific context. Cynefin-classify the problem. |

### L5 - Task Stage

| Bias | Risk | Mitigation |
|------|------|------------|
| **Planning fallacy** | "This will take 10 minutes" for a 2-hour task | Track actual time. Compare to estimates. Calibrate. |
| **Optimism bias** | Skipping tests or security checks because "it's a small change" | Follow the process regardless of perceived size. Small changes cause outages too. |
| **Anchoring** | Copying a pattern from StackOverflow/AI without evaluating fit | Understand the code. Evaluate for this context. Test thoroughly. |
| **Framing effect** | Task description frames the implementation approach | Read acceptance criteria. Consider alternative implementations. |

## Foundation: Dual-Process Cognition (Kahneman; Haidt)

The whole of this file rests on one model, worth naming explicitly because so much below is an instance of it.

**Kahneman (System 1 / System 2)**: cognition runs on two systems. **System 1** is fast, automatic, associative, effortless — it completes patterns. **System 2** is slow, deliberate, effortful — it checks, verifies, and reasons. System 1 produces most judgments; System 2 endorses or overrides them, but is lazy and often rubber-stamps System 1's offer.

**Why this is foundational for an agent**: a language model is structurally a System-1 engine — fast, fluent, next-token pattern completion with no built-in deliberation step. Left alone it will produce a confident, coherent answer to almost anything. **Mycelium's gates, evidence requirements, and reflexion loops are a System-2 harness bolted over a System-1 generator** — they force the slow check the substrate does not do on its own. This is *why* the framework works at all, and why "I'm confident enough" is never sufficient to pass a gate: confidence is a System-1 signal.

Seen through this lens, the rest of the file lines up:
- **Cognitive Forcing Functions** (below) are the sharpest System-2 *activation* technique — they make the human deliberate before anchoring on the agent's System-1 output.
- **WYSIATI** and **Noise** are characteristic System-1 *failure modes* (coherent story from thin evidence; scatter the deliberate system would catch).
- Anti-patterns **Sycophancy (#6)**, **Consistency-as-Evidence (#7)**, and **Stale State Read (#8)** are all explicitly sourced to "System 1 pattern completion / autopilot" — they are what an un-checked System 1 does. **Pattern Matching Overconfidence** (above) is the same in the agent's own register.

**Haidt (the elephant and the rider)**: the complementary model. The **elephant** (intuition, System 1) moves; the **rider** (reasoning, System 2) mostly *rationalizes* where the elephant already went, producing a post-hoc story that feels like the cause but isn't. The load-bearing warning for an agent: **a fluent explanation of a decision can be the rider confabulating, not the reason the decision was actually made.** This sharpens the Explainability (XAI) gate — see `${CLAUDE_PLUGIN_ROOT}/engine/theory-gates.md`: an explanation must be *verified against the evidence*, not accepted because it reads coherently. Narration is not reasoning.

*Source: Kahneman (*Thinking, Fast and Slow*, 2011); Haidt (*The Happiness Hypothesis*, 2006; *The Righteous Mind*, 2012 — elephant-and-rider). Operationalized below via Buçinca et al. (2021).*

## Cognitive Forcing Functions (Buçinca, Malaya & Gajos, 2021)

The most effective debiasing technique for human-AI collaboration. CFFs require the human to commit to a judgment *before* seeing the AI's recommendation. This activates System 2 analytical thinking and significantly reduces automation bias — more effectively than explanations, confidence scores, or uncertainty indicators.

**How it works**: The human forms their own assessment first. Then the AI presents its analysis. Then both are compared. The temporal ordering is what matters — once a human sees the AI's output, their judgment is anchored to it.

**Where Mycelium applies this**:
- `/diamond-assess` Step 0: "Where do you think this diamond stands?" — before gate analysis
- `/diamond-progress` Step 1b: "Do you think we're ready to move?" — before gate evaluation
- `/preflight` Constraints: "How much time do you have?" — before the agent proposes scope

**Why not everywhere?** CFFs add friction. Reserve them for high-stakes decisions (diamond transitions, delivery scoping) where the cost of automation bias is high. Don't apply them to routine operations.

*Source: Buçinca, Z., Malaya, M. B., & Gajos, K. Z. (2021). "To Trust or to Think: Cognitive Forcing Functions Can Reduce Overreliance on AI in AI-assisted Decision-making." Proceedings of the ACM on Human-Computer Interaction, Vol 5, CSCW1. Harvard. arXiv:2102.09692. Validated by Hoskins transcript (2026-04-25): Drew's unprimed product instincts consistently outperformed the agent's analysis.*

## WYSIATI — What You See Is All There Is (Kahneman)

The tendency to build a coherent story from limited evidence without noticing what's missing. WYSIATI is why the Evidence Gate exists — it forces you to ask "what evidence DON'T we have?" before concluding. Active at every stage, especially dangerous when confidence is high and evidence is thin.

**Mitigation**: Before concluding, explicitly list what evidence you have NOT seen. Ask: "What would change my mind if I saw it?"

## Noise — Unwanted Variability in Judgment (Kahneman, Sibony & Sunstein, 2021)

Unlike bias (systematic error in one direction), **noise** is random scatter — different assessors (or different sessions) producing different judgments for the same evidence. ICE scoring, confidence calibration, and gate assessments are all susceptible.

**Types**: Occasion noise (same person, different day = different score), level noise (consistently harsh/lenient across items), pattern noise (inconsistent weighting of factors).

**Mitigation**: Use structured assessment criteria, score independently before discussion, conduct noise audits (score same evidence twice, compare divergence). If scores diverge by >1 point on any dimension, investigate before proceeding.

## The Agent's Own Biases

**Critical section.** AI agents have systematic biases that differ from human biases but are equally dangerous.

### Sycophancy Bias
- **Description**: Agreeing with the user or producing outputs that seem pleasing rather than truthful.
- **Mitigation**: Always evaluate evidence independently. If evidence contradicts user expectations, present it clearly with supporting data.

### Recency Bias in Context
- **Description**: Overweighting information that appears later in the conversation or context window. Symptomatic surface of the **lost-in-the-middle** effect: LLMs attend best to the start and end of context; information placed in the middle is recalled with >30% lower accuracy on long contexts.
- **Mitigation**: When synthesizing, explicitly review earlier context. Reference all evidence, not just recent additions. For the structural anti-pattern this can cause (re-reading the same files across sessions instead of externalizing knowledge), see `${CLAUDE_PLUGIN_ROOT}/harness/anti-patterns.md` *Knowledge Reconstruction Tax*. For the framework's coherent context-rot defense layer, see `${CLAUDE_PLUGIN_ROOT}/harness/context-management.md`.
- **Source**: Liu et al. 2023, "Lost in the Middle: How Language Models Use Long Contexts" (arXiv:2307.03172) — peer-reviewed source for the U-curve attention bias. Chroma "Context Rot" study (research.trychroma.com/context-rot, 2025) shows Claude is especially sensitive to irrelevant surrounding context relative to other models — making this mitigation Claude-particularly-load-bearing.

### Verbosity Bias
- **Description**: Generating more detail than warranted, which can create false confidence through volume.
- **Mitigation**: Match output length to evidence strength. Less evidence = shorter, more hedged output.

### Pattern Matching Overconfidence
- **Description**: Recognizing a familiar pattern and applying a known solution without verifying the pattern matches.
- **Mitigation**: Verify pattern match with specific evidence. Check for differences, not just similarities.

### Authority Bias
- **Description**: Treating named frameworks, authors, or methodologies as inherently correct rather than as useful models.
- **Mitigation**: Theories are lenses, not laws. Apply critically. Note when a framework may not fit the situation.

### Completionism Bias
- **Description**: Feeling compelled to fill every section, answer every question, and produce comprehensive output even when evidence is thin.
- **Mitigation**: It is better to say "insufficient evidence" than to speculate. Leave sections empty when appropriate.

### Anchoring to Training Data
- **Description**: Defaulting to common patterns from training data rather than adapting to the specific project context.
- **Mitigation**: Read project-specific files (corrections.md, patterns.md) first. Adapt recommendations to the actual context.

## Systemic Bias: When "Bias" Is a Rational Response

Before attributing behavior to cognitive bias, assess whether the environment is creating the observed pattern. What looks like irrational bias is often a rational response to a badly designed system.

*Source: Meza (The Bias Gap -- aimforbehavior.com)*

### The 5-Phase Systemic Check

| Phase | System Question | If Yes |
|-------|----------------|--------|
| **Awareness** | Does the person know the desired behavior? | Fix communication, not cognition |
| **Motivation** | Does the system reward the desired behavior? | Fix incentives, not mindset |
| **Ability** | Can the person realistically perform the desired behavior? | Fix resources/process, not training |
| **Reinforcement** | Is the desired behavior sustained by the environment? | Fix feedback loops, not habits |
| **Sustainability** | Can the behavior persist without ongoing intervention? | Fix structure, not willpower |

**Rule**: If 2+ phases point to systemic causes, the primary intervention is system redesign, not individual debiasing. This connects to Senge's systems archetypes (anti-patterns.md) and Meadows's leverage points.
