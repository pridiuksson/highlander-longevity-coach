---
name: schedule-management
license: MIT
description: "Parse schedule input (CSV, XLS, paste, photo, Doc link), sync to Google Calendar with conflict detection, and learn the user's patterns over time. Self-evolving v1."
category: productivity
version: 0.1.0
author: the user's Hermes profile
metadata:
  hermes:
    tags: [calendar, scheduling, google-workspace, self-evolving, telegram]
    depends_on: [google-workspace]
---

# Schedule Management (v1 — Self-Evolving)

the user sends schedule data through Telegram in whatever form is easiest
at the moment — a CSV export, an Excel file, a pasted block of text, a
photo of a printed schedule, or a Google Docs link. This skill turns that
input into Google Calendar events, flags conflicts, reports what changed
in one line, and asks for feedback so it gets smarter each time.

> **Design posture:** This is a deliberate v1. It is small enough to work on
> day one and structured so every interaction can teach it something. Every
> section below has an explicit extension point. See **Evolution Notes** at
> the bottom for what the agent should watch for.

## Dependencies

- **google-workspace** skill — provides `calendar list`, `create`, `update`,
  `delete`, `freebusy`, and `quickadd`. Its CLI is `google_api.py`, inside *that*
  skill's own `scripts` directory: load `google-workspace`, take the directory from
  its `[Skill directory]` block, and use it for the shorthand. Do not assume these
  two skills share a parent — the reader chooses the layout.
