# Delivery Domain - Agent Behavior

## Purpose

Deliver validated solutions with engineering excellence, safety, and continuous learning. Every line of code should be intentional, tested, secure, and accessible.

## Pre-Implementation Checklist

Before writing any code:

1. **Read corrections.md** -- learn from past mistakes before repeating them.
2. **Run preflight skill** -- validate that prerequisites are met.
3. **Verify acceptance criteria** -- if criteria are ambiguous, clarify before coding.
4. **Confirm smallest vertical slice** -- what is the thinnest end-to-end slice that delivers value? Build that first.
5. **Check Cynefin domain** -- is this a clear, complicated, or complex problem? Method depends on domain.
6. **Review relevant patterns.md entries** -- reuse what has worked before.

## Engineering Principles

Apply consistently. See `engineering-principles.md` for full details.

| Principle | Summary |
|-----------|---------|
| **DRY** | Don't Repeat Yourself. Single source of truth for every piece of knowledge. |
| **KISS** | Keep It Simple. Simplest solution that meets the need. |
| **YAGNI** | You Aren't Gonna Need It. Don't build for speculative future needs. |
| **SoC** | Separation of Concerns. Each module has one reason to change. |
| **SOLID** | SRP, OCP, LSP, ISP, DIP -- the five principles of object-oriented design. |
| **LoD** | Law of Demeter. Talk only to immediate friends. |
| **Clean Code** | Readable, intention-revealing, well-named, small functions. |

## Testing Pyramid

Target distribution:

```
        /  E2E  \          5-10%  -- Critical user journeys only
       / Integr. \        15-20% -- API contracts, DB, external services
      /   Unit    \       70-80% -- Pure logic, edge cases, fast feedback
```

### Testing Requirements

- **Unit tests**: Write for every public function. Cover happy path, edge cases, error cases.
- **Integration tests**: Verify component boundaries, API contracts, database interactions.
- **E2E tests**: Cover critical user journeys. Keep minimal -- they are slow and brittle.
- **Property-based tests**: Use for functions with wide input domains. Test invariants, not examples.
- **Security tests**: Input validation, auth flows, injection vectors. See OWASP testing guide.
- **Accessibility tests**: Automated a11y checks in CI. Manual screen reader testing for key flows.

### TDD Practice

**Test-FIRST is the target practice.** Test-alongside satisfies the G-V7 guardrail minimum but misses the design benefits of TDD.

Why test-first matters MORE with AI agents: AI generates code with unknown quality patterns. The test suite is the safety net that catches what review might miss. In the AI era, less testing = more risk.

1. Write a failing test that describes the desired behavior.
2. Write the minimum code to make it pass.
3. Refactor while keeping tests green.
4. Repeat.

*Source: Beck (TDD, XP)*

## Security (OWASP)

Apply at every stage of delivery:

- **Input validation**: Validate all input on the server side. Allowlist over denylist. Validate type, length, range, format.
- **Output encoding**: Encode output based on context (HTML, JS, URL, CSS). Prevent XSS.
- **Parameterized queries**: Never concatenate user input into queries. Use parameterized/prepared statements.
- **Authentication**: Multi-factor where possible. Secure password storage (bcrypt/argon2). Session timeout.
- **Session management**: Generate new session ID on login. Secure, HttpOnly, SameSite cookies. Invalidate on logout.
- **Secrets management**: Never hardcode secrets. Use environment variables or a secrets manager. Rotate regularly. Never log secrets.
- **Dependency scanning**: Automated vulnerability scanning in CI. Pin dependency versions. Review before updating.
- **HTTPS everywhere**: TLS for all connections. HSTS headers. Certificate management.

## Accessibility (WCAG 2.1 AA)

Non-negotiable baseline:

- **Semantic HTML**: Use correct elements (nav, main, article, button, etc.). Headings in order.
- **ARIA**: Use ARIA attributes only when semantic HTML is insufficient. Prefer native semantics.
- **Keyboard navigation**: All interactive elements reachable and operable via keyboard. Visible focus indicators.
- **Color contrast**: Minimum 4.5:1 for normal text, 3:1 for large text. Never use color as the only indicator.
- **Screen reader support**: Meaningful alt text. Aria-labels. Live regions for dynamic content.
- **Motion**: Respect prefers-reduced-motion. No auto-playing animations.
- **Forms**: Associated labels. Error messages linked to fields. Clear instructions.

## Domain-Driven Design (DDD) for Architecture

When decomposing a solution into modules or services (L3->L4 transition):

- **Identify bounded contexts**: Each context has its own domain model and ubiquitous language. Map them in `canvas/bounded-contexts.yml`.
- **Ubiquitous language**: Use the same terms in code that domain experts use. The canvas IS the shared vocabulary.
- **Context mapping**: Define relationships between contexts (partnership, customer-supplier, ACL). These determine integration patterns.
- **Team alignment**: Stream-aligned teams (Team Topologies) should align with bounded contexts. If they don't, Conway's Law works against you.
- **For solo developers**: Think in terms of modules/namespaces rather than services. The DDD principle still applies -- clean boundaries reduce cognitive load.

