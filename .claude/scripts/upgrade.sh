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
trap 'rm -rf "$TEMP_DIR"' EXIT

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

# Top-level files (manifest-driven — single source of truth)
# Reads .claude/manifest.yml#framework.top_level via parse_manifest.py.
# Closes the recurring hardcoded-list drift pattern documented in
# corrections.md 2026-04-28 (harness/) and 2026-05-03 (top_level/AGENTS.md).
TOP_LEVEL=$(python3 .claude/scripts/parse_manifest.py top_level)
for file in $TOP_LEVEL; do
    if [ -f "$TEMP_DIR/$file" ]; then
        cp "$TEMP_DIR/$file" "./$file"
    fi
done

# Framework directories (manifest-driven, full replace)
# Reads .claude/manifest.yml#framework.directories. Paths include trailing
# slash and may live outside .claude/ (e.g., .github/), so iterate full paths.
DIRECTORIES=$(python3 .claude/scripts/parse_manifest.py directories)
for dir_path in $DIRECTORIES; do
    # Strip trailing slash for consistent path handling
    dir_path="${dir_path%/}"
    if [ -d "$TEMP_DIR/$dir_path" ]; then
        rm -rf "$dir_path"
        cp -R "$TEMP_DIR/$dir_path" "$dir_path"
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

# Note: .github/ is now handled by the manifest-driven directories loop
# above (it's listed in framework.directories). Same with .claude/tests/.
# A root-level tests/ directory is NOT in the manifest — if it ever needs
# to be synced, add it to manifest.directories rather than re-introducing
# a hardcoded special case here.

# Single-file framework files (manifest-driven)
# Reads .claude/manifest.yml#framework.single_files (settings.json, manifest.yml).
# settings.local.json is project state (NOT in single_files) — never overwritten.
SINGLE_FILES=$(python3 .claude/scripts/parse_manifest.py single_files)
for file in $SINGLE_FILES; do
    if [ -f "$TEMP_DIR/$file" ]; then
        mkdir -p "$(dirname "$file")"
        cp "$TEMP_DIR/$file" "$file"
    fi
done

info "Framework files replaced."

# ============================================================
# Selectively replace harness files (preserve decision-log.md)
# ============================================================

info "Updating harness framework files..."

# Manifest-driven: read the explicit harness_framework list. Anything NOT
# on this list (e.g., decision-log.md, which is in project_state) is
# preserved by omission — no separate skip logic needed.
HARNESS_FILES=$(python3 .claude/scripts/parse_manifest.py harness_framework)
for file in $HARNESS_FILES; do
    if [ -f "$TEMP_DIR/$file" ]; then
        mkdir -p "$(dirname "$file")"
        cp "$TEMP_DIR/$file" "$file"
    fi
done

info "Harness files updated (decision-log.md preserved by manifest exclusion)."

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

# Manifest-driven: full README paths from preserved_dir_readmes.
READMES_SYNCED=0
PRESERVED_READMES=$(python3 .claude/scripts/parse_manifest.py preserved_dir_readmes)
for readme in $PRESERVED_READMES; do
    if [ -f "$TEMP_DIR/$readme" ]; then
        mkdir -p "$(dirname "$readme")"
        cp "$TEMP_DIR/$readme" "$readme"
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

# Manifest-driven: evals_replace lists directories that get full replacement.
EVALS_REPLACE=$(python3 .claude/scripts/parse_manifest.py evals_replace)
for path in $EVALS_REPLACE; do
    path="${path%/}"
    if [ -d "$TEMP_DIR/$path" ]; then
        rm -rf "$path"
        cp -R "$TEMP_DIR/$path" "$path"
        info "Eval scenarios updated: $path"
    fi
done

# Note: .claude/evals/dogfood-reports/README.md is now covered by the
# preserved_dir_readmes manifest-driven loop above. The previous explicit
# block was removed as redundant during the 2026-05-03 manifest-driven
# refactor. Adding new preserved-dir READMEs is a manifest edit only.

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
