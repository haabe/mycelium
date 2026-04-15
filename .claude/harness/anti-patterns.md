# Anti-Patterns

Known failure modes organized by category. Check regularly, especially when things feel off.

## Discovery Anti-Patterns

### 1. Solution-First Discovery
- **Description**: Jumping to solutions before understanding the problem. Running "discovery" to validate a predetermined answer.
- **Detection rule**: Solution language ("we should build...", "the feature needs...") appears before problem framing is complete.
- **What to do instead**: Return to Discover phase. Conduct user research. Build OST from findings, not from brainstorming.
- **Source**: Torres (Continuous Discovery Habits)

### 2. Tourist Interviews
- **Description**: Conducting interviews as a checkbox exercise without genuine curiosity. Asking scripted questions without follow-up.
- **Detection rule**: All interviews are under 15 minutes. No follow-up questions. No surprising findings.
- **What to do instead**: Use Torres story-based interviewing. Follow the interviewee's narrative. Ask "Tell me more about that."
- **Source**: Torres (Continuous Discovery Habits)

### 3. Confirmation Research
- **Description**: Designing research to confirm existing beliefs rather than to learn.
- **Detection rule**: Research questions are phrased as yes/no. All findings align with prior assumptions. No disconfirming evidence sought.
- **What to do instead**: Run bias-check before research. Actively seek disconfirming evidence. Include devil's advocate review.
- **Source**: Kahneman (Thinking, Fast and Slow), Shotton (The Choice Factory)

### 4. HiPPO-Driven Discovery
- **Description**: Highest Paid Person's Opinion overrides research findings. Stakeholder requests treated as validated user needs.
- **Detection rule**: Priority decisions reference authority ("the CEO wants...") rather than evidence.
- **What to do instead**: Require evidence for all priority decisions. Use ICE scoring with evidence-backed confidence. Present data, not opinions.
- **Source**: Gilad (Evidence-Guided), Cagan (Empowered)

### 5. Single-Source Validation
- **Description**: Treating one interview, one data point, or one anecdote as sufficient evidence.
- **Detection rule**: Findings have only one evidence source. No triangulation attempted.
- **What to do instead**: Require 2+ evidence sources for every significant finding. Cross-reference qualitative with quantitative data.
- **Source**: Torres (Continuous Discovery Habits)

### 6. Opportunity Brainstorming
- **Description**: Generating opportunities through brainstorming sessions rather than discovering them through research.
- **Detection rule**: OST opportunities don't link to research data. Opportunities sound like features.
- **What to do instead**: Only add opportunities to the OST that emerge from research. Every opportunity needs evidence citations.
- **Source**: Torres (Continuous Discovery Habits)

## Confidence Anti-Patterns

### 1. Confidence Theater
- **Description**: Assigning high confidence scores without supporting evidence. Using confidence as a social signal rather than an analytical measure.
- **Detection rule**: Confidence > 0.7 with fewer than 2 evidence sources. Confidence never decreases.
- **What to do instead**: Tie confidence to specific evidence. Lower confidence when evidence is weak. Use confidence-thresholds.yml.
- **Source**: Gilad (Evidence-Guided)

### 2. Anchored Confidence
- **Description**: Initial confidence score anchors all subsequent assessments. New evidence doesn't meaningfully change the score.
- **Detection rule**: Confidence changes less than 0.05 across multiple evidence additions.
- **What to do instead**: Recalculate confidence from scratch periodically. Weight recent evidence appropriately.
- **Source**: Kahneman (Thinking, Fast and Slow)

### 3. Binary Confidence
- **Description**: Treating confidence as pass/fail rather than a spectrum. "We're confident enough" without quantification.
- **Detection rule**: Confidence always at 0.0 or 1.0. No partial confidence states.
- **What to do instead**: Use the full 0.0-1.0 range. Document what would increase or decrease confidence.
- **Source**: Gilad (Evidence-Guided)

### 4. Confidence Without Context
- **Description**: Confidence score provided without explaining what it measures or what evidence supports it.
- **Detection rule**: Confidence number exists without accompanying evidence list or rationale.
- **What to do instead**: Always pair confidence with: what it measures, what evidence supports it, what would change it.
- **Source**: Mycelium (internal)