*Source: Evans (Domain-Driven Design), "Architecture for Flow" (DDD + Wardley + Team Topologies)*

## AI as Pair Partner

The AI agent IS your pair partner. Leverage this:
- **Real-time review**: The agent sees every line of code as it's written. Ask it to challenge your approach.
- **Knowledge transfer**: The agent has read corrections.md, patterns.md, and the full canvas. It knows the project context.
- **Bias check**: The agent can catch confirmation bias, anchoring, and sunk cost fallacy in real-time if prompted.
- **Test generation**: Pair with the agent on TDD -- describe the behavior, let it write the test, then implement.

*Source: Beck (XP Pair Programming, adapted for AI-assisted development)*

## Agile/DevOps Practices

- **Trunk-based development**: Short-lived feature branches (< 1 day ideally). Merge to main frequently.
- **Small batches**: Each commit should be deployable. If it isn't, the batch is too large.
- **WIP limits**: Maximum 1 item in progress per developer. Finish before starting.
- **CI/CD**: Automated build, test, lint, security scan on every push. Deployment pipeline to staging/production.
- **Progressive rollout**: Feature flags, canary deployments, percentage rollouts. Never big-bang releases.
- **Automated rollback**: If health checks fail post-deploy, roll back automatically. Mean time to recovery over mean time between failures.
- **Continuous monitoring**: Dashboards, alerts, SLOs. Know when something breaks before users report it.

## Reflexion Loop

**MANDATORY for all non-trivial code changes.** Use `/reflexion` skill explicitly -- do not implement informally. The loop exists to catch mistakes before they compound.

```
1. IMPLEMENT -- Write code (apply corrections.md proactively)
2. VALIDATE  -- Run full validation suite (tests, types, lint, security)
3. CRITIQUE  -- Structured self-review:
                - Engineering violations (DRY, KISS, YAGNI, SOLID)?
                - Missing edge cases or error states (Downe P10)?
                - Security gaps (OWASP)?
                - Accessibility (WCAG 2.1 AA)?
                - Unnecessary complexity (KISS)?
                - Is this the SIMPLEST solution?
4. RETRY     -- If issues found, fix and return to step 2
               If 3 iterations reached, escalate for review
```

**When validation fails**: PostToolUseFailure hook triggers automatically. Follow its analysis. Do NOT retry blindly -- diagnose root cause first, check corrections.md, then fix.

**After success**: If corrections needed (iterations > 1), add to corrections.md. Offer to capture pattern in patterns.md. Update delivery journal.

## Definition of Done

A feature/story is done when ALL of the following are true:

- [ ] Acceptance criteria met and verified
- [ ] Code reviewed (or self-reviewed with checklist)
- [ ] Unit tests written and passing
- [ ] Integration tests written and passing (where applicable)
- [ ] No linting errors or warnings
- [ ] No type errors
- [ ] Security scan clean (no high/critical findings)
- [ ] Accessibility audit passing
- [ ] Documentation updated (API docs, README if needed)
- [ ] Performance acceptable (no regressions)
- [ ] Feature flag configured (if applicable)
- [ ] Monitoring/alerting configured
- [ ] corrections.md reviewed (no repeated mistakes)
- [ ] Deployed to staging and smoke tested
- [ ] BVSSH check passed

## CALMS Culture Assessment (Humble)

DORA measures delivery OUTCOMES. CALMS explains WHY those outcomes are what they are. Assess periodically alongside BVSSH:

- **Culture**: Learning culture vs blame culture. Blameless post-mortems. Psychological safety.
- **Automation**: Test, deploy, provision automation maturity. Manual = error-prone.
- **Lean**: Small batches, WIP limits, waste identification. Watch for big-batch waterfall.
- **Measurement**: Outcomes (DORA, BVSSH) over outputs (velocity, story points). Avoid MORF anti-pattern.
- **Sharing**: Cross-team knowledge sharing. Break silos. Collective code ownership.

If DORA metrics are poor, check CALMS to find the cultural root cause. If DORA is good but CALMS is weak, the performance is fragile and won't survive team changes.

*Source: Humble (CALMS DevOps Culture Framework)*

## DORA Metrics Tracking

Track and optimize the four key metrics (Forsgren):

- **Deployment Frequency**: How often code reaches production. Target: on-demand (multiple times per day).
- **Lead Time for Changes**: Time from commit to production. Target: less than one hour.
- **Change Failure Rate**: Percentage of deployments causing failure. Target: 0-15%.
- **Mean Time to Recovery**: Time to restore service after failure. Target: less than one hour.

## Theory of Constraints: Fixing Bottlenecks (Goldratt)

When DORA/APEX metrics identify a bottleneck, apply Goldratt's Five Focusing Steps:

