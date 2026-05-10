# Changelog

**Audience**: operators upgrading + practitioners tracking what changed.
**Time to read**: 10 min.
**Last updated**: 2026-05-10.

The live version is in [CLAUDE.md](../CLAUDE.md) first-line frontmatter — that is canonical. This page is the human-readable summary log.

## v0.23.2 — Five bias-mitigation citations from CBI gap analysis

**2026-05-10.** mycelium-roadmap dogfood (gap analysis against cognitivebiasindex.com) surfaced 6 candidate bias additions; pre-ship Read found 1 already present (Dunning-Kruger in L1+L4), 5 graduated as additive citations on existing surfaces. **Illusion of Validity** (Kahneman 2011 ch. 20) added to anti-pattern #7 source line as the established academic name for *Consistency-as-Evidence*. **Curse of Knowledge** (Camerer, Loewenstein & Weber 1989) added as a row to the L2 Opportunity-stage table in `harness/cognitive-biases.md` — founder-vocabulary risk in user interviews. **Hindsight Bias** (Fischhoff 1975) added as a new "Hindsight Bias Check" section in `/retrospective` SKILL.md — counters "we should have seen X coming" rewriting uncertainty as foreknowledge. **Hyperbolic Discounting** (Laibson 1997) added to `/ice-score` Step 5 bias check — near-term Impact overweighting at the expense of longer-horizon outcomes. **Decoy Effect** (Huber, Payne & Puto 1982) added as a Rule in `/ost-builder` — no decoy solutions whose only purpose is to make a preferred option look better. CBI's 14 "tools" all map cleanly to existing Mycelium mechanisms (decision-log, /devils-advocate, /fan-out, /assumption-test, etc.) — no method-level borrowing recommended. User overrode the draft's "wait for real failure" promotion bar; override logged in `mycelium-roadmap/.claude/drafts/cbi-gap-followups.md`. PATCH per version-discipline (additive citations + 1 new table row + 1 new mitigation section in existing skill; no new mechanism, no behavior change beyond the named-and-mitigated biases).

## v0.23.1 — CLAUDE.md restructure

**2026-05-10.** Version history (0.16.0 → 0.23.0) moved from CLAUDE.md into this changelog. CLAUDE.md was 67k chars / 262 lines, with the version preamble alone consuming ~55k. Behavioral content unchanged. Current-version line preserved as Check 26 trigger + agent priming. PATCH per version-discipline (doc-only restructure; no new mechanisms).

## v0.23.0 — Team Topologies multi-agent dogfood findings

**2026-05-09.** Five parallel subagents in isolated git worktrees (3 stream-aligned + 1 platform + 1 stream cross-team) with mechanism-only scoping; social/cognitive findings tagged speculation and discarded at fan-in per anti-pattern #7. Two-agent independent corroboration on F1/F2/F4. **F1 (schema gap, doc-only):** `docs/philosophy.md` adds "What Mycelium does not yet do (single-team scope cut)" naming the deliberate constraint that data + orchestration models assume one author/team/diamond-flow at a time; Team Topologies vocabulary is described content (`/mycelium:team-shape`, L1 strategy table, `team-shape.yml`), not operational discriminator. Four absences named (no `owned_by_team`, no stream→platform request primitive, no interface-contract doc, silent semantic overwrite on multi-author writes). Trigger for revisiting: real adopter brings a two-team setup. **F6 hot-fix (hook deadlock):** `framework-guard.sh` tries `${CLAUDE_PLUGIN_ROOT}/scripts/framework_guard.py` first then falls back to legacy `.claude/scripts/`; legacy path was hardcoded post-0.20.x → bootstrap deadlock. Same hook gains MCP filesystem coverage (`mcp__filesystem__write_file|edit_file|move_file`) — bypass surfaced during dogfood. `framework_guard.py` gains `_handle_mcp_filesystem_path` + `_handle_mcp_filesystem_move` (move handler checks both source + destination). **F8 (Validator Check 32):** `check_four_risks_when_active()` enforces that opportunities referenced by active diamonds have populated `value/usability/feasibility/viability.level` fields. Closes the false-negative gate where `/mycelium:diamond-progress` step 2 vacuously passed when levels were absent. WARN-level initially. **F4 (cluster ledger):** Three new instances of `documented-rule-diverges-from-enforcement` cluster (10/11/12); total 9 → 12; spec-graduation status preserved. MINOR per version-discipline. Theory: Skelton & Pais *Team Topologies*; preferred-blind-subagent-assumption-test pattern; subagent-simulation ≠ lived-friction caveat.

