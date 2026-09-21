# Reflection Loop — Stage 7 (Learn) Extension

Reference: devops-agent PR #22 (`feat/proactive-reflection-self-adjust`).
Source paper: arXiv 2605.06717 — "Agentic Coding Needs Proactivity, Not Just Autonomy"
(Bui & Evangelopoulos, Google Labs). Design is a MANUAL Learning Lift proxy
(SKILL.md §Relation to source, 196-202): reply-rate via ledger.py (acted/ignored)
is NOT insight quality; action space mapped {notify=draft/recommend,
stay-silent=hold, O3 interruption=ALERT exempt).
Design: profile-isolated, ledger-based self-adjustment for proactive cron delivery.

Mechanism (existing ledger.py):
- `ledgers.py` records outcomes (acted / ignored / corrected / dropped)
- Gate: ≥3 consecutive `ignored` spanning ≥7 days (`PAUSE_STREAK` / `PAUSE_SPAN`)
- Extension (recommended, not auto-applied): emit signed hour-offset
  recommendations (accelerate / decelerate / hold) per (profile, source)
- Storage: profile-scoped JSONL (`scripts/.state/proactive-reflections.jsonl`),
  fcntl-locked; never mutates cron expressions; ALERT sources exempt.

Verification performed (2026-09-21, session):
- Maria `Weekly health check-in` executions.db (delivered 2026-09-21 09:02)
- Peer-review (design + code, 2 rounds) applied; fixes: removed DB proxy,
  enforced profile isolation, recommendations-only.

This is not a new skill stage — extends existing `proactive-coach` loop.
