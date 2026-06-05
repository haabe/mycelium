#!/usr/bin/env python3
"""Test fixture stub: simulates sync_derived.py synced case.

Companion to fixtures/check_40/drift/. This stub returns exit 0 with the
"no drift" message, exercising the pass path of check_sync_derived_drift.
See the drift stub's docstring for the rationale on stubbing vs. full
environment replication.
"""
import sys

print("OK: version=1.2.3, skills=5 — no drift.")
sys.exit(0)
