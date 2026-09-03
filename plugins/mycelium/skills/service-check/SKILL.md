---
name: service-check
description: "Use to evaluate a service or feature against Downe's 15 principles of good services."
metadata:
  instruction_budget: "52"
  framework_dependency: "mycelium"
  framework_dependency_note: "This skill is designed to run within the Mycelium framework (https://github.com/haabe/mycelium). Standalone use will skip the canvas state, theory gates, and harness behavior the skill assumes. Install: /plugin install mycelium@haabe-mycelium."
---

# Service Check Skill

Evaluate against Lou Downe's 15 principles.

## Checklist

For each principle, assess: Pass / Partial / Fail / N/A

1. **Easy to find**: Can users find this service without knowing its name?
   - [ ] Discoverable through natural search terms
   - [ ] Linked from logical starting points

2. **Clearly explains its purpose**: Is it immediately clear what this does?
   - [ ] Purpose statement visible without scrolling
   - [ ] Target audience identifiable

3. **Sets expectations**: Do users know what will happen?
   - [ ] Timeline/process visible upfront
   - [ ] Requirements stated before starting

4. **Enables completion**: Can users finish what they came to do?
   - [ ] End-to-end journey works
   - [ ] No organizational barriers blocking completion

5. **Familiar**: Does it work the way users expect?
   - [ ] Uses conventions users know
   - [ ] No surprising behavior

6. **No prior knowledge needed**: Can a new user succeed?
   - [ ] No jargon or acronyms without explanation
   - [ ] No assumed context

7. **Agnostic of org structures**: Are internal boundaries invisible?
   - [ ] Users don't need to know which department handles what
   - [ ] No internal handoffs visible to users

8. **Minimum steps**: Is every step necessary?
   - [ ] No redundant data entry
   - [ ] No unnecessary confirmation steps

9. **Consistent**: Is language/design uniform throughout?
   - [ ] Same terms used for same concepts
   - [ ] Visual patterns consistent

10. **No dead ends**: Is there always a next step?
    - [ ] Error states have recovery paths
    - [ ] Edge cases have guidance

11. **Usable by everyone**: Is it accessible and inclusive?
    - [ ] WCAG 2.1 AA compliant
    - [ ] Works across devices and assistive technologies

12. **Encourages right behaviors**: Does design nudge good outcomes?
    - [ ] No dark patterns (confirmshaming, hidden costs, forced continuity, misdirection, roach motel, trick questions, bait-and-switch)
    - [ ] Default options are the safe/good ones
    - [ ] Behavioral science used to HELP users, not exploit them (Shotton: ethical application)
    - [ ] If dark patterns detected: flag "Dark Pattern Marketing" anti-pattern (see ${CLAUDE_PLUGIN_ROOT}/harness/anti-patterns.md)

13. **Responds to change**: Can it adapt?
    - [ ] Handles edge cases gracefully
    - [ ] Can be updated without full rebuild

14. **Explains decisions**: Are automated decisions transparent?
    - [ ] Rejection reasons are clear
    - [ ] Algorithm outputs are explainable

15. **Easy to get human help**: Can users reach a person?
    - [ ] Help/support clearly accessible
    - [ ] Escalation path exists

## When to Run

- **L3 Define** (solution design): Run a lightweight check focusing on principles 1-4, 8, 10, 11. These inform the Four Risks viability dimension — a solution that violates core service principles has viability risk. Feed results into `/mycelium:ice-score`.
- **L4 Develop→Deliver**: Run the full 15-principle check. Required REVIEW gate (G-V2).
- **L4 Deliver→Complete**: Final validation. Required REVIEW gate.

Running at L3 catches service design issues BEFORE delivery, not after. A solution that can't meet "enable completion" (P4) or "no dead ends" (P10) has a design problem, not just a quality problem.

## Output

```
## Service Check: [Service Name]
| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| 1 | Easy to find | Pass/Partial/Fail | ... |
...
| 15 | Human help | Pass/Partial/Fail | ... |

Score: [X/15 Pass, Y/15 Partial, Z/15 Fail]
Priority fixes: [top 3 items to address]
```

## Canvas (MANDATORY — the source of truth, do this FIRST)

`.claude/canvas/services.yml` is the canonical record. The decision log is provenance; the canvas is
what the framework READS. Write the canvas before the decision log — if only one of the two lands, it
must be this one.

**WHY THIS SECTION EXISTS (v0.170.0).** It did not, and the cost was measured. A full 15-principle
assessment ran on the dogfood project on 2026-05-23 (7 Pass / 8 Partial / 0 Fail), landed in the
decision log, and `services.yml` held every principle at `assessment: not-assessed` with
`overall_score: null` for **103 days**. The scores existed the whole time and no reader of the canvas
could see them. The `Service Quality` theory gate reads this file, so a Required gate at L4 had no
data to read while the data sat in a log nothing gates on.

**UPDATE, per principle, in `principles[]`:**

```yaml
  - id: <1-15>
    assessment: pass|partial|fail|not-assessed   # not-assessed ONLY if genuinely not evaluated
    evidence: "<what was observed, and where — a claim a later reader can check>"
    issues: ["<specific, actionable>"]           # [] when none
    last_checked: "YYYY-MM-DD"
```

**Then set the file-level fields:** `overall_score` (the X pass / Y partial / Z fail tally) and
`last_assessed` (today).

**`not-assessed` IS A REAL VERDICT AND MUST NOT BE USED AS A DEFAULT.** Leaving a principle at
`not-assessed` after running this skill records "we looked and could not judge" — which is different
from "nobody looked", and only one of those is true after a run. If a principle cannot be judged, say
why in `evidence`. A principle whose own fail criterion is "not tested" (P11 accessibility) is a
**fail**, not a `not-assessed`: the criterion is about the testing, not about the product.

## Postflight: Verify-After-Write (write-narration-verification discipline)

**Hard rule** (per CLAUDE.md Communication Rules, anti-pattern #7 Stage 2 graduation). Before any
user-facing summary claims the assessment was recorded, use the **Read tool** on the canvas file and
confirm the VALUE fields above actually changed — not just `_meta.last_validated`. A stamp moving
while the assessed fields stay at their defaults is the exact failure this skill shipped with: the
file reads fresh and holds nothing. Preflight protects what gets written; Postflight protects what
gets claimed about what was written.

## Decision Log (MANDATORY per G-P4)
**APPEND** a `### Service Check` entry to `.claude/harness/decision-log.md` with: principles assessed, scores, priority fixes, overall service quality rating.

## Theory Citations
- Downe: Good Services (15 principles)
