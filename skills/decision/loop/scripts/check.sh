#!/usr/bin/env bash
# Loop skill checker — independent verification via external CLI.
#
# CLI chain (harmonized across all deliberation skills):
#   1. command-code (primary)
#   2. agy (fallback)
#   3. mimo (fallback)
#   4. Exit 3 → parent must manually verify
#
# Usage: check.sh "<desired state>" "<artifact1> <artifact2>" "<test command>"
set -uo pipefail
for p in ~/.bashrc ~/.bash_profile ~/.zshrc ~/.profile; do [[ -f "$p" ]] && source "$p" 2>/dev/null; done

DESIRED="${1:?Usage: check.sh DESIRED ARTIFACTS [TEST_CMD]}"
ARTIFACTS="${2:-}"
TEST_CMD="${3:-}"

PROMPT="You are an independent verifier. Do NOT trust the maker's claims — verify yourself.

DESIRED: $DESIRED
ARTIFACTS: $ARTIFACTS"

if [[ -n "$TEST_CMD" ]]; then
  PROMPT="$PROMPT
TEST COMMAND TO RUN: $TEST_CMD
Run the test command and include results in your evidence."
fi

PROMPT="$PROMPT

For each artifact: read it, verify it exists and meets the desired state.
For non-code: check requirements explicitly (line count, completeness, accuracy).

Output ONLY:
STATUS: converged|not-converged|blocked
EVIDENCE: <what you verified and how>
GAPS: <what's still missing, if anything>"

TMPFILE=$(mktemp)
trap 'rm -f "$TMPFILE"' EXIT
printf '%s\n' "$PROMPT" > "$TMPFILE"

# ── CLI routing (harmonized pattern across peer-review, grill, deliberate) ──

try_cli() {
    local cli="$1"; shift
    local prompt_file="$1"; shift

    case "$cli" in
        command-code)
            timeout 120 command-code -p "$(cat "$prompt_file")" --skip-onboarding -t </dev/null 2>/dev/null
            ;;
        agy)
            timeout 120 agy -p "$(cat "$prompt_file")" --dangerously-skip-permissions --print-timeout 120s </dev/null 2>/dev/null
            ;;
        mimo)
            timeout 120 mimo run "$(cat "$prompt_file")" </dev/null 2>/dev/null
            ;;
        *)
            return 1
            ;;
    esac
}

for CLI in command-code agy mimo; do
    if ! command -v "$CLI" &>/dev/null; then
        continue
    fi

    RESULT=$(try_cli "$CLI" "$TMPFILE")
    RC=$?

    if [ $RC -eq 0 ] && [ -n "$RESULT" ]; then
        echo "$RESULT"
        exit 0
    fi
done

echo "STATUS: blocked" >&2
echo "EVIDENCE: No checker CLI found (tried command-code, agy, mimo)" >&2
echo "GAPS: Cannot independently verify without checker — parent must verify manually" >&2
exit 3
