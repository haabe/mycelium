#!/usr/bin/env bash
# Mycelium Upgrade Script
#
# Safely upgrades Mycelium framework files without destroying project state.
# Reads .claude/manifest.yml to distinguish framework files from project data.
#
# Usage:
#   bash .claude/scripts/upgrade.sh              # upgrade to latest (main branch)
#   bash .claude/scripts/upgrade.sh v0.12.0      # upgrade to specific tag/branch
#
# Prerequisites: git, npx (Node.js)
#
# What it does:
#   1. Checks for uncommitted changes (refuses if dirty)
#   2. Pulls upstream to a temp directory
#   3. Replaces framework files (engine, skills, hooks, etc.)
#   4. Replaces ALL harness files except project state (decision-log.md)
#   5. Syncs READMEs in preserved directories (canvas, diamonds, memory, evals, tests)
#   6. Adds new canvas templates (never overwrites existing)
#   7. Runs validation
#   8. Reports what changed
#
# What it NEVER touches:
#   - .claude/diamonds/active.yml (your diamond state)
#   - .claude/memory/ (corrections, patterns, journals)
#   - .claude/harness/decision-log.md (your decisions)
#   - .claude/canvas/*.yml that already exist (your populated canvases)
#   - .claude/settings.local.json (your local overrides)
#   - .claude/state/ (runtime state)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

VERSION="${1:-main}"
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Colors (if terminal supports them)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ============================================================
# Pre-flight checks
# ============================================================

echo "Mycelium Upgrade"
echo "================"
echo ""

# Check git
if ! git rev-parse --is-inside-work-tree &>/dev/null; then
    error "Not a git repository. Initialize git first:"
    echo "  git init && git add -A && git commit -m 'Pre-upgrade baseline'"
    exit 1
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    error "Uncommitted changes detected. Commit or stash first:"
    echo "  git add -A && git commit -m 'Pre-upgrade snapshot'"
    exit 1
fi

# Record current version
CURRENT_VERSION=$(grep "Version [0-9]" CLAUDE.md 2>/dev/null | head -1 | sed 's/.*Version //' | sed 's/ .*//' || echo "unknown")
info "Current version: $CURRENT_VERSION"
info "Upgrading to: $VERSION"
echo ""

# ============================================================
# Pull upstream
# ============================================================

info "Pulling upstream Mycelium ($VERSION)..."
if ! npx degit "haabe/mycelium#$VERSION" "$TEMP_DIR" --force 2>/dev/null; then
    error "Failed to pull upstream. Check version/tag exists: $VERSION"
    exit 1
fi

NEW_VERSION=$(grep "Version [0-9]" "$TEMP_DIR/CLAUDE.md" 2>/dev/null | head -1 | sed 's/.*Version //' | sed 's/ .*//' || echo "unknown")
info "Upstream version: $NEW_VERSION"
echo ""

# ============================================================
# Replace framework files
# ============================================================

info "Replacing framework files..."

# Top-level files
for file in CLAUDE.md README.md CONTRIBUTORS.md LICENSE requirements-ci.txt; do
    if [ -f "$TEMP_DIR/$file" ]; then
        cp "$TEMP_DIR/$file" "./$file"
    fi
done

# Framework directories (full replace)
for dir in engine skills hooks domains orchestration schemas scripts optimization tests auto-dogfood; do
    if [ -d "$TEMP_DIR/.claude/$dir" ]; then
        rm -rf ".claude/$dir"
        cp -R "$TEMP_DIR/.claude/$dir" ".claude/$dir"
    fi
done

