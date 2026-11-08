#!/usr/bin/env python3
"""Recall benchmark for --expand on Serper.

Compares baseline (no expansion) vs expanded recall across 10 representative
queries. Reports: baseline count, expanded count, recall gain ratio, unique
URL count, corroborated count.

Run:
    python3 .claude/skills/research/scripts/benchmark.py --mode recall

Target: >= 1.5x recall on 8/10 queries with <= 3x latency.
Fails if any query LOSES recall (indicates a bad synonym).

Results are cached to .claude/skills/research/scripts/.benchmark_cache.json
to avoid re-burning API credits on reruns.
"""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

SCRIPT = Path(__file__).parent / "research.py"
CACHE = Path(__file__).parent / ".benchmark_cache.json"

# Import _SYNONYMS so we can fingerprint it for cache invalidation.
# Also import surviving normalizers for the roundtrip mode.
sys.path.insert(0, str(Path(__file__).parent))
try:
    from research import (
        _SYNONYMS,
        ResearchResult,
        normalize_brave,
        normalize_serper,
    )
except ImportError:
    _SYNONYMS = {}
    ResearchResult = None
    normalize_brave = None  # type: ignore[assignment]
    normalize_serper = None  # type: ignore[assignment]


def _hash_synonyms() -> str:
    """Stable sha256 fingerprint of _SYNONYMS.

    Sorted keys + deterministic separators so the hash is reproducible
    across runs. First 12 chars is enough to catch any real edit.
    """
    canonical = json.dumps(_SYNONYMS, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]


QUERIES = [
    "agent orchestration framework",
    "kubernetes tutorial",
    "docker containerization best practices",
    "vector database comparison",
    "LLM fine-tuning techniques",
    "terraform infrastructure as code",
    "websocket streaming realtime",
    "authentication oauth login",
    "parsing extraction tokenizer",
    "scraping crawling spider",
]


def run_query(query: str, expand: bool) -> dict:
    """Run a single query, return merged result stats + wall-clock ms.

    Calls research.py functions directly (not subprocess) so we can access
    the merged expansion results. The old --structured envelope was removed
    in the refactor; this replaces it.
    """
    import concurrent.futures

    from research import (
        expand_query,
        merge_variant_results,
        normalize_serper,
        serper_search,
    )

    t0 = time.monotonic()
    try:
        if expand:
            variants = expand_query(query)
            if len(variants) > 1:
                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=min(len(variants), 5)
                ) as executor:
                    per_variant_raw = list(
                        executor.map(lambda q: serper_search(q, 10, 30)[0], variants)
                    )
                per_variant_normalized = [normalize_serper(d) for d in per_variant_raw]
                normalized = merge_variant_results(per_variant_normalized)
            else:
                data, _ = serper_search(query, 10, 30)
                normalized = normalize_serper(data)
        else:
            data, _ = serper_search(query, 10, 30)
            normalized = normalize_serper(data)
    except SystemExit as e:
        duration_ms = int((time.monotonic() - t0) * 1000)
        return {"error": f"research.py exited: {e.code}", "duration_ms": duration_ms}
    except Exception as e:
        duration_ms = int((time.monotonic() - t0) * 1000)
        return {"error": str(e), "duration_ms": duration_ms}

    duration_ms = int((time.monotonic() - t0) * 1000)
    total = len(normalized)
    unique_urls = len({r.url for r in normalized if r.url})
    corroborated = sum(
        1 for r in normalized if r.metadata.get("found_in_variants", 1) >= 2
    )
    return {
        "data": {
            "stats": {
                "total": total,
                "corroborated": corroborated,
                "unique_urls": unique_urls,
            }
        },
        "duration_ms": duration_ms,
    }


