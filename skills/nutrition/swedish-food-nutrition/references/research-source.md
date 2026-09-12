# Swedish Grocery APIs — Original Research

Source research document that informed this skill. Verified 2026-06-20.
Preserved here for maintenance context — when endpoints break or chains change,
the analysis patterns and GitHub repo references below are the starting point.

## TL;DR routing

| Need | Tool | Notes |
|------|------|-------|
| Recipe ingredients (Swedish, with quantities) | `fetch`/curl on `ica.se/recept/{slug}` | No API needed — ICA recipe pages are static HTML |
| Product search + price + nutrition (Hemköp/Willys) | Axfood JSON API | No auth. Easiest target |
| Product search + price + nutrition (Coop) | Coop personalization API | Public subscription key (auto-extracted) |
| Product search + price (ICA e-commerce) | ICA `webproductpagews` API | Needs AWS WAF token + CSRF — requires Playwright |

Why API, not page fetching: every chain's product page is a JS-rendered SPA.
A page fetcher gets empty/chrome output. The JSON API tier returns structured
data in milliseconds, for free, without hallucination.

## Community source repos

| Repo | Stars | What it gives you | Status |
|------|-------|-------------------|--------|
| **Kronixion/matval** | 3 (low stars, high quality) | Working Scrapy spiders for all 5 chains + an MCP server (`shelfwatch`). MIT. The primary reference. | Active, last push 2026-04 |
| **svendahlstrand/ica-api** | 175 | Reference docs for ICA's `handla.api.ica.se` API | Broken since April 2024 — ICA changed the API |
| `whame/parsewillya` | 0 | Parses Willys receipts (PDF), not products | Niche — post-shop reconciliation |

How to use these repos:
1. Start with matval's spider for the chain you need — it shows the exact endpoint, headers, auth, and robots.txt constraints.
2. Treat svendahlstrand/ica-api as historical context for ICA only; verify against live before trusting.
3. When an endpoint breaks (HTTP 404/403/empty JSON), re-pull the spider source from matval.

## API patterns by chain

### Hemköp & Willys (Axfood) — no auth

Axfood runs Hemköp and Willys on a shared backend. Same endpoints, different domain.
No API key, no login. Just needs browser-like headers.

**Search:**
```
GET https://www.hemkop.se/search?q={query}&page=0&size=20
GET https://www.willys.se/search?q={query}&page=0&size=20
```

**Product detail (with nutrition + ingredients):**
```
GET https://www.hemkop.se/axfood/rest/p/{code}?include=BREADCRUMB,NUTRIENTS
GET https://www.willys.se/axfood/rest/p/{code}?include=BREADCRUMB,NUTRIENTS
```

Returns 80+ fields including ingredients, nutrientHeaders, nutritionsFactList,
originCountry, storage temps, outOfStock.

Nutrition field: use `nutrientHeaders[].nutrientDetails[]` first (full macro
breakdown). Fall back to `nutritionsFactList` only if empty. See
references/nutrition_fields.md for the verified shape.

Fresh produce gap: loose Class 1 produce returns an empty nutrition payload —
the stores don't attach GS1 nutrition data to unpackaged goods.

**Category enumeration:**
```
GET https://www.hemkop.se/c/{slug}?page=0&size=100&sort=topRated
```

robots.txt: Crawl-delay: 10, Visit-time: 0400-0845 UTC.

### Coop — public subscription key

Coop's API sits behind Azure API Management.

Step 1 — extract key:
```
GET https://www.coop.se/handla/aktuella-erbjudanden/
→ regex: "personalizationApiSubscriptionKey"\s*:\s*"([0-9a-fA-F]{32})"
```

Step 2 — category enumeration (POST):
```
POST https://external.api.coop.se/personalization/search/entities/by-attribute
     ?api-version=v1&store={store_id}&groups=CUSTOMER_PRIVATE&device=desktop&direct=false
Header: Ocp-Apim-Subscription-Key: {key}
Body: {
  "attribute": {"name": "categoryIds", "value": "{category_uuid}"},
  "requestAlias": {"name": "Subcategory", "value": "{slug}", "details": "{slug}"},
  "resultsOptions": {"skip": 0, "take": 48, "sortBy": [], "facets": []}
}
```

Free-text search NOT verified — returns 404/empty. Only category enumeration works.
Category UUIDs need discovery from the Coop SPA (browser navigation).

### ICA e-commerce — needs Playwright for WAF

AWS WAF + CSRF token. Working approach (from matval's ica_spider.py):

1. Launch headless Chromium, navigate to category page
2. Wait for aws-waf-token cookie (~5 min TTL) + capture x-csrf-token
3. Call: PUT handlaprivatkund.ica.se/stores/{store_id}/api/webproductpagews/v6/products
4. Body: ["{productId1}", "{productId2}", ...] (batch up to 50 IDs)

Hermes has browser_* tools backed by Playwright — the right tool for this.
Do NOT use AI summarizers here — they confabulate prices when the WAF blocks them.

### ICA recipes — static HTML

ica.se/recept/{slug} pages are server-rendered HTML with JSON-LD blocks.
curl + regex extraction works perfectly. No API needed.

## Anti-patterns

- Don't use page fetchers on Coop/Hemköp/Willys product or search pages (JS SPAs).
- Don't trust AI-sourced prices without verification. When an AI hits a WAF/login
  wall it invents plausible-looking prices. The JSON API either returns data or
  returns an error — no middle ground.
- Don't hardcode the Coop subscription key. It's public but rotates.
- Don't automate carts. All chains' robots.txt forbid it.
- Don't trust svendahlstrand/ica-api endpoints blindly. Broken since April 2024.
- Don't ignore Crawl-delay. Axfood specifies 10s + a 0400-0845 UTC visit window.

## Maintenance

- When an endpoint breaks: re-pull the relevant spider from Kronixion/matval.
- When a key rotates: Coop key auto-extracts; ICA WAF token auto-refreshes via Playwright.
- Legal/ToS: these are unofficial APIs. Personal, low-volume use is tolerated;
  robots.txt sets the polite boundary.
- Verify before relying: run scripts/verify.py as a smoke test.
