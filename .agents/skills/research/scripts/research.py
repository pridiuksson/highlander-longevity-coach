#!/usr/bin/env python3
"""research.py — Search the web via Exa, Serper, Brave, or GitHub.

Usage:
  research.py --answer "question"          # Exa /answer — synthesized answer + citations
  research.py --links "query" [-n 5]       # Exa /search auto — titles + snippets
  research.py --content "query" [-n 5]     # Exa /search + contents — full page text
  research.py --scholar "query" [-n 5]     # Serper /scholar — academic papers
  research.py --fresh "query" [-n 10]      # Brave /web/search freshness=pw — recent results
  research.py --serp "query" [-n 10]       # Serper /search — raw Google SERP
  research.py --repo "owner/repo"          # GitHub — known repo deep analysis
  research.py --repo "owner/repo,owner2/repo2"  # GitHub — multi-repo comparison
  research.py --repo "topic query" [--limit 5]  # Brave + gh (multi-query) — repo topic discovery (parallel)
  research.py --code "pattern" [--language python]  # GitHub code search across repos

Options:
  -n, --num      Number of results (default: 5 for answer/links/content/scholar, 10 otherwise)
  --domains      Comma-separated domains to include (Exa/Serper/Brave)
  --max-chars N  Max chars per result in --content/--repo mode (default: 3000, 0 = no truncation)
  --limit N      Max repos to analyze in --repo topic mode (default: 3, max: 10)
  --language LANG  Language filter for --code mode (e.g., python, rust, typescript)
  --raw          Output raw API JSON (unmodified vendor response)
  --expand       Rule-based query expansion is DEFAULT-ON for --serp, --scholar, --fresh. This flag is accepted for backward-compat but is now a no-op. Exa is semantic, gh code is literal — both excluded.
  --no-expand    Disable query expansion for keyword APIs. Expansion uses 3 credits per query (vs 1 baseline); disable to conserve Serper quota when credits are low.
  --expand-n N   Number of query variants (2-5, default 3). When n>=4, the last variant swaps ALL synonyms at once (max-distance).
  --min-if FLOAT Minimum journal impact factor for --scholar (default: 6.0).
  --min-year YYYY Minimum publication year for primary --scholar (default: 2021). Falls back to pre-YYYY if results < num.
  --all-years    Search all years without primary 2021+ restriction (still enforces --min-if).
  --no-filter    Bypass literature quality criteria filtering on --scholar (raw Google Scholar).
  --timeout SECS Request timeout in seconds (default: 30)

Exit codes: 0 success | 1 API error | 2 config error (missing key/tool)

Reads API keys from os.environ or .env file (walk-up search from script dir).
--repo and --code require gh CLI with auth (gh auth login).
"""

import base64
import concurrent.futures
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, NamedTuple, NoReturn


class _Args(NamedTuple):
    """Parsed CLI arguments.

    parse_args() constructs this by name, so adding a new flag requires
    editing this class — drift is caught at construction time.

    main() unpacks positionally for legacy compatibility with the original
    tuple return, but new code should prefer attribute access
    (args.mode, args.query, etc.).
    """

    mode: str | None = None
    query: str | None = None
    num: int | None = None
    domains: str | None = None
    raw: bool = False
    no_expand: bool = False
    expand_n: int = 3
    timeout: int = 30
    max_chars: int = 3000
    limit: int | None = None
    language: str | None = None
    min_if: float = 6.0
    min_year: int | None = 2021
    no_filter: bool = False


# ── Config ──────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent


def load_env():
    """Load env vars from os.environ (highest priority) then .env file (walk-up search + ~/.hermes/.env)."""
    env = dict(os.environ)  # exported env vars take precedence
    # Walk up from script dir to find .env, and include ~/.hermes/.env
    candidates = []
    d = Path(__file__).resolve().parent
    for _ in range(10):
        candidates.append(d / ".env")
        if d == d.parent:
            break
        d = d.parent
    candidates.append(Path.home() / ".hermes" / ".env")
    for env_file in candidates:
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() not in env:
                        env[k.strip()] = v.strip().strip('"').strip("'")
            if env.get("SERPER_API_KEY") and env.get("EXA_API_KEY"):
                break
    return env


ENV = load_env()

EXA_KEY = ENV.get("EXA_API_KEY", "")
SERPER_KEY = ENV.get("SERPER_API_KEY", "")
BRAVE_KEY = ENV.get("BRAVE_API_KEY", "") or ENV.get("BRAVE_SEARCH_API_KEY", "")


# ── HTTP helpers ────────────────────────────────────────────────


def api_request(url, headers=None, data=None, method="GET", timeout=30, retry=True):
    """Make HTTP request. One retry on 429/503 with 3s backoff."""
    if data is not None and isinstance(data, dict):
        data = json.dumps(data).encode()
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        if retry and e.code in (429, 503):
            time.sleep(3)
            return api_request(url, headers, data, method, timeout, retry=False)
        return e.code, body
    except Exception as e:
        return 0, str(e)


def die(msg, code=1) -> NoReturn:
    """Print error and exit. Never returns."""
    print(f"Error: {msg}", file=sys.stderr)
    raise SystemExit(code)


def parse_json_api(resp, api_name):
    """Parse JSON from API response. Dies with clean error on non-JSON (HTML captcha, WAF block)."""
    try:
        return json.loads(resp)
    except json.JSONDecodeError:
        die(
            f"{api_name} returned non-JSON response (possibly HTML/captcha): {resp[:200]}",
            1,
        )
    raise RuntimeError("unreachable")  # type checker hint


def parse_json_gh(resp, cmd_name):
    """Parse JSON from gh CLI output. Returns (data, None) or (None, error_string)."""
    try:
        return json.loads(resp), None
    except json.JSONDecodeError:
        return None, f"{cmd_name} returned non-JSON output: {resp[:200]}"
    raise RuntimeError("unreachable")  # type checker hint


# Query params that don't change the page content — used for URL dedup.
_TRACKING_PARAMS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "highlight",  # Zed docs, GitHub search highlighting
        "ref",
        "source",
        "mc_cid",
        "mc_eid",
        "_ga",
        "gclid",
        "fbclid",
        "msclkid",
    }
)


def _canonical_url(url: str) -> str:
    """Canonicalize a URL for dedup.

    Strips tracking/analytics params, fragment, normalizes trailing slash
    and scheme/host casing. Meaningful params (pagination, versions) are kept.
    """
    if not url:
        return url
    try:
        parsed = urllib.parse.urlparse(url)
        params = [
            (k, v)
            for k, v in urllib.parse.parse_qsl(parsed.query)
            if k.lower() not in _TRACKING_PARAMS
        ]
        params.sort()
        clean_query = urllib.parse.urlencode(params)
        path = parsed.path.rstrip("/") or "/"
        return urllib.parse.urlunparse(
            (parsed.scheme.lower(), parsed.netloc.lower(), path, "", clean_query, "")
        )
    except Exception:
        return url


def _dedup_by_url_field(results: list, url_field: str) -> list:
    """Remove results with duplicate normalized URLs, keeping first occurrence."""
    seen: set[str] = set()
    deduped: list = []
    for r in results:
        url = r.get(url_field, "") if isinstance(r, dict) else ""
        key = _canonical_url(url) if url else ""
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        deduped.append(r)
    return deduped


# ── gh CLI helpers ──────────────────────────────────────────────


