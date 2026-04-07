---
name: canvas-update
description: "Update canvas sections with new evidence. Ensures canvas stays current as the single source of truth."
---

# Canvas Update

## Rules
1. **Never update without evidence** -- every canvas change must have a source
2. **Maintain cross-file consistency** -- if you update opportunities.yml, check if north-star.yml or gist.yml need updates too
3. **Log the update** -- add an entry to decision-log.md explaining what changed and why

## Which Canvas File for Which Information

| Information Type | Canvas File | Source |
|-----------------|-------------|--------|
| Purpose, mission, why | purpose.yml | Sinek |
| North Star metric, inputs | north-star.yml | North Star Framework |
| BVSSH health scores | bvssh-health.yml | Smart |
| Value chain, competitive | landscape.yml | Wardley |
| Team structure | team-shape.yml | Skelton |
| User opportunities, OST | opportunities.yml | Torres |
| User needs map | user-needs.yml | Allen |
| Goals, ideas, steps | gist.yml | Gilad |
| Service quality scores | services.yml | Downe |
| Go-to-market, positioning | go-to-market.yml | Lauchengco |
| Delivery performance | dora-metrics.yml | Forsgren |
| Security threats | threat-model.yml | OWASP |
| Privacy assessment | privacy-assessment.yml | GDPR/PbD |
| Trust architecture | trust-signals.yml | Digital Trust |
| Jobs to be done | jobs-to-be-done.yml | Christensen |

## Workflow
1. Identify which canvas file(s) need updating
2. Read current state
3. Make the update with evidence citation
4. Check cross-file consistency
5. Log in decision-log.md
