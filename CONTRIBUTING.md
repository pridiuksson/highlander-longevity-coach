# Contributing

## The one rule

**Run the leak gate before you propose anything. A red gate means stop.**

```bash
./scripts/leak-scan.sh .              # the working tree
```

That checks the tree for identity, path and health patterns and delegates secrets to `gitleaks`.
**gitleaks is required, not optional:** if it is missing the scan exits `2` instead of printing a
PASS, because a pass that never ran the secrets check is not evidence of anything. Two things it
will tell you about itself rather than hide:

- the secrets pass covers the **working tree only**. `gitleaks detect` walks git history unless
  `--no-git` is passed, so history needs its own pass (below).
- the **value layer's** state, on every run.
- its need for a **writable temp dir**: the gate stages its work under `mktemp -d`. If your
  environment sandboxes processes behind a read-only default temp dir, the run dies at startup
  (`mktemp: mkdtemp failed … Operation not permitted`) — run the gate outside the sandbox rather
  than route around it, and do not count on a `TMPDIR` override surviving the sandbox.

### Two layers, and why the identifiers are not in the repo

The gate has two layers with different contracts.

| Layer | Where it lives | Contract |
|---|---|---|
| **Shape** | `scripts/leak-patterns.tsv`, tracked | The merge gate. No config, no secret, enforced in every clone and fork. A hit fails the run |
| **Value** | outside the tree, loaded by path | The identifiers themselves — your name, your handle. **Additive**: absent is a printed state, not a failure |

`scripts/leak-patterns.tsv` cannot name the identifiers it exists to catch: a denylist that names
your handle has itself leaked it, and it is the one file every reader opens. So the values live
outside the repository entirely:

```bash
mkdir -p ~/.config/leak
cp scripts/leak-patterns.local.example.tsv ~/.config/leak/patterns.tsv
$EDITOR ~/.config/leak/patterns.tsv          # fill in your name and your handle
./scripts/leak-scan.sh .                     # verdict: value layer: configured (2 pattern(s) applied)
```

The gate finds that path automatically; `--patterns-extra FILE` or `$LEAK_PATTERNS_EXTRA` points it
somewhere else. **Do not put it inside the repository.** The scan enumerates with `find`, not git, so
an in-tree overlay is enumerated and its own patterns match its own text — and the gate refuses to
run rather than grow an exclusion to cope with it, because every exclusion is an evasion surface.

There is deliberately **no flag that silences the value layer**. An absent layer prints
`value-layer: NOT-CONFIGURED (0 value patterns applied)`; a layer that is configured but still full
of placeholders prints `CONFIGURED BUT INERT`. Both are stated on every run, so a PASS is never read
as identity coverage that does not exist. `scripts/check-values-configured.sh` (wired into the
pre-commit hook and run in CI) fails only when the layer is *configured and useless* — never on
simple absence, which a contributor cannot fix and which is not their identity at stake.

A real name used as free prose cannot be caught by shape: no regex decides "is this a human name?"
without a dictionary that also matches places and products. That is the gap the value layer fills,
and the reason its absence is reported rather than ignored.

It does **not** read history, and a personal name in a commit message is public forever — so check
that separately, before you open a PR:

```bash
git log -p HEAD -- . \
  ':(exclude)scripts/leak-patterns.tsv' ':(exclude)scripts/leak-scan.sh' \
  | ./scripts/leak-scan.sh --no-gitleaks -
```

`HEAD`, not `--all`, and the difference matters. `--all` reaches every branch the clone knows about,
so one branch's content can fail another branch's build, and the same commit can pass or fail
depending only on what else existed at the time. A check whose answer changes when someone pushes to
an unrelated branch is not a check. Before a **release or a public flip**, scan everything on
purpose — that is the moment when every branch is your responsibility:

```bash
git log -p --all -- . \
  ':(exclude)scripts/leak-patterns.tsv' ':(exclude)scripts/leak-scan.sh' \
  | ./scripts/leak-scan.sh --no-gitleaks -
```

The two exclusions stop the gate flagging its own pattern file — which necessarily contains the
shapes it looks for — and its own example text. The scanner's own self-exclusion is anchored on
`scripts/<name>` rather than the bare basename, so a file with the same name elsewhere in the tree
is still scanned; every verdict prints how many files were excluded. `--no-gitleaks` because piping
raw patches through gitleaks is mostly noise; run the secrets pass over history directly instead.

Two more pre-push checks:

```bash
python3 scripts/validate-skills.py .            # frontmatter, unique names, refs, config keys,
                                               # token taxonomy, py_compile, doc consistency
gitleaks detect --source . --log-opts="--all"   # secrets, over every commit
```

And one that looks at something the scan above structurally cannot see:

```bash
./scripts/check-git-identities.sh              # who is attached to the commits
```

The history scan drops `Author:` / `Commit:` / `Date:` / `Merge:` lines when it splits `git log -p`
into per-file pseudo-diffs — they are metadata, not content — so a personal address in a commit's
*authorship* is invisible to every pattern in the denylist. The same address inside a file is a hit;
as an author line it is not, and no pattern can ever fire on one because by then the line is gone.