def run_gh(args, timeout=30):
    """Run gh CLI command, return (stdout, stderr, returncode)."""
    try:
        result = subprocess.run(
            ["gh"] + args, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout, result.stderr, result.returncode
    except FileNotFoundError:
        die(
            "gh CLI not found. Install: https://cli.github.com\n"
            "Then run: gh auth login",
            2,
        )
    except subprocess.TimeoutExpired:
        die(f"gh command timed out after {timeout}s", 1)
    raise RuntimeError("unreachable")  # type checker hint


def check_gh_auth():
    """Verify gh CLI is authenticated. Dies with clear error if not."""
    _, stderr, rc = run_gh(["auth", "status"])
    if rc != 0:
        die(
            "gh CLI not authenticated. --repo and --code require auth (even for public repos).\n"
            "Run: gh auth login",
            2,
        )


_REPO_RE = re.compile(r"^[a-zA-Z0-9_.\-]+/[a-zA-Z0-9_.\-]+$")
_GITHUB_URL_RE = re.compile(r"https?://github\.com/([a-zA-Z0-9_.\-]+/[a-zA-Z0-9_.\-]+)")


def is_repo_pattern(query):
    """Check if query looks like owner/repo pattern(s)."""
    parts = [p.strip() for p in query.split(",")]
    return len(parts) > 0 and all(_REPO_RE.match(p) for p in parts)


def extract_repo_from_url(text):
    """Extract owner/repo from a GitHub URL, or return None."""
    match = _GITHUB_URL_RE.match(text.strip().rstrip("/"))
    return match.group(1) if match else None


# ── API calls ───────────────────────────────────────────────────


def exa_answer(query, _num=5, domains=None, timeout=30):
    """Exa /answer — synthesized answer with citations."""
    if not EXA_KEY:
        die("EXA_API_KEY not set in .env", 2)
    body = {"query": query, "text": True}
    if domains:
        body["includeDomains"] = [d.strip() for d in domains.split(",")]
    status, resp = api_request(
        "https://api.exa.ai/answer",
        headers={"x-api-key": EXA_KEY, "Content-Type": "application/json"},
        data=body,
        method="POST",
        timeout=timeout,
    )
    if status != 200:
        die(f"Exa /answer returned HTTP {status}: {resp[:200]}", 1)
    return parse_json_api(resp, "Exa /answer"), "answer"


def exa_search(query, num=5, with_content=False, domains=None, timeout=30):
    """Exa /search — neural search, optionally with full page content."""
    if not EXA_KEY:
        die("EXA_API_KEY not set in .env", 2)
    body = {"query": query, "numResults": num, "type": "auto"}
    if with_content:
        body["contents"] = {"text": True}
    if domains:
        body["includeDomains"] = [d.strip() for d in domains.split(",")]
    status, resp = api_request(
        "https://api.exa.ai/search",
        headers={"x-api-key": EXA_KEY, "Content-Type": "application/json"},
        data=body,
        method="POST",
        timeout=timeout,
    )
    if status != 200:
        die(f"Exa /search returned HTTP {status}: {resp[:200]}", 1)
    data = parse_json_api(resp, "Exa /search")
    data["results"] = _dedup_by_url_field(data.get("results", []), "url")
    return data, "content" if with_content else "links"


def serper_search(query, num=10, timeout=30):
    """Serper /search — Google SERP results."""
    if not SERPER_KEY:
        die("SERPER_API_KEY not set in .env", 2)
    status, resp = api_request(
        "https://google.serper.dev/search",
        headers={"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"},
        data={"q": query, "num": num},
        method="POST",
        timeout=timeout,
    )
    if status != 200:
        die(f"Serper /search returned HTTP {status}: {resp[:200]}", 1)
    data = parse_json_api(resp, "Serper /search")
    if isinstance(data.get("organic"), list):
        data["organic"] = _dedup_by_url_field(data["organic"], "link")
    return data, "serp"


# ── Journal Impact Factor & Quality Filtering ───────────────────

JOURNAL_IMPACT_FACTORS: dict[str, float] = {
    # Multidisciplinary & General Sciences (>6.0)
    "nature": 50.5,
    "nature medicine": 58.7,
    "nature biotechnology": 33.1,
    "nature genetics": 31.7,
    "nature communications": 14.7,
    "nat commun": 14.7,
    "nature immunology": 27.7,
    "nature neuroscience": 21.2,
    "nature metabolism": 18.9,
    "nature aging": 16.6,
    "science": 44.7,
    "science translational medicine": 15.8,
    "science immunology": 17.6,
    "science advances": 11.7,
    "sci adv": 11.7,
    "cell": 45.5,
    "cell metabolism": 29.0,
    "cancer cell": 48.8,
    "immunity": 25.5,
    "cell stem cell": 19.8,
    "molecular cell": 14.5,
    "cell reports": 7.5,
    "cell rep": 7.5,
    "cell reports medicine": 11.7,
    "cell rep med": 11.7,
    "cell death & differentiation": 13.7,
    "proceedings of the national academy of sciences": 9.4,
    "proceedings of the national academy of sciences of the united states of america": 9.4,
    "pnas": 9.4,
    "proc natl acad sci u s a": 9.4,
    "embo journal": 9.4,
    "embo molecular medicine": 11.1,
    "plos biology": 7.8,
    "plos medicine": 11.0,
    # General Medicine (>6.0)
    "the lancet": 98.4,
    "lancet": 98.4,
    "lancet oncology": 41.6,
    "lancet neurology": 46.5,
    "lancet respiratory medicine": 38.7,
    "lancet diabetes & endocrinology": 44.0,
    "lancet infectious diseases": 36.4,
    "lancet healthy longevity": 13.0,
    "lancet digital health": 23.8,
    "npj digital medicine": 15.2,
    "lancet global health": 20.0,
    "lancet psychiatry": 30.8,
    "the lancet global health": 20.0,
    "the lancet digital health": 23.8,
    "the lancet regional health - europe": 13.6,
    "lancet regional health europe": 13.6,
    "lancet reg health eur": 13.6,
    "eclinicalmedicine": 9.6,
    "new england journal of medicine": 96.2,
    "nejm": 96.2,
    "the new england journal of medicine": 96.2,
    "n engl j med": 96.2,
    "jama": 63.1,
    "jama internal medicine": 22.5,
    "jama oncology": 22.5,
    "jama cardiology": 14.8,
    "jama neurology": 20.4,
    "jama pediatrics": 13.9,
    "jama psychiatry": 22.5,
    "jama network open": 10.5,
    "jama netw open": 10.5,
    "medicinal research reviews": 12.9,
    "med res rev": 12.9,
    "bmj": 93.6,
    "the bmj": 93.6,
    "british medical journal": 93.6,
    "gut": 23.0,
    "thorax": 10.0,
    "annals of the rheumatic diseases": 20.3,
    "bmj global health": 7.1,
    "annals of internal medicine": 19.6,
    "bmc medicine": 9.3,
    "journal of internal medicine": 9.0,
    "cochrane database of systematic reviews": 8.4,
    "cochrane database syst rev": 8.4,
    # Cardiology & Vascular (>6.0)
    "circulation": 35.5,
    "circulation research": 16.5,
    "circ res": 16.5,
    "circulation: heart failure": 7.8,
    "circulation: cardiovascular quality and outcomes": 6.9,
    "circulation: arrhythmia and electrophysiology": 6.5,
    "european heart journal": 37.6,
    "eur heart j": 37.6,
    "cardiovascular research": 10.2,
    "journal of the american college of cardiology": 24.0,
    "j am coll cardiol": 24.0,
    "jacc": 24.0,
    "jacc: cardiovascular imaging": 14.0,
    "jacc: heart failure": 13.0,
    "jacc: cardiooncology": 8.4,
    "jacc: basic to translational science": 8.4,
    "arteriosclerosis, thrombosis, and vascular biology": 7.4,
    "atvb": 7.4,
    "hypertension": 6.9,
    "stroke": 7.8,
    # Nephrology (>6.0)
    "kidney international": 14.8,
    "kidney int": 14.8,
    "journal of the american society of nephrology": 10.3,
    "jasn": 10.3,
    "clinical journal of the american society of nephrology": 8.5,
    "cjasn": 8.5,
    "american journal of kidney diseases": 9.4,
    "ajkd": 9.4,
    "nephrology dialysis transplantation": 6.1,
    "nephrol dial transplant": 6.1,
    "ndt": 6.1,
    # Sports Medicine, Exercise Physiology & Physical Medicine (>6.0)
    "british journal of sports medicine": 11.6,
    "br j sports med": 11.6,
    "bjsm": 11.6,
    "sports medicine": 11.1,
    "sports med": 11.1,
    "american journal of sports medicine": 6.2,
    "am j sports med": 6.2,
    "ajsm": 6.2,
    "journal of sport and health science": 9.7,
    "j sport health sci": 9.7,
    "journal of cachexia, sarcopenia and muscle": 8.9,
    # Nutrition, Metabolism & Endocrinology (>6.0)
    "american journal of clinical nutrition": 6.5,
    "am j clin nutr": 6.5,
    "ajcn": 6.5,
    "the american journal of clinical nutrition": 6.5,
    "clinical nutrition": 6.3,
    "clin nutr": 6.3,
    "nutrition reviews": 7.5,
    "nutr rev": 7.5,
    "critical reviews in food science and nutrition": 10.2,
    "crit rev food sci nutr": 10.2,
    "advances in nutrition": 9.3,
    "adv nutr": 9.3,
    "international journal of behavioral nutrition and physical activity": 6.7,
    "ijbnpa": 6.7,
    "annual review of nutrition": 11.8,
    "annual review of medicine": 15.1,
    "annual review of physiology": 15.7,
    "annual review of biochemistry": 20.5,
    "diabetes care": 14.8,
    "diabetologia": 8.2,
    "diabetes": 7.7,
    "metabolism": 10.8,
    "metabolism: clinical and experimental": 10.8,
    "metabolism - clinical and experimental": 10.8,
    "endocrine reviews": 22.0,
    "trends in endocrinology and metabolism": 11.4,
    "trends in molecular medicine": 12.9,
    "trends in pharmacological sciences": 13.8,
    "pharmacological reviews": 19.3,
    "gastroenterology": 25.7,
    "hepatology": 12.9,
    "journal of hepatology": 26.8,
    "blood": 21.0,
    "aging cell": 8.0,
    "geroscience": 6.3,
    "sleep medicine reviews": 11.5,
    "journal of pineal research": 8.3,
    "redox biology": 10.7,
    "free radical biology and medicine": 7.1,
    "autophagy": 14.6,
    "theranostics": 12.4,
    "antioxidants & redox signaling": 6.6,
    "journal of travel medicine": 25.7,
    "biochimica et biophysica acta - molecular basis of disease": 6.2,
    "bba - molecular basis of disease": 6.2,
    # Explicitly Disqualified / Known Lower Impact Journals (IF <= 6.0)
    "journal of clinical sleep medicine": 3.5,
    "jcsm": 3.5,
    "sleep medicine": 3.8,
    "sleep med": 3.8,
    "journal of sleep research": 3.4,
    "j sleep res": 3.4,
    "international urology and nephrology": 1.7,
    "int urol nephrol": 1.7,
    "kidney international reports": 4.1,
    "kidney int rep": 4.1,
    "journal of the american heart association": 5.0,
    "j am heart assoc": 5.0,
    "jaha": 5.0,
    "journal of clinical medicine": 3.0,
    "j clin med": 3.0,
    "nutritional neuroscience": 4.0,
    "nutr neurosci": 4.0,
    "applied physiology, nutrition, and metabolism": 2.4,
    "apnm": 2.4,
    "european journal of sport science": 2.4,
    "ejss": 2.4,
    "journal of science and medicine in sport": 3.4,
    "jsams": 3.4,
    "current opinion in clinical nutrition and metabolic care": 3.0,
    "curr opin clin nutr metab care": 3.0,
    "current opinion in lipidology": 3.8,
    "curr opin lipidol": 3.8,
    "current opinion in nephrology and hypertension": 2.2,
    "american journal of physiology - renal physiology": 2.7,
    "am j physiol renal physiol": 2.7,
    "american journal of physiology - endocrinology and metabolism": 4.2,
    "am j physiol endocrinol metab": 4.2,
    "american journal of physiology - heart and circulatory physiology": 4.1,
    "am j physiol heart circ physiol": 4.1,
    "journal of education, health and sport": 0.3,
    "adolescents": 1.0,
    "nutrients": 4.8,
    "plos one": 2.9,
    "sleep": 5.6,
    "sleep and breathing": 2.1,
    "sleep breath": 2.1,
    "chronobiology international": 2.5,
    "chronobiol int": 2.5,
    "frontiers in human neuroscience": 2.9,
    "front hum neurosci": 2.9,
    "frontiers in physiology": 4.0,
    "frontiers in nutrition": 4.0,
    "frontiers in endocrinology": 3.9,
    "frontiers in medicine": 3.1,
    "frontiers in aging neuroscience": 4.1,
    "frontiers in immunology": 5.7,
    "med j armed forces india": 1.1,
    "medical journal armed forces india": 1.1,
    "journal of biological rhythms": 2.9,
    "j biol rhythms": 2.9,
    "clocks & sleep": 2.1,
    "journal of nutrition": 4.2,
    "j nutr": 4.2,
    "the journal of nutrition": 4.2,
    "journal of the american college of nutrition": 3.4,
    "j am coll nutr": 3.4,
    "journal of strength and conditioning research": 3.2,
    "j strength cond res": 3.2,
    "journal of the international society of sports nutrition": 4.9,
    "j int soc sports nutr": 4.9,
    "jissn": 4.9,
    "international journal of sports physiology and performance": 3.5,
    "int j sports physiol perform": 3.5,
    "ijspp": 3.5,
    "medicine and science in sports and exercise": 4.1,
    "med sci sports exerc": 4.1,
    "medicine & science in sports & exercise": 4.1,
    "journal of applied physiology": 3.3,
    "j appl physiol": 3.3,
    "aviation, space, and environmental medicine": 1.0,
    "aviat space environ med": 1.0,
    "aerospace medicine and human performance": 0.9,
    "exercise and sport sciences reviews": 6.4,
    "exerc sport sci rev": 6.4,
    "journal of physiology": 5.5,
    "j physiol": 5.5,
    "the journal of physiology": 5.5,
    "european journal of applied physiology": 3.0,
    "eur j appl physiol": 3.0,
    "bmc nephrology": 2.2,
    "bmc nephrol": 2.2,
    "bmc public health": 3.5,
    "bmc sports science, medicine and rehabilitation": 2.1,
    "scientific reports": 3.8,
    "diagnostics": 3.0,
    "biomolecules": 4.8,
    "sensors": 3.4,
    "international journal of molecular sciences": 4.9,
    "ijms": 4.9,
    "molecules": 4.2,
    "heliyon": 3.4,
    "peerj": 2.7,
    "f1000research": 2.0,
    "cureus": 1.2,
    "current sports medicine reports": 1.7,
    "amino acids": 3.0,
    "regulatory toxicology and pharmacology": 3.2,
    "annals of pharmacotherapy": 2.5,
    "clinical kidney journal": 3.9,
    "journal of renal nutrition": 2.2,
    "food science & nutrition": 3.5,
    "european journal of clinical nutrition": 3.6,
    "sports medicine - open": 4.0,
    "sports med open": 4.0,
    "translational psychiatry": 5.8,
    "journal of herbal pharmacotherapy": 0.5,
}

NON_JOURNAL_PATTERNS = [
    "arxiv",
    "biorxiv",
    "medrxiv",
    "ssrn",
    "research square",
    "statpearls",
    "book",
    "thesis",
    "patent",
    "intechopen",
    "springerlink",
    "wiley online library",
    "elsevier",
    "sciencedirect",
    "taylor & francis",
    "mdpi.com",
    "oup.com",
]

_JOURNAL_CACHE: dict[str, tuple[float | None, bool, str]] = {}


def _parse_pub_info(info: str, fallback_year: Any = None) -> tuple[str, int | None]:
    """Extract clean journal name and publication year from publicationInfo."""
    parts = [p.strip() for p in (info or "").split(" - ")]
    journal = ""
    year: int | None = None
    if len(parts) >= 3:
        mid = " - ".join(parts[1:-1]).strip()
    elif len(parts) == 2:
        if re.search(r"[,\s]+(19\d\d|20\d\d)$", parts[0]) and not re.search(
            r"[,\s]+(19\d\d|20\d\d)$", parts[1]
        ):
            mid = parts[0].strip()
        else:
            mid = parts[1].strip()
    else:
        mid = parts[0].strip() if parts else ""

    if mid.isdigit() and len(mid) == 4:
        year = int(mid)
    else:
        m = re.search(r"^(.*?)(?:[,\s]+(19\d\d|20\d\d))?$", mid)
        if m:
            candidate_j = m.group(1).strip()
            candidate_y = m.group(2)
            if not candidate_y and re.match(r"^(19\d\d|20\d\d)$", candidate_j):
                year = int(candidate_j)
                journal = ""
            else:
                journal = candidate_j
                if candidate_y:
                    try:
                        year = int(candidate_y)
                    except Exception:
                        pass
    if year is None and fallback_year is not None:
        try:
            year = int(str(fallback_year).strip())
        except Exception:
            pass
    return journal, year


def _title_overlap(t1: str, t2: str) -> float:
    """Calculate token overlap ratio between two paper titles."""
    w1 = set(
        w for w in re.sub(r"[^a-z0-9]", " ", (t1 or "").lower()).split() if len(w) > 2
    )
    w2 = set(
        w for w in re.sub(r"[^a-z0-9]", " ", (t2 or "").lower()).split() if len(w) > 2
    )
    if not w1 or not w2:
        return 0.0
    return len(w1 & w2) / len(w1)


def _journal_matches_prefix(j_prefix: str, resolved_j: str) -> bool:
    """Verify resolved journal name is compatible with truncated Google Scholar journal prefix."""
    if not j_prefix or not resolved_j:
        return True
    p = re.sub(r"^the\s+", "", re.sub(r"[\.…\s]+$", "", j_prefix.lower().strip()))
    p = re.sub(r"^[\.…\s]+", "", p).strip()
    rj = re.sub(r"^the\s+", "", re.sub(r"[\.…\s]+$", "", resolved_j.lower().strip()))
    if not p:
        return True
    if j_prefix.strip().startswith("…") or j_prefix.strip().startswith("..."):
        return rj.endswith(p) or p in rj
    return rj.startswith(p) or p in rj


def _resolve_title_to_journal(
    title: str, j_raw: str | None = None
) -> tuple[str | None, bool | None]:
    """Disambiguate truncated journal names using Crossref works API (with OpenAlex fallback).

    Returns: (resolved_container_title, is_peer_reviewed_journal)
    """
    clean_title = re.sub(r"[\.…\s]+$", "", (title or "").strip())
    clean_title = re.sub(r"^[\.…\s]+", "", clean_title).strip()
    clean_title = " ".join(clean_title.split()[:25])
    if not clean_title:
        return None, None

    headers = {"User-Agent": "devops-agent/1.0 (mailto:agent@local)"}
    # 1. Primary: Crossref works API (query.title) with polite pool
    try:
        c_url = f"https://api.crossref.org/works?rows=5&query.title={urllib.parse.quote(clean_title)}"
        c_req = urllib.request.Request(c_url, headers=headers)
        with urllib.request.urlopen(c_req, timeout=4) as resp:
            c_data = json.loads(resp.read().decode())
            items = c_data.get("message", {}).get("items", [])
            best_cand = None
            best_overlap = 0.0
            for it in items:
                cand_type = it.get("type", "")
                c_titles = it.get("title", [])
                cand_title = c_titles[0] if c_titles else ""
                containers = it.get("container-title", [])
                container = containers[0] if containers else ""
                overlap = _title_overlap(clean_title, cand_title)
                matches_pfx = _journal_matches_prefix(j_raw or "", container)
                if matches_pfx and overlap >= 0.55:
                    if overlap > best_overlap:
                        best_overlap = overlap
                        is_j = cand_type == "journal-article"
                        best_cand = (container, is_j)
            if best_cand:
                return best_cand
    except Exception:
        pass

    # 2. Secondary Crossref: query.bibliographic
    try:
        c_url2 = f"https://api.crossref.org/works?rows=5&query.bibliographic={urllib.parse.quote(clean_title)}"
        c_req2 = urllib.request.Request(c_url2, headers=headers)
        with urllib.request.urlopen(c_req2, timeout=4) as resp:
            c_data2 = json.loads(resp.read().decode())
            items2 = c_data2.get("message", {}).get("items", [])
            best_cand = None
            best_overlap = 0.0
            for it in items2:
                cand_type = it.get("type", "")
                c_titles = it.get("title", [])
                cand_title = c_titles[0] if c_titles else ""
                containers = it.get("container-title", [])
                container = containers[0] if containers else ""
                overlap = _title_overlap(clean_title, cand_title)
                matches_pfx = _journal_matches_prefix(j_raw or "", container)
                if matches_pfx and overlap >= 0.55:
                    if overlap > best_overlap:
                        best_overlap = overlap
                        is_j = cand_type == "journal-article"
                        best_cand = (container, is_j)
            if best_cand:
                return best_cand
    except Exception:
        pass

    # 3. Fallback: OpenAlex works API
    try:
        oa_url = (
            f"https://api.openalex.org/works?search={urllib.parse.quote(clean_title)}"
        )
        oa_req = urllib.request.Request(oa_url, headers=headers)
        with urllib.request.urlopen(oa_req, timeout=3) as resp:
            oa_data = json.loads(resp.read().decode())
            for w in oa_data.get("results", [])[:3]:
                cand_title = w.get("title", "")
                source = (w.get("primary_location") or {}).get("source") or {}
                container = source.get("display_name", "")
                is_j = source.get("type") == "journal"
                overlap = _title_overlap(clean_title, cand_title)
                matches_pfx = _journal_matches_prefix(j_raw or "", container)
                if matches_pfx and overlap >= 0.55 and container:
                    return container, is_j
    except Exception:
        pass

    return None, None


def lookup_journal_impact_factor(
    journal_name: str, title: str | None = None, link: str | None = None
) -> tuple[float | None, bool, str]:
    """Look up journal impact factor and verify peer-reviewed journal status.

    Returns: (impact_factor, is_peer_reviewed_journal, source_label)
    """
    if link:
        lower_link = link.lower()
        for p_dom in [
            "arxiv.org",
            "biorxiv.org",
            "medrxiv.org",
            "ssrn.com",
            "researchgate.net",
            "researchsquare.com",
            "statpearls",
            "ncbi.nlm.nih.gov/books",
        ]:
            if p_dom in lower_link:
                return 0.0, False, f"preprint / non-journal ({p_dom})"
        if any(
            k in lower_link
            for k in ["/chapter/", "/book/", "978-", "979-", "/monograph/"]
        ):
            return 0.0, False, "book / book chapter"

    if not journal_name and not title:
        return None, False, "unknown"

    j_raw = (journal_name or "").strip()
    j_clean = re.sub(r"[\.…\s]+$", "", j_raw.lower().strip())
    j_clean = re.sub(r"^[\.…\s]+", "", j_clean).strip()
    j_norm = re.sub(r"^the\s+", "", j_clean).strip()

    for pat in NON_JOURNAL_PATTERNS:
        if pat in j_clean:
            return 0.0, False, "non-journal"

    # Exact match in curated dictionary
    if j_clean in JOURNAL_IMPACT_FACTORS:
        return JOURNAL_IMPACT_FACTORS[j_clean], True, "JCR curated"
    if j_norm in JOURNAL_IMPACT_FACTORS:
        return JOURNAL_IMPACT_FACTORS[j_norm], True, "JCR curated"

    # Handle truncated journal names (e.g., 'Journal of the …', 'British journal of sports …', '… Urology and Nephrology')
    resolved_journal = None
    resolved_is_j = None
    if ("…" in j_raw or "..." in j_raw or len(j_clean) <= 6) and title:
        resolved_journal, resolved_is_j = _resolve_title_to_journal(title, j_raw)
        if resolved_is_j is False:
            return 0.0, False, f"non-journal ({resolved_journal or 'book/proceedings'})"
        if resolved_journal:
            rj_clean = re.sub(r"[\.…\s]+$", "", resolved_journal.lower().strip())
            rj_clean = re.sub(r"^[\.…\s]+", "", rj_clean).strip()
            rj_norm = re.sub(r"^the\s+", "", rj_clean).strip()
            if rj_clean in JOURNAL_IMPACT_FACTORS:
                return (
                    JOURNAL_IMPACT_FACTORS[rj_clean],
                    True,
                    f"JCR curated ({resolved_journal})",
                )
            if rj_norm in JOURNAL_IMPACT_FACTORS:
                return (
                    JOURNAL_IMPACT_FACTORS[rj_norm],
                    True,
                    f"JCR curated ({resolved_journal})",
                )
            j_clean = rj_clean
            j_norm = rj_norm

    # Unique prefix/suffix match in curated dictionary if unresolved and prefix is substantive
    if ("…" in j_raw or "..." in j_raw) and len(j_norm) >= 10:
        is_leading = j_raw.strip().startswith(("…", "..."))
        matches = [
            (k, v)
            for k, v in JOURNAL_IMPACT_FACTORS.items()
            if (
                k.endswith(j_norm)
                if is_leading
                else (k.startswith(j_norm) or j_norm.startswith(k))
            )
        ]
        if matches:
            unique_ifs = set(v for _, v in matches)
            if len(unique_ifs) == 1:
                matched_k, matched_if = matches[0]
                return matched_if, True, f"JCR curated prefix ({matched_k})"

    # Check known low-impact publisher signatures
    if link:
        lower_link = link.lower()
        if "mdpi.com" in lower_link:
            return 3.0, True, "MDPI (IF <= 5.0)"
        if "cureus.com" in lower_link:
            return 1.2, True, "Cureus (IF 1.2)"
        if "frontiersin.org" in lower_link:
            return 4.2, True, "Frontiers (IF <= 5.7)"

    if j_clean in _JOURNAL_CACHE:
        return _JOURNAL_CACHE[j_clean]

    lookup_name = resolved_journal or j_raw
    if (
        lookup_name
        and len(lookup_name) > 3
        and not ("…" in lookup_name or "..." in lookup_name)
    ):
        try:
            url = f"https://api.openalex.org/sources?search={urllib.parse.quote(lookup_name)}"
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "devops-agent/1.0 (mailto:agent@local)"
                },
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
                if data.get("results"):
                    top = data["results"][0]
                    is_j = top.get("type") == "journal"
                    cited = top.get("summary_stats", {}).get("2yr_mean_citedness")
                    if cited is not None:
                        res = (
                            float(cited),
                            is_j,
                            f"OpenAlex ({top.get('display_name')})",
                        )
                        _JOURNAL_CACHE[j_clean] = res
                        return res
        except Exception:
            pass

    _JOURNAL_CACHE[j_clean] = (None, True, "unknown")
    return None, True, "unknown"


