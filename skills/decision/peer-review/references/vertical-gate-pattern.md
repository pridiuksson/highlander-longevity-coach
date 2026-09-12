# Vertical Gate Pattern — Session 2026-09-11

Derived from `<YOUR_DESIGN_DOC>.md` (`P0-G1`→`G5`) and `phase1-plan.md` / `phase2-plan.md`.

Gate structure: each gate produces `VERIFIABLE ARTIFACT` (file on disk, `stat`-checked). Agent applies `direct observation` (subagent mechanism verified broken — `delegate_task list=0`); no subagent relay; evidence file-cited.

Phase 0 gates: `P0-G1` evidence / `P0-G2` user-decisions (`A/A/A`) / `P0-G3` mechanism-defined (`§8.1-8.4` MISSING → A2 work item) / `P0-G4` e2e unblocked / `P0-G5` `/peer-review` final.
Phase 1: `P1-G1` (`B1` inventory) → `CAN START` (independent of A2, feeds A2); `P1-G2` (`A2` mechanism doc `§8.1-8.4`) → `CAN START` (parallel; required before `B2`); `P1-G3` reflection (`PASS` with open subsection — `A2-DEFINED/A2-OPEN` honest).
Phase 2: `P2-G1` (`B2` repo init + `S1` expanded PII audit `delete`+`encryption`; `S3`; `S5`) → `BLOCKED` `P1-G2` PASS; `P2-G2` (`C1` admin-layer `MANUAL`; references `§8.1-8.4`; `post-B2/post-A2`); `P2-G3` reflection (`honest` `FAIL` if `B2` NOT init / `C1` NOT implemented).

Sequence (`§6` `§4` `§2` `§9d` `§94`; `verified` `plan.md` `§46-§52`): admin-layer (`D`) FIRST (`A2` mechanism before ANY code); repo init (`B2`) `post-A2`; sqlite isolation (`C2`) `post-B2`; `HEALTH` restructure (`C3`) LAST; public flip (`C4`) ONLY after `S1` PASS + stable tag.
NOT BUILT discipline (`§53` `§61-63`): no sqlite copied; no manifest deployed; no repo init; no cron; no gateway; no health restructure; no public flip; no new skills without tier-approval.

Peer-review gate (`SKILL.md` verified; `scripts/peer-review.sh`): `adversarial` `null-hypothesis` = hidden contradiction / missing dependency / PII leak / broken sequence / fabricated PASS. `PASS` = file-cited artifacts present + mechanism `§8.1-8.4` `closes` where `written` + contradiction resolved (`§7` vs `§3` F vs `§6` R4 → manifest/intended + audit/unexpected + manual/reconciliation) + `honest` gap acknowledged (`A2-DEFINED/A2-OPEN`; uncalibrated `§8.2`).
Reference files: `plan.md` (`18544B`); `phase1-plan.md` (`15965B`); `phase2-plan.md` (`15028B`); `b1-inventory.md` (`6905B`); `a2-mechanism.md` (`7289B`); `p1-g3-reflection.md` (`6674B`).