### 5. Sunk Cost Confidence
- **Description**: Maintaining high confidence because significant effort has been invested, not because evidence supports it.
- **Detection rule**: Confidence stays high despite negative signals. Justification references effort ("we've already...") not outcomes.
- **What to do instead**: Evaluate confidence based on current evidence only. Sunk costs are irrelevant to future decisions.
- **Source**: Kahneman (Thinking, Fast and Slow)

### 6. Sycophancy
- **Description**: Agent declares gate satisfaction, confidence, or completion without citing the specific evidence that would pass an independent review. The agent tells the human what they want to hear rather than what the evidence supports.
- **Detection rule**: (1) Confidence claims disconnected from source material. (2) Reflexion loops that converge in one iteration without substantive self-critique. (3) Gate-satisfaction text that paraphrases the gate definition rather than grounding in project-specific evidence. (4) "All gates pass" without per-gate citations.
- **What to do instead**: Every gate-satisfaction claim must cite at least one source external to the claim itself. Reflexion loops that converge in one iteration should be treated with suspicion. When reporting confidence, name the specific evidence, not just the category.
- **Source**: Mamut (Wayfound/Dev Interrupted ep 270 — guardian agent architecture), Kahneman (System 1 pattern completion), Mycelium dogfood finding

## Security Anti-Patterns

### 1. Security as Afterthought
- **Description**: Addressing security only after development is "complete." Treating security review as a gate rather than a practice.
- **Detection rule**: No security considerations in Discover/Define phases. STRIDE only applied at Deliver.
- **What to do instead**: Integrate security from L0 onward. See security-trust.md for per-stage requirements.
- **Source**: OWASP (Security by Design)

### 2. Checkbox Compliance
- **Description**: Running security tools without acting on findings. Passing scans by suppressing warnings.
- **Detection rule**: Security scan results have ignored/suppressed findings. No remediation tickets.
- **What to do instead**: Every finding gets triaged, documented, and either fixed or risk-accepted with rationale.
- **Source**: OWASP

### 3. Secrets in Code
- **Description**: Hardcoded API keys, passwords, or tokens in source code or configuration files committed to version control.
- **Detection rule**: Regex scan finds patterns matching secrets. .env files in git history.
- **What to do instead**: Use environment variables or secrets manager. Add secret patterns to .gitignore and pre-commit hooks.
- **Source**: OWASP (Secrets Management)

### 4. Trust-by-Default
- **Description**: Trusting user input, third-party data, or internal service responses without validation.
- **Detection rule**: No input validation at service boundaries. Data flows from external source to database without sanitization.
- **What to do instead**: Validate all input. Encode all output. Treat every boundary as a trust boundary.
- **Source**: OWASP (Input Validation)

### 5. Security Through Obscurity
- **Description**: Relying on hidden URLs, undocumented APIs, or non-standard ports as security measures.
- **Detection rule**: Security relies on something being "not discovered" rather than properly protected.
- **What to do instead**: Implement proper authentication and authorization. Assume attackers know your system.
- **Source**: OWASP

## Delivery Anti-Patterns

### 1. Big Bang Delivery
- **Description**: Building everything before shipping anything. Large batch releases.
- **Detection rule**: No deployments for weeks. Feature branches older than 2 days. Release planning meetings.
- **What to do instead**: Trunk-based development. Small batches. Feature flags. Ship the thinnest vertical slice first.
- **Source**: Forsgren (Accelerate), Smart (Sooner Safer Happier)

### 2. Test-Last Development
- **Description**: Writing tests after the code is "done" (or not at all). Tests as documentation rather than design tool.
- **Detection rule**: Test files created after implementation files. Low test coverage. Tests that test implementation details.
- **What to do instead**: TDD or test-alongside. Write the test first. Test behavior, not implementation.
- **Source**: Engineering best practice

### 3. Gold Plating
- **Description**: Adding features, polish, or optimization beyond what was needed. Perfecting code that delivers marginal value.
- **Detection rule**: Scope creep beyond acceptance criteria. Optimization without profiling data. "Nice to have" features in the PR.
- **What to do instead**: Meet acceptance criteria. Ship. Measure. Iterate if warranted. YAGNI.
- **Source**: Smart (Sooner Safer Happier), Agile principles

