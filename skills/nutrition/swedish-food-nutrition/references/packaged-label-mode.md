---
name: swedish-packaged-food-nutrition
description: Kcal/protein/net weight for Swedish retail packaged foods.
version: 1.1
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [Research, Nutrition, Sweden, Food-Label, Groceries]
    related_skills: [swedish-cafe-nutrition, swedish-groceries, find-evidence]
---

# Swedish Packaged-Food Nutrition Lookup

Find authoritative nutrition-label data for branded, packaged foods sold in Swedish retail —
kcal per 100 g, kcal per package/bag, protein per 100 g, and net weight — with strict
no-estimation reporting.

## When to use

- "How many kcal/protein in <branded bag/box>?" — chocolate bags, candy, chips, biscuits, snacks
  sold in Swedish retail, including "I ate the whole bag" food-logging questions.
- Verifying a packaged food's label data against official/retailer sources before logging it
  (health tracking, meal planning).
- Tasks that demand source tiers (official/retailer/secondary) and forbid estimation.

**Use instead:** café/restaurant-chain items → `swedish-cafe-nutrition`; shopping lists, prices,
recipes, or store price APIs → `swedish-groceries`.

## The funnel (work in this order, stop at first authoritative hit, cross-check with one more)

1. **Brand official site.** Fetch the product *listing* page and grep slugs/anchors for the product
   family — brand sites confirm the exact name-as-sold but almost never publish nutrition numbers
   (Mondelez/Marabou publishes none). Most brand sites are server-rendered: plain `curl` + browser
   UA works; skip the browser tool.
   - **Naming gotcha:** users describe products in Swedish ("majskrokar", "chokladöverdragna
     majspuffar"); the actual product line may carry an English name ("Crunchy Corn", "Never Stop").
     Search BOTH languages and grep the official listing page for English words like corn/crunch.
2. **Open Food Facts JSON API** — gets you the EAN barcode + provisional numbers:
   ```
   https://se.openfoodfacts.org/cgi/search.pl?search_terms=<query>&search_simple=1&action=process&json=1
   ```
   Parse `products[].nutriments` (`energy-kcal_100g`, `proteins_100g`) and `products[].code` (= EAN,
   needed for Dabas). Intermittently returns HTML "Page temporarily unavailable" — retry once before
   concluding anything. Community-entered: expect small variance between duplicate entries for the
   same product (e.g. <value> vs <value> kcal). Treat as secondary, never final.
3. **Dabas** (Swedish GS1 trade-item aggregator) — official ingredient declarations:
   `https://www.dabas.com/productsheet/<0+EAN13>` (e.g. `07622201701956`). The Dabas *search* URL
   404s — go straight to the productsheet once the EAN is known.
4. **Retailer product page by ID — usually the authoritative tier.** Find the numeric product ID via
   `web_search("site:handla.ica.se <product name>")` (or the chain's equivalent), then curl the page.
   - **`handla.ica.se/produkt/<id>` serves full static HTML to plain curl** (with browser UA):
     complete "Näringsdeklaration" table marked "Information från leverantör" (supplier-fed — data
     originates from the manufacturer), plus net weight in the page title. Verified 2026-08-29
     (product 2159035, Marabou Never Stop Crunchy Corn 110g).
   - **The ICA search endpoint (`/sok?q=`) is dead to curl** (0 bytes / 404) — always route around it
     via web_search to get the product ID first. A failed ICA *search* does NOT mean ICA product
     pages are blocked.
   - willys.se, coop.se, mathem.se: HTML search and guessed `/api/...` paths were blocked to curl
     (2026-08-29). If ICA fails, try the swedish-groceries Axfood scripts (Willys/Hemköp JSON API)
     before giving up on the retailer tier.
5. **Wholesale/distributor shops** — Torebrings, OutOfHome (outofhome.se), Matsmart, godis wholesalers.
   They reproduce the legal declaration verbatim and confirm net weight; excellent independent
   cross-check when the retailer tier is unreachable.
6. **fatsecret.se** — secondary/confirmation only. kcal/100 g is usually exact; macro grams in the
   summary are often badly rounded (7.7 g protein displayed as "5 g"). Never cite as sole source.

## Reporting rules (when the task says "do NOT estimate")

- **Per-package kcal is label arithmetic, not estimation:** kcal/100 g × net weight in kg. Anything
  beyond label arithmetic must be flagged or omitted.
- Always report: product name-as-sold · net weight · kcal per 100 g · kcal per package · protein per
  100 g · source URL · source tier (official / retailer / secondary).
- If the official site lacks numbers (common), say so explicitly — the retailer's supplier-fed table
  is then the best available tier and beats OFF/fatsecret for precision.
- If the exact product cannot be found after the full funnel: say so explicitly and stop. Never
  substitute a "close enough" product's numbers.

## Pitfalls

- **web_extract can be search-backend-only** (errors with "search-only backend cannot extract") —
  fall back to curl via terminal immediately; don't retry it.
- **Per-100 g values may differ by ~0.5% across sources** (recipe updates, entry staleness). Prefer
  the newest retailer declaration; note the delta if cross-checking.
- **Net weight lives in page titles and distributor listings** (e.g. "15 x 110 g" case packs at
  outofhome.se), not always in the nutrition table.
- **Search results for the brand alone return only the famous bars** (Mjölkchoklad, Mörk) — the
  niche line (corn, popcorn) needs the family keyword from the official listing page.

## Worked example (2026-08-29)

Marabou Never Stop Crunchy Corn (roasted corn kernels 24% in milk chocolate, sharing bag):
<size> g bag · <kcal> kcal & <kJ> kJ per 100 g → ≈<kcal>/bag · protein <g>/100 g (≈<g>/bag) — always convert per-100 g to per-package before advising.
fat 29 g / sat 15 g · carbs 57 g / sugars 56 g · fiber 3.2 g · salt 0.55 g.
Sources: ICA handla.ica.se/produkt/2159035 (retailer, authoritative) · Torebrings art. 4317247
(wholesale, identical) · marabou.com/se/produkter/crunchy-corn-36778/ (official, name only) ·
OFF EAN 7622201701956 (secondary) · fatsecret.se (confirmed kcal, rounded macros).
