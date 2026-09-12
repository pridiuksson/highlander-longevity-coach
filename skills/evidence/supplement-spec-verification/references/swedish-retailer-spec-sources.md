# Swedish Retailer Spec Sources — Reliability, Fetch Recipe, Vocabulary

Site-by-site notes for verifying supplement per-unit specs, plus the verified
Aug 2026 8-product snapshot from a real shelf audit.

## Where per-unit spec tables live

| Source | Value | Notes |
|---|---|---|
| apotea.se product page | ✅ best | Full `Innehåll Per dagsdos` table + `Ingredienser:` list in **static HTML** — no JS, no cookie wall for a plain urllib fetch. Often lists EAN. |
| apotekhjartat.se, apohem.se, meds.se, proteinbolaget.se, kronansapotek.se | ✅ good | Same tables, also static. Cross-check a second retailer before declaring CONFIRMED. |
| Manufacturer sites | ⚠️ mixed | biosalma.se: marketing text + ingredients but **no per-unit numbers** (as of Aug 2026). holistic.se and narokallan.se: full dual-column tables. Never conclude "unverifiable" from a missing manufacturer table — check retailers. |
| Search-result snippets | ✅ lead only | Brave/Google descriptions of retailer pages frequently embed the entire nutrition table verbatim. Use as a lead; confirm by fetching the page. |

## Fetch fallback (when web_extract is a search-only backend)

```python
# python3, stdlib only — worked on every Swedish retailer page tried (Aug 2026)
import re, urllib.request, html
req = urllib.request.Request(url, headers={
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36',
    'Accept-Language': 'sv,en;q=0.8'})
txt = urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'ignore')
txt = re.sub(r'(?is)<(script|style|svg|noscript)[^>]*>.*?</\1>', ' ', txt)
txt = re.sub(r'(?s)<[^>]+>', ' ', txt)
txt = re.sub(r'\s+', ' ', html.unescape(txt))
for kw in ('Innehåll per', 'varav', 'Ingredienser', 'DRI', 'EAN'):
    i = txt.find(kw)
    if i >= 0: print(f'[{kw}] ...{txt[max(0,i-120):i+320]}...')
```

Keyword-window printing keeps page noise out of context — extract only the
spans you need, never the whole page. Watch for: a URL that returns binary
(PNG magic bytes) = wrong product URL, not a block. Manufacturer product URLs
may live under `/products/<slug>/` (biosalma.se), not `/produkt/<slug>/`.

## Swedish spec-table vocabulary

- `Innehåll per dagsdos` / `per 1 kapsel (tablett)` — per daily dose / per unit
- `varav` — "of which" (breakdown of a total, e.g. `- varav EPA 110 mg`)
- `Näringsinnehåll` — nutrition table; `Ingredienser` — full ingredient list
- `IE` — international units (IU); `µg` may appear as `ug`/`μg`
- `DRI` — dagligt referensintag; all % values are vs DRI
- Lithuanian (Ecosh/ecosh.lt): `Vienoje kapsulėje` = per capsule, `Sudėtis` = composition

## Verified snapshot — 8-product Swedish shelf (Aug 2026)

Per-unit values, hidden co-formulations in **bold**. All verified against the
listed page unless noted; apotea.se/apotekhjartat.se numbers cross-checked
against a second retailer (proteinbolaget.se / meds.se / apohem.se).

| # | Product | Per unit | Hidden extras | Source |
|---|---|---|---|---|
| 1 | Ecosh Ferrochel (cap) | 135 mg iron bisglycinate (Ferrochel®) = 27 mg elemental Fe | **Vit C 100 mg** (L-ascorbyl-6-palmitate); no folate; vegan capsule | ecosh.lt/produktas/bioaktyvi-gelezis-su-vitaminu-c-90-kapsuliu/ |
| 2 | BioSalma Omega-3 Salmon Oil 1000 mg (cap) | DHA+EPA 70 mg, DPA 15 mg, total omega-3 150 mg, astaxanthin 6 µg | none — **no vit A/D** (natural salmon oil, NOT cod liver oil) | apotea.se/biosalma-omega-3-salmon-oil-1000-mg-180-kapslar |
| 3 | AfteNova Magnesiumbisglycinat (cap) | 833 mg bisglycinate = 100 mg elemental Mg; B6 2 mg as P-5-P | — | apotea.se/aftenova-magnesiumbisglycinat-100-mg-90-kapslar |
| 4 | BioSalma Q10 Coenzym 120 mg + Selen (cap) | Q10 (ubiquinone) 120 mg, Se 55 µg, B12 2 µg | **BioPerine® 1.3 mg, vit C 25 mg, vit E 5 mg α-TE, olive oil 440 mg** (EAN 7350014910813) | apotea.se/biosalma-q10-coenzyme-120-mg-selen-60-kapslar |
| 5 | Holistic B6 B12 Folat Metylerad (cap) | TMG 100 mg, B6 12.5 mg (P-5-P), folate 250 µg as **5-MTHF Quatrefolic® (NOT folic acid)**, B12 500 µg (methylcobalamin + 5'-deoxyadenosylcobalamin) | per-2-cap column (TMG 200 / B6 25 / folate 500 / B12 1000) = same product, dagsdos column | holistic.se/b6-b12-folat-metylerad-60-kapslar |
| 6 | BioSalma Organiskt Zink (TABLET, not capsule) | Zinc 25 mg as citrate | **Vit C 200 mg, BioPerine® 2 mg**, rosehip powder, inulin | apotea.se/biosalma-organiskt-zink-100-tabletter-25-mg |
| 7 | Närokällan TMG (cap) | TMG 500 mg, leucine 20 mg | tapioka filler, pullulan veggie cap | narokallan.se/narokallan-tmg-120-kapslar |
| 8 | Hjärtats Kalcium + Vitamin D (tablet) | Ca 500 mg as carbonate; D3 10 µg = 400 IE (colecalciferol from sheep lanolin) | shellack + talc coating | apotekhjartat.se/varumarken/hjartats/hjartats-kalcium-vitamin-d-tablett-160-st |

Notes from this audit:
- The BioSalma salmon-oil EPA+DHA (70 mg/cap) looked like an error vs typical
  cod liver oil (200–250 mg+) and the user's previous 700 mg/cap concentrate —
  it was CORRECT: natural non-concentrated salmon oil. Confirmed identical
  across apotekhjartat.se, meds.se, proteinbolaget.se.
- The Holistic "conflict" (TMG 100 vs 200 mg etc.) was the per-1-cap vs
  per-2-caps column pair — one product, no reformulation.
- Interaction-relevant finds: TWO BioPerine sources on one shelf (Q10 1.3 mg,
  Zink 2 mg) and three vitamin C co-formulations (Ecosh 100 mg, Q10 25 mg,
  Zink 200 mg) — none visible from product names.
