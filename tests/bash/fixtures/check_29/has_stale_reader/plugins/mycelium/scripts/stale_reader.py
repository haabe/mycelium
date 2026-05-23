"""Test fixture for Check 29: stale-state-read failure mode.

This script intentionally exhibits the failure shape Check 29 looks for.
See tests/bash/test_check_29.sh for the expected detection.

NOTE: Do not describe the missing override mechanism in this docstring;
Check 29 grep cannot distinguish prose from real imports.
"""
from pathlib import Path

MANIFEST_PATH = Path(__file__).resolve().parent.parent / "manifest.yml"


def load_manifest():
    return MANIFEST_PATH.read_text()
