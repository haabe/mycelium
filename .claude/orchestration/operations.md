# Mycelium Operations Guide

Day-to-day, week-to-week, and month-to-month guidance for maintaining a healthy Mycelium practice.

## Session Resumption (Day 2+)

When starting a new session on an existing Mycelium project:

**Note**: The SessionStart hook (`session-start.sh`) automatically checks for overdue strategic feedback loops (BVSSH, DORA) and reminds you at the start of every session.

1. Run `/diamond-assess` -- see current state in plain language
2. Read the output: which diamonds are active, what phase each is in, what's recommended
3. If multiple diamonds are active, prioritize:
   - **Blocked diamonds first** (unblock before starting new work)
   - **Delivery diamonds** (finish what's in progress before starting new discovery)
   - **Highest-confidence opportunities** (don't scatter -- focus)
4. Read the last few entries in `decision-log.md` for context on recent decisions
5. Continue from where the assessment says

## Weekly Routine

| Activity | Frequency | Skill |
|----------|-----------|-------|
| Review corrections.md | Every session | `/preflight` (automatic via hooks) |
| Assess diamond state | Start of week | `/diamond-assess` |
| Update active canvas files | As evidence changes | `/canvas-update` |
| Check delivery health | During delivery | `/dora-check` |
| Feedback loop health | Weekly | `/feedback-review` |

## Monthly Routine

| Activity | Frequency | Skill |
|----------|-----------|-------|
| BVSSH health check | Monthly | `/bvssh-check` |
| Wardley map review | Monthly | `/wardley-map` |
| Value stream review | Monthly (if mapped) | `/dora-check` + `canvas/value-stream.yml` |
| Stale diamond cleanup | Monthly | See Diamond Lifecycle below |
| Corrections pruning | When > 30 entries | See Memory Maintenance below |

## Quarterly Routine

| Activity | Frequency | Skill |
|----------|-----------|-------|
| North Star metric review | Quarterly | Review `canvas/north-star.yml` |
| Strategic landscape refresh | Quarterly | `/wardley-map` full refresh |
| Purpose validation | Quarterly | Re-read `canvas/purpose.yml`, challenge with `/devils-advocate` |
| Eval benchmark run | Quarterly | `/eval-runner run-all` |
| Comprehensive feedback review | Quarterly | `/feedback-review` (full Loop 4 check) |
| Eval benchmark | Quarterly | `/eval-runner run-all` |

## Release Checklist (per minor version)

Run before tagging each minor release (v0.x.0). The manual dogfood session is the most important item — it catches emergent framework gaps that automated evals miss.

| # | Step | Required? |
|---|---|---|
| 1 | `bash .claude/tests/validate-template.sh` passes 13/13 | YES |
| 2 | `python3 .claude/scripts/validate_canvas.py` passes (CI-only, requires `pip install -r requirements-ci.txt`) | YES |
| 3 | `/eval-runner run-all` passes all scenarios (scenarios/discovery, delivery, integration, adversarial) | YES |
| 4 | Version bumped consistently in CLAUDE.md and README.md | YES |
| 5 | `/feedback-review` health check — no regressions across Loop 1-4 | YES |
| 6 | **Manual dogfood session**: run Mycelium end-to-end on a fictional product (different shape than previous sessions), file a dogfood report in `.claude/evals/dogfood-reports/YYYY-MM-DD-<project-name>.md` | YES |
| 7 | Update `CONTRIBUTORS.md` with any new feedback sources that shaped this version | If applicable |
| 8 | Clear `.claude/state/*.jsonl` audit logs before committing (they are gitignored, but check) | YES |

### Why the Manual Dogfood Session Matters

Automated evals test known failure modes. Manual dogfood sessions catch **unknown** failure modes — the emergent gaps that only surface when multiple skills, gates, and hooks interact in an unfamiliar product shape. The macos-fileviewer session (2026-04-09) that surfaced 12 framework gaps is the proof. Per LangChain's 2025 agent eval guidance: "dogfooding with rapid iteration" is one of three canonical eval sources alongside public benchmarks and hand-crafted tests.

**Pick a product shape that's different from the last session.** If macos-fileviewer was a native app, try a CLI tool next. Then a web service. Then a data pipeline. Rotation surfaces different framework gaps.

**Use the template at `.claude/evals/dogfood-reports/README.md`** for report structure. The goal is not to ship the product — the goal is to surface framework gaps and document them.

### Dogfood Session Budget

- **Time**: 3-5 hours of agent + research time, typically 10-15 turns
- **Output**: a dogfood report in `.claude/evals/dogfood-reports/`
- **Deliverable**: top 3-5 tightening recommendations, ranked by value/cost
- **Success criterion**: at least 3 specific, actionable framework improvements identified (even if small)

If a dogfood session surfaces zero gaps, that's a signal to make the session harder (pick a more unusual product shape, introduce more ambiguity, plant adversarial constraints).

## Diamond Lifecycle Management

### Diamond States
- **Active**: Currently being worked on
- **Blocked**: Waiting on something (evidence, dependency, decision)
- **Archived**: Completed or deliberately paused, canvas preserved
- **Killed**: Abandoned with documented reason

### Stale Diamond Detection
A diamond is stale if:
- No progress for 30+ days
- Phase hasn't changed in 2+ weeks without documented reason
- Blocking children that are themselves stale

### Cleanup Process
1. Run `/diamond-assess` to identify stale diamonds
2. For each stale diamond, decide: continue, archive, or kill
3. **Archive**: Move from `active_diamonds` to an `archived` section in `active.yml`. Canvas data preserved.
4. **Kill**: Remove from `active.yml`. Log reason in `decision-log.md`. Canvas data preserved with "killed" note.
5. Never delete canvas artifacts -- they're learning, even from killed work.

## Memory Maintenance

### Corrections Pruning (when > 30 entries)
1. **Graduate**: Corrections now embedded in code (e.g., null check was added) -- delete these
2. **Merge**: Similar corrections into single rule (e.g., 5 "missing null check" -> 1 rule)
3. **Archive**: Situational corrections older than 3 months that haven't recurred -- move to `## Archived` section

### Patterns Library
- After successful delivery: extract reusable patterns to `patterns.md`
- After retrospective: capture what worked
- Periodically review: are patterns still valid? Should any be promoted to guardrails?

### Decision Log
- Grows indefinitely (it's a historical record)
- Don't prune -- it's your product's decision history
- Use search/grep to find relevant past decisions

## Canvas Maintenance

### When to Prune Canvas Data
- **Opportunities**: Archive killed/invalidated branches in OST (don't delete -- they show what was explored)
- **Solutions**: Mark abandoned solutions with reason and date
- **GIST Ideas**: Kill ideas below confidence threshold after 2+ failed steps
- **Threat Model**: Re-assess when architecture changes significantly

### When to Refresh Canvas Data
- **Wardley Map**: When competitive landscape shifts, new tech emerges, or components evolve
- **North Star**: When strategy fundamentally changes (rare -- quarterly check)
- **Team Shape**: When team composition changes or cognitive load shifts
- **BVSSH**: Monthly check, or when something feels off

## Versioning

Mycelium itself has a version number in CLAUDE.md. When updating Mycelium in a project:
1. Compare your version against the upstream repo
2. Canvas files: additive only (new fields won't break old data)
3. Skills: can be replaced wholesale
4. Hooks: review diffs carefully (behavior changes)
5. Engine rules: review for breaking changes in gate definitions
