#!/bin/bash
# Mycelium preflight validation
# Creates a stamp file that the gate.sh checks before allowing code edits.
# This ensures corrections.md has been read and basic system health verified.

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
STAMP_FILE="/tmp/mycelium-preflight-stamp"
CORRECTIONS_FILE="$PROJECT_DIR/.claude/memory/corrections.md"

# Calculate corrections hash
CORRECTIONS_HASH="none"
if [ -f "$CORRECTIONS_FILE" ]; then
  if command -v md5 &>/dev/null; then
    CORRECTIONS_HASH=$(md5 -q "$CORRECTIONS_FILE")
  elif command -v md5sum &>/dev/null; then
    CORRECTIONS_HASH=$(md5sum "$CORRECTIONS_FILE" | cut -d' ' -f1)
  fi
fi

# Count corrections
CORRECTIONS_COUNT=0
if [ -f "$CORRECTIONS_FILE" ]; then
  CORRECTIONS_COUNT=$(grep -c '^### ' "$CORRECTIONS_FILE" 2>/dev/null || echo 0)
fi

# Write stamp
cat > "$STAMP_FILE" << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "corrections_hash": "$CORRECTIONS_HASH",
  "corrections_count": $CORRECTIONS_COUNT,
  "project_dir": "$PROJECT_DIR"
}
EOF

echo "Mycelium preflight complete. $CORRECTIONS_COUNT corrections in memory."
exit 0
