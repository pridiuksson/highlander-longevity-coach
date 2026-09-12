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

[ONBOARDING.md](../ONBOARDING.md) step 7 owns this. It interviews the person, matches them against
the registry above, and adapts the winner — read it before copying anything by hand. The one trap
it exists to prevent: the three files only work where Hermes actually reads them (`SOUL.md` →
`~/.hermes/SOUL.md`, `USER.md`/`MEMORY.md` → `~/.hermes/memories/`). Copying the folder somewhere
Hermes never looks silently does nothing. No gateway restart is needed for profile files — they
are read fresh every turn.

## Adding a bundled profile

The step-7 framework matches against whatever the registry above contains, so a new profile needs
no change to ONBOARDING.md — it needs to carry its own self-description. A bundled profile is:

1. A directory with the three files, written generic — scaffolds, placeholders, no real data (see
   below). Reuse the common placeholder taxonomy (`<USER>`, `<AGE>`, `<CITY>`, `<ROLE>`,
   `<LANGUAGE>`, `<MODALITIES>`, `<INJURIES>`, `<INTOLERANCES>`, `<MEDICATIONS>`, `<DEVICE>`,
   `<CADENCE>`); add fields only where the health content demands them.
2. The same loop block as the others — **Ingest → Verify → Interpret → Decide → Plan → Deliver
   proactively → Learn**.
3. A row in the table above, concrete about who it fits. That row is what the matcher reads.

The gate (`./scripts/leak-scan.sh .`) applies as everywhere else.

## These are scaffolds, not redactions

The content here was *rewritten* to be generic, not blanked out. There is no original hiding
underneath, and no personal data was carried over. So: do not treat a copy of this repo as a
place to store your own data — fork it, or keep your profile files outside the repo entirely.