## v0.22.0 — Behavioral enforcement layer for anti-pattern #7

**2026-05-09.** Documentation-only graduation (0.21.0) shipped the named anti-pattern + /devils-advocate Technique 4 + /corrections-audit Step 6d + G-P-pre item 9, but FIVE instances of the same self-application failure occurred in one session post-graduation — TWO within the same hour. Documentation does not produce behavior; structural enforcement does. **F1:** Every canvas-writing SKILL.md (22 skills) gains a `## Preflight: Read target canvas file(s) before any Write/Edit` block naming the failure mode (head/cat/grep via Bash do NOT satisfy the Read-before-Write check), the cost (~14k tokens per failure cycle), and the citation. **F2:** New Validator Check 31 scans Update/Write/Append-mentioning SKILL.md files against `.claude/canvas/*.yml` and verifies the Preflight marker is present (currently passes for all 15 canvas-writing skills; WARN if any future skill ships without it). **F3:** CLAUDE.md "Canvas writes — Read before Write" rule strengthened with explicit HARD RULE label + cost framing; `/mycelium:diamond-assess` Step 3 now carries a Read-before-claim hard rule. MINOR per version-discipline. The anti-pattern's own graduation surfaced exactly the structural enforcement layer Argyris double-loop predicts.

## v0.21.1 — Hygiene patch (plugin.json drift + Check 30)

**2026-05-09 (commit `72bada4`).** 0.21.0 ship missed bumping `plugins/mycelium/.claude-plugin/plugin.json` (still at 0.20.11 while CLAUDE.md was at 0.21.0). Same coupled-field drift class as the 0.20.x dogfood B2 finding but at MINOR-bump scale. plugin.json bumped to 0.21.1 (tracks CLAUDE.md exactly). New Validator Check 30 enforces the invariant going forward (parses leading `*Version` line from CLAUDE.md and `version` from plugin.json, fails on drift). PATCH per version-discipline.

## v0.21.0 — Three anti-pattern graduations