def _evaluate_paper(r: dict, min_if: float = 6.0, min_year: int | None = 2021) -> dict:
    """Evaluate paper candidate against quality criteria and attach metrics."""
    j_name, year = _parse_pub_info(r.get("publicationInfo", ""), r.get("year"))
    if_val, is_j, src = lookup_journal_impact_factor(
        j_name, r.get("title"), r.get("link")
    )
    r["journal"] = j_name
    r["impact_factor"] = if_val
    r["if_source"] = src
    r["parsed_year"] = year
    r["is_journal"] = is_j

    if not is_j:
        r["quality_status"] = "DISQUALIFIED: Non-journal / Preprint / Book"
        r["quality_tier"] = "disqualified"
    elif if_val is not None and if_val <= min_if:
        r["quality_status"] = f"DISQUALIFIED: IF {if_val:.1f} <= {min_if}"
        r["quality_tier"] = "disqualified"
    elif if_val is not None and if_val > min_if:
        if min_year is not None and year is not None and year >= min_year:
            r["quality_status"] = f"QUALIFIED: {min_year}+, IF {if_val:.1f} > {min_if}"
            r["quality_tier"] = "qualified"
        elif min_year is not None and (year is None or year < min_year):
            y_str = str(year) if year else f"pre-{min_year}"
            r["quality_status"] = (
                f"FALLBACK: Pre-{min_year} ({y_str}), IF {if_val:.1f} > {min_if}"
            )
            r["quality_tier"] = "fallback"
        else:
            r["quality_status"] = f"QUALIFIED: IF {if_val:.1f} > {min_if}"
            r["quality_tier"] = "qualified"
    else:
        r["quality_status"] = "UNVERIFIED: Journal IF unknown (cannot confirm IF > 6.0)"
        r["quality_tier"] = "unknown"

    return r


