# Changelog

**Audience**: operators upgrading + practitioners tracking what changed.
**Time to read**: 10 min.
**Last updated**: 2026-05-16.

The live version is in [CLAUDE.md](../CLAUDE.md) first-line frontmatter — that is canonical. This page is the human-readable summary log.

## v0.23.29 — Diamond assessment 2026-05-20 logged (audit-trail)

**2026-05-20. Attribution: dogfood-audit-trail.** `/mycelium:diamond-assess` invoked following yesterday's Edith-Mari user-test signal. Assessment logged to `.claude/harness/decision-log.md` with the full cognitive-forcing → read-before-claim → why-not-alternatives → anti-pattern-scan → reversibility structure.

**L0 Purpose**: confidence 0.61 → 0.63. Half-weight increment absorbing Edith-Mari's behavior-validation signal. L0 stays in Develop — Develop→Deliver needs density beyond a single half-weight signal.

**L1 Strategy**: held at 0.24. The 2026-05-12 devils-advocate rule ("no further L1 increments from positioning-only signals until ≥1 behavior-validation lands") was framed for arms-length validation. Edith-Mari is relationship-class, not arms-length — counts as half-weight behavior-validation but does not satisfy the L1 movement prerequisite. Arms-length cohort signal (ht-014/ht-015) remains the gate.

**Canvas-health items addressed in the same cycle**: `active.yml` refreshed (8-day staleness closed); `purpose.yml _meta.last_validated` refreshed (9-day staleness closed); landscape.yml staleness flagged but left for next pass (content is current; timestamp-only drift).

PATCH per version-discipline: decision-log entry + version line + changelog; no schema, skill, or behaviour change. Two consecutive PATCHes (0.23.28 + 0.23.29) on the same day reflect substantive cycle work (receipt + assessment) — version-discipline is designed to support this cadence at the bottom of the semver tree.

## v0.23.28 — First non-developer user signal (Edith-Mari Pedersen Bartnes book project)

**2026-05-20. Attribution: user-detected.** First non-developer user to test Mycelium end-to-end. Edith-Mari Pedersen Bartnes ran `/mycelium:start` on her book project (content_publication product-type) on 2026-05-20, reaching the assumption-test stage in ~10–15 minutes.

**Strongest positive emotional signal to date.** Brief synthesis produced a near-tears recognition moment ("captured and presented well, even though it was her own words"). Assumption test left her feeling that the framework and agent "really saw her" and what she was trying to achieve with her book. Validates the brief-synthesis-as-identity-mirror hypothesis at the affective layer for non-developer users on non-software product types.

**Five friction items surfaced**, one graduating to corrections.md:

1. Repo bootstrap confusion (creating initial files/folders before `/mycelium:start` could run) — pre-Mycelium friction; non-dev users hit it first.
2. Claude Code save/update file prompts confused her — host-runtime UX, not a Mycelium issue per se but invisible to Mycelium's UX considerations until now.
3. Long save-structure output confused her about what was important — signal-vs-noise issue for non-tech-savvy readers.
4. Chat scroll auto-bounce — when she scrolled up to answer an earlier question, the window scrolled back down. Host-runtime UX issue. She self-solved by asking the agent to repeat the question.
5. **"You are here" wayfinding gap at the assumption-test → deep-dive-interview transition.** Graduated to corrections.md — orientation mechanism previously covered initial flow only; recurs at phase transitions. Correction extends the surface to fire at every transition with explicit non-developer-user rationale.

A calming moment also worth noting: she became visibly less nervous once she realised she was talking to an AI rather than a human. The same warmth in the brief that produced the recognition moment had been producing social-presence pressure before the AI-ness clicked. One property, two effects — worth holding both in mind for future flow design.

**Attribution**: Edith-Mari gave explicit consent for public attribution on 2026-05-20. Attribution-registry (in the private roadmap repo) updated: consent: public_ok. Full receipt at `docs/receipts/cases/2026-05-20-edith-mari-book-project.md`; CONTRIBUTORS.md adds v0.23.28 cycle credit.

PATCH per version-discipline: new receipt + corrections entry + CONTRIBUTORS entry + version line + this changelog entry; no schema, skill, or behaviour change.

## v0.23.27 — README adds "Where it sits in the field" — harness engineering vocabulary anchors

**2026-05-20. Attribution: external-validation-triggered.** Documentation-only release surfacing the recently-named "harness engineering" practice on the README.

Two canonical anchors emerged in spring 2026:
- **2026-04-02**: Birgitta Böckeler / Martin Fowler / Thoughtworks article "Harness engineering for coding agent users" — practitioner thought-leadership canonical anchor on martinfowler.com
- **2026-05-18**: Ning et al. arxiv 2605.18747 "Code as Agent Harness" — 42-author academic survey

Both name "harness engineering" with explicit feedforward / feedback / computational / inferential taxonomy. Mycelium implements a worked example of this taxonomy on a markdown + canvas-YAML + validator substrate. README adds a 3-sentence "Where it sits in the field" section between "What it is in 5 lines" and "Who it's for" — date-anchored citation, no claim of endorsement, explicit acknowledgement that the family of mechanisms is consensus-forming while Mycelium's substrate and specific gating discipline remain its own design.

The positioning claim is time-bound. Re-check schedule lives in the roadmap repo at `.claude/memory/positioning-claim-recheck-harness-engineering.md` with hard checks at 2026-08-19 (3-month) and 2026-11-19 (6-month), plus soft triggers for new arxiv papers, Thoughtworks Technology Radar listings, Doppler-team follow-ups, and industry tools branding "self-improving" features. The discipline this monitors is anti-pattern #7 (Consistency-as-Evidence) applied to positioning claims that age — preventing the founder-keeps-citing-a-stale-claim failure mode.

PATCH per version-discipline: README addition only; no schema, skill, or behaviour change.

## v0.23.26 — opencode integration doc + README rotation (self-hosted positioning)

**2026-05-16. Attribution: external-validation-triggered.** Documentation-only release surfacing Mycelium-on-opencode as an honest user option.

