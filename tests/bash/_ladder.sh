#!/usr/bin/env bash
# tests/bash/_ladder.sh — shared fixture: everything above an L3 (v0.247.0).
#
# Since 0.247.0 a delivery cycle carries code only when the whole ladder above it is in place: a
# live L0 on a stated purpose, a live L1 on a named strategic decision with a North Star and a
# mapped landscape, a desired outcome naming that North Star, a live L2 on the target opportunity,
# and, for the safety gates, a threat model and a privacy assessment on record. Each gate test used
# to build its chain inline; three copies of this would drift, so it lives here once.
#
#   write_ladder <project_dir>          North Star, landscape, threat model, privacy assessment
#   ladder_diamonds <opportunity_id>    the L0/L1/L2 entries to put under `active_diamonds:`
#   OUTCOME_LINK                        the line to add under a `desired_outcome:` mapping
#   BUILD_GATES / EXPOSE_GATES          theory_gates_status flow maps passing the matrix's full sets

OUTCOME_LINK='  north_star_input_ref: "swaps settled in the app per week"'
BUILD_GATES='{evidence: pass, jtbd: pass, bias: pass, corrections: pass, four_risks: pass, cynefin: pass, privacy: pass, regulatory: n/a}'
EXPOSE_GATES='{evidence: pass, jtbd: pass, bias: pass, corrections: pass, four_risks: pass, cynefin: pass, privacy: pass, regulatory: n/a, security: pass, service_quality: pass-with-risk}'

write_ladder() {
    local c="$1/.claude/canvas"
    mkdir -p "$c"
    printf 'metric:\n  name: "swaps settled in the app per week"\n' > "$c/north-star.yml"
    printf 'components:\n  - id: comp-1\n    name: "group chat swaps"\n' > "$c/landscape.yml"
    printf 'threats:\n  - id: t1\n    description: "a guessed link token approves a swap"\n' > "$c/threat-model.yml"
    printf 'last_assessed: "2026-09-24"\ndata_inventory:\n  - data_type: "phone number"\n' > "$c/privacy-assessment.yml"
}

ladder_diamonds() {
    printf '  - id: l0\n    scale: L0\n    phase: define\n'
    printf '  - id: l1\n    scale: L1\n    phase: develop\n    object_ref: "lead with multi-site cafes"\n'
    printf '  - id: l2\n    scale: L2\n    phase: define\n    object_ref: %s\n' "$1"
}
