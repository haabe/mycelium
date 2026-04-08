---
name: dora-check
description: "Assess DORA metrics and APEX AI-era delivery metrics. Measures deployment frequency, lead time, change failure rate, MTTR, plus AI leverage, predictability, efficiency, and developer experience."
---

# DORA + APEX Check

Assess delivery health using Forsgren's four DORA metrics AND LinearB's APEX AI-era metrics.

## Part 1: DORA Metrics (Forsgren)

Gather current metrics from CI/CD, deployment logs, incident records:

**Deployment Frequency**: How often does code reach production?
- Elite: On-demand (multiple deploys/day)
- High: Between once/day and once/week
- Medium: Between once/week and once/month
- Low: Less than once/month

**Lead Time for Changes**: Commit to production time?
- Elite: Less than one hour
- High: Between one day and one week
- Medium: Between one week and one month
- Low: More than one month

**Change Failure Rate**: % of deployments causing failure?
- Elite: 0-15%
- High: 16-30%
- Medium: 31-45%
- Low: 46-100%

**Mean Time to Recovery**: Time to restore service after failure?
- Elite: Less than one hour
- High: Less than one day
- Medium: Between one day and one week
- Low: More than one week

## Part 2: APEX Metrics (LinearB)

**"Faster coding doesn't mean faster delivery."**

Assess the four APEX pillars to detect AI-era delivery problems:

### A — AI Leverage
- What % of PRs/code changes are AI-generated or AI-assisted?
- What is the AI suggestion acceptance rate? (Benchmark: 32.7% for AI vs 84.4% for human — LinearB 2026)
- What is the AI rework rate? (% of AI code rewritten within 21 days)
- Is AI code quality comparable to human code? (Check corrections.md origin field)

### P — Predictability
- Planning accuracy: % of planned work completed per cycle?
- Rework rate: % of ALL code rewritten within 21 days?
- Are delivery estimates getting more or less reliable with AI?

### E — Efficiency (The Shifting Bottleneck)
- End-to-end cycle time: is it actually decreasing?
- Review wait time: are PRs waiting longer before first review?
- AI review wait ratio: do AI PRs wait longer than human PRs? (Benchmark: 4.6x — LinearB 2026)
- **KEY CHECK**: Is coding faster but review/testing/deployment slower? If yes, the bottleneck has shifted. AI is generating code the pipeline can't absorb.

### X — Developer Experience
- Developer satisfaction with AI tools (survey or conversation)
- Cognitive load: is AI helping or adding complexity?
- Burnout signals: unsustainable pace? Context-switching? Alert fatigue?
- Maps to BVSSH "Happier" dimension

## Output

```
## DORA + APEX Assessment

### DORA Metrics
| Metric | Current | Level | Target | Gap |
|--------|---------|-------|--------|-----|
| Deploy freq | ... | ... | ... | ... |
| Lead time | ... | ... | ... | ... |
| Change fail rate | ... | ... | ... | ... |
| MTTR | ... | ... | ... | ... |

### APEX Metrics (AI-Era)
| Pillar | Status | Key Signal |
|--------|--------|-----------|
| AI Leverage | ... | AI acceptance rate: ...% |
| Predictability | ... | Planning accuracy: ...%, Rework rate: ...% |
| Efficiency | ... | Cycle time: ..., Review wait: ... |
| Developer Experience | ... | Satisfaction: ..., Burnout: ... |

### Shifting Bottleneck Check
[Is coding faster but review/deployment slower? Yes/No]
[If yes: where is the new bottleneck?]

### DORA Bottleneck
[The metric most constraining overall performance]

### Top 3 Improvements
1. [specific action]
2. [specific action]
3. [specific action]
```

## Canvas Output
**Always update** `canvas/dora-metrics.yml` with:
- DORA metrics, classifications, and capability scores
- APEX section: ai_leverage, predictability, efficiency, developer_experience
- Measurement history for trend tracking

## Theory Citations
- Forsgren, Humble, Kim: Accelerate (DORA metrics)
- LinearB: APEX Framework (AI-era delivery measurement)
- Smart: BVSSH (holistic flow optimization — APEX X maps to Happier)
- Kim: Three Ways (Second Way — amplify feedback loops, detect shifting bottlenecks)
