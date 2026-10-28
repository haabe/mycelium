#!/usr/bin/env bash
# tests/bash/_ladder.sh — shared fixture: everything above an L3 (v0.247.0).
#
# Since 0.247.0 a delivery cycle carries code only when the whole ladder above it is in place: a
# live L0 on a stated purpose, a live L1 on a named strategic decision with a North Star and a
# mapped landscape, a desired outcome naming that North Star, a live L2 on the target opportunity,
# and, for the safety gates, a threat model and a privacy assessment on record. Each gate test used
# to build its chain inline; three copies of this would drift, so it lives here once.
#
#   write_ladder <project_dir>          North Star, landscape, threat model, privacy assessment,
#                                       services.yml principles (v0.331.0)
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
    # v0.331.0: a Privacy pass needs the seven principles judged with evidence, and a Service
    # Quality pass all 15 Downe principles; the gate reads the record the skills write.
    local k
    printf 'principles:\n' >> "$c/privacy-assessment.yml"
    for k in proactive_not_reactive privacy_as_default privacy_embedded full_functionality \
             end_to_end_security visibility_transparency respect_for_users; do
        printf '  %s:\n    assessment: pass\n    evidence: "read the swap flow"\n' "$k" \
            >> "$c/privacy-assessment.yml"
    done
    printf 'principles:\n' > "$c/services.yml"
    for k in $(seq 1 15); do
        printf '  - id: %s\n    assessment: partial\n    evidence: "walked the swap flow"\n' "$k" \
            >> "$c/services.yml"
    done
}

# decide_file <diamonds_file>: since v0.306.0 the phase is not read; a fixture written with a
# `phase` gets the decisions that phase stands for, through the migration's own function (the
# python tests' tests/python/decided.py), so the gates judge it where it says it is.
decide_file() {
    python3 - "$1" "$(cd "$(dirname "${BASH_SOURCE[0]}")/../python" && pwd)" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[2])
from decided import decided_text
p = Path(sys.argv[1])
p.write_text(decided_text(p.read_text()))
PY
}

ladder_diamonds() {
    printf '  - id: l0\n    scale: L0\n    phase: define\n'
    printf '  - id: l1\n    scale: L1\n    phase: develop\n    object_ref: "lead with multi-site cafes"\n'
    # v0.307.0: the L2 records its target; its one opportunity is no longer read as one
    printf '  - id: l2\n    scale: L2\n    phase: define\n    object_ref: %s\n    target: %s\n' "$1" "$1"
}
