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
   - Any GATED item fails = **BLOCKED** (list specific blockers with suggested skills)
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

When transitioning from Deliver to Complete, run this checklist. Items marked `GATED` block progression. Items marked `PROMPTED` are asked but don't block.

### Auto-Checked (Machine Verifiable)

**Testing (G-V7 GATED)**:
- Check: Do test files exist? (glob for *.test.*, *.spec.*, Tests/*, __tests__/*)
- If no tests AND project has source files: **GATE FAILED**
- Message: "No tests found. Tests must exist before marking delivery complete. Run /reflexion to add tests."
- If tests exist: run them and verify they pass

**Type Safety (GATED for typed languages)**:
- Check: If tsconfig.json, *.swift, *.cs, go.mod, Cargo.toml detected: run type checker
- If type errors: **GATE FAILED**

**Linting (GATED if linter detected)**:
- Check: If linter config exists (.eslintrc, biome.json, .swiftlint.yml, ruff.toml): run it
- If lint errors: **GATE FAILED**

**Secrets (G-S1 BLOCKED)**:
- Check: Scan all src/ files for secret patterns (same as gate.sh)
- If secrets found: **GATE FAILED**

### Delivery-Type Dependent (from canvas-guidance.yml)

**For user_facing work (G-V2, G-V8, G-V9 GATED)**:
- Check: Has services.yml been assessed? (count of "not-assessed" < 15)
- If all 15 are "not-assessed": **GATE FAILED** -- "Run /service-check before completing."
- Check: Has accessibility been considered? (any evidence of a11y work)
- If no evidence: **GATE FAILED** -- "Run /a11y-check for user-facing work."

**For api_service or permission_requiring work (G-S2 GATED)**:
- Check: Does threat-model.yml have components listed?
- If empty: **GATE FAILED** -- "Run /threat-model for work that handles data or requires permissions."

**For data-handling work (G-S3 GATED)**:
- Check: Does privacy-assessment.yml have principles assessed?
- If all "not-assessed" and product handles user data: **GATE FAILED** -- "Run /privacy-check."

### Always Required (GATED)

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
- **GATED**: Must answer all 5 (even briefly) before completing

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
