# Mycelium: Theory-Guided Agentic Product Development

*Version 0.23.13 -- **Attribution label: lived-friction-triggered**. Two regenericization fixes + Check 33 architecture correction. **(1)** Regenericized the last remaining Check-33 leak: `plugins/mycelium/harness/anti-patterns.md:85` source line previously cited "2026-05-09 (Frida verbosity-attribution gap)" as one of three recurrence triggers for anti-pattern #7. Replaced with "2026-05-09 (verbosity-attribution gap, private-channel observation)". Also collapsed the adjacent "Hoskins over-scoping" to "over-scoping cluster" for consistency (Hoskins-the-theory-author is fine in citation context, but "Hoskins over-scoping" framed the issue as the person's friction-log finding, not the theoretical lens — generic framing is more accurate to what the cluster represents). **(2)** Architecture correction for Check 33 / attribution-registry placement. Initial 0.23.12 ship put the registry at `.claude/memory/attribution-registry.yml` in this PUBLIC repo. User-detected mid-session: *"I thought the registry would live in the roadmap repo, not the mycelium repo"* — and they were right. The registry contains the very names whose private-channel attribution status it tracks; storing it in the public repo is self-defeating because anyone browsing GitHub can read it. Moved to `mycelium-roadmap/.claude/memory/attribution-registry.yml` (haabe/mycelium-roadmap is PRIVATE). Check 33 now resolves the registry via: (a) `$MYCELIUM_ATTRIBUTION_REGISTRY` env-var override, (b) `../mycelium-roadmap/.claude/memory/attribution-registry.yml` sibling-repo lookup, (c) fail-open if neither exists. The fail-open path is correct for CI runners and fresh maintainer clones without the roadmap. Downstream plugin users never hit Check 33 — `tests/` doesn't ship via the plugin (`marketplace.json#source` is `./plugins/mycelium`), so the check is maintainer-side only. **Acknowledged residual leak surface (not done in this patch):** the public mycelium repo still references "Frida" by first name in: `CLAUDE.md` v0.23.9 changelog (generic-framed as "cautious-learner first-run observation" — but in context this is partial reidentification), `CLAUDE.md` v0.23.12 changelog (the Check 33 introduction text quotes the original leak), `.claude/memory/corrections.md` 2026-05-14 entry I wrote (names her by first name explaining the leak mechanism), and prior commit messages (Frida appears in 3eed9d8, 5a9e473, and cb8fec8 commit bodies). Per the user's "we're doomed anyways" observation: scrubbing this fully would require git-history-rewrite, which has higher cost than the marginal incremental exposure of these references. The honest framing is: capture-time discipline is necessary but not sufficient; the framework now has Check 33 to prevent forward leaks into the plugin tree, but historical public-repo references are accepted residual. PATCH per version-discipline.md: regenericization + check-architecture fix; no new mechanism, no new gate, no backwards-incompatible behavior; Check 33 continues to operate WARN-only.*

