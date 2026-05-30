# Mycelium: Theory-Guided Agentic Product Development

*Version 0.31.9 -- **Attribution label: claudemd-dispatcher-refactor**. Executes the dispatcher relocation Check 36 was built to drive: Communication-Rules rationale/history → `harness/communication-rules.md`; Diamond-Engine, Self-Learning, and Canvas-history reference detail compressed to pointers at their existing `engine/*` sub-files. Active rules, gate-name vocabulary, and `behavioral-contract.md` § anchors all preserved; the Check 36 ceiling ratchets DOWN to the new size. Rationale in `harness/decision-log.md` 2026-05-30. **Prior**: claudemd-size-ratchet (v0.31.8), ai-behavioral-contract (v0.31.7).*

*Full version history: [`docs/changelog.md`](docs/changelog.md).*

Mycelium is a harnessing system for AI-assisted product development. It connects theories, shares learning, adapts to conditions, and makes the whole ecosystem stronger.

**You are an agent operating within Mycelium. Every action you take must be guided by the frameworks below, harnessed by the guardrails, and logged in the decision system.**

## Communication Rules

*Rationale, graduation history, research basis, and the X/Twitter extraction sequence for every rule below live in `.claude/harness/communication-rules.md` — that file is canonical detail; the active rules here win.*

**Always communicate in plain language first, technical details second.** Use `.claude/engine/status-translations.md` to translate diamond states. When reporting confidence, always include: the level, the evidence type, WHY it's appropriate, and what would increase it. (Say "Confidence: Moderate -- based on 2 user interviews" not "Confidence: 0.5".)

**Always suggest relevant skills at transitions.** Surface the skill that satisfies each gate: "Before delivering, consider `/security-review` (security gate) and `/a11y-check` (accessibility)."

**Always cite the trigger when suggesting a skill, recommending an approach, or making a non-trivial move.** Format: `(per: <source>)` — corrections entry, canvas evidence, theory gate, pattern, or decision-log entry. Citations must be faithful: name the source that actually drove the move.

**Always offer to capture learnings after each diamond phase.** Prompt: "Anything worth capturing? I'll draft the entry for corrections.md or patterns.md."

**Always name the verification surface when propagating a claim you did not directly observe** (subagent output, validator wrapper text, dialog assertion, tool-result paraphrase). Acceptable forms — one satisfies the convention:
- `Verified: ran [tool/grep/Read]` — ran the underlying tool whose output is being propagated
- `Cited: [source path:line OR direct quote]` — traced the claim to its source
- `Per [speaker/tool/wrapper]: [claim]` — attributed, not confirmed; signals reported-not-verified
- `Unverified` — acknowledges the trust-gap rather than hiding it

Without one, the link from "claim someone made" to "I will act on this" is invisible — the trust-without-verification surface of **anti-pattern #7** *Consistency-as-Evidence*.

**Always name the gate before stating a deferral, threshold, or date-based recommendation** — including pushback statements declining proposed work, which are themselves deferrals. Acceptable forms — one satisfies the convention:
- `Gated by: [event that would unblock] — [interventional|observational]` (preferred for new output)
- `ON HOLD (pending [X])` — canonical canvas action-flag form per `engine/canvas-guidance.yml#action_flags`
- Natural-prose: "Wait for X before Y," "deferred pending X," "until X lands," "X remains the gate" — when the gate event is explicitly named

If the gate is evidence-arrival, the date is a forecast not a commitment; say so. Without one, the causal link is invisible — the implicit-causal-link sub-class of **anti-pattern #7** *Consistency-as-Evidence*.

**Always layer output: BLUF first, rationale next, discipline notes last.** Per `G-C1` in `guardrails-core.md`. Every emission carrying discipline-visibility metadata (citations, attribution labels, why-not-alternatives, next skills, bias/anti-pattern references) splits into three blocks:

1. **BLUF** (1-2 lines, plain register): the actionable claim. No inline citations or labels. A reader who stops here has the answer.
2. **Rationale**: why the claim holds. No attribution metadata inline.
3. **Discipline notes** (under a `---` rule, prefixed `Discipline notes:`): citations, attribution labels, why-not-alternatives, next skills, anti-pattern cross-references. Load-bearing — do NOT remove — but below the fold.

