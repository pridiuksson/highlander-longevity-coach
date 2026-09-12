#!/usr/bin/env bash
# leak-scan.sh — identity / PII gate for the highlander-longevity-coach publish.
# Secrets are delegated to gitleaks; this script owns identity, path and health patterns.
#
# Usage:
#   leak-scan.sh [options] <dir|->      scan a directory, or stdin (`git log -p | leak-scan.sh -`)
#   leak-scan.sh --expect FILE <dir>    fixture mode: assert every expected hit is present
#
# Options:
#   -p, --patterns FILE   pattern file (default: <script_dir>/leak-patterns.tsv)
#       --no-gitleaks     skip the gitleaks pass
#       --quiet           summary only
#
# Exit: 0 clean | 1 hits found / expectation failed | 2 usage or setup error
#
# Path-scoped allowlist: the public repo owner handle is legitimate ONLY in hand-written
# scaffolding (README / ONBOARDING / CONTRIBUTING / LICENSE / .github/**) and is flagged
# anywhere inside skills/** or Profile/**.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATTERNS="$SCRIPT_DIR/leak-patterns.tsv"
TARGET=""
EXPECT=""
USE_GITLEAKS=1
QUIET=0

while [ $# -gt 0 ]; do
  case "$1" in
    -p|--patterns) PATTERNS="${2:-}"; shift 2;;
    --expect)      EXPECT="${2:-}"; shift 2;;
    --no-gitleaks) USE_GITLEAKS=0; shift;;
    --quiet)       QUIET=1; shift;;
    -h|--help)     sed -n '2,20p' "$0"; exit 0;;
    -)             TARGET="$1"; shift;;
    -*)            echo "unknown option: $1" >&2; exit 2;;
    *)             TARGET="$1"; shift;;
  esac
done

[ -n "$TARGET" ] || { echo "usage: leak-scan.sh [options] <dir|->" >&2; exit 2; }
[ -f "$PATTERNS" ] || { echo "pattern file not found: $PATTERNS" >&2; exit 2; }

# Commit messages are scanned as a pseudo-path. The committer identity is the deliberately
# public noreply handle, so the owner handle is allowed there but nothing else is relaxed.
OWNER_ALLOW='(^|/)(README|ONBOARDING|CONTRIBUTING)\.md$|(^|/)LICENSE$|(^|/)\.github/|^COMMIT_MSG$'
# Substrings that make a match benign (public, non-identifying addresses).
GLOBAL_ALLOW='noreply@|users\.noreply\.github\.com|git@github\.com|example\.com|@example\.org'

WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
HITS="$WORK/hits.tsv"; : > "$HITS"

if [ "$TARGET" = "-" ]; then
  STDIN_MODE=1
  SCAN_ROOT="$WORK"; cat > "$WORK/stream.txt"
  # Split a git diff into per-path pseudo-files so the path-scoped allowlists still apply.
  # Without this the owner handle in a README clone URL is indistinguishable from one in a
  # skill body, and history scanning produces false positives (or needs the allowlist off).
  mkdir -p "$WORK/diff"
  awk -v dir="$WORK/diff" -v map="$WORK/map.tsv" '
    /^commit / { n++; out = dir "/commit" n ".txt"; printf "%s\t%s\n", out, "COMMIT_MSG" >> map; next }
    /^(Author|Date|Commit|Merge):/ { next }
    /^diff --git / {
      n++
      p = $NF; sub(/^b\//, "", p)
      printf "%s\t%s\n", dir "/d" n ".txt", p >> map
      out = dir "/d" n ".txt"; next
    }
    { if (out != "") print >> out }
  ' "$WORK/stream.txt"
  mapfile -t FILES < <(find "$WORK/diff" -type f | sort)
else
  [ -d "$TARGET" ] || { echo "not a directory: $TARGET" >&2; exit 2; }
  STDIN_MODE=0
  SCAN_ROOT="$TARGET"
  # Self-exclusion: the pattern file and the scanner legitimately contain the denylisted
  # tokens (they ARE the denylist). Without this, a repo shipping the gate can never pass
  # its own CI. Matched by basename so it also works when scanning a COPY of the tree.
  # A .leakignore at the scan root adds further opt-outs.
  PBASE="$(basename "$PATTERNS")"
  SBASE="$(basename "${BASH_SOURCE[0]}")"
  find "$TARGET" -type f -not -path '*/.git/*' -not -path '*/__pycache__/*' -not -name '*.pyc' > "$WORK/all.txt"
  grep -vE "/(${PBASE}|${SBASE})$" "$WORK/all.txt" > "$WORK/f1.txt" || true
  if [ -f "$TARGET/.leakignore" ]; then
    grep -vF -f "$TARGET/.leakignore" "$WORK/f1.txt" > "$WORK/f2.txt" || true
  else
    cp "$WORK/f1.txt" "$WORK/f2.txt"
  fi
  mapfile -t FILES < <(sort "$WORK/f2.txt")
  # Symlinks are not publishable content and are invisible to `find -type f`, so the pattern
  # pass would never see them. Flag them explicitly rather than letting them through.
  while IFS= read -r l; do
    [ -n "$l" ] && printf 'symlink\t%s\t0\t%s\n' "$l" "symlink (must not be published)" >> "$HITS"
  done < <(find "$TARGET" -type l -not -path '*/.git/*' 2>/dev/null)
fi

declare -A FILEPATH
if [ -f "$WORK/map.tsv" ]; then
  while IFS=$'\t' read -r tf orig; do FILEPATH["$tf"]="$orig"; done < "$WORK/map.tsv"
fi

# ---- identity / path / health pass -----------------------------------------
while IFS=$'\t' read -r name ere; do
  case "$name" in ''|\#*) continue;; esac
  [ -n "${ere:-}" ] || continue
  for f in "${FILES[@]:-}"; do
    [ -f "$f" ] || continue
    dpath="${FILEPATH[$f]:-$f}"          # original path (stdin mode); real path otherwise
    grep -Iq . "$f" 2>/dev/null || continue          # skip binaries
    while IFS= read -r hit; do
      [ -n "$hit" ] || continue
      line="${hit%%:*}"; content="${hit#*:}"
      # The benign-address allowlist applies ONLY to the email pattern. Applying it to every
      # pattern meant any line containing `git@github.com` exempted itself from ALL checks
      # (e.g. `git clone git@github.com:x  # Olle 68 kg` passed).
      if [ "$name" = "contact-email" ]; then
        printf '%s' "$content" | grep -qE "$GLOBAL_ALLOW" && continue
      fi
      if [ "$name" = "owner-handle" ]; then
        printf '%s' "$dpath" | grep -qE "$OWNER_ALLOW" && continue
      fi
      if [ "$name" = "identity-name" ]; then
        # The three template names (Olle/Maria/Els) are intentional and public — they label the
        # scaffolds, and the docs have to be able to name them. Allowed only inside Profile/ or in
        # hand-written scaffolding; matched on the matched TEXT, so any other identity token, or
        # the same name inside a skill body, is still a hit.
        if printf '%s' "$dpath" | grep -qE '(^|/)Profile/' || printf '%s' "$dpath" | grep -qE "$OWNER_ALLOW"; then
          m=$(printf '%s' "$content" | grep -oP "$ere" | head -1)
          case "$m" in Olle|Maria|Els) continue;; esac
        fi
      fi
      printf '%s\t%s\t%s\t%s\n' "$name" "$dpath" "$line" "$content" >> "$HITS"
    done < <(grep -nP "$ere" "$f" 2>/dev/null)
  done
