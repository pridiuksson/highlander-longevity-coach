#!/usr/bin/env bash
# Grill adversary runner — routes through an external LLM CLI for model independence.
#
# CLI chain (harmonized across all deliberation skills):
#   1. command-code (primary)
#   2. agy (fallback)
#   3. mimo (fallback)
#   4. Returns "NO_CLI_FOUND" (exit 3) → fall back to delegate_task
#
# Usage: grill-adversary.sh "<prompt>"

set -uo pipefail

# Source shell profiles to pick up PATH additions (mimo is only on PATH via
# ~/.bashrc — the Xiaomi installer does not symlink into /usr/local/bin).
for p in ~/.bashrc ~/.bash_profile ~/.zshrc ~/.profile; do [[ -f "$p" ]] && source "$p" 2>/dev/null; done

PROMPT="${1:-}"
if [ -z "$PROMPT" ]; then
    PROMPT=$(cat)
fi
if [ -z "$PROMPT" ]; then
    echo "Usage: grill-adversary.sh \"<prompt>\" or pipe a prompt via stdin" >&2
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
for CLI in command-code agy mimo; do
    if ! command -v "$CLI" &>/dev/null; then
        continue
    fi

    RESULT=$(try_cli "$CLI" "$TMPFILE")
    RC=$?

    if [ $RC -eq 0 ] && [ -n "$RESULT" ]; then
        echo "--- Adversary via $CLI ---"
        echo "$RESULT"
        exit 0
    fi
done

echo "NO_CLI_FOUND"
exit 3