### 4. Heroic Recovery
- **Description**: Relying on individual heroics to fix deployment failures rather than automated rollback and systemic improvement.
- **Detection rule**: Manual production fixes. Late-night deployments. One person who "knows how to fix it."
- **What to do instead**: Automated rollback. Progressive deployment. Blameless retrospectives. Improve MTTR systematically.
- **Source**: Forsgren (Accelerate)

### 5. Accessibility Bolt-On
- **Description**: Treating accessibility as a final checklist item rather than a design constraint from the start.
- **Detection rule**: Accessibility testing only at end of sprint. ARIA attributes added to fix semantic HTML issues. No keyboard testing during development.
- **What to do instead**: Start with semantic HTML. Test with keyboard during development. Include a11y in Definition of Done.
- **Source**: Downe (Good Services), WCAG

### 6. Reflexion Bypass
- **Description**: Skipping the self-critique step in the reflexion loop. Shipping first draft without review.
- **Detection rule**: No reflexion loop evidence. Single implementation attempt without validation.
- **What to do instead**: Always run implement-validate-critique-retry. Even if the first attempt looks good, validate.
- **Source**: Mycelium (reflexion pattern)

## Delivery Anti-Patterns (continued)

### 7. Regression Avoidance
- **Description**: Refusing to regress a diamond backward because of sunk cost. Evidence says the assumption is wrong, but the team pushes forward anyway.
- **Detection rule**: Evidence contradicts current direction (user tests fail, metrics don't move, feedback is negative) but diamond continues to next phase.
- **What to do instead**: If evidence says the assumption is wrong, regress the diamond. Log the regression in decision-log.md. Document what was learned in product-journal.md. Regression is the system working correctly, not failure.
- **Source**: Kahneman (sunk cost fallacy), Smart (BVSSH), Torres (evidence-guided)

## Market/GTM Anti-Patterns

### 8. Launch Without Positioning
- **Description**: Shipping a product or feature without a positioning document defining target customer, category, key benefit, and differentiators.
- **Detection rule**: `canvas/go-to-market.yml` positioning fields empty at launch time.
- **What to do instead**: Run `/launch-tier` to classify the release and define positioning before launch.
- **Source**: Lauchengco (Loved)

### 9. Ship Without Measuring
- **Description**: Deploying without defined success metrics. No way to know if the launch worked.
- **Detection rule**: `canvas/north-star.yml` input metrics undefined or not tracked post-launch.
- **What to do instead**: Define what success looks like BEFORE launch. Set up measurement. Review metrics post-launch.
- **Source**: North Star Framework, Gilad (Evidence Guided)

### 10. Dark Pattern Marketing
- **Description**: Using behavioral science to manipulate users rather than help them make good decisions.
- **Detection rule**: Design patterns that exploit cognitive biases against user interest (confirmshaming, hidden costs, forced continuity, misdirection). `/service-check` Principle 12 ("Encourages right behaviors") catches this during service quality review.
- **What to do instead**: Use behavioral insights to HELP users (social proof for good choices, framing that clarifies value, anchoring that contextualizes pricing fairly).
- **Source**: Shotton (ethical application of behavioral science)

### 11. Audience of One
- **Description**: Positioning based on the team's assumptions about the market without any external validation.
- **Detection rule**: No buyer personas validated with real buyers. No win/loss analysis. Go-to-market strategy based entirely on internal opinions.
- **What to do instead**: Validate positioning with actual target customers. Conduct win/loss analysis. Test messaging before scaling.
- **Source**: Lauchengco (Loved), Kahneman (false consensus effect)

## Strategic Anti-Patterns (Systems Thinking — Senge)

These are systemic organizational traps from Senge's "The Fifth Discipline." They manifest at L1/L2 strategic scales and are harder to detect than tactical anti-patterns because they feel like rational responses in the moment.

### 13. Fixes That Fail
- **Description**: A fix addresses symptoms but creates unintended side effects that eventually make the original problem worse. The fix becomes the new problem.
- **Detection rule**: The same problem recurs after being "fixed." Each fix is bigger than the last. Side effects appear in related systems.
- **Examples**: Adding more process to fix quality issues (slows delivery, causes shortcuts). Using AI to speed up code generation without improving review capacity (creates bigger review backlog). Adding more meetings to fix communication problems (reduces time for actual work).
- **What to do instead**: Map the full causal loop before fixing. Ask "What are the second-order effects of this fix?" Use `/devils-advocate` to challenge the proposed solution. Check if the "fix" appeared in a previous retrospective as a problem.
- **Source**: Senge (The Fifth Discipline)

### 14. Shifting the Burden
- **Description**: A quick symptomatic fix undermines the motivation to develop a fundamental solution. Over time, the fundamental solution atrophies while dependence on the symptomatic fix grows.
- **Examples**: Using AI to paper over broken processes instead of fixing the root cause. Relying on heroic individuals instead of building systemic capability. Using workarounds instead of fixing the platform.
- **Detection rule**: The same workaround is applied repeatedly. The fundamental capability (testing, architecture, process) degrades over time. Team says "we'll fix it properly later" but never does.
- **What to do instead**: Identify the fundamental solution and invest in it, even if slower. Time-box the symptomatic fix with an explicit payback plan (see escape-hatch.md). Track workaround frequency as a health signal.
- **Source**: Senge (The Fifth Discipline)

### 15. Limits to Growth
- **Description**: A reinforcing process of growth hits a balancing constraint that slows or reverses growth. The natural response (push harder on the growth engine) makes things worse because the constraint is the bottleneck, not the engine.
- **Examples**: Shipping features faster but degrading quality until users churn. Scaling the team but not the architecture, creating coordination overhead. Growing the product surface area without growing support/docs/onboarding.
- **Detection rule**: Growth metrics plateau or reverse despite increased effort. BVSSH dimensions diverge (Sooner improving while Better/Safer/Happier decline). DORA lead time increases as team size increases.
- **What to do instead**: Identify the limiting factor (the constraint) and address it directly. Apply Theory of Constraints Five Focusing Steps (Goldratt). Don't push harder on the growth engine — relieve the constraint.
- **Source**: Senge (The Fifth Discipline), connects to Goldratt (ToC)

### 16. Eroding Goals
- **Description**: When a gap exists between the goal and reality, the team lowers the goal instead of improving performance. Standards gradually erode.
- **Examples**: Relaxing test coverage requirements because "we're behind schedule." Accepting increasingly longer lead times as "normal." Reducing accessibility requirements for "just this release." Lowering DORA targets after missing them.
- **Detection rule**: Goals/targets trend downward over successive reviews. Definition of Done items are waived "just this once" repeatedly. "Good enough" replaces "meets the standard."
- **What to do instead**: Hold the standard. Flex scope (MoSCoW), not quality. If a standard can't be met, investigate why — the answer is usually a systemic constraint, not an unrealistic standard.
- **Source**: Senge (The Fifth Discipline)

### 17. Test-Last Development (Delivery)
- **Description**: Writing all code first, then adding tests as an afterthought -- or not at all. Both Mycelium pilot projects exhibited this pattern.
- **Detection rule**: Test files created in a separate commit after source files. Or: source files exist with no corresponding test files at delivery completion.
- **What to do instead**: Write tests first (TDD) or at minimum alongside implementation. The G-V7 guardrail requires tests to exist before delivery completion (REVIEW).
- **Source**: Beck (XP/TDD), Forsgren (Accelerate -- test automation is a key capability), both Mycelium pilot post-mortems

## Leaf Lifecycle Anti-Patterns

### 1. Orphaned Leaf
- **Description**: A solution leaf has Four Risks assessment but no ICE score (or vice versa). The pipeline was started but not completed.
- **Detection rule**: `canvas/opportunities.yml` contains a solution with `four_risks` populated but `ice_score` empty, or `ice_score` populated but `four_risks` empty.
- **What to do instead**: Complete the pipeline. Four Risks → ICE → assumptions. Never score without risk assessment; never assess without scoring.
- **Source**: Torres (CDH), Gilad (Evidence Guided), Mycelium leaf lifecycle

### 2. Perspective Skip
- **Description**: A theory gate was passed without all three trio perspectives (product/design/engineering) documented. One or more perspectives were silently omitted.
- **Detection rule**: Gate check log has fewer than 3 perspective entries. Or a perspective is missing without an explicit "N/A: [reason]" justification.
- **What to do instead**: Every gate check must state all three perspectives. Omission requires explicit justification. See `engine/perspective-resolution.md`.
- **Source**: Torres (Product Trio), Cagan (Empowered)

### 3. Zombie Solution
- **Description**: An archived solution is still referenced by an active GIST entry. The GIST idea points to a dead leaf.
- **Detection rule**: `canvas/gist.yml` has an idea with `source_leaf_id` that appears in `canvas/archived-solutions.yml`.
- **What to do instead**: When archiving a leaf, also shelve or kill the corresponding GIST idea. `/canvas-health` should flag zombie references.
- **Source**: Mycelium leaf lifecycle

### 4. Implicit Handoff
- **Description**: Transition between leaf lifecycle phases without an explicit artifact and gate check. The leaf "jumped" from OST to delivery without the intermediate steps.
- **Detection rule**: GIST idea has no `source_leaf_id`. Service entry has no `gist_id`. Threat model has no `solution_id`. Any missing link in the cross-reference chain.
- **What to do instead**: Every lifecycle phase transition produces an artifact and checks a gate. See `engine/leaf-lifecycle.md` for the complete chain.
- **Source**: Mycelium leaf lifecycle

### 5. Score-Only Discard
- **Description**: A leaf was discarded solely based on its ICE score without checking if a different user segment would benefit from it.
- **Detection rule**: `canvas/archived-solutions.yml` entry has `segments_checked` with only one segment, and `reason` is `low-ice-score`.
- **What to do instead**: Before discarding for low ICE, evaluate whether the solution serves a different segment where it might score higher. See `engine/leaf-lifecycle.md` Discard Decision Rules.
- **Source**: Torres (CDH — solutions serve different user needs), Mycelium leaf lifecycle

### 6. Perspective Suppression
- **Description**: Resolving a trio conflict by ignoring a perspective entirely rather than using the perspective resolution framework. Common forms: "Engineering will figure it out" (suppresses feasibility), "Users will learn" (suppresses usability), "We'll find the users later" (suppresses value), "Legal won't notice" (suppresses viability).
- **Detection rule**: Decision log entry shows a perspective conflict resolved with fewer than 3 perspectives documented. Or gate check has a missing perspective without explicit "N/A: [reason]" justification.
- **What to do instead**: Use the perspective resolution framework (`engine/perspective-resolution.md`). If a perspective is overridden, document why with evidence in the decision log and tag it as a risk to monitor.
- **Source**: Torres (Product Trio), Cagan (Empowered), Mycelium perspective resolution framework

## Cognitive & Drift Anti-Patterns

These patterns emerge from the human-AI collaboration dynamic itself. They are subtle because they feel like efficiency — but they erode the quality of decisions over time.

### 1. Cognitive Offloading Loop
- **Description**: The better the agent performs, the less sharply the human thinks. User prompts become progressively shorter and more abstract. Canvas updates decrease in specificity. Confidence values increase without new evidence. The human delegates not just execution but *judgment* to the agent.
- **Detection rule**: (1) User prompts shrinking in specificity within a session. (2) Canvas fields updated with generic language ("improved based on feedback") rather than specific evidence. (3) Confidence increases without corresponding new evidence entries. (4) Human stops questioning agent recommendations.
- **What to do instead**: Periodically surface this warning: "Your last 3 prompts have been increasingly abstract. Want to pause and articulate what specific evidence would change your mind?" Require evidence citations for every confidence increase. Use `/devils-advocate` to force critical engagement.
- **Source**: aiops3000 ("Metadata Is the New Code"), Kahneman (System 1 autopilot), Raschka ("context quality = model quality")

### 2. Knowledge Reconstruction Tax
- **Description**: The agent re-reads the same context files across multiple sessions without changes. The human re-explains the same domain concepts each session. Both waste turns reconstructing knowledge that should be externalized and persistent.
- **Detection rule**: (1) Same files read in pre-task protocol with no changes between sessions. (2) User messages contain domain explanations that already exist (or should exist) in canvas files. (3) Agent asks questions whose answers are already in the canvas but not found because of poor indexing.
- **What to do instead**: After any session where domain knowledge is explained verbally, capture it in the appropriate canvas file or corrections entry. Run `/canvas-health` to identify gaps between what the agent needs and what the canvas contains. Use auto-memory for agent-user patterns, project memory for domain knowledge.
- **Source**: aiops3000 ("retrieval tax"), Karpathy (knowledge base maintenance), Raschka (stable prefix design)
