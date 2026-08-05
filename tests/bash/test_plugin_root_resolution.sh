#!/usr/bin/env bash
# Regression tests for the PLUGIN-CANNOT-KNOW-ITS-OWN-PATH class, v0.88.0.
#
# THE BUG. hooks.codex.json and hooks.cursor.json shipped
# `${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/cache/mycelium-plugin/mycelium}`.
# That literal never resolved on any machine — the marketplace directory is
# `haabe-mycelium` and the cache is versioned — and Cursor/Codex set no
# CLAUDE_PLUGIN_ROOT, so the fallback branch was the LIVE path for every
# consumer. `bash /missing/gate.sh` exits 127; the hook contract blocks on 2.
# Every gate reported "not blocked" without ever running. Five more commands
# carried a bare ${CLAUDE_PLUGIN_ROOT} with no fallback at all.
#
# The same class sat one layer in: the hook SCRIPTS read
# "${CLAUDE_PLUGIN_ROOT}/scripts/*.py" and fell through to a silent no-op when
# it was unset — so even a correctly-wired manifest would have run guards that
# did nothing.
#
# These tests fail if either half comes back.

set -uo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PLUGIN="$REPO_ROOT/plugins/mycelium"
HOOKS="$PLUGIN/hooks"
source "$(dirname "${BASH_SOURCE[0]}")/_assert.sh"

# House idiom on purpose. An earlier draft used a local `check` wrapper, and
# check_negative_control.py correctly reported this suite as "tested only
# passing" — its scan looks for assert_eq "$rc" "1" and similar, and a custom
# wrapper hides the failure direction from it. Conforming the test was the fix;
# widening the guard to recognise my wrapper would have been the fail-open.
ok()   { assert_eq "1" "1" "$1"; }
bad()  { assert_eq "0" "1" "$1"; }
check(){ assert_eq "$2" "$3" "$1"; }

echo "plugin-root resolution"
echo "======================================================"

# --- 1. No shipped artifact may carry a guessed install path. --------------
hits="$(grep -rl 'plugins/cache/mycelium-plugin' "$PLUGIN" 2>/dev/null \
        | grep -v 'install-runtime-hooks.sh' | grep -v 'provision-skills.sh' || true)"
check "no shipped file hardcodes the old cache path" "${hits:-none}" "none"

# The two exempt files may mention it ONLY in prose explaining its removal.
for f in "$HOOKS/install-runtime-hooks.sh" "$PLUGIN/integrations/opencode/provision-skills.sh"; do
  code_hits="$(grep -n 'plugins/cache/mycelium-plugin' "$f" | grep -v '^\s*[0-9]*:\s*#' || true)"
  check "$(basename "$f") mentions the old path only in comments" "${code_hits:-none}" "none"
done

# --- 2. The runtime manifests must be templates, not paths. ----------------
for m in hooks.codex.json hooks.cursor.json; do
  n_ph="$(grep -c '__MYCELIUM_PLUGIN_ROOT__' "$HOOKS/$m" || true)"
  n_env="$(grep -c 'CLAUDE_PLUGIN_ROOT' "$HOOKS/$m" || true)"
  [ "$n_ph" -gt 0 ] && ok "$m uses the placeholder ($n_ph sites)" || bad "$m has no placeholder"
  check "$m carries no CLAUDE_PLUGIN_ROOT" "$n_env" "0"
done

# hooks.json is the Claude Code surface, where the variable IS set. It must
# keep using it — asserting the opposite would be the mirror-image mistake.
n_cc="$(grep -c 'CLAUDE_PLUGIN_ROOT' "$HOOKS/hooks.json" || true)"
[ "$n_cc" -gt 0 ] && ok "hooks.json still uses CLAUDE_PLUGIN_ROOT ($n_cc sites)" \
                  || bad "hooks.json lost its CLAUDE_PLUGIN_ROOT references"

# --- 3. The installer must REFUSE to write an unwired manifest. ------------
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/fake/hooks"
cp "$HOOKS/hooks.cursor.json" "$tmp/fake/hooks/"     # manifest present, scripts absent
mkdir -p "$tmp/proj" "$tmp/good"   # project roots must exist; else the installer
                                   # refuses for THAT reason and hides the real check
out="$(CLAUDE_PLUGIN_ROOT="$tmp/fake" bash "$HOOKS/install-runtime-hooks.sh" cursor "$tmp/proj" 2>&1)"; rc=$?
assert_eq "$rc" "1" "refuses a root whose hook scripts are missing"
case "$out" in *"do not exist"*) ok "says which scripts are missing" ;;
               *) bad "error text does not name the missing scripts: $out" ;; esac
[ -f "$tmp/proj/.cursor/hooks.json" ] && bad "wrote a manifest it could not verify" \
                                      || ok "wrote nothing on refusal"

# --- 4. A real generate must substitute and verify. ------------------------
out="$(env -u CLAUDE_PLUGIN_ROOT bash "$HOOKS/install-runtime-hooks.sh" cursor "$tmp/good" 2>&1)"; rc=$?
check "generates from self-location with no env vars" "$rc" "0"
if [ -f "$tmp/good/.cursor/hooks.json" ]; then
  grep -q '__MYCELIUM_PLUGIN_ROOT__' "$tmp/good/.cursor/hooks.json" \
    && bad "generated manifest still contains the placeholder" \
    || ok "generated manifest has no placeholder left"
  grep -q "$PLUGIN/hooks/gate.sh" "$tmp/good/.cursor/hooks.json" \
    && ok "generated manifest carries the real absolute path" \
    || bad "generated manifest lacks the resolved path"
else
  bad "no manifest generated"
fi

# --- 5. Hook scripts must self-locate, not depend on the env var. ---------
# The load-bearing one: a guard invoked with NO environment at all must still
# find its helper. Before v0.88.0 this produced empty output and exit 0 — the
# silent no-op that reads identically to "nothing to warn about".
payload='{"tool_name":"Write","tool_input":{"file_path":"/Users/x/proj/.claude/canvas/user-needs.yml","content":"So his signal has nowhere to go, and that is the finding."}}'
got="$(printf '%s' "$payload" | env -i PATH="$PATH" bash "$HOOKS/absence-claim-guard.sh" 2>&1)"
case "$got" in *"ABSENCE-CLAIM WARNING"*) ok "guard fires with zero env vars set" ;;
               *) bad "guard silent with no env vars — the fail-open is back" ;; esac

for s in absence-claim-guard ci-signal autonomous-evidence-guard shell-safety-guard \
         scope-gate stop-check framework-guard; do
  grep -q '_mycelium_self' "$HOOKS/$s.sh" && ok "$s.sh self-locates" \
                                          || bad "$s.sh has no self-location block"
done

echo "------------------------------------------------------"
report