def serper_scholar(
    query,
    num: int = 5,
    timeout: int = 30,
    min_if: float = 6.0,
    min_year: int | None = 2021,
    no_filter: bool = False,
):
    """Serper /scholar — Google Scholar results filtered by literature quality criteria.

    Criteria:
      - Primary: 2021 onwards AND peer-reviewed scientific journal AND IF > 6.0
      - Fallback: Pre-2021 AND peer-reviewed scientific journal AND IF > 6.0
      - Disqualified: IF <= 6.0, preprints, books, non-peer-reviewed sources
    """
    if not SERPER_KEY:
        die("SERPER_API_KEY not set in .env", 2)

    if no_filter:
        status, resp = api_request(
            "https://google.serper.dev/scholar",
            headers={"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"},
            data={"q": query, "num": num},
            method="POST",
            timeout=timeout,
        )
        if status != 200:
            die(f"Serper /scholar returned HTTP {status}: {resp[:200]}", 1)
        data = parse_json_api(resp, "Serper /scholar")
        if isinstance(data.get("organic"), list):
            data["organic"] = _dedup_by_url_field(data["organic"], "link")
        return data, "scholar"

    # Primary search: target min_year onwards (default 2021+)
    payload: dict[str, Any] = {"q": query}
    if min_year is not None:
        payload["as_ylo"] = min_year

    status, resp = api_request(
        "https://google.serper.dev/scholar",
        headers={"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"},
        data=payload,
        method="POST",
        timeout=timeout,
    )
    if status != 200:
        die(f"Serper /scholar returned HTTP {status}: {resp[:200]}", 1)
    data = parse_json_api(resp, "Serper /scholar")
    raw_organic = (
        data.get("organic", []) if isinstance(data.get("organic"), list) else []
    )
    raw_organic = _dedup_by_url_field(raw_organic, "link")

    qualified = []
    disqualified = []
    unknown = []

    def _process_candidates(organic_items):
        for r in organic_items:
            evaluated = _evaluate_paper(r, min_if=min_if, min_year=min_year)
            tier = evaluated.get("quality_tier")
            if tier == "qualified":
                qualified.append(evaluated)
            elif tier == "fallback":
                fallback_list.append(evaluated)
            elif tier == "disqualified":
                disqualified.append(evaluated)
            else:
                unknown.append(evaluated)

    # Process page 1
    _process_candidates(raw_organic)

    # If primary search has fewer qualified results than requested, query page 2
    if len(qualified) < num:
        p2_payload = dict(payload)
        p2_payload["page"] = 2
        p2_status, p2_resp = api_request(
            "https://google.serper.dev/scholar",
            headers={"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"},
            data=p2_payload,
            method="POST",
            timeout=timeout,
        )
        if p2_status == 200:
            p2_data = parse_json_api(p2_resp, "Serper /scholar p2")
            p2_raw = (
                p2_data.get("organic", [])
                if isinstance(p2_data.get("organic"), list)
                else []
            )
            p2_raw = _dedup_by_url_field(p2_raw, "link")
            seen_links = set(r.get("link") for r in raw_organic)
            p2_new = [r for r in p2_raw if r.get("link") not in seen_links]
            _process_candidates(p2_new)
            raw_organic.extend(p2_new)

    fallback_list = []
    fallback_screened_count = 0
    # If primary search has fewer than requested results, execute fallback search (< min_year)
    if len(qualified) < num and min_year is not None:
        fb_payload: dict[str, Any] = {
            "q": query,
            "as_yhi": min_year - 1,
        }
        fb_status, fb_resp = api_request(
            "https://google.serper.dev/scholar",
            headers={"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"},
            data=fb_payload,
            method="POST",
            timeout=timeout,
        )
        if fb_status == 200:
            fb_data = parse_json_api(fb_resp, "Serper /scholar fallback")
            raw_fb = (
                fb_data.get("organic", [])
                if isinstance(fb_data.get("organic"), list)
                else []
            )
            raw_fb = _dedup_by_url_field(raw_fb, "link")
            fallback_screened_count += len(raw_fb)
            for r in raw_fb:
                evaluated = _evaluate_paper(r, min_if=min_if, min_year=min_year)
                if evaluated.get("quality_tier") == "fallback":
                    fallback_list.append(evaluated)
                elif evaluated.get("quality_tier") == "disqualified":
                    disqualified.append(evaluated)
                else:
                    unknown.append(evaluated)

            # If still below target, try page 2 of fallback
            if len(qualified) + len(fallback_list) < num:
                fb_p2_payload = dict(fb_payload)
                fb_p2_payload["page"] = 2
                fb2_status, fb2_resp = api_request(
                    "https://google.serper.dev/scholar",
                    headers={
                        "X-API-KEY": SERPER_KEY,
                        "Content-Type": "application/json",
                    },
                    data=fb_p2_payload,
                    method="POST",
                    timeout=timeout,
                )
                if fb2_status == 200:
                    fb2_data = parse_json_api(fb2_resp, "Serper /scholar fallback p2")
                    raw_fb2 = (
                        fb2_data.get("organic", [])
                        if isinstance(fb2_data.get("organic"), list)
                        else []
                    )
                    raw_fb2 = _dedup_by_url_field(raw_fb2, "link")
                    fb_seen = set(r.get("link") for r in raw_fb)
                    raw_fb2_new = [r for r in raw_fb2 if r.get("link") not in fb_seen]
                    fallback_screened_count += len(raw_fb2_new)
                    for r in raw_fb2_new:
                        evaluated = _evaluate_paper(r, min_if=min_if, min_year=min_year)
                        if evaluated.get("quality_tier") == "fallback":
                            fallback_list.append(evaluated)
                        elif evaluated.get("quality_tier") == "disqualified":
                            disqualified.append(evaluated)
                        else:
                            unknown.append(evaluated)

    final_results = list(qualified)
    if len(final_results) < num:
        needed = num - len(final_results)
        final_results.extend(fallback_list[:needed])

    data["organic"] = final_results
    data["quality_summary"] = {
        "screened": len(raw_organic) + fallback_screened_count,
        "qualified": len(qualified),
        "fallback": len(fallback_list),
        "disqualified": len(disqualified),
        "min_if": min_if,
        "min_year": min_year,
    }
    return data, "scholar"


def brave_fresh(query, num=10, domains=None, timeout=30):
    """Brave /web/search with freshness=pw — past week results."""
    if not BRAVE_KEY:
        die("BRAVE_API_KEY not set in .env", 2)
    params = {"q": query, "count": num, "freshness": "pw"}
    if domains:
        site_filter = " OR ".join(f"site:{d.strip()}" for d in domains.split(","))
        params["q"] = f"({site_filter}) {query}"
    url = f"https://api.search.brave.com/res/v1/web/search?{urllib.parse.urlencode(params)}"
    status, resp = api_request(
        url,
        headers={"X-Subscription-Token": BRAVE_KEY, "Accept": "application/json"},
        timeout=timeout,
    )
    if status != 200:
        die(f"Brave /web/search returned HTTP {status}: {resp[:200]}", 1)
    data = parse_json_api(resp, "Brave /web/search")
    web = data.get("web", {})
    if isinstance(web, dict) and isinstance(web.get("results"), list):
        web["results"] = _dedup_by_url_field(web["results"], "url")
    return data, "fresh"


def brave_search(query, num=20, timeout=30):
    """Brave /web/search — general search for repo discovery. Non-fatal on failure."""
    if not BRAVE_KEY:
        print(
            "Warning: BRAVE_API_KEY not set, skipping Brave discovery source",
            file=sys.stderr,
        )
        return None
    params = {"q": query, "count": num}
    url = f"https://api.search.brave.com/res/v1/web/search?{urllib.parse.urlencode(params)}"
    status, resp = api_request(
        url,
        headers={"X-Subscription-Token": BRAVE_KEY, "Accept": "application/json"},
        timeout=timeout,
    )
    if status != 200:
        print(
            f"Warning: Brave search returned HTTP {status}, skipping Brave source",
            file=sys.stderr,
        )
        return None
    try:
        return json.loads(resp)
    except json.JSONDecodeError:
        print(
            "Warning: Brave search returned non-JSON response, skipping Brave source",
            file=sys.stderr,
        )
        return None


# ── GitHub repo analysis ────────────────────────────────────────

_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "for",
        "in",
        "on",
        "at",
        "to",
        "of",
        "with",
        "and",
        "or",
        "is",
        "are",
        "was",
        "were",
        "that",
        "this",
        "it",
        "from",
        "by",
        "as",
        "be",
        "been",
        "has",
        "have",
        "had",
        "do",
        "does",
        "did",
        "i",
        "you",
        "we",
        "they",
        "my",
        "your",
        "our",
        "their",
        "best",
        "top",
        "most",
        "find",
        "me",
        "show",
        "get",
        "what",
        "which",
        "how",
        "can",
        "some",
        "any",
        "all",
        "about",
        "open",
        "source",
        "like",
        "just",
    }
)


def refine_query(query):
    """Extract keyword-style query from natural language for gh search."""
    words = re.findall(r"[a-zA-Z0-9+#.-]+", query.lower())
    keywords = [w for w in words if w not in _STOP_WORDS and len(w) > 1]
    return " ".join(keywords[:6])


def extract_github_repos(brave_data):
    """Extract unique owner/repo from Brave search results."""
    repos = []
    if not brave_data:
        return repos
    results = brave_data.get("web", {}).get("results", [])
    _BLOCKED_OWNERS = frozenset(
        [
            "topics",
            "explore",
            "marketplace",
            "trending",
            "login",
            "signup",
            "notifications",
            "settings",
            "stars",
            "features",
            "pricing",
            "security",
        ]
    )
    for r in results:
        url = r.get("url", "").rstrip("/")
        match = _GITHUB_URL_RE.match(url)
        if match:
            repo = match.group(1)
            owner = repo.split("/")[0].lower()
            if owner not in _BLOCKED_OWNERS:
                repos.append(repo)
    # Deduplicate preserving order (case-insensitive)
    seen = set()
    unique = []
    for r in repos:
        key = r.lower()
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


