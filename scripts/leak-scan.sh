#!/usr/bin/env bash
# leak-scan.sh — identity / PII gate for the highlander-longevity-coach publish.
# Secrets are delegated to gitleaks; this script owns identity, path and health patterns.
#
# Usage:
#   leak-scan.sh [options] <dir|->      scan a directory, or stdin (`git log -p | leak-scan.sh -`)
#   leak-scan.sh --expect FILE <dir>    fixture mode: assert every expected hit is present
#
# Options:
#   -p, --patterns FILE   shape patterns (default: <script_dir>/leak-patterns.tsv)
#       --patterns-extra FILE
#                         value patterns: the identifiers themselves. MUST live outside the
#                         scanned tree — an overlay inside it is enumerated by `find` and matched
#                         by its own patterns. Defaults to $LEAK_PATTERNS_EXTRA, else
#                         ~/.config/leak/patterns.tsv when that file exists.
#       --no-gitleaks     skip the gitleaks pass
#       --quiet           summary only
#
# Two layers, different contracts:
#   shape layer   (tracked)      no config, no secret. The merge gate: findings fail the run.
#   value layer   (out-of-tree)  the real identifiers. ADDITIVE: when absent the run still
#                                passes, but the verdict prints NOT-CONFIGURED so a pass is
#                                never read as coverage that does not exist. There is
#                                deliberately no flag that silences that state.
#
# Exit: 0 clean | 1 hits found / expectation failed | 2 usage or setup error
#
# Path-scoped allowlist: the public repo owner handle is legitimate ONLY in hand-written
# scaffolding (README / ONBOARDING / CONTRIBUTING / LICENSE / .github/**) and is flagged
# anywhere inside skills/** or Profile/**.

set -uo pipefail

# ---- PCRE engine ------------------------------------------------------------
# The pattern dialect is PCRE (inline flags like (?i)). GNU grep's -P is the natural
# engine, but the stock grep on macOS is BSD grep, which has no -P AT ALL: it errors on
# every pattern, and where that error was swallowed (the match loop below) the scan
# matched nothing while still printing PASS. So the engine is chosen, not assumed:
# GNU grep when it is really there, else perl — which ships with macOS and speaks the
# same dialect. Neither means the gate cannot run honestly, so that is a hard error.
if printf 'pcre-probe' | grep -qP 'pcre-probe' 2>/dev/null; then
  PCRE_ENGINE="grep"
elif command -v perl >/dev/null 2>&1; then
  PCRE_ENGINE="perl"
else
  echo "error: no PCRE-capable engine — this gate needs GNU grep (-P) or perl." >&2
  echo "       On macOS the stock /usr/bin/grep is BSD grep, which has no -P; install" >&2
  echo "       GNU grep (brew install grep, then put it ahead of /usr/bin in PATH) or" >&2
  echo "       perl, and re-run. Guessing at patterns here would print a false verdict." >&2
  exit 2
fi

# Compile check: exit 0 iff the regex compiles under the chosen engine. grep exits 2 when
# it cannot compile (0 and 1 both mean it did); perl dies on an invalid qr and is mapped
# to the same convention.
pcre_compiles() {
  case "$PCRE_ENGINE" in
    grep) grep -qP -e "$1" /dev/null 2>/dev/null; [ "$?" -le 1 ];;
    perl) perl -e 'exit(eval { qr/$ARGV[0]/ } ? 0 : 2)' "$1" 2>/dev/null;;
  esac
}

# Line matches in grep -nP -e RE FILE format ("line:content"), newline-terminated like
# grep — files whose last line has no newline would otherwise drop that line in the
# `while read` loop that consumes this.
pcre_lines() {
  case "$PCRE_ENGINE" in
    grep) grep -nP -e "$1" "${@:2}";;
    perl) perl -ne 'BEGIN { $re = eval { qr/$ARGV[0]/ } or exit 2; shift } s/\n\z//; print "$.:$_\n" if /$re/' "$1" "${@:2}";;
  esac
}

# Match-only output, one match per line (grep -oP). Reads files or stdin, like grep.
pcre_matches() {
  case "$PCRE_ENGINE" in
    grep) grep -oP -e "$1" "${@:2}";;
    perl) perl -ne 'BEGIN { $re = eval { qr/$ARGV[0]/ } or exit 2; shift } while (/$re/g) { my $m = $&; print "$m\n" unless $m eq ""; last if $m eq ""; }' "$1" "${@:2}";;
  esac
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATTERNS="$SCRIPT_DIR/leak-patterns.tsv"
PATTERNS_EXTRA="${LEAK_PATTERNS_EXTRA:-}"
TARGET=""
EXPECT=""
USE_GITLEAKS=1
QUIET=0
EXCLUDED=0