**2026-05-09.** **(#7) Consistency-as-Evidence:** constructing causal chains where ≥1 link rests on observational consistency rather than verified attribution. Three documented instances (2026-04-30 Hoskins over-scoping, 2026-05-03 sharper-framing anchoring, 2026-05-09 Frida verbosity-attribution gap). Distinct from confirmation bias (attention-direction failure) — this is attribution failure (misclassifying evidence in hand). Source: Pearl causal inference. **(#8) Stale State Read:** scripts/validators reading state files the same operation is about to replace, producing nominally-correct output against the wrong reference. Four documented instances. Worked example: `parse_manifest.py --manifest=<path>`. **Bias cluster → ambient `/devils-advocate`:** "agent prefers what feels right over what evidence supports" graduated as Techniques 4 (attribution-vs-consistency labeling) and 5 (ambient triggering on assertion-shaped patterns) — converts anti-bias discipline from per-decision ceremony to per-publish self-check. Plus integration: `/corrections-audit` Steps 6d/6e, validator Check 29, CLAUDE.md G-P-pre item 9. MINOR per version-discipline.

## v0.20.15 — Legacy install path deprecated + manifest single-source

**2026-05-09 (commit `1e592f0`).** Three coordinated changes. **(1)** Legacy `npx degit` install path explicitly deprecated; README's "Legacy install" subsection rewritten as deprecation notice (a fresh degit lands an empty `.claude/` with no skills/hooks/engine). Removal scheduled for v0.21.0 / 2026-06-09. **(2)** Stale-upstream detection in `upgrade.sh` legacy refresh mode: when upstream tree has no `.claude/skills/` or `.claude/engine/`, exits with "the canonical Mycelium has moved to plugin form" message recommending `--migrate-to-plugin` or `/mycelium:migrate-from-legacy`. **(3)** `docs/migration.md` gains "Recovering from a broken legacy refresh" section covering four common failure modes. **Manifest dual-source decision:** `plugins/mycelium/manifest.yml` is canonical; `.claude/manifest.yml` is the deprecated legacy copy retained for in-flight migration users (deletion target v0.21.0 / 2026-06-09). New Validator Check 28 enforces byte-equality while both exist. PATCH per version-discipline.

## v0.20.14 — CI restored after legacy `.claude/` cleanup

**2026-05-09 (commit `218477c`).** 0.20.13 migration deleted `.claude/tests/validate-template.sh` + Python tests + auto-dogfood orchestrator, breaking `validate.yml` and orphaning `dogfood.yml`. **(1)** Validator + Python tests rehomed at repo root (`tests/validate-template.sh` + `tests/python/`); REPO_ROOT calc updated; all `.claude/scripts/` references in validator updated to `plugins/mycelium/scripts/`; material_paths in Check 26 stripped of dead `.claude/{skills,engine,harness,hooks,scripts,templates,tests}` entries. **(2)** `plugins/mycelium/manifest.yml` added (copy of `.claude/manifest.yml`) so plugin's `parse_manifest.py` works standalone for `--migrate-to-plugin`. **(3)** `validate.yml` updated to call `bash tests/validate-template.sh`, `python3 plugins/mycelium/scripts/validate_canvas.py`, `pytest tests/python/`; path triggers extended to `plugins/mycelium/**`, `.claude-plugin/**`, `tests/**`, `docs/**`. **(4)** `dogfood.yml` deleted. Validator: 24 passed, 0 failed, 4 warnings. PATCH per version-discipline.

## v0.20.13 — Self-migration dogfood (legacy `.claude/` removed upstream)

**2026-05-09 (commits `7c2a89d` + `e0825be`).** Maintainer ran `--migrate-to-plugin` on upstream and downstream Mycelium repos themselves. **(1)** Legacy `.claude/` framework tree removed from upstream (180 files, 27,464 lines deleted on `chore/legacy-cleanup`); plugin form is now the only Mycelium install path on main. Project state in upstream's `.claude/` (canvas, diamonds, memory, decision-log, evals, drafts, manifest.yml, settings) preserved untouched. **(2)** README.md gains "Heads-up if your install is older than v0.20.10" callout: `--migrate-to-plugin` flag was added in 0.20.10, so older installs misinterpret it as a version arg. Workaround: refresh first, then re-invoke with the flag. PATCH per version-discipline.

## v0.20.12 — Receipts case for plugin-form dogfood

**2026-05-09 (commit `c3cecca`).** New receipts case `docs/receipts/cases/2026-05-09-plugin-form-dogfood.md` capturing: 5 bugs surfaced and closed same-day (B1-B5), the load-bearing L0 adoption assumption ("The harness is light enough that people keep choosing it past the first friction moment"; Cagan four-risks: usability), the operational test design from `/mycelium:assumption-test`, and the framework recusing itself from `/mycelium:bias-check` on its own test design. Lessons: subagent simulation ≠ lived friction; detection-then-route must be a hard gate; variable expansion at Write boundaries is an environment leak; Check 26 must watch manifest files. Receipts indexes updated. PATCH per version-discipline.

## v0.20.11 — Five bug fixes from plugin-form dogfood

**2026-05-09 (commit `5f1b416`).** **B4:** `setup/SKILL.md` warnings-log.md starter content was getting `${CLAUDE_PLUGIN_ROOT}` expanded by the agent during Write, baking the maintainer's absolute path into every user's project. Fixed by switching to prose + explicit "do NOT expand" instruction. **B1:** `start/SKILL.md` Step 2 detection was honored AFTER the agent already ran setup-style `mkdir -p`, causing Read-before-Write tool errors. Fixed by promoting detection to a HARD GATE. **B2:** `plugin.json` version stayed pinned at 0.20.0 while CLAUDE.md moved through 10 patches; ping marker drifted similarly. Fixed: plugin.json bumped to track CLAUDE.md (skill count corrected 45 → 49); ping marker made shape-stable (no version suffix). **B3:** Validator Check 26 watched CLAUDE.md but not `plugin.json` or marketplace.json; `plugins/mycelium/.claude-plugin/plugin.json`, `plugins/mycelium/.claude-plugin/marketplace.json`, `.claude-plugin/marketplace.json` added to material_paths. **B5:** Setup didn't acknowledge `.claude/state/` (Claude Code's runtime state directory). Fixed with one-line note. PATCH per version-discipline. Dogfood also produced the L0 adoption test design at `.claude/evals/assumption-tests/L0-adoption-test.md` (n=5, pre-committed Persevere/Ambiguous/Pivot/Kill thresholds).

