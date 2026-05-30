#!/usr/bin/env bash
# Fixture: upgrade.sh that calls parse_manifest.py for all keys BUT also
# re-introduces hardcoded framework-directory loops. Check 16 must FAIL the
# drift detector (>3 hardcoded .claude/<dir> literals).
set -euo pipefail

TOP_LEVEL=$(python3 plugins/mycelium/scripts/parse_manifest.py top_level)
DIRECTORIES=$(python3 plugins/mycelium/scripts/parse_manifest.py directories)
SINGLE_FILES=$(python3 plugins/mycelium/scripts/parse_manifest.py single_files)
HARNESS_FILES=$(python3 plugins/mycelium/scripts/parse_manifest.py harness_framework)
PRESERVED_READMES=$(python3 plugins/mycelium/scripts/parse_manifest.py preserved_dir_readmes)
EVALS_REPLACE=$(python3 plugins/mycelium/scripts/parse_manifest.py evals_replace)

cp -r upstream/.claude/engine/ "$TEMP/.claude/engine/"
cp -r upstream/.claude/skills/ "$TEMP/.claude/skills/"
cp -r upstream/.claude/hooks/ "$TEMP/.claude/hooks/"
cp -r upstream/.claude/domains/ "$TEMP/.claude/domains/"