*Version 0.23.12 -- **Attribution label: lived-friction-triggered**. New Check 33 + attribution registry: plugin tree must not contain unconsented personal identifiers. Trigger: in-session 2026-05-14 user-asked *"will that file [Mycelium's own canvas/opportunities.yml] interfere with whatever the user is doing in their project?"* during a Check-32 follow-up. The literal answer was "no — plugin scope is `./plugins/mycelium/`, repo-root canvas doesn't ship." But the user pushed: *"there might be a leak of data (such as Frida and her project) if we allow for that to flow into the project?"* Scan of `plugins/mycelium/**` for known names found 5 unconsented leaks: 1× "Frida" in `harness/anti-patterns.md:85` (graduated 2026-05-09 from a generic-framed corrections.md entry — the graduation chain re-coupled identity by citing the trigger date with a name annotation), 4× "Simon" in `harness/theory-tensions.md` (lines 5 and 180 carry the FULL NAME "Simon Rohrer" attributing LinkedIn feedback — higher-doxing-surface than first-name-only). Drew is also present but with explicit prior public-attribution consent, so not flagged. **Mechanism shipped:** `.claude/memory/attribution-registry.yml` (outside plugin tree, never distributed) carries one entry per known individual with `consent: public_ok | generic_only | unknown`; Check 33 scans `plugins/mycelium/**` for `generic_only` and `unknown` names via word-boundary regex across `*.md`, `*.yml`, `*.yaml`, `*.json`, `*.py`, `*.sh`. Adding a name without a consent value = registry parse error → check fails (forces deliberate consent decisions). WARN-only initially per framework's observability-before-enforcement discipline; graduates to FAIL once pre-disclosure leaks are addressed. **Deeper lesson captured in corrections.md (2026-05-14 entry):** lived-friction attribution can leak through the graduation chain even when the source is generic-framed at point of capture. Capture-time discipline is necessary but not sufficient — every step from corrections → anti-patterns → engine docs that cites trigger sources is itself an attribution surface. Theory grounding: GDPR data-minimization (collect only what's needed; carry forward only what's consented) applied to internal framework documentation, not just user data. User-noted nuance: first-name-only references lower the doxing risk but do not remove responsibility — the framework's consent discipline applies independent of doxing risk (the "Simon Rohrer" case is the cautionary instance). **Not done in this patch:** the existing Frida and Simon leaks remain in place (regenericization is a separate decision per individual). Check 33 surfaces them every run until addressed. PATCH per `version-discipline.md`: new validator check is observability-adding, not behavior-changing for downstream users; no new mechanism affecting user-project surfaces; no backwards-incompatible change. Borderline-MINOR argument exists (the check is a new validator gate) but PATCH is defensible because it lands as WARN-only and represents a strengthening of an existing discipline (G-V12 + version-discipline.md's anti-leak intent) rather than introducing a new theory or skill.*

*Version 0.23.11 -- **Attribution label: lived-friction-triggered**. Ruff cleanup pass on `plugins/mycelium/scripts/verify_citations.py`. Trigger: in-session question about when Check 17's 20-error tech debt would be addressed surfaced that the WARN had no entry in any `warnings-log.md` (the file didn't exist) and no trigger condition — a quiet violation of `feedback_no_tech_debt_deferral.md` ("never indefinite"). Ran `ruff check --select=ALL --ignore="D,ANN,COM,T20,S603,S607,EM,TRY003,FBT,PTH,INP001" --fix` per the validator's own invocation; 4 auto-fixed (UP015 redundant-open-modes ×2, I001 unsorted-imports, FURB188 slice-to-remove-prefix-or-suffix). Remaining 17 manually fixed in `verify_citations.py`: 2× SIM103 (return condition directly), 2× E501 collapsed via implicit string concatenation, 1× PLW2901 (renamed shadowed `line` loop var to `raw_line`), 1× combined S110+BLE001 (replaced `except Exception: pass` with narrower `except OSError` + explicit fail-open return), 1× RET504 (collapsed `p = expr.removeprefix("./"); return p` into single-return chain), 1× PERF401 (`for u in ...: lines.append(...)` → `lines.extend(... for u in ...)`), 6× more E501 in `format_human` (rewrote as list-literal seed + parenthesized implicit concatenation for long help/note strings), 2× E501 in argparse description+help (same idiom), 1× E501 in `verify` docstring (line wrap), 1× EXE001 (`chmod +x` — shebang was present but file lacked exec bit). All 14 unit tests in `tests/python/test_verify_citations.py` still pass post-cleanup; behavior is unchanged. Check 17 returns to PASS (0 errors on cleanup-cycle files, 0 total errors across all `plugins/mycelium/scripts/*.py`). PATCH per `version-discipline.md` line 11 (explicit "ruff cleanup" listed as PATCH-class).*

