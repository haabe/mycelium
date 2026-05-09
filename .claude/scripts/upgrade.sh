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

# Parse args. Supports:
#   bash .claude/scripts/upgrade.sh                         # legacy refresh
#   bash .claude/scripts/upgrade.sh v0.21.0                 # legacy refresh to tag
#   bash .claude/scripts/upgrade.sh --migrate-to-plugin     # legacy → plugin migration
#   bash .claude/scripts/upgrade.sh --check-migration       # diagnostic only
MIGRATE_MODE=false
CHECK_ONLY=false
VERSION="main"
for arg in "$@"; do
    case "$arg" in
        --migrate-to-plugin) MIGRATE_MODE=true ;;
        --check-migration)   CHECK_ONLY=true ;;
        --*) echo "Unknown flag: $arg" >&2; exit 2 ;;
        *) VERSION="$arg" ;;
    esac
done

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
# Detect install form (legacy vs migrated-to-plugin)
# ============================================================
# Legacy form: framework reference content lives in .claude/skills/, .claude/engine/, etc.
# Plugin form: only project state in .claude/ (canvas/, diamonds/, memory/, evals/,
#              harness/decision-log+warnings, jit-tooling/active-metrics.yml). The
#              framework lives in ~/.claude/plugins/cache/...
detect_form() {
    if [ -d ".claude/skills" ] || [ -d ".claude/engine" ]; then
        FORM="legacy"
    elif [ -d ".claude/canvas" ] || [ -d ".claude/diamonds" ]; then
        FORM="plugin"
    else
        FORM="unknown"
    fi
}
detect_form

# ============================================================
# --check-migration: diagnostic only (read-only)
# ============================================================
if [ "$CHECK_ONLY" = "true" ]; then
    echo "Mycelium install-form check"
    echo "==========================="
    echo ""
    info "Detected form: $FORM"
    echo ""
    case "$FORM" in
        legacy)
            info "Framework files present in .claude/ (skills/, engine/, etc.)"
            info "This project is on the legacy install path."
            info "To migrate: install the plugin, then run:"
            echo "  bash .claude/scripts/upgrade.sh --migrate-to-plugin"
            ;;
        plugin)
            info "Only project state in .claude/. Framework reference comes from plugin cache."
            info "This project is on the plugin install path."
            info "To upgrade Mycelium: /plugin update mycelium@haabe-mycelium (inside Claude Code)"
            ;;
        unknown)
            warn "Could not detect install form — neither framework files nor project state found in .claude/."
            warn "Run /mycelium:setup (plugin) or 'npx degit haabe/mycelium .' (legacy) to bootstrap."
            ;;
    esac
    exit 0
fi

# ============================================================
# Plugin form: upgrade.sh is not the right surface
# ============================================================
if [ "$FORM" = "plugin" ] && [ "$MIGRATE_MODE" = "false" ]; then
    cat <<EOF
Mycelium Upgrade
================

This project is on plugin form (no legacy framework files in .claude/).
Plugin upgrades happen through Claude Code, not this script:

  /plugin update mycelium@haabe-mycelium

Or for a fresh fetch:

  /plugin marketplace update haabe/mycelium
  /plugin install mycelium@haabe-mycelium

To verify install-form: bash .claude/scripts/upgrade.sh --check-migration

If you intended to install Mycelium fresh in legacy form (npx-degit),
remove the plugin first or use a clean directory.

EOF
    exit 0
fi

