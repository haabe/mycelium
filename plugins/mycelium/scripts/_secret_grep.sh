#!/bin/bash
# Run Mycelium's own short list of secret shapes over stdin (v0.323.0).
#
# Exit 0: a line matched (prints the 1-based number of the first pattern that did).
# Exit 1: nothing matched.
# Exit 2: the scan could not run (prints which pattern and what grep said). A caller treats this
#         as a refusal, never as "clean": until 0.319.1 a grep that failed passed every write.
# shellcheck source=/dev/null
. "$(dirname "${BASH_SOURCE[0]}")/_secret_patterns.sh" || { echo "the pattern list could not be read"; exit 2; }
TEXT=$(cat)
[ -n "$TEXT" ] || exit 1
N=0
for PATTERN in "${SECRET_PATTERNS[@]}"; do
  N=$((N + 1))
  SAID=$(printf '%s\n' "$TEXT" | grep -cE -- "$PATTERN" 2>&1; exit "${PIPESTATUS[1]}")
  RC=$?
  if [ "$RC" -ge 2 ]; then
    echo "grep exited $RC on pattern $N of ${#SECRET_PATTERNS[@]} (${SAID%%$'\n'*})"
    exit 2
  fi
  if [ "$RC" -eq 0 ]; then
    echo "$N"
    exit 0
  fi
done
exit 1
