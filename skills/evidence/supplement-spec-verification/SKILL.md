---
name: supplement-spec-verification
license: MIT
description: "Confirm supplement stack specs via Swedish retailer pages."
tags: [supplements, specs, verification, swedish, pharmacy, ingredients, interaction-analysis]
---

# Supplement Spec Verification

Before ANY supplement dosing math, interaction analysis, or timing rules, the
actual per-unit contents of each product must be verified against a primary
source. Product names routinely hide co-formulated actives (a "Q10 + selen"
product can also contain BioPerine, vitamin C, and vitamin E; an "iron"
product can contain 100 mg vitamin C), and user-maintained stack notes drift
from reality. Interaction conclusions built on unverified labels are
confident-sounding nonsense.

## When to Use

- User lists supplement products (shelf/stash inventory) and analysis will
  depend on their contents
- Two records of the same product disagree (possible reformulation — or not)
- Question of the form "does product X also contain Y?" (BioPerine, vitamin C,
  retinol — co-formulations that change timing/isolation rules)
- "Has this product been reformulated?" / "which of these two products exists?"

## Procedure

1. **Identify the exact commercial name.** User notes contain misspellings and
   wrong categorizations ("Afrenova" → AfteNova; "cod liver oil" for a salmon
   oil product). Search the brand + distinguishing strength (e.g.
   "BioSalma Q10 120 mg selen") to pin the exact SKU. Record the EAN when a
   retailer lists it — it disambiguates reformulations.
2. **Get the spec table from a primary source.** See
   `references/swedish-retailer-spec-sources.md` for which sites carry full
   per-unit tables vs which manufacturer pages don't. Prefer, in order:
   official manufacturer page with numbers → big Swedish pharmacy/retailer
   product page (apotea.se, apotekhjartat.se, apohem.se, meds.se,
   proteinbolaget.se, kronansapotek.se) → two agreeing retailer pages.
3. **Extract BOTH the per-dose table and the full ingredient list**
   (`Ingredienser`). The table gives actives; the ingredient list gives
   co-formulations and exact FORMS (e.g. folate as folic acid vs 5-MTHF
   Quatrefolic®, B12 as cyano- vs methyl-/adenosylcobalamin, Mg as oxide vs
   bisglycinate). Forms matter for interaction and absorption analysis.
4. **Check the dose basis of every number before comparing records.** Swedish
   tables are dual-column: `per 1 kapsel` / `per 2 kapslar (dagsdos)`.
   Two records differing by an exact integer ratio on EVERY value are the two
   columns of one table — not a reformulation, not two products. State the
   basis ("per capsule") with every verified figure. This resolves most
   apparent "spec conflicts" without further digging.
5. **Sanity-check implausible numbers against the product category, then
   verify — don't assume.** Natural (non-concentrated, TG-form) fish oils run
   ~150–300 mg EPA+DHA per 1000 mg capsule; concentrates run 500–700+ mg. A
   "suspiciously low" figure can be correct for a natural oil. Likewise check
   vitamin A/D presence by oil TYPE: cod LIVER oil (torskleverolja) carries
   retinol + D3; salmon OIL (laxolja) does not — users conflate them, and the
   retinol-load question (several caps/day) hinges on the distinction.
6. **Report per product:** verified per-unit actives with forms, ALL
   co-formulated ingredients beyond what the user listed, source URL, and a
   verdict: CONFIRMED / CONFLICTS-WITH-USER / NOT VERIFIED. Never guess —
   NOT VERIFIED is a valid, required output.

## Pitfalls

- **Reasoning from the product name.** Names advertise one or two actives;
  the table is the truth. Always pull `Ingredienser` + the per-dose table.
- **Column-basis false conflicts** (step 4) — the single most common error.
- **Concluding "unverifiable" from a missing manufacturer table.** biosalma.se
  product pages show marketing text but no per-unit numbers; the identical
  product on apotea.se has the full table. Retailer pages are primary enough.
- **Quoting a search snippet as final evidence.** Search descriptions of
  retailer pages often embed the full nutrition table verbatim — use them as
  leads, then confirm by fetching the page.
- **Cross-market brands:** some Nordic brands are headquartered elsewhere
  (Ecosh → ecosh.lt, spec text in Lithuanian: "Vienoje kapsulėje" = per
  capsule, "Sudėtis" = composition). Translate rather than skip.
- **Web fetch fallback:** if `web_extract` returns a search-only backend
  error, fetch with plain `python3` + urllib, browser UA, `Accept-Language:
  sv`, strip script/style/tags, then print ~320-char windows around keywords
  (`Innehåll per`, `varav`, `Ingredienser`, `DRI`). This also keeps page noise
  out of context. Worked on every Swedish retailer page tried (Aug 2026).
- **Unit tables aren't per-unit:** products marketed as capsules may be
  tablets (or vice versa) — note the actual form.

## Output Shape

Numbered list, one entry per product: verified per-unit specs (with forms),
additional co-formulated ingredients, source URL, verdict. Flag prominently
any figure that contradicts the user's assumption strongly enough to change
their dosing (e.g. EPA+DHA per capsule an order of magnitude below their
previous product).

## References

- `references/swedish-retailer-spec-sources.md` — site-by-site reliability for
  spec tables, fetch-fallback recipe, Swedish table vocabulary, and the
  verified Aug 2026 snapshot of an 8-product Swedish supplement shelf
  (BioSalma, Holistic, Närokällan, Ecosh, AfteNova, Hjärtats) with hidden
  co-formulations marked.
