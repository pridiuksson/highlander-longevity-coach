#!/usr/bin/env bash
# peer-review.sh — Run a peer-review prompt via command-code.
# Pass your complete prompt — the script is a dumb pipe to an external LLM.
#
# Usage:
#   scripts/peer-review.sh "[skill-dir]" "<prompt>"
#   scripts/peer-review.sh "<prompt>"
#   echo "<prompt>" | scripts/peer-review.sh
#
# Exit codes: 0 success | 1 no prompt or CLI failed | 2 no CLI found

set -eo pipefail

# Source shell profiles to pick up nvm/fnm/volta/homebrew PATH additions
# Disable set -e temporarily to avoid profile script errors killing us
set +e
for profile in ~/.bashrc ~/.bash_profile ~/.zshrc ~/.zprofile ~/.profile; do
  [[ -f "$profile" ]] && source "$profile" 2>/dev/null
done
set -e

# If $1 is an existing directory (e.g. passed from ${AGENTS_SKILL_DIR}), consume it
if [[ -n "${1:-}" && -d "$1" ]]; then
  shift
fi

# cd to project root so CLI sees CLAUDE.md / AGENTS.md, settings, and project files
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$PROJECT_ROOT" || { echo "Error: Failed to cd to project root" >&2; exit 1; }

PROMPT="${1:-}"
if [[ -z "$PROMPT" ]]; then PROMPT=$(cat); fi
if [[ -z "$PROMPT" ]]; then echo "Usage: peer-review.sh \"<prompt>\" or pipe via stdin" >&2; exit 1; fi

if ! command -v command-code &>/dev/null; then
  echo "Error: command-code not found." >&2
  exit 2
fi

# NOTE: --tools-all is required. A headless (-p) run otherwise WITHHOLDS tools, so the peer
# only sees an empty workspace, cannot read the files it was asked to review, and answers
# "Shell is blocked in this session" (observed 2026-09-20). Interactive runs get the project's
# .commandcode/settings.json permissions instead, which is why the omission went unnoticed.
# NOTE: do not pass -m/--model here. The user controls the model via command-code's
# configured default (e.g. `command-code` -> /model). Adding -m would override that.
set +e
OUTPUT=$(command-code -p "$PROMPT" --max-turns 30 --skip-onboarding --tools-all -t </dev/null 2>/dev/null)
EC=$?
set -e

if [[ $EC -eq 0 && -n "$OUTPUT" ]]; then
  printf '%s\n' "$OUTPUT"
  exit 0
elif [[ $EC -eq 8 && -n "$OUTPUT" ]]; then
  echo "Warning: hit max turns limit (partial response)" >&2
  printf '%s\n' "$OUTPUT"
  exit 0
fi

exit 1
