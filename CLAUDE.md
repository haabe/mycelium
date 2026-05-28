# Mycelium: Theory-Guided Agentic Product Development

*Version 0.31.4 -- **Attribution label: contributor-credit-receipts**. Doc-only credit + receipts backfill following `/framework-health` (2026-05-28). Names two consented cohort contributors who had shaped the framework but weren't yet credited: **Frida** (v0.23.9 first-run friction batch + cohort-tester-1 vocabulary finding) and **Alex** (v0.31.x output-density + post-build-silence) — CONTRIBUTORS.md entries + three receipts cases (`frida-first-run`, `alex-cohort-first-run`, `canvas-drift-reconciliation` self-correction). Frida's project is named only by the approved generic descriptor, never directly (consent carve-out). Also reconciles `cluster-instances.md` (instance 15: canvas-drift graduated via v0.31.3; framework-vs-roadmap log-divergence noted) and records the router-discipline eval re-run (PASS, improved vs 2026-05-03 baseline). **PATCH per version-discipline**: doc-only (CONTRIBUTORS + docs/receipts), no behavioral change. **Attribution class**: maintenance-housekeeping — credit backfill surfaced by `/framework-health` plus the Frida-vs-Alex asymmetry the maintainer caught ("did Frida get credited?"). v0.31.3 entry in docs/changelog.md per Check 34.* **Prior**: human-task-reconciliation (v0.31.3).

*Full version history: [`docs/changelog.md`](docs/changelog.md).*

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

**Always name the verification surface when propagating a claim from a tool, subagent, validator, or dialog assertion.** Applies when the agent is about to confirm, act on, or pass-through a claim that originated outside the agent's own direct observation: subagent outputs, validator wrapper text ("includes pre-existing tech debt"), dialog assertions ("X installed it"), tool result paraphrases, ranked-list summaries from `gh api` / similar. Acceptable forms (any one satisfies the convention):
- Explicit verified: `Verified: ran [tool/grep/Read]` — agent actually ran the underlying tool whose output is being propagated
- Explicit cited: `Cited: [source path:line OR direct quote]` — agent traced the claim to its source
- Explicit per: `Per [speaker/tool/wrapper]: [claim]` — agent attributes the claim to its source without claiming verification; signals the claim is reported, not confirmed
- Explicit unverified: `Unverified` — agent acknowledges propagating without verification; surfaces the trust-gap rather than hiding it

Without any of these forms, the inferential link from "claim someone made" to "I will act on this" is invisible and unverifiable. This is the **trust-without-verification surface of anti-pattern #7** *Consistency-as-Evidence* — historically sub-class (e) subagent-output-verification, generalized 2026-05-23 to cover any tool/wrapper/dialog claim the agent didn't independently verify. Recurrence shape: agent reads "pre-existing tech debt" in validator wrapper text and propagates without running the underlying lint; agent agrees with founder claim about a named user's behavior without challenging the evidence source; agent accepts subagent's claim about a Mycelium file without grep-verifying.

First propagation surface (subagent-output-verification, 2026-05-11) — generalized 2026-05-23 after the EXE001 instance where the validator's "pre-existing" wrapper text was propagated without running ruff. Same graduation philosophy as `Gated by:` (Grice maxim of quantity; Sperber & Wilson relevance theory): make the interpolation visible, don't try to eliminate it. Convention is grep-detectable post-publish; a propagation without any verification form fails the check. Candidate Check N+2 mechanism flagged in corrections.md.

**For X / Twitter URLs specifically**: attempt playwright + nitter.net extraction before defaulting to `Per user:` summary. The WebFetch surface fails on X (HTTP 402 paywall) and on most Nitter mirrors; playwright with full-browser rendering succeeds where lighter fetchers don't (verified 2026-05-24 across 4 thread verifications). Sequence: try `mcp__playwright__browser_navigate` → `mcp__playwright__browser_evaluate` to extract `.tweet-content` text; if Nitter returns empty, accept `Per user:` summary or ask for paste. agent-browser CLI also installed but does not work for Nitter pages (renders empty body; see roadmap decision-log 2026-05-24 benchmark).

**Always name the gate before stating a deferral, threshold, or date-based recommendation.** Applies to all recommendations stating "defer to [date]," "ship at [threshold]," "act when [N]," "after [date]," "before [date]," or "until [N]" — including pushback statements declining proposed work (e.g., "we shouldn't ship X now because Y") which are themselves deferral statements. Acceptable forms (any of these satisfies the convention):
- Explicit format: `Gated by: [event that would unblock] — [interventional|observational]` (preferred for new agent output where ambiguity would otherwise hide the implicit causal link)
- Canvas-state form: `ON HOLD (pending [X])` — already canonical for canvas action flags per `engine/canvas-guidance.yml#action_flags`, semantically equivalent
- Natural-prose form: "Wait for X before Y," "deferred pending X," "until X lands," "X remains the gate" — compliant when the gate event is explicitly named in the surrounding sentence

If the gate is evidence-arrival, the date is a forecast not a commitment; say so. Without ANY of these gate-naming forms, the implied causal link between the date/threshold and the unblock event is invisible and unverifiable, which is the **implicit-causal-link sub-class of anti-pattern #7** *Consistency-as-Evidence* (graduation philosophy: make the interpolation visible, don't try to eliminate it — Grice maxim of quantity; Sperber & Wilson relevance theory).

