---
name: diamond-progress
description: "Progress a diamond from one phase to the next. Runs all required theory gate checks, validates evidence, and at Deliver->Complete runs the executable Definition of Done checklist."
---

# Diamond Progress Skill

Progress a diamond through phases with full theory gate validation. At delivery completion, runs an executable checklist that GATES progression.

## Workflow

1. **Identify transition**: From [current phase] to [next phase] at [scale].

2. **Run all required theory gates** (per theory-gates.md transition matrix):
   - For each gate:
     a. State the gate name and source theory.
     b. **Surface the suggested skill**: "Run `/skill-name` to satisfy this gate."
     c. Evaluate pass criteria against available evidence.
     d. Record Pass / Fail / Insufficient Evidence.
     e. If Fail: document what is missing, recommend the skill to run, and do NOT proceed.

3. **Calculate confidence**:
   - Apply scoring rules from confidence-thresholds.yml.
   - Compare to threshold for this scale.

4. **Check human approval requirement**:
   - Per confidence-thresholds.yml, is human approval required/recommended/optional?
   - If required: present assessment and wait for approval.

5. **Run bias check**: Execute bias-check for the current stage.

6. **Run corrections check**: Review corrections.md for relevant entries.

7. **If transition is Deliver -> Complete: RUN EXECUTABLE DoD CHECKLIST** (see below)

8. **Decision**:
   - All gates pass + confidence met + approval (if needed) + DoD pass (if delivery) = **PROGRESS**
   - Any REVIEW item fails = **blocked** (list specific blockers with suggested skills)
   - Confidence below threshold = **NEEDS EVIDENCE** (list what would help)

9. **If progressing**:
   - Update diamond state in active.yml.
   - Log transition in decision-log.md.
   - Update product-journal.md.
   - Identify if child diamonds should be spawned.
   - **Capture learnings** (see Learning Capture section below)

10. **If blocked or needs evidence**:
    - Report in plain language: "Can't mark this done yet because [reason]."
    - List each failed item with its suggested skill
    - Do not progress. Stay in current phase.

11. **Always communicate in plain language**:
    - Use status-translations.md for all state descriptions
    - Include contextual confidence explanation
    - Suggest specific skills for any gaps

---

## Executable Definition of Done (Deliver -> Complete ONLY)

When transitioning from Deliver to Complete, run this checklist. Items marked `REVIEW` block progression. Items marked `PROMPTED` are asked but don't block.

### Auto-Checked (Machine Verifiable)

