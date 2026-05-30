#!/usr/bin/env bash
# Fixture: upgrade.sh missing the evals_replace parse_manifest.py call.
# Check 16 must FAIL and name the missing key.
set -euo pipefail

TOP_LEVEL=$(python3 plugins/mycelium/scripts/parse_manifest.py top_level)
DIRECTORIES=$(python3 plugins/mycelium/scripts/parse_manifest.py directories)
SINGLE_FILES=$(python3 plugins/mycelium/scripts/parse_manifest.py single_files)
HARNESS_FILES=$(python3 plugins/mycelium/scripts/parse_manifest.py harness_framework)
PRESERVED_READMES=$(python3 plugins/mycelium/scripts/parse_manifest.py preserved_dir_readmes)
# evals_replace intentionally omitted

for item in $TOP_LEVEL $DIRECTORIES $SINGLE_FILES $HARNESS_FILES $PRESERVED_READMES; do
  echo "sync: $item"
done
