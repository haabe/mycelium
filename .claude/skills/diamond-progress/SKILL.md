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
     b. Evaluate pass criteria against available evidence.
     c. Record Pass / Fail / Insufficient Evidence.
     d. If Fail: document what is missing and what action would resolve it.

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
   - Update diamond state.
   - Log transition in decision-log.md.
   - Update product-journal.md.
   - Identify if child diamonds should be spawned.

9. **If blocked or needs evidence**:
   - Recommend specific next actions.
   - Do not progress. Stay in current phase.

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
