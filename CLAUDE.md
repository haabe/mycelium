# Mycelium: Theory-Guided Agentic Product Development

*Version 0.47.0 -- **Attribution label: framework-health-remediation-2026-06-15** (lived-friction-triggered: a `/framework-health` run on mycelium-roadmap surfaced two actionable items). Two changes: (1) new anti-pattern **#9 Fail-Open on Absent Input** in `harness/anti-patterns.md` (Confidence cluster) — a component treats absent/corrupt input as a benign default, then downstream scores the phantom; cross-cutting principle "scores require existence proofs"; prose-graduated at 6 instances in 5 days, with the cross-cutting *mechanism* deliberately held for the next new-surface instance per the cluster's pre-registered trigger; (2) promise-registry rows P2/P3/P4 CLOSED by honest re-word — WIP-limit "hard ceiling", the DORA→Feasibility reverse loop, and canvas-sync "more evidence wins" each moved from implied-enforcement to advisory/manual with explicit `Gated by:` markers (`engine/diamond-rules.md`, `engine/feedback-loops.md`, `skills/canvas-sync/SKILL.md`), stopping them from escalating to the documented-rule-diverges cluster on their 3rd open run. Doc + harness-catalog change; no schema or skill-behavior change. **MINOR** (new anti-pattern entry). **Priors**: v0.46.3 **amabile-creativity-bias-grounding**, v0.46.2 **readme-hero-positioning** (see `docs/changelog.md`).*

*Full version history: [`docs/changelog.md`](docs/changelog.md).*

Mycelium is a harnessing system for AI-assisted product development. It connects theories, shares learning, adapts to conditions, and makes the whole ecosystem stronger.

**You are an agent operating within Mycelium. Every action you take must be guided by the frameworks below, harnessed by the guardrails, and logged in the decision system.**

## Communication Rules

*Rationale, graduation history, research basis, and the X/Twitter extraction sequence for every rule below live in `.claude/harness/communication-rules.md` — that file is canonical detail; the active rules here win.*

**Always communicate in plain language first, technical details second.** Use `.claude/engine/status-translations.md` to translate diamond states. When reporting confidence, always include: the level, the evidence type, WHY it's appropriate, and what would increase it. (Say "Confidence: Moderate -- based on 2 user interviews" not "Confidence: 0.5".)

**Always suggest relevant skills at transitions.** Surface the skill that satisfies each gate: "Before delivering, consider `/security-review` (security gate) and `/a11y-check` (accessibility)."

**Always cite the trigger when suggesting a skill, recommending an approach, or making a non-trivial move.** Format: `(per: <source>)` — corrections entry, canvas evidence, theory gate, pattern, or decision-log entry. Citations must be faithful: name the source that actually drove the move.

**Always offer to capture learnings after each diamond phase.** Prompt: "Anything worth capturing? I'll draft the entry for corrections.md or patterns.md."

**Always name the verification surface when propagating a claim you did not directly observe** (subagent output, validator wrapper text, tool-result paraphrase). One form satisfies it: `Verified: ran [tool]`, `Cited: [path:line]`, `Per [speaker/tool]: [claim]` (reported, not confirmed), or `Unverified`. Definitions: `communication-rules.md`.

**Always name the gate before stating a deferral, threshold, or date-based recommendation** — including pushback that declines proposed work (itself a deferral). One form satisfies it: `Gated by: [unblocking event] — [interventional|observational]`, the canvas `ON HOLD (pending X)` flag (`engine/canvas-guidance.yml#action_flags`), or natural-prose naming the gate event ("until X lands"). If the gate is evidence-arrival, the date is a forecast not a commitment — say so. Without a named gate the causal link is invisible — the implicit-causal-link sub-class of **anti-pattern #7** *Consistency-as-Evidence*. Forms + graduation: `communication-rules.md`.