while [ $# -gt 0 ]; do
  case "$1" in
    -p|--patterns) PATTERNS="${2:-}"; shift 2;;
    --patterns-extra) PATTERNS_EXTRA="${2:-}"; shift 2;;
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

# A pattern file is only useful if every line parses AND every regex compiles. grep reports an
# invalid regex as an error and then matches nothing, so an uncompilable entry is silently inert —
# indistinguishable from a pattern that simply has no hits. Both are caught here instead.
validate_pattern_file() {
  local _file="$1" _pn _pe _px _bad=""
  while IFS=$'\t' read -r _pn _pe _px; do
    # Leading whitespace is stripped before the comment test so an INDENTED comment is a comment
    # for the parser as well as for the counter — otherwise a legitimately-formatted file fails.
    _pn="${_pn#"${_pn%%[![:space:]]*}"}"
    case "$_pn" in ''|\#*) continue;; esac
    if [ -z "${_pe:-}" ]; then _bad="${_bad:+$_bad; }entry '$_pn' has no regex"; continue; fi
    if [ -n "${_px:-}" ]; then _bad="${_bad:+$_bad; }entry '$_pn' has too many fields (a stray tab?)"; continue; fi
    # The compile check goes through the engine chosen above, so a regex the ENGINE cannot
    # compile is caught here regardless of which engine that is.
    if ! pcre_compiles "$_pe"; then _bad="${_bad:+$_bad; }entry '$_pn' has an invalid regex"; continue; fi
  done < "$_file"
  [ -z "$_bad" ] && return 0
  echo "error: $_file: $_bad" >&2
  echo "       A line that does not parse, or a regex that does not compile, matches nothing —" >&2
  echo "       which is indistinguishable from a pattern that has no hits." >&2
  return 2
}

validate_pattern_file "$PATTERNS" || exit 2

# ---- value layer (out-of-tree) ---------------------------------------------
# The identifiers this repo must not publish cannot live in a tracked file: the denylist would
# BE the leak. They live outside the tree and are loaded by path. An explicit path (flag or
# $LEAK_PATTERNS_EXTRA) wins; otherwise a box that has already been set up is picked up
# automatically, so the layer cannot be silently forgotten by whoever configured it.
DEFAULT_EXTRA="$HOME/.config/leak/patterns.tsv"
if [ -z "$PATTERNS_EXTRA" ] && [ -f "$DEFAULT_EXTRA" ]; then PATTERNS_EXTRA="$DEFAULT_EXTRA"; fi

PATTERN_FILES=("$PATTERNS")
VALUE_STATE="NOT-CONFIGURED (0 value patterns applied)"
if [ -n "$PATTERNS_EXTRA" ]; then
  [ -f "$PATTERNS_EXTRA" ] || {
    echo "error: value-layer pattern file not found: $PATTERNS_EXTRA" >&2
    echo "       It was configured explicitly, so this is a broken setup rather than an absent" >&2
    echo "       layer, and a configured-but-missing value layer is a silent hole. Fix the path," >&2
    echo "       or unset LEAK_PATTERNS_EXTRA to run the shape layer alone." >&2
    exit 2
  }
  validate_pattern_file "$PATTERNS_EXTRA" || exit 2
  PATTERN_FILES+=("$PATTERNS_EXTRA")
  VC=$(grep -v '^[[:space:]]*#' "$PATTERNS_EXTRA" | grep -cv '^[[:space:]]*$' || true)
  VI=$(grep -v '^[[:space:]]*#' "$PATTERNS_EXTRA" | grep -c '<YOUR_' || true)
  # Three states, because "configured" alone conflates a working layer with two different kinds of
  # useless one. An overlay that was copied but never edited, or edited into something that matches
  # nothing, reports the SAME summary as real coverage — which is the failure this layer exists to
  # make impossible. The sentinel is the angle-bracket convention the example ships with, so an
  # unedited copy is caught; a silently wrong value cannot be, and is covered by review instead.
  if [ "${VC:-0}" -eq 0 ]; then
    VALUE_STATE="CONFIGURED BUT EMPTY (no patterns — nothing is checked)"
  elif [ "${VI:-0}" -gt 0 ]; then
    VALUE_STATE="CONFIGURED BUT INERT (${VI} of ${VC} still placeholders)"
  else
    VALUE_STATE="configured (${VC} pattern(s) applied)"
  fi
