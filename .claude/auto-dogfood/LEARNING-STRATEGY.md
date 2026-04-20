# Dogfood Learning Strategy

How we use automated dogfood results to improve Mycelium.

## Baseline

First successful run: **2026-04-20** (exploration battery, 19 scenarios)
- Pass rate: 0/19 (0%)
- Average score: 38%
- Baseline file: `results/baseline-2026-04-20.json`

## Run Strategy: Trigger-Scoped, Manual

All runs are **manual** and **local** (CI blocked on API credits — Claude Max ≠ API).
The key insight: run what's relevant to what changed, not everything every time.

### Trigger → Scenario Map

| What Changed | Scenarios to Run | ~Time | Command |
|---|---|---|---|
| **Guardrails / anti-patterns** | `sw-web-team-skip-discovery`, `ai-agent-solo-confidence-inflate`, `sw-solo-hollow-bvssh` | ~15 min | `run sw-web-team-skip-discovery ai-agent-solo-confidence-inflate sw-solo-hollow-bvssh` |
| **Theory gates / confidence** | `ai-tool-solo-theory-gates`, `sw-solo-evidence-decay`, `sw-solo-shallow-cynefin` | ~15 min | `run ai-tool-solo-theory-gates sw-solo-evidence-decay sw-solo-shallow-cynefin` |
| **Diamond lifecycle / progression** | `sw-api-solo-happy-path`, `sw-solo-lifecycle-cycle-recording`, `sw-solo-perspective-conflict` | ~15 min | `run sw-api-solo-happy-path sw-solo-lifecycle-cycle-recording sw-solo-perspective-conflict` |
| **Canvas / BVSSH / delivery gates** | `sw-api-solo-deliver-complete`, `sw-solo-hollow-bvssh`, `course-solo-value-risk` | ~15 min | `run sw-api-solo-deliver-complete sw-solo-hollow-bvssh course-solo-value-risk` |
| **Product-type support** | `content-solo-l5-market`, `ai-tool-solo-value-risk`, `service-team-multiscale-l2-l4` | ~15 min | `run content-solo-l5-market ai-tool-solo-value-risk service-team-multiscale-l2-l4` |
| **Version release** | All 18 scenarios | ~60-90 min | `run-all` |

Shorthand `run` = `python3 .claude/auto-dogfood/orchestrator.py run .claude/auto-dogfood/scenarios/<name>.yml -o .claude/auto-dogfood/results -v`
Shorthand `run-all` = `python3 .claude/auto-dogfood/orchestrator.py run-all .claude/auto-dogfood/scenarios/ -o .claude/auto-dogfood/results -v`

### Why Manual, Not Scheduled

- **20 min per cluster is a real cost.** Running irrelevant scenarios wastes time with no learning.
- **LLM non-determinism** means occasional false negatives. A targeted re-run is cheaper than debugging a full-battery flake.
- **Model updates** (Anthropic ships new Sonnet) can shift behavior. Run the full battery after model changes — that's a real trigger.
- CI will be re-enabled when API credits are available.

## The Learning Loop

```
Change → Pick trigger cluster → Run → Review → Diagnose → Fix → Re-run → Compare
```

### Review (human + agent)
After each run, read the report. Focus on:
- **New failures** (criteria that passed before but now fail = regression)
- **Persistent failures** (same criteria failing across runs = systemic issue)
- **Proposals** (the orchestrator generates fix suggestions per scenario)

### Diagnose
For each failure pattern, classify:

| Pattern | Root Cause | Fix Target |
|---------|-----------|------------|
| Agent doesn't create diamond | Prompt too short / context overload | Scenario journey or runner timeout |
| Canvas not populated | Agent can't write to .claude/ paths | Symlink setup or permission bypass |
| Decision log empty | Agent skips logging | CLAUDE.md instructions or guardrail |
| Criteria never passes | Criteria too strict for headless mode | Evaluator threshold or criteria definition |
| Session too fast (<10s) | Agent erroring out early | Check stderr in observations |