**Testing (G-V7 REVIEW)**:
- Check: Do test files exist? (glob for *.test.*, *.spec.*, Tests/*, __tests__/*)
- If no tests AND project has source files: **GATE FAILED**
- Message: "No tests found. Tests must exist before marking delivery complete. Run /reflexion to add tests."
- If tests exist: run them and verify they pass

**Type Safety (REVIEW for typed languages)**:
- Check: If tsconfig.json, *.swift, *.cs, go.mod, Cargo.toml detected: run type checker
- If type errors: **GATE FAILED**

**Linting (REVIEW if linter detected)**:
- Check: If linter config exists (.eslintrc, biome.json, .swiftlint.yml, ruff.toml): run it
- If lint errors: **GATE FAILED**

**Secrets (G-S1 BLOCK)**:
- Check: Scan all src/ files for secret patterns (same as gate.sh)
- If secrets found: **GATE FAILED**

### Delivery-Type Dependent (from canvas-guidance.yml)

**For user_facing work (G-V2, G-V8, G-V9 REVIEW)**:
- Check: Has services.yml been assessed? (count of "not-assessed" < 15)
- If all 15 are "not-assessed": **GATE FAILED** -- "Run /service-check before completing."
- Check: Has accessibility been considered? (any evidence of a11y work)
- If no evidence: **GATE FAILED** -- "Run /a11y-check for user-facing work."
- Check: Has usability been evaluated? (Nielsen's 10 heuristics via /usability-check)
- If no evidence: **GATE FAILED** -- "Run /usability-check for user-facing interfaces." (G-V10)

**For api_service or permission_requiring work (G-S2 REVIEW)**:
- Check: Does threat-model.yml have components listed?
- If empty: **GATE FAILED** -- "Run /threat-model for work that handles data or requires permissions."

**For data-handling work (G-S3 REVIEW)**:
- Check: Does privacy-assessment.yml have principles assessed?
- If all "not-assessed" and product handles user data: **GATE FAILED** -- "Run /privacy-check."

### Always Required (REVIEW)

**Decision log (G-P4)**:
- Check: Does decision-log.md have an entry for this delivery?
- If no entry since diamond was created: **GATE FAILED** -- "Log the delivery decision."

**BVSSH Quick-Check (Smart -- Fix 6)**:
- Prompt the user/agent with a lightweight 5-question check:
  - "Better: Did quality improve or degrade with this delivery?"
  - "Value: Did we deliver actual user value?"
  - "Sooner: Was flow efficient? Any unnecessary delays?"
  - "Safer: Did we maintain security and trust?"
  - "Happier: How is satisfaction (team or personal)?"
- Record in bvssh-health.yml assessment_history
- **REVIEW**: Must answer all 5 (even briefly) before completing

### Prompted (Not Blocking)

**Delivery journal (PROMPTED)**:
- "What was built? What technical decisions were made? What surprised you?"
- Auto-draft entry from canvas diff if possible
- Present to user for confirmation

**Patterns (PROMPTED)**:
- "Did you discover any reusable patterns? I'll draft for patterns.md."
- Check corrections.md for entries logged during this diamond -- suggest generalizing any

**Retrospective (PROMPTED)**:
- "What went well? What didn't? What to change next time?"
- Suggest /retrospective for deeper review

---

## Non-Progression Paths: Pivot, Park, Kill

Not every diamond makes forward progress. Sometimes the right move is to reframe, pause, or abandon. `/diamond-progress` handles these paths too, via subcommands:

- `/diamond-progress pivot` — reframe the diamond's scope, audience, or JTBD with new evidence
- `/diamond-progress park` — mark the diamond as inactive-pending-conditions
- `/diamond-progress kill` — abandon with a documented reason

All three are **sanctioned exits** from a stuck diamond. They are not failure modes — they are the system working correctly when evidence tells you the current direction is wrong.

Addresses dogfood report finding T5: "Stop-the-diamond pattern has no escape valve."

### Pivot (reframe with new evidence)

Use when evidence invalidates the current framing but the underlying need is still valid. Example: macos-fileviewer pivoted from "replace QuickLook for all devs" to "serve terminal-resistant devs specifically" after mocked-persona findings.

**Workflow**:
1. State the invalidating evidence (what did we learn that broke the old framing?)
2. Propose the new framing (scope change, audience change, JTBD refinement)
3. Log decision in decision-log.md with:
   - Original framing
   - Invalidating evidence
   - New framing
   - Theory: which framework informed the pivot (Torres "evidence-guided", Cagan "value risk", etc.)
   - Confidence delta (the pivot should REDUCE confidence initially — you have less evidence for the new framing)
4. Update `diamonds/active.yml`:
   - Phase often regresses (e.g., Define → Discover) to gather evidence on the new framing
   - Confidence resets to match the new framing's evidence level
   - Add `pivot_history` entry listing old and new framings
5. Update relevant canvas files (purpose.yml, jobs-to-be-done.yml, opportunities.yml)
6. Do NOT archive the old framing — keep it as a pivot_history entry so future agents can see the learning

### Park (inactive-pending-conditions)

Use when the diamond cannot progress right now but may be revisitable later. Example: "park until I have time to do real user interviews" or "park until upstream dependency X ships."

**Workflow**:
1. State the blocking condition(s) — what would un-park this?
2. Log decision in decision-log.md with:
   - Reason for parking
   - Conditions for resuming
   - Expected timeline (best guess)
   - Theory: Goldratt ToC (constraint waiting on resolution) or Torres (evidence insufficient, acceptable to pause)
3. Update `diamonds/active.yml`:
   - State → `parked`
   - Add `parked_reason`, `parked_at`, `resume_conditions` fields
4. Parked diamonds remain in active.yml but do not count against WIP limits
5. `/feedback-review` and `/diamond-assess` surface parked diamonds with their resume conditions at session start

### Kill (abandon with documented reason)

Use when the diamond cannot be rescued via pivot or park. Example: the opportunity turned out to be imaginary (no real users, no demand), or the solution space has been exhausted, or the project direction has fundamentally changed.

**Workflow**:
1. State the reason for killing — what evidence makes this diamond dead?
2. Confirm with user (kill is destructive) — present the reason, ask for explicit confirmation
3. Log decision in decision-log.md with:
   - Final state of the diamond
   - Reason for kill
   - Alternatives considered (why not pivot, why not park?)
   - Theory: Kahneman (sunk cost fallacy — kill is correct when evidence says continuing is worse than stopping)
   - What we learned (the learning is the deliverable for a killed diamond)
4. Update `diamonds/active.yml`:
   - Move to `killed_diamonds` section (NOT deleted — canvas data is preserved)
   - Add `killed_at`, `killed_reason`, `learnings` fields
5. Do NOT delete canvas artifacts associated with the killed diamond — they are learning for future work
6. Capture the learning in `memory/patterns.md` and `memory/corrections.md` as appropriate

### Dogfood Mode Modifier (from canvas-guidance.yml)

When the project has `dogfood: true` set, stop conditions become Mycelium learnings rather than project deaths. In dogfood mode, a killed diamond generates a dogfood report entry in `.claude/evals/dogfood-reports/` instead of only being logged as a project kill. The framework gap caught is the real deliverable.

---

## Learning Capture (After Every Phase Transition)

After EVERY successful transition (not just Deliver->Complete):

1. **Corrections**: "Were any mistakes made during this phase? I'll draft a corrections.md entry."
2. **Patterns**: "Did anything work particularly well that's worth reusing?"
3. **Delivery journal** (delivery phases only): "What implementation decisions and learnings should be recorded?"
4. **Product journal** (discovery phases only): "What insights changed our understanding?"

Draft entries for the user. Present for confirmation before saving. This captures learning at the moment of discovery, not retrospectively.

---

## Theory Citations
- Torres: Evidence requirements
- Cagan: Four risks
- Christensen: JTBD validation
- Snowden: Cynefin classification
- Shotton/Kahneman: Bias mitigation
- OWASP/STRIDE: Security gates
- GDPR/PbD: Privacy gates
- Smart: BVSSH (now at completion, not just monthly)
- Downe: Service quality (gated for user-facing work)
- Forsgren: DORA metrics + testing requirements
- EU AI Act: Regulatory classification (L3-L5)
