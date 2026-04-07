---
name: dora-check
description: "Use to assess DORA metrics (deployment frequency, lead time, change failure rate, MTTR) and identify improvement areas."
---

# DORA Check Skill

Assess the four key DORA metrics.

## Workflow

1. **Gather current metrics** (from CI/CD, deployment logs, incident records):

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

2. **Classify performance level** for each metric.

3. **Identify constraints**: What is blocking improvement on the lowest-performing metric?

4. **Recommend improvements** prioritized by impact.

5. **Output**:
   ```
   ## DORA Assessment
   | Metric | Current | Level | Target | Gap |
   |--------|---------|-------|--------|-----|
   | Deploy freq | ... | ... | ... | ... |
   | Lead time | ... | ... | ... | ... |
   | Change fail rate | ... | ... | ... | ... |
   | MTTR | ... | ... | ... | ... |

   Bottleneck: [the metric most constraining overall performance]
   Top 3 improvements:
   1. [specific action]
   2. [specific action]
   3. [specific action]
   ```

## Theory Citations
- Forsgren, Humble, Kim: Accelerate (DORA metrics)
- Smart: Sooner Safer Happier (flow optimization)
