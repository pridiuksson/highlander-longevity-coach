---
name: research
description: "Search the web with one command. The script picks the right API based on what you need back. Use when you need to search the web, get factual answers, find academic papers, or retrieve page content."
allowed-tools:
  - Bash
argument-hint: "<research-query>"
---

## Do this

Pick a flag based on what you need, then call the script:

```bash
.agents/skills/research/scripts/research.sh --<flag> "your query" [options]
```

Set `cd` to the project root. Set `timeout_ms` to **60000** (this is the Zed agent tool timeout in milliseconds; the script's `--timeout` flag is in seconds — different units).

### Which flag?

| Flag | What you get | When to use | Speed |
|------|-------------|-------------|-------|
| `--answer` | Synthesized answer + citations | Factual Q&A — "What is X?", "When was Y founded?" | ~2s |
| `--links` | Titles + snippets (no full text) | Quick discovery — "find me pages about X" | ~0.4s |
| `--content` | Full page text for each result (empty results tagged `[empty — likely paywalled or JS-rendered]`) | Deep research — "I need to read the full content" | ~1.3s |
| `--scholar` | Academic paper results (enforces 2021+ & peer-reviewed journal IF > 6.0; fallback: pre-2021 IF > 6.0) | Research — "papers about transformer attention", clinical trials, biomarker evidence | ~1.5s |
| `--fresh` | Results from the past week (Brave) | Recent changes — "AWS outage today", price *changes* this week, new releases | ~1.2s |
| `--serp` | Raw Google SERP (knowledge panels, answer boxes) | Current pricing ("How much does Y cost?"), product comparisons, navigational queries | ~0.8s |
| `--repo` | Repo metadata + README + file tree + languages | Analyze a known repo, compare repos, or discover repos by topic | ~2s/repo |
| `--code` | Code search across GitHub repos | "How do people use X?", "find implementations of pattern" | ~1.8s |

### Defaults

- `--content` is your default when you need full page text to reason about. Not for pricing or time-sensitive queries.
- Use `--answer` when you need a single factual answer with citations, not a list of pages.
- Use `--serp` for current pricing and product comparisons — Google surfaces answer boxes with live data.
- Use `--fresh` for recent *changes* — things that happened this week (outages, releases, price updates).
- Use `--links` only when you want to quickly scan what's available before deciding to go deeper.

### Mode guidance

- `--repo` = multi-call aggregation. For each repo it fetches view + readme + tree + languages, all running **in parallel**. Use it to analyze a known repo or discover repos by topic.
- `--code` = thin convenience wrapper around `gh search code`. Useful for finding implementations and usage patterns across GitHub. Supports `--language` filtering.
- `--fresh` = the only fresh-results option. The Zed built-in `fetch` tool retrieves a known URL but does **not** do web search — `--fresh` is how you find what changed this week.

### When results are shallow

If `--content` or `--answer` returns incomplete results on a **multi-dimensional query** (comparisons, broad topics, anything with multiple facets), don't settle — chain another call:

1. Start with `--content` or `--answer` for the broad query
2. If gaps remain, run `--fresh` or `--serp` to discover different sources
3. `fetch` the most authoritative URLs for full content

This discover-then-fetch pattern is your strongest strategy for multi-dimensional queries — it uses multiple backends without any code changes.

### `--repo` modes

The flag auto-detects the mode from your query:

**Known-repo analysis** — query matches `owner/repo` pattern or a GitHub URL:
```bash
research.sh --repo "vercel/next.js"                         # single repo
research.sh --repo "vercel/next.js,remix-run/remix"         # multi-repo comparison
research.sh --repo "https://github.com/vercel/next.js"      # GitHub URL also works
```
Returns: stars, forks, license, language breakdown, README, file tree, homepage. ~2s per repo. Multi-repo comparison runs **in parallel**.

**Topic discovery** — query is a natural-language phrase:
```bash
research.sh --limit 5 --repo "multi-agent debate frameworks"
```
Pipeline: Brave `site:github.com` + `gh search repos` (refined) — both queries run **in parallel** (~1s total) → merge + dedup → analyze top N repos **in parallel**.

Returns: discovery stats (total found, sources, overlap) + per-repo analysis. Use `--limit` to cap repos (default 3, max 10). Higher limits take longer.

**Tip:** Different query phrasings surface different repos. "agent orchestration framework" vs "multi-agent framework" return entirely different results. Try multiple queries for comprehensive coverage.

### `--code` mode

Searches code across GitHub repos — uniquely useful for finding implementations and usage patterns:
```bash
research.sh -n 5 --language python --code "from exa import"
research.sh --language typescript --code "useEffect"
```

### Options

| Option | Purpose | Example |
|--------|---------|---------|
| `-n 5` | Number of results (default: 5 for links/content/scholar, 10 for serp/fresh/code). Not applicable to `--answer` (Exa controls citation count). **Must come BEFORE the mode flag.** | `-n 3 --serp "query"` |
| `--max-chars 3000` | Max chars per result in `--content` / `--repo` mode (default: 3000, 0 = full text). **Must come BEFORE the mode flag.** | `--max-chars 0 --content "query"` |
| `--limit 5` | Max repos to analyze in `--repo` topic mode (default: 3, max: 10) | `--limit 5 --repo "topic"` |
| `--language python` | Language filter for `--code` mode | `--language rust --code "pattern"` |
| `--domains github.com,docs.rs` | Restrict to specific domains (Exa modes + `--fresh` only; ignored for `--serp`/`--scholar`/`--code`/`--repo`) | `--domains arxiv.org --content "query"` |
| `--raw` | Output raw API JSON (unmodified vendor response). Use when you need fields the default formatters drop. | `--raw --serp "query"` |
| `--no-expand` | Disable query expansion for `--serp` / `--scholar` / `--fresh` (expansion is **default-on** for those modes). Use to conserve Serper quota — each expanded query burns ~3 credits vs 1 baseline. Exa is semantic, `--code` is literal, `--repo` has its own hardcoded expansion — all three are unaffected by this flag. | `--no-expand --serp "query"` |
| `--expand` | Backward-compat no-op. Expansion is now default-on for keyword APIs, so this flag is accepted but does nothing. Use `--no-expand` to opt out. | `--expand --serp "query"` (no-op) |
| `--expand-n N` | Number of query variants (2-5, default 3). When N>=4, the last variant swaps ALL detected synonyms at once (max-distance variant) for broader coverage. Only affects `--serp` / `--scholar` / `--fresh`. | `--expand-n 4 --serp "query"` |
| `--min-if 6.0` | Minimum journal impact factor for `--scholar` (default: 6.0). | `--min-if 8.0 --scholar "apob cardiovascular"` |
| `--min-year 2021` | Minimum publication year for primary `--scholar` (default: 2021). | `--min-year 2022 --scholar "creatine renal"` |
| `--all-years` | Search all years without primary 2021+ restriction (still enforces IF > 6.0). | `--all-years --scholar "vo2max mortality"` |
| `--no-filter` | Bypass literature quality criteria filtering on `--scholar` (raw Google Scholar). | `--no-filter --scholar "query"` |
| `--timeout 60` | Script request timeout in **seconds** (default: 30). **Must come BEFORE the mode flag.** | `--timeout 60 --content "query"` |

**Flag ordering matters.** The mode flag (`--answer`, `--links`, `--content`, `--serp`, `--scholar`, `--fresh`, `--repo`, `--code`) always consumes the *next* token as the query. Put other flags BEFORE the mode:
```bash
research.sh --no-expand --serp "kubernetes tutorial"     # ✓ correct
research.sh --serp "kubernetes tutorial" --no-expand     # ✗ --no-expand consumed as query
```

### Academic Paper & Scientific Literature Criteria

When researching health, medical, sports science, biological, or empirical claims, the skill enforces strict literature quality criteria:

**Primary Standard:**
- **2021 onwards** (publication year ≥ 2021)
- **Published in scientific peer-reviewed journals**
- **Impact factor higher than six (Clarivate JCR IF > 6.0)**

**Fallback Standard:**
- Earlier papers (< 2021) are permitted **only if they still possess an impact factor higher than six (IF > 6.0)** in a recognized peer-reviewed journal.

**Disqualification Rules:**
- **Journals with IF ≤ 6.0 are disqualified:** e.g., *Nutrients* (IF ~4.8), *PLOS ONE* (IF ~2.9), *Sleep* (IF ~5.6), *Chronobiology International* (IF ~2.5), *Journal of Biological Rhythms* (IF ~2.9), *Sleep and Breathing* (IF ~2.1), *Journal of Nutrition* (IF ~4.2), *JISSN* (IF ~4.9), *Medicine & Science in Sports & Exercise* (IF ~4.1), *Journal of Applied Physiology* (IF ~3.3), *European Journal of Applied Physiology* (IF ~3.0), *BMC Nephrology* (IF ~2.2).
- **Preprints are disqualified:** *arXiv*, *bioRxiv*, *medRxiv*, *SSRN*, *Research Square* are preprints without peer review. Do not cite them as validated scientific evidence unless confirmed published in a peer-reviewed journal with IF > 6.0.
- **Non-journal sources are disqualified:** Books, conference abstracts without journal status, StatPearls, and blog posts do not qualify.

**How `--scholar` handles this automatically:**
1. Executes primary query with `as_ylo: 2021`.
2. Evaluates each candidate against curated JCR impact factors and OpenAlex citation metrics.
3. If qualifying papers < requested `-n`, automatically triggers pre-2021 fallback search (`as_yhi: 2020`) and filters for IF > 6.0.
4. Clearly labels each result: `[QUALIFIED: 2021+, IF > 6.0]` or `[FALLBACK: Pre-2021, IF > 6.0]`.

### Known URLs → use `fetch` directly

This skill is for **searching**. If you already have a URL, use the built-in `fetch` tool — it's free and faster.

If `fetch` exhausts the subagent's context on large pages, use agy instead — it has built-in context compaction:
```bash
agy --dangerously-skip-permissions --model "Gemini 3.5 Flash (High)" -p "Fetch and summarize https://example.com"
```
Flag order matters: `--dangerously-skip-permissions` must come before `-p` or the model derails.

### `--links` vs `--serp`

They look similar but use different backends:
- `--links` = **Exa neural/semantic ranking**. Finds content by meaning. Better for "find me pages about X".
- `--serp` = **Google SERP**. Returns knowledge panels, answer boxes, and Google-ranked results. Better for navigational queries.

### API keys and prerequisites

Keys are read from `os.environ` first (exported env vars), then `.env` file (walk-up search from the script directory). Exported env vars take precedence.

| Mode | Required | Free tier |
|------|----------|-----------|
| `--answer`, `--links`, `--content` | `EXA_API_KEY` in `.env` or exported env var | 1K queries/month |
| `--serp`, `--scholar` | `SERPER_API_KEY` in `.env` or exported env var | 2.5K one-time credits |
| `--fresh` | `BRAVE_API_KEY` in `.env` or exported env var | 2K queries/month |
| `--repo` | `gh` CLI + `gh auth login` | 5K API calls/hr |
| `--code` | `gh` CLI + `gh auth login` | 10 code searches/min |
| `--repo` (Brave discovery) | `BRAVE_API_KEY` (optional — falls back to gh-only) | 2K queries/month |

### Error handling

The script exits with an actionable error on stderr. Read it and decide:
- **HTTP 429/503**: API rate-limited. Wait 60s or switch to a different flag (e.g., `--serp` instead of `--links`).
- **"API key not set"**: Missing from `.env`. Tell the user which key is needed.
- **HTTP 401**: Invalid API key. Check `.env`.
- **"gh CLI not found"**: Install gh CLI and run `gh auth login`.
- **"gh CLI not authenticated"**: Run `gh auth login`. Required for `--repo` and `--code` (even for public repos).

### Multi-step research

For compound tasks, chain multiple calls. Two common patterns:

**Discover → fetch** (best for pricing, comparisons, broad topics):
```bash
# Step 1: Discover current sources via --serp or --fresh
research.sh --fresh "OCI vs AWS free tier pricing changes 2025"

# Step 2: Fetch full content from the most authoritative URLs
# (use the built-in fetch tool — it's free and faster)
```

**Broad → narrow** (best for technical deep-dives):
```bash
# Step 1: Get broad coverage
research.sh --content "Exa API search types and parameters"

# Step 2: If shallow, try a different backend or more specific query
research.sh --serp "Exa API documentation search type parameter"

# Step 3: Fetch the best URL for full content
```

**Repo analysis** (discover → code search → compare):
```bash
research.sh --limit 3 --repo "Rust async runtime"
research.sh -n 5 --language rust --code "tokio::spawn"
research.sh --content "tokio vs smol vs async-std comparison"
```

### Fact-checking workflow

When verifying a specific claim from a document, **fetch the exact cited source — do not search for the topic.** This is the #1 error in fact-checking: searching for the topic and trusting the first plausible source instead of checking what the document actually references.

**Step 1 — Identify the cited source.** What URL, repo, PR, or model card does the document reference for this claim?

**Step 2 — Fetch that source directly.**
```bash
# Document claims "PR #1142 is a 5-line fix" → check the actual PR:
fetch https://github.com/ml-explore/mlx-lm/pull/1142

# Document claims "Ollama has gemma4:26b-mlx tag" → check the product page:
fetch https://ollama.com/library/gemma4

# Document cites benchmark numbers → fetch the raw data, not just the README
# (README summary tables are frequently stale)
```

**Step 3 — Cross-reference.** Find at least one independent source that agrees or disagrees.

**Step 4 — Report confidence:**
- `CONFIRMED` — primary source matches exactly
- `LIKELY` — secondary source agrees, primary not directly accessible
- `MISMATCH` — source disagrees (explain how)
- `UNVERIFIED` — could not access any authoritative source

**For orchestrating agents spawning fact-check subagents:**
Always include the **specific source URL** and **what to look for** in the subagent prompt. Don't ask "verify X" — ask "fetch URL Y and check if it says X." This prevents subagents from checking the wrong source.

### Source reliability pitfalls

| Source type | Risk | Mitigation |
|-------------|------|------------|
| README summary tables | Frequently stale vs raw data. Incept5 README showed 113 t/s; actual `bench_all_results.json` showed 116.5 | Fetch raw data files (`*.json`, `BENCHMARK_REPORT.md`) not just the README |
| GitHub PR descriptions | Reflect development state, not current release. TurboQuant PRs showed slowdowns in early impl; Metal kernel optimizations brought speedups later | Check if the PR was merged, what version shipped, and whether later commits changed behavior |
| Vendor/marketing docs | Best-case benchmarks on favorable configs. Unsloth's UD-Q4_K_XL docs benchmark dense models; independent tests show it's worse on MoE | Find independent third-party benchmarks; check if the vendor's test config matches your use case |
| Product pages (Ollama library, etc.) | Authoritative for features/tags/capabilities | Fetch directly via URL — don't rely on search results or GitHub issues to determine if a product feature exists |
| JS-rendered pages (leaderboards, etc.) | Different tools see different content; `fetch` may get empty/page-shell | Try multiple tools (`fetch`, agy, `--serp`) and flag uncertainty. agy's browser rendering is most reliable |
| Reddit threads | Blocked to automated access (403) | Use `--fresh` or `--serp` to find references; use agy for content; don't rely on direct fetch |

### Resolving contradictions

When two sources disagree:

1. **Prefer primary over secondary.** Raw data > README. Official model card > mirror site. The actual product page > a GitHub issue about the product.
2. **Check dates.** Newer sources may reflect updates (bug fixes, new releases).
3. **Use agy as independent tiebreaker.** Give it both claims and the URLs, ask it to fetch and resolve:
```bash
agy --dangerously-skip-permissions --model "Gemini 3.5 Flash (High)" -p "Source A says X (URL). Source B says Y (URL). Fetch both and tell me which is correct."
```
4. **When still uncertain, report both findings** rather than picking one. State which source is more authoritative and why.

### Query expansion (default-on for keyword APIs)

**Expansion runs automatically** on `--serp`, `--scholar`, and `--fresh` queries. The query is rewritten into 2-3 keyword variants using a curated 32-entry synonym table, variants run in parallel, results merge + dedupe by URL, and URLs found by 2+ variants get a corroboration score boost and sort to the top.

Benchmarked: **10/10 test queries improved**, avg 1.88× recall, avg 1.28× latency vs baseline.

```bash
# No flag needed — expansion is on by default for these modes.
research.sh --serp "agent orchestration framework"
#   stderr: Expanding query into 2 variants: "agent orchestration framework" | "bot orchestration framework"
#   (query has 1 synonym-bearing token → 2 variants, not 3)

# Opt out to conserve Serper quota (each expanded query burns ~3 credits vs 1).
research.sh --no-expand --serp "agent orchestration framework"

# Force a max-distance variant (swaps ALL synonyms at once) with n>=4.
# Useful when you want orthogonal coverage rather than near-miss variants.
research.sh --expand-n 4 --serp "agent orchestration framework"
#   Variants: original, "bot orchestration framework", "agent coordination framework",
#             "bot coordination framework"  ← max-distance
```

**Modes unaffected by expansion:**
- `--content` / `--links` / `--answer` (Exa is semantic — handles natural language natively)
- `--code` (code patterns are literal strings; synonym substitution corrupts them)
- `--repo` (has its own hardcoded multi-query expansion internally)

**Synonym table** lives at `scripts/research.py::_SYNONYMS` (~32 curated entries, organized by category: concepts, architecture, learning content, interfaces, storage, security, ops, containers/IaC, AI/ML, ingest). Each entry has an inline comment documenting why that synonym was kept. Audit header documents what was dropped and why (`kubernetes→k8s` as a Google-equivalent abbreviation, `docker→container` as too broad, `llm→gpt` as brand bias, etc.). Add new entries following the same convention: a short inline rationale and a "would this retrieve noise?" check.

**When to `--no-expand`:**
- Serper quota is low (credits are one-time 2.5K, not monthly)
- You need deterministic single-query output (regression tests, benchmarks against a fixed baseline)
- You've already verified a query works well without expansion
- You want to control keyword selection yourself — call the skill, reflect on results, reformulate the query manually

## When to Use

- When you need web data you don't have in the codebase
- When the user asks a factual question that requires current information
- When researching technologies, libraries, or services
- When finding documentation or API references
- When analyzing or comparing GitHub repos
- When searching for code patterns across GitHub
- When `fetch` returns empty or a page shell, use agy --dangerously-skip-permissions -p "Fetch and summarize https://example.com" - give it at least a 5 minute timeout - **agy renders JS-heavy pages** that `fetch` and `--content` cannot (leaderboards, product pages).

## When NOT to Use

- Known URLs → use `fetch` directly
- Codebase search → use `grep` / `find_path`
- Adversarial fact-checking → use `@grill`
- Quick gut check → use `@peer-review`
- Multi-hop synthesis → use Agy CLI directly (see `Knowledge/Research/Tech/search-apis.md` for model tier routing)

### Agy fallback for deep research and cross-verification

agy is a general-purpose AI agent with web browsing, built-in context compaction, and tool access. It serves two roles alongside this skill: (1) **deep research** when subagents run out of context on large pages, and (2) **independent cross-verification** when sources conflict or subagent results seem wrong.

#### Usage

```bash
# Deep research / context compaction (fetches large pages without exhausting context)
agy --dangerously-skip-permissions --model "Gemini 3.5 Flash (High)" -p "Fetch and summarize https://example.com"

# Cross-verification (resolve contradictions between sources)
agy --dangerously-skip-permissions --model "Gemini 3.5 Flash (High)" -p "Source A claims X (URL1). Source B claims Y (URL2). Fetch both and tell me which is correct."
```

**Flag order matters.** `--dangerously-skip-permissions` must come *before* `-p` — if reversed, the model treats the flag text as the prompt and derails. Model takes time and requires at least a 5 minute timeout.

#### Tips

- **Keep prompts focused and direct.** Complex multi-part prompts cause agy (especially Claude Sonnet) to spawn its own subagents, which adds 2-3× latency and timeout risk. One focused question per invocation.
- **Add "do not spawn subagents"** to reduce overhead — agy may still do so, but less often.
- **Use agy as a tiebreaker**, not a primary research tool but only when the research skill and subagents disagree.
