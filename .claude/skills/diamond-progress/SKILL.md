---
name: diamond-progress
description: "Use to progress a diamond from one phase to the next. Runs all required theory gate checks and validates evidence."
---

# Diamond Progress Skill

Progress a diamond through phases with full theory gate validation.

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

7. **Decision**:
   - All gates pass + confidence met + approval (if needed) = **PROGRESS**
   - Any gate fails = **BLOCKED** (list specific blockers)
   - Confidence below threshold = **NEEDS EVIDENCE** (list what would help)

8. **If progressing**:
   - Update diamond state in active.yml.
   - Log transition in decision-log.md.
   - Update product-journal.md.
   - Identify if child diamonds should be spawned.
   - **Capture learnings**: "This phase is complete. Anything worth capturing?"
     - Draft corrections.md entry if mistakes were made
     - Draft patterns.md entry if a reusable pattern was discovered
     - Draft delivery-journal.md entry if this was a delivery phase
     - Present drafts to user for confirmation before saving

9. **If blocked or needs evidence**:
   - Report in plain language: "Can't progress yet because [reason in plain language]."
   - List each failed gate with its suggested skill: "Run `/threat-model` to satisfy the Security Gate."
   - Do not progress. Stay in current phase.

10. **Always communicate in plain language**:
    - Use status-translations.md for all state descriptions
    - Include contextual confidence explanation (not just the number)
    - Suggest specific skills for any gaps found

## Theory Citations
- Torres: Evidence requirements
- Cagan: Four risks
- Christensen: JTBD validation
- Snowden: Cynefin classification
- Shotton/Kahneman: Bias mitigation
- OWASP/STRIDE: Security gates
- GDPR/PbD: Privacy gates
- Smart: BVSSH
- Downe: Service quality
- Forsgren: DORA metrics
