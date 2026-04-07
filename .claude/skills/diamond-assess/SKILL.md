---
name: diamond-assess
description: "Use to evaluate the current state of a diamond. Checks theory gates, confidence levels, and recommends next action."
---

# Diamond Assess Skill

Evaluate current diamond state and recommend next action.

## Workflow

1. **Identify the diamond**: Which diamond (ID, scale, phase) is being assessed?

2. **Gather current state**:
   - Current phase (Discover/Define/Develop/Deliver)
   - Evidence collected so far
   - Confidence score with breakdown
   - Blockers or risks

3. **Check theory gates for next transition**:
   - Reference theory-gates.md for the current transition
   - Evaluate each applicable gate: Pass / Fail / Insufficient Evidence
   - Document what is missing for failed gates

4. **Check confidence threshold**:
   - Reference confidence-thresholds.yml for the current scale
   - Compare current confidence to required threshold
   - Identify what would increase confidence

5. **Check for anti-patterns**:
   - Reference anti-patterns.md
   - Flag any detected failure modes

6. **Check corrections.md**:
   - Any relevant past mistakes to avoid?

7. **Recommend next action**:
   - If all gates pass and confidence meets threshold: recommend transition to next phase
   - If gates fail: recommend specific actions to address failures
   - If confidence is low: recommend evidence-gathering activities
   - If anti-patterns detected: recommend corrective actions
   - If regression needed: recommend which phase to return to and why

## Output

```
## Diamond Assessment: [ID]
- Scale: [L0-L5]
- Phase: [current]
- Confidence: [score] / [threshold]

### Theory Gate Status
| Gate | Status | Notes |
|------|--------|-------|
| ... | Pass/Fail/N/A | ... |

### Anti-Patterns Detected
- [any detected patterns]

### Recommendation
[specific next action with rationale]
```

## Theory Citations
- Torres: Evidence-based progression
- Gilad: Confidence scoring
- Cagan: Four risks assessment
- Snowden: Cynefin classification