*Version 0.23.10 -- **Attribution label: lived-friction-triggered**. Migration-skill truth-up patch + retroactive bump for previously-masked test-suite fix. Two changes coalesced into one PATCH because the second surfaced the first. **Change (1):** `plugins/mycelium/skills/migrate-from-legacy/SKILL.md` Step 7 corrected. Trigger: during this session, a stale `"hooks"` block in `.claude/settings.local.json` emitted non-blocking `No such file or directory` errors per turn (PreToolUse/PostToolUse/Stop), pointing at the legacy `.claude/hooks/*.sh` tree deleted in a5cabd3. Investigation found Step 7 claimed *"The migration script warns if either `.claude/settings.json` or `.claude/settings.local.json` contains a `\"hooks\"` block"* — but the actual legacy `--migrate-to-plugin` handler (originating commit 34ea768, deleted from this repo by a5cabd3 along with the rest of `.claude/scripts/`) only ever checked `settings.json`. The `settings.local.json` location — which is conventionally where local hook registrations live — was structurally invisible to the script's warning. Step 7 now (a) names the actual coverage gap honestly ("script only checks settings.json"), (b) takes ownership of the dual-file grep itself via a concrete bash snippet the skill runs post-migration, (c) adds the user-facing symptom signature ("`bash: .../.claude/hooks/gate.sh: No such file or directory` per turn") so future migrators can connect that noise back to this step without re-investigating. **Considered-and-reverted:** initially added a 130-line `--migrate-to-plugin` flag handler to `plugins/mycelium/scripts/upgrade.sh` — reverted after user-prompted git archaeology showed (i) the plugin copy of upgrade.sh is by-design never invoked for migration (legacy users run their *local* `.claude/scripts/upgrade.sh` which still has the original 34ea768 handler; plugin-form users don't need migration), (ii) adding a handler there created dead code with no documented invocation path. The right fix is the SKILL owning the check, not duplicating script logic across two locations. **Change (2) — retroactive bump for `2f0b003`:** the SIGPIPE fix to `tests/validate-template.sh` Check 10 (committed 2026-05-13 21:59 as `fix(tests): Check 10 grep SIGPIPE on Linux with set -o pipefail`) landed without a version bump. At the time, validation appeared to pass — but only because the SIGPIPE bug itself was aborting the script at Check 10 with exit 2 before Checks 11-26 ever ran. **Check 26 is the version-bump-discipline check itself.** So the SIGPIPE fix structurally unmasked the check that would have caught its own missing bump. Classic observer effect: the only way to learn the check was being masked was to fix the mask. This 0.23.10 entry retroactively absorbs `2f0b003` so the next validator run finds `last_version_commit == HEAD` and `committed_count == 0`. Without this absorption, every subsequent commit would inherit `2f0b003`'s debt until someone bumped. **Lesson for version-discipline.md (not graduated yet, pending recurrence):** a test-suite fix that changes which downstream checks run is a structural change to the validator's observable behavior, not a cosmetic fix. Borderline-PATCH at minimum; arguably MINOR if it surfaces previously-masked failures. Worth a sentence in the version-discipline doc the next time it's edited. PATCH per version-discipline overall: both changes are corrections to previously-false-or-masked behavior; no new mechanism, no new gate, no backwards-incompatible runtime behavior.*

