# highlander-longevity-coach

![highlander logevity coach](/highlander.webp)

A **health-coach kit** for the Hermes agent: reusable skills, the coaching loop that ties them
together, and profile templates to instantiate.

It is a coach, not a dashboard. The skills collect and verify data; the loop decides what is worth
saying and learns from whether it landed.

## What is in here

```
skills/       22 skills, grouped by the stage of the loop they serve
Profile/      SOUL / USER / MEMORY templates (Olle, Maria, Els)
Box/          provider cookbooks to stand up a coach box (agent-executed)
scripts/      the leak gate, the validator, and the authorship + value-layer checks
AGENTS.md     working guide for agents (CLAUDE.md points here)
ONBOARDING.md from clone to a working coach
CONTRIBUTING.md
```

### The loop

> **Ingest → Verify → Interpret → Decide → Plan → Deliver proactively → Learn**

| Stage | Skills |
|---|---|
| **Ingest** | `samsung-health-import`, `garmin-import`, `wearable-health-data` |
| **Verify** | `evidence-loop`, `find-evidence` |
| **Interpret** | `nutrition-advisory`, `supplement-spec-verification`, `meal-planning`, `swedish-food-nutrition` |
| **Decide** | `peer-review` → `grill` → `deliberate` |
| **Plan** | `plan`, `schedule-management` |
| **Deliver** | `proactive-coach` |
| **Learn** | `proactive-coach` ledger, `eval-health`, `loop` |
| **Onboard** | `demo` — a fresh box's tour guide: runs real skills on the user's own questions, learns the user slowly (max 3 questions per session, skip allowed), rewards every answer instantly, retires itself at graduation |

Two things make it a loop rather than a toolbox: **nothing reaches interpretation unverified**, and
the outcome of every proactive message writes back to memory. A silent week is a successful week —
`proactive-coach` exists to decide when *not* to speak.

### Contributor workflow

The `skills/workflow/` stage serves the people and agents working **on** this repo, not the coaching
loop: `commit` (leak-gated conventional commits), `create-pr` (push and open a PR without moving
HEAD), `ticket` (author an agent-ready GitHub issue), and `work` (execute an issue end-to-end). They
end at the ship gate `@commit → @create-pr`. [AGENTS.md](./AGENTS.md) has the full flow.

## Install

See **[ONBOARDING.md](./ONBOARDING.md)**. No machine yet? Point your agent at
[Box/Nebius/](./Box/Nebius/nebius-cpu-box-cookbook.md) — it stands one up from zero, agent-executed.

## Privacy

Nothing in this repository contains personal health data. Skills take the paths they need from
`config.yaml` (`skills.config.*`, injected at load) instead of baked-in placeholders, and the
reference docs carry deliberate `<value>` redactions where the authors' measurements were removed.
The gate below enforces that over the working tree; the identity/path/health patterns also run over
the history of the ref being built — never `--all`, so one branch's content cannot fail another
branch's build. The full-history **secrets** pass is a separate `gitleaks --log-opts="--all"`, and
the repo-wide `--all` identity audit is run on purpose before a release or a history rewrite — see
[CONTRIBUTING.md](./CONTRIBUTING.md):

```bash
./scripts/leak-scan.sh .          # identity / path / health patterns + gitleaks, over the tree

git log -p HEAD -- . \
  ':(exclude)scripts/leak-patterns.tsv' ':(exclude)scripts/leak-scan.sh' \
  | ./scripts/leak-scan.sh --no-gitleaks -      # ...and over this ref's history
```

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the rest of the pre-push checks.

## Status

Public, pre-release. **No tagged release yet** — pin by commit (`git rev-parse HEAD`) rather than
by `main`, which moves. Validated against Hermes Agent v0.21.0 (2026.8.31). All changes land as
pull requests: `main` is branch-protected, and the leak-gate check must pass before merge.

The sanitization method and the per-file dispositions are recorded in the authoring workspace,
which is not published.

## License

MIT — see [`LICENSE`](./LICENSE).