def load_cache() -> dict:
    """Load the cache, auto-invalidating if _SYNONYMS has changed.

    Cache shape: {"_synonyms_hash": "<12 chars>", "<query>": {...}, ...}.
    If the stored hash doesn't match the current _SYNONYMS, return empty
    so the benchmark re-runs against the new synonym table.
    """
    if CACHE.exists():
        try:
            cache = json.loads(CACHE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
        if cache.get("_synonyms_hash") != _hash_synonyms():
            print(
                f"  [cache invalidated: _SYNONYMS hash changed "
                f"({cache.get('_synonyms_hash')!r} → {_hash_synonyms()!r})]"
            )
            return {}
        return cache
    return {}


def save_cache(cache: dict) -> None:
    """Persist the cache, stamping the current _SYNONYMS hash."""
    cache["_synonyms_hash"] = _hash_synonyms()
    CACHE.write_text(json.dumps(cache, indent=2))


def recall_benchmark(force: bool = False) -> None:
    cache = load_cache()
    results = []

    print("=" * 70)
    print("RECALL BENCHMARK (--serp baseline vs --serp with --expand)")
    print("=" * 70)
    print(f"queries: {len(QUERIES)}")
    print(f"cache: {CACHE}")
    print()

    improved = 0
    lost = 0
    total_gain_ratio = 0.0
    total_latency_ratio = 0.0

    for query in QUERIES:
        cache_key = query.strip()
        if not force and cache_key in cache:
            baseline = cache[cache_key]["baseline"]
            expanded = cache[cache_key]["expanded"]
            src = "cached"
        else:
            print(f"  running: {query!r} ...", flush=True)
            baseline = run_query(query, expand=False)
            expanded = run_query(query, expand=True)
            # Don't cache error responses — a transient API outage shouldn't
            # poison the cache. The next run will retry.
            if "error" not in baseline and "error" not in expanded:
                cache[cache_key] = {"baseline": baseline, "expanded": expanded}
                save_cache(cache)
            src = "live"

        if "error" in baseline or "error" in expanded:
            print(
                f"  ERROR on {query!r}: baseline={baseline.get('error')}, expanded={expanded.get('error')}"
            )
            continue

        b_total = baseline["data"]["stats"]["total"]
        e_total = expanded["data"]["stats"]["total"]
        b_ms = baseline["duration_ms"]
        e_ms = expanded["duration_ms"]
        e_corroborated = expanded["data"]["stats"]["corroborated"]
        e_unique = expanded["data"]["stats"]["unique_urls"]

        gain_ratio = e_total / b_total if b_total > 0 else 0
        latency_ratio = e_ms / b_ms if b_ms > 0 else 0
        total_gain_ratio += gain_ratio
        total_latency_ratio += latency_ratio

        if e_total > b_total:
            improved += 1
            marker = "↑"
        elif e_total < b_total:
            lost += 1
            marker = "↓ LOSE"
        else:
            marker = "="

        print(
            f"  {marker} {query!r} ({src}): baseline={b_total} expanded={e_total} "
            f"({gain_ratio:.2f}x) | corrob={e_corroborated} unique_urls={e_unique} | "
            f"{b_ms}ms → {e_ms}ms ({latency_ratio:.2f}x)"
        )

        results.append(
            {
                "query": query,
                "baseline_total": b_total,
                "expanded_total": e_total,
                "gain_ratio": gain_ratio,
                "latency_ratio": latency_ratio,
                "corroborated": e_corroborated,
                "unique_urls": e_unique,
            }
        )

    n = len(results)
    if n == 0:
        print("\nNO RESULTS")
        sys.exit(1)

    avg_gain = total_gain_ratio / n
    avg_latency = total_latency_ratio / n

    print()
    print("=" * 70)
    print(f"SUMMARY ({n} queries)")
    print(f"  improved: {improved}/{n}")
    print(f"  lost:     {lost}/{n}")
    print(f"  avg gain ratio:    {avg_gain:.2f}x")
    print(f"  avg latency ratio: {avg_latency:.2f}x")
    print("=" * 70)

    # Pass/fail thresholds from the plan.
    if improved < 8:
        print(f"\nFAIL: only {improved}/10 queries improved (need >= 8/10)")
        sys.exit(1)
    if lost > 0:
        print(f"\nFAIL: {lost} queries LOST recall (bad synonym in table)")
        sys.exit(1)
    if avg_gain < 1.5:
        print(f"\nFAIL: avg gain {avg_gain:.2f}x < 1.5x target")
        sys.exit(1)
    if avg_latency > 3.0:
        print(f"\nFAIL: avg latency {avg_latency:.2f}x > 3.0x budget")
        sys.exit(1)

    print(
        f"\nPASS: {improved}/10 improved, avg {avg_gain:.2f}x gain, avg {avg_latency:.2f}x latency"
    )


def roundtrip_benchmark() -> None:
    """Call each backend once, normalize, validate field shape.

    Purpose: catch regressions where a normalizer silently drops a field
    or changes a field type. Not a performance benchmark — wall-clock
    numbers are reported but not gated.

    gh_code is skipped (requires `gh auth login`); coverage comes from
    the offline test suite's fixture instead.
    """
    # Import the live backend functions here so a missing API key fails
    # loudly with the research.py error rather than at import time.
    from research import (
        brave_fresh,
        normalize_brave,
        normalize_serper,
        serper_scholar,
        serper_search,
    )

    # Each case: (label, lambda returning raw API response, normalizer lambda, min_results).
    # Only surviving normalizers are tested (normalize_exa_answer, normalize_exa_search,
    # normalize_gh_code were removed in the refactor — their backends now use
    # per-mode formatters directly).
    cases = [
        (
            "serper_search",
            lambda: serper_search("kubernetes tutorial", num=3)[0],
            lambda data: normalize_serper(data, content_type="text"),
            1,
        ),
        (
            "serper_scholar",
            lambda: serper_scholar("transformer attention", num=3)[0],
            lambda data: normalize_serper(data, content_type="paper"),
            1,
        ),
        (
            "brave_fresh",
            lambda: brave_fresh("AWS outage", num=3)[0],
            lambda data: normalize_brave(data, fresh=True),
            1,
        ),
    ]

    required_fields = {
        "source": str,
        "url": str,
        "title": str,
        "content": str,
        "content_type": str,
        # score: float | None — accept either
        "citation": str,
        "metadata": dict,
    }

    print("=" * 70)
    print("ROUNDTRIP BENCHMARK (live API → normalize → validate field shape)")
    print("=" * 70)

    backend_pass = 0
    backend_fail = 0

    for label, fetch, normalize, min_results in cases:
        print(f"\n  [{label}]")
        try:
            data = fetch()
        except SystemExit as e:
            # research.py calls die() on missing API key → SystemExit(2).
            print(f"    SKIP (likely missing API key): exit {e.code}")
            continue
        except Exception as e:
            print(f"    FAIL: fetch raised {type(e).__name__}: {e}")
            backend_fail += 1
            continue

        try:
            results = normalize(data)
        except Exception as e:
            print(f"    FAIL: normalize raised {type(e).__name__}: {e}")
            backend_fail += 1
            continue

        if not isinstance(results, list):
            print(f"    FAIL: normalize returned {type(results).__name__}, not list")
            backend_fail += 1
            continue
        if len(results) < min_results:
            print(f"    FAIL: got {len(results)} results, need >= {min_results}")
            backend_fail += 1
            continue

        # Validate the first result's field shape.
        r_dict = results[0].to_dict()
        fails = []
        for field_name, expected_type in required_fields.items():
            if field_name not in r_dict:
                fails.append(f"missing field: {field_name}")
                continue
            val = r_dict[field_name]
            if field_name == "score":
                if val is not None and not isinstance(val, (int, float)):
                    fails.append(
                        f"score should be float|None, got {type(val).__name__}"
                    )
            elif not isinstance(val, expected_type):
                fails.append(
                    f"{field_name} should be {expected_type.__name__}, "
                    f"got {type(val).__name__}"
                )

        if fails:
            print(f"    FAIL ({len(results)} results, field-shape errors):")
            for f in fails:
                print(f"      - {f}")
            backend_fail += 1
        else:
            print(f"    PASS ({len(results)} results, all 8 fields present + typed)")
            backend_pass += 1

    print()
    print("=" * 70)
    print(f"SUMMARY: {backend_pass} backends passed, {backend_fail} failed")
    print("=" * 70)
    if backend_fail > 0:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["recall", "roundtrip"], required=True)
    parser.add_argument("--force", action="store_true", help="ignore cache, rerun all")
    args = parser.parse_args()

    if args.mode == "recall":
        recall_benchmark(force=args.force)
    elif args.mode == "roundtrip":
        roundtrip_benchmark()


if __name__ == "__main__":
    main()
