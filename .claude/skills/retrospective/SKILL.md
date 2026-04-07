---
name: retrospective
description: "Structured retrospective after completing a delivery increment or diamond. Captures learning for continuous improvement."
---

# Retrospective

Run after every completed delivery diamond or significant milestone. Source: Forsgren (learning culture).

## Format

### 1. What Went Well?
- Which patterns from patterns.md were reused successfully?
- What new approaches worked?
- Where did the theory gates catch a real problem?

### 2. What Didn't Go Well?
- What mistakes were made? (Add to corrections.md)
- Where did we skip a guardrail and regret it?
- What took longer than expected and why?

### 3. What Should Change?
- New corrections to add
- New patterns to capture
- Process improvements
- Guardrail adjustments

### 4. BVSSH Dimension Check
- **Better**: Did quality improve or degrade?
- **Value**: Did we deliver actual user value?
- **Sooner**: Was our flow efficient?
- **Safer**: Did we maintain security and trust?
- **Happier**: How is team satisfaction?

## Output
1. Update `.claude/memory/corrections.md` with new corrections
2. Update `.claude/memory/patterns.md` with new patterns
3. Update `.claude/memory/delivery-journal.md` with retrospective entry
4. Update canvas/bvssh-health.yml if dimensions changed
5. Log in decision-log.md
