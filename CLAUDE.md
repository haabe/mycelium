# Mycelium: Theory-Guided Agentic Product Development

*Version 0.88.0 -- **Attribution label: plugin-root-guessed-path-2026-08-05**. A plugin cannot know where it is installed, and these two manifests claimed to. `hooks.codex.json` and `hooks.cursor.json` shipped every command as `${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/cache/mycelium-plugin/mycelium}` — a literal that **has never resolved on any machine**: the marketplace directory is `haabe-mycelium`, and the cache is versioned, so no unversioned path can hit. Codex and Cursor set no `CLAUDE_PLUGIN_ROOT` (Cursor exports `CLAUDE_PROJECT_DIR`), which made **the fallback the live path for every consumer** of those files. It failed SILENTLY and it failed OPEN: `bash /missing/gate.sh` exits **127** and the contract blocks on **2**, so every gate reported not-blocked without running. Five more commands carried a bare `${CLAUDE_PLUGIN_ROOT}` with no fallback at all. **The same class sat one layer in and would have survived fixing the first**: seven hook scripts resolve their helper as `${CLAUDE_PLUGIN_ROOT}/scripts/*.py` and silently `exit 0` when absent, so correctly-wired manifests would have run guards that did nothing. Both halves are now answered by **self-location** — a script at `<plugin_root>/hooks/` knows the root from its own path, needing no environment, the idiom `codex-postfailure-shim.sh` already used. The manifests became templates carrying `__MYCELIUM_PLUGIN_ROOT__`, and `hooks/install-runtime-hooks.sh` substitutes it and **refuses to write unless every hook script it names exists** — a generated manifest pointing at absent scripts is the same defect one layer down. `hooks.json` deliberately keeps the variable, since Claude Code does set it and changing that would be the mirror-image mistake. Closes the gap `hooks/README.md` has carried open since v0.85.0 (nothing copied the manifest to a path Cursor reads); still **unobserved in a live Cursor session** — proven by test, not by a running editor. Prior: **Version 0.87.0** -- **Attribution label: release-gap-failopen-2026-08-04**. The workflow that exists to stop releases going missing was losing them. It read `plugin.json` ONCE, at the tip of the push, and created one Release; a push carrying several version bumps released only the last and **exited 0**. On 2026-07-30 that swallowed SEVEN versions, v0.66.0 through v0.66.6 — all documented in the changelog, none on the releases page, the job green throughout, found five weeks later by accident. The defect was never that the step broke: **nothing distinguished one-version-released from seven-versions-one-released**, the same fail-open shape logged eleven times now, here in shipped CI config. Two changes: release EVERY version the push introduces, each tagged at the commit that first set it; then **re-derive the expected set from the changelog and fail loudly** if any documented version still lacks a Release. The first alone fixes the known route and stays silent on the next one; the second does not care how a gap appeared, which is why it is the load-bearing half. Logic lives in `scripts/release_gaps.py`, not inline YAML, so it is unit tested — 13 tests including the 2026-07-30 case, numeric-not-lexical ordering (0.9.0 < 0.10.0) and the floor boundary. Floor v0.49.0, because 149 versions predate release automation and a permanently-red check is a permanently-ignored one. Prior: **Version 0.86.0** -- **Attribution label: closure-discipline-2026-08-04**. Solution leaves have had a never-delete archive protocol with a reason enum for a long time; **opportunities and human-tasks had nothing**. `status` was not even a declared property on opportunities, so one dogfood canvas drifted to five spellings including an uppercase variant no validator could see, and reopen semantics appeared 17 times in its `human-tasks.yml` against 0 mentions in the schema. The cost was concrete: a task closed with `closure_reason: channel-ended`, justified entirely by a month-old note recording that the other org *expected* to wind down plus the observation that the window had passed. **The passage of time was treated as an event.** Nobody asked; a one-line message later falsified it in hours. By then the reason had been cited as fact across **12 sites** and read as a bare premise. Now, whenever a `closure_reason` is asserted, two companions are required: `closure_basis` (`observed` | `inferred` -- an elapsed interval is not an observation, and `inferred` is the honest label for a guess, not a banned value) and `reopen_trigger` (what would make this wrong, checkable by someone who was not there). **Conditional on purpose** -- work that is simply finished needs no ceremony, which is what stops the gate being deleted later. A status enum alone would NOT have caught it: the bad closure used a well-formed value, and an enum validates spelling rather than reasoning. Prior: **Version 0.85.0** -- **Attribution label: ci-signal-return-path-2026-08-04**. The dogfood workflow was red for THIRTEEN CONSECUTIVE PUSHES and the agent never looked. The tempting diagnosis is discipline; the real one is architecture. **The flow was one-way** — local push, CI runs, the verdict lives on GitHub and never comes back — and the harness had five hook points, none of which looked outward at whether the build passed. On a pull request you are forced to look; on `main` nothing asks. New `ci-signal` hook on **Stop** (the warm catch: one long session with thirteen pushes needs to hear it mid-session, not tomorrow) and on **SessionStart** (the cold catch, which bypasses the dedupe because a new session is a new agent with no memory of what the last one was told). **It tracks no pushes**, deliberately: GitHub already knows, so it compares the newest run's `headSha` against local HEAD and speaks only about the commit actually checked out. That SHA match is load-bearing — the agent spent the same day reporting "CI: success" for a push that had failed, because `gh run list --limit 1` returns the newest run and 45s after a push that is often still the previous commit's. Reported once per run, rate-limited to one network call per 90s, and silent on green, in-progress, other people's commits, detached HEAD, missing `gh`, no auth and no workflows. Prior: **Attribution label: cursor-discovery-unverified-2026-08-04**. Doc-only. v0.83.0 fixed two dead hook registrations by reading vendor documentation, and `hooks/README.md` then stated the Cursor fix as settled. It is not. **Both fixes are correct against the docs and neither has been observed running.** Cursor's docs place hooks at `.cursor/hooks.json`; this plugin ships `hooks/hooks.cursor.json` inside the plugin tree, and whether anything copies it to a path Cursor reads is unknown from inside this repository — if nothing does, Cursor consumers get no Mycelium hooks at all and the corrected registration sits in a file the runtime never opens. Recorded as unverified rather than left reading as fixed, because "we corrected the entry" is the same shape of claim as "registered on all three surfaces", which is what produced the dead registrations. It cannot be closed by inspecting our own manifest again; it needs one person running Cursor to trigger any warning once, tracked as the second question on roadmap `ht-053`. Prior: **Attribution label: absence-guard-shell-reach-2026-08-04**. The guard shipped one release earlier said it "fires at the write". It did not. It watched `Write|Edit|MultiEdit`, and every correction appended during the session that produced it went in as `cat >> .claude/memory/corrections.md <<'EOF'` — a heredoc no PreToolUse write matcher sees. **A guard blind to the way its own author writes is the documented-not-operational failure this project audits others for**, so the reach is closed rather than noted: it now also watches shell writes into evidence surfaces (`>`/`>>`, `tee`, `sed -i`) on the `Bash`/`Shell` matchers of all three manifests. The redirect target is stripped before scanning, because the scope suppressor counts a named file as showing your work and the destination IS a named file — without stripping, `echo "No entry covers x." >> corrections.md` cites its own target and goes quiet. Reads, unwatched destinations and commit messages stay silent; the commit-message case is a fixture, since this project writes long prose messages and warning on them would make the guard noise within a day. Prior: **Attribution label: absence-claim-guard-2026-08-04**. Five findings in one dogfood session took the same shape: a narrow read promoted to a broad claim without the promotion being noticed. Two reached the canvas and were pushed before being caught — "no need covers vocabulary, so his signal has nowhere to go" was false, the concern having its own opportunity, two ID'd evidence items, a named failure mode and a segment constraint. An auto-memory rule against exactly this already existed and never fired, because notes are read at session start and decay. New `absence-claim-guard` PreToolUse hook warns when an assertive absence reaches a `.claude/` evidence surface without naming the search that grounds it. **Calibrated against 60,010 real corpus sentences rather than intuition**: the first draft fired on 0.42% and half were ledger prose ("No confidence gate moved") — records of what a session did, not claims about what exists. Requiring an existence verb, and refusing to treat `;` and `:` as sentence ends, brought it to 0.175%. It warns and never blocks: absence findings are frequently correct, and a guard that blocks real work gets disabled. Prior: **Attribution label: pointer-message-accuracy-2026-08-03**. A correct finding named the wrong culprit. With `source_classes` of `[pointer, internal_desk, pointer]`, `check_source_independence` reported "3 sources, all `pointer`" — because the message printed `classes[0]` while the logic correctly excluded pointers and judged the single method, `internal_desk`. The verdict was right and its explanation blamed the one thing the check had already set aside. **That is worse than a missed finding**: a true report that misnames its cause reads as a tool bug and gets dismissed, which is how a guard loses the benefit of being right. It now reports the method count and names the method, with the pointers set aside shown separately ("1 evidence source(s), all `internal_desk` (2 pointer(s) set aside from 3 total)"). Found by reading a live finding against the data it described rather than trusting the sentence.*


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
