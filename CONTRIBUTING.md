# Contributing

## The one rule

**Run the leak gate before you propose anything. A red gate means stop.**

```bash
./scripts/leak-scan.sh .
```

It checks the tree for identity, path and health patterns, and delegates secrets to `gitleaks`.
It also scans **git history** — a personal name in a commit message is public forever, so the
history matters as much as the working tree.

CI runs the same check, plus a structural pass:

```bash
python3 scripts/validate-skills.py .   # frontmatter, name/dir match, references, py_compile
```

The pre-commit hook is a convenience; CI is the enforcement.

The workflow is shipped as [`ci/leak-gate.yml`](./ci/README.md) rather than in `.github/workflows/`
— see [ci/README.md](./ci/README.md) for why and for the one-line step that activates it.

## Privacy — the part that is not negotiable

This repository is public. Do not put personal health data into it, ever:

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
scripts/                   the leak gate
Profile/                   profile templates
```

Skills are grouped by the stage of the coaching loop they serve — `decision/`, `health/`,
`evidence/`, `nutrition/`, `planning/`, `proactive/`, `quality/`.

**Skills never import across their own boundary.** Duplicate a small reference, or point at the
owning skill's path. Shared state is how two skills drift apart.

## Contributor profile

`Profile/Els/` is the contributor profile — it carries the same coaching loop as the others, plus
a contributor lane with the conventions above. It is a template: copy it, do not edit it in place.

## Changing a skill

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
