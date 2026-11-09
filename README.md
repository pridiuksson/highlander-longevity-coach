# highlander-longevity-coach

> **Hermes + this plugin is the open, local-first stack that can replace a dozen early-stage AI longevity/health startups** — wearable ingestion, stress triage, recovery scoring, evidence checks, proactive coaching, and an outcome ledger, running on your own machine with your own model provider.

![highlander logevity coach](/highlander.webp)

This repo ships a native Hermes Agent plugin that registers **9 config-free skills**, **9 typed tools**, and the **`weekly-crunch` automation blueprint**.

**Private health data:** health-related values referenced in prompts/tool calls are sent to whichever model provider your Hermes session uses. Data stays on your device; only referenced values leave the box, subject to your provider policy. Demo mode uses synthetic in-memory data and does not write to your live ledger or `health.db`.

## Getting Started

1. **Install/load** the plugin from this repo’s `plugin/`. Verify: `hermes plugins doctor`.
2. **Run the demo crunch:** in a Hermes session say: *“Run the longevity crunch in demo mode”* (or call `coach_run_crunch` with `demo=true`).  
   Expected output includes `[DEMO / SYNTHETIC DATA — no writes to live ledger or health.db]`, an `appraisal` (quadrant), a `micro_action`, and demo ledger/recovery placeholders.
3. **Setup proactivity”**: run `/suggestions` and accept `longevity-coach:weekly-crunch` (after setting `proactive.timezone`), **or** run a typed tool chain such as `coach_ledger_add` → `coach_ledger_report`.

Copy-paste prompts:
- *“Run the longevity crunch in demo mode.”*
- *“Use `longevity-coach:grill` to decide: should I adopt X?”*
- *“Load `longevity-coach:plan` and help me plan my week.”*

## Default Config

Configured via plugin settings (`plugins.entries.longevity-coach.settings.*` when supported by Hermes):
- `health.db` (default `${HERMES_HOME}/data/health.db`): SQLite path used by recovery tools when `db_path` is not provided. Current tools honor this via plugin config when available, with env/default fallback.
- `health.health_dir` (default `~/health`): reserved for future plugin surfaces; **not consumed by current tools**.
- `proactive.quiet_hours` (default `08:00-21:00`, `HH:MM-HH:MM`) and `proactive.timezone` (default empty = UTC): **advisory scheduling hints**. This plugin does **not** enforce delivery timing; set timezone to avoid midnight scheduling.

**Trust model:** tools accept an optional `db_path` for flexibility. As with any Hermes tool, the active session can access files the profile can access — treat plugin tool calls like built-in file/SQLite tools.

## Full coaching loop (optional)

The plugin is self-contained. The full proactive coaching loop is enhanced if you also install on-disk skills from this repo (`cp -r skills/* ~/.hermes/skills/`) and configure `skills.config.*`: `proactive-coach`, `stress-dialogue`, `evidence-loop`, `biometric-recovery-ledger`, `nutrition-advisory`, `wearable-health-data`. Use [ONBOARDING.md](./ONBOARDING.md) runbook. Manifest: [`plugin/plugin.yaml`](./plugin/plugin.yaml).

```
plugin/       Hermes plugin (contest entry): manifest, tools, bundled config-free skills, blueprint
skills/       on-disk coaching/workflow skills (config-dependent loop + workflow; plugin-bundled config-free skills live in plugin/skills/)
Profile/      SOUL / USER / MEMORY templates (8 personas) & physiological scaffolds
Box/          optional provider cookbooks for standing up a Hermes coach box
scripts/      the leak gate, the validator, and the authorship + value-layer checks
AGENTS.md     working guide for agents
ONBOARDING.md operator runbook (full loop / on-disk setup)
CONTRIBUTING.md
```

### The loop

> **Ingest → Verify → Interpret → Decide → Plan → Deliver proactively → Learn**

| Stage | Skills |
|---|---|
| **Ingest** | `apple-health-import`, `samsung-health-import`, `garmin-import`, `wearable-health-data` |
| **Verify** | `evidence-loop`, `find-evidence`, `memory-reality-check` |
| **Interpret** | `nutrition-advisory` (on-disk) + plugin: supplement-spec-verification, meal-planning, swedish-food-nutrition |
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
