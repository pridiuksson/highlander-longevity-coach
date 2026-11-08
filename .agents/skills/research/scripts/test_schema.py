#!/usr/bin/env python3
"""Offline smoke tests for the Tier 2 features (schema + expansion).

Run from project root:
    python3 .claude/skills/research/scripts/test_schema.py

Tests run WITHOUT calling any external API — they exercise the rule-based
expansion, the ResearchResult dataclass, the normalizers against fixture
data, and merge_variant_results against synthetic inputs.


"""

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

sys.path.insert(0, str(SCRIPT_DIR))
from research import (  # noqa: E402
    ResearchResult,
    _canonical_url,
    _dedup_by_url_field,
    _evaluate_paper,
    _journal_matches_prefix,
    _parse_pub_info,
    _title_overlap,
    expand_query,
    format_expansion_results,
    lookup_journal_impact_factor,
    merge_variant_results,
    normalize_brave,
    normalize_serper,
)

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}  — {detail}")
        FAILURES.append(name)


def test_expand_query():
    """Rule-based expansion produces expected variants."""
    print("[expand_query]")
    v = expand_query("agent orchestration framework", n=3)
    check(
        "returns 3 variants for 2-synonym query",
        len(v) == 3,
        f"got {v}",
    )
    check(
        "variant 1 is the original query unchanged (casing + stopwords preserved)",
        v[0] == "agent orchestration framework",
        f"v[0]={v[0]!r}",
    )
    check(
        "swaps 'agent' → 'bot' in variant 2 (first synonym)",
        "bot" in v[1] and "agent" not in v[1].split(),
        f"v[1]={v[1]!r}",
    )
    check(
        "swaps 'orchestration' → 'coordination' in variant 3",
        "coordination" in v[2],
        f"v[2]={v[2]!r}",
    )

    # Max-distance variant with n=4: last variant swaps ALL synonyms at once.
    v4 = expand_query("agent orchestration framework", n=4)
    check(
        "n=4 returns 4 variants (2 near + 1 max-distance)",
        len(v4) == 4,
        f"got {v4}",
    )
    check(
        "variant 4 (max-distance) swaps BOTH synonyms at once",
        "bot" in v4[3] and "coordination" in v4[3],
        f"v4[3]={v4[3]!r}",
    )
    check(
        "max-distance variant is distinct from every near-variant",
        v4[3] not in v4[:3],
        f"v4[3] collides with near-variants: {v4}",
    )

    # Max-distance with 3+ synonym-bearing tokens: all 3+ swap at once.
    v_multi = expand_query("agent orchestration framework api tutorial", n=4)
    check(
        "n=4 with 5 synonyms returns 4 variants (2 near + 1 max-distance)",
        len(v_multi) == 4,
        f"got {v_multi}",
    )
    check(
        "max-distance variant swaps ALL synonym-bearing tokens (≥3)",
        all(
            tok in v_multi[3]
            for tok in ("bot", "coordination", "library", "sdk", "guide")
        ),
        f"v_multi[3]={v_multi[3]!r}",
    )

    # Synonym-miss: no expansion, just the original.
    v_miss = expand_query("zygomatic bone anatomy", n=3)
    check(
        "synonym-miss returns single variant (graceful no-op)",
        len(v_miss) == 1,
        f"got {v_miss}",
    )

    # n=5 cap.
    v_many = expand_query("agent orchestration framework api database tutorial", n=5)
    check(
        "n=5 caps at 5 variants",
        len(v_many) <= 5,
        f"got {len(v_many)}",
    )


def test_research_result_to_dict():
    """ResearchResult.to_dict() produces a JSON-serializable dict."""
    print("[ResearchResult.to_dict]")
    r = ResearchResult(
        source="serper",
        url="https://example.com",
        title="Example",
        content="Snippet text.",
        content_type="text",
        score=0.85,
        citation="Example — https://example.com",
        metadata={"position": 1},
    )
    d = r.to_dict()
    check("is dict", isinstance(d, dict))
    check("has all 8 fields", len(d) == 8)
    check("JSON serializable", json.dumps(d) is not None)
    check("metadata preserved", d["metadata"] == {"position": 1})


