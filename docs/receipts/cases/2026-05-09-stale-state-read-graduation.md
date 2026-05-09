---
id: 2026-05-09-stale-state-read-graduation
date: 2026-05-09
contributor: Håvard Bartnes (founder dogfood)
contributor_link: CONTRIBUTORS.md
project: mycelium-self-discipline
mechanism_or_status: graduated
commits: ["TBD"]
subclass: anti-pattern-graduation
---

# stale-state-read-graduation — four instances of mechanisms reading the wrong state

**Audience**: contributors interested in tooling-discipline patterns; evaluators wanting to see how Mycelium catches its own validators failing silently.
**Time to read**: 4 min.
**Last updated**: 2026-05-09.

## The recurring failure

Four times in two weeks, a script or validator produced nominally-correct output by reading state from a stale source — typically the local copy of a file the operation was about to replace, or a hardcoded local path that bypassed the explicit-source override the framework had built specifically for this case.

| Date | Surface | What happened |
|---|---|---|
| 2026-04-28 | `upgrade.sh` harness sync | Hardcoded list of `harness/*.md` files; new harness file added upstream wasn't pulled. |
| 2026-05-03 | `upgrade.sh` top_level | Same hardcoded-list pattern applied to `top_level`; AGENTS.md was added to manifest but the script's hardcoded list missed it. 2nd instance, same pattern, partial fix from 2026-04-28 didn't generalize. |
| 2026-05-04 | `validate_canvas.py` | Validator passed despite duplicate IDs within a canvas file. Validator was scanning shape correctly but didn't enforce ID-uniqueness — same shape: nominally-correct mechanism reads incomplete signal and silently passes. |
| 2026-05-04 | `upgrade.sh` manifest sync | Script ran `parse_manifest.py directories` against the LOCAL manifest BEFORE replacing it with upstream. New `docs/` entry only took effect on the 2nd run. Closed at the structural layer with `parse_manifest.py --manifest=<path>` override. |

## Why four instances forced graduation

`corrections.md` TL;DR has been carrying this as a graduation candidate since instance 4: *"4 instances of this pattern (upgrade.sh hardcoded list ×2 + validate_canvas.py ID-uniqueness + upgrade.sh manifest stale-read) — graduation candidate to a higher-tier guardrail beyond G-V12 if a 5th surfaces."* Waiting for a 5th instance is itself the failure mode the framework's own rule warns against (*"Don't wait for incident #3"*, line 11). The graduation closes the backlog.

## What graduated

**Anti-pattern #8 in `harness/anti-patterns.md`** — *Stale State Read*. Description: scripts/validators reading state from a file the same operation is about to replace, or hardcoded local-path defaults without explicit-source override. Detection rule: `Path(__file__).resolve().parent.* / "state.yml"` patterns without a corresponding `--source=<path>` argv override; or sync flows that read pre-replacement state. Worked example: `parse_manifest.py --manifest=<path>` (the override that closed the 4th instance).

**`/corrections-audit` Step 6e** — ongoing detection. Track instance count; the 5th forces enforcement-layer graduation (validator scan via Check 29).

**`tests/validate-template.sh` Check 29** — heuristic scan. Finds Python scripts in `plugins/mycelium/scripts/` that read state files via `Path(__file__)` AND don't accept argv override (no `argparse`, `sys.argv`, `--manifest`, `--source`, or `--config`). Surfaces candidates at WARN level — manual review confirms whether the script actually needs the override (some scripts read truly-static config that's never replaced mid-run).

## Theory grounding

- **Ohno** (jidoka — build the test that catches the failure, don't rely on memory): the recurring instance count is exactly the signal that "remember to use the override" is not a sustainable discipline. The graduation moves the rule into mechanical detection.
- **Argyris** (double-loop): instance 1 fixed harness/ via globs; instance 2 should have generalized to all hardcoded lists. Symptom-fix at the time was single-loop; the graduation is the deferred double-loop close.
- **Mycelium's G-V12**: every check ships coverage proof. Check 29's heuristic is the coverage proof — flags the pattern; the four corrections.md instances are the test fixtures it would have caught.

## Mechanism + status

**Status**: graduated (2026-05-09). Three integration points:
- Anti-pattern #8 in `harness/anti-patterns.md`
- `/corrections-audit` Step 6e for ongoing pattern detection
- Validator Check 29 for codebase scanning

**Watch-list**: Check 29 currently fires at WARN, not FAIL — heuristic, false-positive risk on truly-static config readers. Promote to FAIL after one full release cycle of clean scans + manual confirmation that the heuristic isn't over-flagging.

## Cross-references

- Sibling graduation: [consistency-as-evidence-graduation](2026-05-09-consistency-as-evidence-graduation.md) — anti-pattern #7 in the same release (related epistemic-attribution failure mode, applied to discovery/analysis rather than tooling)
- Sibling graduation: [bias-cluster-graduation](2026-05-09-bias-cluster-graduation.md) — `/devils-advocate` Techniques 4 and 5
- Source corrections: `corrections.md` 2026-04-28 (upgrade.sh harness hardcoded), 2026-05-03 (upgrade.sh top_level missed AGENTS.md), 2026-05-04 (validate_canvas.py ID-uniqueness), 2026-05-04 (upgrade.sh manifest stale-read)
- Worked example of the prevention: `parse_manifest.py --manifest=<path>` (closed instance 4 structurally)
