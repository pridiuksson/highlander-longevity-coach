# highlander-longevity-coach

A **health-coach kit** for the Hermes agent: reusable skills, the coaching loop that ties them
together, and profile templates to instantiate.

It is a coach, not a dashboard. The skills collect and verify data; the loop decides what is worth
saying and learns from whether it landed.

## What is in here

```
skills/       21 skills, grouped by the stage of the loop they serve
Profile/      SOUL / USER / MEMORY templates (Olle, Maria, Els)
scripts/      the leak gate and the structural validator
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

Two things make it a loop rather than a toolbox: **nothing reaches interpretation unverified**, and
the outcome of every proactive message writes back to memory. A silent week is a successful week —
`proactive-coach` exists to decide when *not* to speak.

### Contributor workflow

The `skills/workflow/` stage serves the people and agents working **on** this repo, not the coaching
loop: `commit` (leak-gated conventional commits), `create-pr` (push and open a PR without moving
HEAD), `ticket` (author an agent-ready GitHub issue), and `work` (execute an issue end-to-end). They
end at the ship gate `@commit → @create-pr`. [AGENTS.md](./AGENTS.md) has the full flow.

## Install

See **[ONBOARDING.md](./ONBOARDING.md)**.

## Privacy

Nothing in this repository contains personal health data. Skills use placeholders
(`<YOUR_WEIGHT_KG>`, `<USER>`, `<YOUR_HEALTH_DIR>`) and expect your data to live in your own files.
The gate below enforces that over the working tree; the identity/path/health patterns also run over
every commit (the history **secrets** pass is a separate `gitleaks --log-opts="--all"` — see
[CONTRIBUTING.md](./CONTRIBUTING.md)):

```bash
./scripts/leak-scan.sh .          # identity / path / health patterns + gitleaks, over the tree

git log -p --all -- . \
  ':(exclude)scripts/leak-patterns.tsv' ':(exclude)scripts/leak-scan.sh' \
  | ./scripts/leak-scan.sh --no-gitleaks -      # ...and over every commit
```

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the rest of the pre-push checks.

## Status

Private, pre-release. Validated against Hermes Agent v0.21.0 (2026.8.31).

The sanitization method and the per-file dispositions are recorded in the authoring workspace,
which is not published.

## License

MIT — see [`LICENSE`](./LICENSE).