1. **Identify** the constraint: Which stage in the value stream has the longest wait time or lowest throughput?
2. **Exploit** the constraint: Maximize output of the bottleneck without adding resources (remove waste, eliminate interruptions, batch efficiently).
3. **Subordinate** everything else: Non-bottleneck stages should produce only what the bottleneck can absorb. Overproduction upstream just creates queues.
4. **Elevate** the constraint: If exploitation isn't enough, invest in increasing capacity (more reviewers, better tooling, automation).
5. **Repeat**: Once the constraint is broken, a NEW constraint emerges. Go back to step 1.

**Key insight for AI-assisted delivery**: When AI accelerates coding (APEX), the bottleneck typically shifts to review/testing/deployment. Don't add more AI coding — fix the review pipeline.

Use `canvas/value-stream.yml` to visualize the full flow and identify where the constraint lives.

*Source: Goldratt (The Goal, Theory of Constraints)*

## Observability

Build observable systems from the start:

- **Structured logging**: JSON format. Include correlation IDs, timestamps, severity levels. Log decisions, not just events.
- **Metrics**: Track request rate, error rate, duration (RED). Track utilization, saturation, errors (USE). Business metrics too.
- **Error tracking**: Capture stack traces, context, affected users. Deduplicate. Alert on new error types.
- **Distributed tracing**: Trace requests across service boundaries. Identify bottlenecks.

## SRE: Error Budgets and SLIs/SLOs

For products with reliability requirements:

- **Define SLIs** (Service Level Indicators): measurable aspects of service health (availability, latency, error rate, throughput)
- **Set SLOs** (Service Level Objectives): target thresholds for each SLI (e.g., 99.9% availability)
- **Track Error Budgets**: The allowed amount of unreliability (1 - SLO). When budget is depleted, feature work pauses and reliability work takes priority.

Error budgets are the social contract: reliability earns the right to ship features faster. Track in `canvas/dora-metrics.yml` under the `sre` section. This connects to BVSSH Safer dimension.

*Source: Beyer, Jones, Petoff, Murphy (Site Reliability Engineering, Google)*

## Usability for User-Facing Work

For any user-facing delivery, two quality layers apply:
- **Service quality** (Downe's 15 principles): end-to-end service design. Run `/service-check`.
- **Interface quality** (Nielsen's 10 heuristics): screen-level usability. Run `/usability-check`.

Both are REVIEW -- delivery cannot be marked complete without them for user-facing work.

## The Shifting Bottleneck (APEX / LinearB)

**"Faster coding doesn't mean faster delivery."**

AI agents accelerate code generation, but the bottleneck often shifts to review, testing, and integration. Watch for:

- **Review queue growth**: If PRs wait longer as coding gets faster, the bottleneck has moved
- **AI rework rate**: If AI-generated code is rewritten within 21 days at >30%, AI quality is insufficient
- **Acceptance rate gap**: Industry benchmark shows AI PR acceptance at 32.7% vs human at 84.4% (LinearB 2026)
- **Review wait ratio**: AI PRs wait 4.6x longer before first review (LinearB 2026)

When you detect this pattern: reduce PR size, add automated review gates, improve AI context (better corrections.md, sharper canvas), or increase review capacity.

Track APEX metrics in `canvas/dora-metrics.yml` under the `apex` section.

*Source: LinearB APEX Framework (AI Leverage, Predictability, Efficiency, Developer Experience)*

## Component Architecture for UI Projects (Frost — Atomic Design)

For UI-heavy projects, consider Frost's Atomic Design hierarchy when structuring components: Atoms (buttons, inputs) -> Molecules (search bar) -> Organisms (header) -> Templates (page layouts) -> Pages. This is a recommended practice for design system organization, not a Mycelium requirement.

## Chaos Engineering for Production-Ready Products (SRE)

For products with reliability requirements in production: consider deliberate failure injection (chaos engineering) to test resilience. Shut down random instances, inject latency, simulate network partitions. Only relevant for production-grade systems with SLOs defined — not for discovery-through-first-delivery stages.

## JiT (Just-in-Time) Tooling

Auto-detect the technology stack and apply appropriate tooling:

- Detect language, framework, package manager, test runner, linter, formatter.
- Apply language-idiomatic practices (don't force Python patterns on Go, etc.).
- Use existing project configuration before introducing new tools.
- Prefer the project's established patterns over "better" alternatives.
- Be language-agnostic in principles, language-specific in implementation.

## Post-Delivery

After every delivery cycle:

1. **Update delivery-journal.md** -- What was delivered, what was learned, what surprised us.
2. **Update patterns.md** -- New patterns discovered, existing patterns refined.
3. **Run retrospective** -- What went well, what didn't, what to change.
4. **BVSSH check** -- Is this delivery Better Value Sooner Safer Happier? If not, why?
5. **Review DORA metrics** -- Did this cycle improve or degrade our metrics?
6. **Update corrections.md** -- Any mistakes made? Document for future prevention.
