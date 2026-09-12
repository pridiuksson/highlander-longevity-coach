# Box — provider cookbooks for standing up a coach box

A "box" is a machine that runs the Hermes agent with this kit installed. Each subdirectory is a
cookbook your agent executes — point the agent at the cookbook's `README.md` and it does the work,
stopping only where a human must act (⛔).

Why a plain VM and not a container/serverless target: Hermes is a **stateful daemon** — a
gateway that stays up, its own cron for proactive delivery, memories and installed skills under
`~/.hermes/`, and an interactive CLI the human drives over SSH. That is a small VM's job
description. Request-shaped container platforms (batch jobs, scale-on-HTTP endpoints) fit the
*model* leg of the kit, not the agent-hosting leg. Serverless-inference keys (e.g. Nebius
Token Factory) are already an option in the cookbooks' credential step.

| Provider | Cookbook |
|---|---|
| Nebius | [Nebius/](./Nebius/README.md) — CPU-only VM from zero via the `nebius` CLI |

To add a provider, copy the shape of an existing cookbook and keep the contract: agent-executable,
human only at stop-points, teardown included, leak-gate clean.