def gh_search_repos(query, limit=10, timeout=30):
    """Search GitHub repos via gh CLI. Returns list of repo dicts."""
    stdout, stderr, rc = run_gh(
        [
            "search",
            "repos",
            query,
            "--sort",
            "stars",
            "--limit",
            str(limit),
            "--json",
            "fullName,description,stargazersCount,updatedAt,url,language",
        ],
        timeout=timeout,
    )
    if rc != 0:
        return []
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return []


def gh_repo_view(repo, timeout=30):
    """Fetch repo metadata. Returns (data_dict, error_string)."""
    stdout, stderr, rc = run_gh(
        [
            "repo",
            "view",
            repo,
            "--json",
            "name,description,stargazerCount,createdAt,updatedAt,pushedAt,url,"
            "homepageUrl,licenseInfo,primaryLanguage,languages,diskUsage,forkCount,"
            "isArchived,repositoryTopics,defaultBranchRef",
        ],
        timeout=timeout,
    )
    if rc != 0:
        return None, stderr.strip()
    try:
        return json.loads(stdout), None
    except json.JSONDecodeError:
        return None, "JSON parse error from gh repo view"


def gh_repo_readme(repo, max_chars=3000, timeout=30):
    """Fetch and decode README. Returns (content_string, error_string)."""
    stdout, stderr, rc = run_gh(["api", f"repos/{repo}/readme"], timeout=timeout)
    if rc != 0:
        return None, "README not found"
    try:
        data = json.loads(stdout)
        content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    except Exception:
        return None, "README decode failed"
    if max_chars > 0 and len(content) > max_chars:
        content = (
            content[:max_chars]
            + f"\n[...truncated — {len(content) - max_chars:,} more chars, use --max-chars 0 for full]"
        )
    return content, None


def gh_repo_tree(repo, default_branch=None, timeout=30):
    """Fetch repo file tree. Returns (data_dict, error_string)."""
    branches = []
    if default_branch:
        branches.append(default_branch)
    branches += [b for b in ("main", "master") if b not in branches]
    for branch in branches:
        stdout, stderr, rc = run_gh(
            ["api", f"repos/{repo}/git/trees/{branch}?recursive=1"],
            timeout=timeout,
        )
        if rc == 0:
            data, err = parse_json_gh(stdout, "git/trees")
            if err or data is None:
                return None, err or "git/trees parse error"
            return {
                "tree": data.get("tree", []),
                "truncated": data.get("truncated", False),
            }, None
    return None, "Tree fetch failed (no main/master branch)"


def gh_repo_languages(repo, timeout=30):
    """Fetch language breakdown. Returns (data_dict, error_string)."""
    stdout, stderr, rc = run_gh(["api", f"repos/{repo}/languages"], timeout=timeout)
    if rc != 0:
        return None, "Languages fetch failed"
    data, err = parse_json_gh(stdout, "languages")
    if err:
        return None, err
    return data, None


def analyze_repo(repo, max_chars=3000, timeout=30):
    """Analyze a single repo. Returns dict with all data."""
    view, err = gh_repo_view(repo, timeout)
    if view is None:
        return {"repo": repo, "error": err}

    # Extract default branch for tree fetch
    ref = view.get("defaultBranchRef") or {}
    default_branch = ref.get("name") if isinstance(ref, dict) else None

    readme, _ = gh_repo_readme(repo, max_chars, timeout)
    tree_data, _ = gh_repo_tree(repo, default_branch=default_branch, timeout=timeout)
    languages, _ = gh_repo_languages(repo, timeout)

    return {
        "repo": repo,
        "view": view,
        "readme": readme,
        "tree": tree_data,
        "languages": languages,
    }


def repo_discovery(query, limit=3, max_chars=3000, timeout=30):
    """Discover repos by topic using Brave + gh search (parallel queries)."""
    refined = refine_query(query)

    # Run discovery queries in parallel (2 sources)
    def _brave():
        return brave_search(f"site:github.com {query}", num=20, timeout=timeout)

    def _gh_refined():
        return gh_search_repos(refined, limit=10, timeout=timeout) if refined else []

    tasks = [_brave, _gh_refined]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        brave_data, gh_refined_results = list(executor.map(lambda f: f(), tasks))

    # Merge results sequentially (fast — just iterating lists)
    all_repos = []
    sources = {}

    brave_repos = extract_github_repos(brave_data)
    for repo in brave_repos:
        all_repos.append(repo)
        sources[repo.lower()] = list(
            dict.fromkeys(sources.get(repo.lower(), []) + ["Brave"])
        )

    for r in gh_refined_results:
        repo = r.get("fullName", "")
        if repo:
            key = repo.lower()
            if key not in sources:
                all_repos.append(repo)
            sources[key] = list(dict.fromkeys(sources.get(key, []) + ["gh"]))

    # Deduplicate preserving order (case-insensitive)
    seen = set()
    unique_repos = []
    for repo in all_repos:
        key = repo.lower()
        if key not in seen:
            seen.add(key)
            unique_repos.append(repo)

    # Limit
    top_repos = unique_repos[:limit]

    # Analyze each repo in parallel
    if top_repos:

        def _analyze(repo):
            print(f"  Analyzing {repo}...", file=sys.stderr)
            analysis = analyze_repo(repo, max_chars=max_chars, timeout=timeout)
            analysis["sources"] = sources.get(repo.lower(), [])
            return analysis

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(len(top_repos), 5)
        ) as executor:
            results = list(executor.map(_analyze, top_repos))
    else:
        results = []

    return {
        "query": query,
        "refined_query": refined,
        "total_discovered": len(unique_repos),
        "brave_count": len(brave_repos),
        "gh_count": sum(
            1 for r in sources if any(s.startswith("gh") for s in sources.get(r, []))
        ),
        "overlap_count": sum(1 for r in sources if len(set(sources.get(r, []))) > 1),
        "analyzed": len(results),
        "repos": results,
    }


def gh_code_search(query, language=None, num=10, timeout=30):
    """Search code across GitHub repos via gh CLI."""
    args = [
        "search",
        "code",
        query,
        "--limit",
        str(num),
        "--json",
        "path,repository,textMatches,url",
    ]
    if language:
        args.extend(["--language", language])
    stdout, stderr, rc = run_gh(args, timeout=timeout)
    if rc != 0:
        die(f"gh search code failed: {stderr.strip()}", 1)
    try:
        return json.loads(stdout), "code"
    except json.JSONDecodeError:
        die("gh search code returned invalid JSON", 1)


# ── Formatting ──────────────────────────────────────────────────


def format_answer(data):
    """Format Exa /answer response."""
    lines = []
    answer = data.get("answer", "")
    citations = data.get("citations", [])
    if answer:
        lines.append(answer)
    if citations:
        lines.append("")
        lines.append("Sources:")
        for i, c in enumerate(citations, 1):
            title = c.get("title", "")
            url = c.get("url", "")
            lines.append(f"  [{i}] {title} — {url}")
    return "\n".join(lines)


def format_links(data):
    """Format Exa /search response (no content)."""
    results = data.get("results", [])
    lines = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "Untitled")
        url = r.get("url", "")
        snippet = (r.get("text") or "")[:300]
        if snippet:
            snippet = snippet.strip()
            if len(snippet) == 300:
                snippet += "..."
        lines.append(f"=== {i} ===")
        lines.append(f"Title: {title}")
        lines.append(f"URL:   {url}")
        if snippet:
            lines.append(f"Text:  {snippet}")
        lines.append("")
    if not results:
        lines.append("No results found.")
    return "\n".join(lines)


def format_content(data, max_chars=3000):
    """Format Exa /search + contents response.

    Args:
        data: Parsed Exa API response.
        max_chars: Max chars per result. 0 = no truncation. Default 3000.
    """
    results = data.get("results", [])
    lines = []
    total_chars = 0
    shown_chars = 0
    skipped = 0
    for i, r in enumerate(results, 1):
        title = r.get("title", "Untitled")
        url = r.get("url", "")
        text = r.get("text") or ""
        if len(text.strip()) < 100:
            lines.append(f"=== {i} === [empty — likely paywalled or JS-rendered]")
            lines.append(f"Title:   {title}")
            lines.append(f"URL:     {url}")
            if text.strip():
                lines.append(f"Content: {text.strip()}")
            else:
                lines.append("Content: (empty)")
            lines.append("")
            skipped += 1
            continue
        total_chars += len(text)
        truncated = max_chars > 0 and len(text) > max_chars
        display = text[:max_chars] if max_chars > 0 else text
        shown_chars += len(display)
        lines.append(f"=== {i} ===")
        lines.append(f"Title:   {title}")
        lines.append(f"URL:     {url}")
        if truncated:
            lines.append(f"Content: {len(text):,} chars (showing first {max_chars:,})")
        else:
            lines.append(f"Content: {len(text):,} chars")
        lines.append(display)
        if truncated:
            lines.append(
                f"[...truncated — {len(text) - max_chars:,} more chars, use --max-chars 0 for full]"
            )
        lines.append("")
    if not results:
        lines.append("No results found.")
    else:
        footer = f"--- {len(results)} results, {total_chars:,} total chars ({shown_chars:,} shown) ---"
        if skipped:
            footer = f"--- {len(results)} results ({skipped} empty), {total_chars:,} total chars ({shown_chars:,} shown) ---"
        lines.append(footer)
    return "\n".join(lines)


def format_serp(data):
    """Format Serper /search response."""
    lines = []
    kg = data.get("knowledgeGraph")
    if kg:
        lines.append(f"Knowledge: {kg.get('title', '')}")
        if kg.get("description"):
            lines.append(f"  {kg['description']}")
        if kg.get("descriptionLink"):
            lines.append(f"  {kg['descriptionLink']}")
        lines.append("")
    ab = data.get("answerBox")
    if ab:
        lines.append(f"Answer: {ab.get('snippet', ab.get('answer', ''))}")
        if ab.get("link"):
            lines.append(f"  {ab['link']}")
        lines.append("")
    results = data.get("organic", [])
    for i, r in enumerate(results, 1):
        title = r.get("title", "Untitled")
        url = r.get("link", "")
        snippet = r.get("snippet", "")
        lines.append(f"=== {i} ===")
        lines.append(f"Title:   {title}")
        lines.append(f"URL:     {url}")
        if snippet:
            lines.append(f"Snippet: {snippet}")
        lines.append("")
    if not results and not kg and not ab:
        lines.append("No results found.")
    return "\n".join(lines)


