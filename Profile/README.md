# Profile templates

A skill set is not a coach. The coaching **loop** lives in three files the agent reads every
turn, and this folder ships three worked scaffolds to start from.

| Template | Flavour | Best suited to |
|---|---|---|
| [`Olle/`](./Olle/) | **Operator.** Direct, high-agency, verification as a pre-flight gate. | Technically senior users who want an agent that pushes back. |
| [`Maria/`](./Maria/) | **Assistant.** Warm, explains, proposes before acting. | Domain experts who are new to AI. |
| [`Els/`](./Els/) | **Middle ground + contributor.** Assisted, but technically comfortable and works on this repo. | Technical users who want coaching *and* to hack on the skills. |

## The three files

| File | Holds | Changes |
|---|---|---|
| `SOUL.md` | Identity, tone, and the always-on loops | Rarely |
| `USER.md` | Durable facts about the person | Occasionally |
| `MEMORY.md` | Working state | Constantly |

`SOUL.md` is who the agent is. `USER.md` is who the person is. `MEMORY.md` is what is true right
now. Skills are the *verbs* the loops call.

## The coaching loop

Every `SOUL.md` here carries the same loop block:

> **Ingest → Verify → Interpret → Decide → Plan → Deliver proactively → Learn**

Two properties matter more than the stage names:

1. **Nothing reaches "interpret" unverified.** Stage 2 exists so a plausible-but-wrong number
   never becomes standing advice.
2. **It closes.** Stage 7 feeds stage 1. Without the outcome ledger writing back to memory, this
   is a report generator, not a coach.

## Instantiating a template

```bash
cp -r Profile/Els ~/my-profile
```

1. **Put the three files where your Hermes actually reads them** — `SOUL.md`, `USER.md` and
   `MEMORY.md` in your profile directory. Copying the folder somewhere Hermes never looks is the
   most common way this silently does nothing; [ONBOARDING.md](../ONBOARDING.md) step 7 has the
   concrete layout.
2. **Replace every `<PLACEHOLDER>`.** Nothing in these files should still contain angle brackets
   when you are done.
3. **Delete anything that does not apply.** A template with sections you do not use is worse than
   a shorter accurate one.
4. Keep the `MEMORY.md` rent rule — it is what stops memory becoming a landfill.
5. Restart the gateway **if you also installed skills** — it caches the skill catalogue at startup.
   Profile files are read fresh, so a restart is not what makes them take effect.

## These are scaffolds, not redactions

The content here was *rewritten* to be generic, not blanked out. There is no original hiding
underneath, and no personal data was carried over. So: do not treat a copy of this repo as a
place to store your own data — fork it, or keep your profile files outside the repo entirely.
