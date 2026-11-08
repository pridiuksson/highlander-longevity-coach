# highlander-longevity-coach

![highlander logevity coach](/highlander.webp)

A **health-coach kit** for the Hermes agent: reusable skills, the coaching loop that ties them
together, and profile templates to instantiate.

It is a coach, not a dashboard. The skills collect and verify data; the loop decides what is worth
saying and learns from whether it landed.

## Hermes Plugin

This repo ships a Hermes Agent plugin (`plugin/`, entry longevity-coach) for the Hermes Plugin Hackathon. Install via the catalog (once listed) or from this repo's `plugin/` subdirectory.

**Disclosure:** This plugin sends health-related values to whichever model provider your Hermes session uses. Health data stays on your device; only the values referenced in prompts leave the box, subject to your provider's policy. The `weekly-crunch` blueprint is self-contained; the full coaching loop (stress triage, recovery scoring) is enhanced if you also have the on-disk `proactive-coach` and `stress-dialogue` skills installed.

**Trust model:** Tools accept a `db_path` argument for flexibility; in normal Hermes use the model passes the configured `health.db` path. As with any Hermes tool, the active session can read/write files the profile can access — treat the plugin's tool calls with the same trust as built-in file/SQLite tools.

See `~/.hermes/plugin-contest.md` for the build plan and `plugin/plugin.yaml` for the manifest.

```
skills/       the coaching skills, grouped by the stage of the loop they serve
Profile/      SOUL / USER / MEMORY templates (8 personas: Catalyst, Visionary, Operator, Scholar, Guide, Concise, Rebuilder, Protector) & 10 physiological scaffolds
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
| **Ingest** | `apple-health-import`, `samsung-health-import`, `garmin-import`, `wearable-health-data` |
| **Verify** | `evidence-loop`, `find-evidence`, `memory-reality-check` |
| **Interpret** | `nutrition-advisory`, `supplement-spec-verification`, `meal-planning`, `swedish-food-nutrition` |
| **Decide** | `stress-dialogue` (pre-decide triage) → `peer-review` → `grill` → `deliberate` |
| **Plan** | `plan`, `schedule-management` |
| **Deliver** | `proactive-coach` |
| **Learn** | `proactive-coach` ledger, `biometric-recovery-ledger`, `eval-health`, `loop` |
| **Onboard** | `demo` — a fresh box's tour guide: runs real skills on the user's own questions, learns the user slowly (max 3 questions per session, skip allowed), rewards every answer instantly, retires itself at graduation |

Two things make it a loop rather than a toolbox: **nothing reaches interpretation unverified**, and
the outcome of every proactive message writes back to memory. A silent week is a successful week —
`proactive-coach` exists to decide when *not* to speak.

### Contributor workflow

The `skills/workflow/` stage serves the people and agents working **on** this repo, not the coaching
loop: `commit` (leak-gated conventional commits), `create-pr` (push and open a PR without moving
HEAD), `ticket` (author an agent-ready GitHub issue), `work` (execute an issue end-to-end), and
`contributions` (send locally-proven improvements back upstream — capture the reason at edit time,
decide at a deliberate monthly check). They
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
