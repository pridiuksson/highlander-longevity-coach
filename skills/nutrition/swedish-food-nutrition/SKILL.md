---
name: swedish-food-nutrition
license: MIT
description: Fetch product data, prices, nutrition, and recipes from Swedish grocery chains (ICA, Hemköp, Willys) via JSON APIs. Use when building shopping lists, comparing prices, or pulling nutrition/ingredient data for Swedish groceries.
version: 1.0
---

# Swedish Grocery Data

Structured product, price, and nutrition data from Swedish grocery chains — without scraping HTML. Calls the JSON API tier the e-commerce SPAs use themselves.

## When to use

- Building a shopping list from a recipe
- Comparing prices across Hemköp and Willys
- Pulling nutrition facts or ingredient lists for Swedish products
- Fetching a Swedish recipe with quantities

## When NOT to use

- Adding items to carts (all chains' robots.txt forbid cart automation)
- Non-Swedish groceries (this is SE-specific)
- Bulk catalogue harvesting (rate limits apply — Crawl-delay: 10)

## TL;DR routing

| Need | Use |
|------|-----|
| Recipe with ingredients + quantities | ICA recipe page via curl (scripts/ica_recipe.py) |
| Product search + price (Hemköp) | scripts/axfood.py — search() |
| Product search + price (Willys) | scripts/axfood.py — search(store="willys") |
| Product detail + nutrition + ingredients | scripts/axfood.py — get_product() |
| Compare same product across stores | scripts/axfood.py — compare_prices() |
| Verify API health | scripts/verify.py |

## Fetching URLs: try web_extract first, fall back to curl

Grocery chains' product pages are JS-rendered SPAs — even a working fetcher gets empty/chrome-only output. The JSON API (via the scripts) returns structured data in milliseconds. That's always the preferred path for product data.

For ICA recipe pages (static HTML), try `web_extract` first. If it returns a search-backend error or empty content, fall back to curl via `execute_code` or `terminal` — the scripts already use curl internally. Don't assume web_extract is broken; just have curl ready as the fallback.

## How to call the scripts

All scripts live in this skill's `scripts/` directory. Import via execute_code:

```python
import sys, os
SCRIPTS = os.path.expanduser("$HERMES_HOME/$HERMES_HOME/skills/swedish-groceries/scripts")
sys.path.insert(0, SCRIPTS)
from axfood import search, get_product, compare_prices, search_with_details
from ica_recipe import get_recipe, extract_ingredients
```

Or run directly via terminal:

```
python $HERMES_HOME/$HERMES_HOME/skills/swedish-groceries/scripts/axfood.py search "arborioris" --store hemkop
python $HERMES_HOME/$HERMES_HOME/skills/swedish-groceries/scripts/axfood.py compare "arborioris"
python $HERMES_HOME/$HERMES_HOME/skills/swedish-groceries/scripts/ica_recipe.py "https://www.ica.se/recept/svamprisotto-1205/"
python $HERMES_HOME/$HERMES_HOME/skills/swedish-groceries/scripts/verify.py
```

## The scripts

### axfood.py — Hemköp & Willys (no auth)

```python
search(query, store="hemkop", size=5)
# → [{name, price, compare_price, code, brand, image_url, out_of_stock}, ...]

get_product(code, store="hemkop")
# → {name, price, ingredients, nutrition: {energy_kj, energy_kcal, fat, ...}, origin_country, ean, ...}

search_with_details(query, store="hemkop", size=3)
# → search + auto-fetch full details for top results

compare_prices(query, size=3)
# → {query, hemkop: [...], willys: [...]} side-by-side
```

### ica_recipe.py — ICA recipes (static HTML, no API)

```python
get_recipe(url)
# → {name, portions, total_time_minutes, rating, ingredients: [...], instructions: [...],
#     nutrition_per_serving: {energy_kcal_per_serving, fat_g, carbs_g, protein_g}}

extract_ingredients(url)
# → ["600 g blandad svamp", "2 msk olivolja", ...]
```

Recipe discovery: `web_search("site:ica.se/recept {dish name}")` to find recipe URLs,
then pass the URL to get_recipe().

## End-to-end workflow: recipe → shopping list with prices + nutrition

```python
import sys, os
sys.path.insert(0, os.path.expanduser("$HERMES_HOME/$HERMES_HOME/skills/swedish-groceries/scripts"))
from axfood import search_with_details
from ica_recipe import get_recipe

# 1. Get the recipe
recipe = get_recipe("https://www.ica.se/recept/svamprisotto-1205/")
print(recipe["name"], "—", recipe["portions"], "portions")
for ing in recipe["ingredients"]:
    print(f"  {ing}")

# 2. For each core ingredient, find the product at Hemköp
core_ingredients = ["arborioris", "parmesan", "kantareller", "vitlök"]
shopping_list = []
for ingredient in core_ingredients:
    products = search_with_details(ingredient, "hemkop", size=1)
    if products:
        p = products[0]
        shopping_list.append({
            "ingredient": ingredient,
            "product": p["name"],
            "price": p["price"],
            "nutrition": p.get("nutrition", {}),
        })

# 3. Print the shopping list
for item in shopping_list:
    print(f"{item['ingredient']:15s} → {item['product']:40s} {item['price']} kr")
```

## Nutrition field shape

Axfood returns nutrition as `nutrientHeaders[0].nutrientDetails[]` with **Swedish field names** (not GS1 codes). The script handles this automatically. Key mapping:

| Swedish field | Output key |
|---|---|
| energi (kilojoule) | energy_kj |
| energi (kilokalori) | energy_kcal |
| fett | fat |
| varav mättat fett | saturated_fat |
| kolhydrat | carbohydrates |
| varav sockerarter | sugars |
| protein | protein |
| salt | salt |

All values are **per 100g**. See references/nutrition_fields.md for full details.

Fresh produce gap (confirmed 2026-06-20): loose produce like vitlök (garlic) and gul lök (onions) return **no nutrition** from the detail endpoint. Packaged items (rice, cheese, canned mushrooms) always return complete data. For fresh produce nutrition, use ICA recipe nutrition (per-serving) or Livsmedelsverket's open database.

ICA recipe nutrition is **per serving** (not per 100g) — already portion-adjusted.

## Pitfalls

1. **web_extract may return a search-only error** for some URLs — if so, fall back to curl via terminal/execute_code. The scripts already handle this internally.
2. **Don't trust AI-sourced prices without verification** — JSON APIs either return real data or an error. No middle ground.
3. **Prices change daily** — don't cache, fetch fresh each time.
4. **Coop free-text search is dead** (404). Only category enumeration works, and needs UUID mappings. Deferred to v2.
5. **ICA e-commerce is WAF-gated** — requires Playwright. Deferred to v2. Use Axfood for product data instead.
6. **Respect Crawl-delay: 10** for bulk operations. A dozen calls per shopping list is fine.

## Supported chains (v1)

| Chain | Status | Coverage |
|-------|--------|----------|
| Hemköp | Working | search + detail + nutrition |
| Willys | Working | search + detail + nutrition |
| ICA (recipes) | Working | recipe fetch via JSON-LD |
| ICA (e-commerce) | Deferred (v2) | WAF-gated, needs Playwright |
| Coop | Deferred (v2) | Key works, search broken, needs UUID mapping |
| Mathem | Not implemented | Same Axfood-like backend, untested |

## Maintenance

- **When an endpoint breaks:** re-check [Kronixion/matval](https://github.com/Kronixion/matval) spiders — they track breakage.
- **Run verify.py** as a smoke test to confirm API health.
- **Prices verified:** 2026-06-20. Re-verify if results look stale.
- **Full research context:** see references/research-source.md for the original analysis, repo comparisons, and anti-pattern rationale.

## Source modes

This skill covers three Swedish nutrition sources. They share one protocol — establish the
source tier, pin the exact product, convert to per-portion — but differ in where the data lives:

| Mode | Where the numbers come from | Reference |
|---|---|---|
| **Grocery** | retailer product APIs/pages (per-100 g and per-package) | this `SKILL.md` |
| **Café / chain** | chain nutrition pages, secondary trackers when the primary fails | `references/cafe-nutrition-sources.md` |
| **Packaged label** | the printed label or a retailer's label scan; per-100 g → per-package | `references/packaged-label-mode.md` |

Source-tier rule for all three: a chain's own published values outrank a user-entered tracker
entry; a label outranks both. Record which tier you used, and never present a secondary-source
value as final.
