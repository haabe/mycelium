# Mycelium: Theory-Guided Agentic Product Development

*Version 0.178.1 -- **Attribution label: the-worst-case-was-the-quietest-one-2026-09-04** (PATCH). `check_confidence_managed.py` reported "no `confidence_derivation` block" at INFO regardless of whether evidence existed — so a diamond with a number nobody can re-derive AND scored instruments standing against it was the LEAST loudly flagged state in the tool. Found within the hour by running the new check across the rest of the dogfood board: three diamonds in exactly that state, one of them **107 days unchanged with five scored instruments naming it**. Severity now depends on whether evidence exists — WARN when it does, INFO when it does not, so a project that has gathered nothing yet is told without being failed and the adoption path stays open. Prior: 0.178.0 -- **Attribution label: evidence-landed-and-nobody-asked-what-it-did-to-the-number-2026-09-04** (MINOR). Five skills instruct an agent to update confidence when evidence lands. **No check ever verified it**, and the only "stale confidence" string in the framework was an example inside a report template. Measured on the dogfood project: a diamond whose confidence had moved ONCE in the project history, then twenty days in which 21 instruments naming it were scored, a pre-registered test returned SUPPORTS on the first attribution evidence the bet had ever had, and a crossing condition written in advance was met three times over. The number never moved and nothing noticed. `check_confidence_managed.py` closes it, and the design constraint matters more than the check: **it never demands that a number MOVE.** Considered-and-unchanged, recorded with a date, is a pass; unexamined is the defect. A guard that pushed confidence upward would be an inflation engine aimed at the one value a project must not inflate. Two failures are recorded in the code because both will recur: the derivation had been stored in a YAML COMMENT and a later rewrite deleted it, so it is a FIELD now and comments are not data; and **the first version of this guard did not bite** -- a 30-day staleness threshold against a 20-day defect, passing the exact case it was written for, so the trigger is evidence rather than the calendar. Prior: 0.177.0 -- **Attribution label: a-version-documented-twice-was-invisible-to-every-reader-2026-09-04** (MINOR). Every reader of the changelog goes through `parse_changelog_versions`, which returns a SET, so a version carrying two `## vX.Y.Z` sections was indistinguishable from one carrying a single section -- in the gap checks, in the counts, everywhere. It is not cosmetic: `notes_for` builds a published Release body from the FIRST matching section, so the others never reach a consumer. v0.108.0 carried two unrelated sections from 2026-08-08 until someone counted headings by hand. Diagnosed rather than guessed -- PR #64 moved plugin.json 0.107.1 to 0.108.1, two versions against three sections, and the published Release names the first -- so the surplus one is demoted to a subsection of the release it actually shipped in. `duplicate_changelog_versions` now blocks above the 0.49.0 floor inside `--check`. Running it without a floor immediately surfaced two more, v0.26.1 and v0.39.5, each carrying two genuinely different bodies under one number; those are REPORTED and not rewritten, because reconstructing which body was which release three months on would be inventing a record, and a floor that hid them would make them permanently unfindable. Prior: 0.176.0 -- **Attribution label: the-release-pipeline-learns-the-other-direction-2026-09-04** (MINOR). Release automation could only ever ask one of two questions: is a documented version missing a Release? Nothing asked whether a Release was missing its documentation, and that direction has the worse failure -- a Release nobody meant to cut is a public claim that a version shipped. Three mechanisms, deliberately not one: `--require-documented` withholds any version that exists only in an intermediate commit and warns rather than failing, because a red main on a push whose work landed trains dismissal; the Latest pointer refuses to promote a version with no changelog section, since a stray Release is a dead tag but a stray Latest is a false statement; and `--audit` runs weekly in its own workflow rather than at release time, because it can only ever fire after the artifact is already public. Also closes a shipped field that nothing read: `purpose_stance` overrides carry `decision: DL-NNNN`, the docs have shown it since the mechanism shipped, and the check only ever validated `human:` -- so a contradiction could be cleared by citing a decision that never existed. Now resolved against the decision log, opt-in by presence. This version number was cut as a phantom Release on 2026-09-03 and deleted the same day; it is reused deliberately rather than skipped, because a silent gap in the chain is the habit this release is about. Prior: 0.175.2 -- **Attribution label: readme-pie-palette-meets-wcag-on-both-surfaces-2026-09-03** (PATCH). The README pie shipped in near-black fills that all but vanished on GitHub's dark canvas. Re-picked from the validated categorical palette and checked computationally rather than by eye: `#3987e5` / `#d95926` / `#199e70` clear WCAG 1.4.11 (3:1 non-text) against **both** `#ffffff` and `#0d1117`, carry black section labels at 5.4-6.2:1 (clearing 1.4.3's 4.5:1), and pass the dataviz validator's CVD gate in both modes (worst all-pairs deutan Delta E 9.4, normal-vision 20.9). Slice borders are white at 2px, which reads as a separator gap on the light surface and a crisp ring on the dark one, plus a `#8b949e` outer ring that clears 3:1 on both. Title and legend colors are deliberately NOT pinned, so GitHub's per-mode theme still supplies them. Prior: 0.175.1 -- **Attribution label: readme-backs-discovery-claim-with-a-count-2026-09-03** (PATCH). The README's claim that nobody thinks discovery is optional rested on one person's word for it. Added a hand-read count instead: 46 shipped-to-no-traction posts across r/microsaas, r/SideProject and r/vibecoding, 37 of 46 never mentioning contact with anyone who had the problem. New receipts case `docs/receipts/cases/2026-08-16-l1-population-read.md` carries the method and the limits (floor not a rate, timing not coded). A craft audit found and fixed the three weakest sections of the README in the same pass, judged by voice against the rest of the file rather than by keyword.*