## v0.20.10 — Legacy → plugin migration path

**2026-05-08 (commit `34ea768`).** Three coordinated artifacts. **(1)** `.claude/scripts/upgrade.sh` gains `--migrate-to-plugin` flag (deletes legacy framework files, preserves project state — manifest-driven via `parse_manifest.py directories` + `harness_framework`) and `--check-migration` flag (read-only diagnostic). Top-level detection routes plugin-form invocations away from upgrade.sh entirely. **(2)** New skill `/mycelium:migrate-from-legacy` (8 steps: detect form, verify plugin installed, verify clean working tree, render explicit will-DELETE/will-PRESERVE preview à la Liao contrastive XAI, invoke script, verify project state survived, manual settings.json hooks-block cleanup, final commit). Idempotent. **(3)** New `docs/migration.md` with three migration paths (skill, script, manual) + reversibility notes. Skill count 48 → 49. Smoke-tested in `/tmp/migrate-smoketest`: clean delete of 9 framework directories, project state preserved. PATCH per version-discipline.

## v0.20.9 — Validator updated for plugin-form layout

**2026-05-08 (commit `828e6d2`).** Closes "Checks 6/7/9 still expect skills under `.claude/skills/`" pending item from 0.20.5. **(1)** `SKILLS_DIR` detection at top of `validate-template.sh` prefers `plugins/mycelium/skills/`, falls back to `.claude/skills/`, exits 2 if neither exists. **(2)** Every Check (5, 6, 7, 8, 9, 15, 26) threads `$SKILLS_DIR` through; Check 26 watches BOTH plugin and legacy material paths. **(3)** New Check 27 (skills-tree parity): when both trees coexist, compares skill count + name set, WARNs on divergence. New skills `ping`, `setup`, `start` had `description:`-only frontmatter; added `name:` to satisfy Check 8. Skill count 45 → 48. Validator: 24 passed, 0 failed, 5 warnings. PATCH per version-discipline.

## v0.20.8 — Dogfood-mode pattern migrated to plugin tree

**2026-05-08 (commit `96954a2`).** `interview/SKILL.md:285` (and two other surfaces) referenced `.claude/evals/dogfood-reports/README.md` "for the pattern," but plugin-form setup creates only a `.gitkeep` there — dogfood-mode users had no pattern to reference. Framework-reference content moves to plugin (`${CLAUDE_PLUGIN_ROOT}/engine/dogfood-mode.md`); `.claude/evals/dogfood-reports/` in user's project stays empty for their own reports. Updated three references. PATCH per version-discipline.

## v0.20.7 — Bare-path discipline sweep across 45 SKILL.md

**2026-05-08 (commit `70c07fb`).** Smoke-test of 0.20.6 (4 parallel blind subagents) flagged two cross-cutting pre-existing patterns the previous path-rewrite scripts didn't catch: bare project-state paths and bare framework-reference filenames. Both classes brittle once `$CLAUDE_PROJECT_DIR` and `$CLAUDE_PLUGIN_ROOT` split path resolution into two trees. Two-pass sweep: pass 1 prefixes bare project-state with `.claude/` and bare framework filenames (50 unique) with `${CLAUDE_PLUGIN_ROOT}/<dir>/`; pass 2 handles bare `<fw-dir>/X` patterns and routes `harness/decision-log.md` + `harness/warnings-log.md` to `.claude/harness/` (project-state carve-out). 36 files, ~145 path rewrites, 12 decision-log re-routes, 1 typo fix. PATCH per version-discipline.