fi

# A pattern still containing a <YOUR_...> placeholder matches that literal string and
# nothing else, so the check it names is silently INERT. That is the same shape of bug as
# a secrets pass that never runs, so it is reported in the verdict rather than left for
# the reader to infer from a PASS.
INERT=0
for _pf in "${PATTERN_FILES[@]}"; do
  _n=$(grep -v '^[[:space:]]*#' "$_pf" 2>/dev/null | grep -c '<YOUR_' || true)
  INERT=$((INERT + ${_n:-0}))
done
INERT_NOTE=""
[ "$INERT" -gt 0 ] && INERT_NOTE="; WARNING: $INERT unreplaced pattern(s) are INERT"

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
  # The value layer must sit OUTSIDE the scanned tree. Inside it, `find` enumerates the file and
  # its own patterns match its own text, so it becomes a guaranteed self-hit — and both ways out
  # of that (a .leakignore line, or widening the self-exclusion below) are evasion surfaces.
  # Refusing outright is what keeps the exclusion list from growing.
  if [ -n "$PATTERNS_EXTRA" ]; then
    _root="$(cd "$TARGET" && pwd)"
    _extra="$(cd "$(dirname "$PATTERNS_EXTRA")" && pwd)/$(basename "$PATTERNS_EXTRA")"
    case "$_extra" in
      "$_root"/*) echo "error: value-layer patterns must live OUTSIDE the scanned tree: $_extra is inside $_root" >&2; exit 2;;
    esac
  fi

  # Self-exclusion: the pattern file and the scanner legitimately contain the denylisted
  # tokens (they ARE the denylist). Without this, a repo shipping the gate can never pass
  # its own CI.
  #
  # Anchored on the EXACT paths of the two files that legitimately contain the denylist. Not on
  # the bare basename, which hides ANY file with that name at ANY depth (so `docs/leak-patterns.tsv`
  # was invisible while CI's history step, which excludes the exact path, still excluded only the
  # real one — the two scans disagreeing about what they read). And not on `(^|/)scripts/<name>`
  # either, which would hide a relocated copy under e.g. `vendor/scripts/`. The count is reported
  # so the exclusions are visible rather than implied.
  # Strip ALL trailing slashes (a single ${x%/} leaves `repo/` from `repo//`, which would make the
  # exact-path exclusion miss and turn the pattern file into a self-hit). `/` survives as itself.
  _T="$TARGET"
  while [ "${_T%/}" != "$_T" ]; do _T="${_T%/}"; done
  [ -n "$_T" ] || _T="/"
  find "$_T" -type f -not -path '*/.git/*' -not -path '*/__pycache__/*' -not -name '*.pyc' > "$WORK/all.txt"
  EXCLUDED=$(grep -cxF -e "$_T/scripts/leak-patterns.tsv" -e "$_T/scripts/leak-scan.sh" "$WORK/all.txt" || true)
  EXCLUDED=${EXCLUDED:-0}
  grep -vxF -e "$_T/scripts/leak-patterns.tsv" -e "$_T/scripts/leak-scan.sh" "$WORK/all.txt" > "$WORK/f1.txt" || true
  if [ -f "$TARGET/.leakignore" ]; then
    grep -vF -f "$TARGET/.leakignore" "$WORK/f1.txt" > "$WORK/f2.txt" || true
  else
    cp "$WORK/f1.txt" "$WORK/f2.txt"
  fi
  mapfile -t FILES < <(sort "$WORK/f2.txt")
  # A verdict over zero files is a PASS that checked nothing — the same class of false green as an
  # inert pattern or a secrets pass that never ran, so it is refused rather than printed.
  if [ "${#FILES[@]}" -eq 0 ]; then
    echo "error: no files enumerated under $_T — the scan would pass over nothing." >&2
    exit 2
  fi
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
# Both layers run the same loop: the allowlists below key on the pattern NAME, so a value layer
# supplying `owner-handle` or `identity-name` inherits them without a second code path.
for _pf in "${PATTERN_FILES[@]}"; do
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
      if [ "$name" = "profile-path" ]; then
        # The three template profiles (Olle/Maria/Els) are public by design — they label the
        # scaffolds and the docs have to be able to name them — so a path resolving to one is
        # legitimate wherever it appears. The pattern matches the whole `profiles/<name>` path, so
        # the FINAL segment is what gets compared. Any other profile name is a hit: this repo's
        # profiles are person-named by convention, which is why the shape is worth having at all.
        #
        # EVERY match on the line must be a template name. Exempting the line on the strength of
        # its first match meant `profiles/olle … profiles/jane` was allowed wholesale, so a real
        # identifier sharing a line with a permitted one was never flagged.
        # Default is NOT allowed: the exemption must be earned by at least one real match, all of
        # which are template names. Starting from "allowed" meant a pattern yielding no non-empty
        # match exempted the line wholesale — the bypass, restored through a different door.
        _allow=0; _seen=0; _ok=1
        while IFS= read -r _m; do
          [ -n "$_m" ] || continue
          _seen=1
          _seg=$(printf '%s' "$_m" | sed -E 's#^.*/##' | tr '[:upper:]' '[:lower:]')
          case "$_seg" in olle|maria|els) ;; *) _ok=0;; esac
        done < <(printf '%s' "$content" | pcre_matches "$ere" 2>/dev/null)
        [ "$_seen" -eq 1 ] && [ "$_ok" -eq 1 ] && _allow=1
        [ "$_allow" -eq 1 ] && continue
      fi
      if [ "$name" = "identity-name" ]; then
        # Allowed only inside Profile/ or in hand-written scaffolding; matched on the matched TEXT,
        # so any other identity token, or the same name inside a skill body, is still a hit. As
        # above, one permitted match must not exempt the rest of the line.
        if printf '%s' "$dpath" | grep -qE '(^|/)Profile/' || printf '%s' "$dpath" | grep -qE "$OWNER_ALLOW"; then
          _allow=0; _seen=0; _ok=1
          while IFS= read -r _m; do
            [ -n "$_m" ] || continue
            _seen=1
            _seg=$(printf '%s' "$_m" | sed -E 's#^.*/##' | tr '[:upper:]' '[:lower:]')
            case "$_seg" in olle|maria|els) ;; *) _ok=0;; esac
          done < <(printf '%s' "$content" | pcre_matches "$ere" 2>/dev/null)
          [ "$_seen" -eq 1 ] && [ "$_ok" -eq 1 ] && _allow=1
          [ "$_allow" -eq 1 ] && continue
        fi
      fi
      printf '%s\t%s\t%s\t%s\n' "$name" "$dpath" "$line" "$content" >> "$HITS"
    done < <(pcre_lines "$ere" "$f" 2>/dev/null)
  done