def format_scholar(data):
    """Format Serper /scholar response with literature quality evaluation."""
    results = data.get("organic", [])
    lines = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "Untitled")
        url = r.get("link", "")
        snippet = r.get("snippet", "")
        cited = r.get("citedBy", "")
        year = r.get("year", "")
        authors = r.get("publicationInfo", "")
        status = r.get("quality_status", "")
        journal = r.get("journal", "")
        if_val = r.get("impact_factor")
        if_source = r.get("if_source", "")

        header = f"=== {i} ==="
        if status:
            header += f" [{status}]"
        lines.append(header)
        lines.append(f"Title:   {title}")
        if journal or if_val is not None:
            if_str = f"{if_val:.1f}" if if_val is not None else "Unknown"
            j_line = f"Journal: {journal or 'Unknown'} (Impact Factor: {if_str}"
            if if_source:
                j_line += f" | {if_source}"
            j_line += ")"
            lines.append(j_line)
        if year or authors:
            lines.append(f"Meta:    {authors} {year}".strip())
        lines.append(f"URL:     {url}")
        if cited:
            lines.append(f"Cited:   {cited}")
        if snippet:
            lines.append(f"Snippet: {snippet}")
        lines.append("")

    summary = data.get("quality_summary")
    if summary:
        min_if = summary.get("min_if", 6.0)
        min_year = summary.get("min_year", 2021)
        screened = summary.get("screened", len(results))
        qual = summary.get("qualified", 0)
        fb = summary.get("fallback", 0)
        disq = summary.get("disqualified", 0)
        if min_year is not None:
            lines.append(
                f"--- Literature Quality Filter: {min_year}+ in peer-reviewed journals with IF > {min_if} (fallback: pre-{min_year}, IF > {min_if}) ---"
            )
        else:
            lines.append(
                f"--- Literature Quality Filter: All years in peer-reviewed journals with IF > {min_if} ---"
            )
        lines.append(
            f"Screened: {screened} | Qualified: {qual} | Fallback: {fb} | Disqualified: {disq}"
        )
        if not results:
            lines.append(
                f"No papers met the literature quality standard (IF > {min_if})."
            )
            lines.append(
                "Pass --no-filter to view raw Google Scholar results or --min-if <float> to adjust threshold."
            )
    elif not results:
        lines.append("No results found.")
    return "\n".join(lines)


def format_fresh(data):
    """Format Brave /web/search response."""
    results = data.get("web", {}).get("results", [])
    lines = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "Untitled")
        url = r.get("url", "")
        snippet = r.get("description", "")
        age = r.get("age", "")
        lines.append(f"=== {i} ===")
        lines.append(f"Title:   {title}")
        if age:
            lines.append(f"Age:     {age}")
        lines.append(f"URL:     {url}")
        if snippet:
            lines.append(f"Snippet: {snippet}")
        lines.append("")
    if not results:
        lines.append("No results found.")
    return "\n".join(lines)


def _format_repo_single(analysis):
    """Format a single repo analysis dict."""
    lines = []
    repo = analysis["repo"]

    if "error" in analysis and "view" not in analysis:
        lines.append(f"=== {repo} ===")
        lines.append(f"Error: {analysis['error']}")
        return "\n".join(lines)

    view = analysis.get("view", {})
    lines.append(f"=== {repo} ===")
    url = view.get("url", f"https://github.com/{repo}")
    desc = view.get("description") or "No description"
    stars = view.get("stargazerCount", 0)
    forks = view.get("forkCount", 0)
    license_info = view.get("licenseInfo") or {}
    license_name = license_info.get("name", "None") if license_info else "None"
    primary_lang = (view.get("primaryLanguage") or {}).get("name", "Unknown")
    archived = view.get("isArchived", False)
    created = view.get("createdAt", "")[:10]
    updated = view.get("updatedAt", "")[:10]
    topics = [t["name"] for t in (view.get("repositoryTopics") or [])]

    lines.append(f"URL:         {url}")
    homepage = view.get("homepageUrl") or ""
    if homepage and homepage != url:
        lines.append(f"Homepage:    {homepage}")
    lines.append(f"Description: {desc}")
    lines.append(f"Stars: {stars:,} | Forks: {forks:,} | License: {license_name}")
    lines.append(f"Language: {primary_lang} | Archived: {'Yes' if archived else 'No'}")
    pushed = view.get("pushedAt", "")[:10]
    lines.append(f"Created: {created} | Updated: {updated} | Last push: {pushed}")
    if topics:
        lines.append(f"Topics: {', '.join(topics)}")

    # Sources (discovery mode only)
    sources = analysis.get("sources", [])
    if sources:
        lines.append(f"Found via: {', '.join(sources)}")

    # Languages breakdown
    languages = analysis.get("languages")
    if languages and isinstance(languages, dict):
        total = sum(languages.values())
        if total > 0:
            lang_items = []
            for lang_name, size in sorted(languages.items(), key=lambda x: -x[1])[:5]:
                pct = round(size / total * 100)
                lang_items.append(f"{lang_name} {pct}%")
            lines.append(f"Languages: {', '.join(lang_items)}")

    # README
    readme = analysis.get("readme")
    if readme:
        lines.append("")
        lines.append("--- README ---")
        lines.append(readme)

    # File tree — show top-level entries
    tree_data = analysis.get("tree")
    if tree_data and isinstance(tree_data, dict):
        tree = tree_data.get("tree", [])
        truncated = tree_data.get("truncated", False)
        lines.append("")
        trunc_note = " (TRUNCATED)" if truncated else ""
        lines.append(f"--- File Tree ({len(tree)} entries{trunc_note}) ---")
        top_entries = []
        for entry in tree:
            path = entry["path"]
            if "/" not in path:
                suffix = "/" if entry["type"] == "tree" else ""
                top_entries.append(f"{path}{suffix}")
        for e in sorted(top_entries)[:30]:
            lines.append(f"  {e}")
        remaining = len(tree) - len(top_entries)
        if remaining > 0:
            lines.append(f"  ... ({remaining} more entries in subdirectories)")

    return "\n".join(lines)


def format_repo_known(repos_data):
    """Format known-repo analysis (single or multi-repo)."""
    parts = []
    for i, analysis in enumerate(repos_data):
        if i > 0:
            parts.append("")
            parts.append("=" * 60)
            parts.append("")
        parts.append(_format_repo_single(analysis))
    return "\n".join(parts)


def format_repo_discovery(data):
    """Format repo topic discovery results."""
    lines = []
    lines.append(f'Discovery: "{data["query"]}"')
    lines.append(f'Refined query for gh: "{data["refined_query"]}"')
    lines.append(
        f"Sources: Brave ({data['brave_count']} repos) "
        f"+ gh search ({data['gh_count']} repos)"
    )
    lines.append(
        f"Total discovered: {data['total_discovered']} "
        f"| Analyzing top {data['analyzed']}"
    )
    if data["overlap_count"] > 0:
        lines.append(
            f"Overlap: {data['overlap_count']} repos found by multiple sources"
        )
    lines.append("")
    lines.append("=" * 60)

    for i, analysis in enumerate(data["repos"]):
        lines.append("")
        lines.append(_format_repo_single(analysis))
        if i < len(data["repos"]) - 1:
            lines.append("")
            lines.append("-" * 60)

    return "\n".join(lines)


def format_code(data):
    """Format gh search code results."""
    results = data if isinstance(data, list) else []
    lines = []
    for i, r in enumerate(results, 1):
        path = r.get("path", "")
        repo_info = r.get("repository", {})
        repo_name = repo_info.get("nameWithOwner", "")
        file_url = r.get("url", "")
        matches = r.get("textMatches", [])

        lines.append(f"=== {i} ===")
        lines.append(f"File: {path}")
        lines.append(f"Repo: {repo_name}")
        if file_url:
            lines.append(f"URL:  {file_url}")
        for m in matches[:3]:
            fragment = m.get("fragment", "")
            if fragment:
                for line in fragment.split("\n")[:5]:
                    if line.rstrip():
                        lines.append(f"  {line.rstrip()}")
        lines.append("")
    if not results:
        lines.append("No code results found.")
    else:
        lines.append(f"--- {len(results)} results ---")
    return "\n".join(lines)


FORMATTERS = {
    "answer": format_answer,
    "links": format_links,
    "content": format_content,
    "serp": format_serp,
    "scholar": format_scholar,
    "fresh": format_fresh,
    "code": format_code,
}


# ── Universal schema + Query expansion ─────────────────────────
#
# Tier 2 features (plan: /Users/pridiuksson/.qoder/plans/gleaming-peak-lark.md):
#   Feature A: ResearchResult — unified schema across Exa/Serper/Brave/gh
#              so downstream consumers (grill, plan, Knowledge notes, future
#              Tier 1 local-first search) don't have to parse 8 different shapes.
#   Feature B: Rule-based query expansion — synonym substitution gives 2-3x
#              recall on keyword APIs (Serper, Brave). Exa is semantic and is
#              intentionally excluded. gh code search is literal and excluded.


@dataclass
class ResearchResult:
    """Unified result schema across all search backends.

    Modeled on NVIDIA AI-Q knowledge_layer's `Chunk` schema
    (sources/knowledge_layer/src/schema.py). Every backend normalizes its
    raw response into a list of these so downstream consumers see one shape.

    Repo modes (`--repo`, `--code`) are NOT normalized — their output is
    structurally different (nested per-repo objects with view/readme/tree/
    languages) and forcing them here would lose information.
    """

    source: str
    url: str
    title: str
    content: str
    content_type: str
    score: float | None
    citation: str
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# Backends that accept --expand. Exa is semantic (already handles natural
# language). gh code search is literal (expansion would corrupt patterns).
_EXPANDABLE_MODES = frozenset({"serp", "scholar", "fresh"})


# Synonym table for rule-based query expansion (used by expand_query).
#
# Curation audit (Group 3 of polish pass):
#   Dropped: kubernetes→k8s (Google-equivalent abbreviation, not a synonym).
#   Dropped: docker→container (too broad — retrieves shipping containers, Linux
#            containers generally). Kept docker→containerization.
#   Dropped: vector→dense (unusual usage in ML context). Kept vector→embedding.
#   Dropped: agent→assistant (too generic — retrieves virtual assistants,
#            administrative assistants). Kept agent→bot, agent→copilot.
#   Dropped: kubernetes→container-orchestration (retrieves Kubernetes
#            competitors — Nomad, Docker Swarm — rather than synonyms).
#   Dropped: llm→gpt (brand bias). Kept llm→language-model, llm→foundation-model.
#   Dropped: serverless→lambda (brand bias, AWS Lambda specifically). Kept
#            serverless→cloud-functions, serverless→faas.
#   Dropped: fine-tuning→rlhf (RLHF is one specific technique, not a synonym).
#            Kept fine-tuning→finetune, fine-tuning→sft.
#   Dropped: search→retrieval (ML jargon, not a web-search synonym).
#   Dropped: search→query (SQL-flavored, retrieves SQL query results).
#            Kept search→lookup.
#
# Each entry must pass: "would this substitution retrieve noise unrelated to
# the original intent?" If yes, drop it.
_SYNONYMS: dict[str, list[str]] = {
    # --- Concept synonyms (framework / library / toolkit) ---
    "framework": ["library", "toolkit", "platform"],  # generic software concept
    "frameworks": ["libraries", "toolkits", "platforms"],  # plural form
    "library": ["framework", "package", "module"],  # symmetric to above
    # --- Architectural patterns ---
    "orchestration": ["coordination", "swarm", "dispatch"],  # multi-agent/coordination
    "microservice": ["service", "distributed", "modular"],  # distributed-systems vocab
    "microservices": ["services", "distributed", "modular"],  # plural form
    # --- Learning content ---
    "tutorial": ["guide", "walkthrough", "howto"],  # all learning-content genres
    # --- Interface / API synonyms ---
    "api": ["sdk", "client", "interface"],  # interface-layer terms, not brand-specific
    "cli": ["command-line", "terminal", "shell"],  # CLI interface variants
    "websocket": ["realtime", "streaming", "sse"],  # realtime transport tech
    # --- Data storage ---
    "database": ["datastore", "storage", "db"],  # generic storage layer terms
    "caching": ["cache", "memoization", "buffering"],  # caching techniques (no brand)
    "queue": ["job-queue", "message-queue", "broker"],  # async-messaging synonyms
    # --- Security ---
    "authentication": [
        "auth",
        "login",
        "oauth",
    ],  # auth layer (oauth is protocol, generic)
    # --- Operations ---
    "deployment": ["deploy", "release", "rollout"],  # release-pipeline verbs
    "monitoring": ["observability", "telemetry", "metrics"],  # observability vocab
    "benchmark": ["evaluation", "comparison", "perf"],  # perf-testing synonyms
    # --- Container / IaC (carefully curated; brand-neutral only) ---
    "docker": ["containerization"],  # brand-neutral; dropped "container" (too broad)
    "terraform": [
        "iac",
        "infrastructure-as-code",
        "pulumi",
    ],  # IaC generic + one peer tool
    "serverless": ["cloud-functions", "faas"],  # generic FaaS terms; dropped "lambda"
    # --- AI/ML concepts (brand-neutral) ---
    "agent": ["bot", "copilot"],  # AI agent synonyms; dropped "assistant" (too generic)
    "agents": ["bots", "copilots"],  # plural form
    "llm": ["language-model", "foundation-model"],  # generic; dropped "gpt" (brand)
    "rag": ["retrieval-augmented", "grounding"],  # RAG expansion terms
    "fine-tuning": [
        "finetune",
        "sft",
    ],  # fine-tuning variants; dropped "rlhf" (specific technique)
    "embedding": ["vector", "representation"],  # ML vector-embedding synonyms
    "embeddings": ["vectors", "representations"],  # plural form
    "vector": ["embedding"],  # symmetric; dropped "dense" (unusual usage)
    # --- Search / ingest operations ---
    "search": [
        "lookup"
    ],  # conservative; dropped "retrieval" (ML jargon) and "query" (SQL-flavored)
    "parsing": ["parser", "extraction", "tokenizer"],  # text-processing synonyms
    "scraping": ["crawling", "spider", "harvesting"],  # web-scraping synonyms
    "indexing": ["index", "ingestion"],  # data-ingest synonyms
}


