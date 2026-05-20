# Decision Log

**Audience**: internal — published as audit trail, not as public reading.

Record of significant decisions made during product development. Decisions are immutable once logged -- if a decision is reversed, log a new entry that references the original.

## Format

```
### [DATE] - [SHORT TITLE]
- **Diamond**: [ID, scale, phase]
- **Decision**: What was decided.
- **Why_not_alternatives** (structured, per-alternative): list every option considered and a one-line rejection rationale per option. Contrastive explanations ("why X rather than Y") land harder than purely positive ones (Liao et al. 2020); this field must be populated for any decision with ≥1 real alternative. Format:
    - `Option A: <one-line rejection rationale>`
    - `Option B: <one-line rejection rationale>`
- **Theory**: Which framework/theory informed this decision (e.g., "Cynefin - Complex domain", "Cagan - Four Risks").
- **Evidence**: What data or research supports this decision.
- **Confidence**: [0.0-1.0] How confident are we, and what would change this.
- **Scenario ref**: [optional — which scenario from scenarios.yml does this decision serve? Keeps architecture decisions connected to user context. Hoskins: "Draw a line between the problem and the why."]
- **Reversibility**: [easily reversible | costly to reverse | irreversible]
```

## Decisions

### Diamond Assessment 2026-05-20 — L0 +0.02, L1 held
- **Diamonds assessed**: L0 Purpose (Develop, 0.61) and L1 Strategy (Discover, 0.24), both active per `mycelium-roadmap/.claude/diamonds/active.yml`
- **Trigger**: `/mycelium:diamond-assess` invoked 2026-05-20 following Edith-Mari Pedersen Bartnes user-test signal (first non-developer end-to-end user; content_publication product-type; brief-synthesis affective recognition moment; "really seen" assumption-test feedback; one corrections.md graduation = "You are here" wayfinding extension at phase transitions, shipped v0.23.28)
- **Pre-assessment human read** (cognitive forcing per Buçinca et al. CHI 2021): "The latest user test might move us a little further, I hope." Cautious-optimistic, evidence-graded, no over-claim. Logged before agent analysis.
- **Decision**: Increment L0 confidence 0.61 → 0.63 (half-weight behavior-validation signal absorbed). Hold L1 at 0.24 — the 2026-05-12 devils-advocate rule ("no further L1 increments from positioning-only signals until ≥1 behavior-validation lands") was framed for arms-length validation; Edith-Mari is relationship-class. Wait for ht-014/ht-015 cohort arms-length signal before L1 movement.
- **Why_not_alternatives**:
    - `Increment L1 0.24 → 0.26 (full-weight Edith-Mari signal)`: rejected — relationship-class behavior-validation is real but distinct from arms-length. Treating it as equivalent would erode the 2026-05-12 rule's discipline and risk shifting-the-burden archetype (relying on relationship-class signal to skip arms-length validation).
    - `Advance L0 Develop → Deliver`: rejected — single half-weight signal isn't density. Develop→Deliver needs multiple arms-length behavior-validations, not a positioning-shift triggered by one emotional moment.
    - `Hold L0 at 0.61 (no increment)`: rejected — that would be ignoring real behavior-validation evidence. Half-weight increment is the honest middle.
    - `Pivot purpose framing based on the affective-recognition moment`: rejected — emotional resonance is evidence FOR the existing brief-synthesis-as-identity-mirror thesis, not evidence FOR a new framing. No JTBD/positioning shift warranted.
