# Mycelium: Theory-Guided Agentic Product Development

*Version 0.17.0 -- Documented-rule-diverges-from-enforcement cluster spec-graduated (8 instances, Check 26's promised 6th-instance graduation honored several days late). Three coordinated artifacts ship: (1) `engine/consistency-check-spec.md` defines consistency-checking, catalogs all 8 instances by subclass (validator-vs-doc, schema-vs-discipline-vocabulary, doc-vs-rendering, schema-vs-discipline-missing-field, hook-vs-rule), articulates 5 candidate detection rules with per-rule catches/misses/FP-risk, sets the spec→mechanism promotion bar (≥3 rules implemented, <5% FP, 100% TP on cluster fixtures, integration into a check); (2) `memory/cluster-instances.md` makes the cluster log canonical so instance count is mechanically auditable rather than oral history; (3) `/corrections-audit` step 6b + `/framework-health` step 4b wire the cluster log into routine audits and graduation-readiness flagging. Schema fix: `jobs-to-be-done.schema.json` gains `validation_status_per_dimension` first-class field with `dimension_status` $def for the Christensen tripartite (instance 8 closed). Backward compatible. MINOR per version-discipline (new convention with structural impact). Closes the recursive bug where the framework's stated graduation criteria couldn't be mechanically counted; promotion to a shipped mechanism is now bounded by the spec's promotion bar rather than vibes.

0.16.5 (folded) -- /diamond-progress SKILL.md step 4 includes explicit prompt-template naming the re-invocation-as-approval shortcut. Footgun → visible affordance (Norman).

0.16.4 (folded) -- engine/wayfinding.md tightened with "STRICT — reproduce the template literally" + explicit list of common improvisations to forbid.

0.16.3 (folded) -- CLAUDE.md "Canvas writes — Read before Write" paragraph: canvas files ship pre-populated as templates, so Claude Code's `Write` tool always requires a prior `Read` on a fresh project; `cat` via Bash doesn't count.

0.16.2 (folded) -- Provenance schema accepts singular `source_class` (single enum) and `notes` (free-text) alongside plural `source_classes`. Strict mode preserved (typos still caught). Same shape as Check 26's "documented rule diverges from enforcement" cluster, at schema layer.

0.16.1 (folded) -- Check 26 refined to WARN on uncommitted post-bump material edits; .claude/tests/ added to watched material paths; AGENTS.md surfaces upgrade.sh + version-bump caveat.

0.16.0 (folded summary) -- Self-correcting harness layer: G-V12 (every validator ships coverage proof) + G-P-pre (Mandatory Pre-Ship Protocol with visible gap analysis) graduate two recurring patterns to mechanism. Check 26 enforces version-bump discipline (5th-instance graduation of "documented rule diverges from enforcement"). Explainability: /xai-check skill + Gate 13 + ai-system-card template + Mycelium's own card + context-surface doc. Warnings ingestor turns CI signals into self-learning input alongside corrections.md. Detector Step 1c gains agent_runtime_target category for harness-shaped products. parse_manifest gains --manifest=<path> override (closes 4th-instance stale-read pattern in upgrade.sh). decision-log gains structured why_not_alternatives field (Liao contrastive). +27 unit tests; coverage 52% → 78%; ruff 35 → 0. Theory citations: Doshi-Velez & Kim, Liao et al., Mitchell et al., Lanham et al., Selbst & Barocas, Bansal et al., Lopopolo, EU AI Act Art. 13/50.*

Mycelium is a harnessing system for AI-assisted product development. It connects theories, shares learning, adapts to conditions, and makes the whole ecosystem stronger.

**You are an agent operating within Mycelium. Every action you take must be guided by the frameworks below, harnessed by the guardrails, and logged in the decision system.**

## Communication Rules

**Always communicate in plain language first, technical details second.** Use `.claude/engine/status-translations.md` to translate diamond states.

- Say "Discovering what problems to solve" not "L2 Opportunity Discover phase"
- Say "Confidence: Moderate -- based on 2 user interviews" not "Confidence: 0.5"
- When reporting confidence, always include: the level, the evidence type, WHY it's appropriate, and what would increase it

**Always suggest relevant skills at transitions.** When checking theory gates, surface the skill that satisfies each gate: "Before delivering, consider running `/security-review` (security gate) and `/a11y-check` (accessibility)."

**Always cite the trigger when suggesting a skill, recommending an approach, or making a non-trivial move.** Format: `(per: <source>)`. Source can be a corrections.md entry, canvas evidence, a theory gate, a pattern, or a prior decision-log entry. Example: "Suggesting `/threat-model` (per: L4 deliver gate + threat-model.yml stale 47 days)." Citations must be faithful — name the source that actually drove the move, not a plausible after-the-fact (Lanham et al. 2023). Tracked in eval `2026-05-04-xai-inline-attribution`.

**Always offer to capture learnings after each diamond phase.** After completing a phase, prompt: "Anything worth capturing? I'll draft the entry for corrections.md or patterns.md."

## Mandatory Pre-Task Protocol

Before ANY implementation task, load context in this order (task-specific first, background last — models attend best to early and late context):
1. Identify which diamond you are operating within (check `.claude/diamonds/active.yml`)
2. Load the appropriate domain context (`.claude/domains/{discovery|delivery|quality}/CLAUDE.md`) — **skip if canvas is empty** (new project with no diamond yet; `/interview` creates the first diamond)
3. Read `.claude/memory/corrections.md` for relevant past mistakes — **skip on first `/interview` round** (no corrections exist yet)
4. Load phase-scoped guardrails: always load `guardrails-core.md`; add `guardrails-discovery.md` (L0-L2), `guardrails-delivery.md` (L3-L4), or `guardrails-market.md` (L5) per current phase. See `.claude/harness/guardrails.md` for full reference.

## Mandatory Pre-Ship Protocol (G-P-pre)

Before committing any **substantive** work — defined as ≥1 framework file modified, OR a new skill/convention introduced, OR a multi-commit batch — perform an explicit pre-ship analysis and surface findings *visibly* in the response. Not an afterthought. Not "I checked everything." A bulleted section with real findings.

The minimum check set:
1. **Dead-end references**: Does every artifact reference something that exists or is tagged as future work? Forward-grep what you wrote against the codebase.
2. **Misalignments**: Are there two places that should agree but don't? Existing skills overlapping with new ones, intent guardrails vs operational gates, schemas vs the data they validate.
3. **Blocked gates**: Any gates that can't pass because of missing prerequisites? Phase-N depends on Phase-M being shipped first.
4. **Functional gaps**: Does the work handle the edge cases — absence signals, defaults, idempotency, multi-entity loops?
5. **Integration debt**: What existing skills/docs need updating to know about the new work? Tag what defers.
6. **Schema/validation impact**: Will writes pass existing validators? Are new validators paired with G-V12 coverage proofs?
7. **Manifest impact**: Are new directories/files in `manifest.yml` so `upgrade.sh` syncs them?
8. **Test coverage**: Per G-V12, every check that flags a problem ships with a test demonstrating it does.

The findings drive what ships now vs defers. Real findings change the plan. Theatre findings are worse than no analysis.

*Source: Graduated 2026-05-04 from corrections.md "Pre-ship gap/misalignment/dead-end analysis skipped despite repeated user instruction" (recurring; user-detected, daily-nag class). The Post-Task Protocol below covers post-ship verification; this protocol covers pre-ship analysis. Together they bracket the work.*

## Mandatory Post-Task Protocol (G-P7)

After completing ANY batch of changes, before reporting done:
1. **Verify**: If changes span repos, diff changed files for consistency. Check reference integrity (counts, cross-links, no orphans).
2. **Corrections**: Did any mistakes happen during this task? Log to `corrections.md`, update TL;DR.
3. **Patterns**: Did anything reusable emerge? Log to `patterns.md`.
4. **Sync**: Ensure both repos match on all changed files.

If the user has to ask whether this happened, the protocol already failed.

## The Diamond Engine

### Diamond Scales (L0-L5)

| Scale | Focus | Primary Theories | Canvas Files |
|-------|-------|-----------------|--------------|
| L0: Purpose | Why we exist | Sinek (Golden Circle), JTBD (Christensen) | `canvas/purpose.yml`, `canvas/jobs-to-be-done.yml` |
| L1: Strategy | Where to play | Wardley Mapping, North Star, Team Topologies (Skelton) | `canvas/landscape.yml`, `canvas/north-star.yml`, `canvas/team-shape.yml` |
| L2: Opportunity | What to solve | Torres (CDH/OST), Allen (User Needs Mapping), Hoskins (Scenarios), Cynefin | `canvas/opportunities.yml`, `canvas/user-needs.yml`, `canvas/scenarios.yml` |
| L3: Solution | How to solve it | Gilad (GIST), Ellis (ICE, adopted by Gilad within GIST), Cagan (Inspired), Downe (Good Services) | `canvas/gist.yml`, `canvas/services.yml` |
| L4: Delivery | Build and ship | Forsgren (DORA), OWASP, Goldratt (ToC), DRY/KISS/YAGNI/SOLID/SoC | `canvas/dora-metrics.yml`, `canvas/threat-model.yml`, `canvas/value-stream.yml` |
| L5: Market | Reach users | Lauchengco (Loved), Shotton (behavioral science) | `canvas/go-to-market.yml`, `canvas/trust-signals.yml` |

L0-L3 are product-agnostic. L4-L5 adapt to `product_type` (software, content_course, content_publication, content_media, ai_tool, service_offering). See `canvas-guidance.yml#product_types`.

### Diamond Phases

Each diamond has four phases, gated by theory checks:
1. **Discover** (diverge) -- Explore broadly. Gather evidence. Challenge assumptions.
2. **Define** (converge) -- Synthesize discoveries. Narrow focus. Frame the problem/opportunity.
3. **Develop** (diverge) -- Generate multiple solutions. Ideate. Prototype.
4. **Deliver** (converge) -- Validate, build, ship, measure.

Diamonds spawn child diamonds when complexity requires it (L0->L1->L2->L3->L4, L5->L2 on market feedback). Parents continue while children execute. If delivery reveals a bad assumption, the diamond **regresses** back with new evidence -- this is the system working correctly.

See `.claude/engine/diamond-rules.md` for full transition rules, WIP limits, and lifecycle management.

### OST Leaf Lifecycle

Every OST solution leaf follows a 10-phase pipeline from creation to market feedback. Each phase has explicit input artifacts, gates, output artifacts, and discard criteria. The pipeline is:

**OST Leaf → Four Risks → ICE Score → Assumption Test → GIST Entry → Bounded Context → Threat Model → Preflight → Delivery Diamond → Launch + Feedback**

See `.claude/engine/leaf-lifecycle.md` for complete phase definitions, discard rules, and cross-reference map. Archived leaves go to `canvas/archived-solutions.yml`.

### Perspective Resolution

When product, design, and engineering perspectives conflict, use the structured resolution framework. See `.claude/engine/perspective-resolution.md`.

### Leaf Bakeoff (Parallel A/B Testing)

When multiple leaves compete for the same opportunity, use the bakeoff protocol for structured comparison. See `.claude/orchestration/leaf-bakeoff.md`.

## Theory Gates (Decision Checkpoints)

Every diamond transition must pass applicable gates from: Evidence, Four Risks, JTBD, Cynefin, Bias, Security, Privacy, BVSSH, Service Quality, Delivery Metrics, Corrections, Regulatory. See `.claude/engine/theory-gates.md` for complete definitions, pass/fail criteria, and suggested skills.

**You cannot progress a diamond by saying "I'm confident enough." You must demonstrate evidence that satisfies each gate.**

## The Canvas (Source of Truth)

All product knowledge lives in `.claude/canvas/*.yml`. These files are:
- The **single source of truth** for the product's state
- Committed to git (they are documentation-as-code)
- Updated through evidence, not assumption
- Readable by any team member starting a new session

**Never make a significant decision without first checking and updating the relevant canvas file.**

Canvas files should include `_meta` blocks for versioning and staleness detection (see `canvas-guidance.yml`). Run `/canvas-health` periodically to lint for missing fields, stale confidence, inconsistent evidence types, and orphaned references.

**Canvas writes — Read before Write.** Every canvas file ships pre-populated as a template (header comments + placeholder fields), so on a fresh project every `.claude/canvas/*.yml` already exists. Claude Code's `Write` tool requires a prior `Read` (the same tool, same session) on existing files; `cat` via Bash does NOT satisfy this check. When a skill populates a canvas file, the agent must use the **Read tool** on the canvas file *before* Write. Use `Edit` for partial updates (also requires prior Read). This applies to `/interview`, `/canvas-update`, `/log-evidence`, `/jtbd-map`, `/wardley-map`, `/ost-builder`, `/gist-plan`, `/dora-check`, every metric-pull evidence write, and any other skill that touches `.claude/canvas/*.yml`. Detected during Juniors.dev pre-run dogfood (2026-05-06).

## Harnessing System

- **Guardrails** (`.claude/harness/guardrails.md`): Three-tier enforcement -- BLOCK (mechanically prevented), REVIEW (gates progression), NUDGE (advised, not blocking).
- **Anti-Patterns** (`.claude/harness/anti-patterns.md`): Known failure modes with detection rules. Stop and self-correct if you catch yourself in one.
- **Cognitive Biases** (`.claude/harness/cognitive-biases.md`): Per-stage bias checklist.
- **Security & Trust** (`.claude/harness/security-trust.md`): Per-stage security requirements.
- **Engineering Principles** (`.claude/harness/engineering-principles.md`): DRY, KISS, YAGNI, SoC, SOLID, LoD.

## Self-Learning System

### Two Memory Systems -- Important Distinction

| System | Location | Scope | Committed to git? |
|---|---|---|---|
| **Project memory** | `.claude/memory/` (in the project repo) | Team-level learnings about *this product* | Yes |
| **Auto-memory** | `~/.claude/projects/<id>/memory/` (in user home) | Per-session continuity between you and the agent | No (user-local) |

**Routing rule**: Project-team learnings -> project memory. Agent-user learnings -> auto-memory. Hardware/environment failures -> neither.

The reflexion hook (PostToolUseFailure) is scoped to **project-relevant failures only** -- do not log entries to project memory for agent self-inflicted tool errors or environment issues outside the project directory.

### Key Artifacts
- **Corrections** (`.claude/memory/corrections.md`): Accumulated learning from mistakes. **Read before every task.** *Recourse SLA*: one-off corrections inform the next session's pre-task protocol (same-day effect on agent behavior); recurring entries (≥3 instances of the same root cause) graduate to mechanism on the next L4 cleanup cycle. Public-graduation cases visible in upstream commit history. No formal SLA on GitHub-issue response — solo-maintainer project (acknowledged in `docs/ai-system-card.md` §6).
- **Patterns** (`.claude/memory/patterns.md`): Successful patterns to reuse.
- **Warnings Log** (`.claude/memory/warnings-log.md`): CI signal capture (validator/upgrade WARN+FAIL lines), auto-updated by `.claude/scripts/ingest_warnings.py`. Best-practice fixes per class live in `.claude/engine/warning-handbook.md`. Consumed by `/corrections-audit` for cross-source pattern detection.
- **Decision Log** (`.claude/harness/decision-log.md`): Every significant decision with context, alternatives, theory, evidence, confidence. **Required structured field**: `why_not_alternatives` — for each alternative considered, a one-line rejection rationale. Contrastive ("why X rather than Y") explanations land harder than purely positive ones (Liao et al. 2020); freeform "alternatives considered" without per-alternative rejection rationale fails the contrastive surface check in `/xai-check` Stage 2.
- **Feedback Loops** (`.claude/engine/feedback-loops.md`): Four-speed system (immediate/incremental/strategic/transformative). Run `/feedback-review` to check health.
- **Reflexion Loop**: Implement -> validate -> self-critique -> retry (max 3). See `.claude/skills/reflexion/SKILL.md`.
- **Eval Benchmarks** (`.claude/evals/`): Periodic self-assessment against scenarios.
- **Cycle History** (`.claude/canvas/cycle-history.yml`): Completed leaf lifecycle outcomes for calibration. See `.claude/engine/cycle-learning.md`.
- **Adaptive Thresholds** (`.claude/canvas/thresholds.yml`): Calibrated thresholds that improve from data. See `.claude/engine/adaptive-thresholds.md`.

### Learning Metabolism (Self-Improving System)

Mycelium gets smarter over time through five learning mechanisms:

1. **Cycle Learning** (`.claude/engine/cycle-learning.md`): Every completed or discarded leaf generates calibration data — predicted vs actual ICE, effort accuracy, risk dimension accuracy.
2. **Pattern Emergence** (`.claude/engine/pattern-detector.md`): Statistical patterns across cycle history surface as correlation rules, anti-pattern signals, and success patterns. Woven into `/retrospective` and `/diamond-assess`.
3. **Adaptive Thresholds** (`.claude/engine/adaptive-thresholds.md`): ICE advance threshold, confidence calibration, and evidence staleness thresholds adjust from historical data. Defaults until N=10 cycles.
4. **Framework Reflexion** (`.claude/engine/framework-reflexion.md`): Quarterly self-assessment — cycle velocity, discard trends, confidence calibration, gate effectiveness, regression rate. Run `/framework-health`.
5. **Evidence Decay** (`.claude/engine/evidence-decay.md`): Evidence ages. Confidence degrades over time unless refreshed. `/canvas-health` flags stale evidence.

## Domain Contexts

Load the appropriate context based on current diamond phase:

- **Discovery**: `.claude/domains/discovery/CLAUDE.md` -- Torres-style interviewing, OST construction, bias-aware research
- **Delivery**: `.claude/domains/delivery/CLAUDE.md` -- Agile/DevOps practices, clean code, security, accessibility, DORA metrics
- **Quality**: `.claude/domains/quality/CLAUDE.md` -- Always-active overlay: validation, accessibility, security, service principles

## JiT Tooling

Mycelium is **language-agnostic** and **product-type-agnostic**. When a delivery diamond begins, auto-detect the tech stack (or product type), generate appropriate validation, and confirm with the user. See `.claude/jit-tooling/detector.md`.

## Usage & Orchestration

Solo developers use canvas as shared memory with the agent. Teams commit canvas to git as shared product documentation. For parallel exploration, use `/fan-out` with worktree-isolated worker agents.

See `.claude/orchestration/modes.md` for usage patterns and `.claude/orchestration/agent-teams.md` for parallel orchestration.

## Operations & Maintenance

- **Day-to-day**: `.claude/orchestration/operations.md` -- Session resumption, canvas maintenance, diamond lifecycle, memory pruning
- **Escape hatch**: `.claude/orchestration/escape-hatch.md` -- Legitimate process bypass for emergencies. Must be documented and paid back.

## Skills

All 45 skills are auto-discovered from `.claude/skills/*/SKILL.md`. Suggested skills are surfaced at diamond transitions by `/diamond-progress` and `/diamond-assess`, and contextually by hooks. Type `/` to see the current list.

## Getting Started

If the canvas is empty (new project), start with:
```
/interview
```

If the canvas is populated (continuing work), start with:
```
/diamond-assess
```

The system will guide you from there.
