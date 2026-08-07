# Check architecture: inventory, classification, and a refactor plan

**Audience**: framework maintainer deciding whether to spend a cycle on this.
**Time to read**: 12 min.
**Last updated**: 2026-08-08.
**Status**: DRAFT PLAN. Nothing here has been built. Written because the founder asked whether 23
checks that each follow best practice individually form a good system collectively. They do not.

---

## 0. The question, and the honest answer

> *"with the total of checks, evals, and tests, I am really worrying that there are many
> overlapping solutions that per unit might follow best practices but not as a whole where much
> might be centralized or coordinated using abstractions."*

Measured, the concern is correct and understates the cost. The sharpest number is not duplication:

**`session-start.sh` takes 4.08s and spawns 33 `python3` processes, against a 5-second hook
timeout. That is 82% of the budget consumed.**

Measured three times (4.08 / 4.05 / 4.08) on the dogfood canvas: 130 YAML files, 2.8 MB. A larger
consumer canvas, a cold filesystem cache, or a slower machine crosses the timeout — and when a
SessionStart hook times out, **the entire orientation silently vanishes**. No canvas state, no open
loops, no reply-owed, no advisories. The failure mode is indistinguishable from "nothing to report",
which is the exact false-green class this framework audits others for.

That risk is architectural, not incidental. It is the sum of 33 interpreter startups.

---

## 1. Inventory

### 1.1 Surface

| Area | Files | Lines |
|---|---:|---:|
| `scripts/` | 85 | 11,223 |
| `skills/` | 61 | 9,762 |
| `hooks/` | 23 | 3,194 |
| `engine/` | 28 | 3,975 |
| `harness/` | 17 | 2,407 |
| `jit-tooling/` | 13 | 1,383 |
| `integrations/` | 7 | 349 |
| `domains/` | 4 | 845 |

### 1.2 Scripts by kind

| Kind | Count |
|---|---:|
| `check_*.py` | 23 |
| `*_guard.py` | 4 |
| `_*lib.py` (shared) | 3 |
| other `.py` | 11 |
| `.sh` | 2 |

**23 checks totalling 6,286 LOC.**

### 1.3 The shared layer exists and is barely used

| Library | Imported by |
|---|---|
| `_manifest_lib.py` | `check_wiring`, `check_test_authenticity`, `framework_guard`, `parse_manifest` |
| `_scan_lib.py` | `check_test_authenticity`, `check_wiring_contract` |
| `_text_lib.py` | `_scan_lib`, `check_wiring_contract`, `check_wiring` |

**5 of 23 checks import anything shared. The other 18 share nothing.**

This is the finding that matters most for the founder's question: the answer is not "we need
abstractions." Abstractions exist. They were built for the three wiring/manifest checks and never
generalised, so every check written since has started from a blank file.

---

## 2. Classification of the architectural concerns

Seven concerns, each currently smeared across all 23 checks rather than owned by one place.

### C1 — CLI contract (DRY violation, 22 instances)

22 of 23 checks hand-roll `argparse`. The flags have drifted:

- `--project-dir` vs `--root` — some accept one, some the other, some both
- `--json` — 26 occurrences, but the payload shape is per-script
- `--quiet-when-clean` — present in some, absent in others

Consequence: every caller (hook, skill, CI) must remember each script's dialect. `session-start.sh`
does exactly that, in 9 bespoke invocations.

### C2 — Failure semantics (consistency violation, the serious one)

**Empty-input honesty exists in 3 of 23 checks.** `PRECONDITION NOT MET` — the rule that a check
which looked at nothing must refuse rather than report green — is implemented in
`check_stale_prose`, `check_source_authenticity`, `check_evidence_landed`. The other 20 do not have
it.

This is not a new discovery. The 2026-08-02 `/bvssh-check` named it:

> *"THE FOUR FITNESS FUNCTIONS NOW SHOW THREE DIFFERENT EMPTY-INPUT BEHAVIOURS, and that
> inconsistency is the concrete next target."*

It was right, and the true scope is **20 of 23**, not 3 of 4.

Exit codes have drifted too: `0` advisory-always, `1` violations-found, `2` precondition-not-met,
`3` gate-missing. No script documents which convention it follows; callers guess.

### C3 — Canvas I/O (DRY + performance)

10 checks hand-roll `yaml.safe_load`. Five independently glob and re-read the same 130-file canvas
tree. Nothing caches; nothing is shared. Each check pays full parse cost for files another check
parsed 200 ms earlier.

### C4 — Domain model (DRY, and it produced a live bug today)

Canvas semantics are re-encoded per check:

- `_status()` — parsing `completed  # trailing YAML comment` — written **twice today**, in
  `check_reply_owed.py` and `check_evidence_landed.py`, by the same agent in the same session,
  neither aware of the other.
