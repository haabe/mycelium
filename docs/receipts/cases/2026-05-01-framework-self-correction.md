---
id: 2026-05-01-framework-self-correction
date: 2026-05-01
contributor: internal-dogfood
contributor_link: null
project: framework-development
mechanism_or_status: multiple-graduated
commits: ["91186b8", "200b4d6", "c25aaff", "d6c4e9d"]
subclass: documented-rule-diverges-from-enforcement
---

# framework-self-correction (May 1 → May 4) — what the framework caught itself doing

**Audience**: practitioners and researchers interested in what self-correcting harness behavior looks like when the inputs are the framework's own friction log, not a new project.
**Time to read**: 5 min.
**Last updated**: 2026-05-08.

## The cycle

A four-day cycle where Mycelium's own harness flagged recurring patterns in its own work and graduated them into mechanism. No outside user, no new project — the inputs were the framework's own corrections log, validator output, and one user remark on May 4 ("the self-learning mechanisms should automatically log both errors and warnings").

Commits: [`91186b8`](https://github.com/haabe/mycelium/commit/91186b8), [`200b4d6`](https://github.com/haabe/mycelium/commit/200b4d6), [`c25aaff`](https://github.com/haabe/mycelium/commit/c25aaff), [`d6c4e9d`](https://github.com/haabe/mycelium/commit/d6c4e9d).

## What the framework caught

| What the framework caught | What now exists in Mycelium |
|---|---|
| Validators shipping without tests proving they catch what they claim to catch | Guardrail **G-V12**: every check ships with a coverage-proof test on a known-bad case |
| Pre-ship gap/misalignment/dead-end analysis silently skipped despite repeated user instruction | Guardrail **G-P-pre**: Mandatory Pre-Ship Protocol — visible bulleted gap analysis on substantive work, not "I checked everything" |
| AI-component products had no explainability surface or recourse path | `/xai-check` skill + theory Gate 13 + `ai-system-card.md` template (EU AI Act Art. 13/50 alignment) |
| Documented version-bump rule kept diverging from what actually shipped (5th instance of "documented rule diverges from enforcement") | **Check 26**: validator detects material framework changes since the last version bump and FAILs the harness |
| CI warnings (validator + upgrade output) had no path back into the learning loop | `ingest_warnings.py` + `warning-handbook.md` + `warnings-log.md` — same machinery as `corrections.md`, now feeding `/corrections-audit` |

## The cluster behind it

Check 26 was the 5th instance of the "documented-rule-diverges-from-enforcement" cluster. The cluster continued: a 6th instance (singular `source_class` schema gap, 2026-05-06), 7th (wayfinding doc descriptive vs prescriptive, 2026-05-06), 8th (JTBD schema lacks per-dimension backing, 2026-05-07). On 2026-05-08 the cluster graduated to a spec — `engine/consistency-check-spec.md` — with a mechanical promotion bar (≥3 detection rules from the spec, <5% FP, 100% TP on the cluster fixtures). See [.claude/memory/cluster-instances.md](../../../.claude/memory/cluster-instances.md) for the canonical instance log.

## Why it stays on the receipts list

It's the demonstration that the framework gets smarter without an external user — the inputs are its own friction. The cluster spec graduation (0.17.0) is the most explicit form of that: "graduate at instance 6" was a stated rule the framework wasn't mechanically enforcing; the recursive bug closed when the cluster log became canonical and the audit skills started reading it.

This case will rotate as the cluster matures past spec → mechanism. The rotation candidate is the next case where the framework graduates a *new* cluster from its own friction.