- **mem0** — for storing and recalling learned patterns ("the user's CSV uses
  columns Date/Time/Studio/Group", "Studio A means the main hall").

## Trigger

Activate this skill when the user sends any schedule-related content:

- A **file** attached: `.csv`, `.xlsx`, `.xls`, `.numbers`, `.pdf`, or an
  image of a schedule/roster.
- **Pasted text** containing dates + times + locations/activities (e.g.
  "Tue 2-4pm Studio A — Group 1, Wed 10-12 Studio B — Group 2").
- A **Google Docs link** that looks like a schedule or roster.
- A **message that mentions** specific dates, times, studios, or groups in a
  scheduling context ("can you add next week's rehearsals?").

If the input is ambiguous, ask one short clarifying question. Do not guess
silently.

## Workflow

Follow these steps in order. Stop and ask the user whenever a step hits a
genuine fork (see **Conflict Resolution**).

### 1. Parse input → normalize to events

Use the right tool for the input type:

| Input | How to parse |
|-------|--------------|
| `.csv` | `read_file`, then split rows. Use the **last learned header mapping** from mem0 if present; otherwise infer from the first row. |
| `.xlsx` / `.xls` | `read_file` (auto-extracts to text). If that fails, `terminal` with a python one-liner + `openpyxl`. |
| Pasted text | Reason about it directly — identify rows of date/time/location/activity. |
| Photo / image | `vision_analyze` to read the schedule, then structure the rows. |
| Google Docs link | Extract the DOC_ID and run `$GAPI docs get DOC_ID`, then parse the returned text. |

Normalize every entry into a consistent event shape:

```json
{
  "summary": "<activity or group>",
  "start": "<ISO 8601 with timezone>",
  "end":   "<ISO 8601 with timezone>",
  "location": "<studio/room>",
  "description": "<optional notes>"
}
```

**When you don't know the year**, default to the nearest upcoming date.
**When you don't know the timezone**, check mem0 for "the user's timezone";
if absent, ask once and store it.

### 2. Confirm the parse (feedback loop — lightweight)

Show the user a compact preview, e.g.:

> Parsed 6 events from your CSV. First: **Tue Jun 24, 2–4pm @ Studio A — Group 1**. Last: **Sun Jun 29, 6–8pm @ Studio B — Group 3**. Want me to sync all 6 to Google Calendar?

If the count or first/last looks wrong, the user will correct you. **Learn
from every correction** (see Self-Evolution). If it looks right, proceed.

### 3. Check for conflicts (freebusy)

Before creating, query busy time for the window spanning all parsed events:

```bash
$GAPI calendar freebusy --start <earliest> --end <latest>
```

Compare each parsed event against the returned busy blocks. Classify each
event:

- **Clean** — no overlap with existing events. → create immediately.
- **Time conflict** — overlaps an existing event's time. → see Conflict
  Resolution.
- **Content match** — an existing event at the same time with the same
  summary → treat as an update, not a duplicate.

### 4. Create / update events

For each event, decide create vs. update:

- **Create** new: `$GAPI calendar create --summary "..." --start ... --end ... --location "..."`.
- **Update** existing (same time + summary, content differs):
  `$GAPI calendar update EVENT_ID --location "..."`.
- **Quick-add** for a single natural-language item the user types:
  `$GAPI calendar quickadd "Studio A rehearsal Tuesday 2-4pm"`.

Batch quietly — do not narrate each event individually unless asked.

### 5. Report what changed (one line)

Summarize the outcome in a single readable line, with detail only on
exceptions:

> Synced 6 events (4 new, 2 updated). One conflict at Wed 10am — see below.

Then expand only the items that need attention.

## Conflict Resolution

Apply these rules in order:

1. **Time changes — latest timestamp wins.** If the user's new schedule moves
   an event's time and the old slot is now free, update the time without
   asking. This reflects the most recent source of truth.
2. **Content changes (location, activity, group) — always ask.** If the time
   matches an existing event but the studio/group differs, surface it:
   > Wed 10am already has "Group 2 @ Studio B" but your new sheet says
   > "Group 2 @ Studio A". Which is correct?

3. **Hard overlaps (two different events at the same time)** — flag clearly
   and ask. Never silently overwrite one event with another.

## Self-Evolution Mechanism

This skill is meant to learn. After **every** schedule interaction, do a
short reflection and store what you learned.

### Store patterns to mem0

Use mem0 to persist anything reusable. Examples:

- `"the user's schedule CSV columns: Date, Start, End, Studio, Group"` — so
  next time you parse a CSV you apply this mapping without re-inferring.
- `"the user's timezone is America/Los_Angeles"` — asked once, reused forever.
- `"Studio A = main hall; Studio B = second floor"` — location aliases.
- `"Rehearsals are 2 hours; if only a start is given, assume 2h duration."`
- `"the user's schedule week runs Monday–Sunday."`

Only store something when it is **demonstrably reusable** — a one-off detail
isn't worth saving. Tag memories with `category: schedule-pattern` so they're
easy to find.

### Propose skill updates for approval

When you notice the skill itself could be improved (a repeated manual step, a
parse rule that keeps failing, a missing abbreviation), **propose a concrete
edit** to the user and ask for approval before applying it. For example:

> I've had to ask which column is the studio three times now. Want me to add a
> note to this skill so I assume column 4 (Studio) by default for your CSV
> exports?

If approved, edit this SKILL.md and bump the version (0.1.0 → 0.2.0). Keep a
one-line note in the changelog below. **Never silently rewrite the skill** —
always show the proposed change and get a yes.

## Feedback Loop

After parsing (step 2) and after syncing (step 5), briefly confirm:

- **Did I get the parse right?** If the user corrects a row, re-parse, apply
  the fix, and store the general lesson ("the user's AM/PM is often swapped
  in column 3 — sanity-check against context").
- **Did I handle conflicts the way you wanted?** If the user overrides your
  resolution, note their preference ("the user wants content conflicts
  resolved by keeping the newest sheet, not asking").

Treat corrections as the highest-value training signal. Phrase the next
confirmation in light of what you just learned.

## Rules

1. **Confirm before writing to the calendar** — show the parsed events and
   get a yes before creating/updating (the google-workspace skill's own rule;
   this skill inherits it).
2. **One-line summary, detail on request** — don't flood Telegram with JSON.
3. **Never overwrite an existing event silently** — content conflicts always
   get a question.
4. **Store reusable patterns, not one-offs** — keep mem0 clean and high-signal.
5. **Propose, don't impose** — skill edits require the user's approval.

## Changelog

- **0.1.0** — initial v1 draft. Parse → confirm → freebusy → create/update →
  report. Conflict rules: latest-timestamp-wins for times, ask for content.
  Self-evolution via mem0 + proposed edits awaiting approval.

## Evolution Notes

Things the agent should **watch for** and turn into skill improvements over
time. Each is an explicit extension point for a future version.

### What to watch for

- **Repeated manual steps.** If you find yourself doing the same correction
  every week (e.g. always swapping column order, always adding 2h to a bare
  start time), that's a candidate to bake into the parse rule or store in
  mem0.
- **Recurring event patterns.** If the user's schedule has true recurring
  events (same thing every Tuesday), propose switching to a Google Calendar
  recurring event instead of creating 10 individual ones.
- **New input formats.** The first time a new format arrives (a screenshot
  from a specific app, a PDF roster, an iCal export), note how you parsed it
  so the next time is automatic.
- **Location/group vocabulary.** Watch for new studio names, group codes, or
  abbreviations and confirm their meaning once, then store the alias.
- **Timezone / DST edge cases.** Note when an event falls near a DST
  transition and confirm the time didn't shift unexpectedly.
- **Conflict-resolution preferences.** Track which resolution the user picks
  most often and whether their preference differs from the default rules.

### How to propose an update

When you spot a pattern worth codifying:

1. **State the observation** — what kept happening and why a rule would help.
2. **Show the concrete edit** — the exact lines you'd add/change in this
   SKILL.md (or the mem0 fact you'd store).
3. **Ask for approval** — one question, yes/no. Apply only on yes.
4. **Record it** — add a changelog line and bump the patch version.

### Explicit extension points (future versions)

These are *not* built yet — they're the places v1 is designed to grow into:

- **Recurring events** — detect and create RRULE-based events instead of
  copies.
- **Multi-calendar routing** — send rehearsals to a "Studio" calendar, admin
  to "Work", based on rules the user defines.
- **Reminders / notifications** — add default reminders per event type.
- **Lookahead / planning** — when the user asks "what's next week?", summarize
  the synced calendar in plain language.
- **Draft vs. confirmed** — a staging area where events are created as
  tentative until the user confirms.
- **Automated format detectors** — a small per-format parser registry that
  grows as the user sends new source types.

Keep v1 honest: every new capability should come from a pattern the user
actually hit, not from speculation.