### Fix
- **Framework issue** → fix in `.claude/` files, commit, PR triggers regression
- **Scenario issue** → fix scenario YAML (journey, persona, criteria)
- **Orchestrator issue** → fix in `auto-dogfood/` Python code
- **Criteria issue** → adjust evaluator thresholds

### Re-run and Compare
```bash
python3 .claude/auto-dogfood/orchestrator.py compare results/baseline-2026-04-20.json results/<new>.json
```

## Pass Rate Tracking

| Date | Scenarios | Passed | Score | Notes |
|------|-----------|--------|-------|-------|
| 2026-04-20 (CI) | 19 | 0 | 38% | First CI run. claude -p returned errors (25 chars each). Not valid results. |
| 2026-04-20 (local) | 1 | 1 | 100% | sw-solo-shallow-cynefin: 95s, 4633 tokens. Scenarios work locally. |
| 2026-04-20 (local) | 18 | 17 | 99.3% | Full battery pre-fix. 133/134 criteria. 1 failure: `decision_log_honest` on L5 content (sycophancy). 3 retries for missing decision-log. |
| 2026-04-21 (local) | 3+1 | 4 | 100% | Verification post-fix: L5 content 8/8, SaaS L1 no retry, coding quality 10/10. Service L2-L4 still retries (dora-check timeout — see known issues). |
| 2026-04-12 (local) | 1 | 1 | 100% | sw-lib-solo-coding-quality: 315-785s range across 4 runs. |

## Known Issues

### Open

5. **`/dora-check` timeout in service-multiscale scenario**: The agent hits the 180s timeout before writing the decision log. Happens consistently in `service-team-multiscale-l2-l4` after `/delivery-bootstrap` — the canvas is too large for a single `claude -p` call to assess + log. Retry recovers it, but wastes ~3 min. Options: bump to 300s, or have `/delivery-bootstrap` write the log entry so `/dora-check` has less work.

6. **Scenarios only test cold-start**: All 19 scenarios begin with an empty canvas. Real usage operates on populated canvases with history and contradictions. No scenario tests mid-project complexity.

7. **No onboarding scenario**: The most important user flow (clone → `/interview` → first value) has zero coverage.

8. **No flake rate data**: Each scenario was run once. Apr 12 data showed 315-785s variance across 4 identical runs. Need repeat runs (3x minimum) to measure non-determinism.

9. **Scenarios stop early — possibly too easy**: All 19 scenarios used 2-5 of their 12-22 round budgets. Criteria may be too loose, or early-stop triggers too eagerly.

### Resolved

1. ~~**CI blocked: Claude Max ≠ API credits**~~: Root cause confirmed. Health-check and error detection added. Cron disabled. **Parked until API credits provisioned.**

2. ~~**Token tracking broken in CI**~~: Downstream of #1. Local runs report tokens correctly.

3. ~~**Runner didn't detect errors**~~: Fixed — `is_error` detection + `[CLAUDE_ERROR]` prefix + abort after 2 consecutive errors.

4. ~~**No prior local run data used to calibrate CI**~~: Documented in corrections.md. Local timing data now tracked in pass rate table.

F1. ~~**L5 sycophantic decision log**~~: Fixed — guardrail G-M1 added, verified passing.

F2. ~~**27/44 skills missing decision log instruction**~~: Fixed — G-P4 strengthened, 10 skills patched, evaluator `require_after` expanded. 2/3 retry scenarios eliminated; #5 above is the remaining edge case.

## Cost Management

Runs are local via Claude Max subscription (no per-token API cost). The real cost is **time**:
- Per scenario: ~2-13 minutes (observed range from local runs)
- Trigger cluster (3 scenarios): ~5-15 minutes
- Full battery (18 scenarios): ~60-90 minutes

This is why trigger-scoped runs matter — running 3 relevant scenarios instead of 18 saves ~45-75 minutes.

## What NOT to Optimize For

- **100% pass rate** — some scenarios are designed to test failure detection. A scenario "passing" means the framework caught the planted failure, not that the simulated project succeeded.
- **Speed** — faster isn't better. Longer sessions with more rounds means the agent is doing more work.
- **Raw score** — a scenario scoring 33% might be doing the right thing if it's correctly blocking a bad progression (3 of 9 criteria passed, including the critical one).
