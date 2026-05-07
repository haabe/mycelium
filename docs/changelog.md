# Changelog

**Audience**: operators upgrading + practitioners tracking what changed.
**Time to read**: 5 min.
**Last updated**: 2026-05-08.

The live version is in [CLAUDE.md](../CLAUDE.md) first-line frontmatter — that is canonical. This page is the human-readable summary log.

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
