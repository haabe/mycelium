#!/usr/bin/env python3
"""
check_gated_by.py — DRAFT, NOT WIRED

Status: stub. Not invoked by any hook, validator, or CI. Lives here as a
design exercise pending evidence-gated graduation per
`.claude/memory/corrections.md` 2026-05-23 entry on the implicit-causal-link
sub-class of anti-pattern #7.

Graduation criterion (NOT YET MET):
    2nd post-convention instance where a deferral/threshold statement in
    agent output OR framework prose lacks any gate-naming form (Gated by:,
    ON HOLD (pending X), or natural-prose equivalent). The convention
    shipped 2026-05-23 to CLAUDE.md Communication Rules is the prevention;
    this script is the enforcement mechanism candidate.

Until graduation:
    - Do NOT add to validate-template.sh.
    - Do NOT add to a pre-push hook.
    - Do NOT add to manifest.yml as a shipped artifact.
    - May be invoked manually for evidence-gathering (`python3
      plugins/mycelium/scripts/check_gated_by.py <path>`).

When graduated:
    1. Add to manifest.yml under scripts/.
    2. Wire into validate-template.sh as Check N+1 (replace N with the
       next free check number; current high-water-mark per
       `tests/validate-template.sh` header).
    3. Ship a G-V12 coverage proof: an intentionally-broken fixture in
       `tests/fixtures/` that this script flags, with a pytest assertion
       that it does.
    4. Re-run inventory against the whole framework before flipping to
       FAIL tier; start at WARN.

Design notes from the 2026-05-23 inventory:
    Hard violations in the framework as of convention-ship: ~0 (this is
    why mechanism graduation cannot happen now — the convention may simply
    work; mechanism-without-evidence is the gold-plating / AP#7 failure
    mode the framework just shipped a correction for).

    Soft format-mismatches: ~8 instances of well-formed gate-naming in
    non-Gated-by formats (canvas ON HOLD (pending X); natural prose like
    "Wait for X before Y" or "deferred pending X"). These are intentionally
    NOT flagged — the convention explicitly accepts these forms.

    Trigger phrases (the patterns that REQUIRE a nearby gate clause):
      - "defer to [date]" / "defer until [event]"
      - "deferred to [date]" / "deferred pending [event]"
      - "ship at [threshold]" / "ship when [event]"
      - "act when [N]" / "act after [date]" / "act before [date]"
      - "after [date]" — only flagged when in recommendation context
      - "before [date]" — only flagged when in recommendation context
      - "until [event/N]" — only flagged in deferral context
      - "post-[event]" (post-surgery, post-launch, etc.) — high false-positive
        risk; needs context filter

    Acceptable gate-naming forms (any one satisfies the convention):
      1. Explicit: `Gated by: [event] — [interventional|observational]`
      2. Canvas: `ON HOLD (pending [X])`
      3. Natural prose: "Wait for X before Y," "deferred pending X,"
         "until X lands," "X remains the gate," similar constructions
         where the gate event is explicitly named in the sentence.

    Window for gate-clause lookup:
        ±3 lines around the trigger phrase (configurable). Tighter window
        produces more false positives; wider window produces more false
        negatives. The right value will be calibrated against lived evidence
        on graduation.

    False-positive risk surfaces:
        - "post-mortem," "post-deploy," "post-launch" are compound nouns
          not deferrals — must be filtered.
        - "after the user does X" in instructional prose (not a deferral)
          must not be flagged.
        - Quoted prior text in audit trails (decision-log entries quoting
          prior decisions) should not be flagged — they're history, not
          new recommendations.

    Output shape:
        For each flagged statement: file path, line number, trigger phrase,
        ±3 lines of context, suggested gate clause (heuristic). Same shape
        as `ingest_warnings.py` and `validate_canvas.py` output.

    Exit codes:
        0 — no hard violations found
        1 — hard violations found (deferral with no gate-naming form within
            window)
        2 — script error

Theory grounding:
    Pearl (interventional vs observational evidence); Kahneman *Illusion of
    Validity*; Grice maxim of quantity; Sperber & Wilson relevance theory.
    See `harness/anti-patterns.md#7-consistency-as-evidence` for the full
    catalog of sub-classes; sub-class (g) implicit-causal-link is what this
    script targets.

Companion artifacts:
    - CLAUDE.md "Always name the gate" convention (Communication Rules)
    - .claude/memory/cluster-instances.md consistency-as-evidence cluster
    - .claude/memory/corrections.md 2026-05-23 entry on implicit-causal-link
"""

import sys


def main() -> int:
    print(
        "check_gated_by.py is a DRAFT stub. Not yet implemented.\n"
        "Graduation criterion: 2nd post-convention instance of a hard\n"
        "violation (deferral/threshold statement with no gate-naming form).\n"
        "Until graduation, the convention in CLAUDE.md Communication Rules\n"
        "is the active prevention; this script is the parking state for the\n"
        "candidate enforcement mechanism.\n"
        "\n"
        "See header comment for design notes from the 2026-05-23 inventory.\n",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