*Version 0.23.9 -- **Attribution label: lived-friction-triggered**. First-run friction batch shipped from a single behavior-validated cautious-learner first-run observation (2026-05-10, generic-framed per disclosure-and-ack 2026-05-13; identity withheld pending separate sign-off for receipts attribution). Seven framework opportunities surfaced and logged to upstream `opportunities.yml` (opp-001 through opp-007); five mechanism patches landed across hooks, skills, and README. Specific changes: **(1)** `plugins/mycelium/hooks/stop-check.sh` no longer emits "Session ended. 0 corrections, 0 decisions logged." per-turn when both counts are zero — silence is correct output for no-activity (opp-003 closed). When counts > 0 the line now reads as turn-summary ("Session:") rather than session-terminal. **(2)** `plugins/mycelium/hooks/preflight.sh` + `session-start.sh` count-display lines disambiguate three states (memory not initialized / empty / N corrections) so bare "0" no longer reads as a counting failure to first-run users (opp-001 partial — pattern precedent set for future hooks). **(3)** `plugins/mycelium/skills/setup/SKILL.md:119` AGENTS.md prompt rewritten with say-yes-vs-skip framing BEFORE the question (cost-of-yes vs cost-of-skip, Claude-Code-only fallthrough), addressing the decision-without-context pattern (opp-002a partial — full audit of remaining "Want to / Do you want" prompts pending). **(4)** `README.md:46` time-budget routing description aligned with current Universal Brief Flow shape — the legacy `<8h / 8-48h / 48+h` routing was removed in /interview but the doc lagged, leaving first-run users expecting a question that no longer exists (opp-002b partial — long-term release-process doc-sweep step still pending). **(5)** `plugins/mycelium/skills/interview/SKILL.md` confidence-0.15 inline rationale rewritten from "hardcoded floor" framing to canvas-density formula breakdown (purpose 0.05 + JTBD functional 0.05 + workarounds 0.025 ≈ 0.125 → 0.15) — the value was already formula-correct; only the framing was misleading. User-facing post-write line surfaces the formula at point of display. DEFERRED block restructured to partial-graduation status with explicit checkboxes — brief-only ✓ shipped; depth-menu writes ☐, classic Phase 1-6 paths ☐, /diamond-assess computation ☐ (opp-004 partial). **(6)** `interview/SKILL.md` brief flow adds a third post-write line surfacing the auto-tagged `source_class: internal_stakeholder, validated: false` choice + revise-path via `/mycelium:assumption-test` or `/mycelium:log-evidence`; names all five source classes for recognition (opp-005 partial — precedent set; remaining nine canvas-writing skills still need the same surface-the-choice line). **(7)** `interview/SKILL.md` gains a NARRATION DISCIPLINE block above Phase 1 explicitly forbidding phase-number narration to users, with concrete ✗/✓ examples (including the exact "Phase 6 questions" leak observed in first-run); `start/SKILL.md:48` cross-skill leak fixed in same idiom — internal vocabulary stays internal (opp-006 partial). **(8)** `interview/SKILL.md:123` friction-log prompt rewritten with three explicit destinations and consent gates (default stays in conversation; opt-in file write to `.claude/evals/dogfood-reports/YYYY-MM-DD-friction.md`; opt-in public receipts case with explicit pre-publish ask) — no more opaque "goes to a receipts case" pipeline shape (opp-007 closed). **(9)** `tests/validate-template.sh` Check 32 wrapper bug fixed: the Python script signals WARN via exit-1, but `set -euo pipefail` was aborting the script before the bash wrapper could honor the WARN intent; added `set +e / set -e` block around the rc capture so WARN is actually WARN (preserves the four-risks-when-active signal without breaking CI for fresh-entry opportunities that lack solution-level four-risks blocks). PATCH per version-discipline: all changes are bug fixes / clarification copy / framing precedent-setting; no new skills, no new gates, no backwards-incompatible behavior. Three opportunities (opp-005 broader sweep, opp-006 broader sweep, opp-007 broader audit) remain open in upstream `opportunities.yml` for the next cleanup cycle.*

