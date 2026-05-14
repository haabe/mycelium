---
name: cynefin-classify
description: "Use when facing a new problem to classify its domain (Clear, Complicated, Complex, Chaotic, Confused) and select appropriate methods."
instruction_budget: 20
---

# Cynefin Classify Skill

Classify problem domain and route to appropriate methods.

## Preflight: Read target canvas file(s) before any Write/Edit

**Hard rule.** Before issuing `Write` or `Edit` against any `.claude/canvas/*.yml`, use the **Read tool** on that file in this session. Claude Code's Read-before-Write check requires the `Read` tool specifically — `cat`/`head`/`grep` via Bash do NOT satisfy it.

**Edit vs Write — different cost profiles** (verified 2026-05-14):
- **`Edit`** (exact-string replacement): `Read` with `limit: 1` satisfies the check at ~50 tokens. State-tracking is per-file, not per-byte — subsequent `Edit` calls work anywhere in the file. Use this for partial updates against large canvas files (e.g., `purpose.yml` at 800+ lines).
- **`Write`** (full replacement): do a **full Read** first. Write obliterates the file; you should see what you're about to replace. The `limit:1` shortcut is *not* appropriate here.

Original failure mode: anti-pattern #7 instance #5, 2026-05-09 — agent conflated Bash `head` with the Read tool, lost ~14k tokens to a Write-fail → remedial-full-Read → re-Write loop. The `limit:1` discipline (graduated 2026-05-14, v0.23.18) prevents the second-order cost where the agent *correctly* follows the rule but full-Reads every time.

If this skill writes to multiple canvas files, register each one first (limit:1 for Edit-only paths; full Read for Write paths).

See `CLAUDE.md` *Canvas writes — Read before Write* for the canonical rule.

## Workflow

1. **Describe the problem** in neutral terms.

2. **Ask diagnostic questions**:
   - Can we predict the outcome of actions? (Yes=Clear/Complicated, No=Complex/Chaotic)
   - Do experts agree on the approach? (Yes=Clear, Somewhat=Complicated, No=Complex)
   - Is the situation stable? (Yes=Clear/Complicated/Complex, No=Chaotic)
   - Has this been solved before? (Yes=Clear, Similar=Complicated, No=Complex)

3. **Classify** into one of five domains using cynefin-routing.md.

4. **Select methods** appropriate to the domain:
   - Clear: Best practice, checklists, automation
   - Complicated: Expert analysis, options evaluation, technical spikes
   - Complex: Safe-to-fail probes, experiments, continuous discovery
   - Chaotic: Stabilize, act, then reassess
   - Confused: Decompose into classifiable parts (formerly "Disorder"; "Aporetic" when deliberately entering this state)

5. **Cross-reference with Wardley evolution** if strategic context is available.

6. **Output**:
   ```
   ## Cynefin Classification
   Problem: [description]
   Domain: [Clear/Complicated/Complex/Chaotic/Confused]
   Confidence: [High/Medium/Low]
   Liminal: [Yes/No — is this between domains?]

   Rationale: [why this classification]

   Recommended methods:
   - [method 1]
   - [method 2]

   Warning signs of misclassification:
   - [what would indicate we got it wrong]
   ```

## Canvas Output
Update `.claude/diamonds/active.yml` with the `cynefin_domain` field for the relevant diamond.
If Wardley mapping was referenced, update `.claude/canvas/landscape.yml` component evolution stages.

## Liminal Zones (Snowden, 2022+)

Most real decisions happen in **liminal zones** — transitional states between domains where characteristics of two adjacent domains blend. If the classification feels uncertain, you may be in a liminal zone rather than a pure domain.

| Transition | What it feels like | Action |
|---|---|---|
| Clear → Complicated | "We have a process but it's not covering edge cases" | Add expert analysis to the existing practice |
| Complicated → Complex | "Experts disagree and new factors keep emerging" | Shift from analysis to experimentation |
| Complex → Chaotic | "Our experiments aren't converging, things are getting worse" | Stabilize first, experiment later |
| Chaotic → Complex | "We've stopped the bleeding, now what?" | Design safe-to-fail probes |
| Clear → Chaotic (catastrophic fold) | "Everything was fine and then it all collapsed" | See warning below |

### Clear→Chaotic Catastrophic Fold

The most important Cynefin warning: when a system in Clear becomes **complacent** — rigid rules, no sensing, "we've always done it this way" — it can **catastrophically collapse into Chaotic with no warning**. The transition is NOT gradual. There is no intermediate Complicated or Complex stage.

**Detection signs**: Over-reliance on best practices without questioning them. No feedback loops. "We don't need to monitor that." Dismissing edge cases as irrelevant.

**Mycelium connection**: Theory gates and `/mycelium:feedback-review` prevent complacent drift by requiring evidence refresh and active sensing at every transition.

*Source: Snowden (Cynefin evolution, cynefin.io, 2022+)*

## Decision Log (MANDATORY per G-P4)
**APPEND** a `### Cynefin Classification` entry to `.claude/harness/decision-log.md` with: domain classified, key indicators, method routed to, confidence in classification.

## Theory Citations
- Snowden: Cynefin framework (including Liminal zones and Confused/Aporetic domain renaming)
- Wardley: Evolution mapping