done < "$_pf"
done

# ---- secrets pass ----------------------------------------------------------
# Fail CLOSED when the pass is enabled but unavailable. Reporting PASS while the
# secrets pass silently never ran is worse than reporting nothing: the docs quote
# this exit code as evidence that the tree is clean.
GITLEAKS_RC=0
GITLEAKS_STATE="skipped (stdin mode — diffs are not a secret surface)"
if [ "$USE_GITLEAKS" -eq 1 ] && [ "$STDIN_MODE" -eq 0 ]; then
  if command -v gitleaks >/dev/null 2>&1; then
    # --no-git is load-bearing: without it `gitleaks detect` walks the GIT HISTORY of the
    # source repo, not the working tree, so a "tree scan" was silently a second history
    # scan and files not yet committed were never checked. History is scanned separately
    # (see CONTRIBUTING.md and ci/leak-gate.yml).
    gitleaks detect --source "$SCAN_ROOT" --no-git --no-banner --redact --exit-code 1 >"$WORK/gitleaks.txt" 2>&1
    GITLEAKS_RC=$?
    if [ "$GITLEAKS_RC" -ne 0 ]; then
      GITLEAKS_STATE="FAILED (rc=$GITLEAKS_RC)"
      if [ -s "$WORK/gitleaks.txt" ]; then
        grep -E 'Finding:|Secret:|File:' "$WORK/gitleaks.txt" >> "$HITS" 2>/dev/null || true
      fi
    else
      GITLEAKS_STATE="clean"
    fi
  else
    echo "error: gitleaks not found, but the secrets pass is enabled." >&2
    echo "       install gitleaks (https://github.com/gitleaks/gitleaks), or re-run with" >&2
    echo "       --no-gitleaks to skip the pass EXPLICITLY. A PASS that never ran the" >&2
    echo "       secrets pass is not a clean tree, and this script will not claim it is." >&2
    exit 2
  fi
elif [ "$USE_GITLEAKS" -eq 0 ]; then
  GITLEAKS_STATE="disabled (--no-gitleaks)"
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