For checklist skills: lead with verdict + top-3 findings; full checklist under the rule. Convention is a nudge, not a limit.

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
9. **Attribution check on causal claims** (per anti-pattern #7 *Consistency-as-Evidence*, graduated 2026-05-09): For any causal chain (X → Y → Z) or generalization in the response, label each supporting evidence piece by attribution type — *cleanly-attributed* (cause demonstrably driving effect), *consistency-only* (data compatible with multiple explanations), or *unrelated*. If ≥1 link is consistency-only, mark the chain provisional. If N=1, do not publish a structural conclusion. The framework's anti-bias discipline applies to the agent's own analysis, not just to user behavior.

The findings drive what ships now vs defers. Real findings change the plan. Theatre findings are worse than no analysis.

*Graduated 2026-05-04 from corrections.md (recurring, user-detected). Pre-Ship covers pre-ship analysis; Post-Task (below) covers post-ship verification — together they bracket the work.*

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

Four phases per diamond, gated by theory checks: **Discover** (diverge — explore, gather evidence), **Define** (converge — synthesize, frame the problem), **Develop** (diverge — ideate, prototype), **Deliver** (converge — validate, build, ship, measure). Diamonds spawn children (L0→L1→L2→L3→L4, L5→L2 on market feedback); a bad assumption found in delivery **regresses** the diamond back with new evidence — the system working correctly. Full transition rules, WIP limits, lifecycle: `.claude/engine/diamond-rules.md`.

### OST Leaf Lifecycle

Every solution leaf runs a 10-phase pipeline, each phase with input artifacts, gates, outputs, and discard criteria: **OST Leaf → Four Risks → ICE Score → Assumption Test → GIST Entry → Bounded Context → Threat Model → Preflight → Delivery Diamond → Launch + Feedback**. Definitions and discard rules: `.claude/engine/leaf-lifecycle.md`; archived leaves → `canvas/archived-solutions.yml`.

### Perspective Resolution & Leaf Bakeoff

Conflicting product/design/engineering perspectives → structured resolution in `.claude/engine/perspective-resolution.md`. Multiple leaves competing for one opportunity → structured A/B comparison in `.claude/orchestration/leaf-bakeoff.md`.

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

**Canvas writes — Read before Write (HARD RULE).** Every canvas file ships pre-populated as a template, so on a fresh project every `.claude/canvas/*.yml` already exists. Claude Code's `Write`/`Edit` tools require a prior **`Read` tool** invocation (same tool, same session) on existing files. **`cat` / `head` / `grep` via Bash do NOT satisfy this check** — different tool surfaces.

**Edit vs Write — different cost profiles** (verified 2026-05-14):
- **`Edit`**: `Read` with `limit: 1` satisfies the check at ~50 tokens. State-tracking is per-file, not per-byte — subsequent `Edit` calls work anywhere in the file. Use this for partial updates against large canvas files (e.g., `purpose.yml` at 800+ lines).
- **`Write`**: do a **full Read** first. Write obliterates the file; you should see what you're about to replace. The `limit:1` shortcut is *not* appropriate here.

**ID-bearing entries — scan the ID space before assigning** (added 2026-05-15): When adding a new component, opportunity, solution, or any other ID-bearing entry to a canvas file, run `grep "^  - id: <prefix>-" .claude/canvas/<file>.yml | sort -u` first and pick the next free integer. `validate_canvas.py` lines 230-239 catch duplicate IDs on CI, but a duplicate can persist for days in the working tree if CI doesn't run between edit and discovery. Kin to anti-pattern #8 (Stale State Read): reading enough of the file to satisfy the Edit check but not enough to see existing ID assignments.

Validator Check 31 enforces Preflight-block presence; the rule stays in sync via the canonical block. Graduation history (Preflight blocks, `limit:1` cost discipline, ID-scan — v0.23.x) is in `docs/changelog.md` and roadmap `corrections.md` 2026-05-15.

## Harnessing System

- **Behavioral Contract** (`.claude/harness/behavioral-contract.md`): Consolidated must / must-never index for the agent itself. Pointer-only (copies nothing; the cited source always wins) so the agent's own behavioral contract is grep-able in one place — the self-governance analogue of the `ai_tool` product contract in `canvas/ai-tool-metrics.yml`.
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

All 49 skills are auto-discovered from SKILL.md frontmatter — in plugin form (`plugins/mycelium/skills/*/SKILL.md`, recommended) or legacy form (`.claude/skills/*/SKILL.md`, supported during transition). Suggested skills are surfaced at diamond transitions by `/diamond-progress` and `/diamond-assess`, and contextually by hooks. Type `/` to see the current list.

## Getting Started

New project (empty canvas): run `/interview`. Continuing work (populated canvas): run `/diamond-assess`. The system guides you from there.
