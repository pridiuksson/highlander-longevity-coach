# Swedish Grocery Endpoint Map

Verified live 2026-06-20. When an endpoint breaks, re-check Kronixion/matval spiders.

## Axfood (Hemköp & Willys) — no auth

Shared backend. Same endpoints, different domain.

### Search

```
GET https://www.hemkop.se/search?q={query}&page=0&size={N}
GET https://www.willys.se/search?q={query}&page=0&size={N}
```

Headers required:
```
User-Agent: Mozilla/5.0 ...
Accept: application/json, text/plain, */*
X-Requested-With: XMLHttpRequest
Referer: https://www.hemkop.se/   (or willys.se)
```

Returns `results[]`: name, priceValue (float), price (display string),
comparePrice, comparePriceUnit, code, manufacturer, image.url, outOfStock.

### Product detail (with nutrition + ingredients)

```
GET https://www.hemkop.se/axfood/rest/p/{code}?include=BREADCRUMB,NUTRIENTS
GET https://www.willys.se/axfood/rest/p/{code}?include=BREADCRUMB,NUTRIENTS
```

Same headers. Returns 80+ fields including: name, priceValue, comparePrice,
ingredients, nutrientHeaders, nutritionsFactList, originCountry, ean,
consumerStorageInstructions, outOfStock.

### Category enumeration (for full-catalogue scraping)

```
GET https://www.hemkop.se/c/{slug}?page=0&size=100&sort=topRated
```

Valid top-level slugs: skafferi, frukt-och-gront, mejeri-och-ost,
broöd-och-bageri, fisk-och-skaldjur, kottratt-och-chark, etc.

### robots.txt constraint

`Crawl-delay: 10`, `Visit-time: 0400-0845 UTC`.
Enforce for bulk scraping. A dozen calls per shopping list is fine.

---

## ICA Recipes — static HTML, no API

```
curl https://www.ica.se/recept/{slug}/
```

Recipe pages are server-rendered HTML with JSON-LD `<script type="application/ld+json">`
blocks. Extract the Recipe object from JSON-LD — gives you:
name, recipeYield, totalTime, aggregateRating, recipeCategory, recipeCuisine,
recipeIngredient[], recipeInstructions[], nutrition (per serving).

Recipe discovery: use web_search("site:ica.se/recept {dish name}") to find URLs.

### ICA E-commerce (products + prices) — NOT in v1

Protected by AWS WAF + CSRF token. Requires Playwright to solve the WAF challenge.
Working approach documented in Kronixion/matval's `ica_spider.py`:

1. Launch headless Chromium → navigate to category page
2. Wait for `aws-waf-token` cookie (~5 min TTL) + capture `x-csrf-token`
3. Call: `PUT handlaprivatkund.ica.se/stores/{store_id}/api/webproductpagews/v6/products`
4. Body: `["{productId1}", "{productId2}", ...]` (batch up to 50)

Store IDs: `1003380` (matval default), `1004581` (ICA Kvantum Mall of Scandinavia).
Defer to v2 — Axfood covers product+price needs without WAF complexity.

---

## Coop — public subscription key

### Step 1: Extract key (one regex)

```
GET https://www.coop.se/handla/aktuella-erbjudanden/
→ regex: "personalizationApiSubscriptionKey"\s*:\s*"([0-9a-fA-F]{32})"
```

Key rotates — extract fresh per run. Verified: returns valid 32-hex key.

### Step 2: Category enumeration API (POST)

```
POST https://external.api.coop.se/personalization/search/entities/by-attribute
     ?api-version=v1&store={store_id}&groups=CUSTOMER_PRIVATE&device=desktop&direct=false
Header: Ocp-Apim-Subscription-Key: {key}
Header: Origin: https://www.coop.se
Body: {
  "attribute": {"name": "categoryIds", "value": "{category_uuid}"},
  "requestAlias": {"name": "Subcategory", "value": "{slug}", "details": "{slug}"},
  "resultsOptions": {"skip": 0, "take": 48, "sortBy": [], "facets": []}
}
```

Store IDs: `251300` (Stockholm-area).
Category UUIDs: Coop uses UUIDs, not slugs. Need a mapping (matval ships
`coop_category_ids.json`). **Problem:** free-text search returns 404/empty —
only category enumeration works.

### Coop status: deferred to v2

Key extraction + API plumbing confirmed working (200 OK). But:
- Free-text search is dead (404)
- Category UUID discovery requires browser navigation of the Coop SPA
- Not worth the complexity when Axfood covers the same products

When needed: use browser_* tools to navigate coop.se, extract category tree
from the rendered SPA, build the UUID mapping.
