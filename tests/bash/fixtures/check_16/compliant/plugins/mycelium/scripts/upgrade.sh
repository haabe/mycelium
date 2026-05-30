#!/usr/bin/env bash
# Fixture: manifest-driven upgrade.sh (compliant with Check 16).
# Calls parse_manifest.py for every required list with literal keys;
# no hardcoded framework-directory or top-level filename literals.
set -euo pipefail

TOP_LEVEL=$(python3 plugins/mycelium/scripts/parse_manifest.py top_level)
DIRECTORIES=$(python3 plugins/mycelium/scripts/parse_manifest.py directories)
SINGLE_FILES=$(python3 plugins/mycelium/scripts/parse_manifest.py single_files)
HARNESS_FILES=$(python3 plugins/mycelium/scripts/parse_manifest.py harness_framework)
PRESERVED_READMES=$(python3 plugins/mycelium/scripts/parse_manifest.py preserved_dir_readmes)
EVALS_REPLACE=$(python3 plugins/mycelium/scripts/parse_manifest.py evals_replace)

for item in $TOP_LEVEL $DIRECTORIES $SINGLE_FILES $HARNESS_FILES $PRESERVED_READMES $EVALS_REPLACE; do
  echo "sync: $item"
done