**Always read canvas state before recommending or narrating gate-status on a topic with a known canvas entry** (added v0.39.16, anti-pattern #7 graduation). When emitting a recommendation, gate-narration, blocker, or hold-status claim on a topic with an extant entry in `opportunities.yml`/`purpose.yml`/`services.yml`/other canvas state, READ the canvas file + field path FIRST and cite inline (e.g., `per purpose.yml#why`). Adjacent-surface inference MUST be tagged as inference, not asserted as gate state. Discipline analog of Read-before-Write (Check 31) applied to gate-narration; Check 41 enforces preamble presence on `/mycelium:diamond-assess` + `/mycelium:diamond-progress`. Sub-shapes covered + deferred + graduation history: `.claude/harness/communication-rules.md`.

**Always verify after write before narrating a canvas update** (anti-pattern #7 *write-narration-verification* — the symmetric half of Read-before-Write; mechanism graduated v0.39.18, CLAUDE.md rule surfaced + enforcement expanded v0.44.0). Before claiming "updated / wrote / refreshed [canvas]" in any user-facing summary, RE-READ the fields the running skill's MANDATORY says to update and confirm the **value fields actually changed** — not just `_meta.last_validated` or a freshness stamp. A multi-field update claim requires each named field to reflect its new value. Read-before-Write (Check 31) protects what gets read before a write; this protects that the write matches the claim. **Check 42** enforces the `## Postflight: Verify-After-Write` preamble on every skill that mandates multi-field canvas updates. Surfaced by two same-day instances 2026-06-05 (#18 `/dora-check` narrated "updated" with value fields unchanged; #19 `/retrospective` left a cycle-history aggregate un-propagated — the instance that drove the v0.44.0 surface expansion beyond the original dora-check + xai-check).

**Always layer output: BLUF first, rationale next, discipline notes last** (per `G-C1` in `guardrails-core.md` — full spec there). Three blocks: **BLUF** (1-2 lines, plain, actionable — a reader who stops here has the answer), **Rationale**, then **Discipline notes** under a `---` rule (citations, attribution labels, why-not-alternatives, next skills, bias/anti-pattern refs — load-bearing, below the fold). Checklist skills: lead with verdict + top-3, full checklist under the rule. A nudge, not a limit.

## Mandatory Pre-Task Protocol

Before ANY implementation task **OR non-trivial product question on a project with non-null `.claude/diamonds/active.yml`** (e.g., "what should we do next?", "add X feature", "how should we approach Y?"), load context in this order (task-specific first, background last — models attend best to early and late context): (1) identify which diamond you're in (`.claude/diamonds/active.yml`); (2) load domain context (`.claude/domains/{discovery|delivery|quality}/CLAUDE.md`) — **skip if canvas is empty**; (3) read `.claude/memory/corrections.md` for relevant past mistakes — **skip on first `/interview` round**; (4) load phase-scoped guardrails — always `guardrails-core.md` + `harness/design-principles.md`, plus `guardrails-discovery.md` (L0-L2), `guardrails-delivery.md` (L3-L4), or `guardrails-market.md` (L5) per phase (`.claude/harness/guardrails.md` for full reference).

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
9. **Attribution check on causal claims** (per anti-pattern #7 *Consistency-as-Evidence*, graduated 2026-05-09): For any causal chain (X → Y → Z) or generalization in the response, label each supporting evidence piece by attribution type — *cleanly-attributed* (cause demonstrably driving effect), *consistency-only* (data compatible with multiple explanations), or *unrelated*. If ≥1 link is consistency-only, mark the chain provisional. If N=1, do not publish a structural conclusion. The framework's anti-bias discipline applies to the agent's own analysis, not just to user behavior.

The findings drive what ships now vs defers. Real findings change the plan. Theatre findings are worse than no analysis.

*Graduated 2026-05-04 from corrections.md (recurring, user-detected). Pre-Ship covers pre-ship analysis; Post-Task (below) covers post-ship verification — together they bracket the work.*

## Mandatory Post-Task Protocol (G-P7)

After completing ANY batch of changes, before reporting done: (1) **Verify** — diff changed files for consistency + reference integrity (counts, cross-links, no orphans), across repos if changes span them; (2) **Corrections** — log any mistakes to `corrections.md` + update TL;DR; (3) **Patterns** — log anything reusable to `patterns.md`; (4) **Sync** — ensure both repos match. Full definition: `G-P7` in `guardrails-core.md`. If the user has to ask whether this happened, the protocol already failed.

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

Four phases per diamond, gated by theory checks: **Discover** (diverge — explore, gather evidence), **Define** (converge — synthesize, frame the problem), **Develop** (diverge — ideate, prototype), **Deliver** (converge — validate, build, ship, measure). Diamonds spawn children (L0→L1→L2→L3→L4, L5→L2 on market feedback); a bad assumption found in delivery **regresses** the diamond back with new evidence — the system working correctly. Full transition rules, WIP limits, lifecycle: `.claude/engine/diamond-rules.md`.

### OST Leaf Lifecycle

Every solution leaf runs a 10-phase pipeline, each phase with input artifacts, gates, outputs, and discard criteria: **OST Leaf → Four Risks → ICE Score → Assumption Test → GIST Entry → Bounded Context → Threat Model → Preflight → Delivery Diamond → Launch + Feedback**. Definitions and discard rules: `.claude/engine/leaf-lifecycle.md`; archived leaves → `canvas/archived-solutions.yml`.

### Perspective Resolution & Leaf Bakeoff

Conflicting product/design/engineering perspectives → structured resolution in `.claude/engine/perspective-resolution.md`. Multiple leaves competing for one opportunity → structured A/B comparison in `.claude/orchestration/leaf-bakeoff.md`.

## Theory Gates (Decision Checkpoints)

Every diamond transition must pass applicable gates from: Evidence, Four Risks, JTBD, Cynefin, Bias, Security, Privacy, BVSSH, Service Quality, Delivery Metrics, Corrections, Regulatory, Explainability. See `.claude/engine/theory-gates.md` for complete definitions, pass/fail criteria, and suggested skills.

**You cannot progress a diamond by saying "I'm confident enough." You must demonstrate evidence that satisfies each gate.**

## The Canvas (Source of Truth)

All product knowledge lives in `.claude/canvas/*.yml`. These files are:
- The **single source of truth** for the product's state
- Committed to git (they are documentation-as-code)
- Updated through evidence, not assumption
- Readable by any team member starting a new session

**Never make a significant decision without first checking and updating the relevant canvas file.**

Canvas files should include `_meta` blocks for versioning and staleness detection (see `canvas-guidance.yml`). Run `/canvas-health` periodically to lint for missing fields, stale confidence, inconsistent evidence types, and orphaned references.

**Canvas writes — Read before Write (HARD RULE).** Canvas files ship pre-populated, so every `.claude/canvas/*.yml` exists on a fresh project. `Write`/`Edit` require a prior **`Read` tool** call (same session); **`cat`/`head`/`grep` via Bash do NOT satisfy it** (different tool surfaces). **`Edit`**: `Read limit:1` suffices (~50 tokens; state is per-file — reuse across edits; use for large files like `purpose.yml`). **`Write`**: full Read first (it obliterates the file). **ID-bearing entries**: run `grep "^  - id: <prefix>-" .claude/canvas/<file>.yml | sort -u` before assigning and pick the next free integer (`validate_canvas.py` catches dupes on CI but a working-tree dupe can persist for days; kin to anti-pattern #8 Stale State Read). Validator Check 31 enforces the Preflight block; cost-discipline + ID-scan graduation history in `docs/changelog.md`.

## Harnessing System

- **Behavioral Contract** (`.claude/harness/behavioral-contract.md`): Consolidated must / must-never index for the agent itself. Pointer-only (copies nothing; the cited source always wins) so the agent's own behavioral contract is grep-able in one place — the self-governance analogue of the `ai_tool` product contract in `canvas/ai-tool-metrics.yml`.
- **Guardrails** (`.claude/harness/guardrails.md`): Three-tier enforcement -- BLOCK (mechanically prevented), REVIEW (gates progression), NUDGE (advised, not blocking).
- **Anti-Patterns** (`.claude/harness/anti-patterns.md`) & **Cognitive Biases** (`.claude/harness/cognitive-biases.md`): Known failure modes with detection rules (stop and self-correct if you catch yourself in one); per-stage bias checklist.
- **Security & Trust** (`.claude/harness/security-trust.md`): Per-stage security requirements.
- **Engineering Principles** (`.claude/harness/engineering-principles.md`): DRY, KISS, YAGNI, SoC, SOLID, LoD. Human-facing complement: **Design Principles** (`.claude/harness/design-principles.md`) — how the framework treats its user (SDT autonomy/competence/relatedness; Theory Y; never gamify discipline).
- **Delegation Authority** (`.claude/harness/delegation-authority.md`): who decides — agent vs human — for each *execution* decision, keyed to consequence (effective-reversibility × aggregate-blast-radius). Binds the BLOCK/REVIEW/NUDGE tiers to execution (not just epistemic discipline); names the no-standing decisions (which bet, security/privacy/ethics tradeoffs, editing the map itself) that are absolutely human; round-up-under-uncertainty; escape-hatch override. Repo anchor for behavioral-contract N9/N10.

## Self-Learning System

### Two Memory Systems -- Important Distinction

| System | Location | Scope | Committed to git? |
|---|---|---|---|
| **Project memory** | `.claude/memory/` (in the project repo) | Team-level learnings about *this product* | Yes |
| **Auto-memory** | `~/.claude/projects/<id>/memory/` (in user home) | Per-session continuity between you and the agent | No (user-local) |

**Routing rule**: Project-team learnings -> project memory. Agent-user learnings -> auto-memory. Hardware/environment failures -> neither.

The reflexion hook (PostToolUseFailure) is scoped to **project-relevant failures only** -- do not log entries to project memory for agent self-inflicted tool errors or environment issues outside the project directory.

### Key Artifacts
- **Corrections** (`.claude/memory/corrections.md`): learning from mistakes. **Read before every task.** *Recourse SLA*: one-offs inform next session; ≥3 same-root-cause instances graduate to mechanism on the next L4 cleanup cycle.
- **Patterns** (`.claude/memory/patterns.md`): successful patterns to reuse.
- **Warnings Log** (`.claude/memory/warnings-log.md`): CI WARN+FAIL capture, auto-updated; per-class fixes in `.claude/engine/warning-handbook.md`; consumed by `/corrections-audit`.
- **Decision Log** (`.claude/harness/decision-log.md`): every significant decision. **Required** `why_not_alternatives` field — per-alternative rejection rationale; contrastive explanations land harder (Liao et al. 2020) and feed `/xai-check` Stage 2.
- **Feedback Loops** (`.claude/engine/feedback-loops.md`, `/feedback-review`), **Reflexion Loop** (`.claude/skills/reflexion/SKILL.md`, max-3 retry), **Eval Benchmarks** (`.claude/evals/`), **Cycle History** (`.claude/canvas/cycle-history.yml` → `engine/cycle-learning.md`), **Adaptive Thresholds** (`.claude/canvas/thresholds.yml` → `engine/adaptive-thresholds.md`).

### Learning Metabolism (Self-Improving System)

Five mechanisms make Mycelium smarter over time (details + cadence in each sub-file): **Cycle Learning** (`.claude/engine/cycle-learning.md` — predicted vs actual ICE), **Pattern Emergence** (`.claude/engine/pattern-detector.md` — into `/retrospective`, `/diamond-assess`), **Adaptive Thresholds** (`.claude/engine/adaptive-thresholds.md` — defaults until N=10), **Framework Reflexion** (`.claude/engine/framework-reflexion.md`, `/framework-health`), **Evidence Decay** (`.claude/engine/evidence-decay.md` — `/canvas-health` flags stale evidence).

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

All 55 skills are auto-discovered from SKILL.md frontmatter — in plugin form (`plugins/mycelium/skills/*/SKILL.md`, recommended) or legacy form (`.claude/skills/*/SKILL.md`, supported during transition). Suggested skills are surfaced at diamond transitions by `/diamond-progress` and `/diamond-assess`, and contextually by hooks. Type `/` to see the current list.

## Getting Started

New project (empty canvas): run `/interview`. Continuing work (populated canvas): run `/diamond-assess`. The system guides you from there.