FIXTURE_OK=0
if [ -n "$EXPECT" ]; then
  [ -f "$EXPECT" ] || { echo "expect file not found: $EXPECT" >&2; exit 2; }
  MISS=0
  : > "$WORK/expected.tsv"
  while IFS=$'\t' read -r ename esub; do
    case "$ename" in ''|\#*) continue;; esac
    if awk -F'\t' -v n="$ename" -v s="${esub:-}" '$1==n && (s=="" || index($2,s)>0){found=1} END{exit !found}' "$HITS"; then
      awk -F'\t' -v n="$ename" -v s="${esub:-}" '$1==n && (s=="" || index($2,s)>0)' "$HITS" >> "$WORK/expected.tsv"
      [ "$QUIET" -eq 0 ] && echo "  ok   expected hit found: $ename ${esub:+($esub)}"
    else
      echo "  MISS expected hit not found: $ename ${esub:+($esub)}"; MISS=1
    fi
  done < "$EXPECT"
  if [ "$MISS" -ne 0 ]; then echo "FAIL: fixture expectation not met"; exit 1; fi
  # Every hit must be accounted for by the expect file. Asserting only *presence* meant a fixture
  # holding the expected hits PLUS a brand-new leak passed, which made the mode useless as a
  # regression test: it could not tell a clean fixture from a dirtier one.
  # A failed comparison must not read as "nothing unexpected", so the error is not swallowed.
  if ! comm -23 <(sort -u "$HITS") <(sort -u "$WORK/expected.tsv") > "$WORK/unexpected.txt" 2>"$WORK/comm.err"; then
    echo "FAIL: could not compare hits against the expect file:" >&2
    cat "$WORK/comm.err" >&2
    exit 1
  fi
  UNEXPECTED=$(wc -l < "$WORK/unexpected.txt" | tr -d ' ')
  if [ "${UNEXPECTED:-0}" -gt 0 ]; then
    echo "FAIL: $UNEXPECTED hit(s) not covered by the expect file:"
    head -10 "$WORK/unexpected.txt" | awk -F'\t' '{printf "  [%s] %s:%s\n", $1, $2, $3}'
    exit 1
  fi
  # An empty fixture asserts nothing; say so rather than reporting a vacuous success.
  if [ "$NHITS" -eq 0 ]; then
    echo "FAIL: fixture asserted nothing — no hits, so nothing was verified."
    exit 1
  fi
  # In fixture mode the hits ARE the assertion. Exiting 1 merely because hits were found made the
  # mode unable to report success at all, so a positive test could never pass and the fixture was
  # unusable for the one thing it exists to do.
  FIXTURE_OK=1
  echo "OK: fixture — all expected hits found, none unexpected ($NHITS total)"
fi

if [ "$INERT" -gt 0 ]; then
  echo "warn: $INERT pattern(s) still contain <YOUR_...> placeholders." >&2
  echo "      They match the literal placeholder text, so those checks are INERT — they" >&2
  echo "      cannot catch the identity/repo data they exist to catch." >&2
  echo "      value layer: $VALUE_STATE (file: ${PATTERNS_EXTRA:-none} — see CONTRIBUTING.md)." >&2
fi

# Only meaningful in directory mode. In stdin mode the exclusions are the caller's git pathspec
# and reporting a 0 here would read as "nothing was excluded" rather than "not applicable".
EXCL_NOTE=""
[ "$STDIN_MODE" -eq 0 ] && EXCL_NOTE="gate file(s) excluded: $EXCLUDED; "

if [ "$FIXTURE_OK" -eq 1 ]; then
  if [ "$GITLEAKS_RC" -ne 0 ]; then
    echo "FAIL: fixture matched, but the secrets pass did not; value layer: $VALUE_STATE$INERT_NOTE"
    exit 1
  fi
  echo "PASS: fixture — every expected hit present ($NHITS hit(s) are the assertion, not a failure); value layer: $VALUE_STATE; ${EXCL_NOTE}secrets pass: $GITLEAKS_STATE$INERT_NOTE"
  exit 0
fi
if [ "$NHITS" -gt 0 ] || [ "$GITLEAKS_RC" -ne 0 ]; then
  echo "FAIL: $NHITS identity/path/health hit(s); value layer: $VALUE_STATE; ${EXCL_NOTE}secrets pass: $GITLEAKS_STATE$INERT_NOTE"
  exit 1
fi
echo "PASS: no identity/path/health hits; value layer: $VALUE_STATE; ${EXCL_NOTE}secrets pass: $GITLEAKS_STATE$INERT_NOTE"
exit 0
