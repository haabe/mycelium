---
name: bias-check
description: "Use before any research activity or significant decision. Reviews cognitive biases relevant to the current stage."
instruction_budget: 27
---

# Bias Check Skill

Pre-research and pre-decision bias review.

## Preflight: Read target canvas file(s) before any Write/Edit

**Hard rule.** Before issuing `Write` or `Edit` against any `.claude/canvas/*.yml`, use the **Read tool** on that file in this session. Claude Code's Read-before-Write check requires the `Read` tool specifically — `cat`/`head`/`grep` via Bash do NOT satisfy it.

**Edit vs Write — different cost profiles** (verified 2026-05-14):
- **`Edit`** (exact-string replacement): `Read` with `limit: 1` satisfies the check at ~50 tokens. State-tracking is per-file, not per-byte — subsequent `Edit` calls work anywhere in the file. Use this for partial updates against large canvas files (e.g., `purpose.yml` at 800+ lines).
- **`Write`** (full replacement): do a **full Read** first. Write obliterates the file; you should see what you're about to replace. The `limit:1` shortcut is *not* appropriate here.

Original failure mode: anti-pattern #7 instance #5, 2026-05-09 — agent conflated Bash `head` with the Read tool, lost ~14k tokens to a Write-fail → remedial-full-Read → re-Write loop. The `limit:1` discipline (graduated 2026-05-14, v0.23.18) prevents the second-order cost where the agent *correctly* follows the rule but full-Reads every time.

If this skill writes to multiple canvas files, register each one first (limit:1 for Edit-only paths; full Read for Write paths).

See `CLAUDE.md` *Canvas writes — Read before Write* for the canonical rule.

## Workflow

1. **Identify context**: What stage (L0-L5)? What activity (research, decision, evaluation)?

2. **Load stage-specific checklist** from ${CLAUDE_PLUGIN_ROOT}/harness/cognitive-biases.md for the current scale.

3. **For each bias on the checklist**:
   - Is this bias likely active in the current situation? (Yes/No/Maybe)
   - If Yes/Maybe: What specific mitigation will be applied?
   - Document the assessment.

4. **Check agent's own biases** (from ${CLAUDE_PLUGIN_ROOT}/harness/cognitive-biases.md agent section):
   - Sycophancy: Am I agreeing with the user when evidence says otherwise?
   - Recency: Am I overweighting recent context over earlier evidence?
   - Pattern matching: Am I assuming this is like something I've seen before without checking?
   - Completionism: Am I filling gaps with speculation rather than acknowledging uncertainty?

5. **Output bias briefing**:
   ```
   ## Bias Check: [Activity]
   Stage: [L0-L5]

   ### Active Risks
   | Bias | Risk Level | Mitigation |
   |------|-----------|------------|
   | ...  | High/Med/Low | ... |

   ### Agent Self-Check
   - Sycophancy: [OK/Risk]
   - Recency: [OK/Risk]
   - Pattern matching: [OK/Risk]
   - Completionism: [OK/Risk]

   ### Proceed? [Yes / Yes with caution / Pause and address]
   ```

6. **System-level bias diagnosis** (Meza):
   Before attributing resistance or poor outcomes to cognitive bias, check if the "bias" is actually a rational response to a badly designed system. Ask:

   | Phase | System Question | If Yes: Fix the System, Not the Person |
   |-------|----------------|---------------------------------------|
   | Awareness | Does the person know the desired behavior? | Fix communication, not cognition |
   | Motivation | Does the system reward the desired behavior? | Fix incentives, not mindset |
   | Ability | Can the person realistically do it? | Fix resources/process, not training |
   | Reinforcement | Is the behavior sustained by the environment? | Fix feedback loops, not habits |
   | Sustainability | Can it persist without ongoing intervention? | Fix structure, not willpower |

   If 2+ phases point to systemic causes, the primary intervention is system redesign, not individual debiasing. Update the bias briefing output above to flag the system-level root cause.

   The 5 phases above are a systemic diagnostic inspired by behavioral design models (COM-B, Fogg Behavior Model), not a named framework. They are prompts for investigation, not rigid steps.

   *Source: Robert Meza (The Bias Gap — diagnostic tool, aimforbehavior.com). Not to be confused with Thaler & Sunstein's "Nudge" theory.*

## When to Surface This Skill

This skill should be triggered:
- Before any research activity (interviews, surveys, data analysis)
- Before significant decisions at any diamond scale
- **At L5 market transitions**: Before launch tier classification and go-to-market planning, check for optimism bias (overweighting positive signals), confirmation bias (seeking validation of "ready to ship"), and anchoring (fixating on initial positioning)
- When `/mycelium:diamond-progress` or `/mycelium:diamond-assess` detects bias-related gate failures

## Canvas Output
Record bias check in `.claude/canvas/opportunities.yml` under `bias_checks` section with date, biases mitigated, and research design adjustments made.

## Decision Log (MANDATORY per G-P4)
**APPEND** a `### Bias Check` entry to `.claude/harness/decision-log.md` with: activity assessed, active bias risks found, mitigations applied, agent self-check results.

## Theory Citations
- Kahneman: Thinking, Fast and Slow (System 1/System 2)
- Shotton: The Choice Factory (behavioral biases in decision-making)
- Torres: Continuous Discovery Habits (bias in research)
- Robert Meza: The Bias Gap (systemic bias reframing -- when "bias" is a rational response to a badly designed system)
