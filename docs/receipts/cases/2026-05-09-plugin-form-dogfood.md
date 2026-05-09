---
id: 2026-05-09-plugin-form-dogfood
date: 2026-05-09
contributor: Håvard Bartnes (founder self-dogfood)
contributor_link: CONTRIBUTORS.md
project: mycelium-plugin-test
mechanism_or_status: bugs-closed-in-session
commits: ["5f1b416", "97f295f"]
subclass: self-dogfood
---

# plugin-form-dogfood — Mycelium evaluated against itself

**Audience**: evaluators wanting evidence that Mycelium catches its own friction; contributors interested in what a self-dogfood session looks like.
**Time to read**: 4 min.
**Last updated**: 2026-05-09.

## The session

On 2026-05-09, the day after the plugin-form pivot bootstrap (see [bentes-install-model](2026-05-08-bentes-install-model.md)), the founder ran Mycelium end-to-end on Mycelium itself. The setup: a fresh `mycelium-plugin-test` directory, the plugin installed via local-path marketplace from the `feat/plugin-form` branch, then `/mycelium:start` invoked cold.

Why dogfood the framework on the framework? Cycle learning needs unfamiliar friction. Subagent simulations had been validating plugin shape at the syntactic level (paths resolve, references exist, skills present) but couldn't surface emergent friction — what the agent actually does when an undefined edge case appears. A real session was the only instrument that would.

## What surfaced — wins

The cognitive forcing function fired exactly where it was supposed to. When `/mycelium:diamond-assess` was invoked on an empty smoke-test project, the agent refused to mechanically render a journey map. It surfaced ambiguity instead — "are you validating plugin shape, bootstrapping a real diamond, or testing the empty-state output?" — and waited for the human to steer (Buçinca, Malaya & Gajos 2021, Cognitive Forcing Functions).

The universal-flow brief produced substantive output. Run on Mycelium-as-product, the 4-question brief captured the **load-bearing adoption assumption**:

> "The harness is light enough that people keep choosing it past the first friction moment."

Cagan four-risks classification by the agent: **usability** — not value, viability, or feasibility. That validates the on-ramp / install-friction / namespace-prefix / setup-welcome work as correctly prioritized.

`/mycelium:assumption-test` then produced an operational research design, not theory: n=5 (2 warm-but-naive, 2 cold, 1 skeptic), 30-minute talk-aloud, pre-committed Persevere / Ambiguous / Pivot / Kill thresholds, recruitment template, Rother-style pre-commit prediction, bias flags. The framework gave the founder the test instrument the founder had been trying to design externally for two weeks.

The framework also caught its own self-coherence trap. The assumption-test design ends with: *"do not run `/mycelium:bias-check` on this test design. Have a human review it."* Mycelium evaluating Mycelium is bias-loaded; the framework noticed and recused itself from a step that would otherwise compound the bias. That's the kind of self-aware behavior that's hard to fake and impossible to write into a test scenario in advance.

## What surfaced — bugs (5, all closed same-day)

| ID | Severity | Bug | Fix |
|---|---|---|---|
| B4 | Real-user-impact | `setup` starter `${CLAUDE_PLUGIN_ROOT}` got expanded by agent at Write time, baking maintainer's absolute path into every user's `warnings-log.md` | Switch starter content to prose; explicit "do NOT expand" instruction at Write boundary |
| B1 | UX | `/mycelium:start` Step 2 detection honored *after* `mkdir -p` ran; existing-state projects got Read-before-Write tool errors before recovering | Promote detection to a HARD GATE; first action after welcome, no preparatory Bash before it fires |
| B2 | Discipline | `plugin.json` pinned at v0.20.0 across 10 patches; ping marker drifted similarly | Bump `plugin.json` to track CLAUDE.md; make ping marker shape-stable (`MYCELIUM_PLUGIN_LOAD_OK`, no version suffix) |
| B3 | Mechanism gap | Validator Check 26 didn't watch `plugin.json` or marketplace.json — that's what let B2 through 10 patches | Added the manifest files to `material_paths` |
| B5 | Cosmetic | Setup didn't acknowledge `.claude/state/` (Claude Code's runtime state, not Mycelium's); agent flagged as anomaly | One-line note in setup Step 2 |

All five closed in commit `5f1b416` before the merge to main.

## What this case taught the framework

| Lesson | Where it lives |
|---|---|
| Subagent simulation ≠ lived friction. Paper-validates syntax; misses agent-execution-order bugs. Real sessions needed before merging architectural changes. | This case + future merge-to-main checklists |
| Detection-then-route logic must be a hard gate, not a soft preference. Agents will run preparatory operations first if not explicitly forbidden. | start/SKILL.md Step 2 |
| Variable expansion at Write boundaries is an environment leak. Documentation files containing `${VAR}` syntax must be authored as prose or explicitly flagged "literal." | setup/SKILL.md warnings-log.md starter |
| Validator's `material_paths` must include manifest files (`plugin.json`, `marketplace.json`) — not just the directories they describe. | validate-template.sh Check 26 |
| Self-dogfood produces research artifacts the framework can use. The L0 adoption test design was *output*, not setup. | mycelium-plugin-test/.claude/evals/assumption-tests/ |

## Mechanism + status

**Status**: bugs-closed-in-session. All five surfaced bugs closed before the merge to main on the same day. Plugin form 0.20.x landed canonical on main 2026-05-09 (commit `97f295f`).

**Commits cited**:
- `5f1b416` — close 5 bugs from 2026-05-09 dogfood; unblock merge
- `97f295f` — Merge feat/plugin-form: Mycelium 0.20.x canonical plugin-form release

## Cross-references

- Architectural finding that drove the plugin-form pivot: [bentes-install-model](2026-05-08-bentes-install-model.md)
- L0 adoption test design (output of this dogfood, ready to recruit against): `mycelium-plugin-test/.claude/evals/assumption-tests/L0-adoption-test.md` (private repo)
- Welcome message validated: `plugins/mycelium/skills/start/SKILL.md` Step 1 (founder quote: "really lowers the cognitive scare")
- Cognitive forcing function source: Buçinca, Malaya & Gajos (Harvard CHI/CSCW 2021)
