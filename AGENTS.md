# AGENTS — working guide for this repository

This file is the canonical guide for any agent working on `highlander-longevity-coach`. Read it
before you change anything. `CLAUDE.md` is a pointer back here.

## What this repo is

A health-coach kit for the Hermes agent: reusable skills, the coaching loop that ties them together,
and profile templates to instantiate. It is a coach, not a dashboard — the skills collect and verify
data; the loop decides what is worth saying and learns from whether it landed.

**Publish boundary.** `skills/` is the published kit. `Profile/`, `scripts/`, and the root docs are
scaffolding around it. The repo is intended to become public, so everything here is written as if it
already is.

## The one rule: the leak gate

Run the gate before you propose anything. A red gate means **stop**.

```bash
./scripts/leak-scan.sh .              # identity / path / health patterns + a gitleaks pass
```

Treat everything you commit as public: no personal health data, no real names, no personal handles,
no hosts — in a skill body, a fixture, a commit message, or a branch name. Keep placeholders
(`<USER>`, `<YOUR_HEALTH_DIR>`) and drop the values. `CONTRIBUTING.md` has the full rule.

CI (`.github/workflows/leak-gate.yml`) re-runs the gate on every push and PR over the tree and the
full history — including secrets over history — so a red gate blocks the merge. The local hook and
the `workflow/` skills exist so you never push something CI will reject. Note the gate walks with
`find`, not `git`: gitignored `staging/` is scanned too.

## Skill layout and discovery

```
skills/<stage>/<name>/SKILL.md      one skill, self-contained
```

Stages group skills by the part of the coaching loop they serve — `decision/`, `evidence/`,
`health/`, `nutrition/`, `planning/`, `proactive/`, `quality/` — plus `workflow/` for the
contribution skills described below.

- **Command Code** discovers every skill via `.commandcode/settings.json` (`skills: ["./skills"]`),
  which is recursive — a skill is any directory containing `SKILL.md`.
- **Hermes** loads by directory: copy with `cp -r skills/* ~/.hermes/skills/` (see ONBOARDING).
- **Claude Code** does not discover nested skill folders natively; read the tree directly.

A skill must carry `license:` frontmatter and its `name:` must match its directory.
`python3 scripts/validate-skills.py .` checks that, that every `references/` and `scripts/` target
resolves, that shipped Python compiles, and that every skill is named in `README.md`.

**Skills are self-contained.** Each skill owns its own `scripts/`. Never import or symlink across a
skill boundary — duplicate a small reference or point at the owning skill's path.

## Contribution workflow

```
@ticket  →  @work  →  @commit  →  @create-pr
```

| Skill | Does |
|---|---|
| `ticket` | Write a self-contained, agent-ready GitHub issue; peer-reviews the body before creating it. |
| `work` | Execute an issue end-to-end: verify, do the scope, run the verification commands and the gates, peer-review, ship. |
| `commit` | Split the change into leak-gated conventional commits. |
| `create-pr` | Push a branch and open a PR **without moving HEAD**; runs the full pre-push gate. |

Decision aids, when the change is not trivial: `peer-review` (quick second opinion, default reflex
before acting on an assumption), `grill` (adversarial, null hypothesis = no, for go/no-go calls),
`plan` (a written plan before a multi-step change), `loop` (iterate to a testable spec).

## Pre-push checks

`@create-pr` runs a diff check plus the five checks below. The tree gate, the skill validator, the
history identity scan, and the authorship check are mandatory. The fifth — secrets over the full
history — needs `gitleaks` installed; if it is missing, report the secrets checks as **unverified**,
never as clean.

```bash
./scripts/leak-scan.sh .                     # tree: identity / path / health + secrets

python3 scripts/validate-skills.py .         # skill structure + README consistency

git log -p --all -- . \
  ':(exclude)scripts/leak-patterns.tsv' ':(exclude)scripts/leak-scan.sh' \
  | ./scripts/leak-scan.sh --no-gitleaks -   # full history

./scripts/check-git-identities.sh            # authorship. The scan above cannot see it: it drops
                                             # Author:/Commit: lines when splitting the log into
                                             # per-file diffs, so no pattern can fire on one

gitleaks detect --source . --log-opts="--all"  # secrets, every commit
```

The authorship check is separate because authorship is the one thing that cannot be edited after
publication. Every commit carries it forever, and no content pattern can reach it.

## Working style

- **Plan first, then act.** For anything beyond a one-line change, write the plan and get agreement
  before editing.
- **One change, one reason.** In the commit, say what the change is *for*, not just what it does.
- **Verify, don't assert.** Prefer running a command over reasoning about what it would do; when a
  claim comes from elsewhere, check it against the source before repeating it.
- **Delegate with enough context.** A subagent cannot see this file or the conversation unless you
  put the relevant part in its prompt.
- **Stay lean.** Offload durable facts into the docs rather than long-lived scratch files.

## Docs index

| Doc | Covers |
|---|---|
| [README.md](./README.md) | What the kit is, the loop, install, privacy |
| [ONBOARDING.md](./ONBOARDING.md) | From clone to a working coach |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | The gate, layout, and how to change a skill |
| [Profile/README.md](./Profile/README.md) | The three profile templates |

## Do not

- Do not commit personal data, real names, handles, or hosts — see the leak gate.
- Do not add symlinks **inside this repository**: the gate flags every symlink it finds, and it is
  not to be relaxed. (Symlinking the repo's skills into a Hermes install is outside the tree and
  unrelated.)
- Do not import across skill boundaries.
- Do not push or merge without the gate passing.
