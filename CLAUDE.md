# Mycelium: Theory-Guided Agentic Product Development

*Version 0.99.1 -- **Attribution label: the-registry-whose-own-guard-caught-it-2026-08-06**. **`right-content-wrong-surface` graduates to a general mechanism**: `engine/surface-registry.yml` declares, per recurring artifact class, which file is AUTHORITATIVE and which mechanism READS it, and `check_surface_registry.py` verifies each declared reader genuinely references its declared surface. The cluster's own criterion was that a fourth class must be a ROW and not a fourth point-check; `correction-to-cluster-instance` was added as a row the same day, which is the criterion satisfying itself. `upstream-candidate` ships as an OPEN row with a null surface and no reader, because a registry that could only express solved classes would hide its most important entry. **Then the new script was caught by an existing guard**: `check_empty_input_honesty.py` (v0.79.0) found that both scripts added today exit 0 over an empty tree, reporting SKIP -- a check that verified nothing and reads green forever, which is anti-pattern #9 inside the mechanisms built to close its sibling cluster. Both now fail the precondition (exit 2) and both gained `--root` so the guard can aim at them at all; coverage went 10 scripts to 12. **And the AP#9 cluster record was three days stale**: its cross-cutting mechanism shipped in v0.79.0 while the catalogue still read NOT BUILT, and a `/framework-health` run read that and repeated it into a dashboard the same morning. Corrected, and logged as a stale-state read on the catalogue itself. 28 new tests.*

*Superseded label (v0.99.0): the-count-that-nothing-writes-2026-08-06. **`cluster-instances.md` graduates clusters on instance COUNTS, and nothing writes those counts.** Measured in dogfood: corrections.md +24 entries over five days, catalogue +1 row, while `consistency-as-evidence` still read 31 / most-recent 2026-07-27. A count-keyed trigger reading a hand-maintained number cannot fire, so "no cluster graduated" and "no cluster crossed its criterion" are indistinguishable from outside: anti-pattern #9 operating on the accounting FOR anti-pattern #9. It had been diagnosed once already, on 2026-07-25, and answered with another hand re-count; twelve days later it was stale again. `check_cluster_reconcile.py` asserts the hop was CONSIDERED and never classifies -- mis-binning corrupts a count that gates a mechanism, which is worse than drift that is honest about being behind. **The first implementation shipped a false green and its own live run caught it**: it matched any ISO date in the catalogue, and the same session's dated closure-note edit silenced it, which is the cheapest-green-is-a-no-op failure its header warns about. Now anchored to instance-log ROWS only. Two honest routes to green, both needing a judgement that happened: log the instance, or add a dated `reviewed-no-cluster-applies` marker. **Scope stated narrowly on purpose**: it detects LAPSE, not under-logging; twenty corrections answered with one row look the same to it. 14 new tests.*

*Superseded label (v0.98.1): the-backfill-could-not-satisfy-the-rule-it-shipped-under-2026-08-06. **v0.98.0 made `calibration.effort_accuracy` the one required field on a meta-dogfood record; the dogfood project then backfilled three arcs and every one had to leave it null.** No estimate was ever set on those arcs, so there is nothing for the actual to be wrong about, and a reconstructed estimate is a number invented today to grade work done in July. `reconstructed_post_hoc: true` is now an explicit exemption, excluded from every calibration aggregate. Without it the framework would have shipped a rule and instantly created three violating rows, with nothing distinguishing exempt-by-design from field-skipped, which is `documented-rule-diverges-from-enforcement` reproducing inside the release meant to close a different gap. A reconstructed record buys an audit trail and a measurement baseline, and ZERO calibration data; it is recorded that way rather than counted as a win.*

*Superseded label (v0.98.0): recordable-in-principle-unrecordable-in-practice-2026-08-06. **`engine/cycle-learning.md` gave two opposite answers about whether framework work is a cycle, sixty lines apart, for two months.** The Framework-on-Framework Exemption (v0.23.16) said framework improvements do NOT populate `cycle-history.yml`; `cycle_class: meta-dogfood` (v0.39.0, nineteen days later) said they do, and neither was reconciled — which one applied was decided by a detection test a dogfood-consumer repo fails on a technicality. **The exemption is narrowed to fields, not records.** Its prediction was right (all ten dogfood meta-dogfood rows carry null ICE/DORA/user-metrics) and its remedy was wrong: stop REQUIRING the null fields rather than dropping the row. `calibration.effort_accuracy` stays REQUIRED and is the whole case — it is the dimension that surfaced *scope-expansion-blind-to-user* at N=4, which graduated to **G-P9**, and which the corrections→cluster path structurally cannot produce (a correction records a mistake, not an estimate that was wrong). **And a trigger that fires on what framework work actually does**: every prior trigger was keyed to the LEAF lifecycle and the only opener fired at a diamond PHASE TRANSITION — framework work ships releases instead, so dogfood ran 48 minor releases across 49 days with zero cycles and nothing could tell "none owed" from "owed and unnoticed". `check_cycle_recording.py` is ADVISORY via session-start, not a CI gate: a cycle needs a judgement, and blocking a push until someone writes a retrospective is coercion, not scaffolding. Three branches earned tests by failing in review — `never-recorded` is its own state (else the framework repo is told it owes one cycle spanning 86 releases, and an unmeetable demand gets muted), `--release-repo` (the wrong repo returns a plausible number, not an error), and `no-releases-matched`. 15 new tests. The built-not-wired guard caught the new script unwired: *"a unit test is not a caller."* Found by `/framework-health`.*

*Superseded label (v0.97.1): the-guard-fired-on-the-retraction-2026-08-06. **A guard that warns hardest when someone admits they were wrong is training the wrong reflex, and the absence-claim guard was doing exactly that.** Dogfood withdrew an absence claim on the canvas — `"zero external sources" is now false, the third row is external` — with the proof three lines above it, and the guard demanded a search for a claim being DELETED. The quoted phrase was the old claim; the sentence was its obituary. `_RETRACTED` now suppresses an absence that is being withdrawn in the same sentence, which is a different suppression in kind from `_SCOPE`: scope means the author showed their work, retraction means there is no claim left to ground. **The narrowing is load-bearing and was verified rather than asserted**: the wrongness word must be CLAUSE-FINAL, so "no check exists, which is false comfort" still warns. The first cut omitted that, this file's own comment claimed the narrow behaviour anyway, and the fixture written to assert it failed on the first run — the guard's documentation was wrong about the guard. Clause-finality then turned out to earn more than it was added for, shrinking the accepted over-suppression to a residual case pinned as its own test. 76 tests (up 6). Found by dogfood, where the same hook fired three times in one session and two were false positives.*


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

All 60 skills are auto-discovered from SKILL.md frontmatter — in plugin form (`plugins/mycelium/skills/*/SKILL.md`, recommended) or legacy form (`.claude/skills/*/SKILL.md`, supported during transition). Suggested skills are surfaced at diamond transitions by `/diamond-progress` and `/diamond-assess`, and contextually by hooks. Type `/` to see the current list.

## Getting Started

New project (empty canvas): run `/interview`. Continuing work (populated canvas): run `/diamond-assess`. The system guides you from there.
