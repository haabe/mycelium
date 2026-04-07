---
name: reflexion
description: "Use for self-correcting implementation. Implements the reflexion loop: implement, validate, self-critique, retry (max 3 iterations)."
---

# Reflexion Skill

Self-correcting implementation loop from the n-trax pattern.

## Workflow

### Iteration Loop (max 3)

**Step 1: Implement**
- Write code according to the specification/acceptance criteria.
- Follow engineering-principles.md.
- Apply patterns from patterns.md.
- Check corrections.md for relevant past mistakes.

**Step 2: Validate**
- Run all tests (unit, integration, e2e as applicable).
- Run linter and type checker.
- Run security scan.
- Run accessibility checks (if UI).
- Verify acceptance criteria.

**Step 3: Self-Critique**
Review the implementation against:
- [ ] Engineering principles: DRY, KISS, YAGNI, SoC, SOLID, LoD, Clean Code
- [ ] Security: Input validation, output encoding, no secrets, parameterized queries
- [ ] Accessibility: Semantic HTML, keyboard nav, contrast, screen reader
- [ ] Edge cases: What happens with empty input? Null? Max values? Concurrent access?
- [ ] Error handling: Are errors handled gracefully? Are error messages helpful?
- [ ] Performance: Any obvious O(n^2) or worse? Unnecessary computation?
- [ ] Testability: Can this be tested in isolation? Are dependencies injectable?
- [ ] Naming: Do names reveal intent? Would a new reader understand this?

**Step 4: Decide**
- If all validations pass AND self-critique finds no issues: **DONE**
- If issues found AND iteration < 3: **FIX and return to Step 1**
- If iteration = 3 AND issues remain: **ESCALATE** with documented issues

### Escalation Protocol
When max iterations reached without full resolution:
1. Document what was attempted in each iteration.
2. Document remaining issues with severity assessment.
3. Recommend: fix now (blocking) vs. fix later (non-blocking) vs. accept risk.
4. Update corrections.md with learnings.

## Rules
- Each iteration must show measurable improvement over the previous.
- If the same issue recurs across iterations, investigate root cause rather than patching symptoms.
- Never skip the self-critique step, even if tests pass.
- Log the reflexion loop outcome in delivery-journal.md.

## Theory Citations
- Reflexion pattern (Shinn et al.)
- Clean Code (Martin)
- OWASP secure coding
- WCAG 2.1 AA