def test_normalize_serper():
    print("[normalize_serper]")
    fixture = {
        "knowledgeGraph": {"title": "Python", "description": "Programming language"},
        "answerBox": {
            "snippet": "Python is a high-level language",
            "link": "https://python.org",
        },
        "organic": [
            {
                "title": "Python.org",
                "link": "https://python.org",
                "snippet": "Welcome",
                "position": 1,
            },
            {
                "title": "Wikipedia",
                "link": "https://en.wikipedia.org/wiki/Python",
                "snippet": "Python...",
                "position": 2,
            },
        ],
    }
    results = normalize_serper(fixture, content_type="text")
    check("produces 4 results (KP + AB + 2 organic)", len(results) == 4)
    check(
        "KP has content_type=knowledge_panel",
        results[0].content_type == "knowledge_panel",
    )
    check("AB has content_type=answer", results[1].content_type == "answer")
    check("organic has score=None (no real relevance signal)", results[2].score is None)
    check(
        "organic pos 1 position_score = 0.95 in metadata",
        results[2].metadata.get("position_score") == 0.95,
    )
    check(
        "organic pos 2 position_score = 0.9 in metadata",
        results[3].metadata.get("position_score") == 0.9,
    )

    # Scholar content_type
    paper_fixture = {
        "organic": [
            {
                "title": "Attention",
                "link": "https://arxiv.org",
                "snippet": "s",
                "position": 1,
                "year": "2017",
                "publicationInfo": "Vaswani et al",
                "citedBy": "100000",
            },
        ]
    }
    papers = normalize_serper(paper_fixture, content_type="paper")
    check("paper content_type", papers[0].content_type == "paper")
    check(
        "paper metadata has year/authors/cited_by",
        papers[0].metadata.get("year") == "2017"
        and papers[0].metadata.get("authors") == "Vaswani et al"
        and papers[0].metadata.get("cited_by") == "100000",
    )


def test_normalize_brave():
    print("[normalize_brave]")
    fixture = {
        "web": {
            "results": [
                {
                    "title": "A",
                    "url": "https://a.com",
                    "description": "snippet a",
                    "age": "2 days ago",
                },
                {"title": "B", "url": "https://b.com", "description": "snippet b"},
            ]
        }
    }
    fresh = normalize_brave(fixture, fresh=True)
    check(
        "fresh flag sets metadata.freshness_filter",
        fresh[0].metadata.get("freshness_filter") == "pw",
    )
    check("age in metadata", fresh[0].metadata.get("age") == "2 days ago")
    non_fresh = normalize_brave(fixture, fresh=False)
    check(
        "non-fresh omits freshness_filter",
        "freshness_filter" not in non_fresh[0].metadata,
    )


def test_merge_variant_results():
    """Test dedup, corroboration boost, empty-URL guard, off-by-one fix."""
    print("[merge_variant_results]")

    def mk(source, url, title, score=0.5):
        return ResearchResult(
            source=source,
            url=url,
            title=title,
            content="x",
            content_type="text",
            score=score,
            citation=f"{title} — {url}",
        )

    # Case 1: same URL across 2 variants → corroboration + boost.
    v1 = [
        mk("serper", "https://a.com", "A", 0.7),
        mk("serper", "https://b.com", "B", 0.6),
    ]
    v2 = [
        mk("serper", "https://a.com", "A", 0.8),
        mk("serper", "https://c.com", "C", 0.5),
    ]
    merged = merge_variant_results([v1, v2])
    check("3 unique URLs after dedup", len(merged) == 3)
    top = merged[0]
    check("corroborated URL sorts to top", top.url == "https://a.com")
    check(
        "corroborated has found_in_variants=2",
        top.metadata.get("found_in_variants") == 2,
    )
    check(
        "score boosted to max+0.05 (0.8+0.05=0.85)",
        top.score is not None and abs(top.score - 0.85) < 1e-6,
        f"got {top.score}",
    )

    # Case 2: empty URL (synthesized answer) is never deduped.
    ans1 = ResearchResult(
        source="exa",
        url="",
        title="Answer 1",
        content="c1",
        content_type="answer",
        score=None,
        citation="exa /answer (5 citations)",
    )
    ans2 = ResearchResult(
        source="exa",
        url="",
        title="Answer 1",
        content="c1",
        content_type="answer",
        score=None,
        citation="exa /answer (5 citations)",
    )
    merged_answers = merge_variant_results([[ans1], [ans2]])
    check(
        "empty-URL results are NOT deduped (both preserved)",
        len(merged_answers) == 2,
        f"got {len(merged_answers)}",
    )

    # Case 3: single-source items have found_in_variants=1 (off-by-one fix).
    single = merge_variant_results([[mk("serper", "https://x.com", "X", 0.5)]])
    check(
        "first occurrence seeded with found_in_variants=1",
        single[0].metadata.get("found_in_variants") == 1,
    )

    # Case 4: malformed fixture — None element surfaces the error loudly
    # instead of silently producing corrupted output.
    try:
        merge_variant_results([[None]])  # type: ignore[arg-type]
        check(
            "None element raises (not silent corruption)", False, "no exception raised"
        )
    except AttributeError:
        check("None element raises AttributeError", True)