*Full version history: [`docs/changelog.md`](docs/changelog.md).*

Mycelium is a harnessing system for AI-assisted product development. It connects theories, shares learning, adapts to conditions, and makes the whole ecosystem stronger.

**You are an agent operating within Mycelium. Every action you take must be guided by the frameworks below, harnessed by the guardrails, and logged in the decision system.**

## Agent Operating Contract (always-on rules)

The always-on behavioral rules — the **Communication Rules** (plain-language-first; suggest-skills-at-transitions; route-through-skills with the freeform escape valve; cite-the-trigger; offer-to-capture-learnings; name-the-verification-surface incl. `Ran: <cmd> → <result>` for runnable artifacts, `G-V13`; name-the-gate; read-canvas-before-narrating; verify-after-write; BLUF-layering, `G-C1`) and the **Mandatory Pre-Task / Pre-Ship (G-P-pre) / Post-Task (G-P7) Protocols** — are defined once, canonically, in **[`plugins/mycelium/engine/agent-operating-contract.md`](plugins/mycelium/engine/agent-operating-contract.md)**.

That file is the single source of truth, and the SessionStart hook (`plugins/mycelium/hooks/session-start.sh`) injects it into every session — so the contract binds in **plugin form** too, where no operating-manual `CLAUDE.md` is templated into the consuming project. It is the plugin-form replacement for the removed legacy `degit`-templating path (the migration kept the computational half of the harness — hooks — but until v0.58.0 silently dropped this always-on inferential half for plugin-form consumers; the framework repo never noticed because its own sessions load this very file as the repo's `CLAUDE.md`). Read the contract; those active rules win over any restatement. **CI Check 47** keeps the wiring intact: contract present + packaged in `manifest.yml` + injected by the hook + referenced here + free of legacy `.claude/` framework paths.

Canonical detail behind individual rules still lives in the harness: `plugins/mycelium/harness/communication-rules.md` (rationale + graduation history + X/Twitter extraction sequence), `guardrails-core.md` (`G-C1` BLUF-layering, `G-V13` runtime-proof, `G-P7` Post-Task, `G-P-pre` Pre-Ship), `engine/canvas-guidance.yml#action_flags` (gate flags). Pre-Ship graduated 2026-05-04; write-narration-verification 2026-06-05 (#18/#19).

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

Four phases per diamond, gated by theory checks: **Discover** (diverge — explore, gather evidence), **Define** (converge — synthesize, frame the problem), **Develop** (diverge — ideate, prototype), **Deliver** (converge — validate, build, ship, measure). Diamonds spawn children (L0→L1→L2→L3→L4, L5→L2 on market feedback); a bad assumption found in delivery **regresses** the diamond back with new evidence — the system working correctly. Full transition rules, WIP limits, lifecycle: `plugins/mycelium/engine/diamond-rules.md`.

### OST Leaf Lifecycle

Every solution leaf runs a 10-phase pipeline, each phase with input artifacts, gates, outputs, and discard criteria: **OST Leaf → Four Risks → ICE Score → Assumption Test → GIST Entry → Bounded Context → Threat Model → Preflight → Delivery Diamond → Launch + Feedback**. Definitions and discard rules: `plugins/mycelium/engine/leaf-lifecycle.md`; archived leaves → `canvas/archived-solutions.yml`.

### Perspective Resolution & Leaf Bakeoff

Conflicting product/design/engineering perspectives → structured resolution in `plugins/mycelium/engine/perspective-resolution.md`. Multiple leaves competing for one opportunity → structured A/B comparison in `plugins/mycelium/orchestration/leaf-bakeoff.md`.

## Theory Gates (Decision Checkpoints)

Every diamond transition must pass applicable gates from: Evidence, Four Risks, JTBD, Cynefin, Bias, Security, Privacy, BVSSH, Service Quality, Delivery Metrics, Corrections, Regulatory, Explainability. See `plugins/mycelium/engine/theory-gates.md` for complete definitions, pass/fail criteria, and suggested skills.

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

- **Behavioral Contract** (`plugins/mycelium/harness/behavioral-contract.md`): Consolidated must / must-never index for the agent itself. Pointer-only (copies nothing; the cited source always wins) so the agent's own behavioral contract is grep-able in one place — the self-governance analogue of the `ai_tool` product contract in `canvas/ai-tool-metrics.yml`.
- **Guardrails** (`plugins/mycelium/harness/guardrails.md`): Three-tier enforcement -- BLOCK (mechanically prevented), REVIEW (gates progression), NUDGE (advised, not blocking).
- **Anti-Patterns** (`plugins/mycelium/harness/anti-patterns.md`) & **Cognitive Biases** (`plugins/mycelium/harness/cognitive-biases.md`): Known failure modes with detection rules (stop and self-correct if you catch yourself in one); per-stage bias checklist.
- **Security & Trust** (`plugins/mycelium/harness/security-trust.md`): Per-stage security requirements.
- **Engineering Principles** (`plugins/mycelium/harness/engineering-principles.md`): DRY, KISS, YAGNI, SoC, SOLID, LoD. Human-facing complement: **Design Principles** (`plugins/mycelium/harness/design-principles.md`) — how the framework treats its user (SDT autonomy/competence/relatedness; Theory Y; never gamify discipline).
- **Delegation Authority** (`plugins/mycelium/harness/delegation-authority.md`): who decides — agent vs human — for each *execution* decision, keyed to consequence (effective-reversibility × aggregate-blast-radius). Binds the BLOCK/REVIEW/NUDGE tiers to execution (not just epistemic discipline); names the no-standing decisions (which bet, security/privacy/ethics tradeoffs, editing the map itself) that are absolutely human; round-up-under-uncertainty; escape-hatch override. Repo anchor for behavioral-contract N9/N10.

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
- **Warnings Log** (`.claude/memory/warnings-log.md`): CI WARN+FAIL capture, auto-updated; per-class fixes in `plugins/mycelium/engine/warning-handbook.md`; consumed by `/corrections-audit`.
- **Decision Log** (`plugins/mycelium/harness/decision-log.md`): every significant decision. **Required** `why_not_alternatives` field — per-alternative rejection rationale; contrastive explanations land harder (Liao et al. 2020) and feed `/xai-check` Stage 2.
- **Feedback Loops** (`plugins/mycelium/engine/feedback-loops.md`, `/feedback-review`), **Reflexion Loop** (`plugins/mycelium/skills/reflexion/SKILL.md`, max-3 retry), **Eval Benchmarks** (`.claude/evals/`), **Cycle History** (`.claude/canvas/cycle-history.yml` → `engine/cycle-learning.md`), **Adaptive Thresholds** (`.claude/canvas/thresholds.yml` → `engine/adaptive-thresholds.md`).

### Learning Metabolism (Self-Improving System)

Five mechanisms make Mycelium smarter over time (details + cadence in each sub-file): **Cycle Learning** (`plugins/mycelium/engine/cycle-learning.md` — predicted vs actual ICE), **Pattern Emergence** (`plugins/mycelium/engine/pattern-detector.md` — into `/retrospective`, `/diamond-assess`), **Adaptive Thresholds** (`plugins/mycelium/engine/adaptive-thresholds.md` — defaults until N=10), **Framework Reflexion** (`plugins/mycelium/engine/framework-reflexion.md`, `/framework-health`), **Evidence Decay** (`plugins/mycelium/engine/evidence-decay.md` — `/canvas-health` flags stale evidence).

## Domain Contexts

Load the appropriate context based on current diamond phase:

- **Discovery**: `${CLAUDE_PLUGIN_ROOT}/domains/discovery/CLAUDE.md` -- Torres-style interviewing, OST construction, bias-aware research
- **Delivery**: `${CLAUDE_PLUGIN_ROOT}/domains/delivery/CLAUDE.md` -- Agile/DevOps practices, clean code, security, accessibility, DORA metrics
- **Quality**: `${CLAUDE_PLUGIN_ROOT}/domains/quality/CLAUDE.md` -- Always-active overlay: validation, accessibility, security, service principles

## JiT Tooling

Mycelium is **language-agnostic** and **product-type-agnostic**. When a delivery diamond begins, auto-detect the tech stack (or product type), generate appropriate validation, and confirm with the user. See `plugins/mycelium/jit-tooling/detector.md`.

## Usage & Orchestration

Solo developers use canvas as shared memory with the agent. Teams commit canvas to git as shared product documentation. For parallel exploration, use `/fan-out` with worktree-isolated worker agents.

See `plugins/mycelium/orchestration/modes.md` for usage patterns and `plugins/mycelium/orchestration/agent-teams.md` for parallel orchestration.

## Operations & Maintenance

- **Day-to-day**: `plugins/mycelium/orchestration/operations.md` -- Session resumption, canvas maintenance, diamond lifecycle, memory pruning
- **Escape hatch**: `plugins/mycelium/orchestration/escape-hatch.md` -- Legitimate process bypass for emergencies. Must be documented and paid back.

## Skills

All 61 skills are auto-discovered from SKILL.md frontmatter — in plugin form (`plugins/mycelium/skills/*/SKILL.md`, recommended) or legacy form (`.claude/skills/*/SKILL.md`, supported during transition). Suggested skills are surfaced at diamond transitions by `/diamond-progress` and `/diamond-assess`, and contextually by hooks. Type `/` to see the current list.

## Getting Started

New project (empty canvas): run `/interview`. Continuing work (populated canvas): run `/diamond-assess`. The system guides you from there.