*Version 0.23.8 -- **Attribution label: lived-friction-triggered**. C1 graduation: read-log + verify_citations infrastructure shipped upstream to attack anti-pattern #7 Level 3 (consistency-as-evidence — fabricated underlying inputs in `(per: <source>)` citations). Trigger: Supra Insider ep 110 (2026-05-11) surfaced Apurva Garware describing the exact same failure shape ("I was building out a skills library ... agent silently used scripts ... fabricated explanation when probed"); cross-mapped to today's recurring cluster activity (3 fresh framing-shape instances same day: cautious-learner leading questions, Drew mechanism-vocab, Johan transactional reciprocity); deep-dive analysis decomposed the gap into four failure levels (skipped read / skipped steps / fabricated inputs / fabricated outputs) with attribution that Mycelium's current mitigations are weakest at Level 3. Two new artifacts: **(1)** `plugins/mycelium/hooks/read-log.sh` — PostToolUse hook on Read tool, mirrors change-log.sh pattern; appends one JSONL line per Read to `.claude/state/read-log.jsonl` with schema `{ts, tool, file_path, session_id, diamond_id?}`. Fail-open. Sister mechanism to change-log.sh — together they answer "what did the agent read AND write during session X?" **(2)** `plugins/mycelium/scripts/verify_citations.py` — standalone Python stdlib script (no pip dependencies). Extracts `(per: <source>)` citations from text via regex, classifies file-shaped vs concept-shaped via path heuristic (slash OR known extension), cross-references file-shaped citations against read-log via suffix matching (citation `landscape.yml` matches read of `/abs/path/.claude/canvas/landscape.yml`). Reports verified / unverified / unverifiable counts plus human-readable narrative explicitly framing "unverified ≠ fabricated" (4 legitimate reasons enumerated: pre-hook-install session, system-reminder-provided content, concept-coincides-with-filename, prior-session recall). Hooks.json registers the new PostToolUse matcher on Read. 14 unit tests in `tests/python/test_verify_citations.py` per G-V12: file-shape heuristic, citation extraction with dedup, suffix matching (positive + no-false-positive), all-verified scenario, unverified-caught scenario (load-bearing test), concept-citations-route-to-unverifiable, session-id filtering, missing read-log fail-open, malformed JSONL fail-open, end-to-end anti-pattern-7 Level-3 scenario, human-format output, main CLI with JSON output. All 14 pass. Smoke-tested end-to-end: hook captures sample event correctly, script verifies + flags + routes concept citations correctly. **What C1 does NOT catch**: Level-2 framing-shape instances (mechanism-vs-value language, leading-question Torres violations, transactional-vs-relational framing) — these don't reference files, so verify_citations is structurally blind to them. Honest acknowledgment in deep-dive: today's three same-day instances are all Level 2, none would be caught by C1; C1 is necessary but not sufficient. **C2 (skill-execution fingerprints) and C3 (external witness)** logged as Tier 2 candidates in `mycelium-roadmap/.claude/drafts/security-strengthening-followups.md` with concrete graduation triggers (C2: ≥3 dogfood-detected Level-3 instances within 4 weeks OR ≥2 more framing-cluster instances; C3: ≥3 active non-founder contributors OR ≥2 contributor PRs to memory/canvas). **Sister observability**: same session shipped a preemptive convention registry to `plugins/mycelium/engine/consistency-check-spec.md` naming the skill-folder-layout convention (one SKILL.md per dir, no helper scripts) as held-by-discipline-not-mechanism; first violation triggers graduation to a validator check. Audit confirmed convention clean across all 49 skill dirs; named so the eventual violation is detected as recurrence, not novelty. MINOR per version-discipline (new mechanism: read-log hook + verify_citations is additive observability infrastructure; PostToolUse matcher on Read is structurally new but follows the change-log.sh pattern exactly). Manual-invocation only for initial ship; automatic Stop-hook integration deferred per Mycelium's observability-before-enforcement discipline. Connection to lived-friction: strong (anti-pattern #7 cluster has 10+ instances across 5 sub-classes, three of them today; user-reviewed deep-dive decomposition confirmed the gap shape and prioritized C1 as bounded-cost preventive attack on the most common failure surface).*

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

**Canvas writes — Read before Write (HARD RULE).** Every canvas file ships pre-populated as a template (header comments + placeholder fields), so on a fresh project every `.claude/canvas/*.yml` already exists. Claude Code's `Write` tool requires a prior **`Read` tool** invocation (same tool, same session) on existing files. **`cat` / `head` / `grep` via Bash do NOT satisfy this check** — they are different tool surfaces. The agent has historically conflated them (anti-pattern #7 instance #5, 2026-05-09: ~14k tokens lost to a Write-fail → Read → re-Write loop on a file the agent had already `head`'d). Use the **Read tool** on every target canvas file before any `Write` or `Edit`. Use `Edit` for partial updates (also requires prior Read). This applies to every canvas-writing skill — see the explicit Step 0 / Preflight blocks in each affected SKILL.md. Validator Check 31 enforces that every canvas-writing SKILL.md surfaces this rule. Detected during Juniors.dev pre-run dogfood (2026-05-06); strengthened 2026-05-09 after structural enforcement layer was needed.

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
