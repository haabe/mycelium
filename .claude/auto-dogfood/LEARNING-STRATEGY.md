# Dogfood Learning Strategy

How we use automated dogfood results to improve Mycelium.

## Baseline

First successful run: **2026-04-20** (exploration battery, 19 scenarios)
- Pass rate: 0/19 (0%)
- Average score: 38%
- Baseline file: `results/baseline-2026-04-20.json`

## The Learning Loop

```
Run → Review → Diagnose → Fix → Re-run → Compare
```

### 1. Run (automated)
- **Weekly**: Exploration battery runs Monday 6am UTC via cron
- **On PR**: Regression suite (4 core scenarios) on any `.claude/` change
- **Manual**: `gh workflow run dogfood.yml -f mode=exploration`

### 2. Review (human + agent)
After each run, download results and review:
```bash
gh run download <run-id> --dir .claude/auto-dogfood/results/<date>
```
Read the report. Focus on:
- **New failures** (criteria that passed before but now fail = regression)
- **Persistent failures** (same criteria failing across runs = systemic issue)
- **Proposals** (the orchestrator generates fix suggestions per scenario)

### 3. Diagnose
For each failure pattern, classify:

| Pattern | Root Cause | Fix Target |
|---------|-----------|------------|
| Agent doesn't create diamond | Prompt too short / context overload | Scenario journey or runner timeout |
| Canvas not populated | Agent can't write to .claude/ paths | Symlink setup or permission bypass |
| Decision log empty | Agent skips logging | CLAUDE.md instructions or guardrail |
| Criteria never passes | Criteria too strict for headless mode | Evaluator threshold or criteria definition |
| Session too fast (<10s) | Agent erroring out early | Check stderr in observations |

### 4. Fix
- **Framework issue** → fix in `.claude/` files, commit, PR triggers regression
- **Scenario issue** → fix scenario YAML (journey, persona, criteria)
- **Orchestrator issue** → fix in `auto-dogfood/` Python code
- **Criteria issue** → adjust evaluator thresholds

### 5. Re-run and Compare
```bash
python .claude/auto-dogfood/orchestrator.py compare results/baseline-2026-04-20.json results/<new>.json
```

## Pass Rate Tracking

| Date | Scenarios | Passed | Score | Notes |
|------|-----------|--------|-------|-------|
| 2026-04-20 (CI) | 19 | 0 | 38% | First CI run. claude -p returned errors (25 chars each). Not valid results. |
| 2026-04-20 (local) | 1 | 1 | 100% | sw-solo-shallow-cynefin: 95s, 4633 tokens. Scenarios work locally. |
| 2026-04-12 (local) | 1 | 1 | 100% | sw-lib-solo-coding-quality: 315-785s range across 4 runs. |

## Known Issues (from baseline)

1. **CI sessions return errors, not real output**: Every `claude -p` call in CI returned exactly 25 chars in ~1 second — a fixed error response, not real agent output. Local runs of the same scenarios take 40-95 seconds and score 100%. Root cause: likely `claude -p` auth or environment issue in GitHub Actions. A health-check step and error detection have been added to diagnose. **This is the blocking issue — all other CI failures are downstream of this.**

2. **Token tracking broken in CI**: All scenarios report 0 tokens because the agent never ran successfully. Local runs do report tokens correctly (e.g., 4633 tokens for cynefin scenario).

3. **Runner didn't detect errors**: `runner.py` parsed JSON output but never checked `is_error` flag. Fixed: now prefixes error responses with `[CLAUDE_ERROR]` and orchestrator aborts after 2 consecutive errors.

4. **No prior local run data was used to calibrate CI**: Local runs from April 11-12 showed 315-785 seconds per scenario. CI timeouts (90-600s) were adequate but never compared against actual timings. The 4-18s CI times should have been an obvious red flag.

## Cost Management

Each exploration run = 19 scenarios × `claude -p` with Sonnet. At current pricing:
- Estimated: ~$1-5 per full exploration run (short sessions)
- If sessions get longer (the goal): ~$10-30 per run
- Weekly budget: monitor and adjust. Consider reducing to biweekly if costs climb.

Token tracking (issue #2) must be fixed before cost can be measured accurately.

## What NOT to Optimize For

- **100% pass rate** — some scenarios are designed to test failure detection. A scenario "passing" means the framework caught the planted failure, not that the simulated project succeeded.
- **Speed** — faster isn't better. Longer sessions with more rounds means the agent is doing more work.
- **Raw score** — a scenario scoring 33% might be doing the right thing if it's correctly blocking a bad progression (3 of 9 criteria passed, including the critical one).
