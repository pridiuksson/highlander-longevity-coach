# Box — provider cookbooks for standing up a coach box

A "box" is a machine that runs the Hermes agent with this kit installed. Each subdirectory is a
cookbook your agent executes — point the agent at the cookbook's `README.md` and it does the work,
stopping only where a human must act (⛔).

| Provider | Cookbook |
|---|---|
| Nebius | [Nebius/](./Nebius/README.md) — CPU-only VM from zero via the `nebius` CLI |

To add a provider, copy the shape of an existing cookbook and keep the contract: agent-executable,
human only at stop-points, teardown included, leak-gate clean.