def test_normalize_serper_metadata():
    """normalize_serper curates metadata — drops bloat from raw API response."""
    print("[normalize_serper metadata curation]")
    # Fixture includes fields that should NOT leak into metadata (imageUrl,
    # attributes, descriptionSource) — verifies A4 fix holds.
    fixture = {
        "knowledgeGraph": {
            "title": "Python",
            "description": "Programming language",
            "descriptionLink": "https://python.org",
            "imageUrl": "https://example.com/python.png",  # should be dropped
            "attributes": {"paradigm": "multi-paradigm"},  # should be dropped
            "descriptionSource": "Wikipedia",  # should be dropped
        },
        "answerBox": {
            "title": "Python Release",
            "snippet": "Python 3.14",
            "link": "https://python.org/downloads",
            "date": "October 2025",  # should be dropped
        },
        "organic": [
            {
                "title": "Python.org",
                "link": "https://python.org",
                "snippet": "Welcome",
                "position": 1,
            },
        ],
    }
    results = normalize_serper(fixture, content_type="text")

    # KP: curated to title/description/link only.
    kp = next(r for r in results if r.content_type == "knowledge_panel")
    check(
        "KP metadata has only curated keys (title, description, link)",
        set(kp.metadata.keys()) == {"title", "description", "link"},
        f"got keys: {set(kp.metadata.keys())}",
    )
    check(
        "KP metadata excludes imageUrl/attributes/descriptionSource",
        all(
            k not in kp.metadata
            for k in ("imageUrl", "attributes", "descriptionSource")
        ),
    )

    # AB: curated to title/snippet/link only.
    ab = next(r for r in results if r.content_type == "answer")
    check(
        "AB metadata has only curated keys (title, snippet, link)",
        set(ab.metadata.keys()) == {"title", "snippet", "link"},
        f"got keys: {set(ab.metadata.keys())}",
    )
    check(
        "AB metadata excludes date",
        "date" not in ab.metadata,
    )

    # Organic: curated to position + position_score.
    organic = next(r for r in results if r.content_type == "text")
    check(
        "organic metadata has position + position_score only",
        set(organic.metadata.keys()) == {"position", "position_score"},
        f"got keys: {set(organic.metadata.keys())}",
    )


def test_format_expansion_results():
    """format_expansion_results produces AI-Q-style structured markdown."""
    print("[format_expansion_results]")

    # Case 1: empty results list → single-line message.
    empty_out = format_expansion_results([], query="test query")
    check(
        "empty results produces 'No results found for query' message",
        "No results found for query: 'test query'" in empty_out,
        f"got {empty_out!r}",
    )

    # Case 2: basic result renders all fields.
    r_basic = ResearchResult(
        source="serper",
        url="https://example.com",
        title="Example",
        content="Some content.",
        content_type="text",
        score=0.85,
        citation="Example — https://example.com",
        metadata={"found_in_variants": 1},
    )
    basic_out = format_expansion_results([r_basic])
    check("basic result has 'Result 1' header", "--- Result 1 ---" in basic_out)
    check("basic result has Source line", "Source: serper" in basic_out)
    check("basic result has URL line", "URL: https://example.com" in basic_out)
    check("basic result has Title line", "Title: Example" in basic_out)
    check("basic result has Content Type line", "Content Type: text" in basic_out)
    check("basic result has Relevance Score", "Relevance Score: 0.85" in basic_out)
    check(
        "basic result has Citation line",
        "Citation: Example — https://example.com" in basic_out,
    )
    check(
        "basic result does NOT have ★ marker (found_in_variants=1)",
        "★" not in basic_out,
    )
    check(
        "basic result does NOT have variants footer (variants=None)",
        "query variants" not in basic_out,
    )

    # Case 3: corroborated result (found_in_variants >= 2) gets ★ marker.
    r_corrob = ResearchResult(
        source="serper",
        url="https://example.com",
        title="Example",
        content="Some content.",
        content_type="text",
        score=0.85,
        citation="Example — https://example.com",
        metadata={"found_in_variants": 3},
    )
    corrob_out = format_expansion_results([r_corrob], variants=["q1", "q2", "q3"])
    check(
        "★ marker appears when found_in_variants >= 2",
        "--- ★ Result 1 ---" in corrob_out,
    )
    check(
        "Corroboration line appears with variant count",
        "Corroboration: found by 3 query variants" in corrob_out,
    )
    check(
        "Variants footer appears when len(variants) > 1",
        'Variants: "q1" | "q2" | "q3"' in corrob_out,
    )
    check(
        "Footer includes corroborated count",
        "1 corroborated across variants" in corrob_out,
    )

    # Case 4: max_chars truncation.
    r_long = ResearchResult(
        source="exa",
        url="https://example.com",
        title="Long",
        content="A" * 5000,
        content_type="text",
        score=None,
        citation="Long",
    )
    trunc_out = format_expansion_results([r_long], max_chars=100)
    check(
        "max_chars truncates content and adds marker",
        "[...truncated" in trunc_out and "4,900 more chars]" in trunc_out,
    )
    check(
        "max_chars=0 disables truncation",
        "truncated" not in format_expansion_results([r_long], max_chars=0),
    )

    # Case 5: single variant (or variants=None) → no variants footer.
    single_variant_out = format_expansion_results([r_basic], variants=["only one"])
    check(
        "single-variant list produces no variants footer",
        "Variants:" not in single_variant_out,
    )


