# USER — durable facts about <USER>

> Pays rent every turn. Keep it short. If the agent does not need it to act correctly, it does
> not belong here — put it in `MEMORY.md` or nowhere.

## Who

- **<USER>**, <AGE>, based in <CITY>.
- <ROLE> — <WHAT THEY OPTIMISE FOR / HOW THEY MAKE DECISIONS>.
- Communicates in <LANGUAGES>; prefers <DIRECTNESS LEVEL>.

## Health and training

- **Baseline file:** `<YOUR_HEALTH_DIR>/baseline.md` — the single source of truth for every
  measured value. The agent reads it. It must never recall a value from conversation.
- **Goals:** <PRIMARY GOAL>; secondary <SECONDARY GOAL>.
- **Training shape:** <MODALITIES>, <SESSIONS PER WEEK>, <SEASONALITY OR SCHEDULE SHAPE>.
- **Hard constraints:** <INJURIES>, <INTOLERANCES>, <MEDICATIONS>. Never plan around these by
  assumption — they are not preferences.
- **Data sources:** <DEVICE>, imported <CADENCE>.

## How to work with them

- Direct disagreement is welcome; hedged agreement is not.
- <PREFERENCE — e.g. "rank the options, don't list them">
- Correcting the agent is expected. Repeating a corrected mistake is not.

## Standing rules

- No secrets written to disk without consent.
- <HOUSE RULE>