First trigger instance 2026-05-23 (capacity-vs-evidence-gating conflation in BVSSH-on-l0-purpose deferral); same-turn recurrence at agent's own scope-pushback surface (2nd instance same day) confirmed convention must apply to pushback statements. Pre-Ship #9 ran without catching either instance because the causal link was implicit, not explicit. Inventory of pre-existing framework prose 2026-05-23: ~0 hard violations, ~8 soft format-mismatches (gate present, alternate form) — the convention's role is to close the agent-output surface that lacked any gate-naming convention, NOT to retrofit existing well-formed canvas-state or natural-prose gate naming. Candidate Check N+1 mechanism flagged in corrections.md; graduation criterion is a 2nd hard-violation instance post-convention.

**Always layer output: BLUF first, rationale next, discipline notes last.** Per `G-C1` in `guardrails-core.md`. Every emission carrying discipline-visibility metadata (citations, `verified | consistency_only | unverified` labels, why-not-alternatives, recommended next skills, bias warnings, anti-pattern references) should split into three blocks:

1. **BLUF** (1-2 lines, plain register): the actionable claim — verdict, recommendation, finding, or next step. No inline citations, no attribution labels, no theory name-drops. A reader who stops here has the answer.
2. **Rationale** (scannable middle block): why the claim holds. No attribution metadata inline.
3. **Discipline notes** (under a `---` rule, prefixed `Discipline notes:`): citations, attribution labels, why-not-alternatives, recommended next skills, anti-pattern cross-references, source attributions. Load-bearing — do NOT remove — but lives below the fold.

For checklist skills (`/mycelium:security-review`, `/mycelium:a11y-check`, `/mycelium:definition-of-done`): lead with overall verdict + top-3 findings; full per-category checklist under the rule. For decisions: why-not-alternatives collapses to one summary line in the body ("considered N alternatives — see notes below"), expanded in the trailing block. Convention is a nudge, not a limit — 3-line and 50-line emissions both satisfy it as long as layering holds.

Example pattern: `Recommendation: ship as experiment, with explicit kill criteria. \n\n Two of three evidence pieces are consistency-only and one is unverified — direction is plausible but not yet attributed. \n\n --- \n Discipline notes: Evidence — 2 consistency_only, 1 unverified (per AP#7, Technique 4). Why-not-alts — (a) defer = no evidence; (c) drop = premature.`

Graduated 2026-05-26 from cohort-tester-2 friction log ("brain fried from gigantic walls of text"). Research basis: Sweller (CLT), Cowan 2001 (working memory ≈4 chunks), Nielsen NN/g (F-pattern), Minto Pyramid, BLUF (military/business), W3C COGA + WCAG 3.0 cognitive accessibility. The chain "wall-of-text → comprehension failure → cohort attrition" is `consistency_only` at N=1 — convention is research-informed, not research-validated for this surface; `/mycelium:prompt-optimizer` A/B is the right next step.

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

**Canvas writes — Read before Write (HARD RULE).** Every canvas file ships pre-populated as a template, so on a fresh project every `.claude/canvas/*.yml` already exists. Claude Code's `Write`/`Edit` tools require a prior **`Read` tool** invocation (same tool, same session) on existing files. **`cat` / `head` / `grep` via Bash do NOT satisfy this check** — different tool surfaces.

**Edit vs Write — different cost profiles** (verified 2026-05-14):
- **`Edit`**: `Read` with `limit: 1` satisfies the check at ~50 tokens. State-tracking is per-file, not per-byte — subsequent `Edit` calls work anywhere in the file. Use this for partial updates against large canvas files (e.g., `purpose.yml` at 800+ lines).
- **`Write`**: do a **full Read** first. Write obliterates the file; you should see what you're about to replace. The `limit:1` shortcut is *not* appropriate here.

**ID-bearing entries — scan the ID space before assigning** (added 2026-05-15): When adding a new component, opportunity, solution, or any other ID-bearing entry to a canvas file, run `grep "^  - id: <prefix>-" .claude/canvas/<file>.yml | sort -u` first and pick the next free integer. `validate_canvas.py` lines 230-239 catch duplicate IDs on CI, but a duplicate can persist for days in the working tree if CI doesn't run between edit and discovery. Kin to anti-pattern #8 (Stale State Read): reading enough of the file to satisfy the Edit check but not enough to see existing ID assignments.

Three graduations: (a) the surface-confusion failure (anti-pattern #7 instance #5, 2026-05-09 — agent conflated Bash `head` with the Read tool, lost ~14k tokens to a Write-fail → remedial-full-Read → re-Write loop) was solved at v0.23.x by the Preflight blocks. (b) The second-order cost — agent *correctly* following the rule but full-Reading every time — was solved at v0.23.18 by the `limit:1` discipline (estimated 10–50k tokens/session saved). (c) The ID-allocation gap — agent reads enough to satisfy the Edit check but not enough to see the ID space — was solved at v0.23.19 by the ID-scan discipline (graduated from a single instance 2026-05-14 in the roadmap repo, comp-010 collision; see roadmap `corrections.md` 2026-05-15). Validator Check 31 enforces Preflight presence; the rule's content stays in sync via the canonical block. Detected Juniors.dev pre-run 2026-05-06; structural layer 2026-05-09; cost-tier sharpening 2026-05-14; ID-scan sharpening 2026-05-15.

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

All 49 skills are auto-discovered from SKILL.md frontmatter — in plugin form (`plugins/mycelium/skills/*/SKILL.md`, recommended) or legacy form (`.claude/skills/*/SKILL.md`, supported during transition). Suggested skills are surfaced at diamond transitions by `/diamond-progress` and `/diamond-assess`, and contextually by hooks. Type `/` to see the current list.

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
