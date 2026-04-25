# Canvas — Product Source of Truth

The canvas is where all product knowledge lives. Every file here is a structured YAML document that captures what the team knows about the product — from its purpose to its threat model to its DORA metrics.

Canvas files are:
- **The single source of truth** — no knowledge lives only in someone's head or a chat log
- **Committed to git** — version-controlled, diffable, reviewable
- **Updated through evidence** — not assumptions, not opinions, not gut feelings
- **Readable by humans and agents** — any new team member (or a fresh Claude session) can read these files and understand the product's state

## Files by Scale

### L0: Purpose
| File | What It Captures | Theory |
|------|-----------------|--------|
| [purpose.yml](purpose.yml) | Why we exist, how we're different, what we do | Sinek (Golden Circle) |
| [jobs-to-be-done.yml](jobs-to-be-done.yml) | What users are trying to accomplish | Christensen (JTBD) |

### L1: Strategy
| File | What It Captures | Theory |
|------|-----------------|--------|
| [landscape.yml](landscape.yml) | Competitive landscape, evolution, gameplay | Wardley Mapping |
| [north-star.yml](north-star.yml) | North Star metric and input metrics | Cutler/Amplitude |
| [team-shape.yml](team-shape.yml) | Team topology and interaction modes | Skelton & Pais |

### L2: Opportunity
| File | What It Captures | Theory |
|------|-----------------|--------|
| [opportunities.yml](opportunities.yml) | Opportunity Solution Tree — problems, solutions, experiments | Torres (CDH) |
| [user-needs.yml](user-needs.yml) | User needs mapped and prioritized | Allen (User Needs Mapping) |
| [scenarios.yml](scenarios.yml) | Future scenarios for strategic planning | Hoskins |

### L3: Solution
| File | What It Captures | Theory |
|------|-----------------|--------|
| [gist.yml](gist.yml) | Goals, Ideas, Steps, Tasks | Gilad (GIST) |
| [services.yml](services.yml) | Service design quality (15 principles) | Downe (Good Services) |
| [bounded-contexts.yml](bounded-contexts.yml) | Domain boundaries and integration points | Evans (DDD) |

### L4: Delivery
| File | What It Captures | Theory |
|------|-----------------|--------|
| [dora-metrics.yml](dora-metrics.yml) | Deployment frequency, lead time, change failure rate, MTTR | Forsgren (DORA) |
| [threat-model.yml](threat-model.yml) | Security threats, mitigations, STRIDE analysis | OWASP/STRIDE |
| [privacy-assessment.yml](privacy-assessment.yml) | Privacy principles and data handling assessment | GDPR/PbD |
| [value-stream.yml](value-stream.yml) | Value stream mapping — where time is spent and wasted | Goldratt (ToC) |

### L5: Market
| File | What It Captures | Theory |
|------|-----------------|--------|
| [go-to-market.yml](go-to-market.yml) | Positioning, channels, launch strategy | Lauchengco (Loved) |
| [trust-signals.yml](trust-signals.yml) | What builds user trust | Shotton (behavioral science) |

### Cross-Cutting
| File | What It Captures |
|------|-----------------|
| [bvssh-health.yml](bvssh-health.yml) | Better/Value/Sooner/Safer/Happier health checks (Smart) |
| [cycle-history.yml](cycle-history.yml) | Completed leaf lifecycle outcomes for calibration |
| [thresholds.yml](thresholds.yml) | Adaptive thresholds calibrated from historical data |
| [human-tasks.yml](human-tasks.yml) | Offline tasks for human execution (interviews, observations) |
| [archived-solutions.yml](archived-solutions.yml) | Discarded solution leaves with reasons |

### Product-Type Specific Metrics
| File | Product Type |
|------|-------------|
| [content-metrics.yml](content-metrics.yml) | Courses, publications, media |
| [ai-tool-metrics.yml](ai-tool-metrics.yml) | AI tools and prompt-based products |
| [service-metrics.yml](service-metrics.yml) | Service offerings and consulting |

## How Canvas Gets Updated

Canvas files are never updated by assumption. The flow is:

1. A skill gathers evidence (interview, metrics pull, assumption test)
2. Evidence is logged with `source_class` (desk_research, external_data, external_human)
3. The relevant canvas file is updated with the new evidence
4. Confidence scores adjust based on evidence quality and quantity
5. All changes are committed to git

Run `/canvas-health` to check for missing fields, stale confidence, or inconsistent evidence.

## Schema and Validation

Canvas file schemas are defined in [`../schemas/canvas/`](../schemas/canvas/). The validation script at [`../scripts/validate_canvas.py`](../scripts/validate_canvas.py) checks structural integrity. CI runs this automatically.

Each canvas file includes a `_meta` block for versioning and staleness detection:

```yaml
_meta:
  version: 2
  last_validated: "2026-04-14"
  evidence_type: interview
  structural_level: schema
```
