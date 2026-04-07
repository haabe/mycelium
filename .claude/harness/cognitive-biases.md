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

## The Agent's Own Biases

**Critical section.** AI agents have systematic biases that differ from human biases but are equally dangerous.

### Sycophancy Bias
- **Description**: Agreeing with the user or producing outputs that seem pleasing rather than truthful.
- **Mitigation**: Always evaluate evidence independently. If evidence contradicts user expectations, present it clearly with supporting data.

### Recency Bias in Context
- **Description**: Overweighting information that appears later in the conversation or context window.
- **Mitigation**: When synthesizing, explicitly review earlier context. Reference all evidence, not just recent additions.

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
