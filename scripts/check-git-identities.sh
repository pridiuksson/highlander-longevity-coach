#!/usr/bin/env bash
# check-git-identities.sh — who is attached to this history, and is any of it personal?
#
# WHY THIS EXISTS, AND WHY NOTHING ELSE COVERS IT
# `leak-scan.sh` drops `Author:` / `Commit:` / `Date:` / `Merge:` lines when it splits `git log -p`
# into per-file pseudo-diffs, because those lines are metadata rather than content:
#
#     /^(Author|Date|Commit|Merge):/ { next }
#
# The consequence is that a personal address in the *authorship* of a commit is invisible to every
# pattern in the denylist. Verified both ways: the address `someone@example.com` inside a file is
# reported as `contact-email`, and the same address on a commit's author line reports a clean PASS.
# No pattern can ever fire on it, because by the time patterns run the line is gone.
#
# That makes this the only mechanism that sees authorship, and authorship is the one thing that
# cannot be edited after publication: every commit carries it forever. Run this before the repo
# becomes public, and before writing a release tag.
#
# Usage:
#   check-git-identities.sh [--repo DIR]
#
# Exit: 0 every identity is a bot or a noreply address | 1 at least one is not | 2 not a repo

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="."
while [ $# -gt 0 ]; do
  case "$1" in
    --repo) REPO="${2:-}"; shift 2;;
    -h|--help) sed -n '2,20p' "$0"; exit 0;;
    *) echo "unknown option: $1" >&2; exit 2;;
  esac
done

# Identities that are deliberately public and carry no personal address:
#   - GitHub's own merges (noreply@github.com)
#   - the noreply addresses GitHub assigns to accounts, which exist precisely so a real address
#     never has to appear in a commit
#   - the agent's own account on the box that authored these commits
#
# Anything else is a decision, not an accident. Add it here ONLY with a comment saying why it is
# safe to publish forever.
ALLOW='^GitHub <noreply@github\.com>$'
ALLOW="$ALLOW"'|^[^<]*<[^@>]*@users\.noreply\.github\.com>$'
ALLOW="$ALLOW"'|^Hermes <hermes@lightsail>$'

if ! git -C "$REPO" rev-parse --git-dir >/dev/null 2>&1; then
  echo "error: not a git repository: $REPO" >&2
  exit 2
fi

IDS=$(git -C "$REPO" log --all --format='%an <%ae>%n%cn <%ce>' 2>/dev/null | sort -u | sed '/^[[:space:]]*$/d')
if [ -z "$IDS" ]; then
  echo "error: no identities found in $REPO — is there any history?" >&2
  exit 2
fi

BAD=$(printf '%s\n' "$IDS" | grep -vE "$ALLOW" || true)
TOTAL=$(printf '%s\n' "$IDS" | wc -l | tr -d ' ')

if [ -n "$BAD" ]; then
  COUNT=$(printf '%s\n' "$BAD" | wc -l | tr -d ' ')
  echo "GIT IDENTITY HITS ($COUNT of $TOTAL):"
  printf '%s\n' "$BAD" | sed 's/^/  /'
  echo
  echo "These are attached to every commit and cannot be edited after publication. The content gate"
  echo "cannot see them: it drops Author:/Commit: lines when splitting history into per-file diffs,"
  echo "so no pattern in leak-patterns.tsv can fire on one. This check is the only thing that looks."
  echo
  echo "Two ways to resolve, and both are deliberate:"
  echo "  1. Rewrite the history to a noreply address — cheap now, disruptive once the repo is"
  echo "     public and branches are merged."
  echo "  2. Add the identity to ALLOW at the top of this file, with a comment saying why it is"
  echo "     safe to publish forever."
  exit 1
fi

echo "OK: all $TOTAL author/committer identit(ies) in history are bot or noreply addresses"
exit 0
