#!/usr/bin/env bash
# peer-review.sh — Run a peer-review prompt via the best available CLI.
# Dumb pipe: sends a prompt to an external LLM and returns its stdout.
#
# CLI chain (harmonized across all deliberation skills):
#   1. command-code (primary)
#   2. agy (fallback)
#   3. mimo (fallback)
#   4. Exit 3 → signals the agent to use a native delegate_task subagent
#
# Usage:
#   scripts/peer-review.sh "<prompt>"
#   echo "<prompt>" | scripts/peer-review.sh
#
# Override the workspace dir: PEER_REVIEW_WORKDIR=/path/to/repo peer-review.sh
#
# Exit codes: 0 success | 1 no prompt | 3 all CLIs failed (use delegate_task fallback)

set -uo pipefail

# Source shell profiles to pick up PATH additions (nvm/fnm/volta).
set +e
for profile in ~/.bashrc ~/.bash_profile ~/.zshrc ~/.zprofile ~/.profile; do
  [[ -f "$profile" ]] && source "$profile" 2>/dev/null
done
set -e

# cd to the workspace so CLIs with cwd-scoped file access can see user files.
WORKDIR="${PEER_REVIEW_WORKDIR:-$HOME}"
cd "$WORKDIR" || { echo "Error: Failed to cd to '$WORKDIR'" >&2; exit 1; }

PROMPT="${1:-}"
if [[ -z "$PROMPT" ]]; then PROMPT=$(cat); fi
if [[ -z "$PROMPT" ]]; then
  echo "Usage: peer-review.sh \"<prompt>\" or pipe a prompt via stdin" >&2
  exit 1
fi

TMPFILE=$(mktemp)
trap 'rm -f "$TMPFILE"' EXIT
printf '%s\n' "$PROMPT" > "$TMPFILE"

# ── CLI routing (harmonized pattern across peer-review, grill, deliberate) ──

try_cli() {
    local cli="$1"; shift
    local prompt_file="$1"; shift

    case "$cli" in
        command-code)
            timeout 180 command-code -p "$(cat "$prompt_file")" --skip-onboarding -t </dev/null 2>/dev/null
            ;;
        agy)
            timeout 180 agy -p "$(cat "$prompt_file")" --dangerously-skip-permissions --print-timeout 180s </dev/null 2>/dev/null
            ;;
        mimo)
            timeout 180 mimo run "$(cat "$prompt_file")" </dev/null 2>/dev/null
            ;;
        *)
            return 1
            ;;
    esac
}

# Try CLIs in priority order
# NOTE: set -e must be disabled during CLI calls — if a CLI returns non-zero
# (e.g., command-code after auto-update), set -e would abort the script before
# the fallback chain can try the next CLI. The entire fallback design depends
# on this.
set +e
for CLI in command-code agy mimo; do
    if ! command -v "$CLI" &>/dev/null; then
        continue
    fi

    OUTPUT=$(try_cli "$CLI" "$TMPFILE" 2>&1)
    EC=$?

    if [ $EC -eq 0 ] && [ -n "$OUTPUT" ]; then
        printf '%s\n' "$OUTPUT"
        exit 0
    fi
    echo "Warning: $CLI failed (exit $EC), trying next" >&2
done
set -e

# ── All CLIs failed → signal agent to use native subagent ─────────────────

echo "Error: All CLIs failed. Use native delegate_task subagent as fallback." >&2
exit 3
