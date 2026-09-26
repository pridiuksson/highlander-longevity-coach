# USER — durable facts about <USER>

> Pays rent every turn. Keep it short. If the agent does not need it to act correctly, it does
> not belong here — put it in `MEMORY.md` or nowhere.

## Who

- **<USER>**, <AGE>, based in <CITY>. Speaks <LANGUAGES>.
- **<ROLE / PROFESSION>** — researcher, clinician, engineer, or deeply analytical professional.
- Comfortable with shell, data structures, SQL, and APIs; inspects raw figures and underlying sources.
- Wants the number before the interpretation; values physiological precision and statistical honesty.

## Health and training

- **Baseline file:** `health.baseline_doc` — single source of truth for all verified clinical metrics.
- **Goals:** <PRIMARY CLINICAL / PERFORMANCE GOAL>; secondary <SECONDARY GOAL>.
- **Training split:** <MODALITIES>, <WEEKLY VOLUME & INTENSITY LANDMARKS>.
- **Hard constraints:** <INJURIES>, <INTOLERANCES>, <MEDICATIONS>.
- **Data sources:** <DEVICES & LAB PLATFORMS>; imported <CADENCE>.

<!-- Note: To specialize this profile for specific physiology, copy a clinical scaffold from
     Profile/scaffolds/ (e.g. USER_cycling_female.md, USER_cardiometabolic_male.md, USER_concurrent_athlete.md) here. -->

## How to work with them

- Direct and objective. Provide citations, effect sizes, and data sources.
- Number first, then clinical synthesis.
- Ask before writing to profile files or updating persistent state.
- If a sensor or test is noisy or inconclusive, state the uncertainty explicitly.

## Standing rules

- No secrets to disk without consent.
- Never publish or merge code without running the leak gate first.
- <HOUSE RULE>