**`docs/integrations/opencode.md`** — first user-facing doc on running Mycelium with opencode + local Ollama. Frames the option for users feeling pressure from Claude Code's pricing model (a visible 2026 trend toward self-hosted AI development workflow). Honest about what works (substrate, skills, validators, MCP, instructions via AGENTS.md/CLAUDE.md fallback) and what doesn't (Read-before-Edit not runtime-enforced, `tool.execute.after` success-only, `tui.prompt.append` silent in headless). Includes setup steps for opencode + `opencode-agent-skills` plugin + Ollama, plus a model-size guidance table (4B–8B not recommended, 14B–32B sweet spot for self-hosted, 70B+ matches Claude-on-Claude-Code discipline level). Links to the three upstream issues filed today (anomalyco/opencode #27899, #27900, #27901).

**README rotation**: tic-tac-toe (oldest, narrowest case study from 2026-04) rotates off "How Mycelium got smarter" highlights; `2026-05-09-consistency-as-evidence-graduation` rotates on (5-instance pattern graduated to anti-pattern #7 with ambient self-check — better demonstrates current verification discipline). README "Who it's for" section gains a pointer to the new opencode doc for users wanting self-hosted setups.

PATCH per version-discipline: new doc + README updates only; no schema, skill, or behaviour change.

## v0.23.25 — Phase 0 substrate audit receipt + Check-26 scope correction

**2026-05-16. Attribution: lived-friction-triggered.** Documentation-only release closing the opencode-port arc's same-day work.

**Phase 0 substrate-neutralization audit** (`docs/receipts/cases/2026-05-16-phase0-substrate-audit.md`): read-only Explore-subagent sweep of 37 substrate files (CLAUDE.md, `.claude/memory/`, `.claude/harness/`, `.claude/engine/`, `docs/`, AGENTS.md, README.md). Four coupling categories surveyed:
- Cat A (tool-surface references): 13 load-bearing findings, concentrated in CLAUDE.md + corrections.md. Read-before-Write rule is the single highest-coupling item.
- Cat B (Claude Code primitive names): hook events, slash-command namespace, auto-memory path. 11 of 13 already labelled "Claude-Code-specific" in AGENTS.md.
- Cat C (paths): `.claude/` referenced 203 times. Treated as location convention, not semantics.
- Cat D (vocabulary/framing): AGENTS.md already documents "framework vs plugin" distinction sharply.

Headline finding: substrate-neutralization claim is verifiable; coupling is visible and documented, not hidden. Three rewrites queued at ~4.5 hours total effort, deferred until either opencode adapter becomes demand-pulled or a quiet maintainer block opens post-Juniors.dev cohort signal.

**Check-26 scope correction** (`.claude/memory/corrections.md`): second same-session trip on the same root cause — `docs/receipts/cases/*.md` files ARE counted as material framework changes by Check 26, contrary to my prior mental model. New rule: bump version pre-emptively when adding any file outside obvious exclusion zones, rather than guessing at what Check 26 treats as material.

PATCH per version-discipline: audit receipt + corrections entry only; no schema, skill, or behaviour change.

## v0.23.24 — opencode port feasibility arc; two delivery patterns graduated; first real decision-log entries

**2026-05-16. Attribution: external-validation-triggered.** Documentation-only release capturing a two-step verification of a potential Mycelium → opencode port.

**Phase 0 — desk + static + binary inspection** estimated a ~1–3 day adapter and flagged three runtime unknowns: whether `tui.prompt.append` mutates the outbound prompt, whether `tool.execute.after` carries a failure signal, whether Read-before-Edit is runtime-enforced.

**Phase 1 — headless runtime test** against opencode 1.15.1 with local Ollama (llama3.1:8b 32k-ctx) overturned all three:

- `tui.prompt.append` is silent in `opencode run` (TUI-scoped only; no documented headless equivalent).
- `tool.execute.after` is success-only — a failed `read` of a nonexistent file fires `before` but never `after`. Errors reach the message stream, not the hook stream.
- Read-before-Edit is **prompt-level only** — the precondition string is in the LLM-facing tool description, not the runtime code path. A clean edit succeeded on a fresh session with no prior read. The Phase 0 binary-inspection conclusion that the precondition was "mechanically enforced" was wrong.

Adapter cost estimate inverts to ~1–2 weeks; PR deferred indefinitely. Substrate-neutralization discipline (canvas + memory + harness + validators as harness-neutral source-of-truth) kept regardless — free option value either way.

**Two delivery patterns graduated** to `patterns.md`:

1. **Don't infer runtime enforcement from schema/description strings.** Binary strings prove what the agent is told, not what the runtime enforces. To reach enforcement evidence: construct the condition the schema warns against, run it against the runtime, observe.
2. **Symmetric API names don't imply symmetric semantics.** `before`/`after` pairs promise temporal ordering, not population symmetry. Any reflexion/cleanup logic depending on "for every X.before I get X.after" must be runtime-verified.

Both are structural twins of anti-pattern #7 (consistency-as-evidence) applied to the framework's own analysis of host runtimes.

**Decision-log gains its first two entries**: "Adopt two-lane harness path (Claude Code + opencode)" at confidence 0.55, immediately superseded by "Re-scope opencode adapter post-Phase-1" at confidence 0.32 — both 2026-05-16, second references the first per the decision-log's immutability convention.

**Two receipts** under `docs/receipts/cases/`: `2026-05-16-opencode-port-feasibility.md` (Phase 0) and `2026-05-16-opencode-phase1-runtime.md` (Phase 1, includes the meta-correction that the Phase 0 binary-inspection conclusion was wrong).

PATCH per version-discipline: documentation + decision-log + memory additions only; no schema change, no skill change, no behavior change for downstream users.

## v0.23.23 — Check 33 scope expansion + WARN→FAIL graduation + pre-disclosure cleanup (mechanism complete)

**2026-05-15. Attribution: lived-friction-triggered.** Three-part graduation closing the named-attribution mechanism stack:

**Part 1 — Check 33 scope expansion**:

Prior scope was `plugins/mycelium/` only, justified as "plugin-marketplace-distribution boundary." But `docs/`, `CLAUDE.md`, `README.md`, `.claude/memory/` are all publicly visible on GitHub even though they don't ship via the plugin — and the v0.23.21 leak hit exactly those paths. Public-visibility scope is the correct boundary, not plugin-distribution scope. New scan paths:

- `plugins/mycelium/` (kept)
- `CLAUDE.md`, `README.md`, `AGENTS.md`, `CONTRIBUTORS.md` (top-level docs)
- `docs/` (recursive)
- `.claude/memory/{corrections,patterns,cluster-instances}.md` (project memory)
- `.claude/canvas/` (canvas state — gitignored in this repo per framework-on-framework exemption, but covered for forks that don't gitignore it)
- `.claude/harness/`, `.claude/engine/` (legacy paths for non-plugin installs)
- `tests/` (catches leaks in test fixtures and validator scripts themselves)

**Part 2 — WARN→FAIL graduation**:

When the registry IS present and Check 33 finds leaks, the check now exits 1 instead of warning. Graduation criterion ("pre-disclosure leaks addressed") satisfied by Part 3.

Layer 1 from v0.23.22 preserved: missing-registry behavior is still INFO in CI, WARN-loud in framework-self-host local context.

**Part 3 — Pre-disclosure cleanup**:

15 leaks regenericized across 4 files:
- `docs/changelog.md` — 3 spots (v0.23.13 title, v0.23.10 entry text, v0.18.x entry text). Title now reads "Cohort-attribution leak fix" instead of the prior cohort-participant-named version. Historical-accuracy preservation: git history retains the original text; only the working-tree state is regenericized.
- `docs/receipts/cases/2026-05-09-consistency-as-evidence-graduation.md` — 1 spot (verbosity-adaptation memo example regenericized).
- `.claude/memory/patterns.md` — 1 spot (named cohort-participant "fork" attribution → generic "audience-attendee fork from a cohort participant" phrasing).
- `.claude/memory/corrections.md` — 6 spots across multiple entries (the 2026-05-14 Check 33 introduction entry, the 2026-05-14 limit:1 cost-framing entry, the 2026-05-14 recurrence-flag entry, and today's 2026-05-15 recurrence-#3 entry).

**Registry update** (in private roadmap repo):

Two cohort participants (ht-014, ht-015) added to the attribution registry as `consent: generic_only`. The prior registry only flagged the ht-012 participant; the two newly-active cohort members were not yet tracked, so Check 33 wouldn't have caught their names had they leaked. Now tracked.

**Validator state after this PATCH**:

```
Check 33: 0 leaks in public-visibility scope (all flagged names absent from publicly-visible paths)
```

Mechanism complete: registry-driven detection + expanded scope + fail-on-leak + cleaned baseline.

**Sequential 4-version arc**:

The named-attribution-leak class has driven four PATCH cycles in two days, each closing a gap exposed by the previous:
- **v0.23.20** — pre-push hook for canvas validation (shipped the hook infrastructure)
- **v0.23.21** — cohort-log-driven friction fixes + in-band leak regenericize after founder pre-push catch
- **v0.23.22** — Layer 1 (Check 33 local fail-loud) + Layer 2 (pre-push runs both validators) — mechanical gates replacing cognitive ones
- **v0.23.23** — scope expansion + WARN→FAIL + cleanup — mechanism completion

Each version satisfies the Hashimoto principle: detect a discipline gap → engineer a mechanism that catches it → verify the mechanism by walking through the next failure attempt. The recurrence count for this class started at 3; one more recurrence (a fourth instance) would now be caught at edit-time by the expanded Check 33 running through the pre-push hook before reaching `origin/main`.

PATCH per version-discipline: validator behavior change + content regenericize; no schema change, no skill change, no behavior change for downstream users.

## v0.23.22 — Layer 1 + Layer 2: Check 33 context-aware fail-loud + pre-push hook runs both validators

**2026-05-15. Attribution: lived-friction-triggered.** Three documented graduations had not prevented recurrence of the named-attribution-leak class (v0.23.13 initial → v0.23.14 commit-message-as-public-surface → v0.23.21 working-tree-leak, all logged in `.claude/memory/corrections.md`). The auto-memory rule was a cognitive gate; cognitive gates degrade across long sessions. This PATCH replaces cognitive gates with mechanical ones at two layers.

**Layer 1 — Check 33 context-aware fail-loud**:

The validator's named-attribution-registry check (`tests/validate-template.sh` Check 33) previously fail-opened uniformly when `$MYCELIUM_ATTRIBUTION_REGISTRY` was absent. The fail-open was intentional for CI (CI runners legitimately can't reach the private companion repo where the registry lives) but undifferentiated from local-dev — which is exactly where edits happen and where the registry SHOULD be configured.

New behavior:
- `$CI` or `$GITHUB_ACTIONS` set → INFO (unchanged; CI fail-open preserved).
- Framework-self-host detected (`plugins/mycelium/.claude-plugin/plugin.json` exists AND `CLAUDE.md` starts with `# Mycelium:`) AND registry absent → **WARN with explicit setup guidance** (was INFO). Surfaces the missing-registry state at the moment of every local validator run.
- Downstream user / non-self-host project → INFO (check is maintainer-side; downstream users don't have a cohort registry concern).

Framework-self-host detection uses the same convention as the v0.23.16 framework-on-framework exemption — no new mechanism, just reusing the established marker.

**Layer 2 — pre-push hook runs both validators**:

The pre-push hook script (`plugins/mycelium/scripts/git-pre-push-example.sh`, shipped v0.23.20) previously ran only `validate_canvas.py`. v0.23.21's leak passed the canvas validator (schema was clean) and would have reached `origin/main` if the founder hadn't caught it manually in commit-message review.

New behavior:
- Hook still runs `validate_canvas.py` first (existing canvas-schema check).
- If `tests/validate-template.sh` exists in the repo (or `.claude/tests/validate-template.sh` for legacy), the hook now runs it too. This surfaces Check 33 (named-attribution scan) and the other 33 structural-integrity checks at push-time as a backstop.
- Downstream user projects don't ship `tests/` — they skip this branch gracefully (the hook detects absence and exits 0 from that branch).

Both repos (`mycelium`, `mycelium-roadmap`) have their local `.git/hooks/pre-push` updated to the new version. Per-clone state, not in git, dogfooding only.

**What this PATCH does NOT do**:
- Does NOT clean up the 3 pre-existing leaks already on `origin` from older versions (v0.23.13 title, v0.23.10 entry, v0.18.x entry naming a cohort participant). Separate regenericize PATCH candidate.
- Does NOT graduate Check 33 leak detection from WARN to FAIL when registry IS present and leaks are found. Depends on the pre-existing-leak cleanup landing first.
- Does NOT add a PostToolUse hook for edit-time interception (Layer 3 from the 2026-05-15 deep-dive). Held until Layer 1 + Layer 2 prove insufficient against future recurrence.

**Theory connection**:

This is the Hashimoto principle applied recursively. Each prior graduation (registry move, CI fail-open documentation, auto-memory rule) was a partial mechanism. The auto-memory rule failed because cognitive gates degrade. Layer 1 + Layer 2 are mechanical gates that fire on every validator run and every push, not on agent vigilance. Per the framework's own discipline (graduated v0.23.16): the corrections-to-mechanism pipeline only counts when the mechanism is *engineered*, not memorized.

PATCH per version-discipline: validator behavior change + hook script extension; no schema change, no skill change, no behavior change for downstream users beyond the (correctly-shaped) push-time backstop.

## v0.23.21 — ht-012 cohort-log driven: Q1 constraint visibility, time-budget expectation, phase-index narration discipline; opp-010 logged; named-attribution leak regenericized

**2026-05-15. Attribution: cohort-log-triggered (ht-012).** Mechanism audit against the first cautious-learner cohort log (ht-012 partial_findings 2026-05-10/12, private roadmap repo) surfaced 7 partial-shipped frictions and 1 unmapped one. Three closed this PATCH, one promoted to opp-010.

**Privacy correction layered into this PATCH**: initial draft of this version named the cohort participant explicitly across 5 working-tree files (CLAUDE.md version line, this changelog entry, two SKILL.md discipline-note attributions, opp-010 description) plus 2 already-pushed entries (opp-009 evidence in commit 43989ae). Recurrence of the v0.23.13 named-attribution-leak class. User caught pre-push; regenericized in this same PATCH. Generic-only attribution discipline holds in the public framework repo per the cohort-attribution-boundary rule; named attribution stays in the private roadmap repo where disclosure-ack covers generic-framed friction flow only. Correction logged separately in framework `corrections.md`.

**Closed by this version**:

- **f4** (Q1 single-sentence constraint mis-read as rhetorical politeness; user wrote 2–3 sentences before discovering the limit was hard). Fix: format spec now appears as a bolded mechanical prefix (`**(one sentence, hard limit)**`) before the question text, not as a prose prefix (`"In one sentence, X?"`) that can be parsed as politeness register. Discipline rule added to `/interview` SKILL.md: format specs must be bolded/parenthesized, not prose.

- **f5** (user expected a time-budget question per stale README mental model; spent time re-reading skills/README to confirm she hadn't misunderstood). Fix: `/interview` Universal Brief Flow intro line now explicitly states no time-budget question at brief stage — "depth and time-cost are chosen after the brief, when you have data to choose." Aligns user expectation with current Universal Brief Flow behavior; resolves the cross-skill consistency drift between `/interview` (no time-budget) and `/mycelium:preflight` (time-budget IS asked, but for L4 delivery scoping, not L0 brief).

- **f9** (internal "Phase 6" vocabulary leaked into user-facing prompts during diamond inspection). Fix: narration-discipline rule added to both `/interview` SKILL.md and `/mycelium:diamond-assess` SKILL.md — Phase-N indices are internal skill structure and MUST NOT be narrated to users; L0–L5 diamond scales are framework-external vocabulary and ARE narratable.

**Promoted to opportunity (not shipped this PATCH)**:

- **f2** (per-file permission prompts during `/mycelium:start` with no upfront preview list; verbatim user quote in the source language preserved in private roadmap canvas — not surfaced here). Logged as **opp-010** with `evidence_type: data-supported` (schema enum; underlying class is behavior-validated per the cohort-log) and `confidence: 0.55`. **First framework-repo opportunity with real-user-research provenance** — opp-001 through opp-007 are anecdotal/N=1 partial-graduations; opp-008/009 are framework-on-framework conversational discovery (anecdotal). opp-010 is real cohort-log evidence and satisfies Torres CDH "from research, not brainstorming" rule cleanly.

  Implementation deferred pending wider cohort triangulation. Suggested shape (in opp-010 notes): add a Step 0 to `/mycelium:start` that enumerates the files/directories `setup` will create and presents them as a flat list with a single "Proceed?" prompt before per-file Claude Code permission prompts arrive. Doesn't bypass Claude Code's per-action model, but aligns user expectation with system behavior — addresses the worst part of the friction (uncertainty about scope mid-install).

**ht-012 cohort-log audit scoreboard after this PATCH**:

| Status | Count | Friction points |
|---|---|---|
| Closed | 5 | f4, f5, f6 (prior), f9, f10 (prior) |
| Partial | 4 | f1, f3, f7, f8 |
| Open as opp (deferred) | 1 | f2 → opp-010 |

5/10 frictions now fully closed. The framework cycle 0.23.16–0.23.21 has moved the cohort-log signal from 2/10 closed → 5/10 closed in two days, with the remaining four flagged for triangulation when wider cohort logs land.

**What did NOT change**: no schema change, no validator change, no new skill, no hook change. Three SKILL.md prompt-copy edits + one new opp entry. PATCH per version-discipline.

## v0.23.20 — Canvas-validation pre-push integration (capability, not auto-install)

**2026-05-15. Attribution: lived-friction-triggered.** Two CI failures on 2026-05-15 (commits 43989ae, 483dd86) — schema violations in `opp-009.trace.upstream` that the local template validator didn't catch because canvas-schema validation is a separate tool (`validate_canvas.py`) that wasn't run before push. Recurrence of "I ran one of two validators" pattern.

**What changed**:
- New reference script: `plugins/mycelium/scripts/git-pre-push-example.sh`. Resolves `validate_canvas.py` via `$CLAUDE_PLUGIN_ROOT` (with legacy fallbacks), checks `.claude/canvas/` exists, runs the validator, blocks the push with a clear error and bypass hint if it fails. Self-skips gracefully when validator or canvas dir is absent.
- Docs section in `docs/contributing/README.md`: how to wire `validate_canvas.py` into existing hook tooling (husky/lefthook/pre-commit/plain bash/GitHub Actions), plus opt-in install command for the reference hook.

**What did NOT change**:
- No plugin installer modification. Mycelium does **not** install hooks for plugin users — `.git/hooks/` is per-clone state, and most projects have or will have their own hook pipeline. The shipped pattern is *library, not framework*: provide the capability, let users integrate it.
- No PostToolUse hook (Option B from v0.23.19 deferred candidate). Pre-push catches the same class one loop later at lower implementation cost; PostToolUse remains future work if pre-push proves insufficient.
- No schema change, no skill change, no validator change.

**Sequencing notes**:

Three discussion rounds collapsed to this smaller correct shape after user pushback ("Won't the users set up their own pre-commit scripts for their project?"). The earlier proposals (Option A doc-only / Option B PostToolUse / pre-push hook auto-install) all overstepped Mycelium's seam: the framework provides discipline scaffolding, not hook-pipeline management for user repos. Original framing was scope-creep; current framing is the right boundary.

**Dogfooding**:

Local pre-push hook installed in `/Users/bartnes/Repos/mycelium/.git/hooks/pre-push` and `/Users/bartnes/Repos/mycelium-roadmap/.git/hooks/pre-push` as part of shipping this version. Per-clone state, not in git. Catches my own failures going forward; would have caught both 2026-05-15 CI failures locally.

**Watched for**:
- Recurrence of "ran one validator, missed the other" pattern on canvas edits. Pre-push hook makes the second validator non-skippable for the cohort that installs it.
- False-positive rate. If `validate_canvas.py` becomes too slow as canvas grows, pre-push pain compounds. Currently ~1s on 25-file canvas; acceptable. Calibration trigger: >5s.

PATCH per version-discipline: new reference artifact + docs section; no schema change, no skill change, no behavior change for downstream users beyond capability discoverability.

## v0.23.19 — Canvas-write Preflight: ID-scan discipline (graduated from comp-010 collision)

**2026-05-15. Attribution: lived-friction-triggered.** On 2026-05-14, the agent (this assistant) added `comp-010 "Harness engineering"` to `mycelium-roadmap/.claude/canvas/landscape.yml` without scanning the existing ID space. `comp-010` was already taken (Anthropic Outcomes, added 2026-05-07). Duplicate persisted ~24 hours in the working tree and on GitHub, caught only when adding a subsequent component (`comp-013 Semantic Anchors`) forced an ID-space scan.

**Detection mechanism already existed**: `validate_canvas.py` lines 230-239 do per-file ID uniqueness with explicit list-not-set discipline (corrections.md 2026-05-04). The check would have fired. It didn't, because the validator only ran in the framework repo's CI — not against the roadmap repo where the canvas data lives.

**Gap was enforcement timing, not detection.** Three graduation candidates identified:
- (A) Doc-only — extend the Preflight rule to require ID-scan before adding ID-bearing entries. Cheapest. Ships with the framework.
- (B) PostToolUse hook — extend `post-write-nudge.sh` to run `validate_canvas.py` against `.claude/canvas/` on canvas Edits. Mechanically enforced. Adds runtime cost.
- (C) Both A and B (belt-and-suspenders).

**v0.23.19 ships A.** B deferred to v0.23.20 candidate pending validator-runtime calibration as canvas grows. Sequencing them avoids bundling unrelated risk surfaces.

**Rule addition** to the Preflight (canonical block in CLAUDE.md + 22 canvas-writing SKILL.md files, byte-identical via script):

> **ID-bearing entries — scan the ID space before assigning.** When adding a new component, opportunity, solution, or any other ID-bearing entry to a canvas file, run `grep "^  - id: <prefix>-" .claude/canvas/<file>.yml | sort -u` first and pick the next free integer.

**Classification**: kin to anti-pattern #8 (Stale State Read) — agent reads enough of the file to satisfy the Edit check but not enough to see existing ID assignments. The v0.23.18 `limit:1` discipline made it easier (fewer tokens) to do the Edit check at minimum cost — and easier to miss the broader context needed for ID allocation. Sharpening pays for the cheap shortcut.

**Worked example** logged in roadmap-repo `.claude/memory/corrections.md` (2026-05-15 entry, commit 2cdfb42). Recurrence count: 1; structural failure shape ≥4 (anti-pattern #8 family).

**Check 31 unchanged**: matches on the `## Preflight: Read target canvas file` heading; rule body sharpened underneath. No validator change.

PATCH — doc-only sharpening of an existing discipline; no schema change, no behavior change for downstream users beyond the new convention prose.

## v0.23.18 — Read-before-Write: limit:1 discipline for Edit (~10–50k tokens/session saved)

**2026-05-14. Attribution: lived-friction-triggered.** The v0.23.x Preflight discipline correctly solved the surface-confusion failure (Bash `head` ≠ Read tool, anti-pattern #7 instance #5, 2026-05-09) but introduced a second-order cost: the agent over-applied "Read before Write" as "full Read before every Edit." With canvas files at 800+ lines (~20k tokens each), per-Edit full-Reads were dominating session token cost — meaningful on Pro-tier sessions where the 5h window already strains under Mycelium's load.

**Mechanism**: Claude Code's read-state tracking is per file, not per byte. `Read(limit:1)` registers the file at ~50 tokens and unblocks subsequent `Edit` calls anywhere in it. Verified experimentally 2026-05-14 (Read line 1 of a 5-line file, then Edited line 3 successfully).

**Rule sharpening**:
- **`Edit`** (exact-string replacement): `Read(limit:1)` satisfies the check. Use for partial updates against large canvas files.
- **`Write`** (full replacement): full Read still required. Write obliterates the file; you should see what you're about to replace. The shortcut is *not* appropriate here — safety motivation preserved.

**Shipped to**:
- `CLAUDE.md` — canonical rule under "Canvas writes — Read before Write (HARD RULE)"
- All 22 canvas-writing SKILL.md Preflight blocks (byte-identical replacement via script — no per-skill drift risk)

**Estimated savings**: 10–50k tokens per session, ongoing, every Mycelium user. Compounds across the install base.

**Check 31 unchanged**: validator still matches on the `## Preflight: Read target canvas file` heading. The rule body sharpened underneath; structural enforcement layer keeps passing.

**Third entry in the 2026-05-14 framework-health cycle**: pairs with v0.23.16 (framework-on-framework exemption) and v0.23.17 (Hashimoto + Torres external-validation citations).

PATCH — rule clarification + cost optimization; same discipline, documented cheap path.

## v0.23.17 — Citations: Hashimoto (harness engineering), Torres (AI-generated OSTs)

**2026-05-14. Attribution: external-validation-triggered.** Two convergent external signals dated 2026-05-13:

1. **Teresa Torres** ("Behind the Scenes: Building AI-Generated Opportunity Solution Trees", producttalk.org): the canonical OST source now ships AI-generated OSTs via Vistaly, generated *from* customer interview transcripts (3 → 16+). Reinforces `/mycelium:ost-builder`'s "never from brainstorming" rule with canonical-source convergence. Torres's service also surfaces a structural gap Mycelium has not yet implemented: when updating an OST from new evidence, emit a change set (add/delete/reframe/merge/split) alongside the new tree so users can accept/modify/reject each move. Logged as L3 backlog; out of scope for this PATCH.

2. **"Harness engineering" as the fourth paradigm of AI engineering** (TechTimes 2026-05-13, citing Mitchell Hashimoto's Feb 2026 blog post and Ryan Lopopolo's 2026-02-11 OpenAI definition). Hashimoto's principle — *"anytime you find an agent makes a mistake, engineer a solution such that the agent never makes that mistake again"* — names the discipline Mycelium's `corrections.md → cluster → mechanism` graduation loop implements directly. Stanford/Tsinghua research cited in the same piece reports 6x performance gaps from harness design alone with the model held constant.

Two citation edits to shipped framework files:
- `engine/cycle-learning.md` — Hashimoto + Lopopolo citation under the framework-on-framework exemption section (paired with the v0.23.16 mechanism).
- `skills/ost-builder/SKILL.md` — Torres-Vistaly citation under Theory Citations; OST-update-with-change-set gap flagged as L3 backlog.

Canvas evidence entries (landscape.yml component for "harness engineering"; purpose.yml evidence sources) land in the roadmap-repo canvas, not here — per the framework-on-framework exemption shipped at v0.23.16.

README / positioning rewrite ("Mycelium is a **theory-grounded** harness for product development") deferred to a deliberate L5 marketing diamond.

PATCH — citation additions to shipped docs; no schema change, no new validator check, no behavior change for downstream users.

## v0.23.16 — Framework-on-framework exemption for `/framework-health`

**2026-05-14. Attribution: lived-friction-triggered.** `/mycelium:framework-health` was returning early on N=0 cycles when run against this repo, because Mycelium dogfoods itself and framework improvements don't fit the OST→ICE→launch cycle schema. The actual learning signal lives in `corrections.md` graduation (21 corrections → mechanisms; Checks 30–34 are recent examples) and `cluster-instances.md`, not in `cycle-history.yml`.

Step 1 of the skill now detects the framework-self-host case (`plugins/mycelium/.claude-plugin/plugin.json` present AND `CLAUDE.md` starts with `# Mycelium:`) and routes to a corrections-graduation summary, skipping cycle-derived dimensions while still running the non-cycle-gated steps (2b router-discipline re-run, 4b cluster graduation, 4c receipts rotation, 4d docs health).

Exemption documented in `engine/cycle-learning.md#framework-on-framework-exemption` with the reconsider trigger: if Mycelium gains a second product surface (e.g., a hosted service) whose delivery fits the cycle shape, the framework-meta work moves to a parallel `framework-cycle-history.yml`. Until then, corrections graduation is the ledger.

PATCH — skill routing + doc clarification; no schema change to `cycle-history.yml`, no new validator check, no behavior change for non-self-host downstream users.

## v0.23.15 — Check 34: CLAUDE.md ≤ 1 version entry (mechanism graduation)

**2026-05-14. Attribution: lived-friction-triggered.** Graduates the discipline failure surfaced at v0.23.14 (deferred-entries-not-migrated, recurred ×5 in one session) from vigilance to mechanism. New validator check counts `^\*Version [0-9]` lines in CLAUDE.md; fails if more than 1. Latest entry stays; prior entries migrate to this file.

Pairs with Check 30 (plugin.json#version tracks CLAUDE.md) as the doc-discipline-fast-failure family. This commit dogfoods the new check by migrating v0.23.14 out (swap, not append). PATCH — observability-and-mechanism-strengthening; no behavior change for downstream users (`tests/` doesn't ship via the plugin).

## v0.23.14 — Doc-only: regenericize architecture narrative + migrate deferred entries

**2026-05-14. Attribution: lived-friction-triggered.** Two coalesced fixes flowing from the same discipline: keep deferred versions and private-architecture details out of CLAUDE.md.

1. **Forward-only regenericization** of changelog entries that named a private companion repo by path while describing v0.23.13's registry-move fix. Generalizes v0.23.13's lesson one step further: commit messages and changelog text are public-disclosure surfaces even when discussing the architecture that *supports* privacy discipline.
2. **Migrated v0.23.9 through v0.23.13** entries out of CLAUDE.md per the established convention (CLAUDE.md keeps only the current release). Five consecutive bumps this session each violated that discipline; the failure replicated forward without being noticed. Recurring-pattern graduation candidate.

Git history retains original phrasing in `c539f29` and earlier; working-tree view is now generic. PATCH per version-discipline.

## v0.23.13 — Cohort-attribution leak fix + Check 33 architecture correction

**2026-05-14. Attribution: lived-friction-triggered.** Regenericized the last Check-33 leak in `plugins/mycelium/harness/anti-patterns.md` (the date-tagged source citation that named a private-channel observer). Also collapsed an adjacent friction-log attribution to its theoretical-lens framing for consistency. Architecture correction for Check 33 / attribution-registry placement: initial 0.23.12 ship put the registry in this public repo, which was self-defeating (registry contains the very names whose private attribution it tracks). Moved out. Check 33 now resolves the registry via `$MYCELIUM_ATTRIBUTION_REGISTRY` env var; fail-open if unset.

Acknowledged residual: prior public-repo references to the same individual remain in commit history and existing changelog entries. Scrubbing fully would require git history rewrite — higher cost than the marginal incremental exposure. Forward leaks into the plugin tree are now mechanism-prevented; historical references are accepted residual.

PATCH.

## v0.23.12 — Check 33: plugin tree must not contain unconsented personal identifiers

**2026-05-14. Attribution: lived-friction-triggered.** Trigger: in-session user-asked whether a repo-root canvas file could leak into downstream user projects. The literal answer was no (plugin scope is `./plugins/mycelium/`), but the deeper question (whether names embedded in plugin-shipped files leak) surfaced 5 unconsented references in `plugins/mycelium/harness/anti-patterns.md` and `plugins/mycelium/harness/theory-tensions.md`.

**Mechanism shipped:** new validator Check 33 reads an attribution registry (kept outside the public repo) listing each known individual's consent state (`public_ok` | `generic_only` | `unknown`). The check scans `plugins/mycelium/**` for `generic_only` and `unknown` names via word-boundary regex across `.md`, `.yml`, `.yaml`, `.json`, `.py`, `.sh`. Adding a name without a consent value fails registry parsing (forces deliberate consent decisions). WARN-only initially per observability-before-enforcement discipline.

**Deeper lesson:** lived-friction attribution can leak through the graduation chain even when the source is generic-framed at point of capture. Capture-time discipline is necessary but not sufficient — every step from corrections → anti-patterns → engine docs that cites trigger sources is itself an attribution surface. GDPR data-minimization applied to internal framework documentation, not just user data.

Borderline-MINOR (new gate) but PATCH defensible because it lands WARN-only and strengthens existing G-V12 + version-discipline.md anti-leak intent rather than introducing new theory.

## v0.23.11 — Ruff cleanup pass on verify_citations.py

**2026-05-14. Attribution: lived-friction-triggered.** Check 17's 20-error WARN was sitting as de-facto indefinite tech debt with no entry in any `warnings-log.md` and no trigger condition — quiet violation of `feedback_no_tech_debt_deferral.md` ("never indefinite"). Ran validator's own ruff invocation: 4 auto-fixed via `--fix`, 17 manually fixed in `verify_citations.py` (SIM103 ×2, PLW2901, S110+BLE001 narrowed, RET504, PERF401, 9× E501 via implicit string concatenation, EXE001 chmod +x). All 14 unit tests still pass; behavior unchanged. Check 17 returns to 0 errors.

PATCH per version-discipline.md line 11 (explicit "ruff cleanup" listed as PATCH-class).

## v0.23.10 — Migration-skill truth-up + retroactive bump

**2026-05-14. Attribution: lived-friction-triggered.** Two changes coalesced because the second surfaced the first.

1. **`plugins/mycelium/skills/migrate-from-legacy/SKILL.md` Step 7 corrected.** Triggered by per-turn `No such file or directory` hook errors from a stale `"hooks"` block in `.claude/settings.local.json`. SKILL.md previously claimed the legacy migration script warned on both `settings.json` and `settings.local.json`; reality is `settings.json` only. SKILL now owns the dual-file grep itself. Considered-and-reverted: a 130-line `--migrate-to-plugin` flag handler in the plugin's `upgrade.sh` — reverted after archaeology showed the plugin copy is by-design never invoked for migration (legacy users run their local `.claude/scripts/upgrade.sh`).
2. **Retroactive bump for `2f0b003`.** The SIGPIPE fix to Check 10 landed without a version bump; validation appeared to pass because the SIGPIPE bug itself was aborting the script at Check 10 with exit 2 before Check 26 (version-bump-discipline) ran. Fixing the SIGPIPE structurally unmasked the check that would have caught its own missing bump — observer effect.

Lesson candidate for `version-discipline.md`: test-suite fixes that change which downstream checks run are structural changes to the validator's observable behavior, not cosmetic. Worth a sentence next time that doc is edited.

PATCH.

## v0.23.9 — First-run friction batch (9 patches)

**2026-05-13. Attribution: lived-friction-triggered.** Behavior-validated cautious-learner first-run observation surfaced 7 framework opportunities (opp-001 through opp-007); 5 mechanism patches shipped across hooks, skills, and README.

**Specific changes:**
1. `plugins/mycelium/hooks/stop-check.sh` — no longer emits per-turn "Session ended" line when counts are zero (opp-003 closed).
2. `plugins/mycelium/hooks/preflight.sh` + `session-start.sh` — count-display lines disambiguate three states (memory not initialized / empty / N corrections) (opp-001 partial).
3. `plugins/mycelium/skills/setup/SKILL.md` — AGENTS.md prompt rewritten with say-yes-vs-skip framing before the question (opp-002a partial).
4. `README.md` — time-budget routing description aligned with current Universal Brief Flow (opp-002b partial).
5. `plugins/mycelium/skills/interview/SKILL.md` — confidence-0.15 rationale rewritten from "hardcoded floor" framing to canvas-density formula breakdown; DEFERRED block restructured to partial-graduation checkbox status (opp-004 partial).
6. `interview/SKILL.md` brief flow — adds post-write line surfacing auto-tagged `source_class` choice + revise-path; names all five source classes (opp-005 partial).
7. `interview/SKILL.md` + `start/SKILL.md` — NARRATION DISCIPLINE block forbidding phase-number narration to users with ✗/✓ examples (opp-006 partial).
8. `interview/SKILL.md` friction-log prompt — three explicit destinations and consent gates (opp-007 closed).
9. `tests/validate-template.sh` Check 32 wrapper bug fixed (set +e / set -e around rc capture so WARN is actually WARN).

PATCH per version-discipline: all changes are bug fixes, clarification copy, or framing precedent-setting; no new skills, no new gates, no backwards-incompatible behavior.

## v0.23.8 — C1: read-log + verify_citations attack anti-pattern #7 Level 3

**2026-05-11. Attribution: lived-friction-triggered.** Triggered by Supra Insider ep 110 surfacing Apurva Garware describing the exact failure shape ("agent silently used scripts instead of skills + fabricated explanation when probed"); cross-mapped to same-day cluster activity (three fresh framing-shape instances) + deep-dive analysis decomposing the failure into four levels (skipped read / skipped steps / fabricated inputs / fabricated outputs). C1 is the bounded-cost preventive attack on Level 3 (fabricated underlying inputs in citations).

**Two new artifacts:**

1. **`plugins/mycelium/hooks/read-log.sh`** — PostToolUse hook on `Read` tool. Mirrors `change-log.sh` pattern. Appends one JSONL line per Read tool use to `.claude/state/read-log.jsonl` with schema `{ts, tool, file_path, session_id, diamond_id?}`. Fail-open (logging failure never blocks reads). Sister to `change-log.sh` — together they answer "what did the agent claim to read, read, and write during session X?"

2. **`plugins/mycelium/scripts/verify_citations.py`** — standalone Python stdlib script. Extracts `(per: <source>)` citations from agent text, classifies file-shaped vs concept-shaped via path heuristic (slash or known extension), cross-references file-shaped citations against read-log via suffix matching. Reports verified / unverified / unverifiable counts. Explicitly frames "unverified ≠ fabricated" with 4 legitimate-reason scenarios enumerated.

**Test coverage (G-V12):** 14 unit tests in `tests/python/test_verify_citations.py`. All pass. File-shape heuristic, citation extraction with dedup, suffix matching (positive + no-false-positive on `scape.yml` vs `landscape.yml`), all-verified, unverified-caught (load-bearing), concept-routing, session-id filter, missing-read-log fail-open, malformed-JSONL fail-open, end-to-end anti-pattern-7 scenario, human-format, main CLI.

**Sister observability shipped same version**: `plugins/mycelium/engine/consistency-check-spec.md` gains a "Preemptive convention registry" subsection naming the skill-folder-layout convention (one SKILL.md per dir, no helper scripts) as held-by-discipline-not-mechanism. First violation triggers graduation to validator check. Audit confirmed clean across all 49 skill dirs.

**What C1 does NOT catch**: Level-2 framing-shape instances (mechanism-vs-value language, leading-question violations, transactional-vs-relational framing). These don't reference files, so the script is structurally blind. Three such instances surfaced same day; C1 is necessary but not sufficient. **C2 (skill-execution fingerprints) and C3 (external witness)** logged as Tier 2 candidates in private follow-up drafts with concrete graduation triggers.

**Manual invocation only for initial ship.** Automatic Stop-hook integration deferred per Mycelium's observability-before-enforcement discipline.

MINOR per version-discipline (additive observability infrastructure; new PostToolUse matcher on Read; no breaking changes; no behavior change beyond logging + on-demand verification).

## v0.23.7 — Count-drift correction across surface docs

**2026-05-11. Attribution: maintenance-housekeeping.** Count-drift correction surfaced by a peer-agent fact-check during outreach drafting (the agent claimed "the public README confirms 32 anti-patterns" — no such number exists anywhere in the framework; grep-verification caught the fabrication; sister anti-pattern #7 instance #9 to yesterday's BDSK case).

Drift swept across all surface docs:
- **Skill count 45 → 49** (README.md ×2, docs/README.md, docs/skills/by-category.md ×2, .claude-plugin/marketplace.json).
- **Theory-gate count standardized to 13** (was "12" in marketplace.json, "15" in plugin.json — actual count per `engine/theory-gates.md` is 13: Evidence, Four Risks, JTBD, Cynefin, Bias, Security, Privacy, BVSSH, Service & Usability Quality, DORA/Delivery Metrics, Corrections, Regulatory, Explainability/XAI).
- Minor redundant phrasing fix in `docs/skills/README.md` ("49 skills (49 skills total)" → "49 skills").

Historical references in `docs/changelog.md` and `docs/receipts/cases/2026-05-08-bentes-install-model.md` deliberately preserved (they cite the count *at that point in history* — correct as historical record).

No anti-pattern count claim in any surface doc — the "32" was fabricated by the peer agent and didn't propagate into Mycelium content. Actual numbered anti-pattern count: 46 across 10 cluster sections.

PATCH per version-discipline (mechanical correctness fix; no new mechanism). Validator: 29 passed, 0 failed, 2 warnings (both pre-existing). Tier 3 candidate for future Validator Check 33 surfaced: skill/gate count consistency between plugin.json description, marketplace.json description, and actual `plugins/mycelium/skills/` + `engine/theory-gates.md` content — would catch this drift class mechanically. Tracked in `mycelium-roadmap/.claude/drafts/security-strengthening-followups.md` Tier 2 (count drift is a specialized case of the broader confidence-evidence-coupling validator candidate).

## v0.23.6 — Security strengthening: threat model + memory-poisoning surveillance + OWASP citations

**2026-05-11. Attribution: mixed (research-while-here + lived-friction-triggered).** Triggered by an in-session security deep-study request + a same-day anti-pattern #7 instance #9 (subagent-output-verification sub-class, BDSK-fabrication caught by user prompt). Three coordinated changes:

**(1) New `docs/threat-model.md`** — consolidated entry point for "what attacks does Mycelium worry about, and what does it do about them." Captures 7 Mycelium-specific threats (T-M1 Memory Poisoning, T-M2 Indirect Prompt Injection, T-M3 Secret Leakage, T-M4 Hook Tampering, T-M5 Sub-agent Escalation, T-M6 Audit-Trail Laundering, T-M7 Marketplace-Install Trust) structured against OWASP Top 10 for LLM Applications 2025 + OWASP Agentic AI Threats and Mitigations Feb 2025. Cross-references existing scattered pieces (harness/security-trust.md, docs/ai-system-card.md, anti-patterns.md cognitive cluster, harness/context-management.md sister doc). External-reviewer-shaped — primary audience is auditors who shouldn't have to assemble the answer from five files. Attribution: research-while-here.

**(2) New SessionStart hook Check 7 — memory-poisoning surveillance.** Watches recently-changed (<7 days) `.claude/memory/*.md` and `.claude/harness/decision-log.md` for imperative-shaped bullet content (`Run`, `Execute`, `Delete`, `Send`, `Curl`, `Wget`, `Push`, `Force`, `Disable`, `Bypass`, `Skip`, `Ignore`, `Override`, `Fetch`, `Download`, `Install`, `Eval`, `Exec`) as PR-shipped-instruction signal. **Observability, not enforcement** — surfaces a warning, not a block. Conservative detection (low FP at cost of missed catches). Addresses OWASP Agentic T1 (Memory Poisoning) which was unmitigated at framework layer prior to this ship; the receipts/contributors-as-recognition GTM mechanism (landscape.yml#strategic_frame) deliberately creates an inbound contribution pathway for memory files — the structural defense follows the structural decision. Attribution: lived-friction-triggered (the 2026-05-11 BDSK-fabrication anti-pattern #7 instance + the receipts mechanism design are the load-bearing triggers).

**(3) Citation backfills in `harness/security-trust.md`** Prompt-Injection Defense section — OWASP LLM Top 10 (2025) explicit (LLM01/02/05/06 named as load-bearing four for agentic dev-tool harness) + OWASP Agentic Threats (T1/T2/T15) added + Anthropic prompt-injection-defenses 2026 (substrate-layer RL refusal ~1% attack success on Opus 4.5) + Microsoft Spotlighting paper (arXiv 2403.14720, three techniques: delimiting/datamarking/encoding) as primary source. Tag-wrapping convention explicitly framed as folklore-grade alone, compounds with substrate defense rather than replacing it. Attribution: research-while-here.

PATCH per version-discipline (additive doc + new hook check + citation backfills; no new enforcement mechanism — the memory-poisoning warning is observability). Roadmap-side draft `mycelium-roadmap/.claude/drafts/security-strengthening-followups.md` tracks Tier 2 (6 candidates) and Tier 3 (5 deferred items). The 2026-05-11 anti-pattern #7 instance #9 (subagent-output-verification sub-class, BDSK-fabrication caught by user prompt) is logged in `mycelium-roadmap/.claude/memory/corrections.md` and `cluster-instances.md` (instance count 6+ → 7+).

## v0.23.5 — Context-rot defense layer doc + per-graduation attribution discipline

**2026-05-10. Attribution label: `research-while-here`.** Triggered by an in-session research request on context rot for AI agents (specifically Claude). Three coordinated changes: **(1) New harness doc `harness/context-management.md`** codifying Mycelium's structural defense against context rot — six rot mechanisms (lost-in-the-middle, attention dilution, instruction drift, NIAH degradation, compaction loss, prompt-cache bloat) mapped against existing Mycelium defenses (phase-scoped loading, JiT detection, two-memory system, Read-before-Write, canvas as SSOT, externalize-everything). Explicitly names the **blind subagent pattern** as a context-rot defense. Calls out Claude-specific findings: Claude is *especially* sensitive to irrelevant surrounding context per Chroma's 18-model study (largest performance gap between focused vs full-context prompts on LongMemEval), making Mycelium's discipline of phase-scoped loading particularly Claude-suited. Lists known gaps (prompt-cache strategy, conversation-length detection, instruction-budget calculation rules, coherent-haystack risk) without graduating speculative defenses. Primary sources: Liu et al. 2023 (arXiv:2307.03172) — peer-reviewed for U-curve attention; Chroma "Context Rot" 2025 — empirical 18-model study; NVIDIA RULER (NeurIPS 2024); Anthropic Engineering "Effective context engineering for AI agents" + Claude Code postmortem 2026-04-23 (worked failure case where compaction logic fired every turn). **(2) Citation backfills**: Recency Bias in Context (`harness/cognitive-biases.md`) cites Liu 2023 + cross-references Knowledge Reconstruction Tax + the new doc; Cognitive Offloading Loop + Knowledge Reconstruction Tax (`harness/anti-patterns.md`) cite Chroma 2025 + cross-reference each other and the new doc. The symptomatic-bias and structural-anti-pattern now sit beside each other in the agent's mental model. **(3) Per-graduation attribution discipline**: new section in `engine/version-discipline.md` requires every Version line to include a dominant attribution label (`lived-friction-triggered` / `research-while-here` / `maintenance-housekeeping` / `scheduled-discipline`); new Work-Mode Mix section in `engine/feedback-loops.md` defines the four modes + when each is fine vs risky. Surfaced 2026-05-10 in-session as the discipline that closes a meta-instance of anti-pattern #7 at the graduation-velocity layer (one genuine lived-friction trigger from earlier in the day extending into a session-long streak via consistency rather than per-graduation attribution). PATCH per version-discipline. Connection to lived-friction: medium — today's CLAUDE.md restructure (51k → 17.9k) was implicit attention-budget management; today's 4-bump session is the multi-turn agent-loop scenario the research describes; meta-instance of anti-pattern #7 surfaced the graduation-velocity failure surface concretely.

## v0.23.4 — Seven primary-source citations from Laws-of-Software-Engineering gap analysis

**2026-05-10.** Same playbook as v0.23.2 (CBI graduations); 7 Tier-1 candidates from a 56-law catalog (lawsofsoftwareengineering.com, Milan Milanović) graduated as primary-source citations on existing surfaces. **Hyrum's Law** (Wright et al. *Software Engineering at Google* 2020) → `engine/version-discipline.md` Theory grounding, articulating why version-bump discipline is load-bearing in plugin-form install. **Postel's Law / Robustness Principle** (RFC 793, Postel 1981) → `engine/consistency-check-spec.md`, retroactive citation for the 0.16.2 schema fix accepting both `source_class` and `source_classes`. **Leaky Abstractions** (Spolsky 2002) → `engine/version-discipline.md`, citing the bare-path sweeps (v0.20.7 + v0.23.3) as instances. **Tesler's Law of Conservation of Complexity** → `jit-tooling/detector.md`, articulating the JiT philosophy. **Gall's Law** (Gall *Systemantics* 1975) → `engine/framework-reflexion.md`, naming the mechanism-graduation discipline. **Cunningham's Law** → `/devils-advocate` as Technique 6 (publish-rough-then-iterate). **Brooks's Law** (Brooks *Mythical Man-Month* 1975) → `domains/delivery/CLAUDE.md` Theory of Constraints section with AI-assisted variant. Three citations (Hyrum, Postel, Leaky Abstractions) connect directly to lived-friction from the same week. PATCH per version-discipline (citation additions on existing surfaces; no new mechanism). 15 Tier-2 candidates tracked in `mycelium-roadmap/.claude/drafts/lawsose-gap-followups.md` for trigger-driven graduation.

## v0.23.3 — Bare-path discipline sweep (round 2)

**2026-05-10.** Trigger: mycelium-roadmap dogfood ran `/mycelium:metrics-pull` and the skill failed to find adapters because `metrics-pull/SKILL.md` referenced `metrics-adapters/<source>.md` as a bare path that resolves relative to user project root, not the plugin tree. v0.20.7's first-level sweep covered top-level dirs (`engine/`, `harness/`, etc.) but missed sub-directory paths and several cross-plugin-tree refs. Audit fixed two classes: **(1) `metrics-adapters/` references** — 18 sites across `metrics-pull/SKILL.md`, `metrics-detect/SKILL.md`, `interview/SKILL.md`, `jit-tooling/metrics-detector.md`, and the four files inside `jit-tooling/metrics-adapters/` itself (TEMPLATE.md, github.md, GENERATING.md, active-metrics.example.yml). **(2) Cross-plugin-tree refs in framework files** — 12 sites in `harness/anti-patterns.md`, `orchestration/operations.md` + `orchestration/modes.md`, `engine/leaf-lifecycle.md`, `engine/feedback-loops.md`, `engine/xai-canvas-threading.md`, `corrections-audit/SKILL.md`. All routed correctly: framework-resident → `${CLAUDE_PLUGIN_ROOT}/<dir>/`, project-state → `.claude/<dir>/`. Glob patterns in prose, GitHub-rendered markdown links, and `setup/SKILL.md` AGENTS.md template body bullets (under `.claude/` section header) deliberately preserved as bare. Same class as v0.20.7; triggered by real lived-friction (the metrics-pull skill failed visibly during dogfood) — same epistemic structure as the 0.20.11 plugin-form findings: subagent simulations miss what real invocation surfaces. PATCH per version-discipline (mechanical content rewrite, correctness fixes; no new mechanism).

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

**2026-05-09.** **(#7) Consistency-as-Evidence:** constructing causal chains where ≥1 link rests on observational consistency rather than verified attribution. Three documented instances (2026-04-30 Hoskins over-scoping, 2026-05-03 sharper-framing anchoring, 2026-05-09 cohort-log verbosity-attribution gap). Distinct from confirmation bias (attention-direction failure) — this is attribution failure (misclassifying evidence in hand). Source: Pearl causal inference. **(#8) Stale State Read:** scripts/validators reading state files the same operation is about to replace, producing nominally-correct output against the wrong reference. Four documented instances. Worked example: `parse_manifest.py --manifest=<path>`. **Bias cluster → ambient `/devils-advocate`:** "agent prefers what feels right over what evidence supports" graduated as Techniques 4 (attribution-vs-consistency labeling) and 5 (ambient triggering on assertion-shaped patterns) — converts anti-bias discipline from per-decision ceremony to per-publish self-check. Plus integration: `/corrections-audit` Steps 6d/6e, validator Check 29, CLAUDE.md G-P-pre item 9. MINOR per version-discipline.

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

**2026-05-06.** 9 forthcoming-stub docs filled (glossary, faq, evaluate, theories, philosophy, usage-modes, jit-tooling, regulatory, changelog, contributing/README) + skills/{README,by-category}.md filled with 45-skill phase-and-category-ordered indexes. evaluate.md is the load-bearing landing for Drew Hoskins's post (~2026-05-25). usage-modes.md ships canvas-sync conflict-resolution rules answering a cohort participant's Q from the 2026-05-07 Juniors.dev presentation. theories.md mechanism-maps every Tier 1 + Tier 2 theory to the Mycelium artifact that implements it. philosophy.md frames opinionated discipline / theory-grounded / in-loop preventive / dogfood-required / build-to-learn-vs-earn / structure-before-content as load-bearing claims. faq.md answers six Juniors.dev questions concretely. PATCH per version-discipline. Validator authority migration from Phase 1 still load-bearing — Checks 6 + 13 now actively validate populated docs/skills/ and docs/theories.md.

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