Authorship is also the one thing you cannot edit after publication: every commit carries it
forever. So this check is the only mechanism that sees it, and it is worth running before the
repository becomes public and before writing a release tag.

`validate-skills.py` is worth knowing in full, because it enforces the conventions on this page. It
also works against an **install root** — `python3 scripts/validate-skills.py --installed ~/.hermes` —
which is how you check a box for shadowed skill names.

**CI enforces the gate.** `.github/workflows/leak-gate.yml` runs on every push and pull request:
the tree scan (with its secrets pass), the skill validator, the HEAD-scoped identity scan (this ref
only, as above), and a full-history `gitleaks` pass. The pre-commit hook is a convenience and is bypassable with
`--no-verify`; CI is the version that actually enforces anything. The hook also needs the
pre-commit framework installed and wired in once — `pipx install pre-commit && pre-commit install`
— otherwise the committed config runs nowhere at all.

It is the only copy — edit the workflow in place. It once shipped inert as `ci/leak-gate.yml`
because activating a workflow needs a token with the `workflow` scope, and GitHub refuses to let a
token without it create or update anything under `.github/workflows/`. The automation that first
populated this repo did not hold that scope, which is also why the copy was removed once CI was
enabled for real: two copies drift.

## Privacy — the part that is not negotiable

Treat everything you commit as public. The repository is private today, but the intent is to
publish it, and git history is forever. Do not put personal health data into it, ever:

- not into a skill body, even as a "worked example"
- not into a fixture
- not into a commit message
- not into a branch name

Keep the *shape* of an example while discarding the values — but use the right kind of placeholder.
There are three, and `validate-skills.py` enforces the difference:

| Class | Example | Rule |
|---|---|---|
| **Substitution** | `<YOUR_HEALTH_DIR>`, `<USER>`, `<YOUR_BASELINE_DOC>` | **Never.** These read as an instruction to the reader but resolve to nothing at load time. A path the user owns belongs in `metadata.hermes.config` (below); a file inside the skill belongs to `${HERMES_SKILL_DIR}` |
| **Redaction** | `<value>`, `<YOUR_WEIGHT_KG>`, `<YOUR_RESTING_HR_BPM>` | Allowed, and visible on purpose — a measurement removed because it was a person's. **Never glued to a number or an arrow:** `<value>→<value>` is a broken expression, not a redaction. Excise the fragment so the sentence still says something true |
| **Syntax** | `<uuid>`, `<prompt>`, `<YYYYMMDDHHMMSS>` | Allowed. Metavariables in usage strings and filename patterns |

This table is the canonical vocabulary — point at it rather than restating the list in a skill,
because restated lists drift.

The three classes apply to **skills**. In a *profile* template they invert: `<USER>`, `<AGE>` and
`<CITY>` are fields the adopter fills in, and there is no config mechanism behind them — see
ONBOARDING step 7. Do not "fix" a profile by resolving its angle brackets for the reader.

Paths come from `config.yaml`, not from the reader doing find-and-replace on an installed skill. A
skill declares what it needs in its frontmatter, and Hermes injects the resolved values when the
skill loads:

```yaml
metadata:
  hermes:
    config:
      - key: health.health_dir
        description: Root of your health data (exports, SQLite DB, verified docs)
        default: "~/health"
```

**Declare every key the skill uses.** An undeclared key is never injected — the agent is left
guessing — and the validator fails the build if you forget one. Adopters set them explicitly with
`hermes config set skills.config.<key> <value>`; do not assume `hermes config migrate` will offer
them, because it does not.

## Layout

```
skills/<stage>/<name>/     one skill, self-contained
scripts/                   the leak gate, the validator, authorship + value-layer checks
Profile/                   profile templates
Box/                       provider cookbooks: stand up a coach box, agent-executed
.commandcode/              Command Code skill discovery
.github/workflows/         the leak gate in CI
```

Skills are grouped by the stage of the coaching loop they serve — `decision/`, `health/`,
`evidence/`, `nutrition/`, `planning/`, `proactive/`, `quality/` — plus `workflow/`, which holds the
contribution skills (`commit`, `create-pr`, `ticket`, `work`) and serves the repo rather than the
coaching loop.

**Skills never import across their own boundary.** Duplicate a small reference, or point at the
owning skill's path. Shared state is how two skills drift apart.

## Contributor profile

`Profile/Els/` is the contributor profile — it carries the same coaching loop as the others, plus
a contributor lane with the conventions above. It is a template: copy it, do not edit it in place.

## Changing a skill

The `workflow/` skills run this loop for you — `@ticket` to file the work, `@work` to execute an
issue end-to-end, `@commit` then `@create-pr` to ship. By hand:

1. Branch.
2. Edit **inside that skill's directory**. If a change is needed in two skills, make the case for
   the duplication or for a pointer — do not create a shared import.
3. Run the gate, plus any test the skill ships.
4. **One change, one reason.** In the commit, say what the change is *for*, not just what it does.
5. Open a PR.

## Changing a profile template

Templates are **scaffolds, not redactions** — the content is rewritten to be generic, so there is
nothing underneath to leak. Keep it that way: do not commit a template derived from a real
person's profile without that person's consent, and do not commit a redacted dump. A shorter
honest scaffold beats a longer masked one.
