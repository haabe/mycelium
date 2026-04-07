# Escape Hatch: When to Bypass Mycelium

Sometimes you need to move fast and the full process is legitimately too heavy. This is OK -- but it must be conscious, documented, and temporary.

## When Bypassing is Legitimate

- **Production incident**: System is down, users are affected. Fix first, process later.
- **Trivial change**: Fixing a typo, updating a version number, changing a comment. No diamond needed.
- **Hotfix**: Critical security patch that can't wait for discovery.
- **Spike/prototype**: Exploring feasibility before committing to a diamond. Time-boxed.
- **External deadline**: Regulatory requirement with a hard date. Adapt process to fit.

## How to Bypass

1. **State it explicitly**: "I'm bypassing the Mycelium process for [reason]"
2. **Log it**: Add entry to `decision-log.md` with `BYPASS` tag:
   ```
   ### YYYY-MM-DD - BYPASS: [what was bypassed]
   - **Reason**: [why the full process was skipped]
   - **What was skipped**: [which gates, which checks]
   - **Risk accepted**: [what could go wrong]
   - **Payback plan**: [when the skipped work will be done]
   ```
3. **Accept the risk**: Acknowledge what you're not checking (security? accessibility? bias?)
4. **Pay it back**: After the emergency, return and do the skipped work

## What You Lose When Bypassing

| Skipped | Risk |
|---------|------|
| Discovery | Building the wrong thing |
| Theory gates | Proceeding without evidence |
| Bias check | Confirmation bias unchecked |
| Threat model | Security vulnerabilities |
| Accessibility check | Excluding users |
| Service check | Dead ends, poor UX |
| Corrections review | Repeating past mistakes |
| Canvas update | Team loses product knowledge |

## The Anti-Pattern: Bypass as Default

If you're bypassing more than 10% of the time, the process needs adjustment -- not bypassing.

Signals that bypass has become the norm:
- Decision log has more BYPASS entries than normal entries
- Canvas files are stale (not updated in weeks)
- Corrections.md is empty despite active delivery
- No retrospectives being run

**If this is happening**: Run `/bvssh-check` and `/retrospective`. The process isn't serving you, which means either the project type classification is wrong (too much ceremony for the context) or the team is under unsustainable pressure (BVSSH Happier dimension failing).
