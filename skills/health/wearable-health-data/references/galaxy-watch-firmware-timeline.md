# Galaxy Watch 7 firmware/update timeline (condensed research, 2026-08-15)

Why this exists: when a Samsung Health export shows a discrete step in sleep
scoring, max-HR, VO2max, or aerobic-threshold (AT) estimates, ask "did the
watch software change near that date?" BEFORE attributing it to behavior or
environment. Samsung changelogs never document scoring internals — use dated
rollouts + feature-level coverage + user reports instead.

Decision rule (from deliberate run-005): an update rolling out within ~±2
weeks of a data step materially strengthens the firmware-re-scoring branch;
one far from every step weakens it.

## Dated rollouts — Galaxy Watch 7 (SM-L300/L310), Jul 2024 → Jul 2026

- **2024-07** — launch firmware: Wear OS 5 / One UI 6 Watch. "Advanced AI
  algorithm" sleep tracking, Energy Score computed from sleep + sleeping HR +
  sleeping HRV.
- **2024-11-<value>→<value>-29** — Nov-2024 security patch AXK6; Korea → Europe (BT).
- **2024-12-10** — Verizon US build (Oct-2024 patch level).
- **2025-01-15** — L310XXU1AXL1, Europe; stability only.
- **2025-03-28** — Samsung-confirmed bug: "sleep-related measurement values
  not reflected properly in Samsung Health" (Watch 4–7/Ultra). Proof that
  silent sleep-pipeline changes ship outside changelogs.
- **2025-10-02** — 9to5Google: en-masse sudden sleep-score inflation
  (99–100/100, no habit change) across models AND One UI versions → a
  Health scoring change can land app/server-side, independent of watch OTA.
- **2025-10-13 / 10-14 / 10-20 — One UI 8 Watch (Wear OS 6) stable:
  Korea / US / Europe+international.** L310XXU1BYI4 → L310XXU1BY14, ~2 GB.
  Health-stack rewrite: Bedtime Guidance, revamped sleep tracking, Vascular
  Load (measured during sleep), Running Coach with personalized HR zones,
  Energy Score revamp. Followed by a Reddit wave of broken/changed sleep
  tracking on Watch 4–8.
- **2025-11-20** — BYK1 (Nov-2025 patch), Korea; European expansion estimated
  mid/late Dec 2025 (LOW confidence — region date inferred).
- **2026-03-03 / 03-10** — Feb-2026 patch Korea/global (BZB1/BZB4);
  changelog: "improves the device's behaviour" (unspecified).
- **2026-06-<value>→<value>-16** — May-2026 patch Korea → US/Europe (L310XXS2BZE1).
- **2026-07-06** — Jul-2026 patch.
- Cadence: security patches ~quarterly; major One UI Watch updates land
  Sep–Dec. Expect ~2 patch windows + 0–1 major OS updates per 6 months.

## Verdict for the H2-2025 sleep anomaly (run-005)

- Window (a) 2025-09-25..11-15 (REM <value>→<value> bouts, deep dip): One UI 8 Watch
  hit Europe 2025-10-20, dead-center → firmware branch STRONG.
- Window (b) 2025-12-10..01-07 (max-HR <value>→<value> on 12-24): only BYK1-EU
  candidate, undated → WEAK.
- Window (c) 2026-02..06 (AT ladder): Mar-10 and Jun-8..16 patch windows align
  moderately; quarterly cadence makes partial alignment partly chance.

Full sourced table + per-update notes + all URLs:
`$HERMES_HOME/skills/deliberate/runs/run-005/fork-firmware-research.md`

## Best sources for this class of question

SamMobile and SammyGuru (dated rollouts with firmware PDA codes, sizes,
region waves), 9to5Google (user-observable scoring anomalies), Samsung
Newsroom (feature-level health-stack changes). samfw.com has per-region PDA
dates but Cloudflare-blocks curl (see blocked-page-recovery →
references/site-block-quirks.md). Reddit evidence is index-only from server.

## Caveat for causal claims

Sleep Score / Energy Score are partly computed phone/cloud-side (Samsung
Health app + One UI phone updates shipped in the same weeks as the Oct-2025
watch OTA). A watch-OTA-only causal story is incomplete; note the app-side
confound whenever firmware re-scoring is argued.