def test_normalize_url():
    """URL normalization strips tracking params, fragments, normalizes casing."""

    # highlight param stripped (the exact issue observed with zed.dev docs)
    check(
        "highlight param stripped",
        _canonical_url("https://zed.dev/docs/python?highlight=ruff")
        == "https://zed.dev/docs/python",
    )

    # Same page with different highlight values → same canonical URL
    check(
        "different highlight values dedup to same URL",
        _canonical_url("https://zed.dev/docs/python?highlight=pyright")
        == _canonical_url("https://zed.dev/docs/python?highlight=ruff"),
    )

    # UTM tracking params stripped
    check(
        "utm params stripped",
        _canonical_url("https://example.com/page?utm_source=twitter&utm_medium=social")
        == "https://example.com/page",
    )

    # Fragment stripped
    check(
        "fragment stripped",
        _canonical_url("https://example.com/page#section")
        == "https://example.com/page",
    )

    # Trailing slash normalized
    check(
        "trailing slash normalized",
        _canonical_url("https://example.com/page/")
        == _canonical_url("https://example.com/page"),
    )

    # Meaningful params preserved
    check(
        "meaningful params preserved",
        "version=3" in _canonical_url("https://example.com/docs?version=3"),
    )

    # Empty URL returns empty
    check("empty URL returns empty", _canonical_url("") == "")

    # _dedup_by_url_field removes same-page duplicates
    results = [
        {"url": "https://zed.dev/docs/python", "title": "A"},
        {"url": "https://zed.dev/docs/python?highlight=ruff", "title": "B"},
        {"url": "https://example.com/other", "title": "C"},
    ]
    deduped = _dedup_by_url_field(results, "url")
    check("dedup removes same-page duplicates", len(deduped) == 2)
    check("dedup keeps first occurrence", deduped[0]["title"] == "A")
    check("dedup keeps unique URL", deduped[1]["title"] == "C")


