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

### 7. Consistency-as-Evidence
- **Description**: Constructing a causal chain (X → Y → Z) or generalization where ≥1 link rests on observational consistency rather than verified attribution. Treating "X is consistent with hypothesis H" as "X is evidence for H," without isolating the cause. Distinct from confirmation bias (#3): confirmation bias is an attention-direction failure (seeking evidence that confirms); consistency-as-evidence is an attribution failure (misclassifying evidence already in hand).
- **Detection rule**: A claim of structural significance (X causes Y; A excludes B; the framework has shape S) rests on multiple data points, ≥1 of which is consistency-only — i.e., the data is compatible with multiple explanations and the cause has not been demonstrably isolated. Or: a generalization claims to apply broadly but rests on N=1 (or N=2 where one is consistency-only).
- **Catalogued sub-classes** (8+ instances across both repos as of 2026-05-23 — full instance log in `.claude/memory/cluster-instances.md#consistency-as-evidence`):
  - **(a) canvas-write** — agent writes a claim into a canvas file conflating consistency with attribution. Closed by behavioral-enforcement layer v0.22.0 (Read-before-Write, Validator Check 31, /diamond-assess Step 3).
  - **(b) conversational** — agent confirms a behavior claim asserted in dialog without challenging the evidence source. Pending sub-graduation.
  - **(c) self-application** — agent constructs the chain in its OWN analysis even after warning against the same failure mode for users in the same response.
  - **(d) graduation-velocity** — multiple framework graduations in one session where the genuine lived-friction trigger extends into adjacent graduations via consistency-with-the-running-playbook rather than per-graduation attribution. Graduated 2026-05-10 to `engine/version-discipline.md` per-graduation attribution requirement.
  - **(e) trust-without-verification** *(broadened 2026-05-23 from subagent-output-verification)* — agent propagates a claim from any external source (subagent, validator wrapper text, tool result, dialog assertion, ranked-list summary) without running the underlying tool or tracing to the source. Original surface (subagent-output-verification) was the 2026-05-11 instance; broadened after 2026-05-23 EXE001 instance where validator's "pre-existing tech debt" wrapper claim was propagated without running ruff. Convention shipped 2026-05-23 to CLAUDE.md Communication Rules: every claim-propagation must include `Verified:`, `Cited:`, `Per [source]:`, or explicit `Unverified` form. Pending mechanism graduation (script enforcement) on 2nd post-convention instance.
  - **(f) window-framing-inconsistency** — agent applies different time windows to different metrics within a single synthesis, picking framings that produce the cleaner narrative. Pending graduation; agent-protocol fix logged.
  - **(g) implicit-causal-link** *(NEW 2026-05-23)* — agent labels evidence-gated items as date-deferred (implicit causal link between a date and an unblock event where the date is observationally consistent but not interventionally causal). Variant: temporal-binarization (collapsing a multi-day pre-event window into "now vs after-event"). Convention shipped 2026-05-23 to CLAUDE.md Communication Rules: every deferral/threshold statement must include a `Gated by:` clause (or equivalent canvas/natural-prose form) naming the actual unblock event. Pending mechanism graduation (script enforcement) on 2nd post-convention instance.
  - **(h) write-narration-verification** *(graduated v0.39.18, surface expanded v0.44.0)* — the symmetric counterpart to (a) canvas-write: after a write, the agent narrates "updated / wrote / refreshed [canvas]" when only *some* of the fields its MANDATORY specifies changed (typically only `_meta.last_validated` / a freshness stamp), conflating "I touched the file" with "the value fields now hold the claimed state." Worked failures 2026-06-05: #18 `/dora-check` narrated "updated" with value fields unchanged; #19 `/retrospective` left a cycle-history aggregate un-propagated. **Mechanism (not pending — shipped):** the `## Postflight: Verify-After-Write` preamble (re-read the value fields, confirm they changed, before narrating done), enforced by **Check 42** on every skill that mandates a multi-field canvas write. The verify-after-write half of Read-before-Write (Check 31).
- **What to do instead**: Before publishing any causal claim or generalization, label each piece of supporting evidence by attribution type — *cleanly-attributed* (the cause was demonstrably driving the effect), *consistency-only* (the data is compatible with multiple explanations), or *unrelated*. If ≥1 link is consistency-only, mark the chain provisional and identify what attribution evidence is missing. If N=1, state the data point and propose the hypothesis but do not publish a structural conclusion until N≥2 with attribution. **For sub-class g specifically**: when stating any deferral, threshold, or date-based recommendation (including pushback statements declining proposed work), name the gate explicitly — see CLAUDE.md Communication Rules `Gated by:` convention. Apply all checks to your own analysis pre-publish, not after the user catches it.
- **Graduation philosophy (load-bearing, 2026-05-09)**: This class is almost impossible to fully avoid — humans don't write or tell absolutely everything (Grice's maxim of quantity; Sperber & Wilson relevance theory). Speakers compress; listeners interpolate; the interpolation IS the failure surface. The mechanism cannot be "stop interpolating" (cognitively impossible at scale). The mechanism must be **make the interpolation visible so it can be checked** — surface the inferred bridge as a flag for the human, not as a claim the agent acts on. Different mechanism class than anti-patterns where the answer is "stop doing X." This distinguishes AP#7-shaped graduations from the rest of the catalog — graduations are conventions and visibility-mechanisms, not blocking rules.
- **Source**: Pearl (causal inference — observational vs interventional evidence); Kahneman, *Thinking Fast and Slow* (2011) ch. 20 — *Illusion of Validity*, the established academic name for the same phenomenon (over-confidence in judgments built from internally-consistent but causally-unverified evidence); Grice (maxim of quantity); Sperber & Wilson (relevance theory). Mycelium recurrence corrections.md 2026-04-30 (over-scoping cluster), 2026-05-03 (sharper-framing anchoring), 2026-05-09 (verbosity-attribution gap, private-channel observation), 2026-05-23 (implicit-causal-link sub-class). Graduated 2026-05-09; sub-class catalog extended 2026-05-23.