- Terminal-status sets, touch-log direction vocabulary, `canvas_refs` parsing, evidence-tier names:
  all re-declared per script.

### C5 — Process model (performance, the headline)

`session-start.sh` is a bash orchestrator that shells out **33 times**: 24 inline `python3 -c`
blocks and 9 script invocations. Each pays ~100 ms of interpreter startup before doing any work.

Measured per-check cost on the dogfood canvas:

| Check | Wall time |
|---|---:|
| `check_source_authenticity` | 0.89 s |
| `check_reply_owed` | 0.35 s |
| `check_evidence_landed` | 0.35 s |
| `check_stale_prose` | 0.20 s |

Most of each figure is startup and re-parsing, not analysis.

### C6 — Logic duplicated into prose (already caused one incident)

v0.105.0 shipped because reply-owed existed twice: as executable code in `session-start.sh` and as
prose in `canvas-health` step 8c(e). The same-day fix landed in the prose; the code kept the bug for
two more days and re-flagged the same two tasks. **The class is not fixed** — it was fixed for that
one rule. Other skills still describe algorithms that scripts also implement.

### C7 — Taxonomy (cognitive load, and the founder hit it)

Three things are called "wiring":

| Name | Actually checks |
|---|---|
| `check_wiring.py` | the framework's own packaged plugin tree |
| `check_wiring_contract.py` | consumer project code against a declared contract |
| `check_evidence_landed.py` | evidence routing between canvases |

The third is a different universe from the first two, and the founder's question — *"I thought we
already had a check for wiring"* — is the evidence that the naming costs real comprehension.

---

## 3. Target architecture

Three layers, each owning one concern. No check knows about argparse, YAML, or exit codes.

```
                    ┌──────────────────────────────────────┐
  ENTRY POINTS      │ hooks/  skills/  CI  pre-push  CLI    │
                    └───────────────┬──────────────────────┘
                                    │  one process, one contract
                    ┌───────────────▼──────────────────────┐
  RUNNER            │ _check_lib.py                        │
                    │  · CLI contract (one dialect)        │
                    │  · CheckResult / Finding types       │
                    │  · empty-input refusal, once         │
                    │  · exit-code policy, once            │
                    │  · JSON payload shape, once          │
                    │  · registry + batch runner           │
                    └───────────────┬──────────────────────┘
                    ┌───────────────▼──────────────────────┐
  DOMAIN            │ _canvas_lib.py                       │
                    │  · load canvas ONCE, cached          │
                    │  · Task / Opportunity / Diamond      │
                    │  · status, touch_log, canvas_refs    │
                    │  · evidence tiers, terminal sets     │
                    └───────────────┬──────────────────────┘
                    ┌───────────────▼──────────────────────┐
  CHECKS (23)       │ pure: scan(ctx) -> list[Finding]     │
                    │ no I/O, no CLI, no exit codes        │
                    └──────────────────────────────────────┘
```

### 3.1 The check contract

Every check collapses to one function:

```python
# check_reply_owed.py — the WHOLE file, after refactor
from _check_lib import Finding, register

@register(
    id="reply-owed",
    tier="advisory",
    needs=("human-tasks",),          # declares its inputs; runner loads them once
    summary="they wrote, you have not answered",
)
def scan(ctx) -> list[Finding]:
    for task in ctx.tasks.open():          # domain model, not YAML
        contact = task.last_contact()      # tie-break lives in ONE place
        if contact and contact.inbound and contact.age_days >= 3:
            yield Finding(subject=task.id, detail=f"inbound {contact.age_days}d ago")
```

What disappears: argparse, `yaml.safe_load`, `_status()`, the JSON block, the empty-input branch,
the exit-code decision, the print formatting. **Roughly 60–70 lines per check become ~10.**

### 3.2 The session-start orchestrator

`session-start.sh` stops being an orchestrator and becomes a thin caller:

```bash
python3 "$PLUGIN/scripts/run_checks.py" --tier=session-start --project-dir "$PROJECT_DIR"
```

One process. One canvas load. All advisory checks run in-process against the cached tree.

---

## 4. Projected improvements — stated as estimates, not results

**These are projections from measured inputs. Nothing has been built, so nothing is verified.**

| Metric | Now (measured) | Target (projected) | Basis |
|---|---:|---:|---|
| `python3` spawns at session start | **33** | **1–3** | one runner + retained bash-native checks |
| Session-start wall time | **4.08 s** | **0.6–1.0 s** | 33 × ~100 ms startup removed; canvas parsed once not 5× |
| Timeout budget consumed | **82%** | **~15%** | derived from above |
| Canvas full-tree parses per session | **≥5** | **1** | shared cached loader |
| Checks with empty-input honesty | **3 / 23** | **23 / 23** | inherited from the runner, not per-file |
| LOC in `check_*.py` | **6,286** | **~2,500–3,000** | ~50 lines of boilerplate × 23 removed |
| CLI dialects | **~4** | **1** | one contract |