def test_literature_quality_filter():
    """Test literature quality criteria: IF > 6.0, 2021+ qualification, pre-2021 fallback, disqualifications."""
    print("[literature quality filter]")

    # 1. Title overlap calculation
    t1 = "Cardiorespiratory fitness, body mass index and mortality: a systematic review and meta-analysis"
    t2 = "Cardiorespiratory fitness, body mass index and mortality: a systematic review and meta-analysis"
    t3 = (
        "Cardiorespiratory Fitness, Body Mass Index, and Heart Failure Mortality in Men"
    )
    check("title_overlap exact match is 1.0", _title_overlap(t1, t2) == 1.0)
    check("title_overlap partial title is < 0.8", _title_overlap(t1, t3) < 0.8)

    # 2. Journal prefix matching
    check(
        "matches BJSM prefix",
        _journal_matches_prefix(
            "British journal of sports …", "British Journal of Sports Medicine"
        ),
    )
    check(
        "rejects BJSM with Circulation",
        not _journal_matches_prefix(
            "British journal of sports …", "Circulation: Heart Failure"
        ),
    )
    check(
        "matches leading ellipsis",
        _journal_matches_prefix(
            "… Urology and Nephrology", "International Urology and Nephrology"
        ),
    )
    check(
        "rejects JCSM with SMR",
        not _journal_matches_prefix(
            "Journal of clinical sleep …", "Sleep Medicine Reviews"
        ),
    )

    # 3. Direct lookup in curated dictionary
    bjsm_if, is_j, src = lookup_journal_impact_factor(
        "British Journal of Sports Medicine"
    )
    check("BJSM IF is 11.6", bjsm_if == 11.6 and is_j)

    lancet_if, is_j, src = lookup_journal_impact_factor("The Lancet")
    check("The Lancet IF is 98.4", lancet_if == 98.4 and is_j)

    jcsm_if, is_j, src = lookup_journal_impact_factor(
        "Journal of Clinical Sleep Medicine"
    )
    check("JCSM IF is 3.5 (disqualified tier)", jcsm_if == 3.5 and is_j)

    jcm_if, is_j, src = lookup_journal_impact_factor("Journal of Clinical Medicine")
    check("JCM IF is 3.0 (disqualified tier)", jcm_if == 3.0 and is_j)

    # 4. Preprint / Non-journal domain detection
    biorxiv_if, is_j, src = lookup_journal_impact_factor(
        "Random Bio", link="https://www.biorxiv.org/content/10.1101/123"
    )
    check("bioRxiv link flagged as non-journal", not is_j and biorxiv_if == 0.0)

    medrxiv_if, is_j, src = lookup_journal_impact_factor(
        "Random Med", link="https://www.medrxiv.org/content/10.1101/456"
    )
    check("medRxiv link flagged as non-journal", not is_j and medrxiv_if == 0.0)

    # 5. Low-impact publisher heuristic detection
    mdpi_if, is_j, src = lookup_journal_impact_factor(
        "Unknown MDPI Title", link="https://www.mdpi.com/1234-5678/1/2/3"
    )
    check("MDPI link flagged as IF <= 5.0", mdpi_if is not None and mdpi_if <= 5.0)

    # 6. Evaluation tiering: 2021+ qualified vs pre-2021 fallback vs disqualified
    p_qual = {
        "title": "Ketone esters",
        "publicationInfo": "M Evans - Sports medicine, 2022 - Springer",
        "year": "2022",
        "link": "https://link.springer.com/article/1",
    }
    ev_qual = _evaluate_paper(p_qual, min_if=6.0, min_year=2021)
    check(
        "2022 paper in Sports Medicine qualifies",
        ev_qual["quality_tier"] == "qualified",
    )

    p_fallback = {
        "title": "Nutritional ketosis",
        "publicationInfo": "PJ Cox - Cell metabolism, 2016 - cell.com",
        "year": "2016",
        "link": "https://www.cell.com/cell-metabolism/1",
    }
    ev_fb = _evaluate_paper(p_fallback, min_if=6.0, min_year=2021)
    check(
        "2016 paper in Cell Metabolism is fallback", ev_fb["quality_tier"] == "fallback"
    )

    p_disq_if = {
        "title": "Nutrients study",
        "publicationInfo": "Author - Nutrients, 2023 - mdpi.com",
        "year": "2023",
        "link": "https://www.mdpi.com/2072-6643/1",
    }
    ev_disq_if = _evaluate_paper(p_disq_if, min_if=6.0, min_year=2021)
    check(
        "2023 paper in Nutrients is disqualified by IF",
        ev_disq_if["quality_tier"] == "disqualified",
    )

    p_disq_preprint = {
        "title": "Preprint study",
        "publicationInfo": "Author, 2024",
        "year": "2024",
        "link": "https://www.biorxiv.org/content/10.1101/999",
    }
    ev_disq_pre = _evaluate_paper(p_disq_preprint, min_if=6.0, min_year=2021)
    check(
        "bioRxiv paper is disqualified as non-journal",
        ev_disq_pre["quality_tier"] == "disqualified",
    )

    # 7. Book chapter / ISBN link detection
    isbn_if, is_j, src = lookup_journal_impact_factor(
        "Creatine Chapter",
        link="https://link.springer.com/content/pdf/10.1007/978-1-4020-6486-9.pdf",
    )
    check("ISBN link flagged as book chapter", not is_j and isbn_if == 0.0)

    # 8. Standalone year parsing in _parse_pub_info
    j_standalone, y_standalone = _parse_pub_info("Author - 2023 - publisher")
    check(
        "standalone year parsed correctly", y_standalone == 2023 and j_standalone == ""
    )

    # 9. Suffix match on leading ellipsis in curated dictionary
    urol_if, is_j, src = lookup_journal_impact_factor("… Urology and Nephrology")
    check("leading ellipsis matches curated suffix", urol_if == 1.7 and is_j)


def main():
    print("=" * 60)
    print("Tier 2 offline smoke tests")
    print("=" * 60)
    test_expand_query()
    test_research_result_to_dict()
    test_normalize_serper()
    test_normalize_brave()
    test_merge_variant_results()
    test_normalize_serper_metadata()
    test_format_expansion_results()
    test_normalize_url()
    test_literature_quality_filter()
    print("=" * 60)
    if FAILURES:
        print(f"FAILED: {len(FAILURES)}")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("ALL PASSED")


if __name__ == "__main__":
    main()