def _tokenize_query(query: str) -> list[str]:
    """Split query into tokens, preserving casing and stopwords.

    Unlike `refine_query` (which lowercases and strips stopwords for gh search
    repos), this preserves the original query so Serper/Brave — which handle
    natural-language context better — get useful signal. The synonym table
    keys are all lowercase, so matching is case-insensitive.
    """
    return re.findall(r"[a-zA-Z0-9+#.\-]+", query)


def expand_query(query: str, n: int = 3) -> list[str]:
    """Generate up to n keyword variants of a query via synonym substitution.

    Variant 1 is always the original query (preserving casing + stopwords).
    Variants 2..n-1 each swap ONE synonym-bearing token to its top synonym.
    When n >= 4 and there are >= 2 synonym-bearing tokens, the last variant
    is a "max-distance" swap: ALL detected synonyms are swapped at once,
    producing the maximally-different query alongside the near-variants.

    Returns only as many variants as are actually produced. If the query has
    fewer synonym-bearing tokens than slots would allow, the list is shorter
    than n (NOT padded with duplicates or garbage). The caller decides what
    to do with a short list — typically run single-query if only 1 variant.

    If no synonyms match, returns just the original (graceful no-op).
    """
    base_tokens = _tokenize_query(query)
    if not base_tokens:
        return [query]

    variants = [query]

    # Map: token index → synonym list (only for tokens that have synonyms).
    # Case-insensitive matching against the lowercase _SYNONYMS keys.
    swap_targets: list[tuple[int, str, list[str]]] = []
    for i, tok in enumerate(base_tokens):
        syns = _SYNONYMS.get(tok.lower())
        if syns:
            swap_targets.append((i, tok, syns))

    # Near-variants: one-token-per-swap, consuming slots 1..(n-1) when n<4
    # or 1..(n-2) when n>=4 (last slot reserved for max-distance).
    # If there aren't enough swap targets, we produce fewer near-variants
    # rather than padding — duplicates would waste API credits and mislead
    # the caller about how many distinct queries were run.
    near_slot_count = (n - 1) if n < 4 else (n - 2)
    for idx, _tok, syns in swap_targets[:near_slot_count]:
        swapped = base_tokens[:]
        swapped[idx] = syns[0]
        variants.append(" ".join(swapped))

    # Max-distance variant: swap ALL synonyms at once (only if n>=4 and
    # there are at least 2 synonym-bearing tokens — otherwise it's
    # identical to one of the near-variants and not worth the slot).
    if n >= 4 and len(swap_targets) >= 2:
        max_distance = base_tokens[:]
        for idx, _tok, syns in swap_targets:
            max_distance[idx] = syns[0]
        variants.append(" ".join(max_distance))

    return variants


def merge_variant_results(
    per_variant: list[list["ResearchResult"]],
) -> list["ResearchResult"]:
    """Merge per-variant result lists into one deduplicated ranked list.

    Same URL found by 2+ variants gets a corroboration score boost and is
    sorted to the top. Dedup is URL-only — synthesized answers with empty
    URL are never deduped (exa_answer legitimately returns citations with
    both url="" and the same citation text, and we want all of them).

    Peer-review fixes baked in:
      - empty-URL never-dedup guard (URL-only dedup; no citation fallback)
      - O(1) boost lookup via seen_urls index dict
      - found_in_variants seeded at 1 so ★ marker is a clean `>= 2` check
    """
    seen_urls: dict[str, int] = {}  # url -> index in merged
    merged: list[ResearchResult] = []

    for variant_results in per_variant:
        for r in variant_results:
            # Dedupe key: URL when present. Empty URL → NEVER dedupe, because
            # synthesized answers from exa_answer legitimately share both url=""
            # AND the same citation text — deduping them by citation would lose
            # real results.
            url_key = _canonical_url(r.url) if r.url else None

            existing_idx = seen_urls.get(url_key) if url_key else None

            if existing_idx is not None:
                existing = merged[existing_idx]
                if existing.score is not None and r.score is not None:
                    existing.score = min(1.0, max(existing.score, r.score) + 0.05)
                existing.metadata["found_in_variants"] = (
                    existing.metadata.get("found_in_variants", 1) + 1
                )
            else:
                r.metadata.setdefault("found_in_variants", 1)
                idx = len(merged)
                merged.append(r)
                if url_key:
                    seen_urls[url_key] = idx

    merged.sort(
        key=lambda r: (
            -r.metadata.get("found_in_variants", 1),
            r.score is None,
            -(r.score or 0.0),
        )
    )
    return merged


# ── Normalizers (raw API JSON → list[ResearchResult]) ──────────


def _serper_position_score(position: int) -> float:
    """Simple position-decay score: pos 1 → 0.95, pos 10 → 0.5."""
    return round(max(0.1, 1.0 - position * 0.05), 2)


def normalize_serper(data: Any, content_type: str = "text") -> list[ResearchResult]:
    """Normalize Serper /search or /scholar response.

    content_type="text" for /search, "paper" for /scholar (adds year/authors/
    citedBy to metadata).
    """
    results: list[ResearchResult] = []

    kg = data.get("knowledgeGraph")
    if kg:
        kg_title = kg.get("title", "")
        kg_desc = kg.get("description", "")
        kg_link = kg.get("descriptionLink", "") or kg.get("website", "")
        results.append(
            ResearchResult(
                source="serper",
                url=kg_link,
                title=kg_title,
                content=kg_desc,
                content_type="knowledge_panel",
                score=1.0,
                citation=f"{kg_title} (Google Knowledge Panel)"
                + (f" — {kg_link}" if kg_link else ""),
                metadata={
                    "title": kg_title,
                    "description": kg_desc,
                    "link": kg_link,
                },
            )
        )

    ab = data.get("answerBox")
    if ab:
        ab_snippet = ab.get("snippet") or ab.get("answer") or ""
        ab_link = ab.get("link", "")
        ab_title = ab.get("title", "") or "Google Answer Box"
        results.append(
            ResearchResult(
                source="serper",
                url=ab_link,
                title=ab_title,
                content=ab_snippet,
                content_type="answer",
                score=1.0,
                citation=f"{ab_title} (Answer Box)"
                + (f" — {ab_link}" if ab_link else ""),
                metadata={
                    "title": ab_title,
                    "snippet": ab_snippet,
                    "link": ab_link,
                },
            )
        )

    for r in data.get("organic", []):
        title = r.get("title", "Untitled")
        url = r.get("link", "")
        snippet = r.get("snippet", "")
        position = r.get("position", 0)
        meta: dict = {"position": position}
        # Position-decay proxy goes in metadata, not top-level score.
        # Serper provides no real relevance signal — fabricating one at the
        # top level would mislead consumers that sort by score. Downstream
        # code that wants a rank-based proxy reads metadata["position_score"].
        if position:
            meta["position_score"] = _serper_position_score(position)
        if content_type == "paper":
            if r.get("year"):
                meta["year"] = r.get("year")
            if r.get("publicationInfo"):
                meta["authors"] = r.get("publicationInfo")
            if r.get("citedBy"):
                meta["cited_by"] = r.get("citedBy")
            if r.get("quality_status"):
                meta["quality_status"] = r.get("quality_status")
            if r.get("journal"):
                meta["journal"] = r.get("journal")
            if r.get("impact_factor") is not None:
                meta["impact_factor"] = r.get("impact_factor")
            if r.get("if_source"):
                meta["if_source"] = r.get("if_source")
        results.append(
            ResearchResult(
                source="serper",
                url=url,
                title=title,
                content=snippet,
                content_type=content_type,
                score=None,
                citation=f"{title} — {url}" if url else title,
                metadata=meta,
            )
        )
    return results


def normalize_brave(data: Any, fresh: bool = False) -> list[ResearchResult]:
    """Normalize Brave /web/search response. `fresh=True` flags the freshness=pw variant."""
    results: list[ResearchResult] = []
    for r in data.get("web", {}).get("results", []):
        title = r.get("title", "Untitled")
        url = r.get("url", "")
        snippet = r.get("description", "")
        age = r.get("age", "")
        meta: dict = {}
        if age:
            meta["age"] = age
        if fresh:
            meta["freshness_filter"] = "pw"
        results.append(
            ResearchResult(
                source="brave",
                url=url,
                title=title,
                content=snippet,
                content_type="text",
                score=None,
                citation=f"{title} — {url}" + (f" ({age})" if age else ""),
                metadata=meta,
            )
        )
    return results


def format_expansion_results(
    results: list[ResearchResult],
    max_chars: int = 3000,
    query: str = "",
    variants: list[str] | None = None,
) -> str:
    """Format a list of ResearchResults into AI-Q-style structured markdown.

    Output shape borrowed from sources/knowledge_layer/src/register.py
    `_format_results`. Downstream consumers (grill, plan, future local-first
    search, Knowledge/ notes) can parse this deterministically.
    """
    if not results:
        line = (
            f"No results found for query: {query!r}" if query else "No results found."
        )
        return line

    lines: list[str] = [f"Found {len(results)} result(s):\n"]

    for i, r in enumerate(results, 1):
        corrob = r.metadata.get("found_in_variants", 1)
        marker = "★ " if corrob >= 2 else ""
        q_tag = (
            f" [{r.metadata['quality_status']}]"
            if r.metadata.get("quality_status")
            else ""
        )
        header = f"--- {marker}Result {i}{q_tag} ---"
        lines.append(header)
        lines.append(f"Source: {r.source}")
        if r.url:
            lines.append(f"URL: {r.url}")
        if r.title:
            lines.append(f"Title: {r.title}")
        if r.metadata.get("journal"):
            if_val = r.metadata.get("impact_factor")
            if_str = f"{if_val:.1f}" if if_val is not None else "Unknown"
            lines.append(f"Journal: {r.metadata['journal']} (Impact Factor: {if_str})")
        lines.append(f"Content Type: {r.content_type}")
        if r.score is not None:
            lines.append(f"Relevance Score: {r.score:.2f}")
        if corrob >= 2:
            lines.append(f"Corroboration: found by {corrob} query variants")
        if r.citation:
            lines.append(f"Citation: {r.citation}")
        lines.append("")

        content = r.content
        if max_chars > 0 and len(content) > max_chars:
            content = (
                content[:max_chars]
                + f"\n[...truncated — {len(content) - max_chars:,} more chars]"
            )
        if content:
            lines.append(content)
            lines.append("")

    # Footer with optional expansion stats.
    total = len(results)
    corroborated = sum(
        1 for r in results if r.metadata.get("found_in_variants", 1) >= 2
    )
    footer_parts = [f"{total} results"]
    if variants and len(variants) > 1:
        footer_parts.append(f"from {len(variants)} query variants")
    if corroborated:
        footer_parts.append(f"{corroborated} corroborated across variants")
    lines.append("--- " + ", ".join(footer_parts) + " ---")
    if variants and len(variants) > 1:
        lines.append("Variants: " + " | ".join(f'"{v}"' for v in variants))

    return "\n".join(lines)