done < "$PATTERNS"

# ---- secrets pass ----------------------------------------------------------
GITLEAKS_RC=0
if [ "$USE_GITLEAKS" -eq 1 ] && [ "$STDIN_MODE" -eq 0 ]; then
  if command -v gitleaks >/dev/null 2>&1; then
    gitleaks detect --source "$SCAN_ROOT" --no-banner --redact --exit-code 1 >"$WORK/gitleaks.txt" 2>&1
    GITLEAKS_RC=$?
    if [ "$GITLEAKS_RC" -ne 0 ] && [ -s "$WORK/gitleaks.txt" ]; then
      grep -E 'Finding:|Secret:|File:' "$WORK/gitleaks.txt" >> "$HITS" 2>/dev/null || true
    fi
  else
    echo "warn: gitleaks not found — secrets pass SKIPPED" >&2
  fi
fi

# ---- report ----------------------------------------------------------------
NHITS=$(wc -l < "$HITS" | tr -d ' ')
if [ "$QUIET" -eq 0 ] && [ "$NHITS" -gt 0 ]; then
  echo "LEAK HITS ($NHITS) — by pattern:"
  awk -F'\t' '{c[$1]++} END{for (k in c) printf "  %-18s %s\n", k, c[k]}' "$HITS" | sort -k2 -rn
  echo "  --- locations (first 80 of $NHITS) ---"
  awk -F'\t' '{printf "  [%s] %s:%s\n", $1, $2, $3}' "$HITS" | sort -u | head -80
  [ "$NHITS" -gt 80 ] && echo "  … $((NHITS-80)) more"
fi

if [ -n "$EXPECT" ]; then
  [ -f "$EXPECT" ] || { echo "expect file not found: $EXPECT" >&2; exit 2; }
  MISS=0
  while IFS=$'\t' read -r ename esub; do
    case "$ename" in ''|\#*) continue;; esac
    if awk -F'\t' -v n="$ename" -v s="${esub:-}" '$1==n && (s=="" || index($2,s)>0){found=1} END{exit !found}' "$HITS"; then
      [ "$QUIET" -eq 0 ] && echo "  ok   expected hit found: $ename ${esub:+($esub)}"
    else
      echo "  MISS expected hit not found: $ename ${esub:+($esub)}"; MISS=1
    fi
  done < "$EXPECT"
  if [ "$MISS" -ne 0 ]; then echo "FAIL: fixture expectation not met"; exit 1; fi
  echo "OK: fixture — all expected hits found ($NHITS total)"
fi

if [ "$NHITS" -gt 0 ] || [ "$GITLEAKS_RC" -ne 0 ]; then
  echo "FAIL: $NHITS identity/path/health hit(s)${GITLEAKS_RC:+, gitleaks rc=$GITLEAKS_RC}"
  exit 1
fi
echo "PASS: no identity/path/health hits${USE_GITLEAKS:+, gitleaks clean}"
exit 0