- **Theory gate snapshot** (read-before-claim discipline applied; canvas files actually opened):
    - L0 Develop-phase: Evidence pass (multi-source external_human including Bentes, Hoskins, a Juniors.dev presentation attendee, Edith-Mari, plus DORA/Fowler/arxiv positioning); Four Risks partial (value+usability strong, viability thin, feasibility ok); JTBD pass; Cynefin pass (complex); Bias pass-with-risk (three anti-pattern #7 self-audits this week working as expected); Corrections pass (24 entries + today's "You are here" graduation).
    - L1 Discover-phase: gates pending per phase (transition-gating not applicable to Discover-internal state). Behavior-validation rule from 2026-05-12 still active.
- **Canvas health findings**: `active.yml` 8 days stale; `purpose.yml _meta.last_validated` 9 days stale; `landscape.yml last_updated` 4 days stale despite heavy edits since (Torres/DORA/arxiv/Fowler entries postdate); `north-star.yml` input metrics as_of 2026-05-10 (10 days stale). All address as part of this assessment cycle: active.yml + purpose.yml._meta refreshed; landscape.yml left for next pass since the staleness is timestamp-only, content is current.
- **Anti-pattern scan**: anti-pattern #7 risk explicitly engaged — the temptation to read Edith-Mari as transformative validation rather than half-weight relationship-class signal. Pre-emptively addressed by the half-weight framing in both purpose.yml entry and L0 notes. System archetype watch (L1): Shifting-the-Burden risk if Edith-Mari is treated as substitute for arms-length validation.
- **Confidence**: 0.7. Would rise to 0.85 with one arms-length cohort behavior-validation event (ht-014/ht-015). Would fall toward 0.5 if subsequent assessment showed Edith-Mari signal was over-read (recognition was partly relational-trust, not framework-property).
- **Scenario ref**: L0 purpose evidence loop + L1 strategy behavior-validation gate (2026-05-12 rule).
- **Reversibility**: easily reversible. L0 0.63 can decrement back to 0.61 if Edith-Mari signal turns out to be relational-trust artifact rather than framework-property. The half-weight framing itself is the disciplined hedge — explicitly enables future re-classification.

### 2026-05-16 - Re-scope opencode adapter post-Phase-1 (refs prior 2026-05-16 entry)
- **Diamond**: L1 strategy (mycelium-roadmap, landscape)
- **Decision**: Keep the two-lane substrate discipline from the prior 2026-05-16 entry; **defer the opencode adapter PR indefinitely** until either (a) opencode upstream adds a headless prompt-injection event + a structured tool-failure event, OR (b) a real cohort participant adopts opencode as their harness, making the work demand-pulled. Phase 0 (substrate-neutralization audit) still proceeds during cohort wait — it's free option value either way. Phase 2 (adapter PR) does NOT proceed on the prior plan's "after Juniors.dev cohort closes" trigger.
- **Why_not_alternatives**:
    - `Proceed with adapter on the original ~1–3 day estimate`: estimate falsified by Phase 1 runtime tests. New estimate ~1–2 weeks of custom plugin code reproducing three Claude Code primitives. Cost/value inverts before any cohort signal demands the work.
    - `Build the workarounds (tool-wrapper, message-stream parser, edit-guard plugin) now anyway`: speculative — none of these workarounds is needed by anyone today. Building them prophylactically violates the "demand-pulled, not speculative" discipline the framework applies to its own work.
    - `Abandon two-lane discipline entirely`: rejected — substrate neutralization is cheap and reversible; abandoning it would re-bind Mycelium to Claude Code at the substrate level for no gain.
    - `File the opencode upstream feature requests and block on them`: viable but slow; file them as a side-channel signal, don't gate on them. Maintainer responsiveness is unknown.
    - `Ship a TUI-only adapter (skip headless)`: rejected — Mycelium's target use is orchestratable / non-interactive; a TUI-only adapter doesn't serve the framework's actual usage shape.
- **Theory**: Evidence-Guided (Gilad) — adjust plan on new evidence rather than honouring the prior plan; Cagan Four Risks — Phase 1 surfaced usability risk (no headless prompt-injection) and feasibility risk (no failure hook) that weren't visible in desk research; YAGNI applied to the adapter — don't build it until a real user needs it.
- **Evidence**: `docs/receipts/cases/2026-05-16-opencode-phase1-runtime.md`. Three runtime tests against opencode 1.15.1 + local Ollama (llama3.1:8b 32k-ctx) headlessly:
    - `tui.prompt.append`: silent in `opencode run` (TUI-scoped, no headless equivalent documented).
    - `tool.execute.after`: success-only; failed `read` of nonexistent file fires `before` but not `after`.
    - Read-before-Edit: not runtime-enforced; clean edit succeeded on a fresh session with no prior read. Prior binary-inspection conclusion in `2026-05-16-opencode-port-feasibility.md` was **wrong** (binary strings describe what the agent is told, not what the runtime enforces — correction worth logging in `patterns.md`).
- **Confidence**: 0.32. Was 0.55 in the prior 2026-05-16 entry. Would rise to 0.55+ with (a) confirmation that one of the un-tested events (`session.created` headless, `message.part.updated` for failures, or `agent.*`) covers a workable hook surface, OR (b) confirmation that `tui.prompt.append` does mutate the outbound prompt in interactive TUI sessions (preserving an interactive-only adapter as a viable narrower scope).
- **Scenario ref**: same as prior entry — L1 landscape comp-005 + comp-017.
- **Reversibility**: easily reversible. Substrate-neutralization work persists value regardless; adapter work can resume whenever the upstream gaps close or a cohort participant pulls it.

### 2026-05-16 - Adopt two-lane harness path (Claude Code + opencode) [SUPERSEDED by re-scope entry above]
- **Diamond**: L1 strategy (mycelium-roadmap, landscape)
- **Decision**: Treat Mycelium's substrate (canvas, memory, harness docs, validators, SKILL.md tree, decision-log) as **harness-neutral source-of-truth**, and the per-harness surface (`plugins/mycelium/` for Claude Code; future `opencode/` adapter for opencode) as **thin adapters** over it. Plan a 1–3 day adapter PR to land after Juniors.dev cohort feedback (ht-014/ht-015) closes, not before.
- **Why_not_alternatives**:
    - `Single-harness commitment to Claude Code only`: opencode hands-on test 2026-05-16 showed ~1–3 day adapter cost, not 1–2 weeks; option-value of a second runtime exceeds maintenance cost at that scale.
    - `Full runtime shim layer abstracting tool calls`: premature abstraction. The two harnesses diverge on enforcement semantics (hook taxonomy, failure signaling), not just naming. A shim hides exactly the differences that matter for reflexion and pre-task protocol.
    - `Two repos (framework core + per-harness adapters)`: overhead too high for solo maintainer; canvas/memory/decision-log are the product, splitting them across repos breaks the read-before-write substrate.
    - `Wait for opencode feature parity on hooks before starting`: `tool.execute.after` + `tui.prompt.append` are documented and sufficient for a working adapter; gating on perfect parity defers indefinitely.
    - `Ship adapter immediately (this week)`: Juniors.dev cohort is mid-test on Claude Code path; adding a second runtime surface before cohort signal closes splits attention and risks the cohort log being diluted with two-harness friction the cohort isn't testing.
- **Theory**: Wardley (option value of evolved component substitutability); Hashimoto (engineer-out-recurrence applied to harness lock-in as a recurrence class); Cagan (Four Risks — usability risk of porting unverified, value risk of fragmenting energy).
- **Evidence**: `docs/receipts/cases/2026-05-16-opencode-port-feasibility.md`. Worktree-isolated hands-on test: opencode 1.15.1 enforces Read-before-Edit (binary-confirmed), reads CLAUDE.md + AGENTS.md natively, third-party `opencode-agent-skills` plugin gives one-config-line skill discovery from `.claude/skills/` and `~/.claude/plugins/cache/`. Mycelium has zero command files (slash commands are skill-frontmatter-derived). Validators run unchanged.
- **Confidence**: 0.55. Would rise to 0.75 with a working opencode auth session confirming `tui.prompt.append` reaches the model and `tool.execute.after` carries a distinguishable failure signal. Would rise to 0.85 with a real cohort participant choosing opencode as their harness and completing one full diamond cycle on it.
- **Scenario ref**: L1 landscape comp-005 (Claude Code as primary harness) and comp-017 (agent-CLI category, of which opencode is a member). The decision graduates Mycelium's relationship to its harness from "Claude Code plugin" to "harness-portable framework with Claude Code as first runtime."
- **Reversibility**: easily reversible — if opencode adapter PR reveals friction we didn't see (e.g., `tui.prompt.append` is observe-only), we can pause adapter work and remain Claude-Code-only without rework. Substrate stays neutral either way.

