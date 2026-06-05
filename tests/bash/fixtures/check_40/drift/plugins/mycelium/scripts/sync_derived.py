#!/usr/bin/env python3
"""Test fixture stub: simulates sync_derived.py drift case.

Check 40 wraps `sync_derived.py --check`. This stub returns exit 1 with a
drift message, exercising the fail path of the gate. The check is testing
the WRAPPER (does it call the script, report correctly on non-zero), not
the script's own drift-detection logic — that has its own coverage in the
upstream sync_derived.py tests if any. Decoupling here lets check_40's
fixture stay light (~10 lines per fixture vs. replicating the full
sync_derived environment of CLAUDE.md + plugin.json + 49 SKILL.md files).
"""
import sys

print("DRIFT (version=1.2.3, skills=5):")
print("  - docs/ai-system-card.md: version → 1.2.3")
sys.exit(1)