# ============================================================
# --migrate-to-plugin: delete legacy framework files in .claude/,
# preserve project state. Idempotent on already-migrated projects.
# ============================================================
if [ "$MIGRATE_MODE" = "true" ]; then
    echo "Mycelium Migration: legacy → plugin"
    echo "===================================="
    echo ""

    if [ "$FORM" = "plugin" ]; then
        info "No legacy framework files found in .claude/ — already migrated."
        info "If the plugin is not installed yet, run inside Claude Code:"
        echo "    /plugin marketplace add haabe/mycelium"
        echo "    /plugin install mycelium@haabe-mycelium"
        exit 0
    fi

    if [ "$FORM" = "unknown" ]; then
        error "Could not detect install form. Aborting migration to be safe."
        error "Inspect .claude/ manually before re-running."
        exit 1
    fi

    if ! git rev-parse --is-inside-work-tree &>/dev/null; then
        error "Not a git repository. Initialize git first so the migration is reversible:"
        echo "  git init && git add -A && git commit -m 'Pre-migration snapshot'"
        exit 1
    fi
    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
        error "Uncommitted changes detected. Commit or stash first so the migration is reversible:"
        echo "  git add -A && git commit -m 'Pre-migration snapshot'"
        exit 1
    fi

    info "This will DELETE legacy framework files from .claude/ in your project:"
    echo ""
    echo "  WILL DELETE (framework reference, now in plugin cache):"
    echo "    .claude/skills/, .claude/engine/, .claude/hooks/,"
    echo "    .claude/scripts/, .claude/schemas/, .claude/domains/,"
    echo "    .claude/orchestration/, .claude/templates/, .claude/tests/"
    echo "    .claude/agents/ (if present)"
    echo "    .claude/jit-tooling/* (except active-metrics.yml)"
    echo "    .claude/harness/* (except decision-log.md, warnings-log.md)"
    echo ""
    echo "  WILL PRESERVE (project state):"
    echo "    .claude/canvas/, .claude/diamonds/, .claude/memory/,"
    echo "    .claude/evals/, .claude/state/,"
    echo "    .claude/harness/decision-log.md, .claude/harness/warnings-log.md,"
    echo "    .claude/jit-tooling/active-metrics.yml,"
    echo "    .claude/settings.local.json (if present)"
    echo ""
    echo "  Project root files (CLAUDE.md, README.md, AGENTS.md, etc.) are NOT touched."
    echo ""
    echo "  Reversible via git: this commit is reversible by 'git reset --hard HEAD' before"
    echo "  the migration commit lands."
    echo ""

    if [ -t 0 ]; then
        read -r -p "Continue? [y/N] " confirm
        if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
            info "Aborted. No changes made."
            exit 0
        fi
    else
        warn "Non-interactive shell — proceeding without prompt. Set MYCELIUM_MIGRATE_AUTO=cancel to abort here in CI."
        if [ "${MYCELIUM_MIGRATE_AUTO:-}" = "cancel" ]; then
            info "Aborted by MYCELIUM_MIGRATE_AUTO=cancel."
            exit 0
        fi
    fi

    # Driven by manifest.yml so the deletion list cannot drift from the
    # upgrade refresh list (Check 16 enforces this).
    fw_dirs=$(python3 .claude/scripts/parse_manifest.py directories)
    harness_fw=$(python3 .claude/scripts/parse_manifest.py harness_framework)

    info "Deleting legacy framework directories (manifest-driven)..."
    for d in $fw_dirs; do
        # Keep only directories under .claude/ (skip docs/, .github/ which are
        # project root / repo metadata, not Mycelium framework reference content).
        case "$d" in
            .claude/*) [ -d "$d" ] && rm -rf "$d" && info "  removed $d" ;;
        esac
    done

    info "Removing harness framework files (preserving project state)..."
    for f in $harness_fw; do
        [ -f "$f" ] && rm -f "$f"
    done
    # Clean up empty harness/ subdirs (READMEs etc.) but never the dir itself
    # if decision-log.md or warnings-log.md remain.
    if [ -d .claude/harness ]; then
        find .claude/harness -mindepth 1 -maxdepth 1 -type d -empty -delete 2>/dev/null || true
    fi

    if [ -d ".claude/jit-tooling" ]; then
        info "Pruning .claude/jit-tooling/ (preserving active-metrics.yml)..."
        find .claude/jit-tooling -mindepth 1 -maxdepth 1 \
            ! -name 'active-metrics.yml' ! -name '.gitkeep' -exec rm -rf {} +
    fi

    # Settings.json: warn if hooks block points at the deleted hooks tree.
    if [ -f .claude/settings.json ] && grep -q '"hooks"' .claude/settings.json 2>/dev/null; then
        warn ".claude/settings.json contains a 'hooks' block — likely points at"
        warn "the deleted hooks tree. Plugin form provides hooks via the plugin"
        warn "manifest; remove the legacy hooks block manually or hooks may fail"
        warn "silently. Edit .claude/settings.json yourself before next session."
    fi

    echo ""
    info "Migration complete."
    echo ""
    info "Project state preserved:"
    echo "    .claude/canvas/, .claude/diamonds/, .claude/memory/,"
    echo "    .claude/evals/, .claude/harness/{decision-log,warnings-log}.md,"
    echo "    .claude/jit-tooling/active-metrics.yml"
    echo ""
    info "Next steps (inside Claude Code):"
    echo "  1. Verify the plugin is installed:  /plugin list"
    echo "     If not: /plugin marketplace add haabe/mycelium"
    echo "             /plugin install mycelium@haabe-mycelium"
    echo "  2. Verify project state reads:      /mycelium:diamond-assess"
    echo "  3. Commit the migration:            git add -A && git commit -m 'chore: migrate from legacy to plugin form'"
    echo ""
    info "If anything looks off: 'git reset --hard HEAD' before committing returns to pre-migration state."
    exit 0
fi

# ============================================================
# Legacy refresh (npx-degit upgrade): existing flow, unchanged
# below. Falls through here only when FORM=legacy and MIGRATE_MODE=false.
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

# Record current version. Source file resolved via parse_manifest.py to avoid
# a hardcoded literal that would drift if version_source ever moves
# (corrections.md 2026-04-28 + 2026-05-03 + 2026-05-04 — recurring "validator/
# script passes on incomplete checks" pattern, graduated as G-V12).
VERSION_SOURCE=$(python3 .claude/scripts/parse_manifest.py version_source)
if [ -z "$VERSION_SOURCE" ]; then
    error "manifest.yml missing framework.version_source — cannot determine current version"
    exit 1
fi
CURRENT_VERSION=$(grep "Version [0-9]" "$VERSION_SOURCE" 2>/dev/null | head -1 | sed 's/.*Version //' | sed 's/ .*//' || echo "unknown")
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

