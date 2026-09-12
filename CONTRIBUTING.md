# Contributing

## The one rule

**Run the leak gate before you propose anything. A red gate means stop.**

```bash
./scripts/leak-scan.sh .              # the working tree
```

That checks the tree for identity, path and health patterns and delegates secrets to `gitleaks`.
It does **not** read history, and a personal name in a commit message is public forever — so check
that separately, before you open a PR:

```bash
git log -p --all -- . \
  ':(exclude)scripts/leak-patterns.tsv' ':(exclude)scripts/leak-scan.sh' \
  | ./scripts/leak-scan.sh --no-gitleaks -
```

The two exclusions stop the gate flagging its own pattern file — which necessarily contains the
shapes it looks for — and its own example text. `--no-gitleaks` because piping raw patches through
gitleaks is mostly noise; run the secrets pass over history directly instead.

Two more pre-push checks:

```bash
python3 scripts/validate-skills.py .            # frontmatter, name/dir match, refs, py_compile
gitleaks detect --source . --log-opts="--all"   # secrets, over every commit
```

**CI enforces the gate.** `.github/workflows/leak-gate.yml` runs on every push and pull request,
scanning the tree, validating the skills, and scanning the full git history. The pre-commit hook is
a convenience and is bypassable with `--no-verify`; CI is the version that actually enforces
anything. `ci/leak-gate.yml` is kept as the source the workflow is copied from — see
[ci/README.md](./ci/README.md).

## Privacy — the part that is not negotiable

Treat everything you commit as public. The repository is private today, but the intent is to
publish it, and git history is forever. Do not put personal health data into it, ever:

- not into a skill body, even as a "worked example"
- not into a fixture
- not into a commit message
- not into a branch name

Use placeholders (`<YOUR_WEIGHT_KG>`, `<USER>`, `<YOUR_HEALTH_DIR>`) and keep the *shape* of an
example while discarding the values. If a value is genuinely load-bearing for a test, put it in a
config file with an example default rather than hardcoding it.

## Layout

```
skills/<stage>/<name>/     one skill, self-contained
scripts/                   the leak gate + the structural validator
Profile/                   profile templates
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
