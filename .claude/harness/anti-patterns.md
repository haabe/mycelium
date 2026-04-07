# Anti-Patterns

Known failure modes organized by category. Check regularly, especially when things feel off.

## Discovery Anti-Patterns

### 1. Solution-First Discovery
- **Description**: Jumping to solutions before understanding the problem. Running "discovery" to validate a predetermined answer.
- **Detection rule**: Solution language ("we should build...", "the feature needs...") appears before problem framing is complete.
- **What to do instead**: Return to Discover phase. Conduct user research. Build OST from findings, not from brainstorming.
- **Source**: Torres (Continuous Discovery Habits)

### 2. Tourist Interviews
- **Description**: Conducting interviews as a checkbox exercise without genuine curiosity. Asking scripted questions without follow-up.
- **Detection rule**: All interviews are under 15 minutes. No follow-up questions. No surprising findings.
- **What to do instead**: Use Torres story-based interviewing. Follow the interviewee's narrative. Ask "Tell me more about that."
- **Source**: Torres (Continuous Discovery Habits)

### 3. Confirmation Research
- **Description**: Designing research to confirm existing beliefs rather than to learn.
- **Detection rule**: Research questions are phrased as yes/no. All findings align with prior assumptions. No disconfirming evidence sought.
- **What to do instead**: Run bias-check before research. Actively seek disconfirming evidence. Include devil's advocate review.
- **Source**: Kahneman (Thinking, Fast and Slow), Shotton (The Choice Factory)

### 4. HiPPO-Driven Discovery
- **Description**: Highest Paid Person's Opinion overrides research findings. Stakeholder requests treated as validated user needs.
- **Detection rule**: Priority decisions reference authority ("the CEO wants...") rather than evidence.
- **What to do instead**: Require evidence for all priority decisions. Use ICE scoring with evidence-backed confidence. Present data, not opinions.
- **Source**: Gilad (Evidence-Guided), Cagan (Empowered)

### 5. Single-Source Validation
- **Description**: Treating one interview, one data point, or one anecdote as sufficient evidence.
- **Detection rule**: Findings have only one evidence source. No triangulation attempted.
- **What to do instead**: Require 2+ evidence sources for every significant finding. Cross-reference qualitative with quantitative data.
- **Source**: Torres (Continuous Discovery Habits)

### 6. Opportunity Brainstorming
- **Description**: Generating opportunities through brainstorming sessions rather than discovering them through research.
- **Detection rule**: OST opportunities don't link to research data. Opportunities sound like features.
- **What to do instead**: Only add opportunities to the OST that emerge from research. Every opportunity needs evidence citations.
- **Source**: Torres (Continuous Discovery Habits)

## Confidence Anti-Patterns

### 1. Confidence Theater
- **Description**: Assigning high confidence scores without supporting evidence. Using confidence as a social signal rather than an analytical measure.
- **Detection rule**: Confidence > 0.7 with fewer than 2 evidence sources. Confidence never decreases.
- **What to do instead**: Tie confidence to specific evidence. Lower confidence when evidence is weak. Use confidence-thresholds.yml.
- **Source**: Gilad (Evidence-Guided)

### 2. Anchored Confidence
- **Description**: Initial confidence score anchors all subsequent assessments. New evidence doesn't meaningfully change the score.
- **Detection rule**: Confidence changes less than 0.05 across multiple evidence additions.
- **What to do instead**: Recalculate confidence from scratch periodically. Weight recent evidence appropriately.
- **Source**: Kahneman (Thinking, Fast and Slow)

### 3. Binary Confidence
- **Description**: Treating confidence as pass/fail rather than a spectrum. "We're confident enough" without quantification.
- **Detection rule**: Confidence always at 0.0 or 1.0. No partial confidence states.
- **What to do instead**: Use the full 0.0-1.0 range. Document what would increase or decrease confidence.
- **Source**: Gilad (Evidence-Guided)

### 4. Confidence Without Context
- **Description**: Confidence score provided without explaining what it measures or what evidence supports it.
- **Detection rule**: Confidence number exists without accompanying evidence list or rationale.
- **What to do instead**: Always pair confidence with: what it measures, what evidence supports it, what would change it.
- **Source**: Mycelium (internal)