## v0.20.6 — Onboarding void closer

**2026-05-08 (commit `b5eeb76`).** New `/mycelium:start` combiner skill that runs setup + interview universal-flow in one invocation, with a 30-second welcome (Norman: visible affordances; Krug: don't-make-me-think). `/mycelium:setup` confirmation expanded with one-paragraph welcome + framing of next move. `/mycelium:interview` cherry-picked from `feat/on-ramp` 0.19.1 with universal-flow shape (canvas-state detection + 4-question brief + informed depth menu). README + AGENTS.md: Quick Start now leads with `/mycelium:start`; both surfaces document tab-completion (`/myc<Tab>`) and natural-language invocation. Source: dogfood report 2026-05-09 — "the onboarding has worsened substantially since converting to plugin." PATCH per version-discipline.

## v0.20.5 — Plugin-form path resolution in scripts

**2026-05-07 (commit `0f073b1`).** Subagent re-verification caught that `validate_canvas.py` and `ingest_warnings.py` hardcoded `Path(__file__).parent.parent.parent` as repo root, which resolves correctly only in legacy form (`<repo>/.claude/scripts/X.py`); in plugin form (`<plugin>/scripts/X.py`) it skips a directory level and points at `plugins/`. Both scripts now use `_resolve_paths()` helper honoring `$CLAUDE_PLUGIN_ROOT` (framework-reference content) and `$CLAUDE_PROJECT_DIR` (project state) with auto-detect fallbacks. Tested in three configurations: legacy, plugin form via cwd-detect, plugin form via explicit env vars on a foreign test directory. PATCH per version-discipline.

## v0.20.4 — Plugin-form path + namespace rewrite across 45 SKILL.md

**2026-05-07 (commit `0d17210`).** 35 path rewrites (`.claude/engine/X` → `${CLAUDE_PLUGIN_ROOT}/engine/X`, same for schemas/scripts/domains/orchestration; `.claude/harness/X` excluding decision-log.md/warnings-log.md; `.claude/jit-tooling/X` excluding active-metrics.yml). 155 slash-command rewrites (`/skill-name` → `/mycelium:skill-name` across all 45 known skills). Project-state paths preserved unchanged. Resolves the headline gap from 2026-05-09 subagent re-simulation. PATCH per version-discipline.

## v0.20.3 — Framework reference tree migrated into `plugins/mycelium/`

**2026-05-07 (commit `20850da`).** Closes the architectural gap surfaced by subagent simulation 2026-05-09: `/mycelium:interview` referenced `.claude/engine/canvas-guidance.yml`, `.claude/engine/wayfinding.md`, `.claude/jit-tooling/metrics-detector.md`, `.claude/harness/security-trust.md`, etc. that the plugin did not yet ship. With this migration the plugin self-contains the full framework reference content; only project-state files (canvas/*.yml, diamonds/active.yml, memory/*, harness/decision-log.md, harness/warnings-log.md, evals/, jit-tooling/active-metrics.yml) live in user's project. Plus setup SKILL.md fixes from same simulation: explicit `.gitkeep` stubs for empty dirs, CLAUDE_PROJECT_DIR fallback documented, auto-mode default-yes policy. PATCH per version-discipline.

## v0.20.2 — Plugin-form install instructions

**2026-05-07 (commit `66fe291`).** AGENTS.md + README install instructions updated to document plugin-form install path alongside legacy `npx degit`. AGENTS.md "What's available" table updated with plugin/legacy file-location distinction. README Quick Start gains plugin-install section as recommended path. README Upgrading section gains `/plugin update` instruction. PATCH per version-discipline.

## v0.20.1 — Plugin-form migration progress

**2026-05-07 (commit `61a823b`).** 45 skills migrated to `plugins/mycelium/skills/` (commit `4656910`); 10 hooks migrated with `hooks.json` wiring all event matchers via `${CLAUDE_PLUGIN_ROOT}` paths (commit `69c00c5`); `/mycelium:setup` skill added for idempotent first-run project init (commit `eae91b6`); receipts case `2026-05-08-bentes-install-model.md` documenting Daniel Bentes's install-model finding + CONTRIBUTORS.md v0.20.0 entry crediting his second-cycle architectural review (commit `cc940e3`). Existing `.claude/` framework dir still preserved during migration. PATCH per version-discipline.

## v0.20.0 — Plugin-form bootstrap

**2026-05-06 (commit `a515448`).** Mycelium repackaged as a Claude Code plugin per Anthropic's plugin spec to solve the install-model architectural debt surfaced by Daniel Bentes 2026-05-08 (top-level framework metadata files contaminate user project root). New top-level structure: `.claude-plugin/marketplace.json` (single-plugin marketplace catalog) + `plugins/mycelium/.claude-plugin/plugin.json` (plugin manifest). Initial smoke-test skill `plugins/mycelium/skills/ping/SKILL.md` validates the plugin shape. Architecture cut documented in `plugins/mycelium/README.md`: skills/agents/hooks/harness/engine/schemas/scripts ship in plugin (versioned, replaceable, cached read-only); canvas/diamonds/memory/decision-log/evals/active-metrics live in user project (writable, gitted). Skill names become namespaced (`/interview` → `/mycelium:interview`). MAJOR-shaped change in user-facing install model (new mechanism: `/plugin marketplace add haabe/mycelium`); MINOR per version-discipline because plugin form is additive. Theory: Anthropic plugin convention; AGENTS.md open standard (Linux Foundation); Daniel Bentes BDSK architectural review; Synapti marketplace pattern study.

## v0.18.2 — Phase 3 audit + maintenance wiring

**2026-05-06.** `/corrections-audit` gains step 6c (scans `docs/receipts/cases/` YAML frontmatter for graduation signals — cluster cross-reference, mechanism-or-status pattern detection, contributor distribution audit, candidate-graduation cases, stalled-spec flags). `/canvas-health` gains step 9b (docs validation: audience markers, stub freshness >60d, length-budget hard/soft caps, last-updated >180d freshness, scent-rule scan for "click here" / "see [filename]", marketing-voice scan, receipts case frontmatter required-fields, README highlights >90d rotation candidacy). `/framework-health` gains step 4c (receipts highlights rotation cadence) + step 4d (docs cross-surface check). Internal-audience markers added to `cluster-instances.md` and `decision-log.md`. `docs/receipts/archive.md` placeholder created with archive rules. PATCH per version-discipline. Closes the multi-phase README + docs restructure (Phases 1, 2, 3 of 3 all shipped). Theory grounding: Argyris double-loop closure.

## v0.18.1 — Phase 2 content backfill

**2026-05-06.** 9 forthcoming-stub docs filled (glossary, faq, evaluate, theories, philosophy, usage-modes, jit-tooling, regulatory, changelog, contributing/README) + skills/{README,by-category}.md filled with 45-skill phase-and-category-ordered indexes. evaluate.md is the load-bearing landing for Drew Hoskins's post (~2026-05-25). usage-modes.md ships canvas-sync conflict-resolution rules answering Alex's Q from the 2026-05-07 Juniors.dev presentation. theories.md mechanism-maps every Tier 1 + Tier 2 theory to the Mycelium artifact that implements it. philosophy.md frames opinionated discipline / theory-grounded / in-loop preventive / dogfood-required / build-to-learn-vs-earn / structure-before-content as load-bearing claims. faq.md answers six Juniors.dev questions concretely. PATCH per version-discipline. Validator authority migration from Phase 1 still load-bearing — Checks 6 + 13 now actively validate populated docs/skills/ and docs/theories.md.

## v0.18.0 — README + docs/ restructure (Phase 1 of 3)

**2026-05-08.** README compressed 525 → 152 lines. New `docs/` tree spokes off README hub. Metadocumentation + style guide + 5 receipts case files + indexes ship Phase 1; 10 forthcoming-stub pages fill in Phase 2; audit + maintenance wiring lands in Phase 3. CONTRIBUTORS.md restructured with explicit "How to get listed" recruitment-shaped section. AGENTS.md expanded with portable-vs-Claude-Code-specific surface table + concrete operating models per agent class. Validator updated for new authority locations (Checks 2/3/4 deprecated, 6 reads docs/skills/, 12 reads engine/theory-gates.md, 13 reads docs/theories.md with stub-aware skip). MINOR per version-discipline.

## v0.17.0 — Documented-rule-diverges-from-enforcement cluster spec-graduated

**2026-05-08.** Cluster reached 8 instances; graduated to a spec at `engine/consistency-check-spec.md` rather than to a half-baked detection mechanism. The spec catalogs all 8 instances by subclass, articulates 5 candidate detection rules with per-rule catches/misses/FP-risk, sets the spec→mechanism promotion bar (≥3 rules implemented, <5% FP, 100% TP on cluster fixtures). `cluster-instances.md` becomes canonical instance log. `/corrections-audit` step 6b + `/framework-health` step 4b wire the cluster log into routine audits. JTBD schema gains `validation_status_per_dimension` first-class field for the Christensen tripartite. MINOR per version-discipline. Backward compatible. Closes the recursive bug where the framework's stated graduation criteria could not be mechanically counted.

## v0.16.5

**2026-05-07.** `/diamond-progress` SKILL.md step 4 includes explicit prompt-template naming the re-invocation-as-approval shortcut. Footgun → visible affordance (Norman).

## v0.16.4

**2026-05-07.** `engine/wayfinding.md` tightened with "STRICT — reproduce the template literally" + explicit list of common improvisations to forbid.

## v0.16.3

**2026-05-06.** CLAUDE.md "Canvas writes — Read before Write" paragraph: canvas files ship pre-populated as templates, so Claude Code's `Write` tool always requires a prior `Read`; `cat` via Bash does not count.

## v0.16.2

**2026-05-06.** Provenance schema accepts singular `source_class` (single enum) and `notes` (free-text) alongside plural `source_classes`. Strict mode preserved (typos still caught). Same shape as Check 26's "documented rule diverges from enforcement" cluster, at schema layer.

## v0.16.1

**2026-05-06.** Check 26 refined to WARN on uncommitted post-bump material edits; `.claude/tests/` added to watched material paths; AGENTS.md surfaces upgrade.sh + version-bump caveat.

## v0.16.0 — Self-correcting harness layer

**2026-05-04.** G-V12 (every validator ships coverage proof) + G-P-pre (Mandatory Pre-Ship Protocol with visible gap analysis) graduate two recurring patterns to mechanism. Check 26 enforces version-bump discipline (5th-instance graduation of "documented rule diverges from enforcement"). Explainability: `/xai-check` skill + Gate 13 + `ai-system-card.md` template + Mycelium's own card + context-surface doc. Warnings ingestor turns CI signals into self-learning input alongside `corrections.md`. Detector Step 1c gains `agent_runtime_target` category for harness-shaped products. `parse_manifest` gains `--manifest=<path>` override. `decision-log` gains structured `why_not_alternatives` field (Liao contrastive). +27 unit tests; coverage 52% → 78%; ruff 35 → 0. Theory citations: Doshi-Velez & Kim, Liao et al., Mitchell et al., Lanham et al., Selbst & Barocas, Bansal et al., Lopopolo, EU AI Act Art. 13/50.

See [framework-self-correction case](receipts/cases/2026-05-01-framework-self-correction.md) for the cycle that produced this.

## Earlier

For pre-v0.16.0 history, see CLAUDE.md (the version line summarizes prior bumps) and the git log on `haabe/mycelium`.

## Update discipline

When a version bumps, this page gets a new entry. Manual extraction once on v0.18.0; manual update on each subsequent bump (no automation until pain warrants — per the framework's bias against premature automation).