# jit-tooling: framework files get replaced, but active-metrics.yml and any
# non-shipped metrics-adapters/*.md are per-project state. Preserve them.
if [ -d "$TEMP_DIR/.claude/jit-tooling" ]; then
    # Save per-project files before wipe
    PRESERVE_DIR=$(mktemp -d)
    if [ -f ".claude/jit-tooling/active-metrics.yml" ]; then
        cp ".claude/jit-tooling/active-metrics.yml" "$PRESERVE_DIR/active-metrics.yml"
    fi
    if [ -d ".claude/jit-tooling/metrics-adapters" ]; then
        # Copy user-generated adapters (everything except shipped ones)
        mkdir -p "$PRESERVE_DIR/metrics-adapters"
        for f in .claude/jit-tooling/metrics-adapters/*.md; do
            [ -e "$f" ] || continue
            name=$(basename "$f")
            case "$name" in
                TEMPLATE.md|GENERATING.md|github.md) ;;  # shipped — skip
                *) cp "$f" "$PRESERVE_DIR/metrics-adapters/$name" ;;
            esac
        done
    fi

    # Replace the framework directory
    rm -rf .claude/jit-tooling
    cp -R "$TEMP_DIR/.claude/jit-tooling" .claude/jit-tooling

    # Restore preserved per-project files
    if [ -f "$PRESERVE_DIR/active-metrics.yml" ]; then
        cp "$PRESERVE_DIR/active-metrics.yml" .claude/jit-tooling/active-metrics.yml
    fi
    if [ -d "$PRESERVE_DIR/metrics-adapters" ]; then
        mkdir -p .claude/jit-tooling/metrics-adapters
        for f in "$PRESERVE_DIR/metrics-adapters"/*.md; do
            [ -e "$f" ] || continue
            cp "$f" ".claude/jit-tooling/metrics-adapters/$(basename "$f")"
        done
    fi

    rm -rf "$PRESERVE_DIR"
fi

# .github and tests
if [ -d "$TEMP_DIR/.github" ]; then
    rm -rf .github
    cp -R "$TEMP_DIR/.github" .github
fi
if [ -d "$TEMP_DIR/tests" ]; then
    rm -rf tests
    cp -R "$TEMP_DIR/tests" tests
fi

# settings.json (NOT settings.local.json)
if [ -f "$TEMP_DIR/.claude/settings.json" ]; then
    cp "$TEMP_DIR/.claude/settings.json" .claude/settings.json
fi

# manifest.yml
if [ -f "$TEMP_DIR/.claude/manifest.yml" ]; then
    cp "$TEMP_DIR/.claude/manifest.yml" .claude/manifest.yml
fi

info "Framework files replaced."

# ============================================================
# Selectively replace harness files (preserve decision-log.md)
# ============================================================

info "Updating harness framework files..."

# Sync ALL framework files in harness, preserving only project state.
# Project state files that must never be overwritten:
HARNESS_PROJECT_STATE="decision-log.md"

for file in "$TEMP_DIR"/.claude/harness/*; do
    [ -e "$file" ] || continue
    basename=$(basename "$file")
    # Skip project state files
    skip=false
    for preserve in $HARNESS_PROJECT_STATE; do
        if [ "$basename" = "$preserve" ]; then
            skip=true
            break
        fi
    done
    if [ "$skip" = false ]; then
        cp "$file" ".claude/harness/$basename"
    fi
done

info "Harness files updated (decision-log.md preserved)."

# ============================================================
# Add new canvas templates (never overwrite existing)
# ============================================================

# ============================================================
# Sync READMEs in preserved directories
# ============================================================
# Directories like canvas/, diamonds/, memory/, evals/, tests/
# contain project state (never overwritten), but their READMEs
# are framework documentation that should be kept current.

info "Syncing READMEs in preserved directories..."

READMES_SYNCED=0
for dir in canvas diamonds memory evals evals/dogfood-reports tests; do
    if [ -f "$TEMP_DIR/.claude/$dir/README.md" ]; then
        mkdir -p ".claude/$dir"
        cp "$TEMP_DIR/.claude/$dir/README.md" ".claude/$dir/README.md"
        READMES_SYNCED=$((READMES_SYNCED + 1))
    fi
done

if [ "$READMES_SYNCED" -gt 0 ]; then
    info "$READMES_SYNCED README(s) synced in preserved directories."
else
    info "No READMEs to sync in preserved directories."
fi

# ============================================================
# Add new canvas templates (never overwrite existing)
# ============================================================

info "Checking for new canvas templates..."

NEW_CANVASES=0
for file in "$TEMP_DIR"/.claude/canvas/*.yml; do
    basename=$(basename "$file")
    if [ ! -f ".claude/canvas/$basename" ]; then
        cp "$file" ".claude/canvas/$basename"
        info "  Added new canvas: $basename"
        NEW_CANVASES=$((NEW_CANVASES + 1))
    fi
done

if [ "$NEW_CANVASES" -eq 0 ]; then
    info "No new canvas templates to add."
else
    info "$NEW_CANVASES new canvas template(s) added."
fi

# ============================================================
# Replace eval scenarios (preserve dogfood reports and results)
# ============================================================

if [ -d "$TEMP_DIR/.claude/evals/scenarios" ]; then
    rm -rf .claude/evals/scenarios
    cp -R "$TEMP_DIR/.claude/evals/scenarios" .claude/evals/scenarios
    info "Eval scenarios updated."
fi

# Update evals README if it exists upstream
if [ -f "$TEMP_DIR/.claude/evals/dogfood-reports/README.md" ]; then
    cp "$TEMP_DIR/.claude/evals/dogfood-reports/README.md" .claude/evals/dogfood-reports/README.md
fi

echo ""

# ============================================================
# Validate
# ============================================================

info "Running validation..."
echo ""

if bash .claude/tests/validate-template.sh; then
    echo ""
    info "Validation passed."
else
    echo ""
    warn "Validation failed. Review the output above."
    warn "To revert: git checkout -- ."
fi

echo ""

# ============================================================
# Summary
# ============================================================

CHANGED=$(git diff --stat | tail -1 || echo "no changes")

echo "================"
echo "Upgrade Summary"
echo "================"
echo "  From: $CURRENT_VERSION"
echo "  To:   $NEW_VERSION"
echo "  $CHANGED"
echo ""
echo "Preserved (not touched):"
echo "  - .claude/diamonds/active.yml (diamond state)"
echo "  - .claude/memory/ (corrections, patterns, journals)"
echo "  - .claude/harness/decision-log.md (decisions)"
echo "  - .claude/canvas/*.yml (populated canvases)"
echo "  - .claude/settings.local.json (local overrides)"
echo ""
echo "Next steps:"
echo "  1. Review changes: git diff"
echo "  2. Commit: git add -A && git commit -m 'Upgrade Mycelium to v$NEW_VERSION'"
echo "  3. Run /diamond-assess to verify diamond compatibility"
echo ""