### 5. Sunk Cost Confidence
- **Description**: Maintaining high confidence because significant effort has been invested, not because evidence supports it.
- **Detection rule**: Confidence stays high despite negative signals. Justification references effort ("we've already...") not outcomes.
- **What to do instead**: Evaluate confidence based on current evidence only. Sunk costs are irrelevant to future decisions.
- **Source**: Kahneman (Thinking, Fast and Slow)

## Security Anti-Patterns

### 1. Security as Afterthought
- **Description**: Addressing security only after development is "complete." Treating security review as a gate rather than a practice.
- **Detection rule**: No security considerations in Discover/Define phases. STRIDE only applied at Deliver.
- **What to do instead**: Integrate security from L0 onward. See security-trust.md for per-stage requirements.
- **Source**: OWASP (Security by Design)

### 2. Checkbox Compliance
- **Description**: Running security tools without acting on findings. Passing scans by suppressing warnings.
- **Detection rule**: Security scan results have ignored/suppressed findings. No remediation tickets.
- **What to do instead**: Every finding gets triaged, documented, and either fixed or risk-accepted with rationale.
- **Source**: OWASP

### 3. Secrets in Code
- **Description**: Hardcoded API keys, passwords, or tokens in source code or configuration files committed to version control.
- **Detection rule**: Regex scan finds patterns matching secrets. .env files in git history.
- **What to do instead**: Use environment variables or secrets manager. Add secret patterns to .gitignore and pre-commit hooks.
- **Source**: OWASP (Secrets Management)

### 4. Trust-by-Default
- **Description**: Trusting user input, third-party data, or internal service responses without validation.
- **Detection rule**: No input validation at service boundaries. Data flows from external source to database without sanitization.
- **What to do instead**: Validate all input. Encode all output. Treat every boundary as a trust boundary.
- **Source**: OWASP (Input Validation)

### 5. Security Through Obscurity
- **Description**: Relying on hidden URLs, undocumented APIs, or non-standard ports as security measures.
- **Detection rule**: Security relies on something being "not discovered" rather than properly protected.
- **What to do instead**: Implement proper authentication and authorization. Assume attackers know your system.
- **Source**: OWASP

## Delivery Anti-Patterns

### 1. Big Bang Delivery
- **Description**: Building everything before shipping anything. Large batch releases.
- **Detection rule**: No deployments for weeks. Feature branches older than 2 days. Release planning meetings.
- **What to do instead**: Trunk-based development. Small batches. Feature flags. Ship the thinnest vertical slice first.
- **Source**: Forsgren (Accelerate), Smart (Sooner Safer Happier)

### 2. Test-Last Development
- **Description**: Writing tests after the code is "done" (or not at all). Tests as documentation rather than design tool.
- **Detection rule**: Test files created after implementation files. Low test coverage. Tests that test implementation details.
- **What to do instead**: TDD or test-alongside. Write the test first. Test behavior, not implementation.
- **Source**: Engineering best practice

### 3. Gold Plating
- **Description**: Adding features, polish, or optimization beyond what was needed. Perfecting code that delivers marginal value.
- **Detection rule**: Scope creep beyond acceptance criteria. Optimization without profiling data. "Nice to have" features in the PR.
- **What to do instead**: Meet acceptance criteria. Ship. Measure. Iterate if warranted. YAGNI.
- **Source**: Smart (Sooner Safer Happier), Agile principles

### 4. Heroic Recovery
- **Description**: Relying on individual heroics to fix deployment failures rather than automated rollback and systemic improvement.
- **Detection rule**: Manual production fixes. Late-night deployments. One person who "knows how to fix it."
- **What to do instead**: Automated rollback. Progressive deployment. Blameless retrospectives. Improve MTTR systematically.
- **Source**: Forsgren (Accelerate)

### 5. Accessibility Bolt-On
- **Description**: Treating accessibility as a final checklist item rather than a design constraint from the start.
- **Detection rule**: Accessibility testing only at end of sprint. ARIA attributes added to fix semantic HTML issues. No keyboard testing during development.
- **What to do instead**: Start with semantic HTML. Test with keyboard during development. Include a11y in Definition of Done.
- **Source**: Downe (Good Services), WCAG

### 6. Reflexion Bypass
- **Description**: Skipping the self-critique step in the reflexion loop. Shipping first draft without review.
- **Detection rule**: No reflexion loop evidence. Single implementation attempt without validation.
- **What to do instead**: Always run implement-validate-critique-retry. Even if the first attempt looks good, validate.
- **Source**: Mycelium (reflexion pattern)