**The honest caveat**: the wall-time projection assumes interpreter startup dominates, which the
per-check numbers support (0.20 s for a check that parses 130 files is mostly startup) but do not
prove. **First implementation step must be a spike that measures the runner on the real canvas
before any check is migrated.** If the projection is wrong, the refactor's main justification is
weaker and the decision should change.

---

## 5. Validation: nothing may be lost

The risk of a refactor this size is silent coverage loss — precisely the failure class this
framework exists to catch. Four mechanisms, in order:

### V1 — Behaviour-equivalence harness, built BEFORE migration

For each check, capture current output on the dogfood canvas + on fixtures as a golden file. After
migration, byte-compare findings (ids and subjects, not prose). **A check whose finding set changes
must be justified in the commit or reverted.** This is not optional and is the single most important
step.

### V2 — Coverage ledger

A table mapping all 23 current checks to their post-refactor home, with a column for "tests that
must still pass". Merged or deleted checks require an explicit line stating what now covers that
case. The ledger is reviewed before the last check is migrated, not after.

### V3 — The existing suites are the floor

828 python tests, 59 bash suites, 54 validate-template checks, ruff. All must stay green at every
step. `scripts/gates.sh` (v0.106.0) already runs them with an exit status that cannot be piped away.

### V4 — The framework's own guards apply to the refactor

`check_negative_control.py` already rejected a new guard this session for asserting only the quiet
path. It will be run against every migrated check. `check_empty_input_honesty.py` becomes
meaningfully enforceable for the first time, because the behaviour will live in one place.

---

## 6. Sequencing

Incremental, each step independently shippable and revertible. **No step changes what any check
finds.**

| Step | Work | Risk | Ships |
|---|---|---|---|
| 0 | **Spike**: build the runner, measure it on the real canvas. Confirm or refute the 0.6–1.0 s projection. | none | measurement only |
| 1 | Build `_check_lib.py` + `_canvas_lib.py` with tests. Migrate nothing. | none | new code, unused |
| 2 | Build the V1 golden-file harness against all 23 checks as they are today. | none | test-only |
| 3 | Migrate **3** checks (`reply_owed`, `evidence_landed`, `stale_prose` — the three I know best and which share the most). Prove byte-equivalence. | low | 3 migrated |
| 4 | Migrate the remaining 20 in batches of ~5, golden-file gated. | medium | rolling |
| 5 | Replace the 24 inline `python3 -c` blocks in `session-start.sh` with runner calls. **This is where the speed arrives.** | medium-high | the 4.08 s → target |
| 6 | Taxonomy pass: rename for C7, deprecate aliases with a release note. | low | naming |

**Stop conditions.** If step 0 refutes the latency projection, re-decide rather than continue — the
DRY and consistency arguments alone may not justify steps 4–5. If any golden-file diff cannot be
explained, stop and revert that batch.

---

## 7. What this plan deliberately does NOT do

- **Does not touch skills prose (C6) beyond the taxonomy pass.** That is a separate audit: finding
  every skill that re-describes an algorithm a script implements. Real, and out of scope here.
- **Does not merge checks.** Overlap is in the *plumbing*, not the *rules*. Every one of the 23
  rules is distinct and earns its place; merging rules would lose coverage, which V1/V2 exist to
  prevent.
- **Does not change any finding.** A refactor that also changes behaviour cannot be validated,
  because the golden files would have no meaning.
- **Does not claim an improvement it has not measured.** Section 4 is projections. Section 0 and 2
  are measurements. The distinction is kept visible on purpose.

---

## 8. The argument against doing this at all

Recorded because the decision should be made against it, not around it.

The framework's quality dimensions are **already strong**: Better improving, Sooner elite,
Automation green, 828 tests. `products_shipped` is **0/10**. This refactor improves the machine
that improves the framework — one more turn of a loop that is already the most self-referential part
of the project, and the 2026-08-08 BVSSH assessment named exactly that as the risk.

**The counter-argument, which is why the plan exists**: the 4.08 s / 5 s timeout is not tidiness. It
is a live reliability risk on the one surface every session depends on, and it degrades to silence
rather than to an error. That part is worth fixing regardless of the rest.

**A minimal option, if the full refactor is not worth a cycle**: do steps 0 and 5 only — collapse
the 24 inline `python3 -c` blocks into one process, leave all 23 checks untouched. That captures
most of the latency win for a fraction of the risk, and leaves the DRY and consistency work for a
later cycle. It is the recommended fallback.