# ── CLI ─────────────────────────────────────────────────────────


def parse_args(argv):
    """Parse command-line arguments."""
    query = None
    mode = None
    num = None
    domains = None
    raw = False
    no_expand = False
    expand_n = 3
    timeout = 30
    max_chars = 3000
    limit = None
    language = None
    min_if = 6.0
    min_year: int | None = 2021
    no_filter = False

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in (
            "--answer",
            "--links",
            "--content",
            "--scholar",
            "--fresh",
            "--serp",
            "--repo",
            "--code",
        ):
            if mode:
                die(f"Only one search mode allowed (got {mode} and {arg})")
            mode = arg.lstrip("-")
            i += 1
            if i < len(argv) and not argv[i].startswith("--"):
                query = argv[i]
                i += 1
            else:
                die(f"{arg} requires a query string")
        elif arg in ("-n", "--num"):
            i += 1
            if i >= len(argv):
                die("--num requires a number")
            num = int(argv[i])
            i += 1
        elif arg == "--domains":
            i += 1
            if i >= len(argv):
                die("--domains requires a comma-separated list")
            domains = argv[i]
            i += 1
        elif arg == "--raw":
            raw = True
            i += 1
        elif arg == "--expand":
            # Backward-compat no-op: expansion is now default-on for keyword
            # APIs (--serp, --scholar, --fresh). Accept the flag but don't
            # change behavior. Use --no-expand to opt out.
            i += 1
        elif arg == "--no-expand":
            no_expand = True
            i += 1
        elif arg == "--expand-n":
            i += 1
            if i >= len(argv):
                die("--expand-n requires a number")
            expand_n = int(argv[i])
            if expand_n < 2 or expand_n > 5:
                die("--expand-n must be between 2 and 5")
            i += 1
        elif arg == "--timeout":
            i += 1
            if i >= len(argv):
                die("--timeout requires a number")
            timeout = int(argv[i])
            i += 1
        elif arg == "--max-chars":
            i += 1
            if i >= len(argv):
                die("--max-chars requires a number (0 = no truncation)")
            max_chars = int(argv[i])
            i += 1
        elif arg == "--limit":
            i += 1
            if i >= len(argv):
                die("--limit requires a number")
            limit = int(argv[i])
            if limit < 1 or limit > 10:
                die("--limit must be between 1 and 10")
            i += 1
        elif arg == "--language":
            i += 1
            if i >= len(argv):
                die("--language requires a language name")
            language = argv[i]
            i += 1
        elif arg == "--min-if":
            i += 1
            if i >= len(argv):
                die("--min-if requires a number")
            min_if = float(argv[i])
            i += 1
        elif arg == "--min-year":
            i += 1
            if i >= len(argv):
                die("--min-year requires a year")
            min_year = int(argv[i])
            i += 1
        elif arg == "--all-years":
            min_year = None
            i += 1
        elif arg == "--no-filter":
            no_filter = True
            i += 1
        elif arg in ("-h", "--help"):
            print(__doc__)
            sys.exit(0)
        else:
            die(f"Unknown argument: {arg}")

    if not mode:
        die(
            "Specify a search mode: --answer, --links, --content, --scholar, "
            "--fresh, --serp, --repo, --code"
        )
    if not query:
        die("A query string is required")
    return _Args(
        mode=mode,
        query=query,
        num=num,
        domains=domains,
        raw=raw,
        no_expand=no_expand,
        expand_n=expand_n,
        timeout=timeout,
        max_chars=max_chars,
        limit=limit,
        language=language,
        min_if=min_if,
        min_year=min_year,
        no_filter=no_filter,
    )


def main():
    parsed = parse_args(sys.argv[1:])
    mode = parsed.mode
    query = parsed.query
    num = parsed.num
    domains = parsed.domains
    raw = parsed.raw
    no_expand = parsed.no_expand
    expand_n = parsed.expand_n
    timeout = parsed.timeout
    max_chars = parsed.max_chars
    limit = parsed.limit
    language = parsed.language
    min_if = parsed.min_if
    min_year = parsed.min_year
    no_filter = parsed.no_filter

    # parse_args() calls die() (NoReturn) when query is falsy. This narrows
    # query to str for the rest of main(). Redundant with the check in
    # parse_args() but needed for the type checker.
    if query is None:
        die("A query string is required")

    # Defaults per mode
    if num is None:
        num = 5 if mode in ("answer", "links", "content", "scholar") else 10

    # Expansion is DEFAULT-ON for keyword APIs (--serp, --scholar, --fresh)
    # unless --no-expand is explicitly set. Exa is semantic (doesn't benefit),
    # --code is literal (synonym substitution corrupts patterns), --repo has
    # its own hardcoded multi-query expansion internally.
    use_expansion = not no_expand and mode in _EXPANDABLE_MODES and query is not None
    variants: list[str] | None = None
    if use_expansion:
        variants = expand_query(query, expand_n)
        if len(variants) > 1:
            print(
                f"Expanding query into {len(variants)} variants: "
                + " | ".join(f'"{v}"' for v in variants),
                file=sys.stderr,
            )

    # Dispatch to backend. For expandable modes with >1 variant, fan out in
    # parallel via ThreadPoolExecutor (reuses the pattern from repo_discovery).
    normalized: list[ResearchResult] | None = None
    # data holds API response JSON (dict for Exa/Serper/Brave, list for repo
    # modes and code search). Typed Any because the shape varies per mode.
    data: Any = None
    fmt_type: str = ""

    if use_expansion and variants and len(variants) > 1:
        per_variant_raw: list = []

        def _call_variant(q: str):
            if mode == "serp":
                return serper_search(q, num, timeout)[0]
            elif mode == "scholar":
                return serper_scholar(
                    q,
                    num,
                    timeout,
                    min_if=min_if,
                    min_year=min_year,
                    no_filter=no_filter,
                )[0]
            elif mode == "fresh":
                return brave_fresh(q, num, domains, timeout)[0]
            return None

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(len(variants), 5)
        ) as executor:
            per_variant_raw = list(executor.map(_call_variant, variants))

        # Use the first variant's fmt_type for legacy --raw output.
        if mode == "serp":
            data, fmt_type = per_variant_raw[0], "serp"
        elif mode == "scholar":
            data, fmt_type = per_variant_raw[0], "scholar"
        else:
            data, fmt_type = per_variant_raw[0], "fresh"

        # Normalize each variant, then merge+dedupe.
        if mode == "serp":
            per_variant_normalized = [normalize_serper(d) for d in per_variant_raw]
        elif mode == "scholar":
            per_variant_normalized = [
                normalize_serper(d, content_type="paper") for d in per_variant_raw
            ]
        else:
            per_variant_normalized = [
                normalize_brave(d, fresh=True) for d in per_variant_raw
            ]
        normalized = merge_variant_results(per_variant_normalized)
    else:
        # Single-query dispatch — legacy path, unchanged.
        if mode == "answer":
            data, fmt_type = exa_answer(query, num, domains, timeout)
        elif mode == "links":
            data, fmt_type = exa_search(
                query, num, with_content=False, domains=domains, timeout=timeout
            )
        elif mode == "content":
            data, fmt_type = exa_search(
                query, num, with_content=True, domains=domains, timeout=timeout
            )
        elif mode == "serp":
            data, fmt_type = serper_search(query, num, timeout)
        elif mode == "scholar":
            data, fmt_type = serper_scholar(
                query,
                num,
                timeout,
                min_if=min_if,
                min_year=min_year,
                no_filter=no_filter,
            )
        elif mode == "fresh":
            data, fmt_type = brave_fresh(query, num, domains, timeout)
        elif mode == "repo":
            # NOTE: repo modes intentionally bypass ResearchResult normalization.
            # Their output is a nested per-repo object (view/readme/tree/languages)
            # whose structure cannot be flattened without losing information.
            # Tier 1 local-first search will only use web modes, so this gap is
            # acceptable and documented rather than forced into the wrong shape.
            check_gh_auth()
            # Resolve GitHub URLs to owner/repo
            parts = [p.strip() for p in query.split(",")]
            resolved = []
            for part in parts:
                url_repo = extract_repo_from_url(part)
                resolved.append(url_repo if url_repo else part)
            query = ",".join(resolved)

            if is_repo_pattern(query):
                # Known-repo mode — analyze repos in parallel
                repos = [r.strip() for r in query.split(",")]

                def _analyze_known(repo):
                    print(f"Analyzing {repo}...", file=sys.stderr)
                    return analyze_repo(repo, max_chars=max_chars, timeout=timeout)

                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=min(len(repos), 5)
                ) as executor:
                    repos_data = list(executor.map(_analyze_known, repos))
                data = repos_data
                fmt_type = "repo_known"
            else:
                # Topic discovery mode
                if limit is None:
                    limit = 3
                print(
                    f'Discovering repos for: "{query}" (limit: {limit})...',
                    file=sys.stderr,
                )
                data = repo_discovery(
                    query, limit=limit, max_chars=max_chars, timeout=timeout
                )
                fmt_type = "repo_discovery"
        elif mode == "code":
            # NOTE: --code is literal code-pattern search, so expansion would
            # corrupt it (swapping `from` with `since` etc.). Bypass normalization
            # path; gh_code_search already returns the list shape we need.
            check_gh_auth()
            data, fmt_type = gh_code_search(
                query, language=language, num=num, timeout=timeout
            )
        else:
            die(f"Unknown mode: {mode}")

    # Output routing.
    if raw:
        # --raw: dump the raw API JSON (unmodified vendor response).
        print(json.dumps(data, indent=2, ensure_ascii=False))
    elif fmt_type == "content":
        print(format_content(data, max_chars))
    elif fmt_type == "repo_known":
        print(format_repo_known(data))
    elif fmt_type == "repo_discovery":
        print(format_repo_discovery(data))
    elif fmt_type == "code":
        print(format_code(data))
    else:
        if use_expansion and variants and len(variants) > 1 and normalized:
            # Expanded output: use format_expansion_results, which produces AI-Q-style
            # "Result N" sections with ★ corroboration markers and a variants
            # footer. This is the formatter the schema was designed for.
            print(format_expansion_results(normalized, max_chars, query, variants))
        else:
            # Non-expanded: legacy per-mode formatters (format_serp, format_links,
            # format_scholar, format_fresh). These preserve the original output
            # shape for scripts that parse it.
            formatter = FORMATTERS.get(fmt_type)
            if formatter:
                print(formatter(data))
            else:
                print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