NEW_VERSION=$(grep "Version [0-9]" "$TEMP_DIR/$VERSION_SOURCE" 2>/dev/null | head -1 | sed 's/.*Version //' | sed 's/ .*//' || echo "unknown")
info "Upstream version: $NEW_VERSION"
echo ""

# ============================================================
# Replace framework files
# ============================================================

info "Replacing framework files..."

# Read manifest from the UPSTREAM (temp dir) copy, not the local one.
# The local manifest is about to be replaced, but its contents drove every
# preceding upgrade — meaning new manifest entries (new top_level files, new
# directories) wouldn't take effect until a 2nd upgrade run if we read locally.
# corrections.md 2026-05-04 "manifest-driven script reads stale local manifest"
# (4th instance of the recurring stale-read pattern). Closed structurally by
# parse_manifest.py's --manifest= override.
UPSTREAM_MANIFEST="$TEMP_DIR/.claude/manifest.yml"

# Top-level files (manifest-driven — single source of truth)
# Closes the recurring hardcoded-list drift pattern documented in
# corrections.md 2026-04-28 (harness/) and 2026-05-03 (top_level/AGENTS.md).
TOP_LEVEL=$(python3 .claude/scripts/parse_manifest.py top_level "--manifest=$UPSTREAM_MANIFEST")
for file in $TOP_LEVEL; do
    if [ -f "$TEMP_DIR/$file" ]; then
        cp "$TEMP_DIR/$file" "./$file"
    fi
done

# Framework directories (manifest-driven, full replace)
# Paths include trailing slash and may live outside .claude/ (e.g., .github/,
# docs/), so iterate full paths.
DIRECTORIES=$(python3 .claude/scripts/parse_manifest.py directories "--manifest=$UPSTREAM_MANIFEST")
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
SINGLE_FILES=$(python3 .claude/scripts/parse_manifest.py single_files "--manifest=$UPSTREAM_MANIFEST")
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
HARNESS_FILES=$(python3 .claude/scripts/parse_manifest.py harness_framework "--manifest=$UPSTREAM_MANIFEST")
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
PRESERVED_READMES=$(python3 .claude/scripts/parse_manifest.py preserved_dir_readmes "--manifest=$UPSTREAM_MANIFEST")
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
EVALS_REPLACE=$(python3 .claude/scripts/parse_manifest.py evals_replace "--manifest=$UPSTREAM_MANIFEST")
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
echo "------------------------------------------------------------"
echo "Heads-up: Mycelium 0.20.x ships as a Claude Code plugin."
echo "Legacy npx-degit install is supported during transition,"
echo "but plugin form is the recommended path:"
echo ""
echo "  /plugin marketplace add haabe/mycelium"
echo "  /plugin install mycelium@haabe-mycelium"
echo ""
echo "To migrate this project from legacy to plugin form:"
echo "  bash .claude/scripts/upgrade.sh --migrate-to-plugin"
echo ""
echo "Project state (canvas/, diamonds/, memory/, decision-log.md,"
echo "evals/, active-metrics.yml) survives migration untouched."
echo "Skill invocations gain the 'mycelium:' namespace prefix"
echo "(e.g. /interview becomes /mycelium:interview); tab-completion"
echo "and natural-language invocation soften the typing tax."
echo "------------------------------------------------------------"
echo ""