### 8. Stale State Read
- **Description**: A script, validator, or check reads project state from a file *that the same operation is about to replace or has just modified*, producing nominally-correct output against a stale source. Mechanism passes silently when it should catch the divergence. Same epistemic shape as Sycophancy (#6) — output looks valid against the wrong reference — but the failure surface is tooling, not gate language.
- **Detection rule**: A script defaults to reading state from a hardcoded local path (`Path(__file__).resolve().parent.* / "state.yml"`) without supporting an explicit `--source=<path>` argv override. Or: an upgrade/sync flow runs validation/parsing against the local copy *before* replacing it with the upstream copy. Any pattern where the question "which version of state is being read here?" has more than one possible answer at runtime.
- **What to do instead**: State-reading scripts must accept an explicit-source parameter (e.g., `parse_manifest.py --manifest=<path>`). Sync/upgrade flows must read upstream state from the temp/upstream location for the operations that consume it (e.g., `UPSTREAM_MANIFEST="$TEMP_DIR/.claude/manifest.yml"` rather than `.claude/manifest.yml`). Validators that scan files must scan the post-upgrade state, not pre-upgrade. When in doubt, run the operation twice — if the second run produces different output than the first, the first read was stale.
- **Source**: Mycelium recurrence corrections.md 2026-04-28 (upgrade.sh harness hardcoded), 2026-05-03 (upgrade.sh top_level missed AGENTS.md), 2026-05-04 (validate_canvas.py ID-uniqueness gap), 2026-05-04 (upgrade.sh manifest stale-read). Graduated 2026-05-09. Ohno (jidoka — build the test that catches the failure, don't rely on memory).

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

### 7b. Undocumented Architecture Decisions
- **Description**: Significant architectural choices (framework selection, infrastructure, integration patterns) made without recorded rationale. Future developers reverse-engineer the "why" from code.
- **Detection rule**: Multi-domain solution or high feasibility risk but `docs/adr/` is empty or missing. Code comments explain "we chose X over Y" but no formal decision record.
- **What to do instead**: Run `/delivery-bootstrap` to scaffold `docs/adr/`. Document each significant decision in Nygard format (Context/Decision/Consequences) before or during implementation.
- **Source**: Nygard (Architecture Decision Records)

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
- **Detection rule**: Design patterns that exploit cognitive biases against user interest (confirmshaming, hidden costs, forced continuity, misdirection). `/service-check` Principle 12 ("Encourages right behaviors") catches this during service quality review. **Turned inward**: the persuasion axioms in `haabe/ux-axioms-mcp` (anchoring, scarcity, social proof, loss aversion, decoy, framing) are dual-use — deploying them in the *agent's own output* to steer the user toward what the framework wants, rather than to help them decide, is this same anti-pattern aimed at the framework's user (see `${CLAUDE_PLUGIN_ROOT}/harness/design-principles.md` → persuasion axioms).
- **What to do instead**: Use behavioral insights to HELP users (social proof for good choices, framing that clarifies value, anchoring that contextualizes pricing fairly).
- **Source**: Shotton (ethical application of behavioral science)

### 11. Audience of One
- **Description**: Positioning based on the team's assumptions about the market without any external validation.
- **Detection rule**: No buyer personas validated with real buyers. No win/loss analysis. Go-to-market strategy based entirely on internal opinions.
- **What to do instead**: Validate positioning with actual target customers. Conduct win/loss analysis. Test messaging before scaling.
- **Source**: Lauchengco (Loved), Kahneman (false consensus effect)

## Strategic Anti-Patterns (Systems Thinking — Senge)

These are systemic organizational traps from Senge's "The Fifth Discipline." They manifest at L1/L2 strategic scales and are harder to detect than tactical anti-patterns because they feel like rational responses in the moment.

### 12. Fixes That Fail
- **Description**: A fix addresses symptoms but creates unintended side effects that eventually make the original problem worse. The fix becomes the new problem.
- **Detection rule**: The same problem recurs after being "fixed." Each fix is bigger than the last. Side effects appear in related systems.
- **Examples**: Adding more process to fix quality issues (slows delivery, causes shortcuts). Using AI to speed up code generation without improving review capacity (creates bigger review backlog). Adding more meetings to fix communication problems (reduces time for actual work).
- **What to do instead**: Map the full causal loop before fixing. Ask "What are the second-order effects of this fix?" Use `/devils-advocate` to challenge the proposed solution. Check if the "fix" appeared in a previous retrospective as a problem.
- **Source**: Senge (The Fifth Discipline)

### 13. Shifting the Burden
- **Description**: A quick symptomatic fix undermines the motivation to develop a fundamental solution. Over time, the fundamental solution atrophies while dependence on the symptomatic fix grows.
- **Examples**: Using AI to paper over broken processes instead of fixing the root cause. Relying on heroic individuals instead of building systemic capability. Using workarounds instead of fixing the platform.
- **Detection rule**: The same workaround is applied repeatedly. The fundamental capability (testing, architecture, process) degrades over time. Team says "we'll fix it properly later" but never does.
- **What to do instead**: Identify the fundamental solution and invest in it, even if slower. Time-box the symptomatic fix with an explicit payback plan (see escape-hatch.md). Track workaround frequency as a health signal.
- **Source**: Senge (The Fifth Discipline)

### 14. Limits to Growth
- **Description**: A reinforcing process of growth hits a balancing constraint that slows or reverses growth. The natural response (push harder on the growth engine) makes things worse because the constraint is the bottleneck, not the engine.
- **Examples**: Shipping features faster but degrading quality until users churn. Scaling the team but not the architecture, creating coordination overhead. Growing the product surface area without growing support/docs/onboarding.
- **Detection rule**: Growth metrics plateau or reverse despite increased effort. BVSSH dimensions diverge (Sooner improving while Better/Safer/Happier decline). DORA lead time increases as team size increases.
- **What to do instead**: Identify the limiting factor (the constraint) and address it directly. Apply Theory of Constraints Five Focusing Steps (Goldratt). Don't push harder on the growth engine — relieve the constraint.
- **Source**: Senge (The Fifth Discipline), connects to Goldratt (ToC)

### 15. Eroding Goals
- **Description**: When a gap exists between the goal and reality, the team lowers the goal instead of improving performance. Standards gradually erode.
- **Examples**: Relaxing test coverage requirements because "we're behind schedule." Accepting increasingly longer lead times as "normal." Reducing accessibility requirements for "just this release." Lowering DORA targets after missing them.
- **Detection rule**: Goals/targets trend downward over successive reviews. Definition of Done items are waived "just this once" repeatedly. "Good enough" replaces "meets the standard."
- **What to do instead**: Hold the standard. Flex scope (MoSCoW), not quality. If a standard can't be met, investigate why — the answer is usually a systemic constraint, not an unrealistic standard.
- **Source**: Senge (The Fifth Discipline)

### 16. Test-Last Development (Delivery)
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
- **What to do instead**: Every gate check must state all three perspectives. Omission requires explicit justification. See `${CLAUDE_PLUGIN_ROOT}/engine/perspective-resolution.md`.
- **Source**: Torres (Product Trio), Cagan (Empowered)

### 3. Zombie Solution
- **Description**: An archived solution is still referenced by an active GIST entry. The GIST idea points to a dead leaf.
- **Detection rule**: `canvas/gist.yml` has an idea with `source_leaf_id` that appears in `canvas/archived-solutions.yml`.
- **What to do instead**: When archiving a leaf, also shelve or kill the corresponding GIST idea. `/canvas-health` should flag zombie references.
- **Source**: Mycelium leaf lifecycle

### 4. Implicit Handoff
- **Description**: Transition between leaf lifecycle phases without an explicit artifact and gate check. The leaf "jumped" from OST to delivery without the intermediate steps.
- **Detection rule**: GIST idea has no `source_leaf_id`. Service entry has no `gist_id`. Threat model has no `solution_id`. Any missing link in the cross-reference chain.
- **What to do instead**: Every lifecycle phase transition produces an artifact and checks a gate. See `${CLAUDE_PLUGIN_ROOT}/engine/leaf-lifecycle.md` for the complete chain.
- **Source**: Mycelium leaf lifecycle

### 5. Score-Only Discard
- **Description**: A leaf was discarded solely based on its ICE score without checking if a different user segment would benefit from it.
- **Detection rule**: `canvas/archived-solutions.yml` entry has `segments_checked` with only one segment, and `reason` is `low-ice-score`.
- **What to do instead**: Before discarding for low ICE, evaluate whether the solution serves a different segment where it might score higher. See `${CLAUDE_PLUGIN_ROOT}/engine/leaf-lifecycle.md` Discard Decision Rules.
- **Source**: Torres (CDH — solutions serve different user needs), Mycelium leaf lifecycle

### 6. Perspective Suppression
- **Description**: Resolving a trio conflict by ignoring a perspective entirely rather than using the perspective resolution framework. Common forms: "Engineering will figure it out" (suppresses feasibility), "Users will learn" (suppresses usability), "We'll find the users later" (suppresses value), "Legal won't notice" (suppresses viability).
- **Detection rule**: Decision log entry shows a perspective conflict resolved with fewer than 3 perspectives documented. Or gate check has a missing perspective without explicit "N/A: [reason]" justification.
- **What to do instead**: Use the perspective resolution framework (`${CLAUDE_PLUGIN_ROOT}/engine/perspective-resolution.md`). If a perspective is overridden, document why with evidence in the decision log and tag it as a risk to monitor.
- **Source**: Torres (Product Trio), Cagan (Empowered), Mycelium perspective resolution framework

## Measurement Anti-Patterns

### 1. Streetlight Effect
- **Description**: Optimizing what's measurable rather than what matters to users. Engineers (and agents) gravitate toward problems they can see — test pass rates, lint scores, latency p99 — without connecting them to user scenarios. The drunk man searches for his keys under the streetlight because "this is where the light is."
- **Detection rule**: (1) Optimization proposed without naming which user scenario benefits. (2) System metric improving but no corresponding improvement in user outcome. (3) Agent proposes technical improvement without referencing a canvas scenario or opportunity. (4) **Loop-extremity signature**: an autonomous minimize/maximize loop drives a proxy metric to an out-of-distribution extreme (e.g., frame time 88ms→2ms, allocations ~150K→500) with no out-of-band check on the property the metric proxies. Under optimization pressure the proxy↔target relationship that held in the normal regime silently breaks (Goodhart / Campbell's Law); the extremity is itself the tell.
- **What to do instead**: Before any optimization, state the user scenario: "This improves [scenario X] because [user impact Y]." If you can't name the scenario, question whether it matters. Draw a line from the technical problem to the "why" — the user scenario that necessitates it. **When an optimization loop produces an extreme or surprising win on a metric, treat the extremity itself as a signal to verify the proxied property out-of-band** — re-derive the target the metric stands in for; don't trust the number. Where the framework runs metric-targeted loops, prefer a train/test holdout split (see `/eval-runner run-split optimization|holdout`) as the structural Goodhart guard.
- **Source**: Hoskins (The Product-Minded Engineer, Ch9 — "Don't be the drunkard"); Goodhart's Law / Campbell's Law (proxy metric under optimization pressure). Loop-extremity clause graduated 2026-05-29 — see also the popular umbrella term "agent psychosis" (Hashimoto 2026, x.com/mitchellh/status/2060088112257372610); Mycelium prefers the sharper Goodhart/Streetlight framing. Scoping rationale + user override of the original evidence-gate in `harness/decision-log.md` 2026-05-29.

## Cognitive & Drift Anti-Patterns

These patterns emerge from the human-AI collaboration dynamic itself. They are subtle because they feel like efficiency — but they erode the quality of decisions over time.

### 1. Cognitive Offloading Loop
- **Description**: The better the agent performs, the less sharply the human thinks. User prompts become progressively shorter and more abstract. Canvas updates decrease in specificity. Confidence values increase without new evidence. The human delegates not just execution but *judgment* to the agent. The human-side complement of context-rot's agent-side recency drift: as the agent's effective focus narrows under context bloat, the human's prompting also narrows — both compounding toward shallow synthesis.
- **Detection rule**: (1) User prompts shrinking in specificity within a session. (2) Canvas fields updated with generic language ("improved based on feedback") rather than specific evidence. (3) Confidence increases without corresponding new evidence entries. (4) Human stops questioning agent recommendations.
- **What to do instead**: Periodically surface this warning: "Your last 3 prompts have been increasingly abstract. Want to pause and articulate what specific evidence would change your mind?" Require evidence citations for every confidence increase. Use `/devils-advocate` to force critical engagement.
- **Source**: aiops3000 ("Metadata Is the New Code"), Kahneman (System 1 autopilot), Raschka ("context quality = model quality"). Chroma "Context Rot" study (research.trychroma.com/context-rot, 2025) — empirical: as context grows past task-focused size, output quality degrades; this anti-pattern is the human-collaboration manifestation. See also `${CLAUDE_PLUGIN_ROOT}/harness/context-management.md` for the framework's structural defense layer.

### 2. Knowledge Reconstruction Tax
- **Description**: The agent re-reads the same context files across multiple sessions without changes. The human re-explains the same domain concepts each session. Both waste turns reconstructing knowledge that should be externalized and persistent. Structural failure mode of the lost-in-the-middle effect (Recency Bias in Context, `${CLAUDE_PLUGIN_ROOT}/harness/cognitive-biases.md`): when knowledge that *should* be retrieved from external memory gets re-derived from conversation context, the agent pays the retrieval tax AND inherits all the attention-budget costs of holding that derivation in-context.
- **Detection rule**: (1) Same files read in pre-task protocol with no changes between sessions. (2) User messages contain domain explanations that already exist (or should exist) in canvas files. (3) Agent asks questions whose answers are already in the canvas but not found because of poor indexing.
- **What to do instead**: After any session where domain knowledge is explained verbally, capture it in the appropriate canvas file or corrections entry. Run `/canvas-health` to identify gaps between what the agent needs and what the canvas contains. Use auto-memory for agent-user patterns, project memory for domain knowledge.
- **Source**: aiops3000 ("retrieval tax"), Karpathy (knowledge base maintenance), Raschka (stable prefix design). Liu et al. 2023 "Lost in the Middle" (arXiv:2307.03172) — peer-reviewed source for the U-curve attention effect that makes re-reading particularly costly. See `${CLAUDE_PLUGIN_ROOT}/harness/context-management.md` for the framework's coherent context-rot defense layer.

### 3. Eval Overfitting
- **Description**: After an eval reveals a gap, the agent encodes the correct answer directly into documentation or data annotations rather than fixing the underlying data or model. The eval passes but the documentation becomes contaminated with defensive qualifiers that serve the test, not the reader.
- **Detection rule**: (1) Documentation contains "NOT" qualifiers that reference specific test scenarios. (2) Data entries include negative framing ("this is NOT X") that answers an eval question rather than describing the entity. (3) Eval pass rate improves without corresponding data quality improvement.
- **What to do instead**: When an eval reveals a gap, fix the source data. If the data was wrong, correct it. If the eval question was poorly framed, fix the eval. Never annotate documentation to pass a test — that's Goodhart's Law in action.
- **Source**: Hoskins friction log (2026-04-25) — Drew caught the agent encoding "NOT the first commercial ICE" into data to pass an eval. Goodhart's Law (when the eval becomes the target, documentation ceases to be good documentation).

### 4. Negative Documentation
- **Description**: Defining things by what they are NOT rather than what they ARE. A defensive writing pattern where the agent anticipates objections and preemptively disclaims, resulting in documentation cluttered with negations that answer questions nobody asked.
- **Detection rule**: (1) Multiple "NOT" or "does not" qualifiers in entity descriptions. (2) Documentation that reads like a FAQ response rather than a reference. (3) Drew's test: "Saying what things are *not*, answering questions that future people won't be asking."
- **What to do instead**: State what something IS, with citations. Let the reader form their own questions. If a distinction is genuinely important (e.g., "compressed-charge cycle" vs "first commercial engine"), state the positive framing and let the data speak.
- **Source**: Hoskins friction log (2026-04-25) — recurring pattern flagged by Drew. Related to Eval Overfitting but broader — occurs even without eval pressure.

### 5. Gamified Discipline (Overjustification)
- **Description**: Bolting an *extrinsic* reward onto the framework's own discipline loop — points, badges, streaks, scores, "XP", leaderboards, or completion-percentage dopamine for passing gates, updating the canvas, or adhering to the protocol. The overjustification effect: once an activity that was intrinsically motivated (building good products, the competence of earning a sound decision) is rewarded extrinsically, the extrinsic token *crowds out* the intrinsic motivation. Discipline that felt like craftsmanship becomes box-ticking for the badge, and collapses the moment the badge stops mattering. The phrase "the agent earns the right to code" is itself reward-shaped — it must signal **mastery** (a competence bar cleared) and never decay into a **token** (a point scored). Distinct from Confidence Theater (#6, Confidence): that fakes the evidence; this corrupts the *motivation* even when the evidence is real.
- **Detection rule**: (1) A proposal to add scores/badges/streaks/leaderboards/XP to gates, skills, canvas updates, or "discipline adherence". (2) A gate or protocol step reframed as a reward-to-collect rather than a quality bar to clear. (3) Adherence framed as "keeping the streak alive" / "don't break the chain" rather than "this produces a better decision". (4) Any mechanism that would make a maintainer keep using the framework *for the token* rather than for the product outcome.
- **What to do instead**: Keep the gate's payoff intrinsic — the reward of a gate is a better product decision and the competence of having earned it; surface *why* it holds (autonomy + competence, per Self-Determination Theory — see `${CLAUDE_PLUGIN_ROOT}/harness/design-principles.md`). To motivate adherence, **remove friction** (Herzberg hygiene: a fast, quiet, false-positive-free validator) and **surface mastery**, never add tokens. The one place extrinsic / variable reward is a legitimate design lever is **end-user product design** (e.g., the Hook Model in `${CLAUDE_PLUGIN_ROOT}/skills/launch-tier/SKILL.md`, L5) — designing a habit *for users of the product being built*. Never point that lever at the maintainer's own discipline loop. If you catch yourself proposing gamification "to drive engagement with the framework," stop: engagement that needs a token isn't engagement with the work.
- **Source**: Deci & Ryan (Self-Determination Theory); Lepper, Greene & Nisbett (1973) — the original overjustification experiment; Deci, Koestner & Ryan (1999) meta-analysis: tangible extrinsic rewards reliably undermine intrinsic motivation for interesting tasks. Pink (*Drive*, 2009) — popular synthesis. Boundary with the Hook Model (Eyal) is deliberate: extrinsic reward is a tool for end-user habit design, a hazard for self-discipline design.
